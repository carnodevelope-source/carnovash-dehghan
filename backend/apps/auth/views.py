from datetime import datetime, time, timedelta
from collections import defaultdict
import re
from decimal import Decimal

from django.contrib.auth import get_user_model, login, logout
from django.db import transaction
from django.db.models import Count, OuterRef, Prefetch, Q, Subquery
from django.utils import timezone
from django.utils.text import slugify
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.models import ExpenseEntry, StockMovement
from apps.notifications.models import NotificationLog
from apps.notifications.services import normalize_phone, send_provider_sms
from apps.payments.models import CashflowTransaction, Payment, Wallet, WalletGatewayRequest
from apps.payments.views import activate_core_software_installment
from apps.reports.views import ReportsDashboardView
from apps.vehicles.models import VehicleEntry
from apps.workers.models import WorkerAttendance, WorkerProfile
from .feature_access import ATTENDANCE_FREE_WORKERS_LIMIT, feature_access_map_for_tenant, tenant_worker_count
from .models import CarWash, CarWashFeaturePurchase, PendingTenantRegistration, SupportTicket, SupportTicketAttachment, SupportTicketMessage, User
from .sms import (
    send_registration_credentials_sms as send_system_registration_credentials_sms,
    send_user_credentials_sms as send_system_user_credentials_sms,
)
from .support_tickets import (
    apply_hq_ticket_visibility,
    calculate_wallet_card_deposit_amounts as _calculate_wallet_card_deposit_amounts,
    build_registration_ticket_body,
    build_registration_ticket_subject,
    build_registration_approval_ticket_note,
    claim_ticket_if_unassigned,
    close_stale_support_tickets,
    is_payment_support_ticket,
    is_wallet_bank_withdrawal_ticket as _is_wallet_bank_withdrawal_ticket,
    is_wallet_card_payment_ticket as _is_wallet_card_payment_ticket,
    parse_wallet_amount_from_ticket as _parse_wallet_amount_from_ticket,
    parse_wallet_id_from_ticket as _parse_wallet_id_from_ticket,
    refer_ticket_to_user,
    send_payment_ticket_sms_to_simple_supporters,
    send_registration_ticket_sms_to_hq,
    WALLET_CARD_DEPOSIT_TAX_PERCENT,
)
from .serializers import (
    CarWashCreateSerializer,
    CarWashListSerializer,
    CarWashUpdateSerializer,
    HqSupportUserListSerializer,
    HqSupportUserCreateSerializer,
    LoginSerializer,
    HqSupportUserUpdateSerializer,
    SupportTicketCreateSerializer,
    SupportTicketDetailSerializer,
    SupportTicketFeedbackSerializer,
    HqTicketWalletTransferSerializer,
    SupportTicketListSerializer,
    SupportTicketMessageSerializer,
    SupportTicketReplySerializer,
    TenantRegisterSerializer,
    UserCreateSerializer,
    UserListSerializer,
    feature_access_map,
)


KARNO_FEATURE_KEYS = {
    CarWashFeaturePurchase.FeatureKey.SMS_CLUB,
    CarWashFeaturePurchase.FeatureKey.EXCEL_IMPORT,
    CarWashFeaturePurchase.FeatureKey.ATTENDANCE,
}

ARAKAR_FEATURE_KEYS = {
    CarWashFeaturePurchase.FeatureKey.CORE_SOFTWARE,
    CarWashFeaturePurchase.FeatureKey.CLOUD_STORAGE,
}

HQ_FEATURE_META = {
    CarWashFeaturePurchase.FeatureKey.SMS_CLUB: {
        'label': 'پنل باشگاه مشتریان پیشرفته',
        'tab_label': 'باشگاه پیشرفته',
        'description': 'درآمد باشگاه مشتریان؛ سهم کارنو.',
    },
    CarWashFeaturePurchase.FeatureKey.EXCEL_IMPORT: {
        'label': 'وارد کردن مشتریان با اکسل',
        'tab_label': 'ورود اکسل',
        'description': 'ورود گروهی مشتریان با اکسل؛ سهم کارنو.',
    },
    CarWashFeaturePurchase.FeatureKey.ATTENDANCE: {
        'label': 'ورود و خروج',
        'tab_label': 'حضور و غیاب',
        'description': 'قابلیت ورود و خروج پرسنل؛ سهم کارنو.',
    },
    CarWashFeaturePurchase.FeatureKey.CORE_SOFTWARE: {
        'label': 'لایسنس اصلی نرم‌افزار',
        'tab_label': 'لایسنس اصلی',
        'description': 'لایسنس اصلی نرم‌افزار؛ سهم آراکار.',
    },
    CarWashFeaturePurchase.FeatureKey.CLOUD_STORAGE: {
        'label': 'فضای ابری',
        'tab_label': 'فضای ابری',
        'description': 'فضای ابری نگهداری داده؛ سهم آراکار.',
    },
}

HQ_FEATURE_KEYS = KARNO_FEATURE_KEYS

FEATURE_PURCHASE_REFERENCE_TYPES = {
    'feature_option_purchase',
    'feature_option_installment',
    'feature_option_installment_manual',
}

KARNO_WALLET_REFERENCE_TYPES = {
    'customer_import_excel',
    'sms_campaign_send',
    'vehicle_assigned_sms',
    'vehicle_released_sms',
    'system_sms',
}


def _feature_share_group(feature_key):
    if feature_key in KARNO_FEATURE_KEYS:
        return 'hq'
    if feature_key in ARAKAR_FEATURE_KEYS:
        return 'rah'
    return 'none'


def _wallet_transaction_share_group(tx):
    wallet_type = tx.wallet.wallet_type if tx.wallet_id else ''
    if tx.direction == CashflowTransaction.Direction.IN:
        return 'none'
    if wallet_type == Wallet.WalletType.SMS or tx.reference_type in KARNO_WALLET_REFERENCE_TYPES:
        return 'hq'
    if tx.reference_type in FEATURE_PURCHASE_REFERENCE_TYPES and tx.reference_id:
        purchase = CarWashFeaturePurchase.objects.filter(pk=tx.reference_id).only('feature_key').first()
        if purchase:
            return _feature_share_group(purchase.feature_key)
    return 'rah'


def _wallet_transaction_share_amount(tx):
    return Decimal(str(tx.amount or 0)) if _wallet_transaction_share_group(tx) in {'hq', 'rah'} else Decimal('0')


def _parse_dt(value, end_of_day=False):
    if not value:
        return None
    dt = datetime.strptime(value, '%Y-%m-%d')
    dt = datetime.combine(dt.date(), time.max if end_of_day else time.min)
    return timezone.make_aware(dt)


def _legacy_platform_role(user):
    if getattr(user, 'username', '') in {'karimi', 'dehestani'}:
        return User.PlatformRoles.HQ_ADMIN
    return User.PlatformRoles.NONE


def _platform_role(user):
    if not getattr(user, 'is_authenticated', False):
        return User.PlatformRoles.NONE
    return getattr(user, 'platform_role', None) or _legacy_platform_role(user)


def _is_hq_user(user):
    return _platform_role(user) in {
        User.PlatformRoles.HQ_ADMIN,
        User.PlatformRoles.HQ_SUPPORT,
        User.PlatformRoles.HQ_PROJECT_MANAGER,
        User.PlatformRoles.HQ_FINANCE,
    }


def _is_hq_admin(user):
    return _platform_role(user) == User.PlatformRoles.HQ_ADMIN


def _can_see_hq_reports(user):
    return _platform_role(user) in {
        User.PlatformRoles.HQ_ADMIN,
        User.PlatformRoles.HQ_FINANCE,
    }


def _default_hq_support_user():
    return (
        User.objects.filter(platform_role=User.PlatformRoles.HQ_SUPPORT, is_active=True, is_deleted=False)
        .order_by('-id')
        .first()
    )


def _parse_wallet_withdraw_amount_from_ticket(ticket):
    return _parse_wallet_amount_from_ticket(ticket)


def _auth_payload(user):
    has_tenant = getattr(user, 'tenant_id', None) is not None
    tenant = user.tenant if has_tenant else None
    feature_keys = set(tenant.active_feature_keys()) if has_tenant else set()
    attendance_worker_count = tenant_worker_count(tenant) if has_tenant else 0
    attendance_feature_purchased = 'attendance' in feature_keys
    trial_active = bool(tenant and tenant.is_trial_active())
    license_status = {}
    # One lookup feeds both the payload field and the menu access map below,
    # which each used to run it separately.
    tenant_locked_features = {}
    if has_tenant:
        from apps.payments.views import license_status_for_tenant, locked_feature_statuses_for_tenant
        tenant_locked_features = locked_feature_statuses_for_tenant(tenant)
        if not _is_hq_user(user):
            license_status = license_status_for_tenant(tenant)
    locked_feature_statuses = {} if _is_hq_user(user) else tenant_locked_features
    return {
        'id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
        'platform_role': _platform_role(user),
        'phone': user.phone,
        'tenant_id': user.tenant_id,
        'tenant_name': tenant.name if has_tenant else '',
        'tenant_address': tenant.address if has_tenant else '',
        'purchased_menu_access': sorted(feature_keys),
        'menu_access': (
            feature_access_map_for_tenant(
                tenant,
                feature_keys=feature_keys,
                locked_features=set(tenant_locked_features.keys()),
            )
            if has_tenant
            else feature_access_map(feature_keys)
        ),
        'locked_feature_statuses': locked_feature_statuses,
        'locked_feature_keys': sorted(locked_feature_statuses.keys()),
        'attendance_free_workers_limit': ATTENDANCE_FREE_WORKERS_LIMIT,
        'attendance_worker_count': attendance_worker_count,
        'attendance_feature_purchased': attendance_feature_purchased,
        'attendance_upgrade_required': bool(
            getattr(user, 'tenant_id', None)
            and not trial_active
            and not attendance_feature_purchased
            and attendance_worker_count > ATTENDANCE_FREE_WORKERS_LIMIT
        ),
        'license_status': license_status,
        'is_hq': _is_hq_user(user),
        'is_hq_admin': _is_hq_admin(user),
    }


def _build_unique_carwash_slug(name, explicit_slug=''):
    base_slug = slugify(explicit_slug or name) or 'carwash'
    unique_slug = base_slug
    index = 1
    while CarWash.objects.filter(slug=unique_slug).exists():
        index += 1
        unique_slug = f'{base_slug}-{index}'
    return unique_slug


def _start_trial_access(tenant, started_at=None):
    if not tenant or tenant.trial_started_at or tenant.trial_ends_at:
        return
    started_at = started_at or timezone.now()
    tenant.trial_started_at = started_at
    tenant.trial_ends_at = started_at + timedelta(hours=24)
    tenant.save(update_fields=['trial_started_at', 'trial_ends_at', 'updated_at'])


def _send_registration_credentials_sms(*, carwash_name, phone, username, password):
    normalized_phone = normalize_phone(phone)
    if not normalized_phone:
        return {'attempted': False, 'ok': False, 'message': 'شماره موبایل مدیر معتبر نیست.'}

    text = (
        f'ثبت کارواش {carwash_name} انجام شد.\n'
        f'نام کاربری: {username}\n'
        f'رمز عبور: {password}\n'
        f'با تشکر از انتخاب خوب شما  -  کارنوواش'
    )
    result = send_provider_sms(None, text, [normalized_phone])
    return {
        'attempted': True,
        'ok': bool(result.get('ok')),
        'message': result.get('message', ''),
        'provider_status': result.get('provider_status', 0),
    }


def _role_sms_label(role):
    return {
        'manager': 'مدیر',
        'admin': 'ادمین',
        'operator': 'اپراتور',
        'accountant': 'حسابدار',
        'worker': 'نیرو',
        'hq_support': 'پشتیبان مرکزی',
    }.get(role, 'کاربر')


def _send_user_credentials_sms(*, tenant_name, phone, username, password, role):
    normalized_phone = normalize_phone(phone)
    if not normalized_phone:
        return {'attempted': False, 'ok': False, 'message': 'شماره موبایل کاربر معتبر نیست.'}

    text = (
        f'{_role_sms_label(role)} جدید برای {tenant_name} ثبت شد.\n'
        f'نام کاربری: {username}\n'
        f'رمز عبور: {password}\n'
        f'ورود از پنل کارنوواش'
    )
    result = send_provider_sms(None, text, [normalized_phone])
    return {
        'attempted': True,
        'ok': bool(result.get('ok')),
        'message': result.get('message', ''),
        'provider_status': result.get('provider_status', 0),
    }


def _create_sms_log(*, tenant, recipient, template_code, payload, result, created_by=None):
    NotificationLog.objects.create(
        tenant=tenant,
        channel=NotificationLog.Channel.SMS,
        recipient=recipient or '',
        template_code=template_code,
        payload=payload or {},
        status=NotificationLog.Status.SENT if result.get('ok') else NotificationLog.Status.FAILED,
        sent_at=timezone.now() if result.get('ok') else None,
        provider_message_id=str(result.get('provider_id') or ''),
        provider_response=str(result.get('message') or ''),
        created_by=created_by if getattr(created_by, 'is_authenticated', False) else None,
    )


def _send_logged_user_credentials_sms(*, tenant, tenant_name, phone, username, password, role, created_by=None, template_code='user_credentials'):
    result = _send_user_credentials_sms(
        tenant_name=tenant_name,
        phone=phone,
        username=username,
        password=password,
        role=role,
    )
    _create_sms_log(
        tenant=tenant,
        recipient=normalize_phone(phone) or phone,
        template_code=template_code,
        payload={'username': username, 'role': role, 'tenant_name': tenant_name},
        result=result,
        created_by=created_by,
    )
    return result


def _sync_tenant_feature_purchases(tenant, feature_keys):
    if not tenant:
        return
    normalized_keys = {
        str(item).strip()
        for item in (feature_keys or [])
        if str(item).strip() in CarWashFeaturePurchase.FeatureKey.values
    }
    existing = {
        purchase.feature_key: purchase
        for purchase in tenant.feature_purchases.all()
    }
    for feature_key in CarWashFeaturePurchase.FeatureKey.values:
        purchase = existing.get(feature_key)
        should_be_active = feature_key in normalized_keys
        if purchase:
            if purchase.is_active != should_be_active:
                purchase.is_active = should_be_active
                purchase.save(update_fields=['is_active', 'updated_at'])
        elif should_be_active:
            CarWashFeaturePurchase.objects.create(
                tenant=tenant,
                feature_key=feature_key,
                is_active=True,
            )


def _response_status_score(status_value):
    return {
        SupportTicket.Status.CLOSED: Decimal('5.0'),
        SupportTicket.Status.ANSWERED: Decimal('4.4'),
        SupportTicket.Status.PENDING: Decimal('3.6'),
        SupportTicket.Status.OPEN: Decimal('3.0'),
    }.get(status_value, Decimal('3.0'))


def _response_length_score(body):
    size = len(str(body or '').strip())
    if size >= 280:
        return Decimal('5.0')
    if size >= 160:
        return Decimal('4.6')
    if size >= 80:
        return Decimal('4.2')
    if size >= 40:
        return Decimal('3.7')
    return Decimal('2.8')


def _response_quality_score(ticket, body):
    status_score = _response_status_score(ticket.status)
    length_score = _response_length_score(body)
    return ((status_score * Decimal('0.65')) + (length_score * Decimal('0.35'))).quantize(Decimal('0.01'))


def _response_speed_score(first_response_minutes):
    minutes = float(first_response_minutes or 0)
    if minutes <= 10:
        return Decimal('5.0')
    if minutes <= 30:
        return Decimal('4.7')
    if minutes <= 60:
        return Decimal('4.2')
    if minutes <= 180:
        return Decimal('3.6')
    if minutes <= 720:
        return Decimal('3.0')
    if minutes <= 1440:
        return Decimal('2.4')
    return Decimal('1.8')


def _average_decimal(values):
    if not values:
        return Decimal('0')
    total = sum((Decimal(str(value)) for value in values), Decimal('0'))
    return (total / Decimal(str(len(values)))).quantize(Decimal('0.01'))


def _recalculate_support_metrics(user):
    if not user or user.platform_role not in {User.PlatformRoles.HQ_ADMIN, User.PlatformRoles.HQ_SUPPORT}:
        return

    tickets = list(
        SupportTicket.objects.filter(assigned_to=user, responded_at__isnull=False).only(
            'id',
            'status',
            'created_at',
            'first_response_at',
            'response_quality_score',
            'customer_satisfaction',
        )
    )
    satisfaction_values = [ticket.customer_satisfaction for ticket in tickets if ticket.customer_satisfaction]
    quality_values = [ticket.response_quality_score for ticket in tickets if Decimal(str(ticket.response_quality_score or 0)) > 0]
    response_minutes = []
    response_speed_values = []
    resolved_count = 0

    for ticket in tickets:
        if ticket.status == SupportTicket.Status.CLOSED:
            resolved_count += 1
        if ticket.first_response_at and ticket.created_at:
            minutes = max((ticket.first_response_at - ticket.created_at).total_seconds() / 60, 0)
            response_minutes.append(Decimal(str(round(minutes, 2))))
            response_speed_values.append(_response_speed_score(minutes))

    satisfaction_avg = _average_decimal(satisfaction_values)
    quality_avg = _average_decimal(quality_values)
    first_response_minutes_avg = _average_decimal(response_minutes)
    speed_avg = _average_decimal(response_speed_values)

    weighted_parts = []
    if satisfaction_values:
        weighted_parts.append((satisfaction_avg, Decimal('0.55')))
    if quality_values:
        weighted_parts.append((quality_avg, Decimal('0.30')))
    if response_speed_values:
        weighted_parts.append((speed_avg, Decimal('0.15')))

    if weighted_parts:
        total_weight = sum((weight for _, weight in weighted_parts), Decimal('0'))
        star_rating = (sum((value * weight for value, weight in weighted_parts), Decimal('0')) / total_weight).quantize(Decimal('0.01'))
    else:
        star_rating = Decimal('0')

    user.support_star_rating = star_rating
    user.support_rating_count = len(satisfaction_values)
    user.support_customer_satisfaction_avg = satisfaction_avg
    user.support_response_quality_avg = quality_avg
    user.support_first_response_minutes_avg = first_response_minutes_avg
    user.support_total_responses = len(tickets)
    user.support_resolved_tickets_count = resolved_count
    user.support_last_scored_at = timezone.now()
    user.save(
        update_fields=[
            'support_star_rating',
            'support_rating_count',
            'support_customer_satisfaction_avg',
            'support_response_quality_avg',
            'support_first_response_minutes_avg',
            'support_total_responses',
            'support_resolved_tickets_count',
            'support_last_scored_at',
        ]
    )


def _tenant_ticket_queryset():
    visible_messages = SupportTicketMessage.objects.filter(is_internal=False).select_related('sender').order_by('created_at', 'id')
    return (
        SupportTicket.objects.select_related('tenant', 'created_by', 'assigned_to', 'responded_by', 'registration_request__manager')
        .prefetch_related(Prefetch('messages', queryset=visible_messages), 'attachments')
    )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'login'

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return Response(_auth_payload(user), status=status.HTTP_200_OK)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'detail': 'خروج با موفقیت انجام شد.'}, status=status.HTTP_200_OK)


class MeView(APIView):
    def get(self, request):
        return Response(_auth_payload(request.user), status=status.HTTP_200_OK)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'csrf'

    def get(self, request):
        return Response({'detail': 'CSRF cookie set.'}, status=status.HTTP_200_OK)


class UserManagementView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'role', '') not in ['admin', 'manager']:
            return Response({'detail': 'شما دسترسی لازم را ندارید.'}, status=status.HTTP_403_FORBIDDEN)
        users = get_user_model().objects.filter(tenant=request.user.tenant).order_by('-id')
        return Response(UserListSerializer(users, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        if getattr(request.user, 'role', '') not in ['admin', 'manager']:
            return Response({'detail': 'شما دسترسی لازم را ندارید.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = UserCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        raw_password = getattr(user, '_raw_password', '')
        if raw_password and getattr(user, 'phone', ''):
            send_system_user_credentials_sms(
                tenant=getattr(request.user, 'tenant', None),
                tenant_name=request.user.tenant.name if getattr(request.user, 'tenant_id', None) else 'کارواش',
                phone=user.phone,
                username=user.username,
                password=raw_password,
                role=user.role,
                created_by=request.user,
            )
        return Response(UserListSerializer(user).data, status=status.HTTP_201_CREATED)


class TenantRegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'tenant_register'

    @transaction.atomic
    def post(self, request):
        serializer = TenantRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_model = get_user_model()
        if user_model.objects.filter(username=data['manager_username']).exists():
            return Response({'manager_username': ['این نام کاربری قبلا ثبت شده است.']}, status=status.HTTP_400_BAD_REQUEST)

        if user_model.objects.filter(phone=data['manager_phone']).exists():
            return Response({'manager_phone': ['این شماره موبایل قبلا ثبت شده است.']}, status=status.HTTP_400_BAD_REQUEST)

        requested_slug = str(data.get('carwash_slug', '') or '').strip()
        if requested_slug and CarWash.objects.filter(slug=requested_slug).exists():
            return Response({'carwash_slug': ['این شناسه قبلا ثبت شده است.']}, status=status.HTTP_400_BAD_REQUEST)

        documents = request.FILES.getlist('business_identity_documents')

        tenant = CarWash.objects.create(
            name=data['carwash_name'],
            slug=requested_slug or _build_unique_carwash_slug(data['carwash_name']),
            address=(data.get('carwash_address') or '').strip(),
            is_active=False,
        )
        manager = user_model.objects.create(
            username=data['manager_username'],
            first_name=data.get('manager_first_name', ''),
            last_name=data.get('manager_last_name', ''),
            full_name=data['manager_full_name'],
            phone=data['manager_phone'],
            tenant=tenant,
            role='manager',
            is_active=False,
            is_staff=True,
            is_superuser=False,
        )
        manager.set_password(data['manager_password'])
        manager.save(update_fields=['password'])
        assignee = None
        document_names = [str(getattr(uploaded_file, 'name', '') or '').strip() for uploaded_file in documents]
        document_names = [name for name in document_names if name]
        registration_ticket_body = build_registration_ticket_body(
            tenant=tenant,
            manager=manager,
            documents_count=len(documents),
            document_names=document_names,
        )
        ticket = SupportTicket.objects.create(
            tenant=tenant,
            created_by=manager,
            subject=build_registration_ticket_subject(tenant.name),
            message=registration_ticket_body,
            category=SupportTicket.Category.ACCOUNT,
            priority=SupportTicket.Priority.HIGH,
            status=SupportTicket.Status.OPEN,
            assigned_to=assignee,
            last_message_at=timezone.now(),
            is_registration_request=True,
        )
        SupportTicketMessage.objects.create(
            ticket=ticket,
            sender=manager,
            body=registration_ticket_body,
        )
        for uploaded_file in documents:
            SupportTicketAttachment.objects.create(
                ticket=ticket,
                uploaded_by=manager,
                file=uploaded_file,
                original_name=getattr(uploaded_file, 'name', '')[:255],
            )
        PendingTenantRegistration.objects.create(
            tenant=tenant,
            manager=manager,
            support_ticket=ticket,
            status=PendingTenantRegistration.Status.PENDING,
            temp_password=data['manager_password'],
        )

        try:
            send_registration_ticket_sms_to_hq(ticket)
        except Exception as exc:
            print(f'registration ticket sms failed: {exc}')

        return Response(
            {
                'tenant': {'id': tenant.id, 'name': tenant.name, 'slug': tenant.slug, 'address': tenant.address, 'is_active': tenant.is_active},
                'manager': {
                    'id': manager.id,
                    'username': manager.username,
                    'full_name': manager.full_name,
                    'first_name': manager.first_name,
                    'last_name': manager.last_name,
                    'phone': manager.phone,
                    'role': manager.role,
                    'is_active': manager.is_active,
                },
                'registration': {
                    'status': PendingTenantRegistration.Status.PENDING,
                    'ticket_id': ticket.id,
                    'documents_count': len(documents),
                    'message': (
                        'درخواست ثبت‌نام شما همراه با مدارک برای پشتیبانی ارسال شد. بعد از تایید، پیامک فعال‌سازی ارسال می‌شود و لاگین شما باز خواهد شد.'
                        if documents
                        else 'درخواست ثبت‌نام شما برای پشتیبانی ارسال شد. بعد از تایید، پیامک فعال‌سازی ارسال می‌شود و لاگین شما باز خواهد شد.'
                    ),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class SupportTicketListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request.user, 'tenant', None)
        if not tenant:
            return Response([], status=status.HTTP_200_OK)
        close_stale_support_tickets()
        last_body = (
            SupportTicketMessage.objects.filter(ticket_id=OuterRef('pk'), is_internal=False)
            .order_by('-created_at', '-id')
            .values('body')[:1]
        )
        tickets = (
            SupportTicket.objects.select_related(
                'tenant', 'created_by', 'assigned_to', 'responded_by', 'registration_request__manager'
            )
            .filter(tenant=tenant)
            .annotate(messages_count=Count('messages', distinct=True), last_message_body=Subquery(last_body))
            .order_by('-last_message_at', '-created_at')
        )
        return Response(SupportTicketListSerializer(tickets, many=True).data, status=status.HTTP_200_OK)

    @transaction.atomic
    def post(self, request):
        tenant = getattr(request.user, 'tenant', None)
        if not tenant:
            return Response({'detail': 'کارواش کاربر مشخص نیست.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SupportTicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        ticket = SupportTicket.objects.create(
            tenant=tenant,
            created_by=request.user,
            subject=data['subject'],
            message=data['message'],
            category=data.get('category') or SupportTicket.Category.OTHER,
            priority=data.get('priority') or SupportTicket.Priority.MEDIUM,
            status=SupportTicket.Status.OPEN,
            assigned_to=None,
            last_message_at=timezone.now(),
        )
        SupportTicketMessage.objects.create(ticket=ticket, sender=request.user, body=data['message'])
        for uploaded_file in request.FILES.getlist('attachments'):
            SupportTicketAttachment.objects.create(
                ticket=ticket,
                uploaded_by=request.user,
                file=uploaded_file,
                original_name=getattr(uploaded_file, 'name', '')[:255],
            )
        if is_payment_support_ticket(ticket):
            send_payment_ticket_sms_to_simple_supporters(ticket)
        ticket = _tenant_ticket_queryset().filter(pk=ticket.pk).first()
        return Response(SupportTicketDetailSerializer(ticket, context={'request': request}).data, status=status.HTTP_201_CREATED)


class SupportTicketSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request.user, 'tenant', None)
        if not tenant:
            return Response({'open_count': 0}, status=status.HTTP_200_OK)
        close_stale_support_tickets()
        open_count = (
            SupportTicket.objects.filter(tenant=tenant)
            .exclude(status=SupportTicket.Status.CLOSED)
            .count()
        )
        return Response({'open_count': open_count}, status=status.HTTP_200_OK)


class SupportTicketDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        close_stale_support_tickets()
        ticket = _tenant_ticket_queryset().filter(pk=pk, tenant=request.user.tenant).first()
        if not ticket:
            return Response({'detail': 'تیکت یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(SupportTicketDetailSerializer(ticket, context={'request': request}).data, status=status.HTTP_200_OK)


class SupportTicketFeedbackView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        ticket = SupportTicket.objects.filter(pk=pk, tenant=request.user.tenant).select_related('assigned_to').first()
        if not ticket:
            return Response({'detail': 'تیکت یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
        if ticket.status not in {SupportTicket.Status.ANSWERED, SupportTicket.Status.CLOSED}:
            return Response({'detail': 'امتیازدهی فقط بعد از پاسخ پشتیبانی ممکن است.'}, status=status.HTTP_400_BAD_REQUEST)
        if not ticket.assigned_to_id:
            return Response({'detail': 'پشتیبان این تیکت مشخص نشده است.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SupportTicketFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ticket.customer_satisfaction = data['customer_satisfaction']
        ticket.customer_feedback = (data.get('customer_feedback') or '').strip()
        ticket.save(update_fields=['customer_satisfaction', 'customer_feedback', 'updated_at'])
        _recalculate_support_metrics(ticket.assigned_to)
        refreshed_ticket = _tenant_ticket_queryset().filter(pk=ticket.pk, tenant=request.user.tenant).first()
        return Response(SupportTicketDetailSerializer(refreshed_ticket, context={'request': request}).data, status=status.HTTP_200_OK)


class SupportTicketMessageCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        ticket = SupportTicket.objects.filter(pk=pk, tenant=request.user.tenant).first()
        if not ticket:
            return Response({'detail': 'تیکت یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = SupportTicketReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        message = SupportTicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            body=data['body'],
            is_internal=False,
        )
        ticket.status = SupportTicket.Status.OPEN
        ticket.last_message_at = message.created_at
        ticket.save(update_fields=['status', 'last_message_at', 'updated_at'])
        return Response(SupportTicketMessageSerializer(message).data, status=status.HTTP_201_CREATED)


class HqBaseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def forbid_if_not_hq(self, request):
        if _is_hq_user(request.user):
            return None
        return Response({'detail': 'دسترسی فقط برای کاربران پنل مرکزی است.'}, status=status.HTTP_403_FORBIDDEN)

    def forbid_if_not_hq_admin(self, request):
        if _is_hq_admin(request.user):
            return None
        return Response({'detail': 'دسترسی فقط برای مدیرکل مجاز است.'}, status=status.HTTP_403_FORBIDDEN)


def _hq_visible_carwashes():
    # Sample/demo tenants stay out of HQ lists & reports; tickets use a separate filter.
    from .sample_tenant import hq_reportable_carwashes_q

    return CarWash.objects.filter(hq_reportable_carwashes_q())


def _hq_ticket_queryset_q():
    from .sample_tenant import hq_ticket_queryset_q

    return hq_ticket_queryset_q()


def _hq_ticket_tenant_filter():
    from .sample_tenant import hq_ticket_tenants_q

    return hq_ticket_tenants_q()


class HqOverviewView(HqBaseView):
    def get(self, request):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        close_stale_support_tickets()
        open_statuses = [SupportTicket.Status.OPEN, SupportTicket.Status.PENDING, SupportTicket.Status.ANSWERED]
        visible_carwashes = _hq_visible_carwashes()
        ticket_q = _hq_ticket_queryset_q()
        summary = {
            'active_carwashes': visible_carwashes.filter(is_active=True).count(),
            'total_carwashes': visible_carwashes.count(),
            'open_tickets': SupportTicket.objects.filter(
                status__in=open_statuses,
            ).filter(ticket_q).count(),
            'urgent_tickets': SupportTicket.objects.filter(
                status__in=open_statuses,
                priority=SupportTicket.Priority.URGENT,
            ).filter(ticket_q).count(),
            'hq_support_users': User.objects.filter(platform_role=User.PlatformRoles.HQ_SUPPORT, is_active=True).count(),
            'today_vehicles': VehicleEntry.objects.filter(
                check_in_at__date=timezone.localdate(),
                tenant__in=visible_carwashes,
            ).count(),
        }

        recent_carwashes = visible_carwashes.order_by('-created_at')[:5]
        recent_tickets = apply_hq_ticket_visibility(
            SupportTicket.objects.select_related('tenant', 'created_by', 'assigned_to').filter(ticket_q),
            request.user,
        ).order_by('-last_message_at', '-created_at')[:6]
        return Response(
            {
                'summary': summary,
                'recent_carwashes': CarWashListSerializer(recent_carwashes, many=True).data,
                'recent_tickets': SupportTicketListSerializer(recent_tickets, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class HqCarWashListCreateView(HqBaseView):
    def get(self, request):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden
        rows = _hq_visible_carwashes().order_by('-id')
        return Response(CarWashListSerializer(rows, many=True).data, status=status.HTTP_200_OK)

    @transaction.atomic
    def post(self, request):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        serializer = CarWashCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_model = get_user_model()
        if user_model.objects.filter(username=data['manager_username']).exists():
            return Response({'manager_username': ['این نام کاربری قبلا ثبت شده است.']}, status=status.HTTP_400_BAD_REQUEST)
        if user_model.objects.filter(phone=data['manager_phone']).exists():
            return Response({'manager_phone': ['این شماره موبایل قبلا ثبت شده است.']}, status=status.HTTP_400_BAD_REQUEST)

        base_slug = slugify(data['carwash_name']) or 'carwash'
        unique_slug = base_slug
        index = 1
        while CarWash.objects.filter(slug=unique_slug).exists():
            index += 1
            unique_slug = f'{base_slug}-{index}'
        tenant = CarWash.objects.create(
            name=data['carwash_name'],
            slug=unique_slug,
            address=(data.get('carwash_address') or '').strip(),
            is_active=True,
        )
        _start_trial_access(tenant)
        _sync_tenant_feature_purchases(tenant, data.get('purchased_menu_access', []))
        first_name = data['manager_first_name'].strip()
        last_name = data['manager_last_name'].strip()
        manager = user_model.objects.create(
            username=data['manager_username'],
            first_name=first_name,
            last_name=last_name,
            full_name=f'{first_name} {last_name}'.strip(),
            phone=data['manager_phone'],
            tenant=tenant,
            role='manager',
            is_active=True,
            is_staff=True,
            is_superuser=False,
        )
        manager.set_password(data['manager_password'])
        manager.save(update_fields=['password'])
        return Response(CarWashListSerializer(tenant).data, status=status.HTTP_201_CREATED)


class HqCarWashUpdateView(HqBaseView):
    def patch(self, request, pk):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        tenant = CarWash.objects.filter(pk=pk).first()
        if not tenant:
            return Response({'detail': 'کارواش یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CarWashUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        changed_fields = []
        if 'carwash_name' in data:
            tenant.name = data['carwash_name']
            changed_fields.append('name')
        if 'carwash_address' in data:
            tenant.address = (data.get('carwash_address') or '').strip()
            changed_fields.append('address')
        was_active = tenant.is_active
        if 'is_active' in data:
            tenant.is_active = data['is_active']
            changed_fields.append('is_active')
        if 'exclude_from_hq_reports' in data:
            tenant.exclude_from_hq_reports = data['exclude_from_hq_reports']
            changed_fields.append('exclude_from_hq_reports')
        if changed_fields:
            changed_fields.append('updated_at')
            tenant.save(update_fields=changed_fields)
            if 'is_active' in data and not was_active and tenant.is_active:
                _start_trial_access(tenant)
        if 'purchased_menu_access' in data:
            _sync_tenant_feature_purchases(tenant, data.get('purchased_menu_access', []))

        manager = get_user_model().objects.filter(tenant=tenant, role='manager').order_by('id').first()
        if manager:
            first_name = data.get('manager_first_name', manager.first_name)
            last_name = data.get('manager_last_name', manager.last_name)
            manager.first_name = first_name
            manager.last_name = last_name
            manager.full_name = f'{first_name} {last_name}'.strip()
            if 'manager_phone' in data:
                manager.phone = data['manager_phone']
            if 'manager_password' in data:
                manager.set_password(data['manager_password'])
            manager.save()

        return Response(CarWashListSerializer(tenant).data, status=status.HTTP_200_OK)


def _money(value):
    return Decimal(str(value or 0))


def _feature_title(feature_key):
    return {
        CarWashFeaturePurchase.FeatureKey.ATTENDANCE: 'ورود و خروج',
        CarWashFeaturePurchase.FeatureKey.ACCOUNTING: 'حسابداری',
        CarWashFeaturePurchase.FeatureKey.CLOUD_STORAGE: 'فضای ابری',
    }.get(feature_key, feature_key)


class HqCarWashInsightView(HqBaseView):
    def get(self, request, pk):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        tenant = _hq_visible_carwashes().filter(pk=pk).first()
        if not tenant:
            return Response({'detail': 'کارواش یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        today = timezone.localdate()
        today_start = timezone.make_aware(datetime.combine(today, time.min))
        today_end = timezone.make_aware(datetime.combine(today, time.max))

        wallets = list(Wallet.objects.filter(tenant=tenant, is_active=True).order_by('wallet_type', 'id'))
        wallet_rows = []
        wallet_summary = {
            'total_balance': Decimal('0'),
            'regular_balance': Decimal('0'),
            'sms_balance': Decimal('0'),
            'today_deposit_total': Decimal('0'),
            'today_withdraw_total': Decimal('0'),
        }
        for wallet in wallets:
            balance = _money(wallet.balance)
            wallet_summary['total_balance'] += balance
            if wallet.wallet_type == Wallet.WalletType.SMS:
                wallet_summary['sms_balance'] += balance
            else:
                wallet_summary['regular_balance'] += balance
            wallet_rows.append(
                {
                    'id': wallet.id,
                    'name': wallet.name,
                    'wallet_type': wallet.wallet_type,
                    'balance': balance,
                    'is_active': wallet.is_active,
                }
            )

        today_wallet_transactions = CashflowTransaction.objects.filter(
            tenant=tenant,
            transacted_at__gte=today_start,
            transacted_at__lte=today_end,
        )
        for tx in today_wallet_transactions:
            if tx.direction == CashflowTransaction.Direction.IN:
                wallet_summary['today_deposit_total'] += _money(tx.amount)
            else:
                wallet_summary['today_withdraw_total'] += _money(tx.amount)

        recent_wallet_transactions = [
            {
                'id': tx.id,
                'wallet_name': tx.wallet.name if tx.wallet_id else '',
                'wallet_type': tx.wallet.wallet_type if tx.wallet_id else '',
                'direction': tx.direction,
                'amount': tx.amount,
                'description': tx.description,
                'reference_type': tx.reference_type,
                'reference_id': tx.reference_id,
                'transacted_at': tx.transacted_at,
                'share_group': _wallet_transaction_share_group(tx),
                'share_amount': _wallet_transaction_share_amount(tx),
            }
            for tx in CashflowTransaction.objects.select_related('wallet')
            .filter(tenant=tenant)
            .order_by('-transacted_at')[:100]
        ]
        sms_summary = NotificationLog.objects.filter(
            tenant=tenant,
            channel=NotificationLog.Channel.SMS,
            status=NotificationLog.Status.SENT,
        ).aggregate(sent_count=Count('id'))
        sms_cost_total = sum(
            (
                _money(tx.amount)
                for tx in today_wallet_transactions
                if tx.wallet_id and tx.wallet.wallet_type == Wallet.WalletType.SMS and tx.direction == CashflowTransaction.Direction.OUT
            ),
            Decimal('0'),
        )

        purchases = []
        installment_summary = {
            'active_count': 0,
            'installment_count': 0,
            'remaining_total': Decimal('0'),
            'monthly_total': Decimal('0'),
        }
        for purchase in CarWashFeaturePurchase.objects.filter(tenant=tenant).order_by('feature_key'):
            remaining = _money(purchase.remaining_amount)
            monthly = _money(purchase.monthly_installment_amount)
            if purchase.is_active:
                installment_summary['active_count'] += 1
            if purchase.payment_plan == CarWashFeaturePurchase.PaymentPlan.INSTALLMENT:
                installment_summary['installment_count'] += 1
                installment_summary['remaining_total'] += remaining
                installment_summary['monthly_total'] += monthly
            purchases.append(
                {
                    'id': purchase.id,
                    'feature_key': purchase.feature_key,
                    'title': _feature_title(purchase.feature_key),
                    'is_active': purchase.is_active,
                    'payment_plan': purchase.payment_plan,
                    'total_amount': purchase.total_amount,
                    'paid_amount': purchase.paid_amount,
                    'remaining_amount': remaining,
                    'installment_months': purchase.installment_months,
                    'monthly_installment_amount': monthly,
                    'next_installment_due_at': purchase.next_installment_due_at,
                    'purchased_at': purchase.purchased_at,
                }
            )

        workers = list(WorkerProfile.objects.select_related('user').filter(tenant=tenant, is_available=True).order_by('user__full_name', 'user__username'))
        events = (
            WorkerAttendance.objects.select_related('worker', 'worker__user')
            .filter(tenant=tenant, event_at__gte=today_start, event_at__lte=today_end)
            .order_by('event_at', 'id')
        )
        last_events = {}
        in_times = {}
        out_count = 0
        for event in events:
            last_events[event.worker_id] = event
            if event.event_type == WorkerAttendance.EventType.IN and event.worker_id not in in_times:
                in_times[event.worker_id] = event.event_at
            if event.event_type == WorkerAttendance.EventType.OUT:
                out_count += 1

        attendance_rows = []
        present_count = 0
        for worker in workers:
            last_event = last_events.get(worker.id)
            is_present = bool(last_event and last_event.event_type == WorkerAttendance.EventType.IN)
            if is_present:
                present_count += 1
            attendance_rows.append(
                {
                    'worker_id': worker.id,
                    'name': worker.user.full_name or worker.user.username,
                    'current_status': 'in' if is_present else 'out',
                    'first_in_at': in_times.get(worker.id),
                    'last_event_at': last_event.event_at if last_event else None,
                    'last_assigned_at': worker.last_assigned_at,
                    'active_jobs_count': worker.active_jobs_count,
                }
            )
        attendance_rows.sort(key=lambda item: (item['current_status'] != 'in', item['first_in_at'] or timezone.now(), item['name']))

        vehicle_counts = VehicleEntry.objects.filter(
            tenant=tenant,
            check_in_at__gte=today_start,
            check_in_at__lte=today_end,
        ).aggregate(
            total=Count('id'),
            released=Count('id', filter=Q(status=VehicleEntry.Status.RELEASED)),
            active=Count('id', filter=Q(status__in=[
                VehicleEntry.Status.ENTERED,
                VehicleEntry.Status.ASSIGNED,
                VehicleEntry.Status.IN_PROGRESS,
                VehicleEntry.Status.READY_TO_SETTLE,
            ])),
        )

        return Response(
            {
                'tenant': {
                    'id': tenant.id,
                    'name': tenant.name,
                    'slug': tenant.slug,
                    'address': tenant.address,
                    'is_active': tenant.is_active,
                    'updated_at': tenant.updated_at,
                },
                'wallet': {
                    'summary': wallet_summary,
                    'wallets': wallet_rows,
                    'recent_transactions': recent_wallet_transactions,
                    'sms_summary': {
                        'sent_count': sms_summary.get('sent_count') or 0,
                        'today_cost_total': sms_cost_total,
                    },
                },
                'options': {
                    'summary': installment_summary,
                    'purchases': purchases,
                },
                'attendance': {
                    'summary': {
                        'worker_count': len(workers),
                        'present_count': present_count,
                        'out_count': out_count,
                        'today_vehicle_count': vehicle_counts['total'] or 0,
                        'today_active_vehicle_count': vehicle_counts['active'] or 0,
                        'today_released_vehicle_count': vehicle_counts['released'] or 0,
                    },
                    'workers': attendance_rows,
                },
            },
            status=status.HTTP_200_OK,
        )


class HqSupportUserListCreateView(HqBaseView):
    def get(self, request):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden
        users = (
            User.objects.filter(
                platform_role__in=[User.PlatformRoles.HQ_ADMIN, User.PlatformRoles.HQ_SUPPORT],
                is_deleted=False,
            )
            .select_related('tenant')
            .order_by('platform_role', 'first_name', 'last_name')
        )
        return Response(HqSupportUserListSerializer(users, many=True).data, status=status.HTTP_200_OK)

    @transaction.atomic
    def post(self, request):
        forbidden = self.forbid_if_not_hq_admin(request)
        if forbidden:
            return forbidden

        serializer = HqSupportUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        raw_password = str(getattr(user, '_raw_password', '') or '').strip()
        phone = str(getattr(user, 'phone', '') or '').strip()
        sms_result = {'ok': False, 'message': 'پیامک اطلاعات ورود ارسال نشد.'}

        if raw_password and phone:
            sms_kwargs = {
                'tenant': getattr(user, 'tenant', None),
                'tenant_name': (user.tenant.name if getattr(user, 'tenant_id', None) else 'سامانه کارنوواش'),
                'phone': phone,
                'username': user.username,
                'password': raw_password,
                'role': 'hq_support',
                'created_by': request.user,
                'template_code': 'hq_support_credentials',
            }

            def _send_credentials_sms():
                try:
                    send_system_user_credentials_sms(**sms_kwargs)
                except Exception as exc:
                    print(f'hq support credentials sms failed for user {user.pk}: {exc}')

            # After commit so a provider error never rolls back the new support user.
            transaction.on_commit(_send_credentials_sms)
            sms_result = {'ok': True, 'message': 'پیامک اطلاعات ورود در صف ارسال قرار گرفت.'}
        elif not phone:
            sms_result = {'ok': False, 'message': 'شماره موبایل برای ارسال پیامک موجود نیست.'}
        elif not raw_password:
            sms_result = {'ok': False, 'message': 'رمز عبور برای ارسال پیامک موجود نیست.'}

        payload = HqSupportUserListSerializer(user).data
        payload['credentials_sms'] = sms_result
        return Response(payload, status=status.HTTP_201_CREATED)


class HqSupportUserDetailView(HqBaseView):
    def patch(self, request, pk):
        forbidden = self.forbid_if_not_hq_admin(request)
        if forbidden:
            return forbidden

        user = User.objects.filter(
            pk=pk,
            platform_role=User.PlatformRoles.HQ_SUPPORT,
            is_deleted=False,
        ).select_related('tenant').first()
        if not user:
            return Response({'detail': 'پشتیبان یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = HqSupportUserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if 'username' in data and data['username'] and User.objects.exclude(pk=user.pk).filter(username__iexact=data['username']).exists():
            return Response({'username': ['این نام کاربری قبلا ثبت شده است.']}, status=status.HTTP_400_BAD_REQUEST)
        if 'phone' in data and data['phone'] and User.objects.exclude(pk=user.pk).filter(phone=data['phone']).exists():
            return Response({'phone': ['این شماره موبایل قبلا ثبت شده است.']}, status=status.HTTP_400_BAD_REQUEST)

        changed_fields = []
        if 'first_name' in data:
            user.first_name = data['first_name']
            changed_fields.append('first_name')
        if 'last_name' in data:
            user.last_name = data['last_name']
            changed_fields.append('last_name')
        if 'username' in data and data['username']:
            user.username = data['username']
            changed_fields.append('username')
        if 'phone' in data and data['phone']:
            user.phone = data['phone']
            changed_fields.append('phone')
        if 'tenant_id' in data:
            user.tenant_id = data['tenant_id']
            changed_fields.append('tenant')
        if 'is_active' in data:
            user.is_active = data['is_active']
            changed_fields.append('is_active')
        if any(field in data for field in ['first_name', 'last_name']):
            user.full_name = f'{user.first_name} {user.last_name}'.strip()
            changed_fields.append('full_name')
        if data.get('password'):
            user.set_password(data['password'])
            changed_fields.append('password')

        if changed_fields:
            user.save(update_fields=list(dict.fromkeys(changed_fields)))
        return Response(HqSupportUserListSerializer(user).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        forbidden = self.forbid_if_not_hq_admin(request)
        if forbidden:
            return forbidden

        user = User.objects.filter(
            pk=pk,
            platform_role=User.PlatformRoles.HQ_SUPPORT,
            is_deleted=False,
        ).first()
        if not user:
            return Response({'detail': 'پشتیبان یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        SupportTicket.objects.filter(assigned_to=user).update(assigned_to=None)
        stamp = timezone.now().strftime('%Y%m%d%H%M%S')
        # Free unique username/phone so the same person can be re-added later.
        user.username = f'del_{user.pk}_{stamp}'[:150]
        user.phone = f'000{user.pk}{stamp}'[-20:]
        user.is_active = False
        user.is_deleted = True
        user.deleted_at = timezone.now()
        user.deleted_by = request.user if getattr(request.user, 'is_authenticated', False) else None
        user.save(update_fields=[
            'username',
            'phone',
            'is_active',
            'is_deleted',
            'deleted_at',
            'deleted_by',
        ])
        return Response({'soft_deleted': True, 'id': pk}, status=status.HTTP_200_OK)


class HqTicketListView(HqBaseView):
    def get(self, request):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        close_stale_support_tickets()
        q = str(request.query_params.get('q', '')).strip()
        status_filter = str(request.query_params.get('status', 'all')).strip().lower()
        priority_filter = str(request.query_params.get('priority', 'all')).strip().lower()
        tenant_id = request.query_params.get('tenant_id')

        queryset = (
            SupportTicket.objects.select_related('tenant', 'created_by', 'responded_by', 'assigned_to')
            .select_related('registration_request__manager')
            .prefetch_related('messages__sender')
            .filter(_hq_ticket_queryset_q())
            .order_by('-last_message_at', '-created_at')
        )
        queryset = apply_hq_ticket_visibility(queryset, request.user)
        if status_filter == 'active':
            queryset = queryset.exclude(status=SupportTicket.Status.CLOSED)
        elif status_filter == SupportTicket.Status.OPEN:
            queryset = queryset.exclude(status=SupportTicket.Status.CLOSED)
        elif status_filter in {choice[0] for choice in SupportTicket.Status.choices}:
            queryset = queryset.filter(status=status_filter)
        if priority_filter in {choice[0] for choice in SupportTicket.Priority.choices}:
            queryset = queryset.filter(priority=priority_filter)
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        if q:
            queryset = queryset.filter(
                Q(subject__icontains=q)
                | Q(message__icontains=q)
                | Q(tenant__name__icontains=q)
                | Q(created_by__full_name__icontains=q)
                | Q(created_by__username__icontains=q)
            )

        return Response(SupportTicketListSerializer(queryset[:300], many=True).data, status=status.HTTP_200_OK)


class HqTicketDetailView(HqBaseView):
    def get(self, request, pk):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        close_stale_support_tickets()
        queryset = (
            SupportTicket.objects.filter(pk=pk)
            .filter(_hq_ticket_queryset_q())
            .select_related('tenant', 'created_by', 'responded_by', 'assigned_to')
            .select_related('registration_request__manager')
            .prefetch_related('messages__sender', 'attachments')
        )
        queryset = apply_hq_ticket_visibility(queryset, request.user)
        ticket = queryset.first()
        if not ticket:
            return Response({'detail': 'تیکت یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(SupportTicketDetailSerializer(ticket, context={'request': request}).data, status=status.HTTP_200_OK)


class HqTicketMessageCreateView(HqBaseView):
    @transaction.atomic
    def post(self, request, pk):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        queryset = SupportTicket.objects.filter(pk=pk).filter(_hq_ticket_queryset_q()).select_related('assigned_to', 'tenant')
        queryset = apply_hq_ticket_visibility(queryset, request.user)
        ticket = queryset.first()
        if not ticket:
            return Response({'detail': 'تیکت یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = SupportTicketReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        previous_assignee = ticket.assigned_to
        referred = None
        if data.get('assign_to_user_id'):
            referred = refer_ticket_to_user(ticket, data['assign_to_user_id'])
            if not referred:
                return Response({'detail': 'پشتیبان مقصد برای ارجاع معتبر نیست.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            claim_ticket_if_unassigned(ticket, request.user)

        message = SupportTicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            body=data['body'],
            is_internal=bool(data.get('is_internal', False)),
        )
        ticket.last_message_at = message.created_at
        if not data.get('is_internal', False):
            ticket.response_text = data['body']
            ticket.responded_by = request.user
            ticket.responded_at = message.created_at
            if not ticket.first_response_at:
                ticket.first_response_at = message.created_at
            if data.get('status'):
                ticket.status = data['status']
                if data['status'] == SupportTicket.Status.CLOSED:
                    ticket.closed_at = message.created_at
            else:
                ticket.status = SupportTicket.Status.ANSWERED
            ticket.response_quality_score = _response_quality_score(ticket, data['body'])
        elif data.get('status'):
            ticket.status = data['status']
            if data['status'] == SupportTicket.Status.CLOSED:
                ticket.closed_at = message.created_at
        ticket.save(
            update_fields=[
                'assigned_to',
                'response_text',
                'responded_by',
                'first_response_at',
                'responded_at',
                'last_message_at',
                'status',
                'closed_at',
                'response_quality_score',
                'updated_at',
            ]
        )
        if previous_assignee and previous_assignee.id != ticket.assigned_to_id:
            _recalculate_support_metrics(previous_assignee)
        if ticket.assigned_to_id:
            _recalculate_support_metrics(ticket.assigned_to)
        return Response(SupportTicketMessageSerializer(message).data, status=status.HTTP_201_CREATED)


class HqTicketWalletTransferView(HqBaseView):
    @transaction.atomic
    def post(self, request, pk):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        queryset = SupportTicket.objects.select_for_update().filter(pk=pk).filter(_hq_ticket_queryset_q()).select_related('tenant', 'assigned_to')
        queryset = apply_hq_ticket_visibility(queryset, request.user)
        ticket = queryset.first()
        if not ticket:
            return Response({'detail': 'تیکت یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
        if not _is_wallet_card_payment_ticket(ticket):
            return Response({'detail': 'انتقال وجه فقط برای تیکت پرداخت کارت به کارت کیف پول مجاز است.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = HqTicketWalletTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        gross_amount = serializer.validated_data['amount']
        gross_amount, tax_amount, net_amount = _calculate_wallet_card_deposit_amounts(gross_amount)
        if net_amount <= 0:
            return Response({'detail': 'مبلغ خالص بعد از مالیات معتبر نیست.'}, status=status.HTTP_400_BAD_REQUEST)
        wallet_id = serializer.validated_data.get('wallet_id') or _parse_wallet_id_from_ticket(ticket)
        if not wallet_id:
            return Response({'detail': 'کیف پول مقصد در تیکت مشخص نیست.'}, status=status.HTTP_400_BAD_REQUEST)

        existing_cashflow = CashflowTransaction.objects.filter(
            tenant=ticket.tenant,
            reference_type='wallet_card_ticket',
            reference_id=ticket.id,
        ).first()
        if existing_cashflow:
            return Response({'detail': 'شارژ این تیکت قبلا ثبت شده است.'}, status=status.HTTP_400_BAD_REQUEST)

        wallet = Wallet.objects.select_for_update().filter(pk=wallet_id, tenant=ticket.tenant, is_active=True).first()
        if not wallet:
            return Response({'detail': 'کیف پول مقصد معتبر نیست.'}, status=status.HTTP_400_BAD_REQUEST)

        wallet.balance = Decimal(str(wallet.balance or 0)) + net_amount
        wallet.save(update_fields=['balance', 'updated_at'])
        cashflow = CashflowTransaction.objects.create(
            tenant=ticket.tenant,
            wallet=wallet,
            direction=CashflowTransaction.Direction.IN,
            amount=net_amount,
            description=(
                f'شارژ کارت به کارت از تیکت #{ticket.id} '
                f'(مبلغ واریزی {gross_amount:,.0f} − مالیات {WALLET_CARD_DEPOSIT_TAX_PERCENT:g}٪ = {tax_amount:,.0f})'
            ),
            reference_type='wallet_card_ticket',
            reference_id=ticket.id,
            created_by=request.user,
        )

        activate_core_software_installment(
            tenant=ticket.tenant,
            wallet=wallet,
            user=request.user,
        )

        message = SupportTicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            body=(
                f'انتقال وجه کارت به کارت تایید شد.\n'
                f'مبلغ خام واریزی: {gross_amount:,.0f} تومان\n'
                f'مالیات {WALLET_CARD_DEPOSIT_TAX_PERCENT:g}٪: {tax_amount:,.0f} تومان\n'
                f'مبلغ نهایی اضافه‌شده به کیف پول «{wallet.name}»: {net_amount:,.0f} تومان'
            ),
            is_internal=True,
        )
        ticket.status = SupportTicket.Status.ANSWERED
        ticket.responded_by = request.user
        ticket.responded_at = message.created_at
        if not ticket.first_response_at:
            ticket.first_response_at = message.created_at
        ticket.last_message_at = message.created_at
        claim_ticket_if_unassigned(ticket, request.user)
        ticket.save(update_fields=[
            'assigned_to',
            'status',
            'responded_by',
            'responded_at',
            'first_response_at',
            'last_message_at',
            'updated_at',
        ])
        if ticket.assigned_to_id:
            _recalculate_support_metrics(ticket.assigned_to)
        return Response(
            {
                'wallet_id': wallet.id,
                'wallet_name': wallet.name,
                'wallet_balance': wallet.balance,
                'transaction_id': cashflow.id,
                'gross_amount': gross_amount,
                'tax_percent': WALLET_CARD_DEPOSIT_TAX_PERCENT,
                'tax_amount': tax_amount,
                'net_amount': net_amount,
                'ticket': SupportTicketDetailSerializer(ticket).data,
            },
            status=status.HTTP_200_OK,
        )


class HqTicketWalletWithdrawView(HqBaseView):
    @transaction.atomic
    def post(self, request, pk):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        queryset = SupportTicket.objects.select_for_update().filter(pk=pk).filter(_hq_ticket_queryset_q()).select_related('tenant', 'assigned_to')
        queryset = apply_hq_ticket_visibility(queryset, request.user)
        ticket = queryset.first()
        if not ticket:
            return Response({'detail': 'تیکت یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
        if not _is_wallet_bank_withdrawal_ticket(ticket):
            return Response({'detail': 'برداشت فقط برای تیکت برداشت بانکی کیف پول مجاز است.'}, status=status.HTTP_400_BAD_REQUEST)

        existing_cashflow = CashflowTransaction.objects.filter(
            tenant=ticket.tenant,
            reference_type='wallet_bank_withdrawal_ticket',
            reference_id=ticket.id,
        ).first()
        if existing_cashflow:
            return Response({'detail': 'برداشت این تیکت قبلا ثبت شده است.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = HqTicketWalletTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data.get('amount') or _parse_wallet_withdraw_amount_from_ticket(ticket)
        wallet_id = serializer.validated_data.get('wallet_id') or _parse_wallet_id_from_ticket(ticket)
        if not wallet_id:
            return Response({'detail': 'کیف پول مبدا در تیکت مشخص نیست.'}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({'detail': 'مبلغ برداشت در تیکت معتبر نیست.'}, status=status.HTTP_400_BAD_REQUEST)

        wallet = Wallet.objects.select_for_update().filter(pk=wallet_id, tenant=ticket.tenant, is_active=True).first()
        if not wallet:
            return Response({'detail': 'کیف پول مبدا معتبر نیست.'}, status=status.HTTP_400_BAD_REQUEST)

        current_balance = Decimal(str(wallet.balance or 0))
        if current_balance < amount:
            return Response({'detail': 'موجودی کیف پول برای ثبت برداشت کافی نیست.'}, status=status.HTTP_400_BAD_REQUEST)

        wallet.balance = current_balance - amount
        wallet.save(update_fields=['balance', 'updated_at'])
        cashflow = CashflowTransaction.objects.create(
            tenant=ticket.tenant,
            wallet=wallet,
            direction=CashflowTransaction.Direction.OUT,
            amount=amount,
            description=f'برداشت بانکی از تیکت #{ticket.id}',
            reference_type='wallet_bank_withdrawal_ticket',
            reference_id=ticket.id,
            created_by=request.user,
        )
        message = SupportTicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            body=f'واریز بانکی تایید شد و مبلغ {amount:,.0f} تومان از کیف پول «{wallet.name}» کسر شد.',
            is_internal=True,
        )
        ticket.status = SupportTicket.Status.ANSWERED
        ticket.responded_by = request.user
        ticket.responded_at = message.created_at
        if not ticket.first_response_at:
            ticket.first_response_at = message.created_at
        ticket.last_message_at = message.created_at
        claim_ticket_if_unassigned(ticket, request.user)
        ticket.save(update_fields=[
            'assigned_to',
            'status',
            'responded_by',
            'responded_at',
            'first_response_at',
            'last_message_at',
            'updated_at',
        ])
        if ticket.assigned_to_id:
            _recalculate_support_metrics(ticket.assigned_to)
        return Response(
            {
                'wallet_id': wallet.id,
                'wallet_name': wallet.name,
                'wallet_balance': wallet.balance,
                'transaction_id': cashflow.id,
                'already_debited': False,
                'ticket': SupportTicketDetailSerializer(ticket).data,
            },
            status=status.HTTP_200_OK,
        )


class HqTicketApproveRegistrationView(HqBaseView):
    @transaction.atomic
    def post(self, request, pk):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        queryset = (
            SupportTicket.objects.select_for_update()
            .filter(pk=pk, is_registration_request=True).filter(_hq_ticket_queryset_q())
            .select_related('tenant', 'assigned_to', 'registration_request__manager')
        )
        queryset = apply_hq_ticket_visibility(queryset, request.user)
        ticket = queryset.first()
        if not ticket:
            return Response({'detail': 'درخواست ثبت‌نام یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        registration = getattr(ticket, 'registration_request', None)
        if not registration:
            return Response({'detail': 'اطلاعات ثبت‌نام برای این تیکت کامل نیست.'}, status=status.HTTP_400_BAD_REQUEST)
        if registration.status != PendingTenantRegistration.Status.PENDING:
            return Response({'detail': 'این درخواست قبلا بررسی شده است.'}, status=status.HTTP_400_BAD_REQUEST)

        tenant = ticket.tenant
        manager = registration.manager
        approval_time = timezone.now()

        tenant.is_active = True
        tenant.save(update_fields=['is_active', 'updated_at'])
        _start_trial_access(tenant, approval_time)

        manager.is_active = True
        if registration.temp_password:
            manager.set_password(registration.temp_password)
            manager.save(update_fields=['is_active', 'password'])
        else:
            manager.save(update_fields=['is_active'])

        sms_result = send_system_registration_credentials_sms(
            tenant=tenant,
            carwash_name=tenant.name,
            phone=manager.phone,
            username=manager.username,
            password=registration.temp_password,
        ) if registration.temp_password else {
            'attempted': False,
            'ok': False,
            'message': 'رمز عبور موقت برای ارسال پیامک در دسترس نیست.',
        }

        note_body = build_registration_approval_ticket_note(
            carwash_name=tenant.name,
            username=manager.username,
            reviewer_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
            sms_sent=bool(sms_result.get('ok')),
            sms_error=sms_result.get('message'),
        )
        message = SupportTicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            body=note_body,
            is_internal=False,
        )
        ticket.status = SupportTicket.Status.CLOSED
        ticket.response_text = note_body
        ticket.responded_by = request.user
        ticket.responded_at = approval_time
        if not ticket.first_response_at:
            ticket.first_response_at = approval_time
        ticket.closed_at = approval_time
        ticket.last_message_at = message.created_at
        claim_ticket_if_unassigned(ticket, request.user)
        ticket.save(update_fields=[
            'assigned_to',
            'status',
            'response_text',
            'responded_by',
            'responded_at',
            'first_response_at',
            'closed_at',
            'last_message_at',
            'updated_at',
        ])

        registration.status = PendingTenantRegistration.Status.APPROVED
        registration.reviewed_by = request.user
        registration.reviewed_at = approval_time
        registration.temp_password = ''
        registration.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'temp_password', 'updated_at'])

        if ticket.assigned_to_id:
            _recalculate_support_metrics(ticket.assigned_to)

        refreshed = (
            SupportTicket.objects.filter(pk=ticket.pk)
            .select_related('tenant', 'created_by', 'responded_by', 'assigned_to')
            .select_related('registration_request__manager')
            .prefetch_related('messages__sender', 'attachments')
            .first()
        )
        return Response(
            {
                'detail': 'ثبت‌نام کارواش تایید و حساب فعال شد.',
                'sms': sms_result,
                'ticket': SupportTicketDetailSerializer(refreshed, context={'request': request}).data,
            },
            status=status.HTTP_200_OK,
        )


class HqTicketAssignView(HqBaseView):
    @transaction.atomic
    def post(self, request, pk):
        forbidden = self.forbid_if_not_hq(request)
        if forbidden:
            return forbidden

        queryset = SupportTicket.objects.select_for_update().filter(pk=pk).filter(_hq_ticket_queryset_q()).select_related('assigned_to', 'tenant')
        queryset = apply_hq_ticket_visibility(queryset, request.user)
        ticket = queryset.first()
        if not ticket:
            return Response({'detail': 'تیکت یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        assignee_id = request.data.get('assign_to_user_id')
        if not assignee_id:
            return Response({'detail': 'پشتیبان مقصد را انتخاب کنید.'}, status=status.HTTP_400_BAD_REQUEST)

        previous_assignee = ticket.assigned_to
        assignee = refer_ticket_to_user(ticket, assignee_id)
        if not assignee:
            return Response({'detail': 'پشتیبان مقصد برای ارجاع معتبر نیست.'}, status=status.HTTP_400_BAD_REQUEST)

        note = str(request.data.get('note') or '').strip()
        if note:
            SupportTicketMessage.objects.create(
                ticket=ticket,
                sender=request.user,
                body=note,
                is_internal=True,
            )
            ticket.last_message_at = timezone.now()

        ticket.save(update_fields=['assigned_to', 'last_message_at', 'updated_at'] if note else ['assigned_to', 'updated_at'])
        if previous_assignee and previous_assignee.id != ticket.assigned_to_id:
            _recalculate_support_metrics(previous_assignee)
        _recalculate_support_metrics(ticket.assigned_to)

        refreshed = (
            SupportTicket.objects.filter(pk=ticket.pk)
            .select_related('tenant', 'created_by', 'responded_by', 'assigned_to')
            .select_related('registration_request__manager')
            .prefetch_related('messages__sender', 'attachments')
            .first()
        )
        return Response(
            SupportTicketDetailSerializer(refreshed, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )


def _build_hq_report_snapshot(start=None, end=None):
    tenants = list(
        _hq_visible_carwashes()
        .filter(is_active=True)
        .order_by('name')
        .only('id', 'name', 'is_active', 'exclude_from_hq_reports')
    )
    grouped = {
        tenant.id: {
            'tenant_id': tenant.id,
            'tenant_name': tenant.name,
            'tenant_is_active': tenant.is_active,
            'vehicles_count': 0,
            'released_count': 0,
            'cancelled_count': 0,
            'active_queue_count': 0,
            'payments_count': 0,
            'paid_amount': Decimal('0'),
            'final_total': Decimal('0'),
            'before_discount_total': Decimal('0'),
            'pending_amount': Decimal('0'),
            'expense_total': Decimal('0'),
            'tips_total': Decimal('0'),
            'discount_total': Decimal('0'),
            'services_total': Decimal('0'),
            'products_total': Decimal('0'),
            'refunded_total': Decimal('0'),
            'hq_share_total': Decimal('0'),
            'rah_share_total': Decimal('0'),
            'unallocated_wallet_total': Decimal('0'),
            'feature_income_total': Decimal('0'),
            'feature_paid_total': Decimal('0'),
            'feature_remaining_total': Decimal('0'),
            'wallet_balance': Decimal('0'),
            'wallet_regular_balance': Decimal('0'),
            'wallet_sms_balance': Decimal('0'),
            'wallet_deposit_total': Decimal('0'),
            'wallet_withdraw_total': Decimal('0'),
            'wallet_gateway_charge_total': Decimal('0'),
            'wallet_manual_charge_total': Decimal('0'),
            'wallet_transactions_count': 0,
            'sms_sent_count': 0,
            'sms_cost_total': Decimal('0'),
            'wallet_charge_health': 'idle',
            'feature_breakdown': [],
            'share_breakdown': {
                'hq': Decimal('0'),
                'rah': Decimal('0'),
                'none': Decimal('0'),
            },
            'last_activity_at': None,
        }
        for tenant in tenants
    }
    trend_map = defaultdict(
        lambda: {
            'date': '',
            'vehicles_count': 0,
            'paid_amount': Decimal('0'),
            'expense_total': Decimal('0'),
            'wallet_deposit_total': Decimal('0'),
            'wallet_withdraw_total': Decimal('0'),
            'hq_share_total': Decimal('0'),
            'rah_share_total': Decimal('0'),
            'sms_cost_total': Decimal('0'),
        }
    )

    vehicles = VehicleEntry.objects.select_related('tenant')
    if start:
        vehicles = vehicles.filter(check_in_at__gte=start)
    if end:
        vehicles = vehicles.filter(check_in_at__lte=end)

    active_statuses = {
        VehicleEntry.Status.ENTERED,
        VehicleEntry.Status.ASSIGNED,
        VehicleEntry.Status.IN_PROGRESS,
        VehicleEntry.Status.READY_TO_SETTLE,
    }
    for vehicle in vehicles:
        tenant = vehicle.tenant
        if not tenant or tenant.id not in grouped:
            continue
        row = grouped[tenant.id]
        row['vehicles_count'] += 1
        if vehicle.status == VehicleEntry.Status.RELEASED:
            row['released_count'] += 1
        if vehicle.status == VehicleEntry.Status.CANCELLED:
            row['cancelled_count'] += 1
        if vehicle.status in active_statuses:
            row['active_queue_count'] += 1
        if not row['last_activity_at'] or vehicle.check_in_at > row['last_activity_at']:
            row['last_activity_at'] = vehicle.check_in_at

        trend_key = timezone.localtime(vehicle.check_in_at).date().isoformat()
        trend = trend_map[trend_key]
        trend['date'] = trend_key
        trend['vehicles_count'] += 1

    payments = Payment.objects.select_related('tenant', 'vehicle_entry')
    if start:
        payments = payments.filter(Q(paid_at__gte=start) | Q(paid_at__isnull=True, created_at__gte=start))
    if end:
        payments = payments.filter(Q(paid_at__lte=end) | Q(paid_at__isnull=True, created_at__lte=end))

    for payment in payments:
        tenant = payment.tenant or getattr(payment.vehicle_entry, 'tenant', None)
        if not tenant or tenant.id not in grouped:
            continue
        row = grouped[tenant.id]
        event_dt = payment.paid_at or payment.created_at
        amount = Decimal(str(payment.amount or 0))
        if payment.status == Payment.Status.SUCCESS:
            discount_amount = Decimal(str(payment.discount_amount or 0))
            row['payments_count'] += 1
            row['paid_amount'] += amount
            row['final_total'] += amount
            row['before_discount_total'] += amount + discount_amount
            row['tips_total'] += Decimal(str(payment.tip_amount or 0))
            row['discount_total'] += discount_amount
            row['services_total'] += Decimal(str(payment.service_amount or 0))
            row['products_total'] += Decimal(str(payment.product_amount or 0))
            if event_dt and (not row['last_activity_at'] or event_dt > row['last_activity_at']):
                row['last_activity_at'] = event_dt
            if event_dt:
                trend_key = timezone.localtime(event_dt).date().isoformat()
                trend = trend_map[trend_key]
                trend['date'] = trend_key
                trend['paid_amount'] += amount
        elif payment.status == Payment.Status.PENDING:
            row['pending_amount'] += amount
        elif payment.status == Payment.Status.REFUNDED:
            row['refunded_total'] += amount

    stock_movements = StockMovement.objects.select_related('tenant').filter(reference_type='manager_purchase')
    if start:
        stock_movements = stock_movements.filter(moved_at__gte=start)
    if end:
        stock_movements = stock_movements.filter(moved_at__lte=end)

    for movement in stock_movements:
        tenant = movement.tenant
        if not tenant or tenant.id not in grouped:
            continue
        cost_total = Decimal(str(movement.quantity or 0)) * Decimal(str(movement.unit_cost or 0))
        row = grouped[tenant.id]
        row['expense_total'] += cost_total
        if not row['last_activity_at'] or movement.moved_at > row['last_activity_at']:
            row['last_activity_at'] = movement.moved_at

        trend_key = timezone.localtime(movement.moved_at).date().isoformat()
        trend = trend_map[trend_key]
        trend['date'] = trend_key
        trend['expense_total'] += cost_total

    manual_expenses = ExpenseEntry.objects.select_related('tenant').filter(source_type=ExpenseEntry.SourceType.MANUAL)
    if start:
        manual_expenses = manual_expenses.filter(spent_at__gte=start)
    if end:
        manual_expenses = manual_expenses.filter(spent_at__lte=end)

    for expense in manual_expenses:
        tenant = expense.tenant
        if not tenant or tenant.id not in grouped:
            continue
        amount = Decimal(str(expense.amount or 0))
        row = grouped[tenant.id]
        row['expense_total'] += amount
        if not row['last_activity_at'] or expense.spent_at > row['last_activity_at']:
            row['last_activity_at'] = expense.spent_at

        trend_key = timezone.localtime(expense.spent_at).date().isoformat()
        trend = trend_map[trend_key]
        trend['date'] = trend_key
        trend['expense_total'] += amount

    feature_summary = {
        feature_key: {
            'key': feature_key,
            'label': HQ_FEATURE_META.get(feature_key, {}).get('label', feature_key),
            'tab_label': HQ_FEATURE_META.get(feature_key, {}).get('tab_label', feature_key),
            'description': HQ_FEATURE_META.get(feature_key, {}).get('description', ''),
            'total_amount': Decimal('0'),
            'paid_amount': Decimal('0'),
            'remaining_amount': Decimal('0'),
            'active_count': 0,
            'purchase_count': 0,
        }
        for feature_key in HQ_FEATURE_KEYS
    }
    feature_purchases = CarWashFeaturePurchase.objects.select_related('tenant').all()
    if start:
        feature_purchases = feature_purchases.filter(purchased_at__gte=start)
    if end:
        feature_purchases = feature_purchases.filter(purchased_at__lte=end)

    for purchase in feature_purchases:
        tenant = purchase.tenant
        if not tenant or tenant.id not in grouped:
            continue
        total_amount = Decimal(str(purchase.total_amount or 0))
        paid_amount = Decimal(str(purchase.paid_amount or 0))
        remaining_amount = Decimal(str(purchase.remaining_amount or 0))
        share_group = _feature_share_group(purchase.feature_key)
        row = grouped[tenant.id]
        feature_item = {
            'id': purchase.id,
            'feature_key': purchase.feature_key,
            'label': HQ_FEATURE_META.get(purchase.feature_key, {}).get('label', purchase.get_feature_key_display()),
            'tab_label': HQ_FEATURE_META.get(purchase.feature_key, {}).get('tab_label', purchase.get_feature_key_display()),
            'payment_plan': purchase.payment_plan,
            'is_active': purchase.is_active,
            'total_amount': total_amount,
            'paid_amount': paid_amount,
            'remaining_amount': remaining_amount,
            'installment_months': purchase.installment_months,
            'monthly_installment_amount': purchase.monthly_installment_amount,
            'next_installment_due_at': purchase.next_installment_due_at,
            'purchased_at': purchase.purchased_at,
            'share_group': share_group,
        }
        row['feature_breakdown'].append(feature_item)
        row['feature_income_total'] += total_amount
        row['feature_paid_total'] += paid_amount
        row['feature_remaining_total'] += remaining_amount
        if share_group == 'hq':
            summary_item = feature_summary.setdefault(purchase.feature_key, {
                'key': purchase.feature_key,
                'label': purchase.get_feature_key_display(),
                'tab_label': purchase.get_feature_key_display(),
                'description': '',
                'total_amount': Decimal('0'),
                'paid_amount': Decimal('0'),
                'remaining_amount': Decimal('0'),
                'active_count': 0,
                'purchase_count': 0,
            })
            summary_item['total_amount'] += total_amount
            summary_item['paid_amount'] += paid_amount
            summary_item['remaining_amount'] += remaining_amount
            summary_item['purchase_count'] += 1
            if purchase.is_active:
                summary_item['active_count'] += 1
        if not row['last_activity_at'] or purchase.purchased_at > row['last_activity_at']:
            row['last_activity_at'] = purchase.purchased_at

    wallets = Wallet.objects.filter(is_active=True).only('tenant_id', 'wallet_type', 'balance')
    for wallet in wallets:
        if not wallet.tenant_id or wallet.tenant_id not in grouped:
            continue
        row = grouped[wallet.tenant_id]
        balance = Decimal(str(wallet.balance or 0))
        row['wallet_balance'] += balance
        if wallet.wallet_type == Wallet.WalletType.SMS:
            row['wallet_sms_balance'] += balance
        else:
            row['wallet_regular_balance'] += balance

    wallet_qs = CashflowTransaction.objects.select_related('wallet', 'tenant', 'created_by')
    if start:
        wallet_qs = wallet_qs.filter(transacted_at__gte=start)
    if end:
        wallet_qs = wallet_qs.filter(transacted_at__lte=end)
    wallet_transactions = list(wallet_qs)

    purchase_ids = {
        tx.reference_id
        for tx in wallet_transactions
        if tx.reference_type in FEATURE_PURCHASE_REFERENCE_TYPES and tx.reference_id
    }
    purchase_feature_map = {
        item.id: item.feature_key
        for item in CarWashFeaturePurchase.objects.filter(id__in=purchase_ids).only('id', 'feature_key')
    }

    wallet_transaction_rows = []
    for tx in wallet_transactions:
        tenant_id = tx.tenant_id
        if not tenant_id or tenant_id not in grouped:
            continue
        row = grouped[tenant_id]
        amount = Decimal(str(tx.amount or 0))
        if tx.reference_type in FEATURE_PURCHASE_REFERENCE_TYPES and tx.reference_id in purchase_feature_map:
            share_group = _feature_share_group(purchase_feature_map[tx.reference_id])
        else:
            share_group = _wallet_transaction_share_group(tx)
        share_amount = amount if share_group in {'hq', 'rah'} else Decimal('0')
        row['wallet_transactions_count'] += 1
        row['share_breakdown'][share_group] += share_amount
        if share_group == 'hq':
            row['hq_share_total'] += share_amount
        elif share_group == 'rah':
            row['rah_share_total'] += share_amount
        else:
            row['unallocated_wallet_total'] += amount
        if tx.direction == CashflowTransaction.Direction.IN:
            row['wallet_deposit_total'] += amount
            if tx.reference_type == 'wallet_gateway_deposit':
                row['wallet_gateway_charge_total'] += amount
            else:
                row['wallet_manual_charge_total'] += amount
        else:
            row['wallet_withdraw_total'] += amount
            if tx.wallet_id and tx.wallet.wallet_type == Wallet.WalletType.SMS:
                row['sms_cost_total'] += amount
        if not row['last_activity_at'] or tx.transacted_at > row['last_activity_at']:
            row['last_activity_at'] = tx.transacted_at

        trend_key = timezone.localtime(tx.transacted_at).date().isoformat()
        trend = trend_map[trend_key]
        trend['date'] = trend_key
        if tx.direction == CashflowTransaction.Direction.IN:
            trend['wallet_deposit_total'] += amount
        else:
            trend['wallet_withdraw_total'] += amount
        if share_group == 'hq':
            trend['hq_share_total'] += share_amount
        elif share_group == 'rah':
            trend['rah_share_total'] += share_amount
        if tx.direction == CashflowTransaction.Direction.OUT and tx.wallet_id and tx.wallet.wallet_type == Wallet.WalletType.SMS:
            trend['sms_cost_total'] += amount
        wallet_transaction_rows.append({
            'id': tx.id,
            'tenant_id': tenant_id,
            'tenant_name': tx.tenant.name if tx.tenant_id else '',
            'wallet_id': tx.wallet_id,
            'wallet_name': tx.wallet.name if tx.wallet_id else '',
            'wallet_type': tx.wallet.wallet_type if tx.wallet_id else '',
            'direction': tx.direction,
            'amount': amount,
            'description': tx.description,
            'reference_type': tx.reference_type,
            'reference_id': tx.reference_id,
            'transacted_at': tx.transacted_at,
            'created_by_name': (tx.created_by.full_name or tx.created_by.username) if tx.created_by_id else '',
            'share_group': share_group,
            'share_amount': share_amount,
            'hq_share_amount': share_amount if share_group == 'hq' else Decimal('0'),
            'rah_share_amount': share_amount if share_group == 'rah' else Decimal('0'),
        })

    sms_logs = NotificationLog.objects.filter(channel=NotificationLog.Channel.SMS, status=NotificationLog.Status.SENT)
    if start:
        sms_logs = sms_logs.filter(sent_at__gte=start)
    if end:
        sms_logs = sms_logs.filter(sent_at__lte=end)
    sms_counts = sms_logs.values('tenant_id').annotate(total=Count('id'))
    for item in sms_counts:
        tenant_id = item.get('tenant_id')
        if tenant_id and tenant_id in grouped:
            grouped[tenant_id]['sms_sent_count'] = item.get('total') or 0

    gateway_requests = WalletGatewayRequest.objects.filter(status=WalletGatewayRequest.Status.PAID)
    if start:
        gateway_requests = gateway_requests.filter(completed_at__gte=start)
    if end:
        gateway_requests = gateway_requests.filter(completed_at__lte=end)

    gateway_counts = defaultdict(int)
    for request in gateway_requests.only('tenant_id'):
        if request.tenant_id:
            gateway_counts[request.tenant_id] += 1

    rows = []
    for item in grouped.values():
        vehicles_count = item['vehicles_count']
        paid_amount = item['paid_amount']
        expense_total = item['expense_total']
        net_amount = paid_amount - expense_total
        average_ticket = (paid_amount / vehicles_count).quantize(Decimal('0.01')) if vehicles_count else Decimal('0')
        completion_rate = round((item['released_count'] / vehicles_count) * 100, 1) if vehicles_count else 0
        if net_amount < 0 or (paid_amount > 0 and item['pending_amount'] >= paid_amount * Decimal('0.35')):
            health = 'risk'
        elif vehicles_count and completion_rate >= 80 and net_amount > 0:
            health = 'strong'
        elif vehicles_count or paid_amount or expense_total or item['pending_amount']:
            health = 'stable'
        else:
            health = 'idle'

        item['net_amount'] = net_amount
        item['average_ticket'] = average_ticket
        item['completion_rate'] = completion_rate
        item['health'] = health
        item['wallet_gateway_charge_count'] = gateway_counts.get(item['tenant_id'], 0)
        if item['wallet_balance'] <= 0 and (item['wallet_withdraw_total'] or item['wallet_deposit_total']):
            item['wallet_charge_health'] = 'empty'
        elif item['wallet_sms_balance'] > item['wallet_regular_balance'] and item['wallet_balance'] > 0:
            item['wallet_charge_health'] = 'sms_heavy'
        elif item['wallet_gateway_charge_total'] >= item['wallet_manual_charge_total'] and item['wallet_deposit_total'] > 0:
            item['wallet_charge_health'] = 'gateway'
        elif item['wallet_balance'] > 0:
            item['wallet_charge_health'] = 'healthy'
        rows.append(item)

    rows.sort(
        key=lambda item: (
            Decimal(str(item['paid_amount'] or 0)),
            int(item['vehicles_count'] or 0),
            Decimal(str(item['net_amount'] or 0)),
        ),
        reverse=True,
    )
    for index, item in enumerate(rows, start=1):
        item['rank'] = index

    active_rows = [item for item in rows if item['vehicles_count'] or item['paid_amount'] or item['expense_total'] or item['pending_amount']]
    total_paid = sum((item['paid_amount'] for item in rows), Decimal('0'))
    total_expense = sum((item['expense_total'] for item in rows), Decimal('0'))
    total_net = sum((item['net_amount'] for item in rows), Decimal('0'))
    total_pending = sum((item['pending_amount'] for item in rows), Decimal('0'))
    total_wallet_balance = sum((item['wallet_balance'] for item in rows), Decimal('0'))
    total_wallet_regular = sum((item['wallet_regular_balance'] for item in rows), Decimal('0'))
    total_wallet_sms = sum((item['wallet_sms_balance'] for item in rows), Decimal('0'))
    total_wallet_deposits = sum((item['wallet_deposit_total'] for item in rows), Decimal('0'))
    total_wallet_withdraws = sum((item['wallet_withdraw_total'] for item in rows), Decimal('0'))
    total_wallet_gateway = sum((item['wallet_gateway_charge_total'] for item in rows), Decimal('0'))
    total_wallet_manual = sum((item['wallet_manual_charge_total'] for item in rows), Decimal('0'))
    total_hq_share = sum((item['hq_share_total'] for item in rows), Decimal('0'))
    total_rah_share = sum((item['rah_share_total'] for item in rows), Decimal('0'))
    total_unallocated_wallet = sum((item['unallocated_wallet_total'] for item in rows), Decimal('0'))
    total_feature_income = sum((item['feature_income_total'] for item in rows), Decimal('0'))
    total_feature_paid = sum((item['feature_paid_total'] for item in rows), Decimal('0'))
    total_feature_remaining = sum((item['feature_remaining_total'] for item in rows), Decimal('0'))
    total_vehicles = sum(item['vehicles_count'] for item in rows)
    total_released = sum(item['released_count'] for item in rows)
    total_cancelled = sum(item['cancelled_count'] for item in rows)

    summary = {
        'tenants_count': len(rows),
        'active_tenants_count': len(active_rows),
        'vehicles_count': total_vehicles,
        'released_count': total_released,
        'cancelled_count': total_cancelled,
        'paid_amount': total_paid,
        'final_total': sum((item['final_total'] for item in rows), Decimal('0')),
        'before_discount_total': sum((item['before_discount_total'] for item in rows), Decimal('0')),
        'expense_total': total_expense,
        'net_total': total_net,
        'pending_amount': total_pending,
        'payments_count': sum(item['payments_count'] for item in rows),
        'tips_total': sum((item['tips_total'] for item in rows), Decimal('0')),
        'discount_total': sum((item['discount_total'] for item in rows), Decimal('0')),
        'services_total': sum((item['services_total'] for item in rows), Decimal('0')),
        'products_total': sum((item['products_total'] for item in rows), Decimal('0')),
        'average_ticket': (total_paid / total_vehicles).quantize(Decimal('0.01')) if total_vehicles else Decimal('0'),
        'completion_rate': round((total_released / total_vehicles) * 100, 1) if total_vehicles else 0,
        'collection_rate': round((float(total_paid) / float(total_paid + total_pending)) * 100, 1) if (total_paid + total_pending) > 0 else 0,
        'wallet_balance_total': total_wallet_balance,
        'wallet_regular_balance_total': total_wallet_regular,
        'wallet_sms_balance_total': total_wallet_sms,
        'wallet_deposit_total': total_wallet_deposits,
        'wallet_withdraw_total': total_wallet_withdraws,
        'wallet_gateway_charge_total': total_wallet_gateway,
        'wallet_manual_charge_total': total_wallet_manual,
        'wallet_transactions_count': sum(item['wallet_transactions_count'] for item in rows),
        'hq_share_total': total_hq_share,
        'rah_share_total': total_rah_share,
        'unallocated_wallet_total': total_unallocated_wallet,
        'sms_sent_count': sum(item['sms_sent_count'] for item in rows),
        'sms_cost_total': sum((item['sms_cost_total'] for item in rows), Decimal('0')),
        'feature_income_total': total_feature_income,
        'feature_paid_total': total_feature_paid,
        'feature_remaining_total': total_feature_remaining,
    }

    trends = []
    for key in sorted(trend_map.keys()):
        entry = trend_map[key]
        entry['net_amount'] = entry['paid_amount'] - entry['expense_total']
        entry['wallet_net_flow'] = entry['wallet_deposit_total'] - entry['wallet_withdraw_total']
        trends.append(entry)

    top_revenue = max(rows, key=lambda item: Decimal(str(item['paid_amount'] or 0)), default=None)
    top_volume = max(rows, key=lambda item: int(item['vehicles_count'] or 0), default=None)
    top_margin = max(rows, key=lambda item: Decimal(str(item['net_amount'] or 0)), default=None)
    top_wallet_balance = max(rows, key=lambda item: Decimal(str(item['wallet_balance'] or 0)), default=None)
    top_wallet_deposit = max(rows, key=lambda item: Decimal(str(item['wallet_deposit_total'] or 0)), default=None)
    wallet_watchlist = min(
        [item for item in rows if item['wallet_balance'] or item['wallet_deposit_total'] or item['wallet_withdraw_total']],
        key=lambda item: (Decimal(str(item['wallet_balance'] or 0)), -Decimal(str(item['wallet_withdraw_total'] or 0))),
        default=None,
    )
    watchlist = min(
        [item for item in rows if item['vehicles_count'] or item['paid_amount'] or item['expense_total'] or item['pending_amount']],
        key=lambda item: (Decimal(str(item['net_amount'] or 0)), -Decimal(str(item['pending_amount'] or 0))),
        default=None,
    )

    return {
        'summary': summary,
        'rows': rows,
        'trends': trends,
        'feature_summary': list(feature_summary.values()),
        'wallet_transactions': sorted(
            wallet_transaction_rows,
            key=lambda item: item['transacted_at'] or timezone.now(),
            reverse=True,
        )[:250],
        'highlights': {
            'top_revenue': top_revenue,
            'top_volume': top_volume,
            'top_margin': top_margin,
            'top_wallet_balance': top_wallet_balance,
            'top_wallet_deposit': top_wallet_deposit,
            'wallet_watchlist': wallet_watchlist,
            'watchlist': watchlist,
        },
    }


def _percent_change(current, previous):
    current_value = Decimal(str(current or 0))
    previous_value = Decimal(str(previous or 0))
    if previous_value == 0:
        if current_value == 0:
            return 0
        return None
    return round(float(((current_value - previous_value) / previous_value) * Decimal('100')), 1)


class HqCarWashReportsView(HqBaseView):
    def get(self, request, pk):
        if not _can_see_hq_reports(request.user):
            return Response({'detail': 'دسترسی گزارشات فقط برای مدیرکل و مالی HQ است.'}, status=status.HTTP_403_FORBIDDEN)

        tenant = _hq_visible_carwashes().filter(pk=pk, is_active=True).first()
        if not tenant:
            return Response({'detail': 'کارواش فعال پیدا نشد.'}, status=status.HTTP_404_NOT_FOUND)

        original_tenant = getattr(request.user, 'tenant', None)
        request.user.tenant = tenant
        try:
            response = ReportsDashboardView().get(request)
        finally:
            request.user.tenant = original_tenant

        payload = getattr(response, 'data', {}) or {}
        payload['tenant'] = {
            'id': tenant.id,
            'name': tenant.name,
            'address': tenant.address,
            'is_active': tenant.is_active,
        }
        return Response(payload, status=getattr(response, 'status_code', status.HTTP_200_OK))


class HqReportsView(HqBaseView):
    def get(self, request):
        if not _can_see_hq_reports(request.user):
            return Response({'detail': 'دسترسی گزارشات فقط برای مدیرکل و مالی HQ است.'}, status=status.HTTP_403_FORBIDDEN)

        start = _parse_dt(request.query_params.get('start'))
        end = _parse_dt(request.query_params.get('end'), end_of_day=True)
        payload = _build_hq_report_snapshot(start=start, end=end)
        payload['summary']['date_start'] = request.query_params.get('start') or ''
        payload['summary']['date_end'] = request.query_params.get('end') or ''

        if start and end and end >= start:
            previous_span = end - start
            previous_end = start - timedelta(seconds=1)
            previous_start = previous_end - previous_span
            previous_payload = _build_hq_report_snapshot(start=previous_start, end=previous_end)
            payload['summary']['revenue_change_percent'] = _percent_change(
                payload['summary']['paid_amount'],
                previous_payload['summary']['paid_amount'],
            )
            payload['summary']['vehicles_change_percent'] = _percent_change(
                payload['summary']['vehicles_count'],
                previous_payload['summary']['vehicles_count'],
            )
            payload['summary']['net_change_percent'] = _percent_change(
                payload['summary']['net_total'],
                previous_payload['summary']['net_total'],
            )
        else:
            payload['summary']['revenue_change_percent'] = None
            payload['summary']['vehicles_change_percent'] = None
            payload['summary']['net_change_percent'] = None

        return Response(payload, status=status.HTTP_200_OK)
