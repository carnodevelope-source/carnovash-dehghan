from rest_framework import serializers
from django.db.models import Q
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .models import VehicleEntry
from .models import BlockedPlate
from .models import CustomerProfile
from .models import PlateLoyaltyProfile
from .models import VehicleJob, VehicleJobService
from .models import VehicleStatusLog
from .models import VehicleJobProduct
from apps.services.models import GeneralSettings, Service, service_tier_keys_for_plate
from apps.workers.models import WorkerProfile
from apps.products.models import Product
from apps.inventory.models import InventoryItem, StockMovement
from apps.notifications.services import send_vehicle_event_sms
from .loyalty import (
    apply_loyalty_visit,
    compute_configured_loyalty_discount,
    get_or_create_plate_loyalty,
    loyalty_snapshot,
    rebuild_customer_score,
    rebuild_plate_loyalty,
    sync_plate_loyalty,
)


VALID_IRAN_MOBILE_PATTERN = r'^0\d{10}$'


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
            'list_unit_price',
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
            'service_list_subtotal',
            'services_total',
            'products_total',
            'discount_total',
            'facility_discount_total',
            'apply_loyalty_discount',
            'loyalty_discount_total',
            'manual_discount_total',
            'total_discount',
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
    plate_number = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    plate_left = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    plate_letter = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    plate_mid = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    plate_right = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    ai_raw_text = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)
    ai_persian_text = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)
    ai_converted_plate = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)
    ai_converted_plate_left = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=True)
    ai_converted_plate_letter = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=True)
    ai_converted_plate_mid = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=True)
    ai_converted_plate_right = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=True)
    ai_converted_plate_type = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=True)
    ai_image_base64 = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)
    ai_session_id = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=True)
    ai_latency_ms = serializers.FloatField(write_only=True, required=False, allow_null=True)
    tariff_type = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    services = serializers.ListField(write_only=True, required=False, default=list)
    products = serializers.ListField(write_only=True, required=False, default=list)
    staff_members = serializers.ListField(write_only=True, required=False, default=list)
    tip_amount = serializers.DecimalField(max_digits=12, decimal_places=2, write_only=True, required=False, default=0)
    manual_discount_total = serializers.DecimalField(max_digits=12, decimal_places=2, write_only=True, required=False, default=0)
    apply_loyalty_discount = serializers.BooleanField(write_only=True, required=False, default=True)
    share = serializers.DictField(write_only=True, required=False, default=dict)
    worker_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    worker_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    customer_score = serializers.SerializerMethodField()
    customer_score_year = serializers.SerializerMethodField()
    customer_loyalty_visit_count = serializers.SerializerMethodField()
    customer_loyalty_discount_percent = serializers.SerializerMethodField()
    is_plate_blocked = serializers.SerializerMethodField()
    blocked_plate_id = serializers.SerializerMethodField()
    blocked_plate_payment_confirmed = serializers.BooleanField(write_only=True, required=False, default=False)
    job = VehicleJobDetailSerializer(read_only=True)
    status_logs = VehicleStatusLogSerializer(many=True, read_only=True)
    _AI_AUDIT_FIELDS = [
        'ai_raw_text',
        'ai_persian_text',
        'ai_converted_plate',
        'ai_converted_plate_left',
        'ai_converted_plate_letter',
        'ai_converted_plate_mid',
        'ai_converted_plate_right',
        'ai_converted_plate_type',
        'ai_image_base64',
        'ai_session_id',
        'ai_latency_ms',
    ]

    def _motorcycle_plate_digits(self, value, limit):
        return ''.join(ch for ch in self._normalize_phone(value) if ch.isdigit())[:limit]

    def _plate_digits(self, value, limit):
        return ''.join(ch for ch in self._normalize_phone(value) if ch.isdigit())[:limit]

    def _car_plate_letter(self, value):
        token = str(value or '').strip().replace('ك', 'ک').replace('ي', 'ی')
        if not token:
            return ''
        if token.startswith('الف'):
            return 'الف'
        for char in token:
            if char.isdigit() or char.isspace():
                continue
            return char
        return ''

    def _normalize_ai_confidence(self, value):
        if value in (None, ''):
            return None
        try:
            normalized = Decimal(str(value))
            if not normalized.is_finite():
                return None
            normalized = normalized.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError):
            return value
        return min(Decimal('999.99'), max(Decimal('0.00'), normalized))

    def to_internal_value(self, data):
        if isinstance(data, dict):
            mutable_data = data.copy()
            if 'ai_confidence' in mutable_data:
                mutable_data['ai_confidence'] = self._normalize_ai_confidence(
                    mutable_data.get('ai_confidence')
                )
            plate_type = str(mutable_data.get('plate_type') or '').strip().lower()
            if plate_type not in {VehicleEntry.PlateType.CAR, VehicleEntry.PlateType.MOTORCYCLE}:
                data = mutable_data
                mutable_data = None
            if mutable_data is not None and plate_type == VehicleEntry.PlateType.MOTORCYCLE:
                mutable_data['plate_left'] = ''
                mutable_data['plate_right'] = ''
                mutable_data['plate_mid'] = self._motorcycle_plate_digits(
                    mutable_data.get('plate_mid') or mutable_data.get('ai_converted_plate_mid') or '',
                    3,
                )
                mutable_data['plate_letter'] = self._motorcycle_plate_digits(
                    mutable_data.get('plate_letter') or mutable_data.get('ai_converted_plate_letter') or '',
                    5,
                )
                mutable_data['ai_converted_plate_left'] = ''
                mutable_data['ai_converted_plate_right'] = ''
                if mutable_data.get('ai_converted_plate_mid') or mutable_data.get('ai_converted_plate_letter'):
                    mutable_data['ai_converted_plate_mid'] = self._motorcycle_plate_digits(
                        mutable_data.get('ai_converted_plate_mid') or mutable_data.get('plate_mid') or '',
                        3,
                    )
                    mutable_data['ai_converted_plate_letter'] = self._motorcycle_plate_digits(
                        mutable_data.get('ai_converted_plate_letter') or mutable_data.get('plate_letter') or '',
                        5,
                    )
                data = mutable_data
            elif mutable_data is not None and plate_type == VehicleEntry.PlateType.CAR:
                mutable_data['plate_left'] = self._plate_digits(
                    mutable_data.get('plate_left') or mutable_data.get('ai_converted_plate_left') or '',
                    2,
                )
                mutable_data['plate_mid'] = self._plate_digits(
                    mutable_data.get('plate_mid') or mutable_data.get('ai_converted_plate_mid') or '',
                    3,
                )
                mutable_data['plate_right'] = self._plate_digits(
                    mutable_data.get('plate_right') or mutable_data.get('ai_converted_plate_right') or '',
                    2,
                )
                mutable_data['plate_letter'] = self._car_plate_letter(
                    mutable_data.get('plate_letter') or mutable_data.get('ai_converted_plate_letter') or ''
                )
                if mutable_data.get('ai_converted_plate_left') or mutable_data.get('ai_converted_plate_mid') or mutable_data.get('ai_converted_plate_right') or mutable_data.get('ai_converted_plate_letter'):
                    mutable_data['ai_converted_plate_left'] = self._plate_digits(
                        mutable_data.get('ai_converted_plate_left') or mutable_data.get('plate_left') or '',
                        2,
                    )
                    mutable_data['ai_converted_plate_mid'] = self._plate_digits(
                        mutable_data.get('ai_converted_plate_mid') or mutable_data.get('plate_mid') or '',
                        3,
                    )
                    mutable_data['ai_converted_plate_right'] = self._plate_digits(
                        mutable_data.get('ai_converted_plate_right') or mutable_data.get('plate_right') or '',
                        2,
                    )
                    mutable_data['ai_converted_plate_letter'] = self._car_plate_letter(
                        mutable_data.get('ai_converted_plate_letter') or mutable_data.get('plate_letter') or ''
                    )
                data = mutable_data
        return super().to_internal_value(data)

    def _discard_ai_audit_fields(self, validated_data):
        for field in self._AI_AUDIT_FIELDS:
            validated_data.pop(field, None)

    def get_customer_score(self, obj):
        return loyalty_snapshot(self._plate_loyalty(obj)).get('score', 0)

    def get_customer_score_year(self, obj):
        return timezone.localtime().year

    def get_customer_loyalty_visit_count(self, obj):
        return loyalty_snapshot(self._plate_loyalty(obj)).get('visit_count', 0)

    def get_customer_loyalty_discount_percent(self, obj):
        loyalty = loyalty_snapshot(self._plate_loyalty(obj))
        settings_obj = self._general_settings(getattr(obj, 'tenant', None))
        discount_percent, _discount_amount = compute_configured_loyalty_discount(
            base_amount=0,
            profile=self._plate_loyalty(obj),
            settings_obj=settings_obj,
            visit_count=loyalty.get('visit_count', 0),
            score=loyalty.get('score', 0),
        )
        return float(discount_percent or 0)

    def get_is_plate_blocked(self, obj):
        return bool(self._cached_blocked_plate(obj))

    def get_blocked_plate_id(self, obj):
        blocked = self._cached_blocked_plate(obj)
        return blocked.id if blocked else None

    def _cached_blocked_plate(self, obj):
        cache = getattr(self, '_blocked_plate_cache', None)
        if cache is None:
            cache = {}
            self._blocked_plate_cache = cache
        key = getattr(obj, 'pk', None) or id(obj)
        if key not in cache:
            cache[key] = self._find_blocked_plate_record(
                tenant=getattr(obj, 'tenant', None),
                plate_number=obj.plate_number,
                plate_left=obj.plate_left,
                plate_letter=obj.plate_letter,
                plate_mid=obj.plate_mid,
                plate_right=obj.plate_right,
            )
        return cache[key]

    def _assigned_worker_ids_from_payload(self, payload, assigned_worker=None):
        worker_ids = []
        if assigned_worker:
            worker_ids.append(int(assigned_worker.id))
        if isinstance(payload, list):
            for item in payload:
                worker_id = item.get('id') if isinstance(item, dict) else item
                try:
                    normalized_id = int(worker_id)
                except (TypeError, ValueError):
                    continue
                if normalized_id > 0:
                    worker_ids.append(normalized_id)
        return list(dict.fromkeys(worker_ids))

    def _mark_workers_assigned(self, tenant, payload, assigned_worker=None):
        worker_ids = self._assigned_worker_ids_from_payload(payload, assigned_worker)
        if not worker_ids:
            return
        assigned_at = timezone.now()
        WorkerProfile.objects.filter(tenant=tenant, id__in=worker_ids, user__role='worker').update(
            last_assigned_at=assigned_at,
            updated_at=assigned_at,
        )

    def _resolve_worker_payment_defaults(self, tenant, payload, assigned_worker=None):
        worker_ids = self._assigned_worker_ids_from_payload(payload, assigned_worker)
        if not worker_ids:
            return None, None

        profiles = list(WorkerProfile.objects.filter(tenant=tenant, id__in=worker_ids, user__role='worker'))
        if not profiles:
            return None, None

        profiles_by_id = {profile.id: profile for profile in profiles}
        ordered_profiles = [profiles_by_id[worker_id] for worker_id in worker_ids if worker_id in profiles_by_id]
        if not ordered_profiles:
            return None, None

        payment_configs = []
        for profile in ordered_profiles:
            if profile.payment_type == 'hourly' and (profile.default_hourly_wage or 0) > 0:
                payment_configs.append((VehicleJob.WorkerPaymentType.HOURLY, Decimal(str(profile.default_hourly_wage or 0))))
            elif profile.payment_type == 'fixed' or (profile.default_fixed_wage or 0) > 0:
                payment_configs.append((VehicleJob.WorkerPaymentType.FIXED, Decimal(str(profile.default_fixed_wage or 0))))
            else:
                payment_configs.append((VehicleJob.WorkerPaymentType.PERCENT, Decimal(str(profile.default_commission_percent or 0))))

        if len(payment_configs) == 1:
            return payment_configs[0]

        unique_types = {config[0] for config in payment_configs}
        if len(unique_types) == 1:
            average_value = sum((config[1] for config in payment_configs), Decimal('0')) / Decimal(str(len(payment_configs)))
            return payment_configs[0][0], average_value

        return payment_configs[0]

    def _normalized_tariff_type(self, value, *, plate_type='car'):
        normalized = str(value or VehicleEntry.TariffType.TYPE_1).strip().lower() or VehicleEntry.TariffType.TYPE_1
        allowed = set(service_tier_keys_for_plate(plate_type))
        if normalized not in allowed:
            return VehicleEntry.TariffType.TYPE_1
        return normalized

    def _resolve_service_defaults(self, service_obj, *, tariff_type, plate_type, fallback_price):
        if service_obj:
            pricing = service_obj.resolve_pricing(tariff_type=tariff_type, plate_type=plate_type)
            return (
                Decimal(str(pricing.get('list_price', fallback_price) or 0)),
                Decimal(str(pricing.get('sale_price', fallback_price) or 0)),
            )
        normalized = Decimal(str(fallback_price or 0))
        return normalized, normalized

    def _discount_percent_per_half_star(self, tenant):
        settings_obj = GeneralSettings.objects.filter(tenant=tenant).order_by('id').first()
        return Decimal(str(getattr(settings_obj, 'discount_percent_per_half_star', 0) or 0))

    def _general_settings(self, tenant):
        return GeneralSettings.objects.filter(tenant=tenant).order_by('id').first()

    def _tax_percent(self, tenant):
        settings_obj = GeneralSettings.objects.filter(tenant=tenant).order_by('id').first()
        if not getattr(settings_obj, 'tax_enabled', False):
            return Decimal('0')
        return min(Decimal('100'), max(Decimal('0'), Decimal(str(getattr(settings_obj, 'tax_percent', 0) or 0))))

    def _plate_loyalty(self, instance):
        profile = get_or_create_plate_loyalty(
            tenant=getattr(instance, 'tenant', None),
            plate_number=getattr(instance, 'plate_number', ''),
            plate_left=getattr(instance, 'plate_left', ''),
            plate_letter=getattr(instance, 'plate_letter', ''),
            plate_mid=getattr(instance, 'plate_mid', ''),
            plate_right=getattr(instance, 'plate_right', ''),
        )
        return sync_plate_loyalty(
            profile,
            discount_percent_per_half_star=self._discount_percent_per_half_star(
                getattr(instance, 'tenant', None)
            ),
        )

    def _compute_job_financials(
        self,
        *,
        service_lines,
        products_total,
        manual_discount_total,
        tip_amount,
        loyalty_score,
        discount_percent_per_half_star,
        loyalty_profile=None,
        settings_obj=None,
        apply_loyalty_discount=True,
        tax_percent=Decimal('0'),
    ):
        service_list_subtotal = Decimal('0')
        services_total = Decimal('0')
        facility_discount_total = Decimal('0')
        for line in service_lines:
            quantity = Decimal(str(line.get('quantity', 1) or 1))
            list_unit_price = Decimal(str(line.get('list_unit_price', 0) or 0))
            unit_price = Decimal(str(line.get('unit_price', 0) or 0))
            line_total = Decimal(str(line.get('line_total', 0) or 0))
            discount_amount = Decimal(str(line.get('discount_amount', 0) or 0))
            list_line_total = (
                list_unit_price * quantity
                if list_unit_price > 0
                else line_total + discount_amount
            )
            service_list_subtotal += list_line_total
            services_total += line_total
            facility_discount_total += max(Decimal('0'), list_line_total - line_total)

        if apply_loyalty_discount:
            loyalty_discount_percent, loyalty_discount_total = compute_configured_loyalty_discount(
                base_amount=service_list_subtotal,
                profile=loyalty_profile,
                settings_obj=settings_obj,
                visit_count=getattr(loyalty_profile, 'visit_count', 0) if loyalty_profile is not None else 0,
                score=loyalty_score,
            )
        else:
            loyalty_discount_percent, loyalty_discount_total = Decimal('0'), Decimal('0')
        total_discount = min(
            service_list_subtotal,
            facility_discount_total + loyalty_discount_total + manual_discount_total,
        )
        taxable_total = max(Decimal('0'), service_list_subtotal - total_discount) + products_total
        tax_total = (taxable_total * Decimal(str(tax_percent or 0))) / Decimal('100')
        final_total = taxable_total + tax_total + tip_amount
        return {
            'service_list_subtotal': service_list_subtotal,
            'services_total': services_total,
            'facility_discount_total': facility_discount_total,
            'loyalty_discount_percent': loyalty_discount_percent,
            'loyalty_discount_total': loyalty_discount_total,
            'manual_discount_total': manual_discount_total,
            'total_discount': total_discount,
            'discount_total': total_discount,
            'tax_total': tax_total,
            'final_total': final_total,
        }

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(getattr(request, 'user', None), 'tenant', None)
        self._discard_ai_audit_fields(validated_data)
        services_payload = validated_data.pop('services', [])
        products_payload = validated_data.pop('products', [])
        staff_members_payload = validated_data.pop('staff_members', [])
        tip_amount = Decimal(str(validated_data.pop('tip_amount', 0) or 0))
        manual_discount_total = max(Decimal('0'), Decimal(str(validated_data.pop('manual_discount_total', 0) or 0)))
        apply_loyalty_discount = bool(validated_data.pop('apply_loyalty_discount', True))
        share_payload = validated_data.pop('share', {})
        blocked_plate_payment_confirmed = bool(validated_data.pop('blocked_plate_payment_confirmed', False))
        worker_id = validated_data.pop('worker_id', None)
        worker_name = (validated_data.pop('worker_name', '') or '').strip()
        requested_status = validated_data.get('status') or VehicleEntry.Status.ENTERED
        plate_type = validated_data.get('plate_type') or VehicleEntry.PlateType.CAR
        validated_data['tariff_type'] = self._normalized_tariff_type(
            validated_data.get('tariff_type'),
            plate_type=plate_type,
        )
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
            assigned_worker = WorkerProfile.objects.filter(id=worker_id, tenant=tenant, user__role='worker').first()
        if not assigned_worker and worker_name:
            assigned_worker = WorkerProfile.objects.select_related('user').filter(
                Q(user__full_name__iexact=worker_name) | Q(user__username__iexact=worker_name),
                tenant=tenant,
                user__role='worker',
            ).first()

        driver_phone = self._normalize_phone(validated_data.get('driver_phone'))
        driver_name = (validated_data.get('driver_name') or '').strip()
        customer = self._resolve_customer_profile(
            phone=driver_phone,
            full_name=driver_name,
            gender=validated_data.get('driver_gender', ''),
            increment_visit=requested_status != VehicleEntry.Status.CANCELLED,
            tenant=tenant,
        )
        if requested_status == VehicleEntry.Status.READY_TO_SETTLE and not validated_data.get('ready_at'):
            validated_data['ready_at'] = timezone.now()
        if requested_status == VehicleEntry.Status.RELEASED and not validated_data.get('released_at'):
            validated_data['released_at'] = timezone.now()
        vehicle_entry = VehicleEntry.objects.create(customer=customer, tenant=tenant, **validated_data)
        settings_obj = self._general_settings(tenant)
        discount_percent_per_half_star = Decimal(str(getattr(settings_obj, 'discount_percent_per_half_star', 0) or 0))
        loyalty_profile = None
        if not vehicle_entry.is_piece_wash:
            loyalty_profile = get_or_create_plate_loyalty(
                tenant=tenant,
                plate_number=vehicle_entry.plate_number,
                plate_left=vehicle_entry.plate_left,
                plate_letter=vehicle_entry.plate_letter,
                plate_mid=vehicle_entry.plate_mid,
                plate_right=vehicle_entry.plate_right,
            )
            if requested_status != VehicleEntry.Status.CANCELLED:
                loyalty_profile = apply_loyalty_visit(
                    loyalty_profile,
                    discount_percent_per_half_star=discount_percent_per_half_star,
                )

        payment_type = share_payload.get('type', VehicleJob.WorkerPaymentType.PERCENT)
        share_value = share_payload.get('value', 0) or 0
        resolved_payment_type, resolved_share_value = self._resolve_worker_payment_defaults(
            tenant=tenant,
            payload=staff_members_payload,
            assigned_worker=assigned_worker,
        )
        if resolved_payment_type:
            payment_type = resolved_payment_type
            share_value = resolved_share_value or 0
        normalized_services = []
        for item in services_payload:
            service_obj = None
            service_id = item.get('id') or item.get('service_id')
            if service_id:
                service_obj = Service.objects.filter(id=service_id, tenant=tenant, is_active=True).first()
            list_unit_price, unit_price = self._resolve_service_defaults(
                service_obj,
                tariff_type=validated_data.get('tariff_type'),
                plate_type=plate_type,
                fallback_price=item.get('price', 0),
            )
            incoming_price = max(Decimal('0'), Decimal(str(item.get('price') or 0))) if 'price' in item else unit_price
            incoming_discount_amount = max(Decimal('0'), Decimal(str(item.get('discount_amount', 0) or 0)))
            manual_price_override = (
                bool(item.get('manual_price_override') or item.get('is_manual_price_override'))
                or ('price' in item and incoming_discount_amount == Decimal('0') and incoming_price != unit_price)
            )
            if manual_price_override:
                unit_price = incoming_price
                list_unit_price = unit_price
            discount_amount = Decimal('0') if manual_price_override else incoming_discount_amount
            line_total = max(Decimal('0'), unit_price - discount_amount)
            normalized_services.append((item, service_obj, list_unit_price, unit_price, discount_amount, line_total))
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

        financials = self._compute_job_financials(
            service_lines=[
                {
                    'quantity': 1,
                    'list_unit_price': list_unit_price,
                    'unit_price': unit_price,
                    'line_total': line_total,
                }
                for _item, _service_obj, list_unit_price, unit_price, _discount_amount, line_total in normalized_services
            ],
            products_total=products_total,
            manual_discount_total=manual_discount_total,
            tip_amount=max(Decimal('0'), tip_amount),
            loyalty_score=getattr(
                loyalty_profile,
                '_loyalty_visit_score',
                getattr(loyalty_profile, 'score', Decimal('0')),
            ),
            discount_percent_per_half_star=discount_percent_per_half_star,
            loyalty_profile=loyalty_profile,
            settings_obj=settings_obj,
            apply_loyalty_discount=apply_loyalty_discount,
            tax_percent=self._tax_percent(tenant),
        )
        services_total = financials['services_total']
        share_base_total = services_total + products_total
        if payment_type in {VehicleJob.WorkerPaymentType.FIXED, VehicleJob.WorkerPaymentType.HOURLY}:
            worker_share_amount = min(share_base_total, Decimal(str(share_value or 0)))
        else:
            percent = min(Decimal('100'), max(Decimal('0'), Decimal(str(share_value or 0))))
            worker_share_amount = (share_base_total * percent) / Decimal('100')
        carwash_share_amount = share_base_total - worker_share_amount

        vehicle_job = VehicleJob.objects.create(
            vehicle=vehicle_entry,
            tenant=tenant,
            assigned_worker=assigned_worker,
            assigned_workers_snapshot=self._normalize_staff_members_payload(
                staff_members_payload,
                assigned_worker,
                tenant=tenant,
            ),
            worker_payment_type=payment_type
            if payment_type in dict(VehicleJob.WorkerPaymentType.choices)
            else VehicleJob.WorkerPaymentType.PERCENT,
            worker_payment_percent=share_value if payment_type == VehicleJob.WorkerPaymentType.PERCENT else 0,
            worker_payment_fixed=share_value if payment_type in {VehicleJob.WorkerPaymentType.FIXED, VehicleJob.WorkerPaymentType.HOURLY} else 0,
            service_list_subtotal=financials['service_list_subtotal'],
            services_total=services_total,
            products_total=products_total,
            discount_total=financials['discount_total'],
            facility_discount_total=financials['facility_discount_total'],
            apply_loyalty_discount=apply_loyalty_discount,
            loyalty_discount_total=financials['loyalty_discount_total'],
            manual_discount_total=manual_discount_total,
            total_discount=financials['total_discount'],
            tax_total=financials['tax_total'],
            tip_amount=max(Decimal('0'), tip_amount),
            final_total=financials['final_total'],
            worker_share_amount=worker_share_amount,
            carwash_share_amount=carwash_share_amount,
        )
        self._mark_workers_assigned(tenant, staff_members_payload, assigned_worker)

        for item, service_obj, list_unit_price, unit_price, discount_amount, line_total in normalized_services:
            title = (item.get('title') or '').strip() or 'خدمت بدون نام'
            if not service_obj:
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
                list_unit_price=list_unit_price,
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

        if requested_status == VehicleEntry.Status.READY_TO_SETTLE:
            send_vehicle_event_sms(
                'vehicle_assigned',
                tenant,
                vehicle_entry,
                created_by=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
                extra_context={'assigned_at': vehicle_entry.ready_at or vehicle_entry.updated_at},
            )

        return vehicle_entry

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get('request')
        tenant = getattr(getattr(request, 'user', None), 'tenant', None)
        self._discard_ai_audit_fields(validated_data)
        previous_status = instance.status
        initial = getattr(self, 'initial_data', {}) or {}
        services_provided = 'services' in initial
        share_provided = 'share' in initial
        tip_provided = 'tip_amount' in initial
        manual_discount_provided = 'manual_discount_total' in initial
        apply_loyalty_provided = 'apply_loyalty_discount' in initial
        worker_id_provided = 'worker_id' in initial
        worker_name_provided = 'worker_name' in initial
        staff_members_provided = 'staff_members' in initial

        services_payload = validated_data.pop('services', None)
        validated_data.pop('products', None)
        staff_members_payload = validated_data.pop('staff_members', None)
        tip_amount_payload = validated_data.pop('tip_amount', None)
        manual_discount_payload = validated_data.pop('manual_discount_total', None)
        apply_loyalty_payload = validated_data.pop('apply_loyalty_discount', None)
        share_payload = validated_data.pop('share', None)
        plate_type = validated_data.get('plate_type') or getattr(instance, 'plate_type', VehicleEntry.PlateType.CAR)
        if 'tariff_type' in validated_data:
            validated_data['tariff_type'] = self._normalized_tariff_type(
                validated_data.get('tariff_type'),
                plate_type=plate_type,
            )
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
                gender=validated_data.get('driver_gender', instance.driver_gender),
                increment_visit=False,
                tenant=tenant,
            )

        instance.save()
        if incoming_status == VehicleEntry.Status.CANCELLED and previous_status != VehicleEntry.Status.CANCELLED:
            rebuild_customer_score(instance.customer)
            if not instance.is_piece_wash:
                rebuild_plate_loyalty(
                    self._plate_loyalty(instance),
                    discount_percent_per_half_star=self._discount_percent_per_half_star(tenant),
                )

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
            assigned_worker = WorkerProfile.objects.filter(id=worker_id, tenant=tenant, user__role='worker').first()
        if worker_name_provided and (not assigned_worker) and worker_name:
            assigned_worker = WorkerProfile.objects.select_related('user').filter(
                Q(user__full_name__iexact=worker_name) | Q(user__username__iexact=worker_name),
                tenant=tenant,
                user__role='worker',
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
                'service_list_subtotal': Decimal('0'),
                'services_total': Decimal('0'),
                'products_total': Decimal('0'),
                'discount_total': Decimal('0'),
                'facility_discount_total': Decimal('0'),
                'loyalty_discount_total': Decimal('0'),
                'manual_discount_total': Decimal('0'),
                'total_discount': Decimal('0'),
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
                tenant=tenant,
            )

        if services_provided:
            vehicle_job.service_lines.all().delete()
            for item in (services_payload or []):
                title = (item.get('title') or '').strip() or 'خدمت بدون نام'
                service_obj = None
                service_id = item.get('id') or item.get('service_id')
                if service_id:
                    service_obj = Service.objects.filter(id=service_id, tenant=tenant, is_active=True).first()
                list_unit_price, unit_price = self._resolve_service_defaults(
                    service_obj,
                    tariff_type=validated_data.get('tariff_type', getattr(instance, 'tariff_type', VehicleEntry.TariffType.TYPE_1)),
                    plate_type=plate_type,
                    fallback_price=item.get('price', 0),
                )
                incoming_price = max(Decimal('0'), Decimal(str(item.get('price') or 0))) if 'price' in item else unit_price
                incoming_discount_amount = max(Decimal('0'), Decimal(str(item.get('discount_amount', 0) or 0)))
                manual_price_override = (
                    bool(item.get('manual_price_override') or item.get('is_manual_price_override'))
                    or ('price' in item and incoming_discount_amount == Decimal('0') and incoming_price != unit_price)
                )
                if manual_price_override:
                    unit_price = incoming_price
                    list_unit_price = unit_price
                discount_amount = Decimal('0') if manual_price_override else incoming_discount_amount
                line_total = max(Decimal('0'), unit_price - discount_amount)
                if not service_obj:
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
                    list_unit_price=list_unit_price,
                    unit_price=unit_price,
                    line_total=line_total,
                    discount_amount=discount_amount,
                    is_completed=False,
                    note='به‌روزرسانی از استپ ۲ پذیرش',
                )

        service_lines = list(vehicle_job.service_lines.all())
        services_total = vehicle_job.service_lines.aggregate(total=Sum('line_total')).get('total') or Decimal('0')
        products_total = vehicle_job.products_total or Decimal('0')

        resolved_payment_type, resolved_share_value = self._resolve_worker_payment_defaults(
            tenant=tenant,
            payload=staff_members_payload if staff_members_provided else (vehicle_job.assigned_workers_snapshot or []),
            assigned_worker=assigned_worker,
        )
        if resolved_payment_type:
            payment_type = resolved_payment_type
            share_value = Decimal(str(resolved_share_value or 0))
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
        apply_loyalty_discount = (
            bool(apply_loyalty_payload)
            if apply_loyalty_provided
            else bool(getattr(vehicle_job, 'apply_loyalty_discount', True))
        )
        tip_amount = (
            max(Decimal('0'), Decimal(str(tip_amount_payload or 0)))
            if tip_provided
            else Decimal(str(vehicle_job.tip_amount or 0))
        )
        loyalty_profile = None if instance.is_piece_wash else self._plate_loyalty(instance)
        settings_obj = self._general_settings(tenant)
        discount_percent_per_half_star = Decimal(str(getattr(settings_obj, 'discount_percent_per_half_star', 0) or 0))
        financials = self._compute_job_financials(
            service_lines=[
                {
                    'quantity': line.quantity,
                    'list_unit_price': line.list_unit_price,
                    'unit_price': line.unit_price,
                    'line_total': line.line_total,
                }
                for line in service_lines
            ],
            products_total=products_total,
            manual_discount_total=manual_discount_total,
            tip_amount=tip_amount,
            loyalty_score=getattr(
                loyalty_profile,
                '_loyalty_visit_score',
                getattr(loyalty_profile, 'score', Decimal('0')),
            ),
            discount_percent_per_half_star=discount_percent_per_half_star,
            loyalty_profile=loyalty_profile,
            settings_obj=settings_obj,
            apply_loyalty_discount=apply_loyalty_discount,
            tax_percent=self._tax_percent(tenant),
        )
        carwash_share_amount = share_base_total - worker_share_amount
        final_total = financials['final_total']

        if instance.status == VehicleEntry.Status.READY_TO_SETTLE and not vehicle_job.completed_at:
            vehicle_job.completed_at = timezone.now()
        if worker_id_provided or worker_name_provided or staff_members_provided:
            self._mark_workers_assigned(
                tenant,
                staff_members_payload or [],
                assigned_worker,
            )

        vehicle_job.worker_payment_type = payment_type
        vehicle_job.worker_payment_percent = payment_percent
        vehicle_job.worker_payment_fixed = payment_fixed
        vehicle_job.service_list_subtotal = financials['service_list_subtotal']
        vehicle_job.services_total = services_total
        vehicle_job.products_total = products_total
        vehicle_job.discount_total = financials['discount_total']
        vehicle_job.facility_discount_total = financials['facility_discount_total']
        vehicle_job.apply_loyalty_discount = apply_loyalty_discount
        vehicle_job.loyalty_discount_total = financials['loyalty_discount_total']
        vehicle_job.manual_discount_total = manual_discount_total
        vehicle_job.total_discount = financials['total_discount']
        vehicle_job.tax_total = financials['tax_total']
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
                'service_list_subtotal',
                'services_total',
                'products_total',
                'discount_total',
                'facility_discount_total',
                'apply_loyalty_discount',
                'loyalty_discount_total',
                'manual_discount_total',
                'total_discount',
                'tax_total',
                'tip_amount',
                'final_total',
                'worker_share_amount',
                'carwash_share_amount',
                'completed_at',
                'updated_at',
            ]
        )

        if instance.status == VehicleEntry.Status.READY_TO_SETTLE and previous_status != VehicleEntry.Status.READY_TO_SETTLE:
            if not instance.ready_at:
                instance.ready_at = timezone.now()
                instance.save(update_fields=['ready_at', 'updated_at'])
            send_vehicle_event_sms(
                'vehicle_assigned',
                tenant,
                instance,
                created_by=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
                extra_context={'assigned_at': instance.ready_at or instance.updated_at},
            )

        return instance

    def validate_plate_type(self, value):
        normalized = str(value or VehicleEntry.PlateType.CAR).strip().lower()
        valid_choices = {choice[0] for choice in VehicleEntry.PlateType.choices}
        if normalized not in valid_choices:
            raise serializers.ValidationError('نوع پلاک نامعتبر است.')
        return normalized

    def validate_tariff_type(self, value):
        return str(value or VehicleEntry.TariffType.TYPE_1).strip().lower()

    def _incoming_plate_type(self):
        if isinstance(getattr(self, 'initial_data', None), dict):
            raw_value = self.initial_data.get('plate_type')
            if raw_value:
                return str(raw_value).strip().lower()
        return str(getattr(self.instance, 'plate_type', VehicleEntry.PlateType.CAR) or VehicleEntry.PlateType.CAR).strip().lower()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        plate_type = str(
            attrs.get('plate_type')
            or getattr(self.instance, 'plate_type', VehicleEntry.PlateType.CAR)
            or VehicleEntry.PlateType.CAR
        ).strip().lower()
        attrs['tariff_type'] = self._normalized_tariff_type(
            attrs.get('tariff_type', getattr(self.instance, 'tariff_type', VehicleEntry.TariffType.TYPE_1)),
            plate_type=plate_type,
        )
        if plate_type == VehicleEntry.PlateType.MOTORCYCLE:
            attrs['plate_left'] = ''
            attrs['plate_right'] = ''
            attrs['plate_mid'] = str(attrs.get('plate_mid', getattr(self.instance, 'plate_mid', '')) or '').strip()[:3]
            attrs['plate_letter'] = str(attrs.get('plate_letter', getattr(self.instance, 'plate_letter', '')) or '').strip()[:5]
            if attrs['plate_mid'] and attrs['plate_letter']:
                attrs['plate_number'] = f"{attrs['plate_mid']} {attrs['plate_letter']}"
        return attrs

    def validate_plate_left(self, value):
        if self._incoming_plate_type() == VehicleEntry.PlateType.MOTORCYCLE:
            return ''
        normalized = str(value or '').strip()
        if len(normalized) > 2:
            raise serializers.ValidationError('بخش آبی پلاک باید حداکثر ۲ کاراکتر باشد.')
        return normalized

    def validate_plate_right(self, value):
        if self._incoming_plate_type() == VehicleEntry.PlateType.MOTORCYCLE:
            return ''
        normalized = str(value or '').strip()
        if len(normalized) > 2:
            raise serializers.ValidationError('بخش دو رقمی پلاک باید حداکثر ۲ کاراکتر باشد.')
        return normalized

    def validate_plate_mid(self, value):
        normalized = str(value or '').strip()
        if self._incoming_plate_type() == VehicleEntry.PlateType.MOTORCYCLE:
            return ''.join(ch for ch in self._normalize_phone(normalized) if ch.isdigit())[:3]
        if len(normalized) > 3:
            raise serializers.ValidationError('بخش سه رقمی پلاک باید حداکثر ۳ کاراکتر باشد.')
        return normalized

    def validate_plate_letter(self, value):
        normalized = str(value or '').strip()
        if self._incoming_plate_type() == VehicleEntry.PlateType.MOTORCYCLE:
            return ''.join(ch for ch in self._normalize_phone(normalized) if ch.isdigit())[:5]
        if len(normalized) > 5:
            raise serializers.ValidationError('بخش حرف پلاک بیش از حد مجاز است.')
        return normalized

    def validate_driver_phone(self, value):
        phone = self._normalize_phone(value)
        requested_status = (
            self.initial_data.get('status')
            if isinstance(getattr(self, 'initial_data', None), dict)
            else None
        ) or VehicleEntry.Status.ENTERED
        if requested_status == VehicleEntry.Status.ENTERED and not phone:
            return ''
        if not phone:
            raise serializers.ValidationError('شماره تماس الزامی است.')
        if len(phone) != 11 or not phone.startswith('09'):
            raise serializers.ValidationError('شماره تماس باید دقیقا 11 رقم و با 09 شروع شود.')
        return phone

    def _normalize_staff_members_payload(self, payload, assigned_worker=None, tenant=None):
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

        allowed_worker_ids = None
        if tenant is not None:
            raw_ids = []
            if isinstance(payload, list):
                for item in payload:
                    worker_id = item.get('id') if isinstance(item, dict) else item
                    try:
                        normalized_id = int(worker_id)
                    except (TypeError, ValueError):
                        continue
                    if normalized_id > 0:
                        raw_ids.append(normalized_id)
            if assigned_worker:
                raw_ids.append(int(assigned_worker.id))
            allowed_worker_ids = set(
                WorkerProfile.objects.filter(
                    tenant=tenant,
                    id__in=list(dict.fromkeys(raw_ids)),
                    user__role='worker',
                ).values_list('id', flat=True)
            )

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
                if allowed_worker_ids is not None and normalized_id not in allowed_worker_ids:
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

    def _resolve_customer_profile(self, phone, full_name='', gender='', increment_visit=False, tenant=None):
        phone_value = self._normalize_phone(phone)
        if not phone_value:
            return None
        normalized_gender = str(gender or '').strip().lower()
        if normalized_gender not in {'male', 'female'}:
            normalized_gender = ''

        customer = CustomerProfile.objects.filter(phone=phone_value).first()
        if not customer:
            customer = CustomerProfile.objects.create(
                phone=phone_value,
                tenant=tenant,
                full_name=(full_name or '').strip(),
                gender=normalized_gender,
                yearly_score=Decimal('0'),
                score_year=timezone.localtime().year,
            )

        update_fields = ['updated_at']
        display_name = (full_name or '').strip()
        if tenant and customer.tenant_id is None:
            customer.tenant = tenant
            update_fields.append('tenant')
        if display_name and display_name != (customer.full_name or '').strip():
            customer.full_name = display_name
            update_fields.append('full_name')
        if normalized_gender and normalized_gender != (customer.gender or ''):
            customer.gender = normalized_gender
            update_fields.append('gender')

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

    def _normalized_plate(self, plate_number='', plate_left='', plate_letter='', plate_mid='', plate_right=''):
        left = str(plate_left or '').strip()
        letter = str(plate_letter or '').strip()
        mid = str(plate_mid or '').strip()
        right = str(plate_right or '').strip()
        if left and letter and mid and right:
            return f'{left} {letter} {mid} {right}'
        if mid and letter and not left and not right:
            return f'{mid} {letter}'
        return str(plate_number or '').strip()

    def _is_plate_blocked(self, tenant, plate_number='', plate_left='', plate_letter='', plate_mid='', plate_right=''):
        return bool(self._find_blocked_plate_record(
            tenant=tenant,
            plate_number=plate_number,
            plate_left=plate_left,
            plate_letter=plate_letter,
            plate_mid=plate_mid,
            plate_right=plate_right,
        ))

    def _find_blocked_plate_record(self, tenant, plate_number='', plate_left='', plate_letter='', plate_mid='', plate_right=''):
        if not tenant:
            return None
        left = str(plate_left or '').strip()
        letter = str(plate_letter or '').strip()
        mid = str(plate_mid or '').strip()
        right = str(plate_right or '').strip()
        normalized_plate = self._normalized_plate(
            plate_number=plate_number,
            plate_left=left,
            plate_letter=letter,
            plate_mid=mid,
            plate_right=right,
        )
        queryset = BlockedPlate.objects.filter(tenant=tenant)
        if normalized_plate:
            found = queryset.filter(plate_number=normalized_plate).first()
            if found:
                return found
        if left and letter and mid and right:
            found = queryset.filter(
                plate_left=left,
                plate_letter=letter,
                plate_mid=mid,
                plate_right=right,
            ).first()
            if found:
                return found
        if mid and letter and not left and not right:
            found = queryset.filter(
                plate_mid=mid,
                plate_letter=letter,
                plate_left='',
                plate_right='',
            ).first()
            if found:
                return found
        raw_plate = str(plate_number or '').strip()
        if raw_plate:
            return queryset.filter(plate_number=raw_plate).first()
        return None

    class Meta:
        model = VehicleEntry
        fields = [
            'id',
            'admission_number',
            'plate_number',
            'plate_left',
            'plate_letter',
            'plate_mid',
            'plate_right',
            'plate_type',
            'tariff_type',
            'intake_source',
            'ai_confidence',
            'car_model',
            'car_color',
            'driver_name',
            'driver_gender',
            'driver_phone',
            'sms_notifications_enabled',
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
            'apply_loyalty_discount',
            'blocked_plate_payment_confirmed',
            'ai_raw_text',
            'ai_persian_text',
            'ai_converted_plate',
            'ai_converted_plate_left',
            'ai_converted_plate_letter',
            'ai_converted_plate_mid',
            'ai_converted_plate_right',
            'ai_converted_plate_type',
            'ai_image_base64',
            'ai_session_id',
            'ai_latency_ms',
            'share',
            'worker_id',
            'worker_name',
            'customer_score',
            'customer_score_year',
            'customer_loyalty_visit_count',
            'customer_loyalty_discount_percent',
            'is_plate_blocked',
            'blocked_plate_id',
            'job',
            'status_logs',
        ]
        read_only_fields = ['id', 'admission_number', 'check_in_at', 'created_at', 'updated_at']
        extra_kwargs = {
            'plate_number': {'required': False, 'allow_blank': True},
            'plate_left': {'required': False, 'allow_blank': True},
            'plate_letter': {'required': False, 'allow_blank': True},
            'plate_mid': {'required': False, 'allow_blank': True},
            'plate_right': {'required': False, 'allow_blank': True},
            'car_model': {'required': False, 'allow_blank': True},
            'car_color': {'required': False, 'allow_blank': True},
            'driver_name': {'required': False, 'allow_blank': True},
            'driver_gender': {'required': False, 'allow_blank': True},
            'driver_phone': {'required': False, 'allow_blank': True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if getattr(user, 'role', None) == 'worker':
            data.pop('driver_gender', None)
        return data
