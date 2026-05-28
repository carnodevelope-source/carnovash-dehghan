from decimal import Decimal

from rest_framework import serializers

from apps.inventory.models import InventoryItem
from apps.products.models import Product, ProductCategory
from .models import (
    Account,
    JournalEntry,
    JournalEntryLine,
    Party,
    PurchaseInvoice,
    PurchaseInvoiceLine,
    SalesInvoice,
    SalesInvoiceLine,
)


class PartySerializer(serializers.ModelSerializer):
    class Meta:
        model = Party
        fields = [
            'id', 'name', 'party_type', 'mobile', 'phone', 'national_id', 'address',
            'is_active', 'created_at', 'updated_at',
        ]


class AccountSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True)

    class Meta:
        model = Account
        fields = [
            'id', 'code', 'name', 'nature', 'parent', 'parent_name',
            'is_active', 'created_at', 'updated_at',
        ]


class InventoryItemListSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='product.id', read_only=True)
    code = serializers.CharField(source='product.sku', read_only=True)
    name = serializers.CharField(source='product.name', read_only=True)
    unit = serializers.CharField(source='product.unit', read_only=True)
    buy_price = serializers.DecimalField(source='product.cost_price', max_digits=12, decimal_places=2, read_only=True)
    sell_price = serializers.DecimalField(source='product.sale_price', max_digits=12, decimal_places=2, read_only=True)
    quantity = serializers.DecimalField(source='quantity_on_hand', max_digits=12, decimal_places=2, read_only=True)
    category = serializers.CharField(source='product.category.name', read_only=True, allow_null=True)
    min_quantity = serializers.DecimalField(source='min_quantity_alert', max_digits=12, decimal_places=2, read_only=True)
    low_stock = serializers.SerializerMethodField()

    def get_low_stock(self, obj):
        return obj.quantity_on_hand <= obj.min_quantity_alert


class InventoryItemWriteSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=60)
    name = serializers.CharField(max_length=120)
    unit = serializers.CharField(max_length=20)
    buy_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    sell_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2)
    category = serializers.CharField(max_length=120, allow_blank=True, required=False, default='')
    min_quantity = serializers.DecimalField(max_digits=12, decimal_places=2)
    is_active = serializers.BooleanField(required=False, default=True)


class PurchaseInvoiceItemSerializer(serializers.ModelSerializer):
    item_id = serializers.IntegerField(source='product_id')
    item_name = serializers.CharField(source='product.name', read_only=True)
    unit = serializers.CharField(source='product.unit', read_only=True)
    current_quantity = serializers.DecimalField(source='product.inventory_item.quantity_on_hand', max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseInvoiceLine
        fields = [
            'id', 'item_id', 'item_name', 'unit', 'current_quantity',
            'quantity', 'unit_price', 'discount', 'tax', 'total', 'description',
        ]


class PurchaseInvoiceSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    items = PurchaseInvoiceItemSerializer(source='lines', many=True)

    class Meta:
        model = PurchaseInvoice
        fields = [
            'id', 'invoice_no', 'supplier', 'supplier_name', 'invoice_date', 'description',
            'subtotal', 'total_discount', 'total_tax', 'grand_total',
            'paid_amount', 'payment_type', 'remaining_amount', 'payment_status',
            'status', 'created_by', 'created_at', 'updated_at', 'items',
        ]


class PurchaseInvoiceItemWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    item_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    tax = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    description = serializers.CharField(required=False, allow_blank=True, default='')


class PurchaseInvoiceWriteSerializer(serializers.Serializer):
    factor_no = serializers.CharField(max_length=60)
    supplier_id = serializers.IntegerField()
    date = serializers.DateField()
    description = serializers.CharField(required=False, allow_blank=True, default='')
    payment_type = serializers.ChoiceField(choices=PurchaseInvoice.PaymentType.choices, default=PurchaseInvoice.PaymentType.CASH)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    items = PurchaseInvoiceItemWriteSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('حداقل یک ردیف لازم است.')
        return value


class SalesInvoiceItemSerializer(serializers.ModelSerializer):
    item_id = serializers.IntegerField(source='product_id')
    item_name = serializers.CharField(source='product.name', read_only=True)
    unit = serializers.CharField(source='product.unit', read_only=True)
    current_quantity = serializers.DecimalField(source='product.inventory_item.quantity_on_hand', max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = SalesInvoiceLine
        fields = [
            'id', 'item_id', 'item_name', 'unit', 'current_quantity',
            'quantity', 'unit_price', 'discount', 'tax', 'total', 'description',
        ]


class SalesInvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    items = SalesInvoiceItemSerializer(source='lines', many=True)

    class Meta:
        model = SalesInvoice
        fields = [
            'id', 'invoice_no', 'customer', 'customer_name', 'invoice_date', 'description',
            'subtotal', 'total_discount', 'total_tax', 'grand_total', 'paid_amount',
            'settlement_type', 'remaining_amount', 'payment_status', 'status',
            'created_by', 'created_at', 'updated_at', 'items',
        ]


class SalesInvoiceItemWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    item_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    tax = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    description = serializers.CharField(required=False, allow_blank=True, default='')


class SalesInvoiceWriteSerializer(serializers.Serializer):
    factor_no = serializers.CharField(max_length=60)
    customer_id = serializers.IntegerField()
    date = serializers.DateField()
    description = serializers.CharField(required=False, allow_blank=True, default='')
    settlement_type = serializers.ChoiceField(choices=SalesInvoice.SettlementType.choices)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    items = SalesInvoiceItemWriteSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('حداقل یک ردیف لازم است.')
        return value


class JournalEntryLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source='account.code', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    row_description = serializers.CharField(source='description')

    class Meta:
        model = JournalEntryLine
        fields = ['id', 'account', 'account_code', 'account_name', 'debit', 'credit', 'row_description']


class JournalEntrySerializer(serializers.ModelSerializer):
    date = serializers.DateField(source='entry_date')
    voucher_entries = JournalEntryLineSerializer(source='lines', many=True)
    total_debit = serializers.SerializerMethodField()
    total_credit = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'voucher_no', 'date', 'description', 'reference_type', 'reference_id',
            'status', 'created_by', 'created_at', 'updated_at',
            'total_debit', 'total_credit', 'voucher_entries',
        ]

    def get_total_debit(self, obj):
        return sum(Decimal(str(item.debit or 0)) for item in obj.lines.all())

    def get_total_credit(self, obj):
        return sum(Decimal(str(item.credit or 0)) for item in obj.lines.all())


class JournalEntryLineWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    account_id = serializers.IntegerField()
    debit = serializers.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    credit = serializers.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    row_description = serializers.CharField(required=False, allow_blank=True, default='')


class JournalEntryWriteSerializer(serializers.Serializer):
    voucher_no = serializers.CharField(max_length=60, required=False, allow_blank=True)
    date = serializers.DateField()
    description = serializers.CharField(required=False, allow_blank=True, default='')
    status = serializers.ChoiceField(choices=JournalEntry.Status.choices, default=JournalEntry.Status.DRAFT)
    voucher_entries = JournalEntryLineWriteSerializer(many=True)

    def validate_voucher_entries(self, value):
        if not value:
            raise serializers.ValidationError('حداقل یک ردیف لازم است.')
        debit = sum(Decimal(str(item['debit'])) for item in value)
        credit = sum(Decimal(str(item['credit'])) for item in value)
        if debit != credit:
            raise serializers.ValidationError('جمع بدهکار و بستانکار باید برابر باشد.')
        return value


class InventoryFilterOptionsSerializer(serializers.Serializer):
    categories = serializers.ListField(child=serializers.CharField())
    parties = PartySerializer(many=True)
    accounts = AccountSerializer(many=True)

