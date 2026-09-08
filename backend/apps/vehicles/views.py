from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import BlockedPlate, VehicleEntry, VehicleJob, VehicleStatusLog
from .loyalty import (
    compute_configured_loyalty_discount,
    compute_loyalty_discount,
    get_or_create_plate_loyalty,
    next_fixed_discount_notice,
    loyalty_snapshot,
    preview_next_loyalty_state,
    rebuild_customer_score,
    rebuild_plate_loyalty,
    resolve_vehicle_loyalty_snapshot,
    sync_plate_loyalty,
)
from .serializers import VehicleEntryBoardSerializer, VehicleEntrySerializer
from apps.inventory.models import InventoryItem, StockMovement
from apps.notifications.models import NotificationLog
from apps.notifications.services import send_vehicle_event_sms
from apps.payments.models import Payment
from apps.products.models import Product
from apps.services.models import GeneralSettings, Service
from apps.workers.models import WorkerProfile
from apps.reports.models import WorkerPayoutTransaction
from .ai_audit import log_ai_plate_audit_event


class VehicleEntryListCreateView(generics.ListCreateAPIView):
    serializer_class = VehicleEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return VehicleEntryBoardSerializer
        return VehicleEntrySerializer

    def get_queryset(self):
        queryset = VehicleEntry.objects.select_related(
            'tenant',
            'customer',
            'job',
            'job__tenant',
            'job__assigned_worker',
            'job__assigned_worker__user',
        ).prefetch_related(
            'job__service_lines__service',
            'job__product_lines__product',
        ).filter(tenant=self.request.user.tenant).order_by('check_in_at', 'id')
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        date_start = parse_date(self.request.query_params.get('date_start') or '')
        date_end = parse_date(self.request.query_params.get('date_end') or '')
        current_timezone = timezone.get_current_timezone()
        if date_start:
            start_at = timezone.make_aware(datetime.combine(date_start, datetime.min.time()), current_timezone)
            queryset = queryset.filter(check_in_at__gte=start_at)
        if date_end:
            end_at = timezone.make_aware(datetime.combine(date_end + timedelta(days=1), datetime.min.time()), current_timezone)
            queryset = queryset.filter(check_in_at__lt=end_at)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user if getattr(self.request.user, 'is_authenticated', False) else None
        vehicle = serializer.save(entered_by=user, updated_by=user)
        log_ai_plate_audit_event(vehicle=vehicle, request=self.request, operation='create')


def _normalized_plate_value(
    plate_number='',
    plate_left='',
    plate_letter='',
    plate_mid='',
    plate_right='',
    plate_type='car',
):
    from .plate_normalize import normalize_plate_parts

    parts = normalize_plate_parts(
        plate_number=plate_number,
        plate_left=plate_left,
        plate_letter=plate_letter,
        plate_mid=plate_mid,
        plate_right=plate_right,
        plate_type=plate_type,
    )
    return parts.get('plate_number') or ''


def _find_blocked_plate(tenant, *, plate_number='', plate_left='', plate_letter='', plate_mid='', plate_right=''):
    if not tenant:
        return None
    left = str(plate_left or '').strip()
    letter = str(plate_letter or '').strip()
    mid = str(plate_mid or '').strip()
    right = str(plate_right or '').strip()
    normalized = _normalized_plate_value(
        plate_number=plate_number,
        plate_left=left,
        plate_letter=letter,
        plate_mid=mid,
        plate_right=right,
    )
    queryset = BlockedPlate.objects.filter(tenant=tenant)
    if normalized:
        found = queryset.filter(plate_number=normalized).first()
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


def _normalized_ai_letter(value=''):
    from .plate_normalize import normalize_plate_letter

    return normalize_plate_letter(value)


def _ai_plate_parts(visual_right='', letter='', mid='', visual_left=''):
    from .plate_normalize import normalize_plate_parts

    return normalize_plate_parts(
        plate_left=visual_left,
        plate_letter=letter,
        plate_mid=mid,
        plate_right=visual_right,
        plate_type='car',
    )


def _parse_ai_plate_from_latin(raw_text=''):
    raw = str(raw_text or '').strip().lower()
    compact_raw = ''.join(ch for ch in raw if ch.isalnum())
    raw_match = re.search(r'(\d{2})([a-z])(\d{3})(\d{2})', compact_raw)
    if not raw_match:
        return {}
    visual_right, letter_token, mid, visual_left = raw_match.groups()
    letter = _normalized_ai_letter(letter_token)
    if not letter:
        return {}
    return _ai_plate_parts(visual_right=visual_right, letter=letter, mid=mid, visual_left=visual_left)


def _parse_ai_plate_from_persian(persian_text=''):
    from .plate_normalize import normalize_digits

    normalized = normalize_digits(persian_text or '')
    normalized = normalized.replace('ك', 'ک').replace('ي', 'ی')
    tokenized = re.sub(r'[^0-9A-Za-zآ-ی]+', ' ', normalized).split()
    for index in range(max(0, len(tokenized) - 3)):
        visual_right = ''.join(ch for ch in tokenized[index] if ch.isdigit())[:2]
        letter = _normalized_ai_letter(tokenized[index + 1])
        mid = ''.join(ch for ch in tokenized[index + 2] if ch.isdigit())[:3]
        visual_left = ''.join(ch for ch in tokenized[index + 3] if ch.isdigit())[:2]
        if len(visual_right) == 2 and letter and len(mid) == 3 and len(visual_left) == 2:
            return _ai_plate_parts(visual_right=visual_right, letter=letter, mid=mid, visual_left=visual_left)

    inline_match = re.search(r'(\d{2})\s*([^0-9\s]{1,4})\s*(\d{3})\s*(\d{2})', normalized)
    if not inline_match:
        return {}
    visual_right, letter_token, mid, visual_left = inline_match.groups()
    letter = _normalized_ai_letter(letter_token)
    if not letter:
        return {}
    return _ai_plate_parts(visual_right=visual_right, letter=letter, mid=mid, visual_left=visual_left)


def _plate_parts_from_ai(raw_text='', persian_text=''):
    latin_parts = _parse_ai_plate_from_latin(raw_text)
    persian_parts = _parse_ai_plate_from_persian(persian_text)
    if latin_parts and persian_parts:
        persian_letter = str(persian_parts.get('plate_letter') or '').strip()
        if persian_letter:
            # Digit model is stronger on latin OCR; Persian overlay is stronger on letters.
            return _ai_plate_parts(
                visual_right=latin_parts.get('plate_right', ''),
                letter=persian_letter,
                mid=latin_parts.get('plate_mid', ''),
                visual_left=latin_parts.get('plate_left', ''),
            )
        return latin_parts
    return latin_parts or persian_parts or {}


def _digit_storage_variants(value=''):
    """Latin + Persian digit forms — older rows / some clients stored Persian digits."""
    from .plate_normalize import normalize_digits

    latin = ''.join(ch for ch in normalize_digits(value) if ch.isdigit())
    if not latin:
        return set()
    persian = latin.translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
    return {latin, persian}


def _q_digit_field(field, value):
    from django.db.models import Q

    variants = _digit_storage_variants(value)
    if not variants:
        return Q(**{field: ''})
    query = Q()
    for item in variants:
        query |= Q(**{field: item})
    return query


def _find_latest_vehicle_by_plate(tenant, *, plate_number='', plate_left='', plate_letter='', plate_mid='', plate_right='', plate_type='car'):
    from .plate_normalize import normalize_plate_parts, plate_letter_lookup_variants

    parts = normalize_plate_parts(
        plate_number=plate_number,
        plate_left=plate_left,
        plate_letter=plate_letter,
        plate_mid=plate_mid,
        plate_right=plate_right,
        plate_type=plate_type,
    )
    queryset = VehicleEntry.objects.filter(tenant=tenant).exclude(status=VehicleEntry.Status.CANCELLED)
    candidates = []
    if parts['plate_number']:
        candidates.append(queryset.filter(plate_number=parts['plate_number']).order_by('-check_in_at').first())
    letter_variants = plate_letter_lookup_variants(parts['plate_letter'] or plate_letter)
    if parts['plate_mid'] and letter_variants:
        if parts['plate_left'] and parts['plate_right']:
            candidates.append(
                queryset.filter(
                    _q_digit_field('plate_left', parts['plate_left']),
                    _q_digit_field('plate_mid', parts['plate_mid']),
                    _q_digit_field('plate_right', parts['plate_right']),
                    plate_letter__in=letter_variants,
                ).order_by('-check_in_at').first()
            )
        elif not parts['plate_left'] and not parts['plate_right']:
            candidates.append(
                queryset.filter(
                    _q_digit_field('plate_mid', parts['plate_mid']),
                    plate_letter__in=letter_variants,
                    plate_left='',
                    plate_right='',
                ).order_by('-check_in_at').first()
            )
    # Legacy rows may still store short "ا" while lookup uses "الف".
    for letter in letter_variants:
        legacy_number = ''
        if parts['plate_left'] and letter and parts['plate_mid'] and parts['plate_right']:
            legacy_number = f"{parts['plate_left']} {letter} {parts['plate_mid']} {parts['plate_right']}"
        elif parts['plate_mid'] and letter and not parts['plate_left'] and not parts['plate_right']:
            legacy_number = f"{parts['plate_mid']} {letter}"
        if legacy_number and legacy_number != parts['plate_number']:
            candidates.append(queryset.filter(plate_number=legacy_number).order_by('-check_in_at').first())
    found = [item for item in candidates if item]
    if found:
        found.sort(key=lambda item: item.check_in_at or timezone.now(), reverse=True)
        return found[0], parts

    return None, parts


class VehicleEntryDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = VehicleEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VehicleEntry.objects.select_related(
            'tenant',
            'customer',
            'job',
            'job__tenant',
            'job__assigned_worker',
            'job__assigned_worker__user',
        ).prefetch_related('job__service_lines__service', 'job__product_lines__product', 'status_logs').filter(tenant=self.request.user.tenant)

    def perform_update(self, serializer):
        user = self.request.user if getattr(self.request.user, 'is_authenticated', False) else None
        vehicle = serializer.save(updated_by=user)
        log_ai_plate_audit_event(vehicle=vehicle, request=self.request, operation='update')


class VehicleEntryStatusUpdateView(generics.UpdateAPIView):
    serializer_class = VehicleEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VehicleEntry.objects.select_related('job').filter(tenant=self.request.user.tenant)

    def _restore_released_inventory(self, instance, request_user):
        release_movements = list(
            StockMovement.objects.select_related('inventory_item')
            .filter(
                tenant=instance.tenant,
                reference_type='vehicle_release',
                reference_id=instance.id,
                movement_type=StockMovement.MovementType.OUT,
            )
        )
        if not release_movements:
            return

        reversed_totals = {
            item['inventory_item_id']: Decimal(str(item['total'] or 0))
            for item in (
                StockMovement.objects.filter(
                    tenant=instance.tenant,
                    reference_type='vehicle_release_cancel',
                    reference_id=instance.id,
                    movement_type=StockMovement.MovementType.IN,
                )
                .values('inventory_item_id')
                .annotate(total=Sum('quantity'))
            )
        }
        released_totals = {}
        for movement in release_movements:
            item_id = movement.inventory_item_id
            if item_id not in released_totals:
                released_totals[item_id] = {'quantity': Decimal('0'), 'movement': movement}
            released_totals[item_id]['quantity'] += Decimal(str(movement.quantity or 0))

        for item_id, payload in released_totals.items():
            restore_quantity = payload['quantity'] - reversed_totals.get(item_id, Decimal('0'))
            if restore_quantity <= 0:
                continue
            inventory_item = InventoryItem.objects.select_for_update().filter(pk=item_id).first()
            if not inventory_item:
                continue
            inventory_item.quantity_on_hand = Decimal(str(inventory_item.quantity_on_hand or 0)) + restore_quantity
            inventory_item.save(update_fields=['quantity_on_hand', 'updated_at'])
            sample_movement = payload['movement']
            StockMovement.objects.create(
                tenant=instance.tenant,
                inventory_item=inventory_item,
                movement_type=StockMovement.MovementType.IN,
                quantity=restore_quantity,
                unit_cost=sample_movement.unit_cost or Decimal('0'),
                sale_price_snapshot=sample_movement.sale_price_snapshot or Decimal('0'),
                note='بازگشت موجودی پس از لغو ترخیص خودرو',
                reference_type='vehicle_release_cancel',
                reference_id=instance.id,
                created_by=request_user if getattr(request_user, 'is_authenticated', False) else None,
            )

    def _neutralize_cancelled_vehicle_effects(self, instance, request_user):
        Payment.objects.filter(vehicle_entry=instance).exclude(
            status=Payment.Status.REFUNDED
        ).update(status=Payment.Status.REFUNDED, updated_at=timezone.now())
        self._restore_released_inventory(instance, request_user)

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        new_status = request.data.get('status')
        valid_statuses = {choice[0] for choice in VehicleEntry.Status.choices}
        if new_status not in valid_statuses:
            return Response({'status': ['Invalid status value.']}, status=status.HTTP_400_BAD_REQUEST)

        previous_status = instance.status
        is_new_cancellation = (
            new_status == VehicleEntry.Status.CANCELLED
            and previous_status != VehicleEntry.Status.CANCELLED
        )
        has_payments = Payment.objects.filter(vehicle_entry=instance).exists()
        instance.status = new_status
        update_fields = ['status', 'updated_at']
        if new_status == VehicleEntry.Status.READY_TO_SETTLE:
            instance.ready_at = timezone.now()
            update_fields.append('ready_at')
        elif new_status == VehicleEntry.Status.RELEASED:
            instance.released_at = timezone.now()
            update_fields.append('released_at')
        elif new_status == VehicleEntry.Status.CANCELLED:
            instance.released_at = None
            instance.payment_status = (
                VehicleEntry.PaymentStatus.REFUNDED
                if has_payments
                else VehicleEntry.PaymentStatus.UNPAID
            )
            instance.payment_method = ''
            update_fields.extend(['released_at', 'payment_status', 'payment_method'])
        instance.save(update_fields=update_fields)

        if is_new_cancellation:
            self._neutralize_cancelled_vehicle_effects(instance, request.user)
            rebuild_customer_score(instance.customer)
            if not instance.is_piece_wash:
                rebuild_plate_loyalty(
                    get_or_create_plate_loyalty(
                        tenant=instance.tenant,
                        plate_number=instance.plate_number,
                        plate_left=instance.plate_left,
                        plate_letter=instance.plate_letter,
                        plate_mid=instance.plate_mid,
                        plate_right=instance.plate_right,
                    ),
                    discount_percent_per_half_star=self.get_serializer()._discount_percent_per_half_star(instance.tenant),
                )

        VehicleStatusLog.objects.create(
            tenant=instance.tenant,
            vehicle=instance,
            from_status=previous_status,
            to_status=new_status,
            changed_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
            note=(request.data.get('note') or '').strip(),
        )

        if hasattr(instance, 'job') and instance.job:
            if new_status == VehicleEntry.Status.READY_TO_SETTLE:
                instance.job.completed_at = timezone.now()
                instance.job.save(update_fields=['completed_at', 'updated_at'])
            elif new_status == VehicleEntry.Status.RELEASED:
                instance.job.released_at = timezone.now()
                instance.job.save(update_fields=['released_at', 'updated_at'])
            elif new_status == VehicleEntry.Status.CANCELLED:
                instance.job.released_at = None
                instance.job.save(update_fields=['released_at', 'updated_at'])

        if previous_status != new_status:
            if new_status == VehicleEntry.Status.READY_TO_SETTLE:
                loyalty = loyalty_snapshot(get_or_create_plate_loyalty(
                    tenant=instance.tenant,
                    plate_number=instance.plate_number,
                    plate_left=instance.plate_left,
                    plate_letter=instance.plate_letter,
                    plate_mid=instance.plate_mid,
                    plate_right=instance.plate_right,
                ))
                send_vehicle_event_sms(
                    'vehicle_assigned',
                    instance.tenant,
                    instance,
                    created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
                    extra_context={
                        'assigned_at': instance.ready_at or timezone.now(),
                        'visit_count': loyalty.get('visit_count', 0),
                    },
                )
            elif new_status == VehicleEntry.Status.RELEASED:
                job = getattr(instance, 'job', None)
                loyalty = loyalty_snapshot(get_or_create_plate_loyalty(
                    tenant=instance.tenant,
                    plate_number=instance.plate_number,
                    plate_left=instance.plate_left,
                    plate_letter=instance.plate_letter,
                    plate_mid=instance.plate_mid,
                    plate_right=instance.plate_right,
                ))
                send_vehicle_event_sms(
                    'vehicle_released',
                    instance.tenant,
                    instance,
                    created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
                    extra_context={
                        'released_at': instance.released_at or timezone.now(),
                        'customer_score': loyalty.get('score', 0),
                        'next_discount_percent': loyalty.get('discount_percent', 0),
                        'visit_count': loyalty.get('visit_count', 0),
                        'final_total': float(
                            (getattr(job, 'final_total', 0) or 0)
                            or (getattr(job, 'services_total', 0) or 0)
                        ),
                        'discount_total': float(getattr(job, 'total_discount', 0) or getattr(job, 'discount_total', 0) or 0),
                        'facility_discount_total': float(getattr(job, 'facility_discount_total', 0) or 0),
                        'loyalty_discount_total': float(getattr(job, 'loyalty_discount_total', 0) or 0),
                        'manual_discount_total': float(getattr(job, 'manual_discount_total', 0) or 0),
                        'tip_amount': float(getattr(job, 'tip_amount', 0) or 0),
                        'tax_total': float(getattr(job, 'tax_total', 0) or 0),
                    },
                )

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BlockedPlateStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request.user, 'tenant', None)
        plate_left = request.query_params.get('plate_left', '')
        plate_letter = request.query_params.get('plate_letter', '')
        plate_mid = request.query_params.get('plate_mid', '')
        plate_right = request.query_params.get('plate_right', '')
        raw_plate = request.query_params.get('plate_number', '')
        plate_number = _normalized_plate_value(
            plate_number=raw_plate,
            plate_left=plate_left,
            plate_letter=plate_letter,
            plate_mid=plate_mid,
            plate_right=plate_right,
        )
        if not plate_number and not any([plate_left, plate_letter, plate_mid, plate_right, raw_plate]):
            return Response({'is_blocked': False}, status=status.HTTP_200_OK)
        blocked = _find_blocked_plate(
            tenant,
            plate_number=plate_number or raw_plate,
            plate_left=plate_left,
            plate_letter=plate_letter,
            plate_mid=plate_mid,
            plate_right=plate_right,
        )
        return Response(
            {
                'id': blocked.id if blocked else None,
                'plate_number': plate_number or (blocked.plate_number if blocked else ''),
                'plate_left': blocked.plate_left if blocked else '',
                'plate_letter': blocked.plate_letter if blocked else '',
                'plate_mid': blocked.plate_mid if blocked else '',
                'plate_right': blocked.plate_right if blocked else '',
                'plate_type': blocked.plate_type if blocked else '',
                'is_blocked': bool(blocked),
                'note': blocked.note if blocked else '',
                'blocked_by_name': (
                    blocked.blocked_by.full_name or blocked.blocked_by.username
                    if blocked and blocked.blocked_by_id
                    else ''
                ),
                'blocked_at': blocked.created_at if blocked else None,
                'created_at': blocked.created_at if blocked else None,
            },
            status=status.HTTP_200_OK,
        )


class VehiclePlateLookupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request.user, 'tenant', None)
        plate_type = str(request.query_params.get('plate_type', 'car') or 'car').strip().lower() or 'car'
        letters_raw = str(request.query_params.get('plate_letters') or '').strip()
        batch_letters = [part.strip() for part in letters_raw.replace('،', ',').split(',') if part.strip()]
        primary_letter = str(request.query_params.get('plate_letter', '') or '').strip()

        latest_vehicle = None
        parts = {}

        if len(batch_letters) > 1:
            # Ambiguous OCR letter probe: only accept when exactly one candidate hits history.
            matched = []
            for letter in batch_letters:
                vehicle, candidate_parts = _find_latest_vehicle_by_plate(
                    tenant,
                    plate_number=request.query_params.get('plate_number', ''),
                    plate_left=request.query_params.get('plate_left', ''),
                    plate_letter=letter,
                    plate_mid=request.query_params.get('plate_mid', ''),
                    plate_right=request.query_params.get('plate_right', ''),
                    plate_type=plate_type,
                )
                parts = candidate_parts
                if vehicle:
                    matched.append((vehicle, candidate_parts))
            if len(matched) == 1:
                latest_vehicle, parts = matched[0]
        else:
            letter = primary_letter or (batch_letters[0] if batch_letters else '')
            latest_vehicle, parts = _find_latest_vehicle_by_plate(
                tenant,
                plate_number=request.query_params.get('plate_number', ''),
                plate_left=request.query_params.get('plate_left', ''),
                plate_letter=letter,
                plate_mid=request.query_params.get('plate_mid', ''),
                plate_right=request.query_params.get('plate_right', ''),
                plate_type=plate_type,
            )
        plate_number = parts.get('plate_number') or ''
        has_car_digits = bool(parts.get('plate_left') and parts.get('plate_mid') and parts.get('plate_right'))
        has_moto_parts = bool(
            parts.get('plate_type') == 'motorcycle'
            and parts.get('plate_mid')
            and parts.get('plate_letter')
        )
        # Digits alone are enough for history; letter may fail to normalize on some clients.
        if not plate_number and not latest_vehicle and not has_car_digits and not has_moto_parts:
            return Response({'found': False}, status=status.HTTP_200_OK)
        if not plate_number and has_car_digits:
            letter_bit = parts.get('plate_letter') or ''
            plate_number = (
                f"{parts['plate_left']} {letter_bit} {parts['plate_mid']} {parts['plate_right']}".strip()
                if letter_bit
                else f"{parts['plate_left']} {parts['plate_mid']} {parts['plate_right']}"
            )
        if latest_vehicle and not plate_number:
            plate_number = latest_vehicle.plate_number or ''

        settings_obj = GeneralSettings.objects.filter(tenant=tenant).order_by('id').first()
        discount_percent_per_half_star = Decimal(
            str(getattr(settings_obj, 'discount_percent_per_half_star', 0) or 0)
        )

        if not latest_vehicle:
            # First visit preview: count=1, score=0.5
            upcoming = preview_next_loyalty_state(
                None,
                discount_percent_per_half_star=discount_percent_per_half_star,
            )
            discount_percent, _discount_amount = compute_configured_loyalty_discount(
                base_amount=0,
                profile=None,
                settings_obj=settings_obj,
                visit_count=upcoming['visit_count'],
                score=upcoming['visit_score'],
            )
            return Response(
                {
                    'found': False,
                    'plate_number': plate_number,
                    'customer_score': upcoming['score'],
                    'customer_loyalty_visit_count': upcoming['visit_count'],
                    'customer_loyalty_discount_percent': float(discount_percent or 0),
                    'discount_calculation_mode': getattr(settings_obj, 'discount_calculation_mode', 'step') if settings_obj else 'step',
                    'fixed_discount_notice': next_fixed_discount_notice(settings_obj, upcoming['visit_count']),
                },
                status=status.HTTP_200_OK,
            )

        loyalty_profile = sync_plate_loyalty(
            get_or_create_plate_loyalty(
                tenant=tenant,
                plate_number=latest_vehicle.plate_number,
                plate_left=latest_vehicle.plate_left,
                plate_letter=latest_vehicle.plate_letter,
                plate_mid=latest_vehicle.plate_mid,
                plate_right=latest_vehicle.plate_right,
                plate_type=getattr(latest_vehicle, 'plate_type', 'car'),
            ),
            discount_percent_per_half_star=discount_percent_per_half_star,
        )
        loyalty = loyalty_snapshot(loyalty_profile)
        # If profile is still empty somehow, treat as first visit.
        if int(loyalty.get('visit_count', 0) or 0) <= 0:
            loyalty = preview_next_loyalty_state(
                None,
                discount_percent_per_half_star=discount_percent_per_half_star,
            )
            loyalty['discount_percent'] = loyalty.get('discount_percent', 0)

        discount_percent, _discount_amount = compute_configured_loyalty_discount(
            base_amount=0,
            profile=loyalty_profile,
            settings_obj=settings_obj,
            visit_count=max(1, int(loyalty.get('visit_count', 0) or 0)),
            score=loyalty.get('score', 0),
        )
        return Response(
            {
                'found': True,
                'plate_number': latest_vehicle.plate_number or plate_number,
                'plate_left': latest_vehicle.plate_left or '',
                'plate_letter': latest_vehicle.plate_letter or '',
                'plate_mid': latest_vehicle.plate_mid or '',
                'plate_right': latest_vehicle.plate_right or '',
                'plate_type': latest_vehicle.plate_type or VehicleEntry.PlateType.CAR,
                'driver_name': latest_vehicle.driver_name or '',
                'driver_gender': latest_vehicle.driver_gender or '',
                'driver_phone': latest_vehicle.driver_phone or '',
                'car_model': latest_vehicle.car_model or '',
                'car_color': latest_vehicle.car_color or '',
                'tariff_type': latest_vehicle.tariff_type or 'type_1',
                'customer_score': loyalty.get('score', 0),
                'customer_loyalty_visit_count': max(1, int(loyalty.get('visit_count', 0) or 0)),
                'customer_loyalty_discount_percent': float(discount_percent or 0),
                'discount_calculation_mode': getattr(settings_obj, 'discount_calculation_mode', 'step') if settings_obj else 'step',
                'fixed_discount_notice': next_fixed_discount_notice(settings_obj, max(1, int(loyalty.get('visit_count', 0) or 0))),
            },
            status=status.HTTP_200_OK,
        )


class VehiclePlateRecognitionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tenant = getattr(request.user, 'tenant', None)
        if not tenant:
            return Response({'detail': 'کارواش کاربر مشخص نیست.'}, status=status.HTTP_400_BAD_REQUEST)

        image_base64 = str(request.data.get('image_base64') or request.data.get('image_data_url') or '').strip()
        if not image_base64:
            return Response({'image_base64': ['تصویر دوربین ارسال نشده است.']}, status=status.HTTP_400_BAD_REQUEST)

        session_suffix = str(request.data.get('session_id') or 'default').strip() or 'default'
        session_id = f'tenant-{tenant.id}:{session_suffix}'
        service_url = str(getattr(settings, 'PLATE_AI_SERVICE_URL', 'http://127.0.0.1:8765')).rstrip('/')
        timeout_seconds = float(getattr(settings, 'PLATE_AI_TIMEOUT_SECONDS', 5.0) or 5.0)
        force_process_value = request.data.get('force_process', False)
        if isinstance(force_process_value, str):
            force_process = force_process_value.strip().lower() in {'1', 'true', 'yes', 'on'}
        else:
            force_process = bool(force_process_value)
        payload = json.dumps(
            {
                'session_id': session_id,
                'image_base64': image_base64,
                'timeout_sec': max(1.0, timeout_seconds - 0.5),
                'force_process': force_process,
            }
        ).encode('utf-8')

        try:
            upstream_request = Request(
                f'{service_url}/recognize',
                data=payload,
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            with urlopen(upstream_request, timeout=timeout_seconds) as response:
                upstream_data = json.loads(response.read().decode('utf-8'))
        except HTTPError as exc:
            try:
                upstream_data = json.loads(exc.read().decode('utf-8'))
            except Exception:
                upstream_data = {'detail': str(exc)}
            return Response(upstream_data, status=exc.code)
        except (URLError, TimeoutError, OSError):
            return Response(
                {
                    'accepted': False,
                    'detail': 'سرویس تشخیص پلاک فعال نیست. سرویس AI را کنار سایت اجرا کنید.',
                    'service_url': service_url,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        raw_text = upstream_data.get('text') or ''
        persian_text = upstream_data.get('persian_text') or ''
        parts = _plate_parts_from_ai(raw_text=raw_text, persian_text=persian_text)
        ai_payload = {
            key: value
            for key, value in upstream_data.items()
            if key not in {'color', 'color_confidence', 'color_reliable', 'color_stable'}
        }
        accepted = bool(ai_payload.get('accepted', True))
        if parts:
            accepted = True
        return Response(
            {
                **ai_payload,
                'accepted': accepted,
                'recognized': bool(parts),
                'plate_number': parts.get('plate_number', ''),
                'plate_left': parts.get('plate_left', ''),
                'plate_letter': parts.get('plate_letter', ''),
                'plate_mid': parts.get('plate_mid', ''),
                'plate_right': parts.get('plate_right', ''),
            },
            status=status.HTTP_200_OK,
        )


class VehicleBlockPlateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        tenant = getattr(request.user, 'tenant', None)
        vehicle = (
            VehicleEntry.objects.select_related('customer', 'job', 'job__assigned_worker', 'job__assigned_worker__user')
            .prefetch_related('job__service_lines__service', 'job__product_lines__product', 'status_logs')
            .filter(pk=pk, tenant=tenant)
            .first()
        )
        if not vehicle:
            return Response({'detail': 'Vehicle not found.'}, status=status.HTTP_404_NOT_FOUND)

        plate_number = _normalized_plate_value(
            plate_number=vehicle.plate_number,
            plate_left=vehicle.plate_left,
            plate_letter=vehicle.plate_letter,
            plate_mid=vehicle.plate_mid,
            plate_right=vehicle.plate_right,
        )
        if not plate_number:
            return Response(
                {
                    'detail': 'این مراجعه پلاک ندارد (ناشناس یا قطعه‌شویی) و قابل بلاک نیست.',
                    'plate_number': ['پلاک معتبر برای بلاک ثبت نشده است.'],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        blocked_plate = _find_blocked_plate(
            tenant,
            plate_number=plate_number,
            plate_left=vehicle.plate_left,
            plate_letter=vehicle.plate_letter,
            plate_mid=vehicle.plate_mid,
            plate_right=vehicle.plate_right,
        )
        created = False
        if not blocked_plate:
            blocked_plate = BlockedPlate.objects.create(
                tenant=tenant,
                plate_number=plate_number,
                plate_left=vehicle.plate_left or '',
                plate_letter=vehicle.plate_letter or '',
                plate_mid=vehicle.plate_mid or '',
                plate_right=vehicle.plate_right or '',
                plate_type=vehicle.plate_type or VehicleEntry.PlateType.CAR,
                blocked_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
                note=(request.data.get('note') or '').strip(),
            )
            created = True
        elif not blocked_plate.blocked_by_id and getattr(request.user, 'is_authenticated', False):
            blocked_plate.blocked_by = request.user
            blocked_plate.save(update_fields=['blocked_by', 'updated_at'])

        vehicle.refresh_from_db()
        serializer = VehicleEntrySerializer(vehicle, context={'request': request})
        return Response(
            {
                'id': blocked_plate.id,
                'plate_number': blocked_plate.plate_number,
                'is_blocked': True,
                'created': created,
                'cancelled': False,
                'note': blocked_plate.note,
                'blocked_by_name': (
                    blocked_plate.blocked_by.full_name or blocked_plate.blocked_by.username
                    if blocked_plate.blocked_by_id
                    else '-'
                ),
                'created_at': blocked_plate.created_at,
                'vehicle': serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class BlockedPlateUnblockView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        tenant = getattr(request.user, 'tenant', None)
        blocked = BlockedPlate.objects.filter(pk=pk, tenant=tenant).first()
        if not blocked:
            return Response({'detail': 'Blocked plate not found.'}, status=status.HTTP_404_NOT_FOUND)
        plate_number = blocked.plate_number
        blocked.delete()
        return Response(
            {
                'id': pk,
                'plate_number': plate_number,
                'is_blocked': False,
            },
            status=status.HTTP_200_OK,
        )


class VehicleReleaseCheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _money(value):
        return Decimal(str(value or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def _service_line_list_total(line):
        quantity = Decimal(str(getattr(line, 'quantity', 0) or 0))
        list_unit_price = Decimal(str(getattr(line, 'list_unit_price', 0) or 0))
        if list_unit_price > 0:
            return list_unit_price * quantity
        return Decimal(str(getattr(line, 'line_total', 0) or 0)) + Decimal(
            str(getattr(line, 'discount_amount', 0) or 0)
        )

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

    def _tax_percent(self, tenant):
        settings_obj = GeneralSettings.objects.filter(tenant=tenant).order_by('id').first()
        if not getattr(settings_obj, 'tax_enabled', False):
            return Decimal('0')
        return self._clamp_percent(getattr(settings_obj, 'tax_percent', Decimal('0')))

    def _compute_discount(self, base_amount, customer_score, percent_per_half_star):
        discount_percent, discount_amount = compute_loyalty_discount(
            base_amount=base_amount,
            score=customer_score,
            percent_per_half_star=percent_per_half_star,
        )
        return self._clamp_percent(discount_percent), self._money(discount_amount)

    def _compute_configured_discount(
        self,
        base_amount,
        loyalty_profile,
        settings_obj,
        *,
        visit_count=None,
        score=None,
    ):
        discount_percent, discount_amount = compute_configured_loyalty_discount(
            base_amount=base_amount,
            profile=loyalty_profile,
            settings_obj=settings_obj,
            visit_count=visit_count,
            score=score,
        )
        return self._clamp_percent(discount_percent), self._money(discount_amount)

    def _loyalty_profile(self, vehicle):
        profile = get_or_create_plate_loyalty(
            tenant=getattr(vehicle, 'tenant', None),
            plate_number=getattr(vehicle, 'plate_number', ''),
            plate_left=getattr(vehicle, 'plate_left', ''),
            plate_letter=getattr(vehicle, 'plate_letter', ''),
            plate_mid=getattr(vehicle, 'plate_mid', ''),
            plate_right=getattr(vehicle, 'plate_right', ''),
        )
        return sync_plate_loyalty(
            profile,
            discount_percent_per_half_star=self._discount_percent_per_half_star(
                getattr(vehicle, 'tenant', None)
            ),
        )

    def _resolve_assigned_workers(self, job):
        snapshot = job.assigned_workers_snapshot if isinstance(job.assigned_workers_snapshot, list) else []
        ordered_ids = []
        names_by_id = {}
        orphan_names = []
        worker_share_percent_by_id = {}
        worker_share_amount_by_id = {}
        for item in snapshot:
            if not isinstance(item, dict):
                continue
            raw_name = (item.get('name') or '').strip()
            try:
                worker_id = int(item.get('id'))
            except (TypeError, ValueError):
                if raw_name:
                    orphan_names.append(raw_name)
                continue
            if worker_id <= 0:
                if raw_name:
                    orphan_names.append(raw_name)
                continue
            if worker_id not in ordered_ids:
                ordered_ids.append(worker_id)
            if raw_name:
                names_by_id[worker_id] = raw_name
            worker_share_percent_by_id[worker_id] = self._clamp_percent(item.get('worker_share_percent', 0))
            worker_share_amount_by_id[worker_id] = self._money(item.get('worker_share_amount', 0))

        if job.assigned_worker_id and job.assigned_worker_id not in ordered_ids:
            ordered_ids.insert(0, int(job.assigned_worker_id))

        if orphan_names:
            candidate_profiles = list(
                WorkerProfile.objects.select_related('user').filter(tenant=job.tenant, user__role='worker')
            )
            profiles_by_name = {}
            for profile in candidate_profiles:
                if not getattr(profile, 'user', None):
                    continue
                full_name = (profile.user.full_name or '').strip()
                username = (profile.user.username or '').strip()
                if full_name:
                    profiles_by_name.setdefault(full_name.casefold(), profile)
                if username:
                    profiles_by_name.setdefault(username.casefold(), profile)
            for raw_name in orphan_names:
                profile = profiles_by_name.get(raw_name.casefold())
                if not profile:
                    continue
                if profile.id not in ordered_ids:
                    ordered_ids.append(profile.id)
                if raw_name and profile.id not in names_by_id:
                    names_by_id[profile.id] = raw_name

        if not ordered_ids:
            return []

        profiles = list(
            WorkerProfile.objects.select_related('user').filter(
                tenant=job.tenant,
                user__role='worker',
            ).filter(
                Q(id__in=ordered_ids) | Q(user_id__in=ordered_ids)
            )
        )
        profiles_by_id = {item.id: item for item in profiles}
        profiles_by_user_id = {item.user_id: item for item in profiles if item.user_id}
        workers = []
        seen_profile_ids = set()
        for worker_id in ordered_ids:
            profile = profiles_by_id.get(worker_id) or profiles_by_user_id.get(worker_id)
            resolved_worker_id = int(profile.id) if profile else int(worker_id)
            if resolved_worker_id in seen_profile_ids:
                continue
            seen_profile_ids.add(resolved_worker_id)
            name = (
                names_by_id.get(worker_id)
                or ((profile.user.full_name or profile.user.username or '').strip() if profile and getattr(profile, 'user', None) else '')
                or f'نیرو {worker_id}'
            )
            workers.append(
                {
                    'id': resolved_worker_id,
                    'name': name,
                    'tip_share_percent': Decimal(str(profile.tip_share_percent or 0)) if profile else Decimal('0'),
                    'worker_share_percent': worker_share_percent_by_id.get(worker_id, Decimal('0')),
                    'worker_share_amount': worker_share_amount_by_id.get(worker_id, Decimal('0')),
                }
            )
        return workers

    def _resolve_workers_from_payload(self, tenant, raw_workers):
        if not isinstance(raw_workers, list):
            return None

        requested = []
        seen_ids = set()
        for item in raw_workers:
            if not isinstance(item, dict):
                continue
            try:
                worker_id = int(item.get('id') or item.get('worker_id') or 0)
            except (TypeError, ValueError):
                worker_id = 0
            if worker_id <= 0 or worker_id in seen_ids:
                continue
            seen_ids.add(worker_id)
            requested.append(
                {
                    'id': worker_id,
                    'name': str(item.get('name') or item.get('worker_name') or '').strip(),
                    'worker_share_percent': self._clamp_percent(item.get('worker_share_percent', 0)),
                }
            )

        if not requested:
            return []

        profiles = list(
            WorkerProfile.objects.select_related('user').filter(
                tenant=tenant,
                id__in=[item['id'] for item in requested],
                user__role='worker',
            )
        )
        profiles_by_id = {int(profile.id): profile for profile in profiles}
        resolved = []
        for item in requested:
            profile = profiles_by_id.get(int(item['id']))
            if not profile:
                continue
            name = (
                item['name']
                or ((profile.user.full_name or profile.user.username or '').strip() if getattr(profile, 'user', None) else '')
                or f"نیرو {profile.id}"
            )
            resolved.append(
                {
                    'id': int(profile.id),
                    'name': name,
                    'tip_share_percent': Decimal(str(profile.tip_share_percent or 0)),
                    'worker_share_percent': item['worker_share_percent'],
                    'worker_share_amount': Decimal('0'),
                }
            )
        return resolved

    def _default_worker_share_distribution(self, assigned_workers):
        worker_count = len(assigned_workers or [])
        if worker_count <= 0:
            return []
        base_percent = (Decimal('100') / Decimal(str(worker_count))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        distribution = []
        remaining = Decimal('100')
        for index, worker in enumerate(assigned_workers):
            percent = remaining if index == worker_count - 1 else base_percent
            percent = self._clamp_percent(percent)
            remaining -= percent
            distribution.append(
                {
                    'id': int(worker['id']),
                    'name': worker.get('name') or f"نیرو {worker['id']}",
                    'worker_share_percent': percent,
                }
            )
        return distribution

    def _normalize_worker_share_distribution(self, assigned_workers, raw_distribution, worker_share_base):
        workers = assigned_workers or []
        if not workers:
            return [], Decimal('0')

        worker_ids = [int(item['id']) for item in workers if item.get('id')]
        requested = {}
        if isinstance(raw_distribution, list):
            for item in raw_distribution:
                if not isinstance(item, dict):
                    continue
                try:
                    worker_id = int(item.get('id'))
                except (TypeError, ValueError):
                    continue
                if worker_id not in worker_ids:
                    continue
                requested[worker_id] = self._clamp_percent(item.get('worker_share_percent', 0))

        default_distribution = self._default_worker_share_distribution(workers)
        normalized = []
        total_percent = Decimal('0')
        for item in default_distribution:
            worker_id = int(item['id'])
            percent = requested.get(worker_id, item['worker_share_percent'])
            normalized.append(
                {
                    'id': worker_id,
                    'name': item['name'],
                    'worker_share_percent': percent,
                }
            )
            total_percent += percent

        if total_percent <= 0:
            normalized = self._default_worker_share_distribution(workers)
            total_percent = sum((item['worker_share_percent'] for item in normalized), Decimal('0'))

        if total_percent > 0 and total_percent != Decimal('100'):
            scaled = []
            distributed_percent = Decimal('0')
            for index, item in enumerate(normalized):
                if index == len(normalized) - 1:
                    percent = self._clamp_percent(Decimal('100') - distributed_percent)
                else:
                    percent = self._clamp_percent(
                        ((item['worker_share_percent'] * Decimal('100')) / total_percent).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    )
                    distributed_percent += percent
                scaled.append({**item, 'worker_share_percent': percent})
            normalized = scaled

        share_base = max(Decimal('0'), self._money(worker_share_base))
        distributed_amount = Decimal('0')
        for index, item in enumerate(normalized):
            if index == len(normalized) - 1:
                amount = self._money(share_base - distributed_amount)
            else:
                amount = self._money((share_base * item['worker_share_percent']) / Decimal('100'))
                distributed_amount += amount
            item['worker_share_amount'] = max(Decimal('0'), amount)

        total_amount = sum((item['worker_share_amount'] for item in normalized), Decimal('0'))
        return normalized, total_amount

    def _distribute_tip(self, tip_amount, assigned_workers):
        tip_value = max(Decimal('0'), Decimal(str(tip_amount or 0)))
        if not assigned_workers:
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

        if tip_value <= 0:
            return [
                {
                    **item,
                    'tip_share_amount': Decimal('0'),
                }
                for item in prepared
            ], Decimal('0')

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
                    'service_id': line.service_id,
                    'service_name': line.custom_service_name or (line.service.name if line.service else 'خدمت'),
                    'custom_service_name': line.custom_service_name,
                    'quantity': line.quantity,
                    'list_unit_price': line.list_unit_price,
                    'unit_price': line.unit_price,
                    'line_total': line.line_total,
                    'discount_amount': line.discount_amount,
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

        available_services = []
        for service in Service.objects.filter(is_active=True, tenant=tenant).order_by('display_order', 'name'):
            pricing = service.resolve_pricing(
                tariff_type=getattr(vehicle, 'tariff_type', 'type_1'),
                plate_type=getattr(vehicle, 'plate_type', 'car'),
            )
            available_services.append(
                {
                    'id': service.id,
                    'name': service.name,
                    'base_price': pricing['sale_price'],
                    'list_price': pricing['list_price'],
                    'estimated_duration_minutes': pricing['duration_minutes'],
                    'tariff_type': pricing['tariff_type'],
                }
            )

        completed_lines = [line for line in vehicle.job.service_lines.all() if line.is_completed]
        services_total = sum((Decimal(str(line.line_total or 0)) for line in completed_lines), Decimal('0'))
        service_list_subtotal = sum(
            (
                self._service_line_list_total(line)
                for line in completed_lines
            ),
            Decimal('0'),
        )
        products_total = vehicle.job.products_total or Decimal('0')
        tip_amount = vehicle.job.tip_amount or Decimal('0')
        loyalty_profile = self._loyalty_profile(vehicle)
        settings_obj = GeneralSettings.objects.filter(tenant=tenant).order_by('id').first()
        order_loyalty = resolve_vehicle_loyalty_snapshot(
            vehicle,
            settings_obj=settings_obj,
            fallback_profile=loyalty_profile,
        )
        manual_discount_total = vehicle.job.manual_discount_total or Decimal('0')
        customer_score = Decimal(str(order_loyalty.get('score', 0) or 0))
        discount_percent_per_half_star = self._discount_percent_per_half_star(tenant)
        if getattr(vehicle.job, 'apply_loyalty_discount', True):
            customer_discount_percent, loyalty_discount_total = self._compute_configured_discount(
                base_amount=services_total,
                loyalty_profile=loyalty_profile,
                settings_obj=settings_obj,
                visit_count=order_loyalty.get('visit_count', 0),
                score=customer_score,
            )
            loyalty_discount_total = min(loyalty_discount_total, services_total)
        else:
            customer_discount_percent, loyalty_discount_total = Decimal('0'), Decimal('0')
        if order_loyalty.get('from_snapshot') and getattr(vehicle, 'loyalty_discount_percent_snapshot', None) is not None:
            customer_discount_percent = Decimal(str(vehicle.loyalty_discount_percent_snapshot or 0))
            if getattr(vehicle.job, 'apply_loyalty_discount', True):
                loyalty_discount_total = min(
                    services_total,
                    self._money((services_total * customer_discount_percent) / Decimal('100')),
                )
            else:
                loyalty_discount_total = Decimal('0')
        facility_discount_total = sum(
            (
                max(
                    Decimal('0'),
                    self._service_line_list_total(line) - Decimal(str(line.line_total or 0)),
                )
                for line in completed_lines
            ),
            Decimal('0'),
        )
        discount_total = min(
            service_list_subtotal,
            facility_discount_total + loyalty_discount_total + manual_discount_total,
        )
        taxable_total = max(Decimal('0'), service_list_subtotal - discount_total) + products_total
        tax_percent = self._tax_percent(tenant)
        tax_total = self._money((taxable_total * tax_percent) / Decimal('100'))
        final_total = taxable_total + tax_total + tip_amount
        assigned_workers = self._resolve_assigned_workers(vehicle.job)
        worker_share_distribution, distributed_worker_share_total = self._normalize_worker_share_distribution(
            assigned_workers=assigned_workers,
            raw_distribution=snapshot if isinstance((snapshot := vehicle.job.assigned_workers_snapshot), list) else [],
            worker_share_base=vehicle.job.worker_share_amount or Decimal('0'),
        )
        distribution_by_id = {int(item['id']): item for item in worker_share_distribution if item.get('id')}
        for worker in assigned_workers:
            distribution_item = distribution_by_id.get(int(worker['id']))
            if distribution_item:
                worker['worker_share_percent'] = distribution_item['worker_share_percent']
                worker['worker_share_amount'] = distribution_item['worker_share_amount']
        assigned_workers_with_tip, workers_tip_share_amount = self._distribute_tip(
            tip_amount=tip_amount,
            assigned_workers=assigned_workers,
        )
        assigned_workers_names = [item['name'] for item in assigned_workers_with_tip]
        manager = get_user_model().objects.filter(tenant=tenant, role='manager').order_by('id').first()

        return Response(
            {
                'vehicle': {
                    'id': vehicle.id,
                    'admission_number': vehicle.admission_number,
                    'tenant_address': getattr(tenant, 'address', '') or '',
                    'manager_phone': getattr(manager, 'phone', '') if manager else '',
                    'plate_number': vehicle.plate_number,
                    'car_model': vehicle.car_model,
                    'car_color': vehicle.car_color,
                    'driver_name': vehicle.driver_name,
                    'driver_gender': vehicle.driver_gender,
                    'driver_phone': vehicle.driver_phone,
                    'status': vehicle.status,
                    'payment_status': vehicle.payment_status,
                    'tariff_type': vehicle.tariff_type,
                    'customer_score': float(customer_score),
                    'customer_loyalty_visit_count': order_loyalty.get('visit_count', 0),
                    'customer_loyalty_discount_percent': float(customer_discount_percent or 0),
                    'discount_calculation_mode': getattr(settings_obj, 'discount_calculation_mode', 'step') if settings_obj else 'step',
                    'fixed_discount_notice': next_fixed_discount_notice(settings_obj, order_loyalty.get('visit_count', 0)),
                },
                'job': {
                    'id': vehicle.job.id,
                    'service_lines': service_lines,
                    'product_lines': product_lines,
                    'available_products': available_products,
                    'available_services': available_services,
                    'service_list_subtotal': service_list_subtotal,
                    'services_total': services_total,
                    'products_total': products_total,
                    'discount_percent_per_half_star': float(discount_percent_per_half_star),
                    'discount_calculation_mode': getattr(settings_obj, 'discount_calculation_mode', 'step') if settings_obj else 'step',
                    'fixed_visit_discounts': getattr(settings_obj, 'fixed_visit_discounts', {}) if settings_obj else {},
                    'customer_discount_percent': float(customer_discount_percent),
                    'facility_discount_total': facility_discount_total,
                    'apply_loyalty_discount': getattr(vehicle.job, 'apply_loyalty_discount', True),
                    'loyalty_discount_total': loyalty_discount_total,
                    'discount_total': discount_total,
                    'manual_discount_total': manual_discount_total,
                    'total_discount': discount_total,
                    'tax_total': tax_total,
                    'tax_percent': float(tax_percent),
                    'tip_amount': tip_amount,
                    'final_total': final_total,
                    'worker_share_amount': vehicle.job.worker_share_amount,
                    'worker_share_distributed_total': distributed_worker_share_total,
                    'workers_tip_share_amount': workers_tip_share_amount,
                    'carwash_share_amount': vehicle.job.carwash_share_amount,
                    'assigned_workers_names': assigned_workers_names,
                    'assigned_workers': [
                        {
                            'id': item['id'],
                            'name': item['name'],
                            'worker_share_percent': float(item.get('worker_share_percent') or 0),
                            'worker_share_amount': float(item.get('worker_share_amount') or 0),
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
        previous_status = vehicle.status
        is_existing_release = previous_status == VehicleEntry.Status.RELEASED

        service_lines_payload = request.data.get('service_lines', [])
        new_service_lines_payload = request.data.get('new_service_lines', [])
        product_lines_payload = request.data.get('product_lines', [])
        assigned_workers_payload = request.data.get('assigned_workers', None)
        worker_share_distribution_payload = request.data.get('worker_share_distribution', [])
        tip_amount = Decimal(str(request.data.get('tip_amount', vehicle.job.tip_amount or 0)))
        payment_method = str(request.data.get('payment_method', Payment.Method.CASH) or Payment.Method.CASH).strip().lower()
        payment_breakdown = request.data.get('payment_breakdown', [])
        sms_notifications_enabled = request.data.get('sms_notifications_enabled', vehicle.sms_notifications_enabled)
        if isinstance(sms_notifications_enabled, str):
            sms_notifications_enabled = sms_notifications_enabled.strip().lower() not in {'0', 'false', 'off', 'no'}
        credit_due_date = request.data.get('credit_due_date')
        cheque_number = str(request.data.get('cheque_number', '') or '').strip()
        cheque_serial_number = str(request.data.get('cheque_serial_number', '') or '').strip()
        cheque_sayadi_number = str(request.data.get('cheque_sayadi_number', '') or '').strip()
        cheque_bank = str(request.data.get('cheque_bank', '') or '').strip()
        cheque_shaba = str(request.data.get('cheque_shaba', '') or '').strip()
        cheque_amount = Decimal(str(request.data.get('cheque_amount', 0) or 0))
        bonus_amount = Decimal(str(request.data.get('bonus', 0) or 0))
        penalty_amount = Decimal(str(request.data.get('penalty', 0) or 0))
        bonus_penalty_worker_id = request.data.get('bonus_penalty_worker_id')
        bonus_penalty_adjustments = request.data.get('bonus_penalty_adjustments', [])
        bonus_penalty_note = str(request.data.get('bonus_penalty_note', '') or '').strip()
        normalized_adjustments = []
        if tip_amount < 0:
            return Response(
                {'tip_amount': ['Invalid tip value.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if bonus_amount < 0 or penalty_amount < 0:
            return Response(
                {'detail': 'Bonus and penalty must be positive values.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if isinstance(bonus_penalty_adjustments, list):
            for item in bonus_penalty_adjustments:
                if not isinstance(item, dict):
                    continue
                try:
                    worker_id = int(item.get('worker_id') or 0)
                except (TypeError, ValueError):
                    continue
                if worker_id <= 0:
                    continue
                item_bonus = Decimal(str(item.get('bonus', 0) or 0))
                item_penalty = Decimal(str(item.get('penalty', 0) or 0))
                if item_bonus < 0 or item_penalty < 0:
                    return Response(
                        {'detail': 'Bonus and penalty must be positive values.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if item_bonus <= 0 and item_penalty <= 0:
                    continue
                normalized_adjustments.append(
                    {
                        'worker_id': worker_id,
                        'bonus': item_bonus,
                        'penalty': item_penalty,
                    }
                )

        if not normalized_adjustments and bonus_penalty_worker_id and (bonus_amount > 0 or penalty_amount > 0):
            try:
                normalized_worker_id = int(bonus_penalty_worker_id or 0)
            except (TypeError, ValueError):
                normalized_worker_id = 0
            if normalized_worker_id > 0:
                normalized_adjustments.append(
                    {
                        'worker_id': normalized_worker_id,
                        'bonus': bonus_amount,
                        'penalty': penalty_amount,
                    }
                )

        if normalized_adjustments and not bonus_penalty_note:
            return Response(
                {'detail': 'توضیح پاداش یا جریمه الزامی است.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        valid_methods = {choice[0] for choice in Payment.Method.choices}
        if payment_method not in valid_methods:
            return Response({'payment_method': ['Invalid payment method.']}, status=status.HTTP_400_BAD_REQUEST)
        normalized_payment_breakdown = []
        if isinstance(payment_breakdown, list):
            for item in payment_breakdown:
                if not isinstance(item, dict):
                    continue
                method = str(item.get('method', '') or '').strip().lower()
                amount = self._money(item.get('amount', 0))
                if method not in {Payment.Method.CASH, Payment.Method.POS, Payment.Method.TRANSFER, Payment.Method.CHEQUE}:
                    continue
                if amount <= 0:
                    continue
                normalized_payment_breakdown.append({
                    'method': method,
                    'amount': float(amount),
                })
        if payment_method == Payment.Method.MANUAL and not normalized_payment_breakdown:
            return Response({'payment_breakdown': ['Payment breakdown is required for manual payment.']}, status=status.HTTP_400_BAD_REQUEST)
        manual_uses_cheque = payment_method == Payment.Method.MANUAL and any(
            item.get('method') == Payment.Method.CHEQUE for item in normalized_payment_breakdown
        )
        reminder_due_at = None
        if payment_method == Payment.Method.CREDIT:
            if not credit_due_date:
                return Response({'credit_due_date': ['Credit due date is required.']}, status=status.HTTP_400_BAD_REQUEST)
            try:
                reminder_due_at = timezone.make_aware(datetime.strptime(str(credit_due_date), '%Y-%m-%d'))
            except ValueError:
                return Response({'credit_due_date': ['Invalid date format.']}, status=status.HTTP_400_BAD_REQUEST)
        if payment_method == Payment.Method.CHEQUE or manual_uses_cheque:
            if not credit_due_date:
                return Response({'credit_due_date': ['Cheque due date is required.']}, status=status.HTTP_400_BAD_REQUEST)
            try:
                reminder_due_at = timezone.make_aware(datetime.strptime(str(credit_due_date), '%Y-%m-%d'))
            except ValueError:
                return Response({'credit_due_date': ['Invalid date format.']}, status=status.HTTP_400_BAD_REQUEST)
            if not cheque_serial_number:
                return Response({'cheque_serial_number': ['Cheque serial number is required.']}, status=status.HTTP_400_BAD_REQUEST)
            if not cheque_sayadi_number:
                return Response({'cheque_sayadi_number': ['Cheque sayadi number is required.']}, status=status.HTTP_400_BAD_REQUEST)
            if not cheque_bank:
                return Response({'cheque_bank': ['Cheque bank is required.']}, status=status.HTTP_400_BAD_REQUEST)
            if not cheque_shaba:
                return Response({'cheque_shaba': ['Cheque shaba is required.']}, status=status.HTTP_400_BAD_REQUEST)
            if cheque_amount <= 0:
                return Response({'cheque_amount': ['Cheque amount must be greater than zero.']}, status=status.HTTP_400_BAD_REQUEST)
            cheque_number = cheque_serial_number

        service_lines_map = {line.id: line for line in vehicle.job.service_lines.all()}
        for item in service_lines_payload:
            line_id = item.get('id')
            line = service_lines_map.get(line_id)
            if not line:
                continue
            line.is_completed = bool(item.get('is_completed', False))
            line.save(update_fields=['is_completed'])

        for item in new_service_lines_payload:
            service_obj = None
            service_id = item.get('service_id')
            if service_id:
                service_obj = Service.objects.filter(id=service_id, tenant=tenant, is_active=True).first()
            service_name = str(
                item.get('service_name')
                or item.get('title')
                or (service_obj.name if service_obj else '')
            ).strip()
            if not service_name:
                continue
            quantity = Decimal(str(item.get('quantity', 1) or 1))
            default_price = 0
            default_list_price = 0
            if service_obj:
                pricing = service_obj.resolve_pricing(
                    tariff_type=getattr(vehicle, 'tariff_type', 'type_1'),
                    plate_type=getattr(vehicle, 'plate_type', 'car'),
                )
                default_list_price = pricing['list_price']
                default_price = pricing['sale_price']
            unit_price = Decimal(str(item.get('unit_price', item.get('price', default_price)) or 0))
            list_unit_price = Decimal(str(item.get('list_unit_price', default_list_price or unit_price) or 0))
            is_completed = bool(item.get('is_completed', True))
            if quantity <= 0 or unit_price < 0:
                continue
            vehicle.job.service_lines.create(
                tenant=tenant,
                service=service_obj,
                custom_service_name=service_name,
                quantity=quantity,
                list_unit_price=list_unit_price,
                unit_price=unit_price,
                line_total=unit_price * quantity,
                discount_amount=0,
                is_completed=is_completed,
                note='خدمت سفارشی ثبت شده در ترخیص',
            )

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

        completed_lines = list(vehicle.job.service_lines.filter(is_completed=True))
        completed_service_totals = sum((Decimal(str(line.line_total or 0)) for line in completed_lines), Decimal('0'))
        completed_service_list_subtotal = sum(
            (
                self._service_line_list_total(line)
                for line in completed_lines
            ),
            Decimal('0'),
        )
        manual_discount_total = vehicle.job.manual_discount_total or Decimal('0')
        loyalty_profile = self._loyalty_profile(vehicle)
        settings_obj = GeneralSettings.objects.filter(tenant=tenant).order_by('id').first()
        order_loyalty = resolve_vehicle_loyalty_snapshot(
            vehicle,
            settings_obj=settings_obj,
            fallback_profile=loyalty_profile,
        )
        customer_score = Decimal(str(order_loyalty.get('score', 0) or 0))
        discount_percent_per_half_star = self._discount_percent_per_half_star(tenant)
        if getattr(vehicle.job, 'apply_loyalty_discount', True):
            customer_discount_percent, loyalty_discount_total = self._compute_configured_discount(
                base_amount=completed_service_totals,
                loyalty_profile=loyalty_profile,
                settings_obj=settings_obj,
                visit_count=order_loyalty.get('visit_count', 0),
                score=customer_score,
            )
            loyalty_discount_total = min(loyalty_discount_total, completed_service_totals)
        else:
            customer_discount_percent, loyalty_discount_total = Decimal('0'), Decimal('0')
        if order_loyalty.get('from_snapshot') and getattr(vehicle, 'loyalty_discount_percent_snapshot', None) is not None:
            customer_discount_percent = Decimal(str(vehicle.loyalty_discount_percent_snapshot or 0))
            if getattr(vehicle.job, 'apply_loyalty_discount', True):
                loyalty_discount_total = min(
                    completed_service_totals,
                    self._money((completed_service_totals * customer_discount_percent) / Decimal('100')),
                )
            else:
                loyalty_discount_total = Decimal('0')
        facility_discount_total = sum(
            (
                max(
                    Decimal('0'),
                    self._service_line_list_total(line) - Decimal(str(line.line_total or 0)),
                )
                for line in completed_lines
            ),
            Decimal('0'),
        )
        discount_total = min(
            completed_service_list_subtotal,
            facility_discount_total + loyalty_discount_total + manual_discount_total,
        )
        post_sale_discount_total = min(
            completed_service_totals,
            loyalty_discount_total + manual_discount_total,
        )
        taxable_total = max(Decimal('0'), completed_service_list_subtotal - discount_total) + product_totals
        tax_percent = self._tax_percent(tenant)
        tax_total = self._money((taxable_total * tax_percent) / Decimal('100'))
        final_total = taxable_total + tax_total + tip_amount

        # Product sales are not shareable — commission pool is services only.
        share_base_total = completed_service_totals
        worker_share_base = vehicle.job.worker_share_amount or Decimal('0')
        if worker_share_base <= 0:
            payment_type = getattr(vehicle.job, 'worker_payment_type', '') or ''
            if payment_type == VehicleJob.WorkerPaymentType.PERCENT:
                percent = min(Decimal('100'), max(Decimal('0'), Decimal(str(vehicle.job.worker_payment_percent or 0))))
                worker_share_base = self._money((share_base_total * percent) / Decimal('100'))
            elif payment_type in {VehicleJob.WorkerPaymentType.FIXED, VehicleJob.WorkerPaymentType.HOURLY}:
                worker_share_base = min(share_base_total, self._money(vehicle.job.worker_payment_fixed or 0))
        if worker_share_base > share_base_total:
            worker_share_base = share_base_total

        assigned_workers_from_payload = self._resolve_workers_from_payload(tenant, assigned_workers_payload)
        assigned_workers = (
            assigned_workers_from_payload
            if assigned_workers_from_payload is not None
            else self._resolve_assigned_workers(vehicle.job)
        )
        if assigned_workers_payload is not None and not assigned_workers:
            return Response(
                {'assigned_workers': ['حداقل یک پرسنل معتبر انتخاب کنید.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        worker_share_distribution, worker_share_base_total = self._normalize_worker_share_distribution(
            assigned_workers=assigned_workers,
            raw_distribution=worker_share_distribution_payload,
            worker_share_base=worker_share_base,
        )
        distribution_by_id = {int(item['id']): item for item in worker_share_distribution if item.get('id')}
        for worker in assigned_workers:
            distribution_item = distribution_by_id.get(int(worker['id']))
            if distribution_item:
                worker['worker_share_percent'] = distribution_item['worker_share_percent']
                worker['worker_share_amount'] = distribution_item['worker_share_amount']
        assigned_workers_with_tip, workers_tip_share_amount = self._distribute_tip(
            tip_amount=tip_amount,
            assigned_workers=assigned_workers,
        )
        carwash_share = (share_base_total - worker_share_base_total) + max(
            Decimal('0'),
            tip_amount - workers_tip_share_amount,
        ) - post_sale_discount_total
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
                    'worker_share_percent': float(worker_data.get('worker_share_percent') or 0),
                    'worker_share_amount': float(worker_data.get('worker_share_amount') or 0),
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
                    'worker_share_percent': float(worker_data.get('worker_share_percent') or 0),
                    'worker_share_amount': float(worker_data.get('worker_share_amount') or 0),
                    'tip_share_percent': float(worker_data.get('tip_share_percent') or 0),
                    'tip_share_amount': float(worker_data.get('tip_share_amount') or 0),
                }
            )

        vehicle.job.services_total = completed_service_totals
        vehicle.job.products_total = product_totals
        vehicle.job.tip_amount = tip_amount
        vehicle.job.workers_tip_share_amount = workers_tip_share_amount
        vehicle.job.discount_total = discount_total
        vehicle.job.facility_discount_total = facility_discount_total
        vehicle.job.loyalty_discount_total = loyalty_discount_total
        vehicle.job.tax_total = tax_total
        vehicle.job.service_list_subtotal = completed_service_list_subtotal
        vehicle.job.total_discount = discount_total
        vehicle.job.final_total = final_total
        vehicle.job.worker_share_amount = worker_share_base_total
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
                'facility_discount_total',
                'loyalty_discount_total',
                'tax_total',
                'service_list_subtotal',
                'total_discount',
                'final_total',
                'worker_share_amount',
                'carwash_share_amount',
                'assigned_workers_snapshot',
                'released_at',
                'updated_at',
            ]
        )

        for line in vehicle.job.product_lines.select_related('product').all():
            if is_existing_release:
                continue
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
                            f'موجودی محصول «{line.product.name}» کافی نیست.'
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

        payment_status = VehicleEntry.PaymentStatus.PAID
        payment_record_status = Payment.Status.SUCCESS
        paid_at = timezone.now()
        if payment_method in {Payment.Method.CREDIT, Payment.Method.CHEQUE}:
            payment_status = VehicleEntry.PaymentStatus.UNPAID
            payment_record_status = Payment.Status.PENDING
            paid_at = None

        payment_defaults = {
            'method': payment_method,
            'status': payment_record_status,
            'amount': final_total,
            'tip_amount': tip_amount,
            'service_amount': completed_service_totals,
            'product_amount': product_totals,
            'discount_amount': discount_total,
            'tax_amount': tax_total,
            'gateway_payload': {'payment_breakdown': normalized_payment_breakdown} if normalized_payment_breakdown else {},
            'paid_at': paid_at,
            'payer_name': vehicle.driver_name or '',
            'payer_phone': vehicle.driver_phone or '',
            'cheque_number': cheque_number,
            'cheque_serial_number': cheque_serial_number,
            'cheque_sayadi_number': cheque_sayadi_number,
            'cheque_bank': cheque_bank,
            'cheque_shaba': cheque_shaba,
            'cheque_amount': cheque_amount if payment_method == Payment.Method.CHEQUE or manual_uses_cheque else Decimal('0'),
            'reminder_due_at': reminder_due_at,
        }
        latest_payment = vehicle.payments.order_by('-created_at', '-id').first() if is_existing_release else None
        if latest_payment:
            for field_name, field_value in payment_defaults.items():
                setattr(latest_payment, field_name, field_value)
            latest_payment.save(update_fields=[*payment_defaults.keys(), 'updated_at'])
        else:
            Payment.objects.create(
                tenant=tenant,
                vehicle_entry=vehicle,
                created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
                **payment_defaults,
            )

        if payment_method == Payment.Method.CREDIT and vehicle.driver_phone:
            NotificationLog.objects.create(
                tenant=tenant,
                vehicle_entry=vehicle,
                channel=NotificationLog.Channel.SMS,
                recipient=vehicle.driver_phone,
                template_code='credit_reminder',
                payload={
                    'driver_name': vehicle.driver_name,
                    'plate_number': vehicle.plate_number,
                    'amount_due': float(final_total),
                    'due_date': credit_due_date,
                },
                status=NotificationLog.Status.PENDING,
                created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
            )

        vehicle.payment_status = payment_status
        vehicle.payment_method = payment_method
        vehicle.status = VehicleEntry.Status.RELEASED
        vehicle.sms_notifications_enabled = bool(sms_notifications_enabled)
        if not vehicle.released_at:
            vehicle.released_at = timezone.now()
        vehicle.save(update_fields=['status', 'payment_status', 'payment_method', 'sms_notifications_enabled', 'released_at', 'updated_at'])

        if normalized_adjustments:
            workers_map = {
                worker.id: worker
                for worker in WorkerProfile.objects.filter(
                    tenant=tenant,
                    id__in=[item['worker_id'] for item in normalized_adjustments],
                )
            }
            for item in normalized_adjustments:
                worker = workers_map.get(item['worker_id'])
                if not worker:
                    continue
                if item['bonus'] > 0:
                    WorkerPayoutTransaction.objects.create(
                        tenant=tenant,
                        worker=worker,
                        vehicle_job=vehicle.job,
                        kind=WorkerPayoutTransaction.Kind.BONUS,
                        amount=item['bonus'],
                        note=bonus_penalty_note,
                        created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
                    )
                if item['penalty'] > 0:
                    WorkerPayoutTransaction.objects.create(
                        tenant=tenant,
                        worker=worker,
                        vehicle_job=vehicle.job,
                        kind=WorkerPayoutTransaction.Kind.PENALTY,
                        amount=item['penalty'],
                        note=bonus_penalty_note,
                        created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
                    )

        if previous_status != VehicleEntry.Status.RELEASED:
            VehicleStatusLog.objects.create(
                tenant=vehicle.tenant,
                vehicle=vehicle,
                from_status=previous_status,
                to_status=VehicleEntry.Status.RELEASED,
                changed_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
                note='ترخیص خودرو',
            )

        serializer = VehicleEntrySerializer(vehicle)
        send_vehicle_event_sms(
            'vehicle_released',
            tenant,
            vehicle,
            created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
            extra_context={
                'released_at': vehicle.released_at or timezone.now(),
                'customer_score': float(customer_score or 0),
                'next_discount_percent': float(loyalty_snapshot(loyalty_profile).get('discount_percent', 0) or 0),
                'visit_count': int(order_loyalty.get('visit_count', 0) or 0),
                'final_total': float(final_total or 0),
                'discount_total': float(discount_total or 0),
                'facility_discount_total': float(facility_discount_total or 0),
                'loyalty_discount_total': float(loyalty_discount_total or 0),
                'manual_discount_total': float(manual_discount_total or 0),
                'tip_amount': float(tip_amount or 0),
                'tax_total': float(tax_total or 0),
            },
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class VehicleJobAdjustView(VehicleReleaseCheckoutView):
    permission_classes = [permissions.IsAuthenticated]

    def _snapshot_from_workers(self, assigned_workers_with_tip):
        return [
            {
                'id': int(item['id']),
                'name': item.get('name') or '',
                'worker_share_percent': float(item.get('worker_share_percent') or 0),
                'worker_share_amount': float(item.get('worker_share_amount') or 0),
                'tip_share_percent': float(item.get('tip_share_percent') or 0),
                'tip_share_amount': float(item.get('tip_share_amount') or 0),
            }
            for item in assigned_workers_with_tip
            if item.get('id')
        ]

    def _recompute_job_totals(self, job, *, tip_amount, workers_tip_share_amount):
        service_list_subtotal = self._money(job.service_list_subtotal or 0)
        services_total = self._money(job.services_total or 0)
        products_total = self._money(job.products_total or 0)
        discount_total = self._money(job.total_discount or job.discount_total or 0)
        tax_total = self._money(job.tax_total or 0)
        worker_share_amount = self._money(job.worker_share_amount or 0)
        post_sale_discount_total = self._money(job.loyalty_discount_total or 0) + self._money(job.manual_discount_total or 0)
        final_total = max(Decimal('0'), service_list_subtotal - discount_total) + products_total + tax_total + tip_amount
        carwash_share = (
            max(Decimal('0'), services_total - worker_share_amount)
            + max(Decimal('0'), tip_amount - workers_tip_share_amount)
            - post_sale_discount_total
        )
        return self._money(final_total), max(Decimal('0'), self._money(carwash_share))

    @transaction.atomic
    def patch(self, request, pk):
        tenant = getattr(request.user, 'tenant', None)
        vehicle = (
            VehicleEntry.objects.select_for_update()
            .select_related('job')
            .filter(pk=pk, tenant=tenant)
            .first()
        )
        if not vehicle or not getattr(vehicle, 'job', None):
            return Response({'detail': 'Vehicle job not found.'}, status=status.HTTP_404_NOT_FOUND)

        job = vehicle.job
        assigned_workers_payload = request.data.get('assigned_workers', None)
        worker_share_distribution_payload = request.data.get('worker_share_distribution', [])
        tip_amount = self._money(request.data.get('tip_amount', job.tip_amount or 0))
        if tip_amount < 0:
            return Response({'tip_amount': ['Invalid tip value.']}, status=status.HTTP_400_BAD_REQUEST)

        assigned_workers_from_payload = self._resolve_workers_from_payload(tenant, assigned_workers_payload)
        assigned_workers = (
            assigned_workers_from_payload
            if assigned_workers_from_payload is not None
            else self._resolve_assigned_workers(job)
        )
        if assigned_workers_payload is not None and not assigned_workers:
            return Response(
                {'assigned_workers': ['حداقل یک پرسنل معتبر انتخاب کنید.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        worker_share_distribution, worker_share_base_total = self._normalize_worker_share_distribution(
            assigned_workers=assigned_workers,
            raw_distribution=worker_share_distribution_payload,
            worker_share_base=job.worker_share_amount or Decimal('0'),
        )
        distribution_by_id = {int(item['id']): item for item in worker_share_distribution if item.get('id')}
        for worker in assigned_workers:
            distribution_item = distribution_by_id.get(int(worker['id']))
            if distribution_item:
                worker['worker_share_percent'] = distribution_item['worker_share_percent']
                worker['worker_share_amount'] = distribution_item['worker_share_amount']

        assigned_workers_with_tip, workers_tip_share_amount = self._distribute_tip(
            tip_amount=tip_amount,
            assigned_workers=assigned_workers,
        )
        final_total, carwash_share = self._recompute_job_totals(
            job,
            tip_amount=tip_amount,
            workers_tip_share_amount=workers_tip_share_amount,
        )

        primary_worker_id = assigned_workers_with_tip[0]['id'] if assigned_workers_with_tip else None
        primary_worker = None
        if primary_worker_id:
            primary_worker = WorkerProfile.objects.filter(
                tenant=tenant,
                id=primary_worker_id,
                user__role='worker',
            ).first()

        job.assigned_worker = primary_worker
        job.assigned_workers_snapshot = self._snapshot_from_workers(assigned_workers_with_tip)
        job.tip_amount = tip_amount
        job.workers_tip_share_amount = workers_tip_share_amount
        job.worker_share_amount = worker_share_base_total
        job.carwash_share_amount = carwash_share
        job.final_total = final_total
        job.save(update_fields=[
            'assigned_worker',
            'assigned_workers_snapshot',
            'tip_amount',
            'workers_tip_share_amount',
            'worker_share_amount',
            'carwash_share_amount',
            'final_total',
            'updated_at',
        ])

        if assigned_workers_payload is not None and assigned_workers_with_tip:
            WorkerProfile.objects.filter(
                tenant=tenant,
                id__in=[int(item['id']) for item in assigned_workers_with_tip],
                user__role='worker',
            ).update(last_assigned_at=timezone.now(), updated_at=timezone.now())

        latest_payment = vehicle.payments.order_by('-created_at', '-id').first()
        if latest_payment:
            latest_payment.amount = final_total
            latest_payment.tip_amount = tip_amount
            latest_payment.save(update_fields=['amount', 'tip_amount', 'updated_at'])

        vehicle.updated_by = request.user if getattr(request.user, 'is_authenticated', False) else None
        vehicle.save(update_fields=['updated_by', 'updated_at'])
        return Response(VehicleEntrySerializer(vehicle).data, status=status.HTTP_200_OK)
