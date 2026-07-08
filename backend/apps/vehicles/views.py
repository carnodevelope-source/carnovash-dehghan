from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import BlockedPlate, VehicleEntry, VehicleStatusLog
from .serializers import VehicleEntrySerializer
from apps.inventory.models import InventoryItem
from apps.inventory.models import StockMovement
from apps.notifications.models import NotificationLog
from apps.notifications.services import send_vehicle_event_sms
from apps.payments.models import Payment
from apps.products.models import Product
from apps.services.models import GeneralSettings, Service
from apps.workers.models import WorkerProfile
from apps.reports.models import WorkerPayoutTransaction


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


def _normalized_plate_value(plate_number='', plate_left='', plate_letter='', plate_mid='', plate_right=''):
    left = str(plate_left or '').strip()
    letter = str(plate_letter or '').strip()
    mid = str(plate_mid or '').strip()
    right = str(plate_right or '').strip()
    if left and letter and mid and right:
        return f'{left} {letter} {mid} {right}'
    return str(plate_number or '').strip()


_PERSIAN_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
_AI_LETTER_MAP = {
    'a': 'ا',
    'b': 'ب',
    'c': 'ص',
    'd': 'د',
    'e': 'ه',
    'f': 'ف',
    'g': 'گ',
    'h': 'ح',
    'i': 'ی',
    'j': 'ج',
    'k': 'ک',
    'l': 'ل',
    'm': 'م',
    'n': 'ن',
    'o': 'و',
    'p': 'پ',
    'q': 'ق',
    'r': 'ر',
    's': 'س',
    't': 'ط',
    'u': 'ع',
    'v': 'و',
    'w': 'و',
    'x': 'ش',
    'y': 'ی',
    'z': 'ز',
}

_PLATE_LETTER_WORD_MAP = {
    'الف': 'ا',
    'ا': 'ا',
    'ب': 'ب',
    'پ': 'پ',
    'ت': 'ت',
    'ث': 'ث',
    'ج': 'ج',
    'چ': 'چ',
    'ح': 'ح',
    'خ': 'خ',
    'د': 'د',
    'ذ': 'ذ',
    'ر': 'ر',
    'ز': 'ز',
    'ژ': 'ژ',
    'س': 'س',
    'ش': 'ش',
    'ص': 'ص',
    'ض': 'ض',
    'ط': 'ط',
    'ظ': 'ظ',
    'ع': 'ع',
    'غ': 'غ',
    'ف': 'ف',
    'ق': 'ق',
    'ک': 'ک',
    'ك': 'ک',
    'گ': 'گ',
    'ل': 'ل',
    'م': 'م',
    'ن': 'ن',
    'و': 'و',
    'ه': 'ه',
    'ی': 'ی',
    'ي': 'ی',
}


def _normalized_ai_letter(value=''):
    token = str(value or '').strip().lower()
    if not token:
        return ''
    token = token.replace('ك', 'ک').replace('ي', 'ی')
    if token in _AI_LETTER_MAP:
        return _AI_LETTER_MAP[token]
    if token in _PLATE_LETTER_WORD_MAP:
        return _PLATE_LETTER_WORD_MAP[token]
    first_char = token[:1]
    if first_char in _AI_LETTER_MAP:
        return _AI_LETTER_MAP[first_char]
    return _PLATE_LETTER_WORD_MAP.get(first_char, '')


def _plate_parts_from_ai(raw_text='', persian_text=''):
    raw = str(raw_text or '').strip().lower()
    compact_raw = ''.join(ch for ch in raw if ch.isalnum())
    raw_match = re.search(r'(\d{2})([a-z])(\d{3})(\d{2})', compact_raw)
    if raw_match:
        left, letter_token, mid, right = raw_match.groups()
        letter = _normalized_ai_letter(letter_token)
        if letter:
            return {
                'plate_left': left,
                'plate_letter': letter,
                'plate_mid': mid,
                'plate_right': right,
                'plate_number': f'{left} {letter} {mid} {right}',
            }

    normalized = str(persian_text or '').translate(_PERSIAN_DIGITS)
    normalized = normalized.replace('ك', 'ک').replace('ي', 'ی')
    tokenized = re.sub(r'[^0-9A-Za-zآ-ی]+', ' ', normalized).split()
    for index in range(max(0, len(tokenized) - 3)):
        left = ''.join(ch for ch in tokenized[index] if ch.isdigit())[:2]
        letter = _normalized_ai_letter(tokenized[index + 1])
        mid = ''.join(ch for ch in tokenized[index + 2] if ch.isdigit())[:3]
        right = ''.join(ch for ch in tokenized[index + 3] if ch.isdigit())[:2]
        if len(left) == 2 and letter and len(mid) == 3 and len(right) == 2:
            return {
                'plate_left': left,
                'plate_letter': letter,
                'plate_mid': mid,
                'plate_right': right,
                'plate_number': f'{left} {letter} {mid} {right}',
            }

    inline_match = re.search(r'(\d{2})\s*([^0-9\s]{1,4})\s*(\d{3})\s*(\d{2})', normalized)
    if inline_match:
        left, letter_token, mid, right = inline_match.groups()
        letter = _normalized_ai_letter(letter_token)
        if letter:
            return {
                'plate_left': left,
                'plate_letter': letter,
                'plate_mid': mid,
                'plate_right': right,
                'plate_number': f'{left} {letter} {mid} {right}',
            }
    return {}


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

        previous_status = instance.status
        instance.status = new_status
        if new_status == VehicleEntry.Status.READY_TO_SETTLE:
            instance.ready_at = timezone.now()
        elif new_status == VehicleEntry.Status.RELEASED:
            instance.released_at = timezone.now()
        instance.save(update_fields=['status', 'ready_at', 'released_at', 'updated_at'])

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

        if previous_status != new_status:
            if new_status == VehicleEntry.Status.READY_TO_SETTLE:
                send_vehicle_event_sms(
                    'vehicle_assigned',
                    instance.tenant,
                    instance,
                    created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
                    extra_context={'assigned_at': instance.ready_at or timezone.now()},
                )
            elif new_status == VehicleEntry.Status.RELEASED:
                job = getattr(instance, 'job', None)
                send_vehicle_event_sms(
                    'vehicle_released',
                    instance.tenant,
                    instance,
                    created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
                    extra_context={
                        'released_at': instance.released_at or timezone.now(),
                        'customer_score': float(getattr(getattr(instance, 'customer', None), 'yearly_score', 0) or 0),
                        'next_discount_percent': 0,
                        'final_total': float(
                            (getattr(job, 'final_total', 0) or 0)
                            or (getattr(job, 'services_total', 0) or 0)
                        ),
                        'discount_total': float(
                            (getattr(job, 'discount_total', 0) or 0)
                            + (getattr(job, 'manual_discount_total', 0) or 0)
                        ),
                    },
                )

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BlockedPlateStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request.user, 'tenant', None)
        plate_number = _normalized_plate_value(
            plate_number=request.query_params.get('plate_number', ''),
            plate_left=request.query_params.get('plate_left', ''),
            plate_letter=request.query_params.get('plate_letter', ''),
            plate_mid=request.query_params.get('plate_mid', ''),
            plate_right=request.query_params.get('plate_right', ''),
        )
        if not plate_number:
            return Response({'is_blocked': False}, status=status.HTTP_200_OK)
        blocked = BlockedPlate.objects.filter(tenant=tenant, plate_number=plate_number).first()
        return Response(
            {
                'plate_number': plate_number,
                'is_blocked': bool(blocked),
                'blocked_at': blocked.created_at if blocked else None,
            },
            status=status.HTTP_200_OK,
        )


class VehiclePlateLookupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request.user, 'tenant', None)
        plate_number = _normalized_plate_value(
            plate_number=request.query_params.get('plate_number', ''),
            plate_left=request.query_params.get('plate_left', ''),
            plate_letter=request.query_params.get('plate_letter', ''),
            plate_mid=request.query_params.get('plate_mid', ''),
            plate_right=request.query_params.get('plate_right', ''),
        )
        if not plate_number:
            return Response({'found': False}, status=status.HTTP_200_OK)
        latest_vehicle = VehicleEntry.objects.filter(
            tenant=tenant,
            plate_number=plate_number,
        ).order_by('-check_in_at').first()
        if not latest_vehicle:
            return Response({'found': False, 'plate_number': plate_number}, status=status.HTTP_200_OK)
        return Response(
            {
                'found': True,
                'plate_number': plate_number,
                'plate_left': latest_vehicle.plate_left or '',
                'plate_letter': latest_vehicle.plate_letter or '',
                'plate_mid': latest_vehicle.plate_mid or '',
                'plate_right': latest_vehicle.plate_right or '',
                'plate_type': latest_vehicle.plate_type or VehicleEntry.PlateType.CAR,
                'driver_name': latest_vehicle.driver_name or '',
                'driver_phone': latest_vehicle.driver_phone or '',
                'car_model': latest_vehicle.car_model or '',
                'car_color': latest_vehicle.car_color or '',
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
        payload = json.dumps(
            {
                'session_id': session_id,
                'image_base64': image_base64,
                'timeout_sec': max(1.0, timeout_seconds - 0.5),
                'force_process': True,
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
        return Response(
            {
                **upstream_data,
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

    def post(self, request, pk):
        tenant = getattr(request.user, 'tenant', None)
        vehicle = VehicleEntry.objects.filter(pk=pk, tenant=tenant).first()
        if not vehicle:
            return Response({'detail': 'Vehicle not found.'}, status=status.HTTP_404_NOT_FOUND)
        blocked_plate, created = BlockedPlate.objects.get_or_create(
            tenant=tenant,
            plate_number=_normalized_plate_value(
                plate_number=vehicle.plate_number,
                plate_left=vehicle.plate_left,
                plate_letter=vehicle.plate_letter,
                plate_mid=vehicle.plate_mid,
                plate_right=vehicle.plate_right,
            ),
            defaults={
                'plate_left': vehicle.plate_left,
                'plate_letter': vehicle.plate_letter,
                'plate_mid': vehicle.plate_mid,
                'plate_right': vehicle.plate_right,
                'plate_type': vehicle.plate_type or VehicleEntry.PlateType.CAR,
                'blocked_by': request.user if getattr(request.user, 'is_authenticated', False) else None,
                'note': (request.data.get('note') or '').strip(),
            },
        )
        if not created and not blocked_plate.blocked_by_id and getattr(request.user, 'is_authenticated', False):
            blocked_plate.blocked_by = request.user
            blocked_plate.save(update_fields=['blocked_by', 'updated_at'])
        return Response(
            {
                'plate_number': blocked_plate.plate_number,
                'is_blocked': True,
                'created': created,
            },
            status=status.HTTP_200_OK,
        )


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

    def _plate_yearly_score(self, vehicle):
        plate_number = str(getattr(vehicle, 'plate_number', '') or '').strip()
        tenant = getattr(vehicle, 'tenant', None)
        if not plate_number or not tenant:
            return Decimal('0')
        current_year = timezone.localtime().year
        visits = VehicleEntry.objects.filter(
            tenant=tenant,
            plate_number=plate_number,
            check_in_at__year=current_year,
        ).count()
        return min(Decimal('5.0'), Decimal(str(visits)) * Decimal('0.5'))

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
                WorkerProfile.objects.select_related('user').filter(tenant=job.tenant)
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
                    'service_id': line.service_id,
                    'service_name': line.custom_service_name or (line.service.name if line.service else 'خدمت'),
                    'custom_service_name': line.custom_service_name,
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

        services_total = (
            vehicle.job.service_lines.filter(is_completed=True).aggregate(total=Sum('line_total')).get('total')
            or Decimal('0')
        )
        products_total = vehicle.job.products_total or Decimal('0')
        tip_amount = vehicle.job.tip_amount or Decimal('0')
        discount_base = services_total + products_total
        manual_discount_total = vehicle.job.manual_discount_total or Decimal('0')
        customer_score = self._plate_yearly_score(vehicle)
        discount_percent_per_half_star = self._discount_percent_per_half_star(tenant)
        customer_discount_percent, discount_total = self._compute_discount(
            base_amount=discount_base,
            customer_score=customer_score,
            percent_per_half_star=discount_percent_per_half_star,
        )
        discount_total = discount_total + manual_discount_total
        final_total = discount_base - discount_total + tip_amount
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
                    'tariff_type': vehicle.tariff_type,
                    'customer_score': float(customer_score),
                },
                'job': {
                    'id': vehicle.job.id,
                    'service_lines': service_lines,
                    'product_lines': product_lines,
                    'available_products': available_products,
                    'available_services': available_services,
                    'services_total': services_total,
                    'products_total': products_total,
                    'discount_percent_per_half_star': float(discount_percent_per_half_star),
                    'customer_discount_percent': float(customer_discount_percent),
                    'discount_total': discount_total,
                    'manual_discount_total': manual_discount_total,
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
        if vehicle.status == VehicleEntry.Status.RELEASED:
            return Response({'detail': 'Vehicle already released.'}, status=status.HTTP_400_BAD_REQUEST)
        previous_status = vehicle.status

        service_lines_payload = request.data.get('service_lines', [])
        new_service_lines_payload = request.data.get('new_service_lines', [])
        product_lines_payload = request.data.get('product_lines', [])
        worker_share_distribution_payload = request.data.get('worker_share_distribution', [])
        tip_amount = Decimal(str(request.data.get('tip_amount', vehicle.job.tip_amount or 0)))
        payment_method = str(request.data.get('payment_method', Payment.Method.CASH) or Payment.Method.CASH).strip().lower()
        payment_breakdown = request.data.get('payment_breakdown', [])
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
            if service_obj:
                pricing = service_obj.resolve_pricing(
                    tariff_type=getattr(vehicle, 'tariff_type', 'type_1'),
                    plate_type=getattr(vehicle, 'plate_type', 'car'),
                )
                default_price = pricing['sale_price']
            unit_price = Decimal(str(item.get('unit_price', item.get('price', default_price)) or 0))
            is_completed = bool(item.get('is_completed', True))
            if quantity <= 0 or unit_price < 0:
                continue
            vehicle.job.service_lines.create(
                tenant=tenant,
                service=service_obj,
                custom_service_name=service_name,
                quantity=quantity,
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

        completed_service_totals = (
            vehicle.job.service_lines.filter(is_completed=True).aggregate(total=Sum('line_total')).get('total')
            or Decimal('0')
        )
        discount_base = completed_service_totals + product_totals
        manual_discount_total = vehicle.job.manual_discount_total or Decimal('0')
        customer_score = self._plate_yearly_score(vehicle)
        discount_percent_per_half_star = self._discount_percent_per_half_star(tenant)
        _customer_discount_percent, discount_total = self._compute_discount(
            base_amount=discount_base,
            customer_score=customer_score,
            percent_per_half_star=discount_percent_per_half_star,
        )
        discount_total = discount_total + manual_discount_total
        final_total = discount_base - discount_total + tip_amount

        share_base_total = completed_service_totals
        worker_share_base = vehicle.job.worker_share_amount or Decimal('0')
        if worker_share_base > share_base_total:
            worker_share_base = share_base_total

        assigned_workers = self._resolve_assigned_workers(vehicle.job)
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
        vehicle.job.tax_total = 0
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

        payment_status = VehicleEntry.PaymentStatus.PAID
        payment_record_status = Payment.Status.SUCCESS
        paid_at = timezone.now()
        if payment_method in {Payment.Method.CREDIT, Payment.Method.CHEQUE}:
            payment_status = VehicleEntry.PaymentStatus.UNPAID
            payment_record_status = Payment.Status.PENDING
            paid_at = None

        Payment.objects.create(
            tenant=tenant,
            vehicle_entry=vehicle,
            method=payment_method,
            status=payment_record_status,
            amount=final_total,
            tip_amount=tip_amount,
            service_amount=completed_service_totals,
            product_amount=product_totals,
            discount_amount=discount_total,
            tax_amount=Decimal('0'),
            gateway_payload={'payment_breakdown': normalized_payment_breakdown} if normalized_payment_breakdown else {},
            paid_at=paid_at,
            payer_name=vehicle.driver_name or '',
            payer_phone=vehicle.driver_phone or '',
            cheque_number=cheque_number,
            cheque_serial_number=cheque_serial_number,
            cheque_sayadi_number=cheque_sayadi_number,
            cheque_bank=cheque_bank,
            cheque_shaba=cheque_shaba,
            cheque_amount=cheque_amount if payment_method == Payment.Method.CHEQUE or manual_uses_cheque else Decimal('0'),
            reminder_due_at=reminder_due_at,
            created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
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
        vehicle.released_at = timezone.now()
        vehicle.save(update_fields=['status', 'payment_status', 'payment_method', 'released_at', 'updated_at'])

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
                'next_discount_percent': float(_customer_discount_percent or 0),
                'final_total': float(final_total or 0),
                'discount_total': float(discount_total or 0),
            },
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
