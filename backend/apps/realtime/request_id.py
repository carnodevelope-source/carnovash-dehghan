import re
import uuid


_SAFE_REQUEST_ID = re.compile(r'^[A-Za-z0-9._-]{8,128}$')


class RequestIdMiddleware:
    """Attach a non-sensitive correlation ID without logging request bodies."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = (request.headers.get('X-Request-ID') or '').strip()
        request.request_id = supplied if _SAFE_REQUEST_ID.match(supplied) else uuid.uuid4().hex
        response = self.get_response(request)
        response['X-Request-ID'] = request.request_id
        return response
