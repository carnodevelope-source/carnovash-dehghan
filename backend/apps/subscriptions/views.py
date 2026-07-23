import csv
import io
from decimal import Decimal

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Prefetch, Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auth.models import CarWash, User
from apps.auth.views import _is_hq_admin, _is_hq_user, _platform_role

from .models import (
    BulkServiceJob,
    BulkServiceJobItem,
    PlatformProject,
    ServiceAlert,
    ServiceOrder,
    ServicePlan,
    ServiceProduct,
    ServiceSubscription,
)
from .serializers import (
    BulkServiceJobSerializer,
    PlatformProjectSerializer,
    ServiceAlertSerializer,
    ServiceAuditLogSerializer,
    ServiceOrderSerializer,
    ServicePaymentRecordSerializer,
    ServicePeriodSerializer,
    ServiceProductSerializer,
    ServiceSubscriptionSerializer,
)
from .services import (
    apply_hq_action,
    backfill_subscriptions_from_feature_purchases,
    create_order_and_activate,
    process_bulk_job,
    product_share_group,
    renew_subscription,
    seed_catalog_from_legacy,
    summarize_subscriptions,
)


SUPPORT_HIDDEN_FIELDS = {
    'cost_amount',
    'net_profit',
    'cost_total',
    'sales_revenue',
    'renewal_revenue',
    'net_profit',
}


def _capabilities(user):
    role = _platform_role(user) or ''
    if role == User.PlatformRoles.HQ_ADMIN or role == 'hq_admin':
        return {
            'role': 'hq_admin',
            'see_all_projects': True,
            'see_financial': True,
            'see_holding_profit': True,
            'see_costs': True,
            'mutate_status': True,
            'register_payment': True,
            'export': True,
            'bulk': True,
            'technical_settings': True,
        }
    if role == 'hq_finance':
        return {
            'role': 'hq_finance',
            'see_all_projects': True,
            'see_financial': True,
            'see_holding_profit': True,
            'see_costs': True,
            'mutate_status': False,
            'register_payment': True,
            'export': True,
            'bulk': False,
            'technical_settings': False,
        }
    if role == 'hq_project_manager':
        return {
            'role': 'hq_project_manager',
            'see_all_projects': False,
            'see_financial': True,
            'see_holding_profit': False,
            'see_costs': False,
            'mutate_status': True,
            'register_payment': False,
            'export': True,
            'bulk': True,
            'technical_settings': False,
        }
    # hq_support and fallback
    return {
        'role': 'hq_support',
        'see_all_projects': True,
        'see_financial': False,
        'see_holding_profit': False,
        'see_costs': False,
        'mutate_status': False,
        'register_payment': False,
        'export': False,
        'bulk': False,
        'technical_settings': False,
    }


def _strip_sensitive(payload, caps):
    if caps.get('see_holding_profit') and caps.get('see_costs') and caps.get('see_financial'):
        return payload
    if isinstance(payload, list):
        return [_strip_sensitive(item, caps) for item in payload]
    if not isinstance(payload, dict):
        return payload
    data = dict(payload)
    if not caps.get('see_financial'):
        for key in (
            'base_amount', 'discount_amount', 'tax_amount', 'final_amount', 'paid_amount',
            'remaining_amount', 'sales_revenue', 'paid_revenue', 'renewal_revenue', 'tax_collected',
            'discount_total', 'receivables', 'overdue_total', 'carno_sales', 'carno_paid',
            'arakar_sales', 'arakar_paid', 'installment_remaining', 'sales', 'paid', 'remaining',
            'tax', 'revenue', 'cost_amount', 'cost_total', 'net_profit', 'default_cost',
        ):
            data.pop(key, None)
    return data


class SubscriptionsHqBaseView(APIView):
    permission_classes = [IsAuthenticated]

    def forbid(self, request):
        if _is_hq_user(request.user):
            return None
        return Response({'detail': 'دسترسی فقط برای کاربران پنل مرکزی است.'}, status=status.HTTP_403_FORBIDDEN)

    def caps(self, request):
        return _capabilities(request.user)


def _apply_subscription_filters(qs, request):
    params = request.query_params
    # Inactive carwashes are excluded from HQ service reports by default.
    include_inactive = str(params.get('include_inactive') or '').strip().lower() in {'1', 'true', 'yes'}
    if not include_inactive:
        qs = qs.filter(tenant__is_active=True)
    search = (params.get('search') or '').strip()
    if search:
        qs = qs.filter(
            Q(tenant__name__icontains=search)
            | Q(product__title__icontains=search)
            | Q(plan__title__icontains=search)
            | Q(license_code__icontains=search)
            | Q(contract_number__icontains=search)
        )
    if params.get('tenant_id'):
        qs = qs.filter(tenant_id=params.get('tenant_id'))
    if params.get('project_id'):
        qs = qs.filter(project_id=params.get('project_id'))
    if params.get('project_code'):
        qs = qs.filter(project__code=params.get('project_code'))
    if params.get('product_id'):
        qs = qs.filter(product_id=params.get('product_id'))
    if params.get('product_key'):
        qs = qs.filter(product__product_key=params.get('product_key'))
    if params.get('status'):
        statuses = [item.strip() for item in str(params.get('status')).split(',') if item.strip()]
        if statuses:
            qs = qs.filter(status__in=statuses)
    if params.get('payment_status'):
        qs = qs.filter(payment_status=params.get('payment_status'))
    if params.get('auto_renew') in {'true', 'false', '1', '0'}:
        qs = qs.filter(auto_renew=params.get('auto_renew') in {'true', '1'})
    if params.get('date_from'):
        qs = qs.filter(purchased_at__date__gte=params.get('date_from'))
    if params.get('date_to'):
        qs = qs.filter(purchased_at__date__lte=params.get('date_to'))
    if params.get('ends_from'):
        qs = qs.filter(ends_at__date__gte=params.get('ends_from'))
    if params.get('ends_to'):
        qs = qs.filter(ends_at__date__lte=params.get('ends_to'))
    if params.get('has_debt') in {'1', 'true'}:
        qs = qs.filter(remaining_amount__gt=0)
    if params.get('near_expiry') in {'1', 'true'}:
        now = timezone.now()
        qs = qs.filter(ends_at__gte=now, ends_at__lte=now + timezone.timedelta(days=15))
    ordering = params.get('ordering') or '-updated_at'
    allowed = {
        'updated_at', '-updated_at', 'purchased_at', '-purchased_at', 'ends_at', '-ends_at',
        'final_amount', '-final_amount', 'remaining_amount', '-remaining_amount',
        'client_name', '-client_name', 'status', '-status',
    }
    if ordering in {'client_name', '-client_name'}:
        ordering = ordering.replace('client_name', 'tenant__name')
    if ordering.lstrip('-') in {item.lstrip('-') for item in allowed} or ordering in allowed:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by('-updated_at')
    return qs


def _paginate(qs, request, serializer_class, caps):
    try:
        page = max(1, int(request.query_params.get('page') or 1))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(100, max(1, int(request.query_params.get('page_size') or 20)))
    except (TypeError, ValueError):
        page_size = 20
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)
    rows = serializer_class(page_obj.object_list, many=True).data
    return {
        'count': paginator.count,
        'page': page_obj.number,
        'page_size': page_size,
        'num_pages': paginator.num_pages,
        'results': _strip_sensitive(rows, caps),
    }


class CatalogListView(SubscriptionsHqBaseView):
    def get(self, request):
        forbidden = self.forbid(request)
        if forbidden:
            return forbidden
        seed_catalog_from_legacy()
        projects = PlatformProject.objects.filter(is_active=True).prefetch_related(
            Prefetch('products', queryset=ServiceProduct.objects.filter(is_available=True).prefetch_related('plans'))
        )
        products = ServiceProduct.objects.filter(is_available=True).select_related('project').prefetch_related('plans')
        return Response(
            {
                'projects': PlatformProjectSerializer(projects, many=True).data,
                'products': ServiceProductSerializer(products, many=True).data,
                'capabilities': self.caps(request),
            }
        )


class ServicesSummaryView(SubscriptionsHqBaseView):
    def get(self, request):
        forbidden = self.forbid(request)
        if forbidden:
            return forbidden
        qs = _apply_subscription_filters(
            ServiceSubscription.objects.select_related('tenant', 'project', 'product', 'plan'),
            request,
        )
        summary = summarize_subscriptions(qs)
        return Response(_strip_sensitive(summary, self.caps(request)))


class SubscriptionListView(SubscriptionsHqBaseView):
    def get(self, request):
        forbidden = self.forbid(request)
        if forbidden:
            return forbidden
        qs = _apply_subscription_filters(
            ServiceSubscription.objects.select_related(
                'tenant', 'project', 'product', 'plan', 'sales_owner', 'support_owner'
            ),
            request,
        )
        return Response(_paginate(qs, request, ServiceSubscriptionSerializer, self.caps(request)))


class SubscriptionDetailView(SubscriptionsHqBaseView):
    def get(self, request, pk):
        forbidden = self.forbid(request)
        if forbidden:
            return forbidden
        sub = (
            ServiceSubscription.objects.select_related(
                'tenant', 'project', 'product', 'plan', 'sales_owner', 'support_owner', 'feature_purchase'
            )
            .prefetch_related('periods', 'payments', 'audit_logs', 'alerts', 'orders')
            .filter(pk=pk)
            .first()
        )
        if not sub:
            return Response({'detail': 'یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
        caps = self.caps(request)
        payload = {
            'subscription': _strip_sensitive(ServiceSubscriptionSerializer(sub).data, caps),
            'periods': ServicePeriodSerializer(sub.periods.all()[:50], many=True).data,
            'payments': ServicePaymentRecordSerializer(sub.payments.all()[:50], many=True).data,
            'orders': ServiceOrderSerializer(sub.orders.all()[:50], many=True).data,
            'audit_logs': ServiceAuditLogSerializer(sub.audit_logs.all()[:100], many=True).data,
            'alerts': ServiceAlertSerializer(sub.alerts.filter(is_resolved=False)[:20], many=True).data,
        }
        if not caps.get('see_financial'):
            payload['payments'] = []
            payload['orders'] = []
        return Response(payload)


class SubscriptionActionView(SubscriptionsHqBaseView):
    WRITE_ACTIONS = {
        'activate', 'deactivate', 'suspend', 'unsuspend', 'block', 'cancel', 'restore',
        'extend_days', 'change_plan', 'set_usage_cap', 'apply_discount', 'forgive_debt',
        'adjust_amount', 'register_payment', 'free_activate', 'renew',
    }

    def post(self, request, pk):
        forbidden = self.forbid(request)
        if forbidden:
            return forbidden
        caps = self.caps(request)
        action = str(request.data.get('action') or '').strip()
        if action not in self.WRITE_ACTIONS:
            return Response({'action': ['عملیات نامعتبر است.']}, status=status.HTTP_400_BAD_REQUEST)
        financial_actions = {'apply_discount', 'forgive_debt', 'adjust_amount', 'register_payment', 'free_activate'}
        if action in financial_actions and not caps.get('register_payment') and not caps.get('see_holding_profit'):
            return Response({'detail': 'دسترسی مالی ندارید.'}, status=status.HTTP_403_FORBIDDEN)
        if action not in financial_actions and action != 'renew' and not caps.get('mutate_status'):
            return Response({'detail': 'اجازه تغییر وضعیت ندارید.'}, status=status.HTTP_403_FORBIDDEN)
        if action == 'renew' and not (caps.get('mutate_status') or caps.get('register_payment')):
            return Response({'detail': 'اجازه تمدید ندارید.'}, status=status.HTTP_403_FORBIDDEN)

        sub = ServiceSubscription.objects.select_related('product', 'plan', 'tenant').filter(pk=pk).first()
        if not sub:
            return Response({'detail': 'یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
        reason = str(request.data.get('reason') or '').strip()
        note = str(request.data.get('note') or '').strip()
        if action in {'deactivate', 'suspend', 'block', 'cancel', 'forgive_debt', 'adjust_amount', 'free_activate'} and not reason:
            return Response({'reason': ['ثبت دلیل برای این عملیات الزامی است.']}, status=status.HTTP_400_BAD_REQUEST)
        try:
            if action == 'renew':
                plan_id = request.data.get('plan_id')
                plan = ServicePlan.objects.filter(pk=plan_id, product=sub.product).first() if plan_id else sub.plan
                payment_method = request.data.get('payment_method') or ServiceOrder.PaymentMethod.MANUAL_HQ
                order = renew_subscription(
                    sub,
                    actor=request.user,
                    plan=plan,
                    payment_method=payment_method,
                    idempotency_key=str(request.data.get('idempotency_key') or ''),
                )
                return Response({'detail': 'تمدید انجام شد.', 'order': ServiceOrderSerializer(order).data if hasattr(order, 'order_code') else None})
            updated = apply_hq_action(
                sub,
                action=action,
                actor=request.user,
                reason=reason,
                note=note,
                payload=request.data.get('payload') or request.data,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'detail': 'عملیات با موفقیت انجام شد.',
            'subscription': _strip_sensitive(ServiceSubscriptionSerializer(updated).data, caps),
        })


class ClientServicesView(SubscriptionsHqBaseView):
    def get(self, request, tenant_id):
        forbidden = self.forbid(request)
        if forbidden:
            return forbidden
        tenant = CarWash.objects.filter(pk=tenant_id, is_active=True).first()
        if not tenant:
            return Response({'detail': 'کلاینت فعال یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
        seed_catalog_from_legacy()
        caps = self.caps(request)
        subs = (
            ServiceSubscription.objects.filter(tenant=tenant)
            .select_related('product', 'plan', 'project')
            .order_by('product__sort_order')
        )
        products = ServiceProduct.objects.filter(project__code='carnowash', is_available=True).prefetch_related('plans')
        owned_keys = {sub.product_id for sub in subs}
        missing = [
            ServiceProductSerializer(product).data
            for product in products
            if product.id not in owned_keys
        ]
        return Response(
            {
                'tenant': {'id': tenant.id, 'name': tenant.name, 'slug': tenant.slug, 'is_active': tenant.is_active},
                'subscriptions': _strip_sensitive(ServiceSubscriptionSerializer(subs, many=True).data, caps),
                'not_purchased': missing,
                'summary': _strip_sensitive(summarize_subscriptions(subs), caps),
            }
        )


class ManualOrderCreateView(SubscriptionsHqBaseView):
    def post(self, request):
        forbidden = self.forbid(request)
        if forbidden:
            return forbidden
        caps = self.caps(request)
        if not caps.get('mutate_status') and not caps.get('register_payment'):
            return Response({'detail': 'دسترسی ایجاد سفارش ندارید.'}, status=status.HTTP_403_FORBIDDEN)
        tenant = CarWash.objects.filter(pk=request.data.get('tenant_id')).first()
        product = ServiceProduct.objects.filter(pk=request.data.get('product_id')).select_related('project').first()
        plan = ServicePlan.objects.filter(pk=request.data.get('plan_id'), product=product).first() if product else None
        if not tenant or not product or not plan:
            return Response({'detail': 'کلاینت، سرویس یا پلن معتبر نیست.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            order = create_order_and_activate(
                tenant=tenant,
                product=product,
                plan=plan,
                actor=request.user,
                payment_method=request.data.get('payment_method') or ServiceOrder.PaymentMethod.MANUAL_HQ,
                discount_amount=request.data.get('discount_amount') or 0,
                idempotency_key=str(request.data.get('idempotency_key') or ''),
                require_manual_approval=bool(request.data.get('require_manual_approval')),
                auto_activate=bool(request.data.get('auto_activate', True)),
                note=str(request.data.get('note') or ''),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ServiceOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class BulkJobCreateView(SubscriptionsHqBaseView):
    def post(self, request):
        forbidden = self.forbid(request)
        if forbidden:
            return forbidden
        if not self.caps(request).get('bulk'):
            return Response({'detail': 'دسترسی عملیات گروهی ندارید.'}, status=status.HTTP_403_FORBIDDEN)
        action = str(request.data.get('action') or '').strip()
        subscription_ids = request.data.get('subscription_ids') or []
        if action not in BulkServiceJob.Action.values:
            return Response({'action': ['عملیات گروهی نامعتبر است.']}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(subscription_ids, list) or not subscription_ids:
            return Response({'subscription_ids': ['حداقل یک اشتراک لازم است.']}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            job = BulkServiceJob.objects.create(
                action=action,
                payload=request.data.get('payload') or {},
                created_by=request.user,
            )
            subs = ServiceSubscription.objects.filter(id__in=subscription_ids).select_related('tenant')
            BulkServiceJobItem.objects.bulk_create([
                BulkServiceJobItem(job=job, subscription=sub, tenant=sub.tenant)
                for sub in subs
            ])
            process_bulk_job(job.id)
            job.refresh_from_db()
        return Response(BulkServiceJobSerializer(job).data, status=status.HTTP_201_CREATED)


class AlertsListView(SubscriptionsHqBaseView):
    def get(self, request):
        forbidden = self.forbid(request)
        if forbidden:
            return forbidden
        qs = ServiceAlert.objects.select_related('tenant', 'subscription', 'subscription__product').filter(
            is_resolved=False,
            tenant__is_active=True,
        )
        if request.query_params.get('tenant_id'):
            qs = qs.filter(tenant_id=request.query_params.get('tenant_id'))
        if request.query_params.get('severity'):
            qs = qs.filter(severity=request.query_params.get('severity'))
        return Response(_paginate(qs.order_by('-created_at'), request, ServiceAlertSerializer, self.caps(request)))

    def post(self, request):
        forbidden = self.forbid(request)
        if forbidden:
            return forbidden
        alert_ids = request.data.get('alert_ids') or []
        ServiceAlert.objects.filter(id__in=alert_ids).update(is_resolved=True, resolved_at=timezone.now())
        return Response({'detail': 'هشدارها حل شدند.'})


class SpecializedReportView(SubscriptionsHqBaseView):
    PRODUCT_ALIASES = {
        'license': ServiceProduct.ProductKey.CORE_SOFTWARE,
        'wallet': ServiceProduct.ProductKey.WALLET,
        'attendance': ServiceProduct.ProductKey.ATTENDANCE,
        'cloud': ServiceProduct.ProductKey.CLOUD_STORAGE,
        'sms_club': ServiceProduct.ProductKey.SMS_CLUB,
        'sms': ServiceProduct.ProductKey.SMS_PANEL,
        'sms_credit': ServiceProduct.ProductKey.SMS_CREDIT,
    }

    def get(self, request, report_key):
        forbidden = self.forbid(request)
        if forbidden:
            return forbidden
        product_key = self.PRODUCT_ALIASES.get(report_key, report_key)
        qs = _apply_subscription_filters(
            ServiceSubscription.objects.filter(product__product_key=product_key).select_related(
                'tenant', 'project', 'product', 'plan'
            ),
            request,
        )
        caps = self.caps(request)
        summary = summarize_subscriptions(qs)
        page = _paginate(qs, request, ServiceSubscriptionSerializer, caps)
        return Response({'report_key': report_key, 'product_key': product_key, 'summary': _strip_sensitive(summary, caps), **page})


class RevenueMatrixView(SubscriptionsHqBaseView):
    def get(self, request):
        forbidden = self.forbid(request)
        if forbidden:
            return forbidden
        caps = self.caps(request)
        if not caps.get('see_financial'):
            return Response({'detail': 'دسترسی مالی ندارید.'}, status=status.HTTP_403_FORBIDDEN)
        qs = _apply_subscription_filters(ServiceSubscription.objects.select_related('product', 'project'), request)
        by_product = (
            qs.values('product__product_key', 'product__title')
            .annotate(
                count=Count('id'),
                sales=Sum('final_amount'),
                paid=Sum('paid_amount'),
                remaining=Sum('remaining_amount'),
                tax=Sum('tax_amount'),
            )
            .order_by('product__title')
        )
        by_project = (
            qs.values('project__code', 'project__name')
            .annotate(
                sales=Sum('final_amount'),
                paid=Sum('paid_amount'),
                remaining=Sum('remaining_amount'),
            )
            .order_by('project__name')
        )
        rows = []
        for row in by_product:
            sales = Decimal(str(row['sales'] or 0))
            paid = Decimal(str(row['paid'] or 0))
            remaining = Decimal(str(row['remaining'] or 0))
            share = product_share_group(row['product__product_key'])
            item = {
                'product_key': row['product__product_key'],
                'product_title': row['product__title'],
                'share_owner': share,
                'share_owner_label': 'کارنو' if share == 'carno' else ('آراکار' if share == 'arakar' else '—'),
                'subscriptions_count': row['count'] or 0,
                'sales': float(sales),
                'paid': float(paid),
                'remaining': float(remaining),
                'tax': float(Decimal(str(row['tax'] or 0))),
                'revenue': float(paid),
            }
            rows.append(_strip_sensitive(item, caps))
        projects = [_strip_sensitive({
            'project_code': row['project__code'],
            'project_name': row['project__name'],
            'sales': float(Decimal(str(row['sales'] or 0))),
            'paid': float(Decimal(str(row['paid'] or 0))),
            'remaining': float(Decimal(str(row['remaining'] or 0))),
        }, caps) for row in by_project]
        return Response({
            'summary': _strip_sensitive(summarize_subscriptions(qs), caps),
            'by_product': rows,
            'by_project': projects,
        })


class ExportSubscriptionsView(SubscriptionsHqBaseView):
    def get(self, request):
        forbidden = self.forbid(request)
        if forbidden:
            return forbidden
        if not self.caps(request).get('export'):
            return Response({'detail': 'دسترسی خروجی ندارید.'}, status=status.HTTP_403_FORBIDDEN)
        qs = _apply_subscription_filters(
            ServiceSubscription.objects.select_related('tenant', 'project', 'product', 'plan'),
            request,
        )[:5000]
        caps = self.caps(request)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        headers = [
            'client', 'project', 'product', 'plan', 'status', 'payment_status',
            'purchased_at', 'activated_at', 'starts_at', 'ends_at', 'days_remaining',
            'base_amount', 'discount_amount', 'tax_amount', 'final_amount', 'paid_amount',
            'remaining_amount', 'usage_used', 'usage_cap',
        ]
        if caps.get('see_costs'):
            headers.append('cost_amount')
        writer.writerow(headers)
        for sub in qs:
            row = [
                sub.tenant.name,
                sub.project.name,
                sub.product.title,
                sub.plan.title if sub.plan else '',
                sub.status,
                sub.payment_status,
                sub.purchased_at.isoformat() if sub.purchased_at else '',
                sub.activated_at.isoformat() if sub.activated_at else '',
                sub.starts_at.isoformat() if sub.starts_at else '',
                sub.ends_at.isoformat() if sub.ends_at else '',
                sub.days_remaining if sub.days_remaining is not None else '',
                sub.base_amount,
                sub.discount_amount,
                sub.tax_amount,
                sub.final_amount,
                sub.paid_amount,
                sub.remaining_amount,
                sub.usage_used,
                sub.usage_cap,
            ]
            if caps.get('see_costs'):
                row.append(sub.cost_amount)
            writer.writerow(row)
        response = HttpResponse('\ufeff' + buffer.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="services-report.csv"'
        return response


class SeedCatalogView(SubscriptionsHqBaseView):
    def post(self, request):
        forbidden = self.forbid(request)
        if forbidden:
            return forbidden
        if not _is_hq_admin(request.user):
            return Response({'detail': 'فقط مدیرکل.'}, status=status.HTTP_403_FORBIDDEN)
        seed_catalog_from_legacy()
        created = backfill_subscriptions_from_feature_purchases()
        return Response({'detail': 'کاتالوگ و اشتراک‌ها همگام شد.', 'backfilled': created})


class TenantCatalogView(APIView):
    """Tenant-facing catalog for data-driven purchase UI."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = getattr(request.user, 'tenant', None)
        if not tenant:
            return Response({'detail': 'کارواش کاربر مشخص نیست.'}, status=status.HTTP_400_BAD_REQUEST)
        seed_catalog_from_legacy()
        products = (
            ServiceProduct.objects.filter(project__code='carnowash', is_available=True)
            .prefetch_related('plans')
            .order_by('sort_order')
        )
        subs = {
            sub.product_id: sub
            for sub in ServiceSubscription.objects.filter(tenant=tenant).select_related('plan')
        }
        payload = []
        for product in products:
            sub = subs.get(product.id)
            payload.append({
                'product': ServiceProductSerializer(product).data,
                'subscription': ServiceSubscriptionSerializer(sub).data if sub else None,
            })
        return Response({'items': payload})
