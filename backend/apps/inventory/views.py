from decimal import Decimal

from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import InventoryItem, StockMovement
from .serializers import InventoryItemSerializer
from apps.products.models import Product


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
            note=note or 'Manual purchase from manager panel',
            reference_type='manager_purchase',
            reference_id=product.id,
            created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
        )

        return Response(InventoryItemSerializer(inventory_item).data, status=status.HTTP_201_CREATED)
