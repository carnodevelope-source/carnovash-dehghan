from decimal import Decimal

from datetime import timedelta
from decimal import ROUND_HALF_UP
from secrets import token_urlsafe
from urllib.parse import quote_plus, unquote_plus

from django.db import transaction
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CashflowTransaction, Wallet, WalletGatewayRequest
from .serializers import (
    CashflowTransactionSerializer,
    WalletDepositSerializer,
    WalletSerializer,
    WalletWithdrawSerializer,
)
from apps.auth.models import CarWashFeaturePurchase, SupportTicket, SupportTicketMessage


FEATURE_OPTION_CATALOG = {
    CarWashFeaturePurchase.FeatureKey.CORE_SOFTWARE: {
        'title': 'نرم‌افزار کارنوواش',
        'subtitle': 'فعال‌سازی اصلی نرم‌افزار',
        'description': 'دسترسی کامل به نرم‌افزار فقط بعد از خرید این مورد فعال می‌شود. بعد از پایان سال اول، اشتراک سالانه فعال می‌شود.',
        'base_price': Decimal('7000000'),
        'upfront_amount': Decimal('1000000'),
        'installment_months': 12,
        'monthly_installment_amount': Decimal('500000'),
        'annual_renewal_amount': Decimal('1500000'),
        'annual_renewal_installment_months': 3,
        'annual_renewal_monthly_amount': Decimal('500000'),
        'accent': '#0f172a',
        'is_required': True,
    },
    CarWashFeaturePurchase.FeatureKey.ATTENDANCE: {
        'title': 'ورود و خروج',
        'subtitle': 'صف حضور و غیاب هوشمند پرسنل',
        'description': 'ثبت ورود و خروج، لینک اختصاصی پرسنل، صف نوبت‌دهی و گزارش کارکرد روزانه.',
        'base_price': Decimal('3000000'),
        'upfront_amount': Decimal('1000000'),
        'installment_months': 4,
        'monthly_installment_amount': Decimal('500000'),
        'accent': '#0f766e',
    },
    CarWashFeaturePurchase.FeatureKey.SMS_CLUB: {
        'title': 'پنل باشگاه مشتریان پیشرفته',
        'subtitle': 'باشگاه مشتریان و پیامک حرفه‌ای',
        'description': 'پنل پیشرفته باشگاه مشتریان، قالب‌ها و امکانات پیامکی توسعه‌یافته.',
        'base_price': Decimal('3000000'),
        'upfront_amount': Decimal('1000000'),
        'installment_months': 4,
        'monthly_installment_amount': Decimal('500000'),
        'accent': '#db2777',
    },
    CarWashFeaturePurchase.FeatureKey.CLOUD_STORAGE: {
        'title': 'فضای ابری',
        'subtitle': 'نگهداری امن اطلاعات و فایل‌ها',
        'description': 'در حالت عادی داده‌ها ۳ ماه نگهداری می‌شوند؛ با خرید فضای ابری، داده‌ها دائمی نگهداری می‌شوند.',
        'base_price': Decimal('3000000'),
        'upfront_amount': Decimal('1000000'),
        'installment_months': 4,
        'monthly_installment_amount': Decimal('500000'),
        'accent': '#7c3aed',
    },
    CarWashFeaturePurchase.FeatureKey.ACCOUNTING: {
        'title': 'حسابداری',
        'subtitle': 'خدمات حسابداری و حسابرسی پیشرفته',
        'description': 'ثبت اسناد، هزینه‌ها، خرید و فروش، بدهکار و بستانکار و حسابرسی پیشرفته.',
        'base_price': Decimal('6000000'),
        'upfront_amount': Decimal('1000000'),
        'installment_months': 10,
        'monthly_installment_amount': Decimal('500000'),
        'accent': '#94a3b8',
        'is_available': False,
        'status_label': 'به‌زودی',
        'unavailable_message': 'صفحه حسابداری پیشرفته هنوز در حال توسعه است و فعلا قابل خرید یا فعال‌سازی نیست.',
    },
}

LICENSE_GRACE_DAYS = 7
INITIAL_SMS_CREDIT_AMOUNT = Decimal('5000')
INITIAL_SMS_CREDIT_REFERENCE = 'initial_sms_credit'


def _money(value):
    return Decimal(str(value or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def grant_initial_sms_credit(tenant, created_by=None):
    if tenant is None:
        return None
    if CashflowTransaction.objects.filter(
        tenant=tenant,
        reference_type=INITIAL_SMS_CREDIT_REFERENCE,
    ).exists():
        return Wallet.objects.filter(
            tenant=tenant,
            wallet_type=Wallet.WalletType.SMS,
            is_active=True,
        ).order_by('id').first()

    wallet = Wallet.objects.select_for_update().filter(
        tenant=tenant,
        wallet_type=Wallet.WalletType.SMS,
        is_active=True,
    ).order_by('id').first()
    if not wallet:
        wallet = Wallet.objects.create(
            tenant=tenant,
            name='کیف پول پیامک',
            wallet_type=Wallet.WalletType.SMS,
            balance=0,
            is_active=True,
        )

    wallet.balance = _money(wallet.balance + INITIAL_SMS_CREDIT_AMOUNT)
    wallet.save(update_fields=['balance', 'updated_at'])
    CashflowTransaction.objects.create(
        tenant=tenant,
        wallet=wallet,
        direction=CashflowTransaction.Direction.IN,
        amount=INITIAL_SMS_CREDIT_AMOUNT,
        description='شارژ اولیه پیامک کاربر جدید',
        reference_type=INITIAL_SMS_CREDIT_REFERENCE,
        created_by=created_by if getattr(created_by, 'is_authenticated', False) else None,
    )
    return wallet


def _feature_payment_plan_label(payment_plan):
    return {
        CarWashFeaturePurchase.PaymentPlan.MANUAL: 'ثبت مدیریتی',
        CarWashFeaturePurchase.PaymentPlan.CASH: 'نقدی',
        CarWashFeaturePurchase.PaymentPlan.INSTALLMENT: 'پرداخت قسطی',
    }.get(payment_plan or '', 'ثبت نشده')


def _feature_option_price(feature_key):
    config = FEATURE_OPTION_CATALOG[feature_key]
    return _money(config['base_price'])


def _feature_installment_terms(feature_key):
    config = FEATURE_OPTION_CATALOG[feature_key]
    total_amount = _feature_option_price(feature_key)
    upfront_amount = _money(config.get('upfront_amount', total_amount))
    if config.get('cash_only'):
        return total_amount, total_amount, Decimal('0'), 0, Decimal('0')
    installment_months = int(config.get('installment_months') or 0)
    monthly_installment = _money(config.get('monthly_installment_amount') or 0)
    remaining_amount = _money(total_amount - upfront_amount)
    if installment_months > 0 and monthly_installment <= 0:
        monthly_installment = _money(remaining_amount / Decimal(str(installment_months)))
    return total_amount, upfront_amount, remaining_amount, installment_months, monthly_installment


def license_status_for_tenant(tenant, now=None):
    if tenant is None:
        return {'is_locked': False, 'reason': '', 'notice': '', 'core_purchase_required': False}
    now = now or timezone.now()
    if tenant.is_trial_active(now):
        remaining_seconds = max(0, int((tenant.trial_ends_at - now).total_seconds()))
        return {
            'is_locked': False,
            'reason': 'trial_active',
            'notice': 'دسترسی رایگان ۲۴ ساعته به همه امکانات سامانه فعال است.',
            'core_purchase_required': False,
            'trial_active': True,
            'trial_started_at': tenant.trial_started_at,
            'trial_ends_at': tenant.trial_ends_at,
            'trial_remaining_seconds': remaining_seconds,
            'grace_days': LICENSE_GRACE_DAYS,
        }
    purchase = CarWashFeaturePurchase.objects.filter(
        tenant=tenant,
        feature_key=CarWashFeaturePurchase.FeatureKey.CORE_SOFTWARE,
        is_active=True,
    ).order_by('-id').first()
    if not purchase:
        return {
            'is_locked': True,
            'reason': 'core_purchase_required',
            'notice': 'برای استفاده از نرم‌افزار باید ابتدا خود نرم‌افزار کارنوواش خریداری شود.',
            'core_purchase_required': True,
            'grace_days': LICENSE_GRACE_DAYS,
        }
    next_due_at = purchase.next_installment_due_at
    if next_due_at and next_due_at <= now:
        overdue_days = max(0, (now.date() - timezone.localtime(next_due_at).date()).days)
        return {
            'is_locked': overdue_days > LICENSE_GRACE_DAYS,
            'reason': 'installment_overdue',
            'notice': f'سررسید پرداخت نرم‌افزار گذشته است. پس از {LICENSE_GRACE_DAYS} روز عدم پرداخت، دسترسی قفل می‌شود.',
            'core_purchase_required': False,
            'overdue_days': overdue_days,
            'grace_days': LICENSE_GRACE_DAYS,
            'next_due_at': next_due_at,
            'amount_due': purchase.monthly_installment_amount,
        }
    return {
        'is_locked': False,
        'reason': '',
        'notice': '',
        'core_purchase_required': False,
        'next_due_at': next_due_at,
        'amount_due': purchase.monthly_installment_amount if next_due_at else Decimal('0'),
        'grace_days': LICENSE_GRACE_DAYS,
    }


def feature_installment_status(purchase, now=None):
    now = now or timezone.now()
    if (
        purchase is None
        or not purchase.is_active
        or purchase.payment_plan != CarWashFeaturePurchase.PaymentPlan.INSTALLMENT
        or purchase.remaining_amount <= 0
        or not purchase.next_installment_due_at
    ):
        return {
            'is_due': False,
            'is_locked': False,
            'overdue_days': 0,
            'grace_days': LICENSE_GRACE_DAYS,
        }
    next_due_at = purchase.next_installment_due_at
    if next_due_at > now:
        return {
            'is_due': False,
            'is_locked': False,
            'overdue_days': 0,
            'grace_days': LICENSE_GRACE_DAYS,
            'next_due_at': next_due_at,
            'amount_due': purchase.monthly_installment_amount,
        }
    overdue_days = max(0, (now.date() - timezone.localtime(next_due_at).date()).days)
    feature_title = FEATURE_OPTION_CATALOG.get(purchase.feature_key, {}).get('title', 'آپشن نرم‌افزار')
    return {
        'is_due': True,
        'is_locked': overdue_days > LICENSE_GRACE_DAYS,
        'reason': 'installment_overdue',
        'notice': f'سررسید پرداخت {feature_title} گذشته است. پس از {LICENSE_GRACE_DAYS} روز عدم پرداخت، دسترسی این بخش قفل می‌شود.',
        'overdue_days': overdue_days,
        'grace_days': LICENSE_GRACE_DAYS,
        'next_due_at': next_due_at,
        'amount_due': purchase.monthly_installment_amount,
    }


def locked_feature_statuses_for_tenant(tenant, now=None):
    if tenant is None:
        return {}
    now = now or timezone.now()
    if tenant.is_trial_active(now):
        return {}
    statuses = {}
    purchases = CarWashFeaturePurchase.objects.filter(
        tenant=tenant,
        is_active=True,
        payment_plan=CarWashFeaturePurchase.PaymentPlan.INSTALLMENT,
        remaining_amount__gt=0,
        next_installment_due_at__isnull=False,
    )
    for purchase in purchases:
        status_info = feature_installment_status(purchase, now)
        if status_info.get('is_locked'):
            statuses[purchase.feature_key] = status_info
    return statuses


def _feature_option_payload(tenant, feature_key, purchase=None):
    config = FEATURE_OPTION_CATALOG[feature_key]
    is_available = config.get('is_available', True)
    if not is_available:
        purchase = None
    base_total_amount = _feature_option_price(feature_key)
    purchased_total_amount = _money(purchase.total_amount) if purchase else Decimal('0')
    total_amount = purchased_total_amount if purchased_total_amount > 0 else base_total_amount
    _base_total, default_upfront_amount, default_remaining_amount, default_installment_months, default_monthly_installment = _feature_installment_terms(feature_key)
    is_active = bool(purchase and purchase.is_active)
    payment_plan = purchase.payment_plan if purchase else ''
    paid_amount = _money(purchase.paid_amount if purchase else Decimal('0'))
    live_remaining_amount = _money(purchase.remaining_amount if purchase else Decimal('0'))
    installment_months = purchase.installment_months if purchase and purchase.installment_months else default_installment_months
    upfront_amount = (
        paid_amount
        if purchase and payment_plan == CarWashFeaturePurchase.PaymentPlan.INSTALLMENT
        else default_upfront_amount
    )
    remaining_amount = (
        live_remaining_amount
        if purchase and payment_plan == CarWashFeaturePurchase.PaymentPlan.INSTALLMENT
        else default_remaining_amount
    )
    monthly_installment = (
        _money(purchase.monthly_installment_amount)
        if purchase and payment_plan == CarWashFeaturePurchase.PaymentPlan.INSTALLMENT
        else default_monthly_installment
    )
    total_for_progress = max(total_amount, Decimal('1'))
    if purchase and is_active and total_amount <= 0:
        progress_percent = 100
    else:
        progress_percent = int((paid_amount / total_for_progress) * 100) if purchase and total_amount > 0 else 0
    progress_percent = max(0, min(progress_percent, 100))
    next_due_at = purchase.next_installment_due_at if purchase else None
    installment_status = feature_installment_status(purchase) if purchase else {}
    return {
        'feature_key': feature_key,
        'title': config['title'],
        'subtitle': config['subtitle'],
        'description': config['description'],
        'accent': config['accent'],
        'tenant_name': getattr(tenant, 'name', '') or '',
        'tenant_slug': getattr(tenant, 'slug', '') or '',
        'personalized_title': f"{config['title']} {getattr(tenant, 'name', '') or 'کارواش'}",
        'personalized_path': f"/manager/options/{getattr(tenant, 'slug', '') or getattr(tenant, 'id', '')}/{feature_key}",
        'is_active': is_active,
        'is_available': is_available,
        'has_purchase': bool(purchase),
        'status_label': (
            config.get('status_label')
            if not is_available
            else ('قفل شده' if installment_status.get('is_locked') else ('فعال شده' if is_active else 'قابل خرید'))
        ),
        'unavailable_message': config.get('unavailable_message', ''),
        'payment_plan': payment_plan,
        'payment_plan_label': _feature_payment_plan_label(payment_plan),
        'is_required': bool(config.get('is_required')),
        'cash_only': bool(config.get('cash_only')),
        'annual_renewal_amount': _money(config.get('annual_renewal_amount') or 0),
        'annual_renewal_installment_months': int(config.get('annual_renewal_installment_months') or 0),
        'annual_renewal_monthly_amount': _money(config.get('annual_renewal_monthly_amount') or 0),
        'grace_days': LICENSE_GRACE_DAYS,
        'total_amount': total_amount,
        'cash_amount': total_amount,
        'installment_upfront_amount': upfront_amount,
        'installment_remaining_amount': remaining_amount,
        'installment_months': installment_months,
        'monthly_installment_amount': monthly_installment,
        'paid_amount': paid_amount,
        'remaining_amount': live_remaining_amount,
        'live_monthly_installment_amount': monthly_installment,
        'progress_percent': progress_percent,
        'next_installment_due_at': next_due_at,
        'next_installment_amount': monthly_installment if next_due_at and live_remaining_amount > 0 else Decimal('0'),
        'installment_is_due': bool(installment_status.get('is_due')),
        'installment_is_locked': bool(installment_status.get('is_locked')),
        'installment_overdue_days': installment_status.get('overdue_days', 0),
        'installment_lock_notice': installment_status.get('notice', ''),
        'can_pay_next_installment': bool(
            purchase
            and purchase.is_active
            and payment_plan == CarWashFeaturePurchase.PaymentPlan.INSTALLMENT
            and live_remaining_amount > 0
        ),
        'auto_charge_enabled': bool(
            purchase
            and purchase.is_active
            and payment_plan == CarWashFeaturePurchase.PaymentPlan.INSTALLMENT
            and live_remaining_amount > 0
        ),
        'purchased_at': purchase.purchased_at if purchase else None,
    }


class WalletBaseMixin:
    wallet_deposit_roles = {'accountant', 'admin', 'owner', 'manager', 'operator'}
    wallet_withdraw_roles = {'admin', 'owner', 'manager'}

    def _require_wallet_deposit_access(self, user):
        if getattr(user, 'role', '') not in self.wallet_deposit_roles:
            raise PermissionDenied('شما دسترسی ثبت واریز کیف پول را ندارید.')

    def _require_wallet_withdraw_access(self, user):
        if getattr(user, 'role', '') not in self.wallet_withdraw_roles:
            raise PermissionDenied('برداشت از کیف پول فقط برای مدیران مجاز است.')

    def _get_or_create_wallet(self, tenant, wallet_type=Wallet.WalletType.BANK, default_name='کیف پول اصلی'):
        wallet = Wallet.objects.filter(
            tenant=tenant,
            wallet_type=wallet_type,
            is_active=True,
        ).order_by('id').first()
        if wallet:
            return wallet
        return Wallet.objects.create(
            tenant=tenant,
            name=default_name,
            wallet_type=wallet_type,
            balance=0,
            is_active=True,
        )

    def _get_or_create_default_wallet(self, tenant):
        return self._get_or_create_wallet(tenant)

    def _get_or_create_sms_wallet(self, tenant):
        return self._get_or_create_wallet(
            tenant,
            wallet_type=Wallet.WalletType.SMS,
            default_name='کیف پول پیامک',
        )

    def _ensure_single_wallets(self, tenant):
        default_wallet = self._get_or_create_default_wallet(tenant)
        sms_wallet = self._get_or_create_sms_wallet(tenant)
        canonical_wallets = [
            (Wallet.WalletType.BANK, default_wallet),
            (Wallet.WalletType.SMS, sms_wallet),
        ]
        for wallet_type, canonical in canonical_wallets:
            duplicate_wallets = list(
                Wallet.objects.select_for_update()
                .filter(tenant=tenant, wallet_type=wallet_type, is_active=True)
                .exclude(id=canonical.id)
                .order_by('id')
            )
            if not duplicate_wallets:
                continue
            transfer_total = sum((Decimal(str(wallet.balance or 0)) for wallet in duplicate_wallets), Decimal('0'))
            if transfer_total:
                canonical = Wallet.objects.select_for_update().get(id=canonical.id)
                canonical.balance = Decimal(str(canonical.balance or 0)) + transfer_total
                canonical.save(update_fields=['balance', 'updated_at'])
            Wallet.objects.filter(id__in=[wallet.id for wallet in duplicate_wallets]).update(is_active=False)
        return (
            Wallet.objects.select_for_update().get(id=default_wallet.id),
            Wallet.objects.select_for_update().get(id=sms_wallet.id),
        )

    def _resolve_wallet_for_update(self, wallet_id, tenant):
        default_wallet, sms_wallet = self._ensure_single_wallets(tenant)
        allowed_wallet_ids = {default_wallet.id, sms_wallet.id}
        wallet = None
        if wallet_id:
            wallet = (
                Wallet.objects.select_for_update()
                .filter(id=wallet_id, tenant=tenant, is_active=True, id__in=allowed_wallet_ids)
                .first()
            )
        if wallet is not None:
            return wallet

        return Wallet.objects.select_for_update().get(id=default_wallet.id)

    def _collect_due_installments(self, tenant, user=None):
        if tenant is None:
            return None
        wallet = self._get_or_create_default_wallet(tenant)
        wallet = Wallet.objects.select_for_update().get(id=wallet.id)
        now = timezone.now()
        purchases = list(
            CarWashFeaturePurchase.objects.select_for_update()
            .filter(
                tenant=tenant,
                is_active=True,
                payment_plan=CarWashFeaturePurchase.PaymentPlan.INSTALLMENT,
                remaining_amount__gt=0,
                next_installment_due_at__isnull=False,
                next_installment_due_at__lte=now,
            )
            .order_by('next_installment_due_at', 'id')
        )
        if not purchases:
            return wallet

        wallet_balance = _money(wallet.balance)
        for purchase in purchases:
            monthly_amount = _money(purchase.monthly_installment_amount)
            if monthly_amount <= 0:
                continue

            while purchase.next_installment_due_at and purchase.next_installment_due_at <= now:
                if purchase.remaining_amount <= 0:
                    purchase.remaining_amount = Decimal('0')
                    purchase.next_installment_due_at = None
                    break

                debit_amount = min(_money(purchase.remaining_amount), monthly_amount)
                if wallet_balance < debit_amount:
                    break

                wallet_balance = _money(wallet_balance - debit_amount)
                purchase.paid_amount = _money(purchase.paid_amount + debit_amount)
                purchase.remaining_amount = _money(purchase.remaining_amount - debit_amount)
                if purchase.remaining_amount <= 0:
                    purchase.remaining_amount = Decimal('0')
                    purchase.next_installment_due_at = None
                else:
                    purchase.next_installment_due_at = purchase.next_installment_due_at + timedelta(days=30)

                CashflowTransaction.objects.create(
                    tenant=tenant,
                    wallet=wallet,
                    direction=CashflowTransaction.Direction.OUT,
                    amount=debit_amount,
                    description=f"پرداخت قسط آپشن {FEATURE_OPTION_CATALOG[purchase.feature_key]['title']}",
                    reference_type='feature_option_installment',
                    reference_id=purchase.id,
                    created_by=user if getattr(user, 'is_authenticated', False) else None,
                )

            purchase.save(
                update_fields=[
                    'paid_amount',
                    'remaining_amount',
                    'next_installment_due_at',
                    'updated_at',
                ]
            )

        if _money(wallet.balance) != wallet_balance:
            wallet.balance = wallet_balance
            wallet.save(update_fields=['balance', 'updated_at'])
        return wallet

    def _pay_feature_installment(self, tenant, purchase, user=None):
        if tenant is None or purchase is None:
            raise ValidationError('درخواست پرداخت نامعتبر است.')
        if not purchase.is_active or purchase.payment_plan != CarWashFeaturePurchase.PaymentPlan.INSTALLMENT:
            raise ValidationError('برای این آپشن پرداخت قسطی فعالی ثبت نشده است.')
        if _money(purchase.remaining_amount) <= 0:
            raise ValidationError('مانده‌ای برای پرداخت این آپشن وجود ندارد.')

        wallet = self._get_or_create_default_wallet(tenant)
        wallet = Wallet.objects.select_for_update().get(id=wallet.id)
        installment_amount = min(
            _money(purchase.remaining_amount),
            _money(purchase.monthly_installment_amount),
        )
        if installment_amount <= 0:
            raise ValidationError('مبلغ قسط بعدی معتبر نیست.')

        wallet_balance = _money(wallet.balance)
        if wallet_balance < installment_amount:
            raise ValidationError('موجودی کیف پول اصلی برای پرداخت قسط بعدی کافی نیست.')

        wallet.balance = _money(wallet_balance - installment_amount)
        wallet.save(update_fields=['balance', 'updated_at'])

        purchase.paid_amount = _money(purchase.paid_amount + installment_amount)
        purchase.remaining_amount = _money(purchase.remaining_amount - installment_amount)
        if purchase.remaining_amount <= 0:
            purchase.remaining_amount = Decimal('0')
            purchase.next_installment_due_at = None
        else:
            base_due_at = purchase.next_installment_due_at or timezone.now()
            purchase.next_installment_due_at = max(base_due_at, timezone.now()) + timedelta(days=30)
        purchase.save(
            update_fields=[
                'paid_amount',
                'remaining_amount',
                'next_installment_due_at',
                'updated_at',
            ]
        )

        transaction_record = CashflowTransaction.objects.create(
            tenant=tenant,
            wallet=wallet,
            direction=CashflowTransaction.Direction.OUT,
            amount=installment_amount,
            description=f"پرداخت دستی قسط آپشن {FEATURE_OPTION_CATALOG[purchase.feature_key]['title']}",
            reference_type='feature_option_installment_manual',
            reference_id=purchase.id,
            created_by=user if getattr(user, 'is_authenticated', False) else None,
        )
        try:
            from apps.subscriptions.services import sync_subscription_from_feature_purchase

            sync_subscription_from_feature_purchase(
                purchase,
                actor=user if getattr(user, 'is_authenticated', False) else None,
                cashflow=transaction_record,
                debit_amount=installment_amount,
            )
        except Exception:
            pass
        return wallet, purchase, transaction_record, installment_amount


class WalletDashboardView(WalletBaseMixin, APIView):
    @transaction.atomic
    def get(self, request):
        tenant = getattr(request.user, 'tenant', None)
        default_wallet, sms_wallet = self._ensure_single_wallets(tenant)
        self._collect_due_installments(tenant, request.user)
        tx_type = str(request.query_params.get('type', 'all')).strip().lower()
        query = str(request.query_params.get('q', '')).strip()

        wallets = Wallet.objects.filter(tenant=tenant, is_active=True, id__in=[default_wallet.id, sms_wallet.id]).order_by('id')
        transactions = CashflowTransaction.objects.select_related('wallet').filter(tenant=tenant).order_by('-transacted_at')

        if tx_type in {'payments', 'withdraw', 'withdrawal', 'withdrawals'}:
            transactions = transactions.filter(direction=CashflowTransaction.Direction.OUT)
        elif tx_type in {'deposits', 'deposit'}:
            transactions = transactions.filter(direction=CashflowTransaction.Direction.IN)

        if query:
            transactions = transactions.filter(
                Q(description__icontains=query)
                | Q(wallet__name__icontains=query)
                | Q(reference_type__icontains=query)
            )

        transactions = transactions[:100]
        totals = Wallet.objects.filter(tenant=tenant, is_active=True, id__in=[default_wallet.id, sms_wallet.id]).aggregate(
            total_balance=Coalesce(Sum('balance'), Value(Decimal('0'))),
            regular_balance=Coalesce(
                Sum('balance', filter=~Q(wallet_type=Wallet.WalletType.SMS)),
                Value(Decimal('0')),
            ),
            sms_balance=Coalesce(
                Sum('balance', filter=Q(wallet_type=Wallet.WalletType.SMS)),
                Value(Decimal('0')),
            ),
        )
        tx_totals = CashflowTransaction.objects.filter(tenant=tenant).aggregate(
            deposits_total=Coalesce(
                Sum('amount', filter=Q(direction=CashflowTransaction.Direction.IN)),
                Value(Decimal('0')),
            ),
            payments_total=Coalesce(
                Sum('amount', filter=Q(direction=CashflowTransaction.Direction.OUT)),
                Value(Decimal('0')),
            ),
        )

        return Response(
            {
                'summary': {
                    'total_balance': totals['total_balance'],
                    'regular_balance': totals['regular_balance'],
                    'sms_balance': totals['sms_balance'],
                    'deposits_total': tx_totals['deposits_total'],
                    'payments_total': tx_totals['payments_total'],
                    'withdrawals_total': tx_totals['payments_total'],
                },
                'license_status': license_status_for_tenant(tenant),
                'wallets': WalletSerializer(wallets, many=True).data,
                'transactions': CashflowTransactionSerializer(transactions, many=True).data,
            }
        )


class WalletOptionsView(WalletBaseMixin, APIView):
    @transaction.atomic
    def get(self, request):
        tenant = getattr(request.user, 'tenant', None)
        if not tenant:
            return Response({'detail': 'کارواش کاربر مشخص نیست.'}, status=status.HTTP_400_BAD_REQUEST)
        self._collect_due_installments(tenant, request.user)
        purchases = {
            purchase.feature_key: purchase
            for purchase in CarWashFeaturePurchase.objects.filter(tenant=tenant)
        }
        wallet = self._get_or_create_default_wallet(tenant)
        return Response(
            {
                'tenant': {
                    'id': tenant.id,
                    'name': tenant.name,
                    'slug': tenant.slug,
                },
                'license_status': license_status_for_tenant(tenant),
                'wallet': WalletSerializer(wallet).data,
                'options': [
                    _feature_option_payload(tenant, feature_key, purchases.get(feature_key))
                    for feature_key in FEATURE_OPTION_CATALOG.keys()
                ],
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def post(self, request):
        tenant = getattr(request.user, 'tenant', None)
        if not tenant:
            return Response({'detail': 'کارواش کاربر مشخص نیست.'}, status=status.HTTP_400_BAD_REQUEST)

        feature_key = str(request.data.get('feature_key', '') or '').strip()
        action = str(request.data.get('action', '') or '').strip()
        payment_plan = str(request.data.get('payment_plan', '') or '').strip()
        wallet_id = request.data.get('wallet_id')
        if feature_key not in FEATURE_OPTION_CATALOG:
            return Response({'feature_key': ['آپشن انتخاب‌شده معتبر نیست.']}, status=status.HTTP_400_BAD_REQUEST)
        if not FEATURE_OPTION_CATALOG[feature_key].get('is_available', True):
            return Response({'detail': 'این آپشن در حال حاضر در دسترس نمی‌باشد.'}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'pay_installment':
            purchase = CarWashFeaturePurchase.objects.select_for_update().filter(
                tenant=tenant,
                feature_key=feature_key,
            ).first()
            if not purchase:
                return Response({'detail': 'خرید فعالی برای این آپشن پیدا نشد.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                wallet, purchase, transaction_record, installment_amount = self._pay_feature_installment(
                    tenant,
                    purchase,
                    request.user,
                )
            except ValidationError as exc:
                detail = exc.detail[0] if isinstance(exc.detail, list) else exc.detail
                return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)

            return Response(
                {
                    'detail': f'قسط بعدی به مبلغ {installment_amount} با موفقیت پرداخت شد.',
                    'wallet': WalletSerializer(wallet).data,
                    'option': _feature_option_payload(tenant, feature_key, purchase),
                    'transaction': CashflowTransactionSerializer(transaction_record).data,
                },
                status=status.HTTP_200_OK,
            )

        if payment_plan not in {
            CarWashFeaturePurchase.PaymentPlan.CASH,
            CarWashFeaturePurchase.PaymentPlan.INSTALLMENT,
        }:
            return Response({'payment_plan': ['شیوه پرداخت معتبر نیست.']}, status=status.HTTP_400_BAD_REQUEST)

        existing = CarWashFeaturePurchase.objects.select_for_update().filter(
            tenant=tenant,
            feature_key=feature_key,
            is_active=True,
        ).first()
        if existing:
            return Response({'detail': 'این آپشن قبلا برای این کارواش فعال شده است.'}, status=status.HTTP_400_BAD_REQUEST)

        wallet = self._resolve_wallet_for_update(wallet_id, tenant)
        if wallet.wallet_type == Wallet.WalletType.SMS:
            return Response({'wallet_id': ['خرید آپشن از کیف پول پیامک مجاز نیست.']}, status=status.HTTP_400_BAD_REQUEST)

        total_amount, configured_upfront_amount, configured_remaining_amount, configured_installment_months, configured_monthly_installment = _feature_installment_terms(feature_key)
        if payment_plan == CarWashFeaturePurchase.PaymentPlan.INSTALLMENT:
            if FEATURE_OPTION_CATALOG[feature_key].get('cash_only'):
                return Response({'payment_plan': ['این مورد فقط به صورت نقدی قابل پرداخت است.']}, status=status.HTTP_400_BAD_REQUEST)
            try:
                debit_amount = _money(request.data.get('upfront_amount') or configured_upfront_amount)
            except Exception:
                return Response({'upfront_amount': ['مبلغ نقدی معتبر نیست.']}, status=status.HTTP_400_BAD_REQUEST)
            if debit_amount != configured_upfront_amount:
                return Response({'upfront_amount': ['مبلغ نقدی باید مطابق پلن تعریف‌شده باشد.']}, status=status.HTTP_400_BAD_REQUEST)
            if configured_installment_months <= 0:
                return Response({'payment_plan': ['برای این مورد پلن قسطی تعریف نشده است.']}, status=status.HTTP_400_BAD_REQUEST)
            installment_months = configured_installment_months
            remaining_amount = _money(total_amount - debit_amount)
            monthly_installment = configured_monthly_installment or _money(remaining_amount / Decimal(str(installment_months)))
            next_due_at = timezone.now() + timedelta(days=30)
        else:
            debit_amount = total_amount
            installment_months = 0
            remaining_amount = Decimal('0')
            monthly_installment = Decimal('0')
            next_due_at = None

        current_balance = Decimal(str(wallet.balance or 0))
        if current_balance < debit_amount:
            return Response(
                {'detail': 'موجودی کیف پول برای خرید این آپشن کافی نیست.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        purchase, _created = CarWashFeaturePurchase.objects.select_for_update().get_or_create(
            tenant=tenant,
            feature_key=feature_key,
            defaults={'is_active': False},
        )
        purchase.is_active = True
        purchase.payment_plan = payment_plan
        purchase.total_amount = total_amount
        purchase.paid_amount = debit_amount
        purchase.remaining_amount = remaining_amount
        purchase.installment_months = installment_months
        purchase.monthly_installment_amount = monthly_installment
        purchase.next_installment_due_at = next_due_at
        purchase.save(
            update_fields=[
                'is_active',
                'payment_plan',
                'total_amount',
                'paid_amount',
                'remaining_amount',
                'installment_months',
                'monthly_installment_amount',
                'next_installment_due_at',
                'updated_at',
            ]
        )

        wallet.balance = current_balance - debit_amount
        wallet.save(update_fields=['balance', 'updated_at'])

        transaction_record = CashflowTransaction.objects.create(
            tenant=tenant,
            wallet=wallet,
            direction=CashflowTransaction.Direction.OUT,
            amount=debit_amount,
            description=f"خرید آپشن {FEATURE_OPTION_CATALOG[feature_key]['title']}",
            reference_type='feature_option_purchase',
            reference_id=purchase.id,
            created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
        )

        try:
            from apps.subscriptions.services import sync_subscription_from_feature_purchase

            sync_subscription_from_feature_purchase(
                purchase,
                actor=request.user if getattr(request.user, 'is_authenticated', False) else None,
                cashflow=transaction_record,
                debit_amount=debit_amount,
            )
        except Exception:
            pass

        return Response(
            {
                'detail': 'آپشن با موفقیت فعال شد.',
                'wallet': WalletSerializer(wallet).data,
                'option': _feature_option_payload(tenant, feature_key, purchase),
                'transaction': CashflowTransactionSerializer(transaction_record).data,
            },
            status=status.HTTP_201_CREATED,
        )


class WalletDepositView(WalletBaseMixin, APIView):
    def post(self, request):
        self._require_wallet_deposit_access(request.user)
        serializer = WalletDepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        amount = Decimal(str(data['amount']))
        description = (data.get('description') or '').strip() or 'شارژ کیف پول'

        with transaction.atomic():
            tenant = getattr(request.user, 'tenant', None)
            wallet = self._resolve_wallet_for_update(data.get('wallet_id'), tenant)

            wallet.balance = Decimal(str(wallet.balance or 0)) + amount
            wallet.save(update_fields=['balance', 'updated_at'])

            transaction_record = CashflowTransaction.objects.create(
                tenant=tenant,
                wallet=wallet,
                direction=CashflowTransaction.Direction.IN,
                amount=amount,
                description=description,
                reference_type='wallet_deposit',
                created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
            )

        return Response(
            {
                'detail': 'شارژ کیف پول با موفقیت ثبت شد.',
                'wallet': WalletSerializer(wallet).data,
                'transaction': CashflowTransactionSerializer(transaction_record).data,
            },
            status=status.HTTP_201_CREATED,
        )


class WalletDepositStartView(WalletBaseMixin, APIView):
    def post(self, request):
        self._require_wallet_deposit_access(request.user)
        serializer = WalletDepositSerializer(
            data={
                'wallet_id': request.data.get('wallet_id'),
                'amount': request.data.get('amount'),
                'description': request.data.get('description'),
            }
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return_url = str(request.data.get('return_url', '') or '').strip()

        amount = Decimal(str(data['amount']))

        tenant = getattr(request.user, 'tenant', None)
        wallet = self._resolve_wallet_for_update(data.get('wallet_id'), tenant)
        gateway_request = WalletGatewayRequest.objects.create(
            tenant=tenant,
            wallet=wallet,
            token=token_urlsafe(24),
            amount=amount,
            description=(data.get('description') or '').strip() or 'شارژ کیف پول از درگاه پرداخت',
            created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
        )

        return Response(
            {
                'detail': 'درخواست پرداخت ایجاد شد.',
                'payment_url': request.build_absolute_uri(
                    f'/api/payments/wallet/deposit/checkout/?token={gateway_request.token}&next={quote_plus(return_url)}'
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class WalletDepositCheckoutView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        token = str(request.query_params.get('token', '') or '').strip()
        confirm = str(request.query_params.get('confirm', '') or '').strip() == '1'
        next_url = unquote_plus(str(request.query_params.get('next', '') or '').strip()) or '/manager/wallet'
        gateway_request = WalletGatewayRequest.objects.select_related('wallet').filter(token=token).first()
        if not gateway_request:
            return HttpResponse('<h2 dir="rtl">درخواست پرداخت پیدا نشد.</h2>', status=404)

        if confirm:
            with transaction.atomic():
                locked_request = WalletGatewayRequest.objects.select_for_update().select_related('wallet').filter(id=gateway_request.id).first()
                if not locked_request:
                    return HttpResponse('<h2 dir="rtl">درخواست پرداخت پیدا نشد.</h2>', status=404)
                if locked_request.status != WalletGatewayRequest.Status.PENDING:
                    separator = '&' if '?' in next_url else '?'
                    return redirect(f'{next_url}{separator}gateway=already-processed')

                wallet = Wallet.objects.select_for_update().get(id=locked_request.wallet_id)
                wallet.balance = Decimal(str(wallet.balance or 0)) + Decimal(str(locked_request.amount or 0))
                wallet.save(update_fields=['balance', 'updated_at'])

                CashflowTransaction.objects.create(
                    tenant=locked_request.tenant,
                    wallet=wallet,
                    direction=CashflowTransaction.Direction.IN,
                    amount=locked_request.amount,
                    description=locked_request.description or 'شارژ کیف پول از درگاه پرداخت',
                    reference_type='wallet_gateway_deposit',
                    reference_id=locked_request.id,
                    created_by=locked_request.created_by,
                )

                locked_request.status = WalletGatewayRequest.Status.PAID
                locked_request.completed_at = wallet.updated_at
                locked_request.save(update_fields=['status', 'completed_at', 'updated_at'])

            separator = '&' if '?' in next_url else '?'
            return redirect(f'{next_url}{separator}gateway=success')

        amount_label = f"{int(gateway_request.amount):,}".replace(',', '،')
        confirm_url = f'/api/payments/wallet/deposit/checkout/?token={gateway_request.token}&confirm=1'
        cancel_separator = '&' if '?' in next_url else '?'
        cancel_url = f'{next_url}{cancel_separator}gateway=cancelled'
        html = f"""
<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>درگاه پرداخت کیف پول</title>
  <style>
    body{{font-family:tahoma,sans-serif;background:#f8fafc;margin:0;padding:24px;display:flex;justify-content:center}}
    .card{{width:min(460px,100%);background:#fff;border:1px solid #dbe5f0;border-radius:24px;padding:24px;box-shadow:0 24px 60px rgba(15,23,42,.12)}}
    h1{{margin:0 0 8px;color:#0f172a;font-size:22px}} p{{color:#475569;line-height:1.9}}
    .amount{{margin:18px 0;padding:16px;border-radius:18px;background:#eff6ff;color:#1d4ed8;font-weight:700;font-size:24px;text-align:center}}
    .actions{{display:grid;gap:10px;margin-top:18px}} a{{text-decoration:none;text-align:center;padding:14px 16px;border-radius:14px;font-weight:700}}
    .ok{{background:linear-gradient(135deg,#0f766e,#14b8a6);color:#fff}} .cancel{{background:#eef2f7;color:#334155}}
  </style>
</head>
<body>
  <section class="card">
    <h1>درگاه پرداخت کیف پول</h1>
    <p>برای شارژ <strong>{gateway_request.wallet.name}</strong> مبلغ زیر را تایید کنید.</p>
    <div class="amount">{amount_label} تومان</div>
    <p>{gateway_request.description or ''}</p>
    <div class="actions">
      <a class="ok" href="{confirm_url}&next={quote_plus(next_url)}">پرداخت و تکمیل شارژ</a>
      <a class="cancel" href="{cancel_url}">انصراف</a>
    </div>
  </section>
</body>
</html>
"""
        return HttpResponse(html)


class WalletWithdrawView(WalletBaseMixin, APIView):
    def _normalize_iban(self, value):
        normalized = str(value or '').replace(' ', '').replace('-', '').upper()
        if normalized and not normalized.startswith('IR'):
            normalized = f'IR{normalized}'
        return normalized

    def _create_bank_withdraw_ticket(self, *, tenant, user, source_wallet, amount, iban, holder, description):
        now = timezone.now()
        from apps.auth.models import SupportTicket, SupportTicketMessage
        from apps.auth.support_tickets import send_payment_ticket_sms_to_simple_supporters

        message = "\n".join([
            "wallet-bank-withdrawal",
            f"wallet_id: {source_wallet.id}",
            f"withdraw_amount: {amount}",
            f"iban: {iban}",
            f"account_holder: {holder or '-'}",
            f"wallet_name: {source_wallet.name}",
            f"tenant_id: {tenant.id if tenant else ''}",
            f"tenant_name: {tenant.name if tenant else ''}",
            f"description: {description or '-'}",
            f"wallet_debited: no",
            "",
            f"درخواست برداشت {amount:,.0f} تومان از کیف پول «{source_wallet.name}» به شماره شبا {iban} ثبت شد.",
            "مبلغ هنوز از کیف پول کم نشده است. بعد از واریز دستی به حساب بانکی، با دکمه تایید همین تیکت مبلغ از کیف پول کسر می‌شود.",
        ])
        ticket = SupportTicket.objects.create(
            tenant=tenant,
            created_by=user if getattr(user, 'is_authenticated', False) else None,
            subject='درخواست برداشت از کیف پول به حساب بانکی',
            message=message,
            category=SupportTicket.Category.FINANCIAL,
            priority=SupportTicket.Priority.URGENT,
            status=SupportTicket.Status.OPEN,
            assigned_to=None,
            last_message_at=now,
        )
        SupportTicketMessage.objects.create(
            ticket=ticket,
            sender=user if getattr(user, 'is_authenticated', False) else None,
            body=message,
        )
        ticket_id = ticket.id

        def _notify():
            try:
                fresher = SupportTicket.objects.filter(pk=ticket_id).first()
                if fresher:
                    send_payment_ticket_sms_to_simple_supporters(fresher)
            except Exception as exc:
                print(f'withdraw ticket sms failed: {exc}')

        transaction.on_commit(_notify)
        return ticket

    def post(self, request):
        self._require_wallet_withdraw_access(request.user)
        serializer = WalletWithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        amount = Decimal(str(data['amount']))
        destination_type = data.get('destination_type') or 'bank'
        description = (data.get('description') or '').strip()
        bank_account_iban = self._normalize_iban(data.get('bank_account_iban'))
        bank_account_holder = (data.get('bank_account_holder') or '').strip()

        with transaction.atomic():
            tenant = getattr(request.user, 'tenant', None)
            source_wallet = self._resolve_wallet_for_update(
                data.get('source_wallet_id') or data.get('wallet_id'),
                tenant,
            )

            current_balance = Decimal(str(source_wallet.balance or 0))
            if current_balance < amount:
                raise ValidationError({'detail': 'موجودی کیف پول برای برداشت کافی نیست.'})

            destination_wallet = None
            if destination_type == 'wallet':
                destination_wallet_id = data.get('destination_wallet_id')
                if not destination_wallet_id:
                    raise ValidationError({'destination_wallet_id': ['کیف پول مقصد را انتخاب کنید.']})
                if int(destination_wallet_id) == int(source_wallet.id):
                    raise ValidationError({'destination_wallet_id': ['کیف پول مقصد نمی‌تواند با مبدا یکی باشد.']})

                destination_wallet = (
                    Wallet.objects.select_for_update()
                    .filter(
                        id=destination_wallet_id,
                        tenant=tenant,
                        is_active=True,
                        wallet_type__in=[Wallet.WalletType.BANK, Wallet.WalletType.SMS],
                    )
                    .first()
                )
                if destination_wallet is None:
                    raise ValidationError({'destination_wallet_id': ['کیف پول مقصد معتبر نیست.']})

                source_wallet.balance = current_balance - amount
                source_wallet.save(update_fields=['balance', 'updated_at'])
                destination_wallet.balance = Decimal(str(destination_wallet.balance or 0)) + amount
                destination_wallet.save(update_fields=['balance', 'updated_at'])
            else:
                if not bank_account_iban or len(bank_account_iban) < 10:
                    raise ValidationError({'bank_account_iban': ['شماره شبا را برای برداشت بانکی وارد کنید.']})
                ticket = self._create_bank_withdraw_ticket(
                    tenant=tenant,
                    user=request.user,
                    source_wallet=source_wallet,
                    amount=amount,
                    iban=bank_account_iban,
                    holder=bank_account_holder,
                    description=description,
                )
                return Response(
                    {
                        'detail': 'درخواست برداشت ثبت شد و برای پشتیبانی تیکت ساخته شد. مبلغ بعد از تایید پشتیبانی از کیف پول کم می‌شود.',
                        'wallet': WalletSerializer(source_wallet).data,
                        'ticket': {
                            'id': ticket.id,
                            'subject': ticket.subject,
                            'status': str(ticket.status),
                            'is_wallet_bank_withdrawal': True,
                            'can_wallet_withdraw': True,
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )

            default_description = (
                f"انتقال به {destination_wallet.name}"
                if destination_wallet
                else 'برداشت به حساب بانکی'
            )
            transaction_description = description or default_description

            transaction_record = CashflowTransaction.objects.create(
                tenant=tenant,
                wallet=source_wallet,
                direction=CashflowTransaction.Direction.OUT,
                amount=amount,
                description=transaction_description,
                reference_type='wallet_transfer_out' if destination_wallet else 'wallet_withdraw',
                created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
            )
            destination_transaction = None
            if destination_wallet:
                destination_transaction = CashflowTransaction.objects.create(
                    tenant=tenant,
                    wallet=destination_wallet,
                    direction=CashflowTransaction.Direction.IN,
                    amount=amount,
                    description=description or f"انتقال از {source_wallet.name}",
                    reference_type='wallet_transfer_in',
                    reference_id=transaction_record.id,
                    created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
                )
                transaction_record.reference_id = destination_transaction.id
                transaction_record.save(update_fields=['reference_id', 'updated_at'])

        return Response(
            {
                'detail': 'انتقال کیف پول با موفقیت ثبت شد.' if destination_wallet else 'برداشت کیف پول با موفقیت ثبت شد.',
                'wallet': WalletSerializer(source_wallet).data,
                'destination_wallet': WalletSerializer(destination_wallet).data if destination_wallet else None,
                'transaction': CashflowTransactionSerializer(transaction_record).data,
            },
            status=status.HTTP_201_CREATED,
        )
