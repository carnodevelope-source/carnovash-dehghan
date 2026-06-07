from decimal import Decimal

from secrets import token_urlsafe
from urllib.parse import quote_plus, unquote_plus

from django.db import transaction
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import redirect
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
    allowed_amounts = {Decimal('1000000'), Decimal('2000000'), Decimal('3000000')}

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
        if amount not in self.allowed_amounts:
            raise ValidationError({'amount': 'مبلغ باید ۱، ۲ یا ۳ میلیون تومان باشد.'})

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
