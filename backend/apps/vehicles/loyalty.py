from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from .models import PlateLoyaltyProfile


HALF_STAR = Decimal('0.5')
MAX_STARS = Decimal('5.0')
CYCLE_VISIT_LIMIT = 10
FIXED_VISIT_MILESTONES = (2, 5, 10)

_PERSIAN_ORDINAL_ONES = {
    1: 'اول',
    2: 'دوم',
    3: 'سوم',
    4: 'چهارم',
    5: 'پنجم',
    6: 'ششم',
    7: 'هفتم',
    8: 'هشتم',
    9: 'نهم',
}
_PERSIAN_ORDINAL_TENS = {
    10: 'دهم',
    20: 'بیستم',
    30: 'سی‌ام',
    40: 'چهلم',
    50: 'پنجاهم',
    60: 'شصتم',
    70: 'هفتادم',
    80: 'هشتادم',
    90: 'نودم',
}
_PERSIAN_ORDINAL_TEENS = {
    11: 'یازدهم',
    12: 'دوازدهم',
    13: 'سیزدهم',
    14: 'چهاردهم',
    15: 'پانزدهم',
    16: 'شانزدهم',
    17: 'هفدهم',
    18: 'هجدهم',
    19: 'نوزدهم',
}
_PERSIAN_CARDINAL_TENS = {
    20: 'بیست',
    30: 'سی',
    40: 'چهل',
    50: 'پنجاه',
    60: 'شصت',
    70: 'هفتاد',
    80: 'هشتاد',
    90: 'نود',
}


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


def persian_visit_ordinal(visit_number):
    number = int(visit_number or 0)
    if number <= 0:
        return str(number)
    if number in _PERSIAN_ORDINAL_ONES:
        return _PERSIAN_ORDINAL_ONES[number]
    if number in _PERSIAN_ORDINAL_TEENS:
        return _PERSIAN_ORDINAL_TEENS[number]
    if number in _PERSIAN_ORDINAL_TENS:
        return _PERSIAN_ORDINAL_TENS[number]
    if number < 100:
        tens = (number // 10) * 10
        ones = number % 10
        tens_label = _PERSIAN_CARDINAL_TENS.get(tens)
        ones_label = _PERSIAN_ORDINAL_ONES.get(ones)
        if tens_label and ones_label:
            return f'{tens_label}\u200cو{ones_label}'
    return str(number)


def cycle_visit_position(visit_count):
    number = int(visit_count or 0)
    if number <= 0:
        return 0
    return ((number - 1) % CYCLE_VISIT_LIMIT) + 1


def format_discount_percent_label(percent):
    value = Decimal(str(percent or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if value == value.to_integral():
        return f'{int(value)}'
    return f'{value.normalize()}'


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
    profile, _created = PlateLoyaltyProfile.objects.get_or_create(
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
    return profile


def preview_next_loyalty_state(profile=None, *, discount_percent_per_half_star=0):
    """Compute loyalty values for the upcoming visit without writing to DB.

    First visit (no profile / empty profile) => visit_count=1, score=0.5.
    """
    current_visit_count = int(getattr(profile, 'visit_count', 0) or 0) if profile else 0
    current_cycle_visit_count = int(getattr(profile, 'cycle_visit_count', 0) or 0) if profile else 0

    next_cycle_visit_count = current_cycle_visit_count + 1
    if next_cycle_visit_count > CYCLE_VISIT_LIMIT:
        next_cycle_visit_count = 1

    earned_score = HALF_STAR * Decimal(str(next_cycle_visit_count))
    if earned_score > MAX_STARS:
        earned_score = MAX_STARS
    cycle_completed = next_cycle_visit_count >= CYCLE_VISIT_LIMIT
    next_discount_percent = Decimal(str(discount_percent_per_half_star or 0)) * (earned_score * Decimal('2'))

    return {
        'visit_count': current_visit_count + 1,
        'cycle_visit_count': 0 if cycle_completed else next_cycle_visit_count,
        'score': float(Decimal('0') if cycle_completed else earned_score),
        'visit_score': float(earned_score),
        'discount_percent': float(Decimal('0') if cycle_completed else next_discount_percent),
    }


def apply_loyalty_visit(profile, *, discount_percent_per_half_star=0, now=None):
    if not profile:
        return None
    now = timezone.localtime(now or timezone.now())

    next_cycle_visit_count = int(profile.cycle_visit_count or 0) + 1
    if next_cycle_visit_count > CYCLE_VISIT_LIMIT:
        next_cycle_visit_count = 1
        profile.last_cycle_started_at = now

    earned_score = HALF_STAR * Decimal(str(next_cycle_visit_count))
    if earned_score > MAX_STARS:
        earned_score = MAX_STARS
    cycle_completed = next_cycle_visit_count >= CYCLE_VISIT_LIMIT
    next_discount_percent = Decimal(str(discount_percent_per_half_star or 0)) * (earned_score * Decimal('2'))

    profile.visit_count = int(profile.visit_count or 0) + 1
    profile.cycle_visit_count = 0 if cycle_completed else next_cycle_visit_count
    profile.score = Decimal('0') if cycle_completed else earned_score
    profile.next_discount_percent = Decimal('0') if cycle_completed else next_discount_percent
    profile._loyalty_visit_score = earned_score
    if not profile.first_order_at:
        profile.first_order_at = now
    if cycle_completed or not profile.last_cycle_started_at:
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


def count_loyalty_vehicle_entries(profile):
    if not profile or not profile.tenant_id or not profile.plate_number:
        return 0
    from .models import VehicleEntry

    return (
        VehicleEntry.objects.filter(
            tenant=profile.tenant,
            plate_number=profile.plate_number,
            is_piece_wash=False,
        )
        .exclude(status=VehicleEntry.Status.CANCELLED)
        .count()
    )


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


def sync_plate_loyalty(profile, *, discount_percent_per_half_star=0, now=None):
    """Rebuild loyalty when stored visit_count/score does not match real vehicle entries."""
    if not profile:
        return None
    current_visits = int(profile.visit_count or 0)
    current_score = Decimal(str(profile.score or 0))
    cycle_just_completed = current_visits > 0 and current_visits % CYCLE_VISIT_LIMIT == 0
    # Healthy profiles skip the extra count query on every serialize.
    if current_visits > 0 and (current_score > 0 or cycle_just_completed):
        return profile

    expected_visits = count_loyalty_vehicle_entries(profile)
    first_visit_missing_score = (
        expected_visits > 0 and current_visits > 0 and current_score == 0 and not cycle_just_completed
    )
    if expected_visits == current_visits and not first_visit_missing_score:
        return profile
    return rebuild_plate_loyalty(
        profile,
        discount_percent_per_half_star=discount_percent_per_half_star,
        now=now,
    )


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
        position = cycle_visit_position(current_visit)
        discount_percent = Decimal(str(fixed_discounts.get(str(position), 0) or 0))
        discount_amount = money((normalized_base * discount_percent) / Decimal('100'))
        return discount_percent, discount_amount

    visit_score = score
    if visit_score is None and profile is not None:
        visit_score = getattr(profile, '_loyalty_visit_score', None)
    if visit_score is None:
        visit_score = getattr(profile, 'score', 0) if profile is not None else 0

    return compute_loyalty_discount(
        base_amount=normalized_base,
        score=visit_score,
        percent_per_half_star=getattr(settings_obj, 'discount_percent_per_half_star', 0) or 0,
    )


def iter_fixed_discount_milestones(visit_count, fixed_discounts, *, ahead=3):
    current_visit = int(visit_count or 0)
    start_cycle = max(0, current_visit // CYCLE_VISIT_LIMIT)
    for cycle_index in range(start_cycle, start_cycle + max(1, ahead)):
        cycle_base = cycle_index * CYCLE_VISIT_LIMIT
        for milestone in FIXED_VISIT_MILESTONES:
            percent = Decimal(str(fixed_discounts.get(str(milestone), 0) or 0))
            if percent <= 0:
                continue
            absolute_visit = cycle_base + milestone
            if absolute_visit > current_visit:
                yield absolute_visit, percent


def next_fixed_discount_notice(settings_obj, visit_count):
    if loyalty_discount_mode(settings_obj) != 'fixed':
        return None
    fixed_discounts = normalize_fixed_visit_discounts(getattr(settings_obj, 'fixed_visit_discounts', {}))
    current_visit = int(visit_count or 0)
    for absolute_visit, percent in iter_fixed_discount_milestones(current_visit, fixed_discounts):
        percent_label = format_discount_percent_label(percent)
        remaining = absolute_visit - current_visit
        return {
            'remaining_visits': remaining,
            'target_visit': absolute_visit,
            'discount_percent': float(percent),
            'text': f'درصد تخفیف مراجعه {persian_visit_ordinal(absolute_visit)} : {percent_label}٪',
        }
    return None


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
