from decimal import Decimal, ROUND_HALF_UP
from secrets import token_hex

from django.db import transaction
from django.db.models import Sum, Count, Q, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.auth.models import CarWashFeaturePurchase
from apps.payments.models import CashflowTransaction, Wallet
from apps.payments.views import FEATURE_OPTION_CATALOG

from .models import (
    BulkServiceJob,
    BulkServiceJobItem,
    PlatformProject,
    ServiceAlert,
    ServiceAuditLog,
    ServiceOrder,
    ServicePaymentRecord,
    ServicePeriod,
    ServicePlan,
    ServiceProduct,
    ServiceSubscription,
    ServiceUsageMeter,
)

VAT_PERCENT = Decimal('10')

# Share ownership for HQ finance (Carno vs Arakar).
KARNO_PRODUCT_KEYS = {'attendance', 'excel_import', 'sms_club', 'sms_panel', 'sms_credit', 'wallet'}
ARAKAR_PRODUCT_KEYS = {'core_software', 'cloud_storage'}

SMS_COST_PER_100 = Decimal('145')
SMS_PROFIT_PER_100 = Decimal('40')
SMS_BILL_PER_100 = SMS_COST_PER_100 + SMS_PROFIT_PER_100


def product_share_group(product_key_or_feature):
    key = (product_key_or_feature or '').strip()
    if key in KARNO_PRODUCT_KEYS:
        return 'carno'
    if key in ARAKAR_PRODUCT_KEYS:
        return 'arakar'
    return 'none'


def money(value):
    return Decimal(str(value or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


PAYMENT_PLAN_LABELS = {
    'cash': 'نقدی',
    'installment': 'اقساطی',
    'manual': 'ثبت مدیریتی',
}


def resolve_plan_for_product(product, purchase=None):
    """Pick the service plan that matches the real payment method — never invent installment."""
    plans = list(product.plans.filter(is_active=True))
    if not plans:
        return None

    def by_code(code):
        return next((item for item in plans if item.code == code), None)

    payment_plan = (getattr(purchase, 'payment_plan', None) or '').strip() if purchase else ''
    remaining = money(getattr(purchase, 'remaining_amount', 0)) if purchase else Decimal('0')
    installment_months = int(getattr(purchase, 'installment_months', 0) or 0) if purchase else 0

    if payment_plan == CarWashFeaturePurchase.PaymentPlan.CASH:
        return by_code('cash') or by_code('annual') or by_code('perpetual') or plans[0]
    if payment_plan == CarWashFeaturePurchase.PaymentPlan.INSTALLMENT and (remaining > 0 or installment_months > 0):
        return by_code('installment') or plans[0]
    if payment_plan == CarWashFeaturePurchase.PaymentPlan.INSTALLMENT and remaining <= 0:
        # Fully settled installment purchase still keeps installment plan identity.
        return by_code('installment') or by_code('cash') or plans[0]
    if payment_plan == CarWashFeaturePurchase.PaymentPlan.MANUAL:
        if remaining > 0 and installment_months > 0:
            return by_code('installment') or plans[0]
        return by_code('cash') or by_code('annual') or by_code('perpetual') or plans[0]
    return by_code('cash') or by_code('annual') or by_code('perpetual') or sorted(plans, key=lambda p: p.sort_order)[0]


def compute_totals(base_amount, discount_amount=0, tax_percent=VAT_PERCENT):
    base = money(base_amount)
    discount = money(discount_amount)
    taxable = max(Decimal('0'), base - discount)
    tax = money(taxable * money(tax_percent) / Decimal('100'))
    return {
        'base_amount': base,
        'discount_amount': discount,
        'tax_amount': tax,
        'final_amount': taxable + tax,
    }


def ensure_main_wallet(tenant):
    wallet = Wallet.objects.filter(tenant=tenant, wallet_type=Wallet.WalletType.BANK, is_active=True).order_by('id').first()
    if wallet:
        return wallet
    return Wallet.objects.create(
        tenant=tenant,
        name='کیف پول اصلی',
        wallet_type=Wallet.WalletType.BANK,
        balance=Decimal('0'),
        is_active=True,
    )


def write_audit(*, tenant, action, actor=None, subscription=None, order=None, reason='', note='', before='', after='', financial=0, access='', payload=None):
    return ServiceAuditLog.objects.create(
        tenant=tenant,
        subscription=subscription,
        order=order,
        action=action,
        reason=reason or '',
        note=note or '',
        before_status=before or '',
        after_status=after or '',
        financial_impact=money(financial),
        access_impact=access or '',
        actor=actor,
        payload=payload or {},
    )


def sync_feature_purchase(subscription, *, activate=True):
    feature_key = (subscription.product.feature_key or subscription.product.product_key or '').strip()
    if not feature_key:
        return None
    valid_keys = {choice[0] for choice in CarWashFeaturePurchase.FeatureKey.choices}
    if feature_key not in valid_keys:
        return None
    purchase, _ = CarWashFeaturePurchase.objects.get_or_create(
        tenant=subscription.tenant,
        feature_key=feature_key,
        defaults={
            'is_active': bool(activate),
            'payment_plan': CarWashFeaturePurchase.PaymentPlan.CASH,
            'total_amount': subscription.final_amount,
            'paid_amount': subscription.paid_amount,
            'remaining_amount': subscription.remaining_amount,
        },
    )
    purchase.is_active = bool(activate) and subscription.status in {
        ServiceSubscription.Status.ACTIVE,
        ServiceSubscription.Status.NEAR_EXPIRY,
        ServiceSubscription.Status.TRIAL,
    }
    purchase.total_amount = subscription.final_amount
    purchase.paid_amount = subscription.paid_amount
    purchase.remaining_amount = subscription.remaining_amount
    purchase.save(update_fields=['is_active', 'total_amount', 'paid_amount', 'remaining_amount', 'updated_at'])
    subscription.feature_purchase = purchase
    subscription.save(update_fields=['feature_purchase', 'updated_at'])
    return purchase


def refresh_subscription_status(subscription, now=None):
    now = now or timezone.now()
    if subscription.status in {
        ServiceSubscription.Status.CANCELLED,
        ServiceSubscription.Status.BLOCKED,
        ServiceSubscription.Status.SUSPENDED,
        ServiceSubscription.Status.PENDING_PAYMENT,
        ServiceSubscription.Status.PENDING_ACTIVATION,
    }:
        return subscription
    if subscription.ends_at:
        if subscription.ends_at < now:
            if subscription.grace_ends_at and subscription.grace_ends_at >= now:
                subscription.status = ServiceSubscription.Status.EXPIRED
            elif subscription.grace_ends_at and subscription.grace_ends_at < now:
                subscription.status = ServiceSubscription.Status.BLOCKED
                sync_feature_purchase(subscription, activate=False)
            else:
                subscription.status = ServiceSubscription.Status.EXPIRED
                sync_feature_purchase(subscription, activate=False)
        else:
            days = (subscription.ends_at.date() - now.date()).days
            if 0 <= days <= 15:
                subscription.status = ServiceSubscription.Status.NEAR_EXPIRY
            elif subscription.status in {ServiceSubscription.Status.NEAR_EXPIRY, ServiceSubscription.Status.EXPIRED}:
                subscription.status = ServiceSubscription.Status.ACTIVE
    if subscription.remaining_amount > 0 and subscription.payment_status == ServiceSubscription.PaymentStatus.OVERDUE:
        pass
    elif subscription.remaining_amount <= 0 and subscription.paid_amount > 0:
        subscription.payment_status = ServiceSubscription.PaymentStatus.SETTLED
    elif subscription.paid_amount > 0:
        subscription.payment_status = ServiceSubscription.PaymentStatus.PARTIAL
    subscription.save(update_fields=['status', 'payment_status', 'updated_at'])
    return subscription


def make_order_code():
    return f'SO-{timezone.now().strftime("%Y%m%d%H%M%S")}-{token_hex(3).upper()}'


@transaction.atomic
def create_order_and_activate(
    *,
    tenant,
    product,
    plan,
    actor=None,
    payment_method=ServiceOrder.PaymentMethod.WALLET,
    discount_amount=0,
    idempotency_key='',
    require_manual_approval=False,
    auto_activate=True,
    note='',
):
    if idempotency_key:
        existing = ServiceOrder.objects.filter(tenant=tenant, idempotency_key=idempotency_key).select_related('subscription').first()
        if existing:
            return existing

    amounts = plan.compute_amounts()
    if discount_amount:
        amounts = compute_totals(plan.base_price, discount_amount, amounts['tax_percent'])

    order = ServiceOrder.objects.create(
        order_code=make_order_code(),
        tenant=tenant,
        project=product.project,
        product=product,
        plan=plan,
        status=ServiceOrder.Status.PENDING_APPROVAL if require_manual_approval else ServiceOrder.Status.PENDING_PAYMENT,
        payment_method=payment_method,
        base_amount=amounts['base_amount'],
        discount_amount=amounts['discount_amount'],
        tax_amount=amounts['tax_amount'],
        final_amount=amounts['final_amount'],
        remaining_amount=amounts['final_amount'],
        idempotency_key=idempotency_key or '',
        created_by=actor,
        meta={'note': note or ''},
    )

    subscription, _ = ServiceSubscription.objects.select_for_update().get_or_create(
        tenant=tenant,
        product=product,
        defaults={
            'project': product.project,
            'plan': plan,
            'status': ServiceSubscription.Status.PENDING_PAYMENT,
            'payment_status': ServiceSubscription.PaymentStatus.UNPAID,
            'base_amount': amounts['base_amount'],
            'discount_amount': amounts['discount_amount'],
            'tax_amount': amounts['tax_amount'],
            'final_amount': amounts['final_amount'],
            'remaining_amount': amounts['final_amount'],
            'cost_amount': product.default_cost,
            'usage_cap': plan.usage_cap,
            'usage_unit': plan.usage_unit,
            'purchased_at': timezone.now(),
            'idempotency_key': idempotency_key or '',
        },
    )
    order.subscription = subscription
    order.save(update_fields=['subscription', 'updated_at'])

    write_audit(
        tenant=tenant,
        action='order_created',
        actor=actor,
        subscription=subscription,
        order=order,
        before=subscription.status,
        after=subscription.status,
        financial=order.final_amount,
        payload={'order_code': order.order_code},
    )

    if require_manual_approval:
        subscription.status = ServiceSubscription.Status.PENDING_ACTIVATION
        subscription.save(update_fields=['status', 'updated_at'])
        return order

    if payment_method == ServiceOrder.PaymentMethod.WALLET:
        pay_order_from_wallet(order, actor=actor)
    elif payment_method == ServiceOrder.PaymentMethod.MANUAL_HQ:
        mark_order_paid(order, actor=actor, method=payment_method, tracking_code=f'HQ-{token_hex(4)}')

    if auto_activate and order.status == ServiceOrder.Status.PAID:
        activate_subscription_from_order(order, actor=actor)
    return order


@transaction.atomic
def pay_order_from_wallet(order, *, actor=None):
    wallet = ensure_main_wallet(order.tenant)
    wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
    amount = money(order.final_amount)
    if wallet.balance < amount:
        raise ValueError('موجودی کیف پول کافی نیست.')
    wallet.balance = money(wallet.balance) - amount
    wallet.save(update_fields=['balance', 'updated_at'])
    cashflow = CashflowTransaction.objects.create(
        tenant=order.tenant,
        wallet=wallet,
        direction=CashflowTransaction.Direction.OUT,
        amount=amount,
        description=f'خرید سرویس {order.product.title} / {order.order_code}',
        reference_type='service_order',
        reference_id=order.id,
        created_by=actor,
    )
    return mark_order_paid(
        order,
        actor=actor,
        method=ServiceOrder.PaymentMethod.WALLET,
        tracking_code=cashflow.id,
        cashflow=cashflow,
    )


@transaction.atomic
def mark_order_paid(order, *, actor=None, method='', tracking_code='', cashflow=None):
    order.status = ServiceOrder.Status.PAID
    order.paid_amount = order.final_amount
    order.remaining_amount = Decimal('0')
    order.paid_at = timezone.now()
    order.tracking_code = str(tracking_code or '')
    order.payment_method = method or order.payment_method
    order.save(update_fields=['status', 'paid_amount', 'remaining_amount', 'paid_at', 'tracking_code', 'payment_method', 'updated_at'])

    ServicePaymentRecord.objects.create(
        order=order,
        subscription=order.subscription,
        tenant=order.tenant,
        kind=ServicePaymentRecord.Kind.PURCHASE,
        amount=order.final_amount,
        tax_amount=order.tax_amount,
        discount_amount=order.discount_amount,
        method=order.payment_method,
        tracking_code=order.tracking_code,
        cashflow=cashflow,
        created_by=actor,
        idempotency_key=f'pay-order-{order.id}',
    )
    if order.subscription:
        sub = order.subscription
        sub.paid_amount = money(sub.paid_amount) + money(order.final_amount)
        sub.remaining_amount = max(Decimal('0'), money(sub.final_amount) - money(sub.paid_amount))
        sub.payment_status = ServiceSubscription.PaymentStatus.SETTLED if sub.remaining_amount <= 0 else ServiceSubscription.PaymentStatus.PARTIAL
        sub.last_paid_at = timezone.now()
        sub.save(update_fields=['paid_amount', 'remaining_amount', 'payment_status', 'last_paid_at', 'updated_at'])
    write_audit(
        tenant=order.tenant,
        action='order_paid',
        actor=actor,
        subscription=order.subscription,
        order=order,
        financial=order.final_amount,
        after='paid',
    )
    return order


@transaction.atomic
def activate_subscription_from_order(order, *, actor=None):
    subscription = order.subscription
    if not subscription:
        raise ValueError('سفارش به اشتراک متصل نیست.')
    plan = order.plan
    now = timezone.now()
    starts = now
    ends = None
    if plan and plan.duration_days:
        ends = now + timezone.timedelta(days=int(plan.duration_days))
    grace_days = subscription.product.grace_days_default or 7
    grace_ends = ends + timezone.timedelta(days=grace_days) if ends else None

    period = ServicePeriod.objects.create(
        subscription=subscription,
        plan=plan,
        kind=ServicePeriod.Kind.PURCHASE,
        starts_at=starts,
        ends_at=ends,
        base_amount=order.base_amount,
        discount_amount=order.discount_amount,
        tax_amount=order.tax_amount,
        final_amount=order.final_amount,
        paid_amount=order.paid_amount,
        cost_amount=subscription.product.default_cost,
        created_by=actor,
        note='فعالسازی پس از خرید',
    )
    before = subscription.status
    subscription.plan = plan
    subscription.status = ServiceSubscription.Status.ACTIVE
    subscription.activated_at = now
    subscription.starts_at = starts
    subscription.ends_at = ends
    subscription.grace_ends_at = grace_ends
    subscription.purchased_at = subscription.purchased_at or now
    subscription.usage_cap = plan.usage_cap if plan else subscription.usage_cap
    subscription.usage_unit = plan.usage_unit if plan else subscription.usage_unit
    subscription.base_amount = order.base_amount
    subscription.discount_amount = order.discount_amount
    subscription.tax_amount = order.tax_amount
    subscription.final_amount = order.final_amount
    subscription.save()
    sync_feature_purchase(subscription, activate=True)
    order.status = ServiceOrder.Status.ACTIVATED
    order.activated_at = now
    order.approved_by = actor
    order.approved_at = now
    order.save(update_fields=['status', 'activated_at', 'approved_by', 'approved_at', 'updated_at'])
    write_audit(
        tenant=order.tenant,
        action='activated',
        actor=actor,
        subscription=subscription,
        order=order,
        before=before,
        after=subscription.status,
        access='feature_enabled',
        payload={'period_id': period.id},
    )
    ServiceAlert.objects.filter(subscription=subscription, is_resolved=False).update(is_resolved=True, resolved_at=now)
    return subscription


@transaction.atomic
def renew_subscription(subscription, *, actor=None, plan=None, payment_method=ServiceOrder.PaymentMethod.WALLET, idempotency_key=''):
    plan = plan or subscription.plan
    if not plan:
        raise ValueError('پلن تمدید مشخص نیست.')
    order = create_order_and_activate(
        tenant=subscription.tenant,
        product=subscription.product,
        plan=plan,
        actor=actor,
        payment_method=payment_method,
        idempotency_key=idempotency_key or f'renew-{subscription.id}-{timezone.now().strftime("%Y%m%d")}',
        auto_activate=False,
        note='تمدید سرویس',
    )
    if order.status != ServiceOrder.Status.PAID:
        return order
    now = timezone.now()
    base_start = subscription.ends_at if subscription.ends_at and subscription.ends_at > now else now
    ends = base_start + timezone.timedelta(days=int(plan.duration_days or 0)) if plan.duration_days else None
    ServicePeriod.objects.create(
        subscription=subscription,
        plan=plan,
        kind=ServicePeriod.Kind.RENEWAL,
        starts_at=base_start,
        ends_at=ends,
        base_amount=order.base_amount,
        discount_amount=order.discount_amount,
        tax_amount=order.tax_amount,
        final_amount=order.final_amount,
        paid_amount=order.paid_amount,
        cost_amount=subscription.product.default_cost,
        created_by=actor,
        note='تمدید دوره جدید',
    )
    before = subscription.status
    subscription.plan = plan
    subscription.status = ServiceSubscription.Status.ACTIVE
    subscription.ends_at = ends
    subscription.grace_ends_at = ends + timezone.timedelta(days=subscription.product.grace_days_default or 7) if ends else None
    subscription.last_renewed_at = now
    subscription.save()
    sync_feature_purchase(subscription, activate=True)
    order.status = ServiceOrder.Status.ACTIVATED
    order.activated_at = now
    order.subscription = subscription
    order.save(update_fields=['status', 'activated_at', 'subscription', 'updated_at'])
    write_audit(
        tenant=subscription.tenant,
        action='renewed',
        actor=actor,
        subscription=subscription,
        order=order,
        before=before,
        after=subscription.status,
        financial=order.final_amount,
    )
    return order


@transaction.atomic
def apply_hq_action(subscription, *, action, actor, reason='', note='', payload=None):
    payload = payload or {}
    before = subscription.status
    financial = Decimal('0')
    access = ''

    if action == 'activate':
        subscription.status = ServiceSubscription.Status.ACTIVE
        if not subscription.activated_at:
            subscription.activated_at = timezone.now()
        sync_feature_purchase(subscription, activate=True)
        access = 'enabled'
    elif action == 'deactivate':
        subscription.status = ServiceSubscription.Status.INACTIVE
        sync_feature_purchase(subscription, activate=False)
        access = 'disabled'
    elif action == 'suspend':
        subscription.status = ServiceSubscription.Status.SUSPENDED
        sync_feature_purchase(subscription, activate=False)
        access = 'suspended'
    elif action == 'unsuspend':
        subscription.status = ServiceSubscription.Status.ACTIVE
        sync_feature_purchase(subscription, activate=True)
        access = 'enabled'
    elif action == 'block':
        subscription.status = ServiceSubscription.Status.BLOCKED
        sync_feature_purchase(subscription, activate=False)
        access = 'blocked'
    elif action == 'cancel':
        subscription.status = ServiceSubscription.Status.CANCELLED
        sync_feature_purchase(subscription, activate=False)
        access = 'cancelled'
    elif action == 'restore':
        subscription.status = ServiceSubscription.Status.ACTIVE
        sync_feature_purchase(subscription, activate=True)
        access = 'restored'
    elif action == 'extend_days':
        days = int(payload.get('days') or 0)
        if days and subscription.ends_at:
            subscription.ends_at = subscription.ends_at + timezone.timedelta(days=days)
            if subscription.grace_ends_at:
                subscription.grace_ends_at = subscription.grace_ends_at + timezone.timedelta(days=days)
    elif action == 'change_plan':
        plan_id = payload.get('plan_id')
        plan = ServicePlan.objects.filter(pk=plan_id, product=subscription.product, is_active=True).first()
        if not plan:
            raise ValueError('پلن معتبر نیست.')
        subscription.plan = plan
        amounts = plan.compute_amounts()
        subscription.base_amount = amounts['base_amount']
        subscription.discount_amount = amounts['discount_amount']
        subscription.tax_amount = amounts['tax_amount']
        subscription.final_amount = amounts['final_amount']
        subscription.usage_cap = plan.usage_cap
        subscription.usage_unit = plan.usage_unit
        ServicePeriod.objects.create(
            subscription=subscription,
            plan=plan,
            kind=ServicePeriod.Kind.PLAN_CHANGE,
            starts_at=timezone.now(),
            ends_at=subscription.ends_at,
            base_amount=amounts['base_amount'],
            discount_amount=amounts['discount_amount'],
            tax_amount=amounts['tax_amount'],
            final_amount=amounts['final_amount'],
            created_by=actor,
            note='تغییر پلن توسط HQ',
        )
    elif action == 'set_usage_cap':
        subscription.usage_cap = money(payload.get('usage_cap') or 0)
    elif action == 'apply_discount':
        discount = money(payload.get('discount_amount') or 0)
        subscription.discount_amount = discount
        totals = compute_totals(subscription.base_amount, discount, subscription.product.tax_percent)
        subscription.tax_amount = totals['tax_amount']
        subscription.final_amount = totals['final_amount']
        subscription.remaining_amount = max(Decimal('0'), totals['final_amount'] - money(subscription.paid_amount))
        financial = -discount
    elif action == 'forgive_debt':
        financial = -money(subscription.remaining_amount)
        subscription.remaining_amount = Decimal('0')
        subscription.payment_status = ServiceSubscription.PaymentStatus.SETTLED
    elif action == 'adjust_amount':
        subscription.final_amount = money(payload.get('final_amount') or subscription.final_amount)
        subscription.remaining_amount = max(Decimal('0'), money(subscription.final_amount) - money(subscription.paid_amount))
        financial = money(payload.get('final_amount') or 0)
    elif action == 'register_payment':
        amount = money(payload.get('amount') or 0)
        if amount <= 0:
            raise ValueError('مبلغ پرداخت نامعتبر است.')
        ServicePaymentRecord.objects.create(
            subscription=subscription,
            tenant=subscription.tenant,
            kind=ServicePaymentRecord.Kind.MANUAL,
            amount=amount,
            method=payload.get('method') or 'manual_hq',
            tracking_code=payload.get('tracking_code') or '',
            created_by=actor,
            note=note or 'ثبت پرداخت HQ',
            idempotency_key=payload.get('idempotency_key') or f'hq-pay-{subscription.id}-{token_hex(4)}',
        )
        subscription.paid_amount = money(subscription.paid_amount) + amount
        subscription.remaining_amount = max(Decimal('0'), money(subscription.final_amount) - money(subscription.paid_amount))
        subscription.payment_status = (
            ServiceSubscription.PaymentStatus.SETTLED
            if subscription.remaining_amount <= 0
            else ServiceSubscription.PaymentStatus.PARTIAL
        )
        subscription.last_paid_at = timezone.now()
        financial = amount
    elif action == 'free_activate':
        subscription.status = ServiceSubscription.Status.ACTIVE
        subscription.activated_at = timezone.now()
        subscription.starts_at = timezone.now()
        if payload.get('days'):
            subscription.ends_at = timezone.now() + timezone.timedelta(days=int(payload['days']))
        sync_feature_purchase(subscription, activate=True)
        access = 'free_enabled'
    else:
        raise ValueError('عملیات نامعتبر است.')

    subscription.save()
    write_audit(
        tenant=subscription.tenant,
        action=action,
        actor=actor,
        subscription=subscription,
        reason=reason,
        note=note,
        before=before,
        after=subscription.status,
        financial=financial,
        access=access,
        payload=payload,
    )
    return subscription


def seed_catalog_from_legacy():
    project, _ = PlatformProject.objects.get_or_create(
        code='carnowash',
        defaults={'name': 'کارنواش', 'sort_order': 1},
    )
    PlatformProject.objects.get_or_create(code='carnomanad', defaults={'name': 'کارنومند', 'sort_order': 2, 'is_active': False})
    PlatformProject.objects.get_or_create(code='carwashman', defaults={'name': 'کارواشمن', 'sort_order': 3, 'is_active': False})

    defaults = [
        (ServiceProduct.ProductKey.CORE_SOFTWARE, 'core_software', 'لایسنس اصلی نرم‌افزار', True, True, 1),
        (ServiceProduct.ProductKey.WALLET, '', 'کیف پول', True, False, 2),
        (ServiceProduct.ProductKey.ATTENDANCE, 'attendance', 'ورود و خروج', True, False, 3),
        (ServiceProduct.ProductKey.CLOUD_STORAGE, 'cloud_storage', 'فضای ابری', True, False, 4),
        (ServiceProduct.ProductKey.SMS_CLUB, 'sms_club', 'پنل پیشرفته مشتریان', True, False, 5),
        (ServiceProduct.ProductKey.SMS_PANEL, 'sms_club', 'پنل پیامک', True, False, 6),
        (ServiceProduct.ProductKey.SMS_CREDIT, '', 'بسته و اعتبار پیامک', True, False, 7),
        (ServiceProduct.ProductKey.ACCOUNTING, 'accounting', 'حسابداری', False, False, 8),
        (ServiceProduct.ProductKey.EXCEL_IMPORT, 'excel_import', 'ورود اکسل', True, False, 9),
        (ServiceProduct.ProductKey.CUSTOM_ADDON, '', 'افزونه اختصاصی', True, False, 10),
    ]
    for key, feature_key, title, available, required, order in defaults:
        product, _ = ServiceProduct.objects.update_or_create(
            project=project,
            product_key=key,
            defaults={
                'feature_key': feature_key,
                'title': title,
                'subtitle': FEATURE_OPTION_CATALOG.get(feature_key, {}).get('subtitle', ''),
                'description': FEATURE_OPTION_CATALOG.get(feature_key, {}).get('description', ''),
                'is_available': available and FEATURE_OPTION_CATALOG.get(feature_key, {}).get('is_available', True) if feature_key in FEATURE_OPTION_CATALOG else available,
                'is_required': required,
                'sort_order': order,
                'tax_percent': VAT_PERCENT,
                'grace_days_default': 7,
                'reminder_days_json': [30, 15, 7, 3, 1],
                'accent': FEATURE_OPTION_CATALOG.get(feature_key, {}).get('accent', '#0f172a'),
                'default_cost': money(FEATURE_OPTION_CATALOG.get(feature_key, {}).get('base_price', 0)) * Decimal('0.2'),
            },
        )
        legacy = FEATURE_OPTION_CATALOG.get(feature_key)
        if legacy:
            ServicePlan.objects.update_or_create(
                product=product,
                code='cash',
                defaults={
                    'title': 'نقدی',
                    'billing_cycle': ServicePlan.BillingCycle.CUSTOM,
                    'duration_days': 365,
                    'base_price': money(legacy.get('base_price')),
                    'tax_percent': VAT_PERCENT,
                    'is_active': legacy.get('is_available', True),
                    'sort_order': 1,
                    'renewal_terms': 'پرداخت یکجای نقدی',
                },
            )
            ServicePlan.objects.update_or_create(
                product=product,
                code='installment',
                defaults={
                    'title': 'اقساطی',
                    'billing_cycle': ServicePlan.BillingCycle.INSTALLMENT,
                    'duration_days': 365,
                    'base_price': money(legacy.get('base_price')),
                    'upfront_amount': money(legacy.get('upfront_amount')),
                    'installment_months': int(legacy.get('installment_months') or 0),
                    'monthly_installment_amount': money(legacy.get('monthly_installment_amount')),
                    'tax_percent': VAT_PERCENT,
                    'is_active': legacy.get('is_available', True) and not legacy.get('cash_only', False),
                    'sort_order': 2,
                    'renewal_terms': 'تمدید سالانه طبق تعرفه روز',
                },
            )
            if legacy.get('annual_renewal_amount'):
                ServicePlan.objects.update_or_create(
                    product=product,
                    code='annual',
                    defaults={
                        'title': 'سالانه',
                        'billing_cycle': ServicePlan.BillingCycle.ANNUAL,
                        'duration_days': 365,
                        'base_price': money(legacy.get('annual_renewal_amount')),
                        'tax_percent': VAT_PERCENT,
                        'is_active': True,
                        'sort_order': 3,
                    },
                )
        else:
            ServicePlan.objects.update_or_create(
                product=product,
                code='cash',
                defaults={
                    'title': 'نقدی',
                    'billing_cycle': ServicePlan.BillingCycle.CUSTOM,
                    'duration_days': 365,
                    'base_price': Decimal('0'),
                    'tax_percent': VAT_PERCENT,
                    'is_active': True,
                    'sort_order': 1,
                },
            )
            ServicePlan.objects.update_or_create(
                product=product,
                code='annual',
                defaults={
                    'title': 'سالانه',
                    'billing_cycle': ServicePlan.BillingCycle.ANNUAL,
                    'duration_days': 365,
                    'base_price': Decimal('0'),
                    'tax_percent': VAT_PERCENT,
                    'is_active': True,
                    'sort_order': 2,
                },
            )
        if key == ServiceProduct.ProductKey.WALLET:
            ServicePlan.objects.update_or_create(
                product=product,
                code='perpetual',
                defaults={
                    'title': 'دائمی',
                    'billing_cycle': ServicePlan.BillingCycle.PERPETUAL,
                    'duration_days': 0,
                    'base_price': Decimal('0'),
                    'tax_percent': Decimal('0'),
                    'is_active': True,
                    'sort_order': 1,
                },
            )
    return project


@transaction.atomic
def backfill_subscriptions_from_feature_purchases():
    project = seed_catalog_from_legacy()
    created = 0
    for purchase in CarWashFeaturePurchase.objects.select_related('tenant').all():
        product = ServiceProduct.objects.filter(project=project, feature_key=purchase.feature_key).first()
        if not product:
            product = ServiceProduct.objects.filter(project=project, product_key=purchase.feature_key).first()
        if not product:
            continue
        plan = resolve_plan_for_product(product, purchase)
        sub, was_created = ServiceSubscription.objects.get_or_create(
            tenant=purchase.tenant,
            product=product,
            defaults={
                'project': project,
                'plan': plan,
                'feature_purchase': purchase,
                'status': ServiceSubscription.Status.ACTIVE if purchase.is_active else ServiceSubscription.Status.INACTIVE,
                'payment_status': (
                    ServiceSubscription.PaymentStatus.SETTLED
                    if money(purchase.remaining_amount) <= 0
                    else ServiceSubscription.PaymentStatus.PARTIAL
                ),
                'purchased_at': purchase.purchased_at,
                'activated_at': purchase.purchased_at if purchase.is_active else None,
                'starts_at': purchase.purchased_at,
                'base_amount': money(purchase.total_amount),
                'final_amount': money(purchase.total_amount),
                'paid_amount': money(purchase.paid_amount),
                'remaining_amount': money(purchase.remaining_amount),
                'cost_amount': product.default_cost,
            },
        )
        if not was_created:
            correct_plan = resolve_plan_for_product(product, purchase)
            dirty = False
            if correct_plan and sub.plan_id != correct_plan.id:
                sub.plan = correct_plan
                dirty = True
            if sub.feature_purchase_id != purchase.id:
                sub.feature_purchase = purchase
                dirty = True
            expected_payment = (
                ServiceSubscription.PaymentStatus.SETTLED
                if money(purchase.remaining_amount) <= 0
                else ServiceSubscription.PaymentStatus.PARTIAL
            )
            if sub.payment_status != expected_payment:
                sub.payment_status = expected_payment
                dirty = True
            if money(sub.paid_amount) != money(purchase.paid_amount):
                sub.paid_amount = money(purchase.paid_amount)
                dirty = True
            if money(sub.remaining_amount) != money(purchase.remaining_amount):
                sub.remaining_amount = money(purchase.remaining_amount)
                dirty = True
            if money(sub.final_amount) != money(purchase.total_amount):
                sub.final_amount = money(purchase.total_amount)
                sub.base_amount = money(purchase.total_amount)
                dirty = True
            if dirty:
                sub.save()
        if was_created:
            created += 1
            if plan and purchase.is_active:
                ServicePeriod.objects.get_or_create(
                    subscription=sub,
                    kind=ServicePeriod.Kind.PURCHASE,
                    starts_at=purchase.purchased_at or timezone.now(),
                    defaults={
                        'plan': plan,
                        'ends_at': None,
                        'base_amount': money(purchase.total_amount),
                        'final_amount': money(purchase.total_amount),
                        'paid_amount': money(purchase.paid_amount),
                        'note': 'Backfill from legacy feature purchase',
                    },
                )
    return created


def summarize_subscriptions(queryset=None):
    qs = queryset if queryset is not None else ServiceSubscription.objects.all()
    now = timezone.now()
    near = now + timezone.timedelta(days=15)
    aggregates = qs.aggregate(
        clients=Count('tenant', distinct=True),
        active=Count('id', filter=Q(status=ServiceSubscription.Status.ACTIVE)),
        inactive=Count('id', filter=Q(status=ServiceSubscription.Status.INACTIVE)),
        expired=Count('id', filter=Q(status=ServiceSubscription.Status.EXPIRED)),
        near_expiry=Count('id', filter=Q(ends_at__gte=now, ends_at__lte=near) | Q(status=ServiceSubscription.Status.NEAR_EXPIRY)),
        blocked=Count('id', filter=Q(status=ServiceSubscription.Status.BLOCKED)),
        pending_payment=Count('id', filter=Q(status=ServiceSubscription.Status.PENDING_PAYMENT)),
        sales_total=Coalesce(Sum('final_amount'), Value(Decimal('0'))),
        paid_total=Coalesce(Sum('paid_amount'), Value(Decimal('0'))),
        renew_total=Coalesce(
            Sum('periods__final_amount', filter=Q(periods__kind=ServicePeriod.Kind.RENEWAL)),
            Value(Decimal('0')),
        ),
        tax_total=Coalesce(Sum('tax_amount'), Value(Decimal('0'))),
        discount_total=Coalesce(Sum('discount_amount'), Value(Decimal('0'))),
        receivables=Coalesce(Sum('remaining_amount'), Value(Decimal('0'))),
        overdue=Coalesce(
            Sum('remaining_amount', filter=Q(payment_status=ServiceSubscription.PaymentStatus.OVERDUE)),
            Value(Decimal('0')),
        ),
        carno_sales=Coalesce(
            Sum('final_amount', filter=Q(product__product_key__in=KARNO_PRODUCT_KEYS)),
            Value(Decimal('0')),
        ),
        carno_paid=Coalesce(
            Sum('paid_amount', filter=Q(product__product_key__in=KARNO_PRODUCT_KEYS)),
            Value(Decimal('0')),
        ),
        arakar_sales=Coalesce(
            Sum('final_amount', filter=Q(product__product_key__in=ARAKAR_PRODUCT_KEYS)),
            Value(Decimal('0')),
        ),
        arakar_paid=Coalesce(
            Sum('paid_amount', filter=Q(product__product_key__in=ARAKAR_PRODUCT_KEYS)),
            Value(Decimal('0')),
        ),
    )
    sales = money(aggregates['sales_total'])
    paid = money(aggregates['paid_total'])
    receivables = money(aggregates['receivables'])
    return {
        'clients_count': aggregates['clients'] or 0,
        'active_count': aggregates['active'] or 0,
        'inactive_count': aggregates['inactive'] or 0,
        'expired_count': aggregates['expired'] or 0,
        'near_expiry_count': aggregates['near_expiry'] or 0,
        'blocked_count': aggregates['blocked'] or 0,
        'pending_payment_count': aggregates['pending_payment'] or 0,
        'sales_revenue': float(sales),
        'paid_revenue': float(paid),
        'renewal_revenue': float(money(aggregates['renew_total'])),
        'tax_collected': float(money(aggregates['tax_total'])),
        'discount_total': float(money(aggregates['discount_total'])),
        'receivables': float(receivables),
        'overdue_total': float(money(aggregates['overdue'])),
        'carno_sales': float(money(aggregates['carno_sales'])),
        'carno_paid': float(money(aggregates['carno_paid'])),
        'arakar_sales': float(money(aggregates['arakar_sales'])),
        'arakar_paid': float(money(aggregates['arakar_paid'])),
        'installment_remaining': float(receivables),
    }


@transaction.atomic
def sync_subscription_from_feature_purchase(purchase, *, actor=None, cashflow=None, debit_amount=None):
    """Keep SaaS subscription history in sync with legacy feature purchase gate."""
    project = seed_catalog_from_legacy()
    product = ServiceProduct.objects.filter(project=project, feature_key=purchase.feature_key).first()
    if not product:
        product = ServiceProduct.objects.filter(project=project, product_key=purchase.feature_key).first()
    if not product:
        return None
    plan = resolve_plan_for_product(product, purchase)
    now = timezone.now()
    sub, created = ServiceSubscription.objects.select_for_update().get_or_create(
        tenant=purchase.tenant,
        product=product,
        defaults={
            'project': project,
            'plan': plan,
            'feature_purchase': purchase,
            'status': ServiceSubscription.Status.ACTIVE if purchase.is_active else ServiceSubscription.Status.INACTIVE,
            'payment_status': (
                ServiceSubscription.PaymentStatus.SETTLED
                if money(purchase.remaining_amount) <= 0
                else ServiceSubscription.PaymentStatus.PARTIAL
            ),
            'purchased_at': purchase.purchased_at or now,
            'activated_at': now if purchase.is_active else None,
            'starts_at': purchase.purchased_at or now,
            'base_amount': money(purchase.total_amount),
            'final_amount': money(purchase.total_amount),
            'paid_amount': money(purchase.paid_amount),
            'remaining_amount': money(purchase.remaining_amount),
            'cost_amount': product.default_cost,
        },
    )
    before = sub.status
    sub.feature_purchase = purchase
    sub.plan = plan or sub.plan
    sub.status = ServiceSubscription.Status.ACTIVE if purchase.is_active else ServiceSubscription.Status.INACTIVE
    sub.payment_status = (
        ServiceSubscription.PaymentStatus.SETTLED
        if money(purchase.remaining_amount) <= 0
        else ServiceSubscription.PaymentStatus.PARTIAL
    )
    sub.base_amount = money(purchase.total_amount)
    sub.final_amount = money(purchase.total_amount)
    sub.paid_amount = money(purchase.paid_amount)
    sub.remaining_amount = money(purchase.remaining_amount)
    sub.last_paid_at = now
    if purchase.is_active and not sub.activated_at:
        sub.activated_at = now
    if not sub.starts_at:
        sub.starts_at = purchase.purchased_at or now
    sub.save()

    amount = money(debit_amount if debit_amount is not None else purchase.paid_amount)
    if amount > 0:
        order = ServiceOrder.objects.create(
            order_code=make_order_code(),
            tenant=purchase.tenant,
            project=project,
            product=product,
            plan=plan,
            subscription=sub,
            status=ServiceOrder.Status.ACTIVATED,
            payment_method=(
                ServiceOrder.PaymentMethod.INSTALLMENT
                if purchase.payment_plan == CarWashFeaturePurchase.PaymentPlan.INSTALLMENT
                else ServiceOrder.PaymentMethod.WALLET
            ),
            base_amount=money(purchase.total_amount),
            final_amount=money(purchase.total_amount),
            paid_amount=amount,
            remaining_amount=money(purchase.remaining_amount),
            tracking_code=str(getattr(cashflow, 'id', '') or ''),
            paid_at=now,
            activated_at=now,
            created_by=actor,
            meta={'source': 'feature_purchase', 'purchase_id': purchase.id, 'payment_plan': purchase.payment_plan},
        )
        if created or not sub.periods.exists():
            period = ServicePeriod.objects.create(
                subscription=sub,
                plan=plan,
                kind=ServicePeriod.Kind.PURCHASE if created else ServicePeriod.Kind.RENEWAL,
                starts_at=sub.starts_at or now,
                ends_at=sub.ends_at,
                base_amount=money(purchase.total_amount),
                final_amount=money(purchase.total_amount),
                paid_amount=amount,
                cost_amount=product.default_cost,
                created_by=actor,
                note='Synced from wallet feature purchase',
            )
        else:
            period = sub.periods.order_by('-created_at').first()
        ServicePaymentRecord.objects.create(
            order=order,
            subscription=sub,
            period=period,
            tenant=purchase.tenant,
            kind=ServicePaymentRecord.Kind.PURCHASE if created else ServicePaymentRecord.Kind.INSTALLMENT,
            amount=amount,
            method='wallet',
            tracking_code=str(getattr(cashflow, 'id', '') or ''),
            cashflow=cashflow,
            created_by=actor,
            idempotency_key=f'feature-purchase-{purchase.id}-{getattr(cashflow, "id", token_hex(3))}',
        )
        write_audit(
            tenant=purchase.tenant,
            action='synced_from_feature_purchase',
            actor=actor,
            subscription=sub,
            order=order,
            before=before,
            after=sub.status,
            financial=amount,
            payload={'purchase_id': purchase.id, 'created': created},
        )
    return sub


@transaction.atomic
def process_bulk_job(job_id):
    job = BulkServiceJob.objects.select_for_update().get(pk=job_id)
    job.status = BulkServiceJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=['status', 'started_at', 'updated_at'])
    success = 0
    failure = 0
    for item in job.items.select_related('subscription', 'tenant').all():
        try:
            if job.action in {
                BulkServiceJob.Action.ACTIVATE,
                BulkServiceJob.Action.DEACTIVATE,
                BulkServiceJob.Action.RENEW,
                BulkServiceJob.Action.CHANGE_PLAN,
            }:
                if not item.subscription:
                    raise ValueError('اشتراک یافت نشد.')
                if job.action == BulkServiceJob.Action.ACTIVATE:
                    apply_hq_action(item.subscription, action='activate', actor=job.created_by, reason='bulk')
                elif job.action == BulkServiceJob.Action.DEACTIVATE:
                    apply_hq_action(item.subscription, action='deactivate', actor=job.created_by, reason='bulk')
                elif job.action == BulkServiceJob.Action.RENEW:
                    renew_subscription(item.subscription, actor=job.created_by, payment_method=ServiceOrder.PaymentMethod.MANUAL_HQ)
                elif job.action == BulkServiceJob.Action.CHANGE_PLAN:
                    apply_hq_action(
                        item.subscription,
                        action='change_plan',
                        actor=job.created_by,
                        reason='bulk',
                        payload=job.payload,
                    )
            elif job.action in {
                BulkServiceJob.Action.SMS_RENEWAL,
                BulkServiceJob.Action.SMS_DEBT,
                BulkServiceJob.Action.SMS_EXPIRY,
            }:
                ServiceAlert.objects.create(
                    tenant=item.tenant,
                    subscription=item.subscription,
                    code=f'bulk_{job.action}',
                    title='اعلان گروهی سرویس',
                    message=f'اعلان {job.action} برای {item.tenant.name} ثبت شد.',
                    severity=ServiceAlert.Severity.INFO,
                )
            elif job.action == BulkServiceJob.Action.ASSIGN_SUPPORT:
                if item.subscription and job.payload.get('support_owner_id'):
                    item.subscription.support_owner_id = job.payload.get('support_owner_id')
                    item.subscription.save(update_fields=['support_owner_id', 'updated_at'])
            elif job.action in {BulkServiceJob.Action.ADD_CREDIT, BulkServiceJob.Action.ADD_CLOUD}:
                if not item.subscription:
                    raise ValueError('اشتراک یافت نشد.')
                delta = money(job.payload.get('amount') or job.payload.get('usage_cap') or 0)
                item.subscription.usage_cap = money(item.subscription.usage_cap) + delta
                item.subscription.save(update_fields=['usage_cap', 'updated_at'])
            item.status = BulkServiceJobItem.Status.SUCCESS
            item.message = 'ok'
            success += 1
        except Exception as exc:
            item.status = BulkServiceJobItem.Status.FAILED
            item.message = str(exc)[:250]
            failure += 1
        item.save(update_fields=['status', 'message', 'updated_at'])
    job.success_count = success
    job.failure_count = failure
    job.status = BulkServiceJob.Status.COMPLETED
    job.finished_at = timezone.now()
    job.save(update_fields=['success_count', 'failure_count', 'status', 'finished_at', 'updated_at'])
    return job


def run_expiry_and_reminder_jobs():
    now = timezone.now()
    reminder_set = {1, 3, 7, 15, 30}
    for sub in ServiceSubscription.objects.select_related('product', 'tenant').exclude(
        status__in=[ServiceSubscription.Status.CANCELLED, ServiceSubscription.Status.BLOCKED]
    ):
        refresh_subscription_status(sub, now=now)
        if not sub.ends_at:
            continue
        days = (sub.ends_at.date() - now.date()).days
        if days in reminder_set:
            ServiceAlert.objects.get_or_create(
                tenant=sub.tenant,
                subscription=sub,
                code=f'near_expiry_{days}',
                is_resolved=False,
                defaults={
                    'title': f'سرویس نزدیک انقضا ({days} روز)',
                    'message': f'{sub.product.title} برای {sub.tenant.name} تا {days} روز دیگر منقضی می‌شود.',
                    'severity': ServiceAlert.Severity.WARNING if days > 7 else ServiceAlert.Severity.CRITICAL,
                },
            )
        if sub.status == ServiceSubscription.Status.EXPIRED:
            ServiceAlert.objects.get_or_create(
                tenant=sub.tenant,
                subscription=sub,
                code='expired',
                is_resolved=False,
                defaults={
                    'title': 'سرویس منقضی شد',
                    'message': f'{sub.product.title} برای {sub.tenant.name} منقضی شده است.',
                    'severity': ServiceAlert.Severity.CRITICAL,
                },
            )
        if sub.usage_cap and sub.usage_used >= sub.usage_cap:
            ServiceAlert.objects.get_or_create(
                tenant=sub.tenant,
                subscription=sub,
                code='usage_exceeded',
                is_resolved=False,
                defaults={
                    'title': 'عبور از سقف مصرف',
                    'message': f'{sub.product.title} از سقف مصرف عبور کرده است.',
                    'severity': ServiceAlert.Severity.CRITICAL,
                },
            )
