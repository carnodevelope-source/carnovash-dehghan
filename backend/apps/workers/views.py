from datetime import datetime, time, timedelta

from django.db.models import F
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auth.feature_access import (
    ATTENDANCE_FREE_WORKERS_LIMIT,
    free_attendance_worker_ids,
    tenant_worker_count,
    worker_has_attendance_access,
)
from apps.auth.sms import send_user_credentials_sms

from .models import WorkerAttendance, WorkerProfile
from .serializers import (
    WorkerAttendanceEventSerializer,
    WorkerProfileCreateUpdateSerializer,
    WorkerProfileListSerializer,
    _resolve_request_tenant,
    ensure_attendance_token,
)


def _is_manager(user):
    return getattr(user, 'role', '') in {'admin', 'manager'}


def _today_bounds():
    local_now = timezone.localtime()
    start = timezone.make_aware(datetime.combine(local_now.date(), time.min))
    end = timezone.make_aware(datetime.combine(local_now.date(), time.max))
    return start, end, timezone.now()


def _worker_name(worker):
    if not worker or not worker.user:
        return '-'
    return worker.user.full_name or worker.user.username or '-'


def _worker_avatar(worker):
    name = _worker_name(worker)
    parts = [part for part in name.split(' ') if part]
    if len(parts) >= 2:
        return f'{parts[0][0]}{parts[1][0]}'
    return name[:2] or '--'


def _serialize_worker_state(worker, events, now):
    worked_seconds = 0
    open_started_at = None
    last_event = events[-1] if events else None
    for event in events:
        if event.event_type == WorkerAttendance.EventType.IN:
            open_started_at = event.event_at
        elif event.event_type == WorkerAttendance.EventType.OUT and open_started_at:
            worked_seconds += max((event.event_at - open_started_at).total_seconds(), 0)
            open_started_at = None
    if open_started_at:
        worked_seconds += max((now - open_started_at).total_seconds(), 0)

    worked_minutes = int(worked_seconds // 60)
    return {
        'id': worker.id,
        'full_name': _worker_name(worker),
        'avatar': _worker_avatar(worker),
        'phone': worker.user.phone if worker.user else '',
        'role': worker.user.role if worker.user else '',
        'is_available': worker.is_available,
        'load_status': worker.load_status,
        'active_jobs_count': worker.active_jobs_count,
        'attendance_token': ensure_attendance_token(worker),
        'attendance_path': f'/attendance/{ensure_attendance_token(worker)}',
        'current_status': last_event.event_type if last_event else 'out',
        'last_event_type': last_event.event_type if last_event else '',
        'last_event_at': last_event.event_at if last_event else None,
        'today_events_count': len(events),
        'today_check_in_count': len([event for event in events if event.event_type == WorkerAttendance.EventType.IN]),
        'today_check_out_count': len([event for event in events if event.event_type == WorkerAttendance.EventType.OUT]),
        'today_worked_minutes': worked_minutes,
        'today_worked_hours': round(worked_minutes / 60, 2),
        'open_shift_started_at': open_started_at,
    }


def _worker_queue_states(workers, tenant):
    worker_ids = [worker.id for worker in workers if worker.id]
    states = {
        worker.id: {
            'current_status': WorkerAttendance.EventType.OUT,
            'last_event_type': '',
            'last_event_at': None,
            'open_shift_started_at': None,
            'queue_position_at': None,
        }
        for worker in workers
    }
    if not worker_ids:
        return states

    start, end, _now = _today_bounds()
    events = (
        WorkerAttendance.objects
        .filter(tenant=tenant, worker_id__in=worker_ids, event_at__gte=start, event_at__lte=end)
        .order_by('worker_id', 'event_at', 'id')
    )
    for event in events:
        state = states.setdefault(event.worker_id, {})
        state['current_status'] = event.event_type
        state['last_event_type'] = event.event_type
        state['last_event_at'] = event.event_at
        if event.event_type == WorkerAttendance.EventType.IN:
            state['open_shift_started_at'] = event.event_at
        elif event.event_type == WorkerAttendance.EventType.OUT:
            state['open_shift_started_at'] = None

    for worker in workers:
        state = states.setdefault(worker.id, {})
        open_shift_started_at = state.get('open_shift_started_at')
        if state.get('current_status') == WorkerAttendance.EventType.IN and open_shift_started_at:
            last_assigned_at = worker.last_assigned_at
            state['queue_position_at'] = (
                last_assigned_at
                if last_assigned_at and last_assigned_at > open_shift_started_at
                else open_shift_started_at
            )
        else:
            state['queue_position_at'] = None
    return states


def _queue_sort_key(worker):
    state = getattr(worker, '_attendance_queue_state', {}) or {}
    is_present = state.get('current_status') == WorkerAttendance.EventType.IN
    queue_position_at = state.get('queue_position_at')
    name = _worker_name(worker)
    return (
        0 if is_present else 1,
        0 if worker.is_available is not False else 1,
        queue_position_at.timestamp() if queue_position_at else float('inf'),
        name,
        worker.id or 0,
    )


def _create_attendance_event(worker, event_type, source='manager', note='', request=None):
    last_event = worker.attendance_events.order_by('-event_at', '-id').first()
    if last_event and last_event.event_type == event_type:
        raise ValueError('این وضعیت قبلاً ثبت شده است.')
    return WorkerAttendance.objects.create(
        worker=worker,
        tenant=worker.tenant,
        event_type=event_type,
        event_at=timezone.now(),
        source=source,
        note=note,
        ip_address=_client_ip(request) if request else None,
        device_info=_device_info(request) if request else '',
    )


def _attendance_limit_message():
    return f'ورود و خروج تا {ATTENDANCE_FREE_WORKERS_LIMIT} نیرو رایگان است. برای نیروهای بیشتر باید آپشن ورود و خروج را از کیف پول خریداری کنید.'


def _attendance_access_context(tenant):
    allowed_ids = free_attendance_worker_ids(tenant)
    has_purchase = tenant.has_feature('attendance') if tenant else False
    return {
        'has_purchase': has_purchase,
        'worker_count': tenant_worker_count(tenant),
        'allowed_ids': allowed_ids,
    }


def _attendance_worker_denied_response():
    return Response(
        {
            'detail': _attendance_limit_message(),
            'code': 'attendance_worker_limit_reached',
        },
        status=status.HTTP_403_FORBIDDEN,
    )


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _device_info(request):
    return str(request.META.get('HTTP_USER_AGENT', '') or '')[:255]


class WorkerProfileListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return WorkerProfileCreateUpdateSerializer
        return WorkerProfileListSerializer

    def get_queryset(self):
        tenant = _resolve_request_tenant(self.request)
        return WorkerProfile.objects.select_related('user').filter(tenant=tenant, is_deleted=False, user__is_deleted=False).order_by(
            'user__full_name',
            'user__username',
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        workers = list(queryset)
        states = _worker_queue_states(workers, _resolve_request_tenant(request))
        for worker in workers:
            worker._attendance_queue_state = states.get(worker.id, {})
        workers.sort(key=_queue_sort_key)

        page = self.paginate_queryset(workers)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(workers, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        credentials = getattr(serializer, 'created_credentials', None) or {}
        if credentials:
            send_user_credentials_sms(
                tenant=credentials.get('tenant') or instance.tenant,
                tenant_name=getattr(credentials.get('tenant') or instance.tenant, 'name', ''),
                phone=credentials.get('phone') or getattr(instance.user, 'phone', ''),
                username=credentials.get('username') or getattr(instance.user, 'username', ''),
                password=credentials.get('password') or '',
                role=credentials.get('role') or getattr(instance.user, 'role', ''),
                created_by=request.user,
                template_code='worker_credentials',
            )
        output = WorkerProfileListSerializer(instance, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)


class WorkerProfileRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    def get_queryset(self):
        tenant = _resolve_request_tenant(self.request)
        return WorkerProfile.objects.select_related('user').filter(tenant=tenant, is_deleted=False, user__is_deleted=False).order_by(
            F('last_assigned_at').asc(nulls_first=True),
            'user__full_name',
            'user__username',
        )

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return WorkerProfileCreateUpdateSerializer
        return WorkerProfileListSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()
        output = WorkerProfileListSerializer(updated_instance, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        user = instance.user
        instance.is_available = False
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.deleted_by = self.request.user if getattr(self.request.user, 'is_authenticated', False) else None
        instance.save(update_fields=['is_available', 'is_deleted', 'deleted_at', 'deleted_by', 'updated_at'])
        if user:
            user.is_active = False
            user.is_deleted = True
            user.deleted_at = timezone.now()
            user.deleted_by = self.request.user if getattr(self.request.user, 'is_authenticated', False) else None
            user.save(update_fields=['is_active', 'is_deleted', 'deleted_at', 'deleted_by'])


class AttendanceDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not _is_manager(request.user):
            return Response({'detail': 'دسترسی مجاز نیست.'}, status=status.HTTP_403_FORBIDDEN)

        tenant = _resolve_request_tenant(request)
        attendance_access = _attendance_access_context(tenant)

        start, end, now = _today_bounds()
        workers = list(
            WorkerProfile.objects.select_related('user')
            .filter(tenant=tenant, is_deleted=False, user__is_deleted=False)
            .order_by('user__full_name', 'user__username')
        )
        events = list(
            WorkerAttendance.objects.select_related('worker', 'worker__user')
            .filter(tenant=tenant, event_at__gte=start, event_at__lte=end)
            .order_by('event_at', 'id')
        )

        worker_events = {worker.id: [] for worker in workers}
        for event in events:
            worker_events.setdefault(event.worker_id, []).append(event)

        worker_cards = []
        for worker in workers:
            card = _serialize_worker_state(worker, worker_events.get(worker.id, []), now)
            card['attendance_enabled'] = worker_has_attendance_access(
                worker,
                purchased=attendance_access['has_purchase'],
                allowed_ids=attendance_access['allowed_ids'],
            )
            card['attendance_locked_reason'] = '' if card['attendance_enabled'] else _attendance_limit_message()
            worker_cards.append(card)

        present_count = len([item for item in worker_cards if item['current_status'] == WorkerAttendance.EventType.IN])
        total_minutes = sum(item['today_worked_minutes'] for item in worker_cards)

        trend = []
        for offset in range(6, -1, -1):
            day = timezone.localdate() - timedelta(days=offset)
            day_start = timezone.make_aware(datetime.combine(day, time.min))
            day_end = timezone.make_aware(datetime.combine(day, time.max))
            trend.append({
                'date': str(day),
                'checkins': WorkerAttendance.objects.filter(
                    tenant=tenant,
                    event_type=WorkerAttendance.EventType.IN,
                    event_at__gte=day_start,
                    event_at__lte=day_end,
                ).count(),
                'checkouts': WorkerAttendance.objects.filter(
                    tenant=tenant,
                    event_type=WorkerAttendance.EventType.OUT,
                    event_at__gte=day_start,
                    event_at__lte=day_end,
                ).count(),
            })

        recent_events = WorkerAttendance.objects.select_related('worker', 'worker__user').filter(tenant=tenant).order_by('-event_at', '-id')[:80]

        return Response({
            'summary': {
                'workers_count': len(worker_cards),
                'attendance_free_workers_limit': ATTENDANCE_FREE_WORKERS_LIMIT,
                'attendance_worker_count': attendance_access['worker_count'],
                'attendance_feature_purchased': attendance_access['has_purchase'],
                'present_count': present_count,
                'absent_count': max(len(worker_cards) - present_count, 0),
                'today_events_count': len(events),
                'today_worked_minutes': total_minutes,
                'today_worked_hours': round(total_minutes / 60, 2),
            },
            'workers': worker_cards,
            'recent_events': WorkerAttendanceEventSerializer(recent_events, many=True).data,
            'trend': trend,
            'generated_at': now,
        })


class AttendanceManagerEventCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not _is_manager(request.user):
            return Response({'detail': 'دسترسی مجاز نیست.'}, status=status.HTTP_403_FORBIDDEN)

        tenant = _resolve_request_tenant(request)
        worker_id = request.data.get('worker_id')
        event_type = str(request.data.get('event_type', '')).strip().lower()
        note = str(request.data.get('note', '')).strip()

        try:
            worker_id = int(worker_id)
        except (TypeError, ValueError):
            return Response({'worker_id': ['پرسنل نامعتبر است.']}, status=status.HTTP_400_BAD_REQUEST)
        if event_type not in {WorkerAttendance.EventType.IN, WorkerAttendance.EventType.OUT}:
            return Response({'event_type': ['نوع رویداد نامعتبر است.']}, status=status.HTTP_400_BAD_REQUEST)

        worker = WorkerProfile.objects.select_related('user').filter(id=worker_id, tenant=tenant).first()
        if not worker:
            return Response({'worker_id': ['پرسنل پیدا نشد.']}, status=status.HTTP_404_NOT_FOUND)
        if not worker_has_attendance_access(worker):
            return _attendance_worker_denied_response()

        try:
            event = _create_attendance_event(worker, event_type, source='manager', note=note, request=request)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'detail': 'رویداد حضور و غیاب ثبت شد.',
            'event': WorkerAttendanceEventSerializer(event).data,
        }, status=status.HTTP_201_CREATED)


class AttendanceTokenRefreshView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not _is_manager(request.user):
            return Response({'detail': 'دسترسی مجاز نیست.'}, status=status.HTTP_403_FORBIDDEN)

        tenant = _resolve_request_tenant(request)
        worker = WorkerProfile.objects.filter(id=pk, tenant=tenant).first()
        if not worker:
            return Response({'detail': 'پرسنل پیدا نشد.'}, status=status.HTTP_404_NOT_FOUND)
        if not worker_has_attendance_access(worker):
            return _attendance_worker_denied_response()

        worker.attendance_token = None
        worker.save(update_fields=['attendance_token', 'updated_at'])
        token = ensure_attendance_token(worker)
        return Response({
            'detail': 'لینک حضور و غیاب بازسازی شد.',
            'attendance_token': token,
            'attendance_path': f'/attendance/{token}',
        })


class AttendancePublicView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = 'attendance_public'

    def get_worker(self, token):
        return WorkerProfile.objects.select_related('user', 'tenant').filter(attendance_token=token).first()

    def get(self, request, token):
        worker = self.get_worker(token)
        if not worker:
            return Response({'detail': 'لینک حضور و غیاب معتبر نیست.'}, status=status.HTTP_404_NOT_FOUND)
        if not worker_has_attendance_access(worker):
            return _attendance_worker_denied_response()

        start, end, now = _today_bounds()
        events = list(
            WorkerAttendance.objects.filter(worker=worker, event_at__gte=start, event_at__lte=end).order_by('event_at', 'id')
        )
        state = _serialize_worker_state(worker, events, now)
        state['attendance_enabled'] = True
        state['attendance_locked_reason'] = ''
        last_event = WorkerAttendance.objects.filter(worker=worker).order_by('-event_at', '-id').first()
        return Response({
            'worker': state,
            'tenant_name': worker.tenant.name if worker.tenant else '',
            'last_event': WorkerAttendanceEventSerializer(last_event).data if last_event else None,
            'today_events': WorkerAttendanceEventSerializer(events[::-1], many=True).data,
            'server_time': now,
        })

    def post(self, request, token):
        worker = self.get_worker(token)
        if not worker:
            return Response({'detail': 'لینک حضور و غیاب معتبر نیست.'}, status=status.HTTP_404_NOT_FOUND)
        if not worker_has_attendance_access(worker):
            return _attendance_worker_denied_response()

        event_type = str(request.data.get('event_type', '')).strip().lower()
        note = str(request.data.get('note', '')).strip()
        if event_type not in {WorkerAttendance.EventType.IN, WorkerAttendance.EventType.OUT}:
            return Response({'event_type': ['نوع رویداد نامعتبر است.']}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = _create_attendance_event(worker, event_type, source='link', note=note, request=request)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'detail': 'ثبت با موفقیت انجام شد.',
            'event': WorkerAttendanceEventSerializer(event).data,
        }, status=status.HTTP_201_CREATED)
