from django.http import JsonResponse


LICENSE_EXEMPT_PREFIXES = (
    '/api/auth/csrf/',
    '/api/auth/login/',
    '/api/auth/logout/',
    '/api/auth/me/',
    '/api/auth/support/',
    '/api/auth/hq/',
    '/api/payments/wallet/',
    '/api/notifications/sms/simple/',
    '/api/workers/attendance/public/',
)


class TenantLicenseLockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._should_block(request):
            return JsonResponse(
                {
                    'detail': 'دسترسی نرم‌افزار قفل است. برای ادامه، پرداخت نرم‌افزار یا سررسید را از کیف پول تکمیل کنید.',
                    'code': 'tenant_license_locked',
                },
                status=402,
            )
        return self.get_response(request)

    def _should_block(self, request):
        path = request.path or ''
        if not path.startswith('/api/'):
            return False
        if any(path.startswith(prefix) for prefix in LICENSE_EXEMPT_PREFIXES):
            return False
        user = getattr(request, 'user', None)
        if not getattr(user, 'is_authenticated', False):
            return False
        if getattr(user, 'platform_role', '') in {'hq_admin', 'hq_support'}:
            return False
        tenant = getattr(user, 'tenant', None)
        if tenant is None:
            return False
        from apps.payments.views import license_status_for_tenant
        return bool(license_status_for_tenant(tenant).get('is_locked'))
