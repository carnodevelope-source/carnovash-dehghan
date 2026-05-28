from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import VehicleEntry
from .serializers import VehicleEntrySerializer
from apps.inventory.models import InventoryItem
from apps.inventory.models import StockMovement
from apps.products.models import Product


class VehicleEntryListCreateView(generics.ListCreateAPIView):
    serializer_class = VehicleEntrySerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = VehicleEntry.objects.select_related(
            'job',
            'job__assigned_worker',
            'job__assigned_worker__user',
        ).prefetch_related('job__service_lines__service', 'status_logs').order_by('-check_in_at')
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user if getattr(self.request.user, 'is_authenticated', False) else None
        serializer.save(entered_by=user, updated_by=user)


class VehicleEntryDetailView(generics.RetrieveAPIView):
    serializer_class = VehicleEntrySerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    queryset = VehicleEntry.objects.select_related(
        'job',
        'job__assigned_worker',
        'job__assigned_worker__user',
    ).prefetch_related('job__service_lines__service', 'status_logs')


class VehicleEntryStatusUpdateView(generics.UpdateAPIView):
    serializer_class = VehicleEntrySerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    queryset = VehicleEntry.objects.select_related('job')

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        new_status = request.data.get('status')
        valid_statuses = {choice[0] for choice in VehicleEntry.Status.choices}
        if new_status not in valid_statuses:
            return Response({'status': ['Invalid status value.']}, status=status.HTTP_400_BAD_REQUEST)

        instance.status = new_status
        if new_status == VehicleEntry.Status.READY_TO_SETTLE:
            instance.ready_at = timezone.now()
        elif new_status == VehicleEntry.Status.RELEASED:
            instance.released_at = timezone.now()
        instance.save(update_fields=['status', 'ready_at', 'released_at', 'updated_at'])

        if hasattr(instance, 'job') and instance.job:
            if new_status == VehicleEntry.Status.READY_TO_SETTLE:
                instance.job.completed_at = timezone.now()
                instance.job.save(update_fields=['completed_at', 'updated_at'])
            elif new_status == VehicleEntry.Status.RELEASED:
                instance.job.released_at = timezone.now()
                instance.job.save(update_fields=['released_at', 'updated_at'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VehicleReleaseCheckoutView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        vehicle = VehicleEntry.objects.select_related('job').prefetch_related(
            'job__service_lines__service',
            'job__product_lines__product',
        ).filter(pk=pk).first()
        if not vehicle:
            return Response({'detail': 'Vehicle not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not getattr(vehicle, 'job', None):
            return Response({'detail': 'Vehicle job not found.'}, status=status.HTTP_400_BAD_REQUEST)

        service_lines = []
        for line in vehicle.job.service_lines.all():
            service_lines.append(
                {
                    'id': line.id,
                    'service_name': line.service.name if line.service else 'خدمت',
                    'quantity': line.quantity,
                    'unit_price': line.unit_price,
                    'line_total': line.line_total,
                    'is_completed': line.is_completed,
                }
            )

        product_lines = []
        for line in vehicle.job.product_lines.all():
            stock = (
                InventoryItem.objects.filter(product_id=line.product_id)
                .values('quantity_on_hand', 'reserved_quantity')
                .first()
            )
            available_qty = Decimal('0')
            if stock:
                available_qty = Decimal(stock.get('quantity_on_hand') or 0) - Decimal(
                    stock.get('reserved_quantity') or 0
                )
            product_lines.append(
                {
                    'id': line.id,
                    'product_id': line.product_id,
                    'product_name': line.product.name if line.product else 'محصول',
                    'sku': line.product.sku if line.product else '',
                    'quantity': line.quantity,
                    'unit_price': line.unit_price,
                    'line_total': line.line_total,
                    'available_quantity': available_qty,
                }
            )

        selected_qty_by_product = {
            int(line['product_id']): Decimal(str(line['quantity'] or 0))
            for line in product_lines
            if line.get('product_id')
        }
        available_products = []
        for product in Product.objects.filter(is_active=True).order_by('name'):
            stock = (
                InventoryItem.objects.filter(product_id=product.id)
                .values('quantity_on_hand', 'reserved_quantity')
                .first()
            )
            available_qty = Decimal('0')
            if stock:
                available_qty = Decimal(stock.get('quantity_on_hand') or 0) - Decimal(
                    stock.get('reserved_quantity') or 0
                )
            available_products.append(
                {
                    'id': product.id,
                    'name': product.name,
                    'sku': product.sku,
                    'sale_price': product.sale_price,
                    'available_quantity': available_qty,
                    'selected_quantity': selected_qty_by_product.get(product.id, Decimal('0')),
                }
            )

        services_total = (
            vehicle.job.service_lines.filter(is_completed=True).aggregate(total=Sum('line_total')).get('total')
            or Decimal('0')
        )
        products_total = vehicle.job.products_total or Decimal('0')
        tip_amount = vehicle.job.tip_amount or Decimal('0')
        final_total = services_total + products_total + tip_amount

        return Response(
            {
                'vehicle': {
                    'id': vehicle.id,
                    'plate_number': vehicle.plate_number,
                    'car_model': vehicle.car_model,
                    'car_color': vehicle.car_color,
                    'driver_name': vehicle.driver_name,
                    'driver_phone': vehicle.driver_phone,
                    'status': vehicle.status,
                    'payment_status': vehicle.payment_status,
                },
                'job': {
                    'id': vehicle.job.id,
                    'service_lines': service_lines,
                    'product_lines': product_lines,
                    'available_products': available_products,
                    'services_total': services_total,
                    'products_total': products_total,
                    'tip_amount': tip_amount,
                    'final_total': final_total,
                    'worker_share_amount': vehicle.job.worker_share_amount,
                    'carwash_share_amount': vehicle.job.carwash_share_amount,
                },
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def patch(self, request, pk):
        vehicle = (
            VehicleEntry.objects.select_for_update()
            .select_related('job')
            .prefetch_related('job__service_lines', 'job__product_lines')
            .filter(pk=pk)
            .first()
        )
        if not vehicle:
            return Response({'detail': 'Vehicle not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not getattr(vehicle, 'job', None):
            return Response({'detail': 'Vehicle job not found.'}, status=status.HTTP_400_BAD_REQUEST)
        if vehicle.status == VehicleEntry.Status.RELEASED:
            return Response({'detail': 'Vehicle already released.'}, status=status.HTTP_400_BAD_REQUEST)

        service_lines_payload = request.data.get('service_lines', [])
        product_lines_payload = request.data.get('product_lines', [])
        tip_amount = Decimal(str(request.data.get('tip_amount', vehicle.job.tip_amount or 0)))
        if tip_amount < 0:
            return Response(
                {'tip_amount': ['Invalid tip value.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service_lines_map = {line.id: line for line in vehicle.job.service_lines.all()}
        for item in service_lines_payload:
            line_id = item.get('id')
            line = service_lines_map.get(line_id)
            if not line:
                continue
            line.is_completed = bool(item.get('is_completed', False))
            line.save(update_fields=['is_completed'])

        product_lines_by_id = {line.id: line for line in vehicle.job.product_lines.all()}
        product_lines_by_product_id = {
            line.product_id: line for line in vehicle.job.product_lines.all()
        }
        active_products = {
            product.id: product
            for product in Product.objects.filter(is_active=True)
        }
        touched_product_ids = set()
        product_totals = Decimal('0')
        for item in product_lines_payload:
            line_id = item.get('id')
            product_id = item.get('product_id')
            line = product_lines_by_id.get(line_id)
            if not line and product_id:
                line = product_lines_by_product_id.get(product_id)
            qty = Decimal(str(item.get('quantity', line.quantity or 0 if line else 0)))
            if qty < 0:
                return Response(
                    {'product_lines': [f'Invalid quantity for line {line_id}.']},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not line and product_id and qty > 0:
                product = active_products.get(product_id)
                if not product:
                    continue
                line = vehicle.job.product_lines.create(
                    product=product,
                    quantity=0,
                    unit_price=product.sale_price or Decimal('0'),
                    line_total=0,
                )
                product_lines_by_id[line.id] = line
                product_lines_by_product_id[line.product_id] = line
            if not line:
                continue

            touched_product_ids.add(line.product_id)

            product = active_products.get(line.product_id)
            unit_price = (product.sale_price if product and product.sale_price is not None else line.unit_price) or Decimal('0')
            line.quantity = qty
            line.unit_price = unit_price
            line.line_total = unit_price * qty
            line.save(update_fields=['quantity', 'unit_price', 'line_total'])
            product_totals += line.line_total

        for line in vehicle.job.product_lines.all():
            if line.product_id in touched_product_ids:
                continue
            if line.quantity <= 0:
                continue
            line.quantity = 0
            line.line_total = 0
            line.save(update_fields=['quantity', 'line_total'])

        completed_service_totals = (
            vehicle.job.service_lines.filter(is_completed=True).aggregate(total=Sum('line_total')).get('total')
            or Decimal('0')
        )
        final_total = completed_service_totals + product_totals + tip_amount

        worker_share = vehicle.job.worker_share_amount or Decimal('0')
        share_base_total = completed_service_totals
        if worker_share > share_base_total:
            worker_share = share_base_total
        carwash_share = share_base_total - worker_share

        vehicle.job.services_total = completed_service_totals
        vehicle.job.products_total = product_totals
        vehicle.job.tip_amount = tip_amount
        vehicle.job.discount_total = 0
        vehicle.job.tax_total = 0
        vehicle.job.final_total = final_total
        vehicle.job.carwash_share_amount = carwash_share
        vehicle.job.released_at = timezone.now()
        vehicle.job.save(
            update_fields=[
                'services_total',
                'products_total',
                'tip_amount',
                'discount_total',
                'tax_total',
                'final_total',
                'carwash_share_amount',
                'released_at',
                'updated_at',
            ]
        )

        for line in vehicle.job.product_lines.select_related('product').all():
            if line.quantity <= 0:
                continue
            inventory_item, _created = InventoryItem.objects.select_for_update().get_or_create(
                product=line.product,
                defaults={'quantity_on_hand': 0, 'reserved_quantity': 0, 'min_quantity_alert': 0},
            )
            if inventory_item.available_quantity < line.quantity:
                return Response(
                    {
                        'inventory': [
                            f'Insufficient stock for product "{line.product.name}".'
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            inventory_item.quantity_on_hand = F('quantity_on_hand') - line.quantity
            inventory_item.save(update_fields=['quantity_on_hand', 'updated_at'])
            inventory_item.refresh_from_db(fields=['quantity_on_hand', 'reserved_quantity'])
            StockMovement.objects.create(
                inventory_item=inventory_item,
                movement_type=StockMovement.MovementType.OUT,
                quantity=line.quantity,
                unit_cost=line.unit_price or Decimal('0'),
                note='مصرف در ترخیص خودرو',
                reference_type='vehicle_release',
                reference_id=vehicle.id,
                created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
            )

        vehicle.payment_status = VehicleEntry.PaymentStatus.PAID
        vehicle.status = VehicleEntry.Status.RELEASED
        vehicle.released_at = timezone.now()
        vehicle.save(update_fields=['status', 'payment_status', 'released_at', 'updated_at'])

        serializer = VehicleEntrySerializer(vehicle)
        return Response(serializer.data, status=status.HTTP_200_OK)
