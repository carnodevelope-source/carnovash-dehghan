from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
import uuid
from collections.abc import Iterator
from datetime import timedelta

from django.conf import settings
from django.db import connections, transaction
from django.db.models import Q
from django.http import JsonResponse, StreamingHttpResponse
from django.utils import timezone

from apps.realtime.models import LiveOutbox


logger = logging.getLogger(__name__)

# Keep this short: a tab refresh does not always close the previous stream, and
# the generator only notices the drop on the next write.
HEARTBEAT_SECONDS = 8
MAX_QUEUE_SIZE = 100
RELAY_RETRY_SECONDS = 5
# Every open stream occupies one gunicorn thread until the browser tab closes.
# Refusing extra streams keeps the pool available for ordinary API requests;
# the frontend falls back to its periodic refresh when it is turned away.
# Never allow the configured cap to eat the whole gthread pool — keep a reserve
# so /auth/me/ and vehicle mutations still have a worker when the shop is busy.
def _max_subscribers() -> int:
    configured = int(getattr(settings, 'LIVE_MAX_SUBSCRIBERS', 12) or 12)
    try:
        threads = max(1, int(os.environ.get('GUNICORN_THREADS') or 24))
    except (TypeError, ValueError):
        threads = 24
    reserved = min(8, max(2, threads // 3))
    return max(4, min(configured, threads - reserved))


MAX_SUBSCRIBERS = _max_subscribers()
REDIS_URL = getattr(settings, 'LIVE_REDIS_URL', '')
REDIS_CHANNEL = getattr(settings, 'LIVE_REDIS_CHANNEL', 'carvash:live')


class _Subscriber:
    """Identity is captured at connect time so the stream never touches the DB."""

    __slots__ = ('events', 'is_hq', 'tenant_id', 'user_id')

    def __init__(self, *, is_hq: bool, tenant_id: str, user_id: str) -> None:
        self.events: queue.Queue[dict] = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self.is_hq = is_hq
        self.tenant_id = tenant_id
        self.user_id = user_id

    def accepts(self, event: dict) -> bool:
        data = event.get('data') or {}
        if not data or self.is_hq:
            return True

        tenant_id = data.get('tenant_id')
        if tenant_id is not None:
            return str(tenant_id) == self.tenant_id

        user_id = data.get('user_id')
        if user_id is not None:
            return str(user_id) == self.user_id

        return False


_subscribers: set[_Subscriber] = set()
_subscribers_lock = threading.Lock()


def _encode(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _fan_out(event: dict) -> None:
    with _subscribers_lock:
        subscribers = list(_subscribers)
    for subscriber in subscribers:
        if not subscriber.accepts(event):
            continue
        try:
            subscriber.events.put_nowait(event)
        except queue.Full:
            pass


class _RedisRelay:
    """Carries events between gunicorn worker processes.

    Subscribers live in the memory of whichever process accepted their stream,
    so without a shared channel a tab only ever sees events raised by that one
    process — roughly a third of them with the default worker count.
    """

    def __init__(self, url: str, channel: str) -> None:
        self._url = url
        self._channel = channel
        self._lock = threading.Lock()
        self._publisher = None
        self._listener: threading.Thread | None = None

    def _connect(self):
        import redis

        return redis.Redis.from_url(
            self._url,
            decode_responses=True,
            socket_keepalive=True,
            health_check_interval=30,
            socket_connect_timeout=getattr(settings, 'LIVE_REDIS_CONNECT_TIMEOUT_SECONDS', 2.0),
            socket_timeout=getattr(settings, 'LIVE_REDIS_SOCKET_TIMEOUT_SECONDS', 2.0),
        )

    def publish(self, event: dict) -> bool:
        with self._lock:
            if self._publisher is None:
                try:
                    self._publisher = self._connect()
                except Exception:
                    logger.exception('live: could not create redis publisher')
                    return False
            publisher = self._publisher
        try:
            publisher.publish(self._channel, _encode(event))
            return True
        except Exception:
            logger.warning('live: redis publish failed, delivering locally', exc_info=True)
            with self._lock:
                self._publisher = None
            return False

    def ensure_listening(self) -> None:
        with self._lock:
            if self._listener is not None and self._listener.is_alive():
                return
            self._listener = threading.Thread(
                target=self._listen,
                name='live-redis-relay',
                daemon=True,
            )
            self._listener.start()

    def _listen(self) -> None:
        retry_seconds = RELAY_RETRY_SECONDS
        while True:
            try:
                # ``listen()`` blocks in a socket read forever.  With the
                # deliberately finite Redis socket timeout, a quiet channel
                # then looks like a failed connection every few seconds and
                # creates noisy reconnect loops.  Polling below keeps idle
                # channels idle while real disconnects still enter recovery.
                with self._connect().pubsub(ignore_subscribe_messages=True) as pubsub:
                    pubsub.subscribe(self._channel)
                    retry_seconds = RELAY_RETRY_SECONDS
                    while True:
                        message = pubsub.get_message(timeout=1.0)
                        if not message or message.get('type') != 'message':
                            continue
                        try:
                            event = json.loads(message['data'])
                        except (TypeError, ValueError):
                            continue
                        _fan_out(event)
            except Exception:
                logger.warning('live: redis relay dropped, reconnecting', exc_info=True)
                time.sleep(retry_seconds)
                retry_seconds = min(retry_seconds * 2, 60)


_relay = _RedisRelay(REDIS_URL, REDIS_CHANNEL) if REDIS_URL else None


def _deliver(event: dict) -> None:
    # A successful publish comes back through this process's own relay thread,
    # so fanning out locally as well would duplicate the event.
    if _relay is not None and _relay.publish(event):
        return
    _fan_out(event)


def publish_live_event(event_type: str, data: dict | None = None) -> None:
    data = data or {}
    if getattr(settings, 'LIVE_OUTBOX_ENABLED', False):
        if not transaction.get_connection().in_atomic_block:
            raise RuntimeError(
                'LiveOutbox producers must call publish_live_event inside transaction.atomic().'
            )
        # Producer models open the transaction before Django emits their
        # signals. The outbox row rolls back with the business write, while
        # low-latency Redis publishing stays strictly after commit.
        outbox = LiveOutbox.objects.create(
            tenant_id=data.get('tenant_id'),
            actor_user_id=data.get('actor_user_id') or data.get('user_id'),
            event_type=event_type,
            entity_type=event_type.split('.', 1)[0],
            entity_id=str(data.get('entity_id') or data.get('vehicle_id') or data.get('id') or ''),
            payload=data,
        )
        event = _outbox_event(outbox)
    else:
        # Compatibility path used until the V2 flags have passed staging.
        event = {
            "id": uuid.uuid4().hex,
            "event_id": None,
            "type": event_type,
            "event_type": event_type,
            "data": data,
            "payload": data,
            "created_at": timezone.now().isoformat(),
        }
    # Signals fire mid-transaction; delivering only after commit stops clients
    # from refetching state that a rollback is about to discard.
    transaction.on_commit(lambda: _deliver(event))


def _outbox_event(outbox: LiveOutbox) -> dict:
    """Return a backwards-compatible event envelope with a durable cursor."""
    action = outbox.event_type.rsplit('.', 1)[-1]
    return {
        'id': str(outbox.id),
        'event_id': str(outbox.id),
        'type': outbox.event_type,
        'event_type': outbox.event_type,
        'entity': outbox.entity_type,
        'entity_id': outbox.entity_id,
        'action': action,
        'tenant_id': str(outbox.tenant_id) if outbox.tenant_id is not None else None,
        'actor_user_id': str(outbox.actor_user_id) if outbox.actor_user_id is not None else None,
        'version': outbox.created_at.isoformat(),
        'occurred_at': outbox.created_at.isoformat(),
        # Existing Vue consumers use type/data; these aliases keep the wire
        # contract stable while V2 consumers use the standard fields above.
        'data': outbox.payload,
        'payload': outbox.payload,
        'created_at': outbox.created_at.isoformat(),
    }


def _at_capacity() -> bool:
    with _subscribers_lock:
        return len(_subscribers) >= MAX_SUBSCRIBERS


def _subscribe(subscriber: _Subscriber) -> bool:
    with _subscribers_lock:
        if len(_subscribers) >= MAX_SUBSCRIBERS:
            return False
        _subscribers.add(subscriber)
    return True


def _unsubscribe(subscriber: _Subscriber) -> None:
    with _subscribers_lock:
        _subscribers.discard(subscriber)


def _is_hq_user(user) -> bool:
    platform_role = getattr(user, 'platform_role', '') or ''
    return bool(
        getattr(user, 'is_superuser', False)
        or platform_role.startswith('hq_')
    )


def _scoped_outbox(subscriber: _Subscriber):
    queryset = LiveOutbox.objects.order_by('id')
    if subscriber.is_hq:
        return queryset
    if not subscriber.tenant_id.isdigit():
        return queryset.filter(tenant_id__isnull=True)
    return queryset.filter(Q(tenant_id=subscriber.tenant_id) | Q(tenant_id__isnull=True))


def _parse_cursor(value: str | None) -> int | None:
    if value in (None, ''):
        return 0
    try:
        parsed = int(value)
        return parsed if parsed >= 0 else None
    except (TypeError, ValueError):
        return None


def _full_resync_event(reason: str = 'retention_or_replay_limit') -> dict:
    return {
        'id': '',
        'event_id': '',
        'type': 'system.full_resync_required',
        'event_type': 'system.full_resync_required',
        'data': {'reason': reason},
        'payload': {'reason': reason},
        'created_at': timezone.now().isoformat(),
    }


def _replay_limits() -> tuple[int, int, timedelta]:
    """Return bounded replay limits even if an environment value is malformed."""
    batch_size = max(1, min(int(getattr(settings, 'LIVE_REPLAY_BATCH_SIZE', 100)), 1000))
    max_events = max(batch_size, min(int(getattr(settings, 'LIVE_REPLAY_MAX_EVENTS', 1000)), 10000))
    max_age_hours = max(1, int(getattr(settings, 'LIVE_REPLAY_MAX_AGE_HOURS', 72)))
    return batch_size, max_events, timedelta(hours=max_age_hours)


def _replay_snapshot(subscriber: _Subscriber, after_id: int | None):
    """Validate a cursor and capture a finite, tenant-scoped replay snapshot.

    The subscriber is already registered before this function is called. Its
    queue therefore captures events committed while this snapshot is emitted;
    the returned high-watermark removes duplicate queued events afterwards.
    """
    if after_id is None:
        return None, 0, 'invalid_cursor'

    queryset = _scoped_outbox(subscriber)
    high_watermark = queryset.order_by('-id').values_list('id', flat=True).first() or 0
    if after_id > high_watermark:
        return None, high_watermark, 'future_cursor'

    _batch_size, max_events, max_age = _replay_limits()
    cutoff = timezone.now() - max_age
    if after_id:
        cursor_row = queryset.filter(id=after_id).only('created_at').first()
        if cursor_row is not None and cursor_row.created_at < cutoff:
            return None, high_watermark, 'cursor_too_old'
        oldest = queryset.filter(created_at__gte=cutoff).order_by('id').values_list('id', flat=True).first()
        # A cursor preceding the retained scope may refer to pruned events. A
        # conservative full sync is safer than pretending the gap is harmless.
        if oldest is not None and after_id < oldest - 1:
            return None, high_watermark, 'cursor_outside_retention'

    # Probe at most max+1 IDs. This distinguishes a safe finite replay from a
    # backlog that must be reconciled from authoritative API state.
    probe = list(queryset.filter(id__gt=after_id, id__lte=high_watermark).values_list('id', flat=True)[:max_events + 1])
    if len(probe) > max_events:
        return None, high_watermark, 'replay_limit_exceeded'
    return queryset, high_watermark, None


def _iter_replay_rows(queryset, after_id: int, high_watermark: int) -> Iterator[LiveOutbox]:
    batch_size, _max_events, _max_age = _replay_limits()
    cursor = after_id
    while cursor < high_watermark:
        rows = list(queryset.filter(id__gt=cursor, id__lte=high_watermark)[:batch_size])
        if not rows:
            return
        for row in rows:
            yield row
        cursor = rows[-1].id


def _event_stream(subscriber: _Subscriber, after_id: int | None = 0, *, skip_replay: bool = False) -> Iterator[str]:
    # The stream outlives the request by hours, so give the database connection
    # back instead of parking it for the whole session.
    connections.close_all()
    if _relay is not None:
        _relay.ensure_listening()
    # Registering here rather than in the view means a client that disconnects
    # before the body is consumed never leaves a phantom subscriber behind.
    if not _subscribe(subscriber):
        return
    try:
        yield "retry: 5000\n\n"
        yield f"data: {_encode({'type': 'live.connected', 'data': {}})}\n\n"
        replayed_ids: set[str] = set()
        high_watermark = 0
        if (
            not skip_replay
            and getattr(settings, 'LIVE_V2_ENABLED', False)
            and getattr(settings, 'LIVE_REPLAY_ENABLED', False)
            and getattr(settings, 'LIVE_OUTBOX_ENABLED', False)
        ):
            # The subscriber is registered before the snapshot. Events
            # arriving during replay land in its bounded queue; ids in the
            # snapshot are removed below so the client sees each event once.
            queryset, high_watermark, reason = _replay_snapshot(subscriber, after_id)
            if reason:
                yield f"data: {_encode(_full_resync_event(reason))}\n\n"
            elif queryset is not None:
                for row in _iter_replay_rows(queryset, after_id or 0, high_watermark):
                    event = _outbox_event(row)
                    replayed_ids.add(event['id'])
                    yield f"id: {event['id']}\ndata: {_encode(event)}\n\n"
            connections.close_all()
        while True:
            try:
                event = subscriber.events.get(timeout=HEARTBEAT_SECONDS)
            except queue.Empty:
                yield f": heartbeat {timezone.now().isoformat()}\n\n"
                continue
            event_id = str(event.get('id') or '')
            if event_id in replayed_ids or (high_watermark and event_id.isdigit() and int(event_id) <= high_watermark):
                continue
            prefix = f"id: {event_id}\n" if event_id else ''
            yield f"{prefix}data: {_encode(event)}\n\n"
    except (BrokenPipeError, ConnectionResetError, OSError):
        return
    finally:
        _unsubscribe(subscriber)


def live_events_view(request):
    if request.method != 'GET':
        return JsonResponse({'detail': 'Method not allowed.'}, status=405)
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return JsonResponse({'detail': 'Unauthorized.'}, status=401)

    if _at_capacity():
        return JsonResponse({'detail': 'Live stream capacity reached.'}, status=503)

    subscriber = _Subscriber(
        is_hq=_is_hq_user(user),
        tenant_id=str(getattr(user, 'tenant_id', '') or ''),
        user_id=str(getattr(user, 'id', '') or ''),
    )
    raw_cursor = request.headers.get('Last-Event-ID') or request.GET.get('after')
    # A first connection has no cursor. Replaying the whole retained outbox
    # would stampede the UI; catch-up is only for reconnect/reconcile.
    if raw_cursor in (None, ''):
        stream = _event_stream(subscriber, skip_replay=True)
    else:
        stream = _event_stream(subscriber, _parse_cursor(raw_cursor))
    response = StreamingHttpResponse(stream, content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def _live_replay_enabled() -> bool:
    return bool(
        getattr(settings, 'LIVE_V2_ENABLED', False)
        and getattr(settings, 'LIVE_REPLAY_ENABLED', False)
        and getattr(settings, 'LIVE_OUTBOX_ENABLED', False)
    )


def _authenticated_subscriber(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return None
    return _Subscriber(
        is_hq=_is_hq_user(user),
        tenant_id=str(getattr(user, 'tenant_id', '') or ''),
        user_id=str(getattr(user, 'id', '') or ''),
    )


def live_revision_view(request):
    subscriber = _authenticated_subscriber(request)
    if request.method != 'GET':
        return JsonResponse({'detail': 'Method not allowed.'}, status=405)
    if subscriber is None:
        return JsonResponse({'detail': 'Unauthorized.'}, status=401)
    if not _live_replay_enabled() or not getattr(settings, 'LIVE_REVISION_SAFETY_CHECK', True):
        return JsonResponse({'detail': 'Live replay is disabled.'}, status=404)
    latest_id = _scoped_outbox(subscriber).order_by('-id').values_list('id', flat=True).first() or 0
    return JsonResponse({'latest_event_id': str(latest_id)})


def live_sync_view(request):
    subscriber = _authenticated_subscriber(request)
    if request.method != 'GET':
        return JsonResponse({'detail': 'Method not allowed.'}, status=405)
    if subscriber is None:
        return JsonResponse({'detail': 'Unauthorized.'}, status=401)
    if not _live_replay_enabled():
        return JsonResponse({'detail': 'Live replay is disabled.'}, status=404)
    after_id = _parse_cursor(request.GET.get('after'))
    queryset, high_watermark, reason = _replay_snapshot(subscriber, after_id)
    if reason:
        return JsonResponse({'full_resync_required': True, 'reason': reason, 'events': []})
    rows = list(_iter_replay_rows(queryset, after_id or 0, high_watermark)) if queryset is not None else []
    return JsonResponse({
        'full_resync_required': False,
        'events': [_outbox_event(row) for row in rows],
        'latest_event_id': str(high_watermark),
    })
