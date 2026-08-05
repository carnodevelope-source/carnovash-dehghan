"""Sample / demo carwash helpers: caps, HQ visibility, PII mask, clone."""

from __future__ import annotations

import copy
import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

SAMPLE_MASKED_PHONE = '09999999999'
SAMPLE_MASKED_NAME = 'مـ ـ ـ ـ ـ'
SAMPLE_TENANT_NAME = 'کارنوواش نمونه'
SAMPLE_TENANT_SLUG = 'carnowash-sample'
SAMPLE_MANAGER_USERNAME = 'carnowash'
SAMPLE_MANAGER_PASSWORD = 'carnowash@123'
SAMPLE_MANAGER_PHONE = '09134279848'
SAMPLE_MANAGER_NAME = 'میلاد دهستانی'
SAMPLE_DAILY_SMS_LIMIT = 15
SAMPLE_DAILY_VEHICLE_LIMIT = 20
SAMPLE_MONTHLY_SMS_ALERT_THRESHOLD = 250
SAMPLE_SMS_ALERT_CODE = 'sample_sms_monthly_cap'


def mask_person_name(_value=''):
    return SAMPLE_MASKED_NAME


def is_sample_tenant(tenant):
    return bool(tenant and getattr(tenant, 'is_sample', False))


def hq_reportable_carwashes_q():
    return Q(exclude_from_hq_reports=False, is_sample=False)


def hq_ticket_tenants_q():
    """Tickets visible for normal tenants and sample tenants."""
    return Q(exclude_from_hq_reports=False) | Q(is_sample=True)


def hq_ticket_queryset_q():
    """Q() for SupportTicket queryset joins."""
    return Q(tenant__exclude_from_hq_reports=False) | Q(tenant__is_sample=True)


def sample_daily_sms_limit(tenant):
    if not is_sample_tenant(tenant):
        return None
    return int(getattr(tenant, 'sample_daily_sms_limit', None) or SAMPLE_DAILY_SMS_LIMIT)


def sample_daily_vehicle_limit(tenant):
    if not is_sample_tenant(tenant):
        return None
    return int(getattr(tenant, 'sample_daily_vehicle_limit', None) or SAMPLE_DAILY_VEHICLE_LIMIT)


def _local_day_bounds(now=None):
    now = timezone.localtime(now or timezone.now())
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def _local_month_bounds(now=None):
    now = timezone.localtime(now or timezone.now())
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def count_sample_sms_sent(*, tenant=None, since=None, until=None):
    from apps.auth.models import CarWash
    from apps.notifications.models import NotificationLog

    qs = NotificationLog.objects.filter(
        channel=NotificationLog.Channel.SMS,
        status=NotificationLog.Status.SENT,
        tenant__is_sample=True,
    )
    if tenant is not None:
        qs = qs.filter(tenant=tenant)
    else:
        qs = qs.filter(tenant_id__in=CarWash.objects.filter(is_sample=True).values('id'))
    if since is not None:
        qs = qs.filter(created_at__gte=since)
    if until is not None:
        qs = qs.filter(created_at__lt=until)
    return qs.count()


def count_sample_vehicles_today(tenant):
    from apps.vehicles.models import VehicleEntry

    start, end = _local_day_bounds()
    return (
        VehicleEntry.objects.filter(
            tenant=tenant,
            check_in_at__gte=start,
            check_in_at__lt=end,
        )
        .exclude(status=VehicleEntry.Status.CANCELLED)
        .count()
    )


def assert_sample_vehicle_capacity(tenant):
    limit = sample_daily_vehicle_limit(tenant)
    if limit is None:
        return
    used = count_sample_vehicles_today(tenant)
    if used >= limit:
        raise ValueError(f'سقف ثبت روزانه خودرو برای کارواش نمونه ({limit} مورد) تکمیل شده است.')


def assert_sample_sms_capacity(tenant, extra=1):
    limit = sample_daily_sms_limit(tenant)
    if limit is None:
        return
    start, end = _local_day_bounds()
    used = count_sample_sms_sent(tenant=tenant, since=start, until=end)
    if used + int(extra) > limit:
        raise ValueError(f'سقف پیامک روزانه کارواش نمونه ({limit} پیامک) تکمیل شده است.')


def maybe_raise_sample_monthly_sms_alert():
    from apps.auth.models import CarWash
    from apps.subscriptions.models import ServiceAlert

    start, end = _local_month_bounds()
    total = count_sample_sms_sent(since=start, until=end)
    if total < SAMPLE_MONTHLY_SMS_ALERT_THRESHOLD:
        return None

    sample = CarWash.objects.filter(is_sample=True, is_active=True).order_by('id').first()
    if not sample:
        return None

    existing = ServiceAlert.objects.filter(
        code=SAMPLE_SMS_ALERT_CODE,
        is_resolved=False,
        created_at__gte=start,
        created_at__lt=end,
    ).first()
    if existing:
        return existing

    return ServiceAlert.objects.create(
        tenant=sample,
        subscription=None,
        code=SAMPLE_SMS_ALERT_CODE,
        title='سقف پیامک ماهانه کارواش‌های نمونه',
        message=(
            f'مجموع پیامک ارسال‌شده از پنل‌های نمونه کارنواش در این ماه به '
            f'{total} رسیده است (سقف هشدار: {SAMPLE_MONTHLY_SMS_ALERT_THRESHOLD}).'
        ),
        severity=ServiceAlert.Severity.WARNING,
    )


def find_milan_source_tenant():
    from apps.auth.models import CarWash

    return (
        CarWash.objects.filter(Q(name__icontains='میلان') | Q(slug__icontains='milan'))
        .order_by('id')
        .first()
    )


def _unique_slug(base, model):
    candidate = slugify(base, allow_unicode=True) or 'item'
    candidate = candidate[:140]
    if not model.objects.filter(slug=candidate).exists():
        return candidate
    for i in range(2, 10000):
        suffix = f'-{i}'
        trimmed = candidate[: max(1, 140 - len(suffix))] + suffix
        if not model.objects.filter(slug=trimmed).exists():
            return trimmed
    return f'{candidate[:120]}-{uuid.uuid4().hex[:8]}'


def _unique_sku(base):
    from apps.products.models import Product

    candidate = (base or f'S-{uuid.uuid4().hex[:8]}')[:60]
    if not Product.objects.filter(sku=candidate).exists():
        return candidate
    for i in range(2, 10000):
        suffix = f'-{i}'
        trimmed = candidate[: max(1, 60 - len(suffix))] + suffix
        if not Product.objects.filter(sku=trimmed).exists():
            return trimmed
    return f'S-{uuid.uuid4().hex[:12]}'


def _copy_row(instance, **overrides):
    clone = copy.copy(instance)
    clone.pk = None
    for field in instance._meta.concrete_fields:
        if field.primary_key:
            setattr(clone, field.attname, None)
    for key, value in overrides.items():
        setattr(clone, key, value)
    return clone


@transaction.atomic
def create_or_refresh_sample_carwash(*, source=None, force=False, stdout=None):
    """
    Clone Milan (or given source) into sample tenant with masked historical PII.
    New customers added later keep real name/phone (normal flow).
    """
    from apps.auth.models import CarWash, CarWashFeaturePurchase, SupportTicket
    from apps.inventory.models import ExpenseEntry, InventoryItem, StockMovement
    from apps.notifications.models import CustomerGroup, ImportedCustomer, NotificationLog, SmsTemplate
    from apps.payments.models import CashflowTransaction, Payment, Wallet
    from apps.products.models import Product, ProductCategory
    from apps.services.models import GeneralSettings, Service, ServiceCategory
    from apps.vehicles.models import (
        BlockedPlate,
        CustomerProfile,
        PlateLoyaltyProfile,
        VehicleEntry,
        VehicleJob,
        VehicleJobProduct,
        VehicleJobService,
        VehicleStatusLog,
    )
    from apps.workers.models import WorkerAttendance, WorkerProfile

    User = get_user_model()
    log = stdout.write if stdout else (lambda *_a, **_k: None)

    source = source or find_milan_source_tenant()
    if not source:
        raise ValueError(
            'کارواش منبع (میلان) پیدا نشد. ابتدا بکاپ را روی دیتابیس لود کنید یا --source-tenant-id بدهید.'
        )

    existing = CarWash.objects.filter(Q(slug=SAMPLE_TENANT_SLUG) | Q(is_sample=True, name=SAMPLE_TENANT_NAME)).first()
    if existing and not force:
        raise ValueError(f'کارواش نمونه از قبل وجود دارد (id={existing.id}). برای جایگزینی --force بزنید.')

    if existing and force:
        log(f'Removing existing sample tenant id={existing.id}...')
        User.objects.filter(tenant=existing).delete()
        existing.delete()

    if User.objects.filter(username__iexact=SAMPLE_MANAGER_USERNAME).exists():
        raise ValueError(f'یوزرنیم {SAMPLE_MANAGER_USERNAME} از قبل وجود دارد.')

    phone_conflict = (
        User.objects.filter(phone=SAMPLE_MANAGER_PHONE)
        .exclude(tenant__is_sample=True)
        .first()
    )
    if phone_conflict:
        raise ValueError(
            f'شماره مدیر نمونه ({SAMPLE_MANAGER_PHONE}) قبلا برای کاربر {phone_conflict.username} ثبت شده است.'
        )

    sample = CarWash.objects.create(
        name=SAMPLE_TENANT_NAME,
        slug=SAMPLE_TENANT_SLUG,
        address=source.address or '',
        is_active=True,
        exclude_from_hq_reports=False,
        is_sample=True,
        sample_daily_sms_limit=SAMPLE_DAILY_SMS_LIMIT,
        sample_daily_vehicle_limit=SAMPLE_DAILY_VEHICLE_LIMIT,
        trial_started_at=None,
        trial_ends_at=None,
    )
    log(f'Created sample tenant id={sample.id}')

    manager = User(
        username=SAMPLE_MANAGER_USERNAME,
        full_name=SAMPLE_MANAGER_NAME,
        phone=SAMPLE_MANAGER_PHONE,
        role=User.Roles.MANAGER,
        tenant=sample,
        is_active=True,
        email=f'{SAMPLE_MANAGER_USERNAME}@sample.carnowash.local',
    )
    manager.set_password(SAMPLE_MANAGER_PASSWORD)
    manager.save()

    user_map = {}
    worker_map = {}

    source_users = list(
        User.objects.filter(tenant=source)
        .filter(Q(platform_role='') | Q(platform_role__isnull=True))
        .order_by('id')
    )

    for old_user in source_users:
        if old_user.role in {User.Roles.MANAGER, User.Roles.ADMIN, User.Roles.OWNER}:
            continue
        new_username = f'sample_{old_user.username}'[:150]
        base = new_username
        n = 1
        while User.objects.filter(username__iexact=new_username).exists():
            n += 1
            new_username = f'{base[:140]}_{n}'

        clone = User(
            username=new_username,
            full_name=mask_person_name(old_user.full_name),
            phone=SAMPLE_MASKED_PHONE,
            role=old_user.role,
            tenant=sample,
            is_active=old_user.is_active,
            is_active_worker=getattr(old_user, 'is_active_worker', True),
            email=f'{new_username}@sample.carnowash.local',
            is_deleted=getattr(old_user, 'is_deleted', False),
        )
        clone.set_password(uuid.uuid4().hex[:12])
        clone.save()
        user_map[old_user.id] = clone

    for old_worker in WorkerProfile.objects.filter(tenant=source).select_related('user').order_by('id'):
        new_user = user_map.get(old_worker.user_id)
        if not new_user:
            new_username = f'sample_worker_{old_worker.id}'
            new_user = User(
                username=new_username,
                full_name=mask_person_name(getattr(old_worker.user, 'full_name', '')),
                phone=SAMPLE_MASKED_PHONE,
                role=User.Roles.WORKER,
                tenant=sample,
                is_active=True,
                email=f'{new_username}@sample.carnowash.local',
            )
            new_user.set_password(uuid.uuid4().hex[:12])
            new_user.save()
            user_map[old_worker.user_id] = new_user

        code = None
        if old_worker.code:
            code = f's{old_worker.code}'[:30]
            if WorkerProfile.objects.filter(code=code).exists():
                code = f'sw{old_worker.id}'[:30]

        new_worker = _copy_row(
            old_worker,
            user=new_user,
            tenant=sample,
            code=code,
            national_id='',
            attendance_token=uuid.uuid4().hex,
            address='',
            notes='',
            deleted_by=None,
        )
        new_worker.save()
        worker_map[old_worker.id] = new_worker

    for old_att in WorkerAttendance.objects.filter(tenant=source).order_by('id'):
        new_worker = worker_map.get(old_att.worker_id)
        if not new_worker:
            continue
        _copy_row(old_att, tenant=sample, worker=new_worker).save()

    for fp in CarWashFeaturePurchase.objects.filter(tenant=source):
        _copy_row(fp, tenant=sample).save()

    src_settings = GeneralSettings.objects.filter(tenant=source).first()
    if src_settings:
        _copy_row(src_settings, tenant=sample).save()

    cat_map = {}
    for old_cat in ServiceCategory.objects.filter(tenant=source).order_by('id'):
        new_cat = _copy_row(
            old_cat,
            tenant=sample,
            slug=_unique_slug(f'{old_cat.slug}-sample', ServiceCategory),
            created_by=manager,
        )
        new_cat.save()
        cat_map[old_cat.id] = new_cat

    service_map = {}
    for old_svc in Service.objects.filter(tenant=source).order_by('id'):
        new_code = old_svc.code
        if new_code:
            base_code = f'S{new_code}'[:30]
            new_code = base_code
            n = 1
            while Service.objects.filter(code=new_code).exists():
                n += 1
                suffix = str(n)
                new_code = f'{base_code[: max(1, 30 - len(suffix))]}{suffix}'
        new_svc = _copy_row(
            old_svc,
            tenant=sample,
            category=cat_map.get(old_svc.category_id),
            code=new_code,
            created_by=manager,
            deleted_by=None,
        )
        new_svc.save()
        service_map[old_svc.id] = new_svc

    pcat_map = {}
    for old_pc in ProductCategory.objects.filter(tenant=source).order_by('id'):
        new_pc = _copy_row(
            old_pc,
            tenant=sample,
            slug=_unique_slug(f'{old_pc.slug}-sample', ProductCategory),
        )
        new_pc.save()
        pcat_map[old_pc.id] = new_pc

    product_map = {}
    for old_p in Product.objects.filter(tenant=source).order_by('id'):
        new_p = _copy_row(
            old_p,
            tenant=sample,
            category=pcat_map.get(old_p.category_id),
            sku=_unique_sku(f'S-{old_p.sku}'),
            created_by=manager,
            deleted_by=None,
        )
        new_p.save()
        product_map[old_p.id] = new_p

    inv_map = {}
    for old_inv in InventoryItem.objects.filter(tenant=source).order_by('id'):
        new_product = product_map.get(old_inv.product_id)
        if not new_product:
            continue
        new_inv = _copy_row(old_inv, tenant=sample, product=new_product)
        new_inv.save()
        inv_map[old_inv.id] = new_inv

    for old_m in StockMovement.objects.filter(tenant=source).order_by('id'):
        new_inv = inv_map.get(old_m.inventory_item_id)
        if not new_inv:
            continue
        _copy_row(
            old_m,
            tenant=sample,
            inventory_item=new_inv,
            created_by=user_map.get(old_m.created_by_id) or manager,
        ).save()

    for old_exp in ExpenseEntry.objects.filter(tenant=source, is_deleted=False).order_by('id'):
        _copy_row(
            old_exp,
            tenant=sample,
            created_by=user_map.get(old_exp.created_by_id) or manager,
            deleted_by=None,
            attachment=None,
        ).save()

    wallet_map = {}
    for old_w in Wallet.objects.filter(tenant=source).order_by('id'):
        new_w = _copy_row(old_w, tenant=sample)
        new_w.save()
        wallet_map[old_w.id] = new_w

    masked_customer, _created = CustomerProfile.objects.get_or_create(
        phone=SAMPLE_MASKED_PHONE,
        defaults={
            'tenant': sample,
            'full_name': SAMPLE_MASKED_NAME,
            'gender': '',
            'yearly_score': Decimal('0'),
            'score_year': timezone.localtime().year,
        },
    )
    if masked_customer.tenant_id != sample.id or masked_customer.full_name != SAMPLE_MASKED_NAME:
        masked_customer.tenant = sample
        masked_customer.full_name = SAMPLE_MASKED_NAME
        masked_customer.save(update_fields=['tenant', 'full_name', 'updated_at'])

    for old_lp in PlateLoyaltyProfile.objects.filter(tenant=source).order_by('id'):
        _copy_row(old_lp, tenant=sample).save()

    for old_bp in BlockedPlate.objects.filter(tenant=source).order_by('id'):
        _copy_row(
            old_bp,
            tenant=sample,
            blocked_by=user_map.get(old_bp.blocked_by_id) or manager,
        ).save()

    vehicle_map = {}
    for old_v in VehicleEntry.objects.filter(tenant=source).order_by('id'):
        new_v = _copy_row(
            old_v,
            tenant=sample,
            driver_name=SAMPLE_MASKED_NAME,
            driver_phone=SAMPLE_MASKED_PHONE,
            customer=masked_customer,
            entered_by=user_map.get(old_v.entered_by_id) or manager,
            updated_by=user_map.get(old_v.updated_by_id),
        )
        new_v.save()
        vehicle_map[old_v.id] = new_v

    for old_log in VehicleStatusLog.objects.filter(tenant=source).order_by('id'):
        new_v = vehicle_map.get(old_log.vehicle_id)
        if not new_v:
            continue
        _copy_row(
            old_log,
            tenant=sample,
            vehicle=new_v,
            changed_by=user_map.get(old_log.changed_by_id) or manager,
        ).save()

    for old_job in VehicleJob.objects.filter(tenant=source).order_by('id'):
        new_v = vehicle_map.get(old_job.vehicle_id)
        if not new_v:
            continue
        new_job = _copy_row(
            old_job,
            tenant=sample,
            vehicle=new_v,
            assigned_worker=worker_map.get(old_job.assigned_worker_id),
        )
        new_job.save()

        for old_js in VehicleJobService.objects.filter(vehicle_job=old_job).order_by('id'):
            _copy_row(
                old_js,
                tenant=sample,
                vehicle_job=new_job,
                service=service_map.get(old_js.service_id),
            ).save()

        for old_jp in VehicleJobProduct.objects.filter(vehicle_job=old_job).order_by('id'):
            new_product = product_map.get(old_jp.product_id)
            if not new_product:
                continue
            _copy_row(
                old_jp,
                tenant=sample,
                vehicle_job=new_job,
                product=new_product,
            ).save()

    for old_pay in Payment.objects.filter(tenant=source).order_by('id'):
        new_v = vehicle_map.get(old_pay.vehicle_entry_id)
        if not new_v:
            continue
        _copy_row(
            old_pay,
            tenant=sample,
            vehicle_entry=new_v,
            wallet=wallet_map.get(old_pay.wallet_id),
            payer_name=SAMPLE_MASKED_NAME if old_pay.payer_name else '',
            payer_phone=SAMPLE_MASKED_PHONE if old_pay.payer_phone else '',
            created_by=user_map.get(old_pay.created_by_id) or manager,
        ).save()

    for old_cf in CashflowTransaction.objects.filter(tenant=source).order_by('id'):
        new_w = wallet_map.get(old_cf.wallet_id)
        if not new_w:
            continue
        _copy_row(
            old_cf,
            tenant=sample,
            wallet=new_w,
            created_by=user_map.get(old_cf.created_by_id) or manager,
        ).save()

    for old_t in SmsTemplate.objects.filter(tenant=source).order_by('id'):
        _copy_row(old_t, tenant=sample, created_by=manager).save()

    for old_g in CustomerGroup.objects.filter(tenant=source).order_by('id'):
        _copy_row(old_g, tenant=sample, created_by=manager, updated_by=None).save()

    ImportedCustomer.objects.filter(tenant=sample).delete()
    ImportedCustomer.objects.create(
        tenant=sample,
        full_name=SAMPLE_MASKED_NAME,
        phone=SAMPLE_MASKED_PHONE,
        car_model='',
        car_color='',
        plate_number='',
        notes='masked historical import',
        source='sample_clone',
        imported_by=manager,
    )

    for old_n in NotificationLog.objects.filter(tenant=source).order_by('id'):
        recipient = old_n.recipient
        if old_n.channel == NotificationLog.Channel.SMS:
            recipient = SAMPLE_MASKED_PHONE
        _copy_row(
            old_n,
            tenant=sample,
            vehicle_entry=vehicle_map.get(old_n.vehicle_entry_id),
            recipient=recipient,
            created_by=user_map.get(old_n.created_by_id) or manager,
        ).save()

    SupportTicket.objects.filter(tenant=sample).delete()

    log(
        f'Sample ready: tenant={sample.id} manager={SAMPLE_MANAGER_USERNAME} '
        f'vehicles={len(vehicle_map)} workers={len(worker_map)}'
    )
    return sample, manager
