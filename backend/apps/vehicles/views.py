from decimal import Decimal, ROUND_HALF_UP

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
from apps.services.models import GeneralSettings
from apps.workers.models import WorkerProfile


class VehicleEntryListCreateView(generics.ListCreateAPIView):
    serializer_class = VehicleEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = VehicleEntry.objects.select_related(
            'customer',
            'job',
            'job__assigned_worker',
            'job__assigned_worker__user',
        ).prefetch_related('job__service_lines__service', 'status_logs').filter(tenant=self.request.user.tenant).order_by('-check_in_at')
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user if getattr(self.request.user, 'is_authenticated', False) else None
        serializer.save(entered_by=user, updated_by=user)


class VehicleEntryDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = VehicleEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VehicleEntry.objects.select_related(
            'customer',
            'job',
            'job__assigned_worker',
            'job__assigned_worker__user',
        ).prefetch_related('job__service_lines__service', 'status_logs').filter(tenant=self.request.user.tenant)

    def perform_update(self, serializer):
        user = self.request.user if getattr(self.request.user, 'is_authenticated', False) else None
        serializer.save(updated_by=user)


class VehicleEntryStatusUpdateView(generics.UpdateAPIView):
    serializer_class = VehicleEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VehicleEntry.objects.select_related('job').filter(tenant=self.request.user.tenant)

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
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _money(value):
        return Decimal(str(value or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def _clamp_percent(value):
        percent = Decimal(str(value or 0))
        if percent < 0:
            return Decimal('0')
        if percent > 100:
            return Decimal('100')
        return percent

    def _discount_percent_per_half_star(self, tenant):
        settings_obj = GeneralSettings.objects.filter(tenant=tenant).order_by('id').first()
        return self._clamp_percent(
            getattr(settings_obj, 'discount_percent_per_half_star', Decimal('0'))
        )

    def _compute_discount(self, base_amount, customer_score, percent_per_half_star):
        score = Decimal(str(customer_score or 0))
        if score < 0:
            score = Decimal('0')
        if score > 5:
            score = Decimal('5')
        half_stars = score * Decimal('2')
        discount_percent = self._clamp_percent(percent_per_half_star * half_stars)
        discount_amount = self._money((Decimal(str(base_amount or 0)) * discount_percent) / Decimal('100'))
        return discount_percent, discount_amount

    def _resolve_assigned_workers(self, job):
        snapshot = job.assigned_workers_snapshot if isinstance(job.assigned_workers_snapshot, list) else []
        ordered_ids = []
        names_by_id = {}
        for item in snapshot:
            if not isinstance(item, dict):
                continue
            try:
                worker_id = int(item.get('id'))
            except (TypeError, ValueError):
                continue
            if worker_id <= 0:
                continue
            if worker_id not in ordered_ids:
                ordered_ids.append(worker_id)
            raw_name = (item.get('name') or '').strip()
            if raw_name:
                names_by_id[worker_id] = raw_name

        if job.assigned_worker_id and job.assigned_worker_id not in ordered_ids:
            ordered_ids.insert(0, int(job.assigned_worker_id))

        if not ordered_ids:
            return []

        profiles = {
            item.id: item
            for item in WorkerProfile.objects.select_related('user').filter(id__in=ordered_ids, tenant=job.tenant)
        }
        workers = []
        for worker_id in ordered_ids:
            profile = profiles.get(worker_id)
            if not profile:
                continue
            name = (
                names_by_id.get(worker_id)
                or (profile.user.full_name or profile.user.username or '').strip()
                or f'نیرو {worker_id}'
            )
            workers.append(
                {
                    'id': worker_id,
                    'name': name,
                    'tip_share_percent': Decimal(str(profile.tip_share_percent or 0)),
                }
            )
        return workers

    def _distribute_tip(self, tip_amount, assigned_workers):
        tip_value = max(Decimal('0'), Decimal(str(tip_amount or 0)))
        if tip_value <= 0 or not assigned_workers:
            return [], Decimal('0')

        prepared = []
        total_percent = Decimal('0')
        for item in assigned_workers:
            percent = Decimal(str(item.get('tip_share_percent') or 0))
            if percent < 0:
                percent = Decimal('0')
            if percent > 100:
                percent = Decimal('100')
            prepared.append({**item, 'tip_share_percent': percent})
            total_percent += percent

        if total_percent <= 0:
            return [
                {
                    **item,
                    'tip_share_amount': Decimal('0'),
                }
                for item in prepared
            ], Decimal('0')

        distributed_total = Decimal('0')
        result = []
        if total_percent <= 100:
            for idx, item in enumerate(prepared):
                if idx == len(prepared) - 1:
                    amount = self._money((tip_value * item['tip_share_percent']) / Decimal('100'))
                else:
                    amount = self._money((tip_value * item['tip_share_percent']) / Decimal('100'))
                result.append({**item, 'tip_share_amount': amount})
                distributed_total += amount
        else:
            for idx, item in enumerate(prepared):
                if idx == len(prepared) - 1:
                    amount = self._money(tip_value - distributed_total)
                else:
                    amount = self._money((tip_value * item['tip_share_percent']) / total_percent)
                result.append({**item, 'tip_share_amount': amount})
                distributed_total += amount

        if distributed_total > tip_value:
            overflow = distributed_total - tip_value
            if result:
                result[-1]['tip_share_amount'] = self._money(result[-1]['tip_share_amount'] - overflow)
            distributed_total = tip_value

        return result, self._money(distributed_total)

    def get(self, request, pk):
        tenant = getattr(request.user, 'tenant', None)
        vehicle = VehicleEntry.objects.select_related('job', 'customer').prefetch_related(
            'job__service_lines__service',
            'job__product_lines__product',
        ).filter(pk=pk, tenant=tenant).first()
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
                InventoryItem.objects.filter(product_id=line.product_id, tenant=tenant)
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
        for product in Product.objects.filter(is_active=True, tenant=tenant).order_by('name'):
            stock = (
                InventoryItem.objects.filter(product_id=product.id, tenant=tenant)
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
        discount_base = services_total + products_total
        customer_score = Decimal(str(getattr(vehicle.customer, 'yearly_score', 0) or 0))
        discount_percent_per_half_star = self._discount_percent_per_half_star(tenant)
        customer_discount_percent, discount_total = self._compute_discount(
            base_amount=discount_base,
            customer_score=customer_score,
            percent_per_half_star=discount_percent_per_half_star,
        )
        final_total = discount_base - discount_total + tip_amount
        assigned_workers = self._resolve_assigned_workers(vehicle.job)
        assigned_workers_with_tip, workers_tip_share_amount = self._distribute_tip(
            tip_amount=tip_amount,
            assigned_workers=assigned_workers,
        )
        assigned_workers_names = [item['name'] for item in assigned_workers_with_tip]

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
                    'customer_score': float(customer_score),
                },
                'job': {
                    'id': vehicle.job.id,
                    'service_lines': service_lines,
                    'product_lines': product_lines,
                    'available_products': available_products,
                    'services_total': services_total,
                    'products_total': products_total,
                    'discount_percent_per_half_star': float(discount_percent_per_half_star),
                    'customer_discount_percent': float(customer_discount_percent),
                    'discount_total': discount_total,
                    'tip_amount': tip_amount,
                    'final_total': final_total,
                    'worker_share_amount': vehicle.job.worker_share_amount,
                    'workers_tip_share_amount': workers_tip_share_amount,
                    'carwash_share_amount': vehicle.job.carwash_share_amount,
                    'assigned_workers_names': assigned_workers_names,
                    'assigned_workers': [
                        {
                            'id': item['id'],
                            'name': item['name'],
                            'tip_share_percent': float(item['tip_share_percent']),
                            'tip_share_amount': float(item['tip_share_amount']),
                        }
                        for item in assigned_workers_with_tip
                    ],
                },
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def patch(self, request, pk):
        tenant = getattr(request.user, 'tenant', None)
        vehicle = (
            VehicleEntry.objects.select_for_update()
            .select_related('job', 'customer')
            .prefetch_related('job__service_lines', 'job__product_lines')
            .filter(pk=pk, tenant=tenant)
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
            for product in Product.objects.filter(is_active=True, tenant=tenant)
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
        discount_base = completed_service_totals + product_totals
        customer_score = Decimal(str(getattr(vehicle.customer, 'yearly_score', 0) or 0))
        discount_percent_per_half_star = self._discount_percent_per_half_star(tenant)
        _customer_discount_percent, discount_total = self._compute_discount(
            base_amount=discount_base,
            customer_score=customer_score,
            percent_per_half_star=discount_percent_per_half_star,
        )
        final_total = discount_base - discount_total + tip_amount

        share_base_total = completed_service_totals
        worker_share_base = vehicle.job.worker_share_amount or Decimal('0')
        if worker_share_base > share_base_total:
            worker_share_base = share_base_total

        assigned_workers = self._resolve_assigned_workers(vehicle.job)
        assigned_workers_with_tip, workers_tip_share_amount = self._distribute_tip(
            tip_amount=tip_amount,
            assigned_workers=assigned_workers,
        )
        carwash_share = (share_base_total - worker_share_base) + max(
            Decimal('0'),
            tip_amount - workers_tip_share_amount,
        ) - discount_total
        if carwash_share < 0:
            carwash_share = Decimal('0')
        workers_map = {
            int(item['id']): item for item in assigned_workers_with_tip if item.get('id')
        }
        snapshot = (
            vehicle.job.assigned_workers_snapshot
            if isinstance(vehicle.job.assigned_workers_snapshot, list)
            else []
        )
        updated_snapshot = []
        used_ids = set()
        for item in snapshot:
            if not isinstance(item, dict):
                continue
            try:
                worker_id = int(item.get('id'))
            except (TypeError, ValueError):
                continue
            worker_data = workers_map.get(worker_id)
            if not worker_data:
                continue
            used_ids.add(worker_id)
            updated_snapshot.append(
                {
                    'id': worker_id,
                    'name': worker_data.get('name') or (item.get('name') or ''),
                    'tip_share_percent': float(worker_data.get('tip_share_percent') or 0),
                    'tip_share_amount': float(worker_data.get('tip_share_amount') or 0),
                }
            )
        for worker_data in assigned_workers_with_tip:
            worker_id = int(worker_data['id'])
            if worker_id in used_ids:
                continue
            updated_snapshot.append(
                {
                    'id': worker_id,
                    'name': worker_data.get('name') or '',
                    'tip_share_percent': float(worker_data.get('tip_share_percent') or 0),
                    'tip_share_amount': float(worker_data.get('tip_share_amount') or 0),
                }
            )

        vehicle.job.services_total = completed_service_totals
        vehicle.job.products_total = product_totals
        vehicle.job.tip_amount = tip_amount
        vehicle.job.workers_tip_share_amount = workers_tip_share_amount
        vehicle.job.discount_total = discount_total
        vehicle.job.tax_total = 0
        vehicle.job.final_total = final_total
        vehicle.job.worker_share_amount = worker_share_base
        vehicle.job.carwash_share_amount = carwash_share
        vehicle.job.assigned_workers_snapshot = updated_snapshot
        vehicle.job.released_at = timezone.now()
        vehicle.job.save(
            update_fields=[
                'services_total',
                'products_total',
                'tip_amount',
                'workers_tip_share_amount',
                'discount_total',
                'tax_total',
                'final_total',
                'worker_share_amount',
                'carwash_share_amount',
                'assigned_workers_snapshot',
                'released_at',
                'updated_at',
            ]
        )

        for line in vehicle.job.product_lines.select_related('product').all():
            if line.quantity <= 0:
                continue
            inventory_item, _created = InventoryItem.objects.select_for_update().get_or_create(
                product=line.product,
                tenant=tenant,
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
                tenant=tenant,
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

