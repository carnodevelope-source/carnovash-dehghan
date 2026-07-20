from apps.workers.models import WorkerProfile

from .models import CarWashFeaturePurchase


ATTENDANCE_FREE_WORKERS_LIMIT = 5


def feature_access_map_for_tenant(tenant):
    feature_keys = set(tenant.active_feature_keys()) if tenant else set()
    locked_features = set()
    if tenant:
        from apps.payments.views import locked_feature_statuses_for_tenant
        locked_features = set(locked_feature_statuses_for_tenant(tenant).keys())
    access_map = {
        key: key in feature_keys and key not in locked_features
        for key in CarWashFeaturePurchase.FeatureKey.values
    }
    access_map[CarWashFeaturePurchase.FeatureKey.ATTENDANCE] = (
        bool(tenant)
        and CarWashFeaturePurchase.FeatureKey.ATTENDANCE not in locked_features
    )
    return access_map


def tenant_has_attendance_access(tenant, feature_keys=None):
    if not tenant:
        return False
    from apps.payments.views import locked_feature_statuses_for_tenant
    if CarWashFeaturePurchase.FeatureKey.ATTENDANCE in locked_feature_statuses_for_tenant(tenant):
        return False
    active_keys = set(feature_keys) if feature_keys is not None else set(tenant.active_feature_keys())
    if CarWashFeaturePurchase.FeatureKey.ATTENDANCE in active_keys:
        return True
    return tenant_worker_count(tenant) <= ATTENDANCE_FREE_WORKERS_LIMIT


def tenant_worker_count(tenant):
    if not tenant:
        return 0
    return WorkerProfile.objects.filter(
        tenant=tenant,
        is_available=True,
        is_deleted=False,
        user__is_active=True,
        user__is_deleted=False,
    ).count()


def free_attendance_worker_ids(tenant):
    if not tenant:
        return set()
    return set(
        WorkerProfile.objects.filter(
            tenant=tenant,
            is_available=True,
            is_deleted=False,
            user__is_active=True,
            user__is_deleted=False,
        )
        .order_by('created_at', 'id')
        .values_list('id', flat=True)[:ATTENDANCE_FREE_WORKERS_LIMIT]
    )


def worker_has_attendance_access(worker, purchased=None, allowed_ids=None):
    tenant = getattr(worker, 'tenant', None)
    if not tenant:
        return False
    if getattr(worker, 'is_available', False) is not True:
        return False
    user = getattr(worker, 'user', None)
    if getattr(worker, 'is_deleted', False) or getattr(user, 'is_active', False) is not True or getattr(user, 'is_deleted', False):
        return False
    from apps.payments.views import locked_feature_statuses_for_tenant
    if CarWashFeaturePurchase.FeatureKey.ATTENDANCE in locked_feature_statuses_for_tenant(tenant):
        return False
    has_purchase = tenant.has_feature(CarWashFeaturePurchase.FeatureKey.ATTENDANCE) if purchased is None else purchased
    if has_purchase:
        return True
    available_ids = free_attendance_worker_ids(tenant) if allowed_ids is None else allowed_ids
    return worker.id in available_ids
