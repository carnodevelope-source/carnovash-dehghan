from django.http import JsonResponse


LICENSE_EXEMPT_PREFIXES = (
    '/api/auth/csrf/',
    '/api/auth/login/',
    '/api/auth/logout/',
    '/api/auth/me/',
    '/api/auth/support/',
    '/api/auth/hq/',
    '/api/payments/wallet/',
    '/api/workers/attendance/public/',
)

FEATURE_LOCK_PREFIXES = {
    'sms_club': (
        '/api/notifications/',
    ),
    'attendance': (
        '/api/workers/attendance/',
    ),
}


class TenantLicenseLockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        block_reason = self._block_reason(request)
        if block_reason:
            return JsonResponse(
                {
                    'detail': block_reason['detail'],
                    'code': block_reason['code'],
                    'feature_key': block_reason.get('feature_key', ''),
                },
                status=402,
            )
        return self.get_response(request)

    def _block_reason(self, request):
        path = request.path or ''
        if not path.startswith('/api/'):
            return None
        if any(path.startswith(prefix) for prefix in LICENSE_EXEMPT_PREFIXES):
            return None
        user = getattr(request, 'user', None)
        if not getattr(user, 'is_authenticated', False):
            return None
        if getattr(user, 'platform_role', '') in {
            'hq_admin',
            'hq_support',
            'hq_project_manager',
            'hq_finance',
        }:
            return None
        if getattr(user, 'tenant_id', None) is None:
            return None
        tenant = user.tenant
        from apps.payments.views import license_status_for_tenant, locked_feature_statuses_for_tenant
        license_status = license_status_for_tenant(tenant)
        if license_status.get('is_locked'):
            return {
                'detail': 'دسترسی نرم‌افزار قفل است. برای ادامه، پرداخت نرم‌افزار یا سررسید را از کیف پول تکمیل کنید.',
                'code': 'tenant_license_locked',
                'feature_key': 'core_software',
            }

        # Only the handful of paths below can be feature-locked, so skip the
        # installment lookup entirely for every other API request.
        candidate_features = [
            feature_key
            for feature_key, prefixes in FEATURE_LOCK_PREFIXES.items()
            if any(path.startswith(prefix) for prefix in prefixes)
        ]
        if not candidate_features:
            return None

        locked_features = locked_feature_statuses_for_tenant(tenant)
        for feature_key in candidate_features:
            if feature_key in locked_features:
                return {
                    'detail': 'دسترسی این بخش به دلیل پرداخت نشدن قسط قفل است. برای ادامه، قسط را از کیف پول پرداخت کنید.',
                    'code': 'tenant_feature_locked',
                    'feature_key': feature_key,
                }
        return None
