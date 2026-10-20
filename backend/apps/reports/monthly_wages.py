from django.db import transaction

from apps.reports.models import WorkerPayoutTransaction
from apps.workers.models import WorkerProfile
from apps.reports.views import (
    _gregorian_to_jalali,
    _jalali_month_days,
    _worker_monthly_wage_for_month,
)


@transaction.atomic
def accrue_monthly_wages_for_day(target_day):
    """
    ثبت حق حقوق نیروهای ماهیانه فقط در آخرین روز ماه شمسی.
    """
    jy, jm, jd = _gregorian_to_jalali(target_day)

    # اگر امروز آخر ماه شمسی نیست، هیچ کاری نکن.
    if jd != _jalali_month_days(jy, jm):
        return 0

    reference_month = f'{jy:04d}/{jm:02d}'
    created_count = 0

    workers = WorkerProfile.objects.select_related('user').filter(
        payment_type=WorkerProfile.PaymentType.MONTHLY,
        is_deleted=False,
        user__is_deleted=False,
    )

    for worker in workers:
        amount = _worker_monthly_wage_for_month(
            worker,
            reference_month,
        )

        if amount <= 0:
            continue

        accrual_key = f'monthly-wage:{worker.id}:{reference_month}'

        _, created = WorkerPayoutTransaction.objects.get_or_create(
            accrual_key=accrual_key,
            defaults={
                'tenant': worker.tenant,
                'worker': worker,
                'kind': WorkerPayoutTransaction.Kind.MONTHLY_WAGE_ACCRUAL,
                'reference_month': reference_month,
                'amount': amount,
                'note': f'Monthly wage accrual {reference_month}',
            },
        )

        if created:
            created_count += 1

    return created_count