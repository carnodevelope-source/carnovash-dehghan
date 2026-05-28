from decimal import Decimal

from django.db import transaction
from django.db.models import F, Prefetch, Q
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.models import InventoryItem, StockMovement
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
from .serializers import (
    AccountSerializer,
    InventoryFilterOptionsSerializer,
    InventoryItemListSerializer,
    InventoryItemWriteSerializer,
    JournalEntrySerializer,
    JournalEntryWriteSerializer,
    PartySerializer,
    PurchaseInvoiceSerializer,
    PurchaseInvoiceWriteSerializer,
    SalesInvoiceSerializer,
    SalesInvoiceWriteSerializer,
)


class IsAccountingRole(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and getattr(user, 'role', None) in {'accountant', 'admin', 'manager'}
        )


def paginate(request, queryset):
    page = max(1, int(request.query_params.get('page', 1) or 1))
    page_size = max(1, min(100, int(request.query_params.get('page_size', 20) or 20)))
    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    return queryset[start:end], {'page': page, 'page_size': page_size, 'total': total}


def next_voucher_no():
    prefix = timezone.localdate().strftime('%Y%m')
    count = JournalEntry.objects.filter(voucher_no__startswith=prefix).count() + 1
    return f'{prefix}-{count:05d}'


def resolve_payment_status(grand_total, paid_amount):
    if paid_amount <= 0:
        return 'unpaid'
    if paid_amount >= grand_total:
        return 'paid'
    return 'partial'


def get_account_by_code(code):
    return Account.objects.get(code=code)


def build_invoice_totals(items):
    subtotal = Decimal('0')
    total_discount = Decimal('0')
    total_tax = Decimal('0')
    for item in items:
        subtotal += Decimal(str(item['quantity'])) * Decimal(str(item['unit_price']))
        total_discount += Decimal(str(item['discount']))
        total_tax += Decimal(str(item['tax']))
    grand_total = subtotal - total_discount + total_tax
    return subtotal, total_discount, total_tax, grand_total


def create_voucher(*, date, description, reference_type, reference_id, lines, user, status_value=JournalEntry.Status.POSTED, voucher_no=''):
    voucher = JournalEntry.objects.create(
        voucher_no=voucher_no or next_voucher_no(),
        entry_date=date,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
        status=status_value,
        created_by=user,
    )
    debit_total = Decimal('0')
    credit_total = Decimal('0')
    entries = []
    for line in lines:
        debit = Decimal(str(line['debit']))
        credit = Decimal(str(line['credit']))
        debit_total += debit
        credit_total += credit
        entries.append(
            JournalEntryLine(
                journal_entry=voucher,
                account_id=line['account_id'],
                debit=debit,
                credit=credit,
                description=line.get('row_description', ''),
            )
        )
    if debit_total != credit_total:
        raise ValueError('جمع بدهکار و بستانکار باید برابر باشد.')
    JournalEntryLine.objects.bulk_create(entries)
    return voucher


class InventoryListCreateView(APIView):
    permission_classes = [IsAccountingRole]

    def get(self, request):
        queryset = InventoryItem.objects.select_related('product', 'product__category').order_by('product__name')
        search = request.query_params.get('search', '').strip()
        category = request.query_params.get('category', '').strip()
        low_stock = request.query_params.get('low_stock', '').strip()
        if search:
            queryset = queryset.filter(Q(product__name__icontains=search) | Q(product__sku__icontains=search))
        if category:
            queryset = queryset.filter(product__category__name__icontains=category)
        if low_stock in {'1', 'true'}:
            queryset = queryset.filter(quantity_on_hand__lte=F('min_quantity_alert'))
        page_items, meta = paginate(request, queryset)
        return Response({'results': InventoryItemListSerializer(page_items, many=True).data, **meta})

    @transaction.atomic
    def post(self, request):
        serializer = InventoryItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        category_name = data.get('category', '').strip()
        category = None
        if category_name:
            category, _ = ProductCategory.objects.get_or_create(
                slug=category_name.replace(' ', '-').lower(),
                defaults={'name': category_name},
            )
        product = Product.objects.create(
            sku=data['code'],
            name=data['name'],
            unit=data['unit'],
            cost_price=data['buy_price'],
            sale_price=data['sell_price'],
            min_stock=int(data['min_quantity']),
            is_active=data['is_active'],
            category=category,
            created_by=request.user,
        )
        inventory = InventoryItem.objects.create(
            product=product,
            quantity_on_hand=data['quantity'],
            min_quantity_alert=data['min_quantity'],
        )
        return Response(InventoryItemListSerializer(inventory).data, status=status.HTTP_201_CREATED)


class InventoryDetailView(APIView):
    permission_classes = [IsAccountingRole]

    def get_object(self, pk):
        return InventoryItem.objects.select_related('product', 'product__category').get(product_id=pk)

    def get(self, request, pk):
        return Response(InventoryItemListSerializer(self.get_object(pk)).data)

    @transaction.atomic
    def put(self, request, pk):
        inventory = self.get_object(pk)
        serializer = InventoryItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        category_name = data.get('category', '').strip()
        category = None
        if category_name:
            category, _ = ProductCategory.objects.get_or_create(
                slug=category_name.replace(' ', '-').lower(),
                defaults={'name': category_name},
            )
        product = inventory.product
        product.sku = data['code']
        product.name = data['name']
        product.unit = data['unit']
        product.cost_price = data['buy_price']
        product.sale_price = data['sell_price']
        product.min_stock = int(data['min_quantity'])
        product.is_active = data['is_active']
        product.category = category
        product.save()
        inventory.quantity_on_hand = data['quantity']
        inventory.min_quantity_alert = data['min_quantity']
        inventory.save()
        return Response(InventoryItemListSerializer(inventory).data)

    def delete(self, request, pk):
        inventory = self.get_object(pk)
        inventory.product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PartyListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAccountingRole]
    serializer_class = PartySerializer

    def get_queryset(self):
        queryset = Party.objects.order_by('name')
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(mobile__icontains=search) | Q(phone__icontains=search))
        return queryset


class PartyDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAccountingRole]
    serializer_class = PartySerializer
    queryset = Party.objects.order_by('name')


class AccountListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAccountingRole]
    serializer_class = AccountSerializer

    def get_queryset(self):
        queryset = Account.objects.select_related('parent').order_by('code')
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(Q(code__icontains=search) | Q(name__icontains=search))
        return queryset


class AccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAccountingRole]
    serializer_class = AccountSerializer
    queryset = Account.objects.select_related('parent').order_by('code')


class PurchaseListCreateView(APIView):
    permission_classes = [IsAccountingRole]

    def get(self, request):
        queryset = PurchaseInvoice.objects.select_related('supplier').prefetch_related('lines__product').order_by('-invoice_date', '-id')
        search = request.query_params.get('search', '').strip()
        status_value = request.query_params.get('status', '').strip()
        supplier_id = request.query_params.get('supplier', '').strip()
        if search:
            queryset = queryset.filter(Q(invoice_no__icontains=search) | Q(description__icontains=search))
        if status_value:
            queryset = queryset.filter(status=status_value)
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        page_items, meta = paginate(request, queryset)
        return Response({'results': PurchaseInvoiceSerializer(page_items, many=True).data, **meta})

    @transaction.atomic
    def post(self, request):
        serializer = PurchaseInvoiceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        subtotal, total_discount, total_tax, grand_total = build_invoice_totals(data['items'])
        paid_amount = Decimal(str(data['paid_amount']))
        invoice = PurchaseInvoice.objects.create(
            invoice_no=data['factor_no'],
            supplier_id=data['supplier_id'],
            invoice_date=data['date'],
            description=data['description'],
            subtotal=subtotal,
            total_discount=total_discount,
            total_tax=total_tax,
            grand_total=grand_total,
            paid_amount=paid_amount,
            payment_type=data['payment_type'],
            remaining_amount=max(Decimal('0'), grand_total - paid_amount),
            payment_status=resolve_payment_status(grand_total, paid_amount),
            status=PurchaseInvoice.Status.DRAFT,
            created_by=request.user,
        )
        self._save_items(invoice, data['items'])
        return Response(PurchaseInvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)

    def _save_items(self, invoice, items):
        lines = []
        products = {item.id: item for item in Product.objects.filter(id__in=[row['item_id'] for row in items])}
        for row in items:
            total = (Decimal(str(row['quantity'])) * Decimal(str(row['unit_price']))) - Decimal(str(row['discount'])) + Decimal(str(row['tax']))
            lines.append(
                PurchaseInvoiceLine(
                    purchase_invoice=invoice,
                    product=products[row['item_id']],
                    quantity=row['quantity'],
                    unit_price=row['unit_price'],
                    discount=row['discount'],
                    tax=row['tax'],
                    total=total,
                    description=row['description'],
                )
            )
        PurchaseInvoiceLine.objects.bulk_create(lines)


class PurchaseDetailView(APIView):
    permission_classes = [IsAccountingRole]

    def get_object(self, pk):
        return PurchaseInvoice.objects.select_related('supplier').prefetch_related('lines__product').get(pk=pk)

    def get(self, request, pk):
        return Response(PurchaseInvoiceSerializer(self.get_object(pk)).data)

    @transaction.atomic
    def put(self, request, pk):
        invoice = self.get_object(pk)
        if invoice.status != PurchaseInvoice.Status.DRAFT:
            return Response({'detail': 'فقط فاکتور draft قابل ویرایش است.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = PurchaseInvoiceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        subtotal, total_discount, total_tax, grand_total = build_invoice_totals(data['items'])
        paid_amount = Decimal(str(data['paid_amount']))
        invoice.invoice_no = data['factor_no']
        invoice.supplier_id = data['supplier_id']
        invoice.invoice_date = data['date']
        invoice.description = data['description']
        invoice.subtotal = subtotal
        invoice.total_discount = total_discount
        invoice.total_tax = total_tax
        invoice.grand_total = grand_total
        invoice.paid_amount = paid_amount
        invoice.payment_type = data['payment_type']
        invoice.remaining_amount = max(Decimal('0'), grand_total - paid_amount)
        invoice.payment_status = resolve_payment_status(grand_total, paid_amount)
        invoice.save()
        invoice.lines.all().delete()
        PurchaseListCreateView()._save_items(invoice, data['items'])
        return Response(PurchaseInvoiceSerializer(invoice).data)

    def delete(self, request, pk):
        invoice = self.get_object(pk)
        if invoice.status != PurchaseInvoice.Status.DRAFT:
            return Response({'detail': 'فقط فاکتور draft قابل حذف است.'}, status=status.HTTP_400_BAD_REQUEST)
        invoice.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PurchaseConfirmView(APIView):
    permission_classes = [IsAccountingRole]

    @transaction.atomic
    def post(self, request, pk):
        invoice = PurchaseInvoice.objects.select_for_update().prefetch_related('lines__product').get(pk=pk)
        if invoice.status != PurchaseInvoice.Status.DRAFT:
            return Response({'detail': 'فاکتور قبلاً تعیین تکلیف شده است.'}, status=status.HTTP_400_BAD_REQUEST)
        for line in invoice.lines.select_related('product'):
            product = line.product
            product.cost_price = line.unit_price
            product.save(update_fields=['cost_price', 'updated_at'])
            inventory, _ = InventoryItem.objects.get_or_create(product=product)
            inventory.quantity_on_hand += line.quantity
            inventory.min_quantity_alert = max(inventory.min_quantity_alert, Decimal(str(product.min_stock or 0)))
            inventory.save()
            StockMovement.objects.create(
                inventory_item=inventory,
                movement_type=StockMovement.MovementType.IN,
                quantity=line.quantity,
                unit_cost=line.unit_price,
                reference_type='purchase_invoice',
                reference_id=invoice.id,
                note=f'Purchase invoice {invoice.invoice_no}',
                created_by=request.user,
            )
        lines = []
        if invoice.paid_amount > 0:
            account_code = '1101' if invoice.payment_type == PurchaseInvoice.PaymentType.CASH else '1102'
            lines.append({'account_id': get_account_by_code(account_code).id, 'debit': 0, 'credit': invoice.paid_amount, 'row_description': 'پرداخت'})
        if invoice.remaining_amount > 0:
            lines.append({'account_id': get_account_by_code('2101').id, 'debit': 0, 'credit': invoice.remaining_amount, 'row_description': 'بدهی تامین کننده'})
        lines.insert(0, {'account_id': get_account_by_code('1501').id, 'debit': invoice.grand_total, 'credit': 0, 'row_description': 'موجودی کالا'})
        create_voucher(
            date=invoice.invoice_date,
            description=f'سند خودکار خرید {invoice.invoice_no}',
            reference_type='purchase_invoice',
            reference_id=invoice.id,
            lines=lines,
            user=request.user,
        )
        invoice.status = PurchaseInvoice.Status.CONFIRMED
        invoice.save(update_fields=['status', 'updated_at'])
        return Response(PurchaseInvoiceSerializer(invoice).data)


class SalesListCreateView(APIView):
    permission_classes = [IsAccountingRole]

    def get(self, request):
        queryset = SalesInvoice.objects.select_related('customer').prefetch_related('lines__product').order_by('-invoice_date', '-id')
        search = request.query_params.get('search', '').strip()
        status_value = request.query_params.get('status', '').strip()
        customer_id = request.query_params.get('customer', '').strip()
        settlement_type = request.query_params.get('settlement_type', '').strip()
        if search:
            queryset = queryset.filter(Q(invoice_no__icontains=search) | Q(description__icontains=search))
        if status_value:
            queryset = queryset.filter(status=status_value)
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        if settlement_type:
            queryset = queryset.filter(settlement_type=settlement_type)
        page_items, meta = paginate(request, queryset)
        return Response({'results': SalesInvoiceSerializer(page_items, many=True).data, **meta})

    @transaction.atomic
    def post(self, request):
        serializer = SalesInvoiceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        subtotal, total_discount, total_tax, grand_total = build_invoice_totals(data['items'])
        paid_amount = Decimal(str(data['paid_amount']))
        invoice = SalesInvoice.objects.create(
            invoice_no=data['factor_no'],
            customer_id=data['customer_id'],
            invoice_date=data['date'],
            description=data['description'],
            subtotal=subtotal,
            total_discount=total_discount,
            total_tax=total_tax,
            grand_total=grand_total,
            paid_amount=paid_amount,
            settlement_type=data['settlement_type'],
            remaining_amount=max(Decimal('0'), grand_total - paid_amount),
            payment_status=resolve_payment_status(grand_total, paid_amount),
            status=SalesInvoice.Status.DRAFT,
            created_by=request.user,
        )
        self._save_items(invoice, data['items'])
        return Response(SalesInvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)

    def _save_items(self, invoice, items):
        lines = []
        products = {item.id: item for item in Product.objects.filter(id__in=[row['item_id'] for row in items])}
        for row in items:
            total = (Decimal(str(row['quantity'])) * Decimal(str(row['unit_price']))) - Decimal(str(row['discount'])) + Decimal(str(row['tax']))
            lines.append(
                SalesInvoiceLine(
                    sales_invoice=invoice,
                    line_type=SalesInvoiceLine.LineType.PRODUCT,
                    product=products[row['item_id']],
                    title=products[row['item_id']].name,
                    quantity=row['quantity'],
                    unit_price=row['unit_price'],
                    discount=row['discount'],
                    tax=row['tax'],
                    total=total,
                    description=row['description'],
                )
            )
        SalesInvoiceLine.objects.bulk_create(lines)


class SalesDetailView(APIView):
    permission_classes = [IsAccountingRole]

    def get_object(self, pk):
        return SalesInvoice.objects.select_related('customer').prefetch_related('lines__product').get(pk=pk)

    def get(self, request, pk):
        return Response(SalesInvoiceSerializer(self.get_object(pk)).data)

    @transaction.atomic
    def put(self, request, pk):
        invoice = self.get_object(pk)
        if invoice.status != SalesInvoice.Status.DRAFT:
            return Response({'detail': 'فقط فاکتور draft قابل ویرایش است.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = SalesInvoiceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        subtotal, total_discount, total_tax, grand_total = build_invoice_totals(data['items'])
        paid_amount = Decimal(str(data['paid_amount']))
        invoice.invoice_no = data['factor_no']
        invoice.customer_id = data['customer_id']
        invoice.invoice_date = data['date']
        invoice.description = data['description']
        invoice.subtotal = subtotal
        invoice.total_discount = total_discount
        invoice.total_tax = total_tax
        invoice.grand_total = grand_total
        invoice.paid_amount = paid_amount
        invoice.settlement_type = data['settlement_type']
        invoice.remaining_amount = max(Decimal('0'), grand_total - paid_amount)
        invoice.payment_status = resolve_payment_status(grand_total, paid_amount)
        invoice.save()
        invoice.lines.all().delete()
        SalesListCreateView()._save_items(invoice, data['items'])
        return Response(SalesInvoiceSerializer(invoice).data)

    def delete(self, request, pk):
        invoice = self.get_object(pk)
        if invoice.status != SalesInvoice.Status.DRAFT:
            return Response({'detail': 'فقط فاکتور draft قابل حذف است.'}, status=status.HTTP_400_BAD_REQUEST)
        invoice.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SalesConfirmView(APIView):
    permission_classes = [IsAccountingRole]

    @transaction.atomic
    def post(self, request, pk):
        invoice = SalesInvoice.objects.select_for_update().prefetch_related('lines__product__inventory_item').get(pk=pk)
        if invoice.status != SalesInvoice.Status.DRAFT:
            return Response({'detail': 'فاکتور قبلاً تعیین تکلیف شده است.'}, status=status.HTTP_400_BAD_REQUEST)
        for line in invoice.lines.select_related('product'):
            inventory = InventoryItem.objects.select_for_update().get(product=line.product)
            if inventory.quantity_on_hand < line.quantity:
                return Response({'detail': f'موجودی {line.product.name} کافی نیست.'}, status=status.HTTP_400_BAD_REQUEST)
            inventory.quantity_on_hand -= line.quantity
            inventory.save()
            StockMovement.objects.create(
                inventory_item=inventory,
                movement_type=StockMovement.MovementType.OUT,
                quantity=line.quantity,
                unit_cost=line.unit_price,
                reference_type='sales_invoice',
                reference_id=invoice.id,
                note=f'Sales invoice {invoice.invoice_no}',
                created_by=request.user,
            )
        debit_code = '1101'
        if invoice.settlement_type == SalesInvoice.SettlementType.CARD:
            debit_code = '1102'
        elif invoice.settlement_type == SalesInvoice.SettlementType.CREDIT:
            debit_code = '1301'
        create_voucher(
            date=invoice.invoice_date,
            description=f'سند خودکار فروش {invoice.invoice_no}',
            reference_type='sales_invoice',
            reference_id=invoice.id,
            lines=[
                {'account_id': get_account_by_code(debit_code).id, 'debit': invoice.grand_total, 'credit': 0, 'row_description': 'دریافت / مطالبات'},
                {'account_id': get_account_by_code('4101').id, 'debit': 0, 'credit': invoice.grand_total, 'row_description': 'درآمد فروش'},
            ],
            user=request.user,
        )
        invoice.status = SalesInvoice.Status.CONFIRMED
        invoice.save(update_fields=['status', 'updated_at'])
        return Response(SalesInvoiceSerializer(invoice).data)


class VoucherListCreateView(APIView):
    permission_classes = [IsAccountingRole]

    def get(self, request):
        queryset = JournalEntry.objects.prefetch_related('lines__account').order_by('-entry_date', '-id')
        search = request.query_params.get('search', '').strip()
        status_value = request.query_params.get('status', '').strip()
        reference_type = request.query_params.get('reference_type', '').strip()
        if search:
            queryset = queryset.filter(Q(voucher_no__icontains=search) | Q(description__icontains=search))
        if status_value:
            queryset = queryset.filter(status=status_value)
        if reference_type:
            queryset = queryset.filter(reference_type=reference_type)
        page_items, meta = paginate(request, queryset)
        return Response({'results': JournalEntrySerializer(page_items, many=True).data, **meta})

    @transaction.atomic
    def post(self, request):
        serializer = JournalEntryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        voucher = create_voucher(
            date=data['date'],
            description=data['description'],
            reference_type='manual',
            reference_id=None,
            lines=data['voucher_entries'],
            user=request.user,
            status_value=data['status'],
            voucher_no=data.get('voucher_no') or '',
        )
        return Response(JournalEntrySerializer(voucher).data, status=status.HTTP_201_CREATED)


class VoucherDetailView(APIView):
    permission_classes = [IsAccountingRole]

    def get_object(self, pk):
        return JournalEntry.objects.prefetch_related('lines__account').get(pk=pk)

    def get(self, request, pk):
        return Response(JournalEntrySerializer(self.get_object(pk)).data)

    @transaction.atomic
    def put(self, request, pk):
        voucher = self.get_object(pk)
        if voucher.reference_type and voucher.reference_type != 'manual':
            return Response({'detail': 'سند خودکار قابل ویرایش مستقیم نیست.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = JournalEntryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        voucher.entry_date = data['date']
        voucher.description = data['description']
        voucher.status = data['status']
        if data.get('voucher_no'):
            voucher.voucher_no = data['voucher_no']
        voucher.save()
        voucher.lines.all().delete()
        entries = []
        for item in data['voucher_entries']:
            entries.append(
                JournalEntryLine(
                    journal_entry=voucher,
                    account_id=item['account_id'],
                    debit=item['debit'],
                    credit=item['credit'],
                    description=item.get('row_description', ''),
                )
            )
        JournalEntryLine.objects.bulk_create(entries)
        voucher.refresh_from_db()
        return Response(JournalEntrySerializer(voucher).data)

    def delete(self, request, pk):
        voucher = self.get_object(pk)
        if voucher.reference_type and voucher.reference_type != 'manual':
            return Response({'detail': 'سند خودکار قابل حذف نیست.'}, status=status.HTTP_400_BAD_REQUEST)
        voucher.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountingBootstrapView(APIView):
    permission_classes = [IsAccountingRole]

    def get(self, request):
        categories = list(
            ProductCategory.objects.order_by('name').values_list('name', flat=True)
        )
        serializer = InventoryFilterOptionsSerializer({
            'categories': categories,
            'parties': Party.objects.filter(is_active=True).order_by('name'),
            'accounts': Account.objects.filter(is_active=True).order_by('code'),
        })
        return Response(serializer.data)
