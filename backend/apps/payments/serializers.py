from rest_framework import serializers

from .models import CashflowTransaction, Wallet


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['id', 'name', 'wallet_type', 'balance', 'is_active']


class CashflowTransactionSerializer(serializers.ModelSerializer):
    wallet_name = serializers.CharField(source='wallet.name', read_only=True)

    class Meta:
        model = CashflowTransaction
        fields = [
            'id',
            'wallet',
            'wallet_name',
            'direction',
            'amount',
            'description',
            'reference_type',
            'reference_id',
            'transacted_at',
        ]


class WalletDepositSerializer(serializers.Serializer):
    wallet_id = serializers.IntegerField(required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)


class WalletWithdrawSerializer(serializers.Serializer):
    wallet_id = serializers.IntegerField(required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
