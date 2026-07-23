from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsHqAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (
            getattr(user, 'is_hq_admin', False) or getattr(user, 'platform_role', '') == 'hq_admin'
        ))


class IsHqUser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'is_hq_admin', False) or getattr(user, 'platform_role', '') == 'hq_admin':
            return True
        if getattr(user, 'is_hq', False) or getattr(user, 'platform_role', '') == 'hq_support':
            return request.method in SAFE_METHODS or getattr(view, 'allow_hq_support_write', False)
        return False


class IsTenantManagerLike(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, 'tenant_id', None)
            and user.role in {'admin', 'owner', 'manager', 'accountant', 'operator'}
        )
