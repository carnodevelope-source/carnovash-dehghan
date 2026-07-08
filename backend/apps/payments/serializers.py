from rest_framework import serializers

from .models import CashflowTransaction, Payment, Wallet


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


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id',
            'vehicle_entry',
            'method',
            'status',
            'amount',
            'tip_amount',
            'service_amount',
            'product_amount',
            'discount_amount',
            'tax_amount',
            'paid_at',
            'payer_name',
            'payer_phone',
            'cheque_number',
            'cheque_serial_number',
            'cheque_sayadi_number',
            'cheque_bank',
            'cheque_shaba',
            'cheque_amount',
            'reminder_due_at',
            'reminder_sent_at',
        ]


class WalletDepositSerializer(serializers.Serializer):
    wallet_id = serializers.IntegerField(required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)


class WalletWithdrawSerializer(serializers.Serializer):
    wallet_id = serializers.IntegerField(required=False)
    source_wallet_id = serializers.IntegerField(required=False)
    destination_type = serializers.ChoiceField(
        choices=[('bank', 'Bank'), ('wallet', 'Wallet')],
        required=False,
        default='bank',
    )
    destination_wallet_id = serializers.IntegerField(required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
