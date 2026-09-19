from decimal import Decimal, ROUND_HALF_UP

ZERO = Decimal('0')
CENT = Decimal('0.01')


def money(value):
    try:
        amount = Decimal(str(value if value is not None else 0))
    except Exception:
        amount = ZERO
    if amount < 0:
        amount = ZERO
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def worker_commission_pool(services_total, *, manual_discount_total=0):
    """Charged services minus manual discount. Loyalty/step/fixed discounts stay out."""
    services = money(services_total)
    manual = min(services, money(manual_discount_total))
    return max(ZERO, services - manual)


def net_services_pool(services_total, *, loyalty_discount_total=0, manual_discount_total=0):
    """Charged services after loyalty and manual discounts (what remains to split with carwash)."""
    services = money(services_total)
    discounts = min(services, money(loyalty_discount_total) + money(manual_discount_total))
    return max(ZERO, services - discounts)


def carwash_remainder(
    worker_pool,
    worker_share,
    *,
    loyalty_discount_total=0,
    tip_amount=0,
    workers_tip_share_amount=0,
):
    """Carwash gets the leftover after worker share and loyalty/step/fixed discounts."""
    leftover_tip = max(ZERO, money(tip_amount) - money(workers_tip_share_amount))
    remainder = money(worker_pool) - money(worker_share) - money(loyalty_discount_total)
    return max(ZERO, remainder) + leftover_tip
