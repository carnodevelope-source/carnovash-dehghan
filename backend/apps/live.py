from __future__ import annotations

import json
import logging
import queue
import threading
import time
import uuid
from collections.abc import Iterator

from django.conf import settings
from django.db import connections, transaction
from django.http import JsonResponse, StreamingHttpResponse
from django.utils import timezone


logger = logging.getLogger(__name__)

# Keep this short: a tab refresh does not always close the previous stream, and
# the generator only notices the drop on the next write.
HEARTBEAT_SECONDS = 8
MAX_QUEUE_SIZE = 100
RELAY_RETRY_SECONDS = 5
# Every open stream occupies one gunicorn thread until the browser tab closes.
# Refusing extra streams keeps the pool available for ordinary API requests;
# the frontend falls back to its periodic refresh when it is turned away.
MAX_SUBSCRIBERS = getattr(settings, 'LIVE_MAX_SUBSCRIBERS', 40)
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
        while True:
            try:
                pubsub = self._connect().pubsub(ignore_subscribe_messages=True)
                pubsub.subscribe(self._channel)
                for message in pubsub.listen():
                    if message.get('type') != 'message':
                        continue
                    try:
                        event = json.loads(message['data'])
                    except (TypeError, ValueError):
                        continue
                    _fan_out(event)
            except Exception:
                logger.warning('live: redis relay dropped, reconnecting', exc_info=True)
                time.sleep(RELAY_RETRY_SECONDS)


_relay = _RedisRelay(REDIS_URL, REDIS_CHANNEL) if REDIS_URL else None


def _deliver(event: dict) -> None:
    # A successful publish comes back through this process's own relay thread,
    # so fanning out locally as well would duplicate the event.
    if _relay is not None and _relay.publish(event):
        return
    _fan_out(event)


def publish_live_event(event_type: str, data: dict | None = None) -> None:
    event = {
        "id": uuid.uuid4().hex,
        "type": event_type,
        "data": data or {},
        "created_at": timezone.now().isoformat(),
    }
    # Signals fire mid-transaction; delivering only after commit stops clients
    # from refetching state that a rollback is about to discard.
    transaction.on_commit(lambda: _deliver(event))


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


def _event_stream(subscriber: _Subscriber) -> Iterator[str]:
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
        while True:
            try:
                event = subscriber.events.get(timeout=HEARTBEAT_SECONDS)
            except queue.Empty:
                yield f": heartbeat {timezone.now().isoformat()}\n\n"
                continue
            yield f"id: {event['id']}\ndata: {_encode(event)}\n\n"
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
    response = StreamingHttpResponse(_event_stream(subscriber), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
