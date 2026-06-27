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
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CashflowTransaction, Wallet, WalletGatewayRequest
from .serializers import (
    CashflowTransactionSerializer,
    WalletDepositSerializer,
    WalletSerializer,
    WalletWithdrawSerializer,
)
from apps.auth.models import CarWashFeaturePurchase


FEATURE_OPTION_CATALOG = {
    CarWashFeaturePurchase.FeatureKey.ATTENDANCE: {
        'title': 'ورود و خروج',
        'subtitle': 'صف حضور و غیاب هوشمند پرسنل',
        'description': 'ثبت ورود و خروج، لینک اختصاصی پرسنل، صف نوبت‌دهی و گزارش کارکرد روزانه.',
        'base_price': Decimal('2400000'),
        'accent': '#0f766e',
    },
    CarWashFeaturePurchase.FeatureKey.ACCOUNTING: {
        'title': 'حسابداری',
        'subtitle': 'کنترل دقیق درآمد، هزینه و سهم‌ها',
        'description': 'گزارش مالی، سهم کارواش و نیرو، جریان نقدی، تخفیف‌ها و پایش دریافت‌ها.',
        'base_price': Decimal('3600000'),
        'accent': '#315f9f',
    },
    CarWashFeaturePurchase.FeatureKey.CLOUD_STORAGE: {
        'title': 'فضای ابری',
        'subtitle': 'نگهداری امن اطلاعات و فایل‌ها',
        'description': 'فضای اختصاصی برای فایل‌ها، رسیدها، سوابق مشتری و داده‌های عملیاتی کارواش.',
        'base_price': Decimal('3000000'),
        'accent': '#7c3aed',
    },
}


def _money(value):
    return Decimal(str(value or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _tenant_price_factor(tenant):
    tenant_id = int(getattr(tenant, 'id', 1) or 1)
    return Decimal('1') + (Decimal(str(tenant_id % 5)) * Decimal('0.03'))


def _feature_option_price(tenant, feature_key):
    config = FEATURE_OPTION_CATALOG[feature_key]
    return _money(config['base_price'] * _tenant_price_factor(tenant))


def _feature_option_payload(tenant, feature_key, purchase=None):
    config = FEATURE_OPTION_CATALOG[feature_key]
    total_amount = _feature_option_price(tenant, feature_key)
    upfront_amount = _money(total_amount * Decimal('0.25'))
    remaining_amount = _money(total_amount - upfront_amount)
    monthly_installment = _money(remaining_amount / Decimal('12'))
    is_active = bool(purchase and purchase.is_active)
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
        'payment_plan': purchase.payment_plan if purchase else '',
        'total_amount': total_amount,
        'cash_amount': total_amount,
        'installment_upfront_amount': upfront_amount,
        'installment_remaining_amount': remaining_amount,
        'installment_months': 12,
        'monthly_installment_amount': monthly_installment,
        'paid_amount': purchase.paid_amount if purchase else Decimal('0'),
        'remaining_amount': purchase.remaining_amount if purchase else Decimal('0'),
        'next_installment_due_at': purchase.next_installment_due_at if purchase else None,
    }


class WalletBaseMixin:
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

    def _resolve_wallet_for_update(self, wallet_id, tenant):
        wallet = None
        if wallet_id:
            wallet = (
                Wallet.objects.select_for_update()
                .filter(id=wallet_id, tenant=tenant, is_active=True)
                .first()
            )
        if wallet is not None:
            return wallet

        default_wallet = self._get_or_create_default_wallet(tenant)
        return Wallet.objects.select_for_update().get(id=default_wallet.id)


class WalletDashboardView(WalletBaseMixin, APIView):
    def get(self, request):
        tenant = getattr(request.user, 'tenant', None)
        self._get_or_create_default_wallet(tenant)
        self._get_or_create_sms_wallet(tenant)
        tx_type = str(request.query_params.get('type', 'all')).strip().lower()
        query = str(request.query_params.get('q', '')).strip()

        wallets = Wallet.objects.filter(tenant=tenant, is_active=True).order_by('id')
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
        totals = Wallet.objects.filter(tenant=tenant, is_active=True).aggregate(
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
                'wallets': WalletSerializer(wallets, many=True).data,
                'transactions': CashflowTransactionSerializer(transactions, many=True).data,
            }
        )


class WalletOptionsView(WalletBaseMixin, APIView):
    def get(self, request):
        tenant = getattr(request.user, 'tenant', None)
        if not tenant:
            return Response({'detail': 'کارواش کاربر مشخص نیست.'}, status=status.HTTP_400_BAD_REQUEST)
        self._get_or_create_default_wallet(tenant)
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
        payment_plan = str(request.data.get('payment_plan', '') or '').strip()
        wallet_id = request.data.get('wallet_id')
        if feature_key not in FEATURE_OPTION_CATALOG:
            return Response({'feature_key': ['آپشن انتخاب‌شده معتبر نیست.']}, status=status.HTTP_400_BAD_REQUEST)
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

        total_amount = _feature_option_price(tenant, feature_key)
        if payment_plan == CarWashFeaturePurchase.PaymentPlan.INSTALLMENT:
            try:
                debit_amount = _money(request.data.get('upfront_amount'))
            except Exception:
                return Response({'upfront_amount': ['مبلغ نقدی معتبر نیست.']}, status=status.HTTP_400_BAD_REQUEST)
            if debit_amount <= 0:
                return Response({'upfront_amount': ['مبلغ نقدی باید بزرگ‌تر از صفر باشد.']}, status=status.HTTP_400_BAD_REQUEST)
            if debit_amount >= total_amount:
                return Response({'upfront_amount': ['برای پرداخت قسطی، مبلغ نقدی باید کمتر از کل مبلغ باشد.']}, status=status.HTTP_400_BAD_REQUEST)
            installment_months = 12
            remaining_amount = _money(total_amount - debit_amount)
            monthly_installment = _money(remaining_amount / Decimal(str(installment_months)))
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
    def post(self, request):
        serializer = WalletWithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        amount = Decimal(str(data['amount']))
        description = (data.get('description') or '').strip() or 'برداشت از کیف پول'

        with transaction.atomic():
            tenant = getattr(request.user, 'tenant', None)
            wallet = self._resolve_wallet_for_update(data.get('wallet_id'), tenant)

            current_balance = Decimal(str(wallet.balance or 0))
            if current_balance < amount:
                raise ValidationError({'detail': 'موجودی کیف پول برای برداشت کافی نیست.'})

            wallet.balance = current_balance - amount
            wallet.save(update_fields=['balance', 'updated_at'])

            transaction_record = CashflowTransaction.objects.create(
                tenant=tenant,
                wallet=wallet,
                direction=CashflowTransaction.Direction.OUT,
                amount=amount,
                description=description,
                reference_type='wallet_withdraw',
                created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
            )

        return Response(
            {
                'detail': 'برداشت کیف پول با موفقیت ثبت شد.',
                'wallet': WalletSerializer(wallet).data,
                'transaction': CashflowTransactionSerializer(transaction_record).data,
            },
            status=status.HTTP_201_CREATED,
        )
