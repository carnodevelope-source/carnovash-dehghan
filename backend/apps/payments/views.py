from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CashflowTransaction, Wallet
from .serializers import (
    CashflowTransactionSerializer,
    WalletDepositSerializer,
    WalletSerializer,
    WalletWithdrawSerializer,
)


class WalletBaseMixin:
    def _get_or_create_default_wallet(self, tenant):
        wallet = Wallet.objects.filter(tenant=tenant, is_active=True).order_by('id').first()
        if wallet:
            return wallet
        return Wallet.objects.create(
            tenant=tenant,
            name='کیف پول اصلی',
            wallet_type=Wallet.WalletType.BANK,
            balance=0,
            is_active=True,
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
            total_balance=Coalesce(Sum('balance'), Value(Decimal('0')))
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
