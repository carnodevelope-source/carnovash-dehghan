from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.auth.models import CarWash, CarWashFeaturePurchase
from apps.inventory.models import InventoryItem
from apps.products.models import Product, ProductCategory
from apps.services.models import GeneralSettings, Service, ServiceCategory


PRODUCTION_CARWASHES = []


HQ_ADMIN = {
    "username": "milad_dhs",
    "password": "m11051386M!@",
    "full_name": "Milad Dehestani",
    "phone": "09120001090",
    "role": "admin",
    "platform_role": "hq_admin",
    "is_staff": True,
    "is_superuser": True,
}


DEFAULT_SERVICE_CATEGORIES = [
    {"name": "شستشو", "slug": "wash", "display_order": 1},
    {"name": "دیتیلینگ", "slug": "detailing", "display_order": 2},
]


DEFAULT_SERVICES = [
    {
        "name": "شستشوی بدنه",
        "code": "BODY-WASH",
        "category_slug": "wash",
        "base_price": Decimal("350000"),
        "estimated_duration_minutes": 25,
        "display_order": 1,
    },
    {
        "name": "شستشوی کامل",
        "code": "FULL-WASH",
        "category_slug": "wash",
        "base_price": Decimal("650000"),
        "estimated_duration_minutes": 45,
        "display_order": 2,
    },
    {
        "name": "صفرشویی داخل کابین",
        "code": "CABIN-DETAIL",
        "category_slug": "detailing",
        "base_price": Decimal("1800000"),
        "estimated_duration_minutes": 120,
        "display_order": 3,
    },
]


DEFAULT_PRODUCT_CATEGORIES = [
    {"name": "شوینده‌ها", "slug": "detergents", "display_order": 1},
    {"name": "لوازم مصرفی", "slug": "consumables", "display_order": 2},
]


DEFAULT_PRODUCTS = [
    {
        "name": "شامپو بدنه خودرو",
        "sku": "SH-001",
        "unit": "عدد",
        "sale_price": Decimal("180000"),
        "cost_price": Decimal("130000"),
        "min_stock": 5,
        "category_slug": "detergents",
        "stock_qty": Decimal("40"),
    },
    {
        "name": "واکس داشبورد",
        "sku": "WX-002",
        "unit": "عدد",
        "sale_price": Decimal("250000"),
        "cost_price": Decimal("190000"),
        "min_stock": 5,
        "category_slug": "detergents",
        "stock_qty": Decimal("30"),
    },
    {
        "name": "دستمال مایکروفایبر",
        "sku": "MF-003",
        "unit": "عدد",
        "sale_price": Decimal("70000"),
        "cost_price": Decimal("45000"),
        "min_stock": 20,
        "category_slug": "consumables",
        "stock_qty": Decimal("120"),
    },
]


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


def _tenant_key(tenant, value):
    return f"{tenant.slug}-{value}"


def _seed_services(tenant, created_by):
    category_by_slug = {}
    for item in DEFAULT_SERVICE_CATEGORIES:
        category, _created = ServiceCategory.objects.update_or_create(
            slug=_tenant_key(tenant, item["slug"]),
            defaults={
                "tenant": tenant,
                "name": item["name"],
                "display_order": item["display_order"],
                "is_active": True,
                "created_by": created_by,
            },
        )
        category_by_slug[item["slug"]] = category

    for item in DEFAULT_SERVICES:
        Service.objects.update_or_create(
            code=_tenant_key(tenant, item["code"]),
            defaults={
                "tenant": tenant,
                "category": category_by_slug[item["category_slug"]],
                "name": item["name"],
                "base_price": item["base_price"],
                "estimated_duration_minutes": item["estimated_duration_minutes"],
                "display_order": item["display_order"],
                "allow_price_override": True,
                "is_active": True,
                "created_by": created_by,
            },
        )

    GeneralSettings.objects.get_or_create(tenant=tenant)


def _seed_products(tenant, created_by):
    category_by_slug = {}
    for item in DEFAULT_PRODUCT_CATEGORIES:
        category, _created = ProductCategory.objects.update_or_create(
            slug=_tenant_key(tenant, item["slug"]),
            defaults={
                "tenant": tenant,
                "name": item["name"],
                "display_order": item["display_order"],
                "is_active": True,
            },
        )
        category_by_slug[item["slug"]] = category

    for item in DEFAULT_PRODUCTS:
        product, _created = Product.objects.update_or_create(
            sku=_tenant_key(tenant, item["sku"]),
            defaults={
                "tenant": tenant,
                "category": category_by_slug[item["category_slug"]],
                "name": item["name"],
                "unit": item["unit"],
                "sale_price": item["sale_price"],
                "cost_price": item["cost_price"],
                "min_stock": item["min_stock"],
                "is_active": True,
                "created_by": created_by,
            },
        )
        InventoryItem.objects.update_or_create(
            product=product,
            defaults={
                "tenant": tenant,
                "quantity_on_hand": item["stock_qty"],
                "reserved_quantity": Decimal("0"),
                "min_quantity_alert": Decimal(str(item["min_stock"])),
                "location": "انبار اصلی",
            },
        )


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

        manager = _upsert_user(
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
