from decimal import Decimal

from django.db import transaction
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.products.models import Product

from .models import ExpenseEntry, InventoryItem, StockMovement
from .serializers import ExpenseEntrySerializer, InventoryItemSerializer, StockMovementHistorySerializer


class InventoryItemListCreateView(generics.ListCreateAPIView):
    serializer_class = InventoryItemSerializer

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        return InventoryItem.objects.select_related('product').filter(tenant=tenant).order_by('product__name')

    def perform_create(self, serializer):
        serializer.save(tenant=getattr(self.request.user, 'tenant', None))


class InventoryItemRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = InventoryItemSerializer

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        return InventoryItem.objects.select_related('product').filter(tenant=tenant).order_by('product__name')


class InventoryPurchaseView(APIView):
    @transaction.atomic
    def post(self, request):
        tenant = getattr(request.user, 'tenant', None)
        product_id = request.data.get('product_id')
        quantity = Decimal(str(request.data.get('quantity', 0) or 0))
        unit_cost_raw = request.data.get('unit_cost', None)
        sale_price_raw = request.data.get('sale_price', None)
        unit_cost = Decimal(str(unit_cost_raw if unit_cost_raw is not None else 0))
        sale_price = Decimal(str(sale_price_raw if sale_price_raw is not None else 0))
        note = (request.data.get('note') or '').strip()

        if not product_id:
            return Response({'product_id': ['Product is required.']}, status=status.HTTP_400_BAD_REQUEST)
        if quantity <= 0:
            return Response({'quantity': ['Quantity must be greater than zero.']}, status=status.HTTP_400_BAD_REQUEST)
        if unit_cost < 0:
            return Response({'unit_cost': ['Unit cost cannot be negative.']}, status=status.HTTP_400_BAD_REQUEST)
        if sale_price < 0:
            return Response({'sale_price': ['Sale price cannot be negative.']}, status=status.HTTP_400_BAD_REQUEST)

        product = Product.objects.filter(pk=product_id, tenant=tenant).first()
        if not product:
            return Response({'product_id': ['Product not found.']}, status=status.HTTP_404_NOT_FOUND)

        inventory_item, _ = InventoryItem.objects.select_for_update().get_or_create(
            product=product,
            tenant=tenant,
            defaults={
                'quantity_on_hand': Decimal('0'),
                'reserved_quantity': Decimal('0'),
                'min_quantity_alert': Decimal(str(product.min_stock or 0)),
            },
        )
        inventory_item.quantity_on_hand = Decimal(str(inventory_item.quantity_on_hand or 0)) + quantity
        inventory_item.min_quantity_alert = Decimal(str(product.min_stock or 0))
        inventory_item.save(update_fields=['quantity_on_hand', 'min_quantity_alert', 'updated_at'])

        product_changed_fields = ['updated_at']
        if unit_cost_raw is not None:
            product.cost_price = unit_cost
            product_changed_fields.append('cost_price')
        if sale_price_raw is not None:
            product.sale_price = sale_price
            product_changed_fields.append('sale_price')
        if len(product_changed_fields) > 1:
            product.save(update_fields=product_changed_fields)

        StockMovement.objects.create(
            tenant=tenant,
            inventory_item=inventory_item,
            movement_type=StockMovement.MovementType.IN,
            quantity=quantity,
            unit_cost=unit_cost,
            sale_price_snapshot=sale_price,
            note=note or 'Manual purchase from manager panel',
            reference_type='manager_purchase',
            reference_id=product.id,
            created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
        )

        return Response(InventoryItemSerializer(inventory_item).data, status=status.HTTP_201_CREATED)


class ProductPurchaseHistoryView(APIView):
    def get(self, request, product_id):
        tenant = getattr(request.user, 'tenant', None)
        product = Product.objects.filter(pk=product_id, tenant=tenant).first()
        if not product:
            return Response({'detail': 'محصول یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)

        history = (
            StockMovement.objects
            .select_related('inventory_item__product', 'created_by')
            .filter(
                tenant=tenant,
                inventory_item__product_id=product_id,
                reference_type='manager_purchase',
                movement_type=StockMovement.MovementType.IN,
            )
            .order_by('-moved_at', '-id')
        )
        rows = []
        for item in history:
            row = StockMovementHistorySerializer(item).data
            if not row.get('sale_price_snapshot'):
                row['sale_price_snapshot'] = product.sale_price
            rows.append(row)
        return Response({
            'product': {
                'id': product.id,
                'name': product.name,
                'sale_price': product.sale_price,
                'cost_price': product.cost_price,
            },
            'history': rows,
        }, status=status.HTTP_200_OK)


class ExpenseEntryListCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        tenant = getattr(request.user, 'tenant', None)
        manual_entries = [
            {
                **ExpenseEntrySerializer(item, context={'request': request}).data,
                'row_id': f'manual-{item.id}',
                'source_label': 'ثبت دستی',
                'can_edit': True,
                'can_delete': True,
            }
            for item in ExpenseEntry.objects.filter(tenant=tenant).select_related('created_by').order_by('-spent_at', '-id')
        ]

        purchase_entries = []
        purchase_rows = (
            StockMovement.objects
            .select_related('inventory_item__product', 'created_by')
            .filter(
                tenant=tenant,
                reference_type='manager_purchase',
                movement_type=StockMovement.MovementType.IN,
            )
            .order_by('-moved_at', '-id')
        )
        for item in purchase_rows:
            amount = Decimal(str(item.quantity or 0)) * Decimal(str(item.unit_cost or 0))
            purchase_entries.append({
                'id': item.id,
                'row_id': f'purchase-{item.id}',
                'title': f'خرید محصول: {item.inventory_item.product.name}',
                'amount': amount,
                'details': item.note or '',
                'source_type': 'purchase',
                'source_label': 'خرید محصول',
                'spent_at': item.moved_at,
                'created_at': item.created_at,
                'updated_at': item.updated_at,
                'created_by_name': item.created_by.full_name or item.created_by.username if item.created_by else '-',
                'attachment_url': '',
                'attachment_name': '',
                'can_edit': False,
                'can_delete': False,
                'product_id': item.inventory_item.product_id,
                'quantity': item.quantity,
                'unit_cost': item.unit_cost,
            })

        rows = sorted(
            [*manual_entries, *purchase_entries],
            key=lambda item: item.get('spent_at') or item.get('created_at'),
            reverse=True,
        )
        return Response(rows, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ExpenseEntrySerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(
            tenant=getattr(request.user, 'tenant', None),
            created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
            source_type=ExpenseEntry.SourceType.MANUAL,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ExpenseEntryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExpenseEntrySerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        return ExpenseEntry.objects.filter(tenant=tenant, source_type=ExpenseEntry.SourceType.MANUAL).order_by('-spent_at', '-id')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
