from django.contrib.auth import get_user_model

from apps.auth.models import CarWash, CarWashFeaturePurchase


PRODUCTION_CARWASHES = [
    {
        "name": "کارواش یک",
        "slug": "carwash-1",
        "address": "تهران",
        "manager": {
            "username": "manager1",
            "password": "manager1@!23",
            "full_name": "Manager One",
            "phone": "09120001001",
        },
        "features": list(CarWashFeaturePurchase.FeatureKey.values),
    },
    {
        "name": "کارواش دو",
        "slug": "carwash-2",
        "address": "تهران",
        "manager": {
            "username": "manager2",
            "password": "manager2@123",
            "full_name": "Manager Two",
            "phone": "09120001002",
        },
        "features": list(CarWashFeaturePurchase.FeatureKey.values),
    },
]


HQ_ADMIN = {
    "username": "miladdhs",
    "password": "m11223344M!@",
    "full_name": "Milad Dehestani",
    "phone": "09120001090",
    "role": "admin",
    "platform_role": "hq_admin",
    "is_staff": True,
    "is_superuser": True,
}


def _sync_feature_flags(tenant, feature_keys):
    normalized_keys = {str(item).strip() for item in (feature_keys or []) if str(item).strip()}
    for feature_key in CarWashFeaturePurchase.FeatureKey.values:
        purchase, _created = CarWashFeaturePurchase.objects.get_or_create(
            tenant=tenant,
            feature_key=feature_key,
            defaults={"is_active": feature_key in normalized_keys},
        )
        should_be_active = feature_key in normalized_keys
        changed_fields = []
        if purchase.is_active != should_be_active:
            purchase.is_active = should_be_active
            changed_fields.append("is_active")
        if changed_fields:
            changed_fields.append("updated_at")
            purchase.save(update_fields=changed_fields)


def _upsert_user(user_defaults, tenant=None):
    user_model = get_user_model()
    username = user_defaults["username"]
    password = user_defaults["password"]
    defaults = {
        "full_name": user_defaults.get("full_name", ""),
        "phone": user_defaults["phone"],
        "tenant": tenant,
        "role": user_defaults.get("role", "manager"),
        "platform_role": user_defaults.get("platform_role", ""),
        "is_staff": user_defaults.get("is_staff", False),
        "is_superuser": user_defaults.get("is_superuser", False),
        "is_active": True,
    }

    user, _created = user_model.objects.get_or_create(username=username, defaults=defaults)
    changed_fields = []
    for key, value in defaults.items():
        if getattr(user, key) != value:
            setattr(user, key, value)
            changed_fields.append(key)
    if changed_fields:
        user.save(update_fields=changed_fields)

    user.set_password(password)
    user.save(update_fields=["password"])
    return user


def seed_production_data():
    for item in PRODUCTION_CARWASHES:
        tenant, _created = CarWash.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "name": item["name"],
                "address": item.get("address", ""),
                "is_active": True,
            },
        )
        changed_fields = []
        if tenant.name != item["name"]:
            tenant.name = item["name"]
            changed_fields.append("name")
        if tenant.address != item.get("address", ""):
            tenant.address = item.get("address", "")
            changed_fields.append("address")
        if not tenant.is_active:
            tenant.is_active = True
            changed_fields.append("is_active")
        if changed_fields:
            changed_fields.append("updated_at")
            tenant.save(update_fields=changed_fields)

        _upsert_user(
            {
                **item["manager"],
                "role": "manager",
                "platform_role": "",
                "is_staff": True,
                "is_superuser": False,
            },
            tenant=tenant,
        )
        _sync_feature_flags(tenant, item.get("features", []))

    _upsert_user(HQ_ADMIN, tenant=None)
