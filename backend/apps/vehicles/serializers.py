from rest_framework import serializers
from django.db.models import Q
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal

from .models import VehicleEntry
from .models import BlockedPlate
from .models import CustomerProfile
from .models import VehicleJob, VehicleJobService
from .models import VehicleStatusLog
from .models import VehicleJobProduct
from apps.services.models import Service
from apps.workers.models import WorkerProfile
from apps.products.models import Product
from apps.inventory.models import InventoryItem, StockMovement


class VehicleJobServiceLineSerializer(serializers.ModelSerializer):
    service_name = serializers.SerializerMethodField()

    def get_service_name(self, obj):
        return obj.custom_service_name or (obj.service.name if obj.service else 'خدمت')

    class Meta:
        model = VehicleJobService
        fields = [
            'id',
            'service',
            'service_name',
            'custom_service_name',
            'quantity',
            'unit_price',
            'line_total',
            'discount_amount',
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
    assigned_workers_names = serializers.SerializerMethodField()
    assigned_workers_snapshot = serializers.JSONField(read_only=True)
    service_lines = VehicleJobServiceLineSerializer(many=True, read_only=True)

    def _resolve_snapshot_worker_names(self, obj):
        snapshot = obj.assigned_workers_snapshot if isinstance(obj.assigned_workers_snapshot, list) else []
        ordered_ids = []
        names_by_ref = {}
        for item in snapshot:
            if not isinstance(item, dict):
                continue
            try:
                ref_id = int(item.get('id'))
            except (TypeError, ValueError):
                continue
            if ref_id <= 0:
                continue
            if ref_id not in ordered_ids:
                ordered_ids.append(ref_id)
            raw_name = str(item.get('name') or '').strip()
            if raw_name:
                names_by_ref[ref_id] = raw_name

        if obj.assigned_worker_id and obj.assigned_worker_id not in ordered_ids:
            ordered_ids.insert(0, int(obj.assigned_worker_id))

        if not ordered_ids:
            return []

        profiles = list(
            WorkerProfile.objects.select_related('user').filter(
                Q(id__in=ordered_ids) | Q(user_id__in=ordered_ids),
                tenant=obj.tenant,
            )
        )
        profiles_by_id = {profile.id: profile for profile in profiles}
        profiles_by_user_id = {profile.user_id: profile for profile in profiles if profile.user_id}

        names = []
        seen = set()
        for ref_id in ordered_ids:
            resolved_name = names_by_ref.get(ref_id, '')
            profile = profiles_by_id.get(ref_id) or profiles_by_user_id.get(ref_id)
            if not resolved_name and profile and getattr(profile, 'user', None):
                resolved_name = (profile.user.full_name or profile.user.username or '').strip()
            if not resolved_name:
                continue
            if resolved_name in seen:
                continue
            seen.add(resolved_name)
            names.append(resolved_name)
        return names

    def get_assigned_worker_name(self, obj):
        if not obj.assigned_worker or not obj.assigned_worker.user:
            names = self._resolve_snapshot_worker_names(obj)
            return names[0] if names else None
        return obj.assigned_worker.user.full_name or obj.assigned_worker.user.username

    def get_assigned_workers_names(self, obj):
        names = self._resolve_snapshot_worker_names(obj)
        if obj.assigned_worker and obj.assigned_worker.user:
            primary_name = (obj.assigned_worker.user.full_name or obj.assigned_worker.user.username or '').strip()
            if primary_name and primary_name not in names:
                names.insert(0, primary_name)
        return names

    class Meta:
        model = VehicleJob
        fields = [
            'id',
            'assigned_worker',
            'assigned_worker_name',
            'assigned_workers_names',
            'assigned_workers_snapshot',
            'worker_payment_type',
            'worker_payment_percent',
            'worker_payment_fixed',
            'services_total',
            'products_total',
            'discount_total',
            'tax_total',
            'final_total',
            'worker_share_amount',
            'workers_tip_share_amount',
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
    staff_members = serializers.ListField(write_only=True, required=False, default=list)
    tip_amount = serializers.DecimalField(max_digits=12, decimal_places=2, write_only=True, required=False, default=0)
    manual_discount_total = serializers.DecimalField(max_digits=12, decimal_places=2, write_only=True, required=False, default=0)
    share = serializers.DictField(write_only=True, required=False, default=dict)
    worker_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    worker_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    customer_score = serializers.SerializerMethodField()
    customer_score_year = serializers.SerializerMethodField()
    is_plate_blocked = serializers.SerializerMethodField()
    blocked_plate_payment_confirmed = serializers.BooleanField(write_only=True, required=False, default=False)
    job = VehicleJobDetailSerializer(read_only=True)
    status_logs = VehicleStatusLogSerializer(many=True, read_only=True)

    def get_customer_score(self, obj):
        return float(self._plate_yearly_score(obj) or 0)

    def get_customer_score_year(self, obj):
        return timezone.localtime().year

    def get_is_plate_blocked(self, obj):
        return self._is_plate_blocked(
            tenant=getattr(obj, 'tenant', None),
            plate_number=obj.plate_number,
            plate_left=obj.plate_left,
            plate_letter=obj.plate_letter,
            plate_mid=obj.plate_mid,
            plate_right=obj.plate_right,
        )

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(getattr(request, 'user', None), 'tenant', None)
        services_payload = validated_data.pop('services', [])
        products_payload = validated_data.pop('products', [])
        staff_members_payload = validated_data.pop('staff_members', [])
        tip_amount = Decimal(str(validated_data.pop('tip_amount', 0) or 0))
        manual_discount_total = max(Decimal('0'), Decimal(str(validated_data.pop('manual_discount_total', 0) or 0)))
        share_payload = validated_data.pop('share', {})
        blocked_plate_payment_confirmed = bool(validated_data.pop('blocked_plate_payment_confirmed', False))
        worker_id = validated_data.pop('worker_id', None)
        worker_name = (validated_data.pop('worker_name', '') or '').strip()
        requested_status = validated_data.get('status') or VehicleEntry.Status.ENTERED
        if (
            requested_status == VehicleEntry.Status.READY_TO_SETTLE
            and self._is_plate_blocked(
                tenant=tenant,
                plate_number=validated_data.get('plate_number', ''),
                plate_left=validated_data.get('plate_left', ''),
                plate_letter=validated_data.get('plate_letter', ''),
                plate_mid=validated_data.get('plate_mid', ''),
                plate_right=validated_data.get('plate_right', ''),
            )
            and not blocked_plate_payment_confirmed
        ):
            raise serializers.ValidationError(
                {'blocked_plate_payment_confirmed': ['برای پلاک بلاک‌شده باید پرداخت تایید شود.']}
            )
        assigned_worker = None
        if worker_id:
            assigned_worker = WorkerProfile.objects.filter(id=worker_id, tenant=tenant).first()
        if not assigned_worker and worker_name:
            assigned_worker = WorkerProfile.objects.select_related('user').filter(
                Q(user__full_name__iexact=worker_name) | Q(user__username__iexact=worker_name),
                tenant=tenant,
            ).first()

        driver_phone = self._normalize_phone(validated_data.get('driver_phone'))
        driver_name = (validated_data.get('driver_name') or '').strip()
        customer = self._resolve_customer_profile(
            phone=driver_phone,
            full_name=driver_name,
            increment_visit=True,
            tenant=tenant,
        )
        vehicle_entry = VehicleEntry.objects.create(customer=customer, tenant=tenant, **validated_data)

        payment_type = share_payload.get('type', VehicleJob.WorkerPaymentType.PERCENT)
        share_value = share_payload.get('value', 0) or 0
        if assigned_worker:
            if assigned_worker.payment_type == 'hourly' and (assigned_worker.default_hourly_wage or 0) > 0:
                payment_type = VehicleJob.WorkerPaymentType.HOURLY
                share_value = assigned_worker.default_hourly_wage or 0
            elif (assigned_worker.default_fixed_wage or 0) > 0:
                payment_type = VehicleJob.WorkerPaymentType.FIXED
                share_value = assigned_worker.default_fixed_wage or 0
            else:
                payment_type = VehicleJob.WorkerPaymentType.PERCENT
                share_value = assigned_worker.default_commission_percent or 0
        services_total = Decimal('0')
        normalized_services = []
        for item in services_payload:
            unit_price = Decimal(str(item.get('price', 0) or 0))
            discount_amount = max(Decimal('0'), Decimal(str(item.get('discount_amount', 0) or 0)))
            line_total = max(Decimal('0'), unit_price - discount_amount)
            services_total += line_total
            normalized_services.append((item, unit_price, discount_amount, line_total))
        if assigned_worker:
            assigned_worker.last_assigned_at = timezone.now()
            assigned_worker.save(update_fields=['last_assigned_at', 'updated_at'])

        products_total = Decimal('0')
        product_lines_data = []
        for item in products_payload:
            product_id = item.get('id') or item.get('product_id')
            qty = Decimal(str(item.get('quantity', 0) or 0))
            if not product_id or qty <= 0:
                continue
            product = Product.objects.filter(id=product_id, is_active=True, tenant=tenant).first()
            if not product:
                continue
            inventory_item, _created = InventoryItem.objects.select_for_update().get_or_create(
                product=product,
                tenant=tenant,
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
        if payment_type in {VehicleJob.WorkerPaymentType.FIXED, VehicleJob.WorkerPaymentType.HOURLY}:
            worker_share_amount = min(share_base_total, Decimal(str(share_value or 0)))
        else:
            percent = min(Decimal('100'), max(Decimal('0'), Decimal(str(share_value or 0))))
            worker_share_amount = (share_base_total * percent) / Decimal('100')
        carwash_share_amount = share_base_total - worker_share_amount
        final_total = max(Decimal('0'), share_base_total - manual_discount_total) + max(Decimal('0'), tip_amount)

        vehicle_job = VehicleJob.objects.create(
            vehicle=vehicle_entry,
            tenant=tenant,
            assigned_worker=assigned_worker,
            assigned_workers_snapshot=self._normalize_staff_members_payload(staff_members_payload, assigned_worker),
            worker_payment_type=payment_type
            if payment_type in dict(VehicleJob.WorkerPaymentType.choices)
            else VehicleJob.WorkerPaymentType.PERCENT,
            worker_payment_percent=share_value if payment_type == VehicleJob.WorkerPaymentType.PERCENT else 0,
            worker_payment_fixed=share_value if payment_type in {VehicleJob.WorkerPaymentType.FIXED, VehicleJob.WorkerPaymentType.HOURLY} else 0,
            services_total=services_total,
            products_total=products_total,
            manual_discount_total=manual_discount_total,
            tip_amount=max(Decimal('0'), tip_amount),
            final_total=final_total,
            worker_share_amount=worker_share_amount,
            carwash_share_amount=carwash_share_amount,
        )

        for item, unit_price, discount_amount, line_total in normalized_services:
            title = (item.get('title') or '').strip() or 'خدمت بدون نام'
            service_obj, _ = Service.objects.get_or_create(
                name=title,
                tenant=tenant,
                defaults={'base_price': unit_price, 'is_active': True},
            )
            VehicleJobService.objects.create(
                tenant=tenant,
                vehicle_job=vehicle_job,
                service=service_obj,
                custom_service_name=title,
                quantity=1,
                unit_price=unit_price,
                line_total=line_total,
                discount_amount=discount_amount,
                is_completed=False,
                note='ثبت از استپ ۲ پذیرش',
            )

        for item in product_lines_data:
            VehicleJobProduct.objects.create(
                tenant=tenant,
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
                tenant=tenant,
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

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get('request')
        tenant = getattr(getattr(request, 'user', None), 'tenant', None)
        initial = getattr(self, 'initial_data', {}) or {}
        services_provided = 'services' in initial
        share_provided = 'share' in initial
        tip_provided = 'tip_amount' in initial
        manual_discount_provided = 'manual_discount_total' in initial
        worker_id_provided = 'worker_id' in initial
        worker_name_provided = 'worker_name' in initial
        staff_members_provided = 'staff_members' in initial

        services_payload = validated_data.pop('services', None)
        validated_data.pop('products', None)
        staff_members_payload = validated_data.pop('staff_members', None)
        tip_amount_payload = validated_data.pop('tip_amount', None)
        manual_discount_payload = validated_data.pop('manual_discount_total', None)
        share_payload = validated_data.pop('share', None)
        blocked_plate_payment_confirmed = bool(validated_data.pop('blocked_plate_payment_confirmed', False))
        worker_id = validated_data.pop('worker_id', None)
        worker_name = (validated_data.pop('worker_name', '') or '').strip()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        incoming_status = validated_data.get('status', instance.status)
        if (
            incoming_status == VehicleEntry.Status.READY_TO_SETTLE
            and self._is_plate_blocked(
                tenant=tenant,
                plate_number=validated_data.get('plate_number', instance.plate_number),
                plate_left=validated_data.get('plate_left', instance.plate_left),
                plate_letter=validated_data.get('plate_letter', instance.plate_letter),
                plate_mid=validated_data.get('plate_mid', instance.plate_mid),
                plate_right=validated_data.get('plate_right', instance.plate_right),
            )
            and not blocked_plate_payment_confirmed
        ):
            raise serializers.ValidationError(
                {'blocked_plate_payment_confirmed': ['برای پلاک بلاک‌شده باید پرداخت تایید شود.']}
            )

        driver_phone = self._normalize_phone(validated_data.get('driver_phone', instance.driver_phone))
        driver_name = (validated_data.get('driver_name', instance.driver_name) or '').strip()
        if driver_phone:
            instance.customer = self._resolve_customer_profile(
                phone=driver_phone,
                full_name=driver_name,
                increment_visit=False,
                tenant=tenant,
            )

        instance.save()

        should_sync_job = any([
            services_provided,
            share_provided,
            tip_provided,
            manual_discount_provided,
            worker_id_provided,
            worker_name_provided,
            staff_members_provided,
        ])
        if not should_sync_job:
            return instance

        assigned_worker = None
        if worker_id_provided and worker_id:
            assigned_worker = WorkerProfile.objects.filter(id=worker_id, tenant=tenant).first()
        if worker_name_provided and (not assigned_worker) and worker_name:
            assigned_worker = WorkerProfile.objects.select_related('user').filter(
                Q(user__full_name__iexact=worker_name) | Q(user__username__iexact=worker_name),
                tenant=tenant,
            ).first()

        vehicle_job, _ = VehicleJob.objects.get_or_create(
            vehicle=instance,
            defaults={
                'tenant': tenant,
                'assigned_worker': assigned_worker,
                'assigned_workers_snapshot': [],
                'worker_payment_type': VehicleJob.WorkerPaymentType.PERCENT,
                'worker_payment_percent': Decimal('0'),
                'worker_payment_fixed': Decimal('0'),
                'services_total': Decimal('0'),
                'products_total': Decimal('0'),
                'discount_total': Decimal('0'),
                'manual_discount_total': Decimal('0'),
                'tax_total': Decimal('0'),
                'final_total': Decimal('0'),
                'worker_share_amount': Decimal('0'),
                'workers_tip_share_amount': None,
                'carwash_share_amount': Decimal('0'),
                'tip_amount': Decimal('0'),
            },
        )

        if worker_id_provided or worker_name_provided:
            vehicle_job.assigned_worker = assigned_worker
        elif vehicle_job.assigned_worker:
            assigned_worker = vehicle_job.assigned_worker
        if staff_members_provided:
            vehicle_job.assigned_workers_snapshot = self._normalize_staff_members_payload(
                staff_members_payload or [],
                assigned_worker,
            )

        if services_provided:
            vehicle_job.service_lines.all().delete()
            for item in (services_payload or []):
                title = (item.get('title') or '').strip() or 'خدمت بدون نام'
                unit_price = Decimal(str(item.get('price', 0) or 0))
                discount_amount = max(Decimal('0'), Decimal(str(item.get('discount_amount', 0) or 0)))
                line_total = max(Decimal('0'), unit_price - discount_amount)
                service_obj, _ = Service.objects.get_or_create(
                    name=title,
                    tenant=tenant,
                    defaults={'base_price': unit_price, 'is_active': True},
                )
                VehicleJobService.objects.create(
                    tenant=tenant,
                    vehicle_job=vehicle_job,
                    service=service_obj,
                    custom_service_name=title,
                    quantity=1,
                    unit_price=unit_price,
                    line_total=line_total,
                    discount_amount=discount_amount,
                    is_completed=False,
                    note='به‌روزرسانی از استپ ۲ پذیرش',
                )

        services_total = (
            vehicle_job.service_lines.aggregate(total=Sum('line_total')).get('total') or Decimal('0')
        )
        products_total = vehicle_job.products_total or Decimal('0')

        if assigned_worker:
            if assigned_worker.payment_type == 'hourly' and (assigned_worker.default_hourly_wage or 0) > 0:
                payment_type = VehicleJob.WorkerPaymentType.HOURLY
                share_value = Decimal(str(assigned_worker.default_hourly_wage or 0))
            elif (assigned_worker.default_fixed_wage or 0) > 0:
                payment_type = VehicleJob.WorkerPaymentType.FIXED
                share_value = Decimal(str(assigned_worker.default_fixed_wage or 0))
            else:
                payment_type = VehicleJob.WorkerPaymentType.PERCENT
                share_value = Decimal(str(assigned_worker.default_commission_percent or 0))
        else:
            if share_provided and isinstance(share_payload, dict):
                payment_type = share_payload.get('type', vehicle_job.worker_payment_type or VehicleJob.WorkerPaymentType.PERCENT)
                share_value = Decimal(str(share_payload.get('value', 0) or 0))
            else:
                payment_type = vehicle_job.worker_payment_type or VehicleJob.WorkerPaymentType.PERCENT
                share_value = (
                    Decimal(str(vehicle_job.worker_payment_fixed or 0))
                    if payment_type == VehicleJob.WorkerPaymentType.FIXED
                    else Decimal(str(vehicle_job.worker_payment_percent or 0))
                )

        if payment_type not in dict(VehicleJob.WorkerPaymentType.choices):
            payment_type = VehicleJob.WorkerPaymentType.PERCENT

        share_base_total = services_total + products_total
        if payment_type in {VehicleJob.WorkerPaymentType.FIXED, VehicleJob.WorkerPaymentType.HOURLY}:
            fixed_amount = max(Decimal('0'), share_value)
            worker_share_amount = min(share_base_total, fixed_amount)
            payment_percent = Decimal('0')
            payment_fixed = fixed_amount
        else:
            percent = min(Decimal('100'), max(Decimal('0'), share_value))
            worker_share_amount = (share_base_total * percent) / Decimal('100')
            payment_percent = percent
            payment_fixed = Decimal('0')

        manual_discount_total = (
            max(Decimal('0'), Decimal(str(manual_discount_payload or 0)))
            if manual_discount_provided
            else Decimal(str(vehicle_job.manual_discount_total or 0))
        )
        tip_amount = (
            max(Decimal('0'), Decimal(str(tip_amount_payload or 0)))
            if tip_provided
            else Decimal(str(vehicle_job.tip_amount or 0))
        )
        carwash_share_amount = share_base_total - worker_share_amount
        final_total = max(Decimal('0'), share_base_total - manual_discount_total) + tip_amount

        if instance.status == VehicleEntry.Status.READY_TO_SETTLE and not vehicle_job.completed_at:
            vehicle_job.completed_at = timezone.now()
        if (worker_id_provided or worker_name_provided) and assigned_worker:
            assigned_worker.last_assigned_at = timezone.now()
            assigned_worker.save(update_fields=['last_assigned_at', 'updated_at'])

        vehicle_job.worker_payment_type = payment_type
        vehicle_job.worker_payment_percent = payment_percent
        vehicle_job.worker_payment_fixed = payment_fixed
        vehicle_job.services_total = services_total
        vehicle_job.manual_discount_total = manual_discount_total
        vehicle_job.tip_amount = tip_amount
        vehicle_job.final_total = final_total
        vehicle_job.worker_share_amount = worker_share_amount
        vehicle_job.carwash_share_amount = carwash_share_amount
        vehicle_job.save(
            update_fields=[
                'assigned_worker',
                'assigned_workers_snapshot',
                'worker_payment_type',
                'worker_payment_percent',
                'worker_payment_fixed',
                'services_total',
                'manual_discount_total',
                'tip_amount',
                'final_total',
                'worker_share_amount',
                'carwash_share_amount',
                'completed_at',
                'updated_at',
            ]
        )

        return instance

    def _normalize_staff_members_payload(self, payload, assigned_worker=None):
        def _normalized_percent(value):
            try:
                numeric = Decimal(str(value or 0))
            except Exception:
                return None
            if numeric < 0:
                numeric = Decimal('0')
            if numeric > 100:
                numeric = Decimal('100')
            return float(numeric)

        def _normalized_money(value):
            try:
                numeric = Decimal(str(value or 0))
            except Exception:
                return None
            if numeric < 0:
                numeric = Decimal('0')
            return float(numeric)

        result = []
        seen_ids = set()

        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    worker_id = item.get('id')
                    worker_name = (item.get('name') or '').strip()
                    worker_share_percent = _normalized_percent(item.get('worker_share_percent'))
                    worker_share_amount = _normalized_money(item.get('worker_share_amount'))
                    tip_share_percent = _normalized_percent(item.get('tip_share_percent'))
                    tip_share_amount = _normalized_money(item.get('tip_share_amount'))
                else:
                    worker_id = item
                    worker_name = ''
                    worker_share_percent = None
                    worker_share_amount = None
                    tip_share_percent = None
                    tip_share_amount = None
                try:
                    normalized_id = int(worker_id)
                except (TypeError, ValueError):
                    continue
                if normalized_id in seen_ids:
                    continue
                seen_ids.add(normalized_id)
                payload_item = {'id': normalized_id, 'name': worker_name}
                if worker_share_percent is not None:
                    payload_item['worker_share_percent'] = worker_share_percent
                if worker_share_amount is not None:
                    payload_item['worker_share_amount'] = worker_share_amount
                if tip_share_percent is not None:
                    payload_item['tip_share_percent'] = tip_share_percent
                if tip_share_amount is not None:
                    payload_item['tip_share_amount'] = tip_share_amount
                result.append(payload_item)

        if assigned_worker:
            primary_id = int(assigned_worker.id)
            primary_name = (
                assigned_worker.user.full_name or assigned_worker.user.username
            ) if getattr(assigned_worker, 'user', None) else ''
            if primary_id not in seen_ids:
                result.insert(0, {'id': primary_id, 'name': primary_name})
            else:
                for item in result:
                    if int(item.get('id')) == primary_id and not (item.get('name') or '').strip():
                        item['name'] = primary_name
                        break

        return result

    def _resolve_customer_profile(self, phone, full_name='', increment_visit=False, tenant=None):
        phone_value = self._normalize_phone(phone)
        if not phone_value:
            return None

        customer, _ = CustomerProfile.objects.get_or_create(
            phone=phone_value,
            tenant=tenant,
            defaults={
                'full_name': (full_name or '').strip(),
                'yearly_score': Decimal('0'),
                'score_year': timezone.localtime().year,
            },
        )

        update_fields = ['updated_at']
        display_name = (full_name or '').strip()
        if display_name and display_name != (customer.full_name or '').strip():
            customer.full_name = display_name
            update_fields.append('full_name')

        if increment_visit:
            current_year = timezone.localtime().year
            if customer.score_year != current_year:
                customer.score_year = current_year
                customer.yearly_score = Decimal('0')
                update_fields.extend(['score_year', 'yearly_score'])

            next_score = min(Decimal('5.0'), Decimal(str(customer.yearly_score or 0)) + Decimal('0.5'))
            if next_score != Decimal(str(customer.yearly_score or 0)):
                customer.yearly_score = next_score
                if 'yearly_score' not in update_fields:
                    update_fields.append('yearly_score')

        if len(update_fields) > 1:
            customer.save(update_fields=update_fields)

        return customer

    def _normalize_phone(self, value):
        raw = str(value or '').strip()
        if not raw:
            return ''
        persian_digits = '۰۱۲۳۴۵۶۷۸۹'
        arabic_digits = '٠١٢٣٤٥٦٧٨٩'
        translated = []
        for ch in raw:
            if ch in persian_digits:
                translated.append(str(persian_digits.index(ch)))
            elif ch in arabic_digits:
                translated.append(str(arabic_digits.index(ch)))
            else:
                translated.append(ch)
        normalized = ''.join(translated)
        normalized = ''.join(ch for ch in normalized if ch.isdigit() or ch == '+')
        return normalized

    def _plate_yearly_score(self, instance):
        plate_number = str(getattr(instance, 'plate_number', '') or '').strip()
        tenant = getattr(instance, 'tenant', None)
        if not plate_number or not tenant:
            return Decimal('0')
        current_year = timezone.localtime().year
        visits = VehicleEntry.objects.filter(
            tenant=tenant,
            plate_number=plate_number,
            check_in_at__year=current_year,
        ).count()
        return min(Decimal('5.0'), Decimal(str(visits)) * Decimal('0.5'))

    def _normalized_plate(self, plate_number='', plate_left='', plate_letter='', plate_mid='', plate_right=''):
        left = str(plate_left or '').strip()
        letter = str(plate_letter or '').strip()
        mid = str(plate_mid or '').strip()
        right = str(plate_right or '').strip()
        if left and letter and mid and right:
            return f'{left} {letter} {mid} {right}'
        return str(plate_number or '').strip()

    def _is_plate_blocked(self, tenant, plate_number='', plate_left='', plate_letter='', plate_mid='', plate_right=''):
        normalized_plate = self._normalized_plate(
            plate_number=plate_number,
            plate_left=plate_left,
            plate_letter=plate_letter,
            plate_mid=plate_mid,
            plate_right=plate_right,
        )
        if not tenant or not normalized_plate:
            return False
        return BlockedPlate.objects.filter(tenant=tenant, plate_number=normalized_plate).exists()

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
            'is_piece_wash',
            'piece_details',
            'notes',
            'status',
            'payment_status',
            'payment_method',
            'check_in_at',
            'created_at',
            'updated_at',
            'services',
            'products',
            'staff_members',
            'tip_amount',
            'manual_discount_total',
            'blocked_plate_payment_confirmed',
            'share',
            'worker_id',
            'worker_name',
            'customer_score',
            'customer_score_year',
            'is_plate_blocked',
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

