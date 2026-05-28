from rest_framework import serializers
from django.db.models import Q
from django.db import transaction
from decimal import Decimal

from .models import VehicleEntry
from .models import VehicleJob, VehicleJobService
from .models import VehicleStatusLog
from .models import VehicleJobProduct
from apps.services.models import Service
from apps.workers.models import WorkerProfile
from apps.products.models import Product
from apps.inventory.models import InventoryItem, StockMovement


class VehicleJobServiceLineSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = VehicleJobService
        fields = [
            'id',
            'service',
            'service_name',
            'quantity',
            'unit_price',
            'line_total',
            'is_completed',
            'note',
        ]


class VehicleStatusLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    def get_changed_by_name(self, obj):
        if not obj.changed_by:
            return None
        return obj.changed_by.full_name or obj.changed_by.username

    class Meta:
        model = VehicleStatusLog
        fields = ['id', 'from_status', 'to_status', 'changed_by_name', 'changed_at', 'note']


class VehicleJobDetailSerializer(serializers.ModelSerializer):
    assigned_worker_name = serializers.SerializerMethodField()
    service_lines = VehicleJobServiceLineSerializer(many=True, read_only=True)

    def get_assigned_worker_name(self, obj):
        if not obj.assigned_worker or not obj.assigned_worker.user:
            return None
        return obj.assigned_worker.user.full_name or obj.assigned_worker.user.username

    class Meta:
        model = VehicleJob
        fields = [
            'id',
            'assigned_worker',
            'assigned_worker_name',
            'worker_payment_type',
            'worker_payment_percent',
            'worker_payment_fixed',
            'services_total',
            'products_total',
            'discount_total',
            'tax_total',
            'final_total',
            'worker_share_amount',
            'carwash_share_amount',
            'tip_amount',
            'delivered_to_worker_at',
            'completed_at',
            'released_at',
            'service_lines',
        ]


class VehicleEntrySerializer(serializers.ModelSerializer):
    services = serializers.ListField(write_only=True, required=False, default=list)
    products = serializers.ListField(write_only=True, required=False, default=list)
    tip_amount = serializers.DecimalField(max_digits=12, decimal_places=2, write_only=True, required=False, default=0)
    share = serializers.DictField(write_only=True, required=False, default=dict)
    worker_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    worker_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    job = VehicleJobDetailSerializer(read_only=True)
    status_logs = VehicleStatusLogSerializer(many=True, read_only=True)

    @transaction.atomic
    def create(self, validated_data):
        services_payload = validated_data.pop('services', [])
        products_payload = validated_data.pop('products', [])
        tip_amount = Decimal(str(validated_data.pop('tip_amount', 0) or 0))
        share_payload = validated_data.pop('share', {})
        worker_id = validated_data.pop('worker_id', None)
        worker_name = (validated_data.pop('worker_name', '') or '').strip()
        assigned_worker = None
        if worker_id:
            assigned_worker = WorkerProfile.objects.filter(id=worker_id).first()
        if not assigned_worker and worker_name:
            assigned_worker = WorkerProfile.objects.select_related('user').filter(
                Q(user__full_name__iexact=worker_name) | Q(user__username__iexact=worker_name)
            ).first()

        vehicle_entry = VehicleEntry.objects.create(**validated_data)

        payment_type = share_payload.get('type', VehicleJob.WorkerPaymentType.PERCENT)
        share_value = share_payload.get('value', 0) or 0
        services_total = Decimal(str(sum((item.get('price', 0) or 0) for item in services_payload)))

        products_total = Decimal('0')
        product_lines_data = []
        for item in products_payload:
            product_id = item.get('id') or item.get('product_id')
            qty = Decimal(str(item.get('quantity', 0) or 0))
            if not product_id or qty <= 0:
                continue
            product = Product.objects.filter(id=product_id, is_active=True).first()
            if not product:
                continue
            inventory_item, _created = InventoryItem.objects.select_for_update().get_or_create(
                product=product,
                defaults={'quantity_on_hand': 0, 'reserved_quantity': 0, 'min_quantity_alert': 0},
            )
            if inventory_item.available_quantity < qty:
                raise serializers.ValidationError(
                    {'products': [f'موجودی محصول "{product.name}" کافی نیست.']}
                )
            unit_price = Decimal(str(product.sale_price or 0))
            line_total = unit_price * qty
            products_total += line_total
            product_lines_data.append(
                {
                    'product': product,
                    'quantity': qty,
                    'unit_price': unit_price,
                    'line_total': line_total,
                    'inventory_item': inventory_item,
                }
            )

        share_base_total = services_total + products_total
        if payment_type == VehicleJob.WorkerPaymentType.FIXED:
            worker_share_amount = min(share_base_total, Decimal(str(share_value or 0)))
        else:
            percent = min(Decimal('100'), max(Decimal('0'), Decimal(str(share_value or 0))))
            worker_share_amount = (share_base_total * percent) / Decimal('100')
        carwash_share_amount = share_base_total - worker_share_amount
        final_total = share_base_total + max(Decimal('0'), tip_amount)

        vehicle_job = VehicleJob.objects.create(
            vehicle=vehicle_entry,
            assigned_worker=assigned_worker,
            worker_payment_type=payment_type
            if payment_type in dict(VehicleJob.WorkerPaymentType.choices)
            else VehicleJob.WorkerPaymentType.PERCENT,
            worker_payment_percent=share_value if payment_type == VehicleJob.WorkerPaymentType.PERCENT else 0,
            worker_payment_fixed=share_value if payment_type == VehicleJob.WorkerPaymentType.FIXED else 0,
            services_total=services_total,
            products_total=products_total,
            tip_amount=max(Decimal('0'), tip_amount),
            final_total=final_total,
            worker_share_amount=worker_share_amount,
            carwash_share_amount=carwash_share_amount,
        )

        for item in services_payload:
            title = (item.get('title') or '').strip() or 'خدمت بدون نام'
            unit_price = item.get('price', 0) or 0
            service_obj, _ = Service.objects.get_or_create(
                name=title,
                defaults={'base_price': unit_price, 'is_active': True},
            )
            VehicleJobService.objects.create(
                vehicle_job=vehicle_job,
                service=service_obj,
                quantity=1,
                unit_price=unit_price,
                line_total=unit_price,
                is_completed=False,
                note='ثبت از استپ ۲ پذیرش',
            )

        for item in product_lines_data:
            VehicleJobProduct.objects.create(
                vehicle_job=vehicle_job,
                product=item['product'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                line_total=item['line_total'],
            )
            inventory_item = item['inventory_item']
            inventory_item.quantity_on_hand = inventory_item.quantity_on_hand - item['quantity']
            inventory_item.save(update_fields=['quantity_on_hand', 'updated_at'])
            StockMovement.objects.create(
                inventory_item=inventory_item,
                movement_type=StockMovement.MovementType.OUT,
                quantity=item['quantity'],
                unit_cost=item['unit_price'],
                note='مصرف در ثبت پذیرش خودرو',
                reference_type='vehicle_intake',
                reference_id=vehicle_entry.id,
                created_by=self.context['request'].user
                if getattr(self.context.get('request'), 'user', None) and self.context['request'].user.is_authenticated
                else None,
            )

        return vehicle_entry

    class Meta:
        model = VehicleEntry
        fields = [
            'id',
            'plate_number',
            'plate_left',
            'plate_letter',
            'plate_mid',
            'plate_right',
            'car_model',
            'car_color',
            'driver_name',
            'driver_phone',
            'notes',
            'status',
            'payment_status',
            'check_in_at',
            'created_at',
            'updated_at',
            'services',
            'products',
            'tip_amount',
            'share',
            'worker_id',
            'worker_name',
            'job',
            'status_logs',
        ]
        read_only_fields = ['id', 'check_in_at', 'created_at', 'updated_at']
        extra_kwargs = {
            'plate_number': {'required': False, 'allow_blank': True},
            'car_model': {'required': False, 'allow_blank': True},
            'car_color': {'required': False, 'allow_blank': True},
            'driver_name': {'required': False, 'allow_blank': True},
            'driver_phone': {'required': False, 'allow_blank': True},
        }

