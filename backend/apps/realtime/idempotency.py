"""Header-driven idempotency with no retry or mutation side effects of its own."""

from __future__ import annotations

import hashlib
import json

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils import timezone

from .models import IdempotencyRecord


UNSAFE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
MAX_KEY_LENGTH = 128


def _json_response(payload, status):
    response = JsonResponse(payload, status=status, safe=not isinstance(payload, list))
    response['Idempotency-Replayed'] = 'true'
    return response


def _request_hash(request):
    digest = hashlib.sha256()
    digest.update(request.method.encode())
    digest.update(b'\0')
    digest.update(request.path.encode())
    digest.update(b'\0')
    digest.update(request.body or b'')
    return digest.hexdigest()


class IdempotencyMiddleware:
    """Replay a completed response and reject concurrent/key-reuse mutations.

    A key is opt-in: legacy callers retain exactly their former behaviour. The
    middleware is deliberately placed after authentication so each cache entry
    is bound to an authenticated user and tenant.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, 'IDEMPOTENCY_ENABLED', True):
            return self.get_response(request)
        if request.method not in UNSAFE_METHODS or not request.path.startswith('/api/'):
            return self.get_response(request)

        key = (request.headers.get('Idempotency-Key') or '').strip()
        user = getattr(request, 'user', None)
        if not key or not getattr(user, 'is_authenticated', False):
            return self.get_response(request)
        if len(key) > MAX_KEY_LENGTH:
            return JsonResponse({'detail': 'Idempotency-Key is too long.'}, status=400)

        tenant_id = getattr(user, 'tenant_id', None) or 0
        request_hash = _request_hash(request)
        record, first_request = self._claim_or_find(
            tenant_id=tenant_id,
            user=user,
            key=key,
            method=request.method,
            path=request.path,
            request_hash=request_hash,
        )
        if not first_request:
            if record.request_hash != request_hash or record.method != request.method or record.path != request.path:
                return JsonResponse({'detail': 'Idempotency-Key was already used with a different request.'}, status=409)
            if record.status_code is None:
                return JsonResponse({'detail': 'An identical request is already in progress.'}, status=409)
            return _json_response(record.response_json, record.status_code)

        try:
            response = self.get_response(request)
            # Django's JsonResponse and DRF Response are rendered before the
            # middleware returns. Only JSON responses are safe to replay.
            if 200 <= response.status_code < 500 and 'application/json' in response.get('Content-Type', ''):
                response.render() if hasattr(response, 'render') else None
                payload = json.loads(response.content.decode('utf-8'))
                record.status_code = response.status_code
                record.response_json = payload
                record.completed_at = timezone.now()
                record.save(update_fields=['status_code', 'response_json', 'completed_at'])
            else:
                record.delete()
            return response
        except Exception:
            record.delete()
            raise

    @staticmethod
    def _claim_or_find(**kwargs):
        try:
            with transaction.atomic():
                return IdempotencyRecord.objects.create(**kwargs), True
        except IntegrityError:
            return IdempotencyRecord.objects.get(
                tenant_id=kwargs['tenant_id'], user=kwargs['user'], key=kwargs['key']
            ), False
