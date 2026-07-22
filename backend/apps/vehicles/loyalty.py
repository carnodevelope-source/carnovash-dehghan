from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from .models import PlateLoyaltyProfile


HALF_STAR = Decimal('0.5')
MAX_STARS = Decimal('5.0')
CYCLE_VISIT_LIMIT = 10
FIXED_VISIT_MILESTONES = (2, 5, 10)


def money(value):
    return Decimal(str(value or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def normalize_plate(
    *,
    plate_number='',
    plate_left='',
    plate_letter='',
    plate_mid='',
    plate_right='',
):
    left = str(plate_left or '').strip()
    letter = str(plate_letter or '').strip()
    mid = str(plate_mid or '').strip()
    right = str(plate_right or '').strip()
    if left and letter and mid and right:
        return f'{left} {letter} {mid} {right}'
    if mid and letter and not left and not right:
        return f'{mid} {letter}'
    return str(plate_number or '').strip()


def needs_anniversary_reset(profile, now=None):
    now = timezone.localtime(now or timezone.now())
    first_order_at = getattr(profile, 'first_order_at', None)
    if not first_order_at:
        return False
    first_local = timezone.localtime(first_order_at)
    anniversary_this_year = first_local.replace(year=now.year)
    if anniversary_this_year > now:
        anniversary_this_year = anniversary_this_year.replace(year=now.year - 1)
    return anniversary_this_year > timezone.localtime(profile.updated_at)


def reset_loyalty_profile(profile, now=None):
    now = timezone.localtime(now or timezone.now())
    profile.score = Decimal('0')
    profile.cycle_visit_count = 0
    profile.next_discount_percent = Decimal('0')
    profile.last_cycle_started_at = now
    profile.save(
        update_fields=[
            'score',
            'cycle_visit_count',
            'next_discount_percent',
            'last_cycle_started_at',
            'updated_at',
        ]
    )
    return profile


def get_or_create_plate_loyalty(
    *,
    tenant,
    plate_number='',
    plate_left='',
    plate_letter='',
    plate_mid='',
    plate_right='',
    now=None,
):
    normalized_plate = normalize_plate(
        plate_number=plate_number,
        plate_left=plate_left,
        plate_letter=plate_letter,
        plate_mid=plate_mid,
        plate_right=plate_right,
    )
    if not tenant or not normalized_plate:
        return None
    now = timezone.localtime(now or timezone.now())
    profile, created = PlateLoyaltyProfile.objects.get_or_create(
        tenant=tenant,
        plate_number=normalized_plate,
        defaults={
            'plate_left': str(plate_left or '').strip(),
            'plate_letter': str(plate_letter or '').strip(),
            'plate_mid': str(plate_mid or '').strip(),
            'plate_right': str(plate_right or '').strip(),
            'first_order_at': now,
            'last_cycle_started_at': now,
            'is_active': True,
        },
    )
    changed_fields = []
    for field_name, raw_value in (
        ('plate_left', plate_left),
        ('plate_letter', plate_letter),
        ('plate_mid', plate_mid),
        ('plate_right', plate_right),
    ):
        normalized_value = str(raw_value or '').strip()
        if normalized_value != getattr(profile, field_name):
            setattr(profile, field_name, normalized_value)
            changed_fields.append(field_name)
    if not profile.first_order_at:
        profile.first_order_at = now
        changed_fields.append('first_order_at')
    if not profile.last_cycle_started_at:
        profile.last_cycle_started_at = now
        changed_fields.append('last_cycle_started_at')
    if not profile.is_active:
        profile.is_active = True
        changed_fields.append('is_active')
    if changed_fields:
        changed_fields.append('updated_at')
        profile.save(update_fields=changed_fields)
    if not created and needs_anniversary_reset(profile, now=now):
        profile = reset_loyalty_profile(profile, now=now)
    return profile


def apply_loyalty_visit(profile, *, discount_percent_per_half_star=0, now=None):
    if not profile:
        return None
    now = timezone.localtime(now or timezone.now())
    if needs_anniversary_reset(profile, now=now):
        reset_loyalty_profile(profile, now=now)
        profile.refresh_from_db()

    next_cycle_visit_count = int(profile.cycle_visit_count or 0) + 1
    if next_cycle_visit_count > CYCLE_VISIT_LIMIT:
        next_cycle_visit_count = 1
        profile.last_cycle_started_at = now

    score = HALF_STAR * Decimal(str(next_cycle_visit_count))
    if score > MAX_STARS:
        score = HALF_STAR

    next_discount_percent = Decimal(str(discount_percent_per_half_star or 0)) * (score * Decimal('2'))
    profile.visit_count = int(profile.visit_count or 0) + 1
    profile.cycle_visit_count = next_cycle_visit_count
    profile.score = score
    profile.next_discount_percent = next_discount_percent
    if not profile.first_order_at:
        profile.first_order_at = now
    if not profile.last_cycle_started_at:
        profile.last_cycle_started_at = now
    profile.save(
        update_fields=[
            'visit_count',
            'cycle_visit_count',
            'score',
            'next_discount_percent',
            'first_order_at',
            'last_cycle_started_at',
            'updated_at',
        ]
    )
    return profile


def rebuild_plate_loyalty(profile, *, discount_percent_per_half_star=0, now=None):
    if not profile:
        return None
    from .models import VehicleEntry

    now = timezone.localtime(now or timezone.now())
    vehicles = list(
        VehicleEntry.objects.filter(
            tenant=profile.tenant,
            plate_number=profile.plate_number,
            is_piece_wash=False,
        )
        .exclude(status=VehicleEntry.Status.CANCELLED)
        .order_by('check_in_at', 'id')
    )

    profile.visit_count = 0
    profile.cycle_visit_count = 0
    profile.score = Decimal('0')
    profile.next_discount_percent = Decimal('0')
    profile.first_order_at = vehicles[0].check_in_at if vehicles else now
    profile.last_cycle_started_at = vehicles[0].check_in_at if vehicles else now
    profile.save(
        update_fields=[
            'visit_count',
            'cycle_visit_count',
            'score',
            'next_discount_percent',
            'first_order_at',
            'last_cycle_started_at',
            'updated_at',
        ]
    )
    for vehicle in vehicles:
        profile = apply_loyalty_visit(
            profile,
            discount_percent_per_half_star=discount_percent_per_half_star,
            now=vehicle.check_in_at,
        )
    return profile


def rebuild_customer_score(customer, *, now=None):
    if not customer:
        return None
    from .models import VehicleEntry

    current_year = timezone.localtime(now or timezone.now()).year
    visits_count = VehicleEntry.objects.filter(
        customer=customer,
        check_in_at__year=current_year,
    ).exclude(status=VehicleEntry.Status.CANCELLED).count()
    customer.score_year = current_year
    customer.yearly_score = min(MAX_STARS, HALF_STAR * Decimal(str(visits_count)))
    customer.save(update_fields=['score_year', 'yearly_score', 'updated_at'])
    return customer


def compute_loyalty_discount(base_amount, score, percent_per_half_star):
    normalized_score = Decimal(str(score or 0))
    if normalized_score < 0:
        normalized_score = Decimal('0')
    if normalized_score > MAX_STARS:
        normalized_score = MAX_STARS
    half_stars = normalized_score * Decimal('2')
    discount_percent = Decimal(str(percent_per_half_star or 0)) * half_stars
    discount_amount = money((Decimal(str(base_amount or 0)) * discount_percent) / Decimal('100'))
    return discount_percent, discount_amount


def normalize_fixed_visit_discounts(raw_value):
    source = raw_value if isinstance(raw_value, dict) else {}
    normalized = {}
    for visit_number in FIXED_VISIT_MILESTONES:
        value = source.get(str(visit_number), source.get(visit_number, 0))
        try:
            percent = Decimal(str(value or 0))
        except Exception:
            percent = Decimal('0')
        if percent < 0:
            percent = Decimal('0')
        if percent > 100:
            percent = Decimal('100')
        normalized[str(visit_number)] = float(percent)
    return normalized


def loyalty_discount_mode(settings_obj):
    mode = str(getattr(settings_obj, 'discount_calculation_mode', '') or '').strip().lower()
    return 'fixed' if mode == 'fixed' else 'step'


def compute_configured_loyalty_discount(base_amount, profile, settings_obj, *, visit_count=None, score=None):
    mode = loyalty_discount_mode(settings_obj)
    normalized_base = Decimal(str(base_amount or 0))
    if mode == 'fixed':
        current_visit = int(visit_count if visit_count is not None else getattr(profile, 'visit_count', 0) or 0)
        fixed_discounts = normalize_fixed_visit_discounts(getattr(settings_obj, 'fixed_visit_discounts', {}))
        discount_percent = Decimal(str(fixed_discounts.get(str(current_visit), 0) or 0))
        discount_amount = money((normalized_base * discount_percent) / Decimal('100'))
        return discount_percent, discount_amount

    return compute_loyalty_discount(
        base_amount=normalized_base,
        score=score if score is not None else getattr(profile, 'score', 0),
        percent_per_half_star=getattr(settings_obj, 'discount_percent_per_half_star', 0) or 0,
    )


def next_fixed_discount_notice(settings_obj, visit_count):
    if loyalty_discount_mode(settings_obj) != 'fixed':
        return ''
    fixed_discounts = normalize_fixed_visit_discounts(getattr(settings_obj, 'fixed_visit_discounts', {}))
    current_visit = int(visit_count or 0)
    for visit_number in FIXED_VISIT_MILESTONES:
        percent = Decimal(str(fixed_discounts.get(str(visit_number), 0) or 0))
        if percent <= 0 or visit_number <= current_visit:
            continue
        remaining = visit_number - current_visit
        return {
            'remaining_visits': remaining,
            'target_visit': visit_number,
            'discount_percent': float(percent),
            'text': f'{remaining} مراجعه مانده تا تخفیف {float(percent):g}٪',
        }
    return {
        'remaining_visits': 0,
        'target_visit': 0,
        'discount_percent': 0,
        'text': 'تخفیف ثابتی برای مراجعات بعدی ثبت نشده است.',
    }


def loyalty_snapshot(profile):
    if not profile:
        return {
            'score': 0.0,
            'visit_count': 0,
            'discount_percent': 0.0,
        }
    return {
        'score': float(profile.score or 0),
        'visit_count': int(profile.visit_count or 0),
        'discount_percent': float(profile.next_discount_percent or 0),
    }
