from __future__ import annotations

import json
import queue
import threading
import uuid
from collections.abc import Iterator

from django.http import JsonResponse, StreamingHttpResponse
from django.utils import timezone


HEARTBEAT_SECONDS = 25
MAX_QUEUE_SIZE = 100

_subscribers: set[queue.Queue[dict]] = set()
_subscribers_lock = threading.Lock()


def _encode(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def publish_live_event(event_type: str, data: dict | None = None) -> None:
    event = {
        "id": uuid.uuid4().hex,
        "type": event_type,
        "data": data or {},
        "created_at": timezone.now().isoformat(),
    }
    with _subscribers_lock:
        subscribers = list(_subscribers)
    for subscriber in subscribers:
        try:
            subscriber.put_nowait(event)
        except queue.Full:
            pass


def _subscribe() -> queue.Queue[dict]:
    subscriber: queue.Queue[dict] = queue.Queue(maxsize=MAX_QUEUE_SIZE)
    with _subscribers_lock:
        _subscribers.add(subscriber)
    return subscriber


def _unsubscribe(subscriber: queue.Queue[dict]) -> None:
    with _subscribers_lock:
        _subscribers.discard(subscriber)


def _is_hq_user(user) -> bool:
    platform_role = getattr(user, 'platform_role', '') or ''
    return bool(
        getattr(user, 'is_superuser', False)
        or platform_role.startswith('hq_')
    )


def _can_receive_event(user, event: dict) -> bool:
    data = event.get('data') or {}
    if not data:
        return True
    if _is_hq_user(user):
        return True

    tenant_id = data.get('tenant_id')
    if tenant_id is not None:
        return str(tenant_id) == str(getattr(user, 'tenant_id', '') or '')

    user_id = data.get('user_id')
    if user_id is not None:
        return str(user_id) == str(getattr(user, 'id', '') or '')

    return False


def _event_stream(user) -> Iterator[str]:
    subscriber = _subscribe()
    try:
        yield "retry: 5000\n\n"
        yield f"data: {_encode({'type': 'live.connected', 'data': {}})}\n\n"
        while True:
            try:
                event = subscriber.get(timeout=HEARTBEAT_SECONDS)
            except queue.Empty:
                yield f": heartbeat {timezone.now().isoformat()}\n\n"
                continue
            if not _can_receive_event(user, event):
                continue
            yield f"id: {event['id']}\ndata: {_encode(event)}\n\n"
    finally:
        _unsubscribe(subscriber)


def live_events_view(request):
    if request.method != 'GET':
        return JsonResponse({'detail': 'Method not allowed.'}, status=405)
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return JsonResponse({'detail': 'Unauthorized.'}, status=401)

    response = StreamingHttpResponse(_event_stream(request.user), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
