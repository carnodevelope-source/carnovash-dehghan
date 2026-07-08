from datetime import datetime, time
from decimal import Decimal

from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.models import Payment
from apps.vehicles.models import VehicleEntry, VehicleJob
from apps.workers.models import WorkerAttendance, WorkerProfile
from apps.reports.models import WorkerPayoutTransaction


def _parse_dt(value, end_of_day=False):
    if not value:
        return None
    dt = datetime.strptime(value, '%Y-%m-%d')
    dt = datetime.combine(dt.date(), time.max if end_of_day else time.min)
    return timezone.make_aware(dt)


def _normalize_decimal(value):
    return Decimal(str(value or 0))


def _worker_name(worker):
    if not worker or not getattr(worker, 'user', None):
        return '-'
    return worker.user.full_name or worker.user.username or '-'


def _job_has_worker(job, worker_id):
    if not worker_id or not job:
        return True
    if job.assigned_worker_id == worker_id:
        return True
    snapshot = job.assigned_workers_snapshot if isinstance(job.assigned_workers_snapshot, list) else []
    for item in snapshot:
        try:
            if int(item.get('id')) == int(worker_id):
                return True
        except (TypeError, ValueError, AttributeError):
            continue
    return False


def _job_worker_ids(job):
    if not job:
        return []
    result = []
    snapshot = job.assigned_workers_snapshot if isinstance(job.assigned_workers_snapshot, list) else []
    for item in snapshot:
        try:
            worker_id = int(item.get('id'))
        except (TypeError, ValueError, AttributeError):
            continue
        if worker_id > 0 and worker_id not in result:
            result.append(worker_id)
    if job.assigned_worker_id and int(job.assigned_worker_id) not in result:
        result.insert(0, int(job.assigned_worker_id))
    return result


def _job_worker_share_for(job, worker_id):
    snapshot = job.assigned_workers_snapshot if isinstance(job.assigned_workers_snapshot, list) else []
    for item in snapshot:
        try:
            if int(item.get('id')) != int(worker_id):
                continue
        except (TypeError, ValueError, AttributeError):
            continue
        if item.get('worker_share_amount') is not None:
            return _normalize_decimal(item.get('worker_share_amount'))
    worker_ids = _job_worker_ids(job)
    if not worker_ids or int(worker_id) not in worker_ids:
        return Decimal('0')
    total = _normalize_decimal(job.worker_share_amount)
    share_per_worker = total / Decimal(str(len(worker_ids)))
    return share_per_worker


def _job_worker_tip_for(job, worker_id):
    snapshot = job.assigned_workers_snapshot if isinstance(job.assigned_workers_snapshot, list) else []
    for item in snapshot:
        try:
            if int(item.get('id')) == int(worker_id):
                tip_share_amount = item.get('tip_share_amount')
                if tip_share_amount is not None:
                    return _normalize_decimal(tip_share_amount)
        except (TypeError, ValueError, AttributeError):
            continue
    worker_ids = _job_worker_ids(job)
    if not worker_ids or int(worker_id) not in worker_ids:
        return Decimal('0')
    if len(worker_ids) == 1:
        return _normalize_decimal(job.workers_tip_share_amount or job.tip_amount)
    distributed = _normalize_decimal(job.workers_tip_share_amount)
    if distributed <= 0:
        return Decimal('0')
    return distributed / Decimal(str(len(worker_ids)))


def _get_worker_jobs(tenant, worker_id):
    jobs = list(VehicleJob.objects.select_related('vehicle').filter(tenant=tenant))
    return [job for job in jobs if _job_has_worker(job, worker_id)]


def _compute_worker_financials(worker, jobs):
    job_ids = [job.id for job in jobs if job]
    transactions = WorkerPayoutTransaction.objects.filter(worker=worker)
    if job_ids:
        transactions = transactions.filter(Q(vehicle_job_id__in=job_ids) | Q(vehicle_job__isnull=True))
    else:
        transactions = transactions.none()

    aggregates = transactions.aggregate(
        bonus_total=Coalesce(
            Sum('amount', filter=Q(kind=WorkerPayoutTransaction.Kind.BONUS)),
            Value(Decimal('0')),
        ),
        penalty_total=Coalesce(
            Sum('amount', filter=Q(kind=WorkerPayoutTransaction.Kind.PENALTY)),
            Value(Decimal('0')),
        ),
        wage_paid_total=Coalesce(
            Sum('amount', filter=Q(kind=WorkerPayoutTransaction.Kind.WAGE_PAYMENT)),
            Value(Decimal('0')),
        ),
        tip_paid_total=Coalesce(
            Sum('amount', filter=Q(kind=WorkerPayoutTransaction.Kind.TIP_PAYMENT)),
            Value(Decimal('0')),
        ),
    )

    wage_total = sum((_job_worker_share_for(job, worker.id) for job in jobs), Decimal('0'))
    tip_total = sum((_job_worker_tip_for(job, worker.id) for job in jobs), Decimal('0'))
    payable_total = wage_total + _normalize_decimal(aggregates['bonus_total']) - _normalize_decimal(aggregates['penalty_total']) - _normalize_decimal(aggregates['wage_paid_total'])
    if payable_total < 0:
        payable_total = Decimal('0')
    tip_balance = tip_total - _normalize_decimal(aggregates['tip_paid_total'])
    if tip_balance < 0:
        tip_balance = Decimal('0')

    return {
        'wage_total': wage_total,
        'tip_total': tip_total,
        'bonus_total': _normalize_decimal(aggregates['bonus_total']),
        'penalty_total': _normalize_decimal(aggregates['penalty_total']),
        'wage_paid_total': _normalize_decimal(aggregates['wage_paid_total']),
        'tip_paid_total': _normalize_decimal(aggregates['tip_paid_total']),
        'payable_total': payable_total,
        'tip_balance': tip_balance,
        'transactions': transactions.select_related('vehicle_job').order_by('-created_at', '-id'),
    }


def _compute_all_workers_totals(tenant, jobs):
    workers_map = {}
    for job in jobs:
        for worker_id in _job_worker_ids(job):
            if worker_id not in workers_map:
                workers_map[worker_id] = WorkerProfile.objects.select_related('user').filter(
                    id=worker_id,
                    tenant=tenant,
                ).first()
    workers = [item for item in workers_map.values() if item]
    total_payable = Decimal('0')
    total_bonus = Decimal('0')
    total_penalty = Decimal('0')
    for worker in workers:
        state = _compute_worker_financials(worker, [job for job in jobs if _job_has_worker(job, worker.id)])
        total_payable += state['payable_total']
        total_bonus += state['bonus_total']
        total_penalty += state['penalty_total']
    return {
        'payable_total': total_payable,
        'bonus_total': total_bonus,
        'penalty_total': total_penalty,
    }


class ReportsDashboardView(APIView):
    @staticmethod
    def _base_queryset(tenant):
        return VehicleEntry.objects.select_related(
            'job',
            'job__assigned_worker',
            'job__assigned_worker__user',
            'customer',
        ).prefetch_related('job__product_lines__product', 'job__service_lines__service', 'payments').filter(tenant=tenant)

    @classmethod
    def _build_filtered_vehicles(cls, start, end, query, tenant, worker_id=None, plate_number='', plate_type=''):
        vehicles = cls._base_queryset(tenant)
        if start:
            vehicles = vehicles.filter(check_in_at__gte=start)
        if end:
            vehicles = vehicles.filter(check_in_at__lte=end)
        if query:
            vehicles = vehicles.filter(
                Q(driver_name__icontains=query)
                | Q(driver_phone__icontains=query)
                | Q(car_model__icontains=query)
                | Q(plate_number__icontains=query)
                | Q(job__assigned_worker__user__full_name__icontains=query)
                | Q(job__assigned_worker__user__username__icontains=query)
            ).distinct()
        if plate_number:
            vehicles = vehicles.filter(plate_number__icontains=plate_number)
        if plate_type in {'car', 'motorcycle'}:
            vehicles = vehicles.filter(plate_type=plate_type)

        records = list(vehicles.order_by('-check_in_at'))
        if worker_id:
            records = [vehicle for vehicle in records if _job_has_worker(getattr(vehicle, 'job', None), worker_id)]
        return records

    def get(self, request):
        start = _parse_dt(request.query_params.get('start'))
        end = _parse_dt(request.query_params.get('end'), end_of_day=True)
        query = request.query_params.get('q', '').strip()
        plate_number = request.query_params.get('plate_number', '').strip()
        plate_left = request.query_params.get('plate_left', '').strip()
        plate_letter = request.query_params.get('plate_letter', '').strip()
        plate_mid = request.query_params.get('plate_mid', '').strip()
        plate_right = request.query_params.get('plate_right', '').strip()
        plate_type = request.query_params.get('plate_type', '').strip().lower()
        if not plate_number:
            plate_parts = [plate_left, plate_letter, plate_mid, plate_right]
            plate_number = ' '.join([part for part in plate_parts if part])
        tenant = getattr(request.user, 'tenant', None)
        worker_id = request.query_params.get('worker_id')
        try:
            worker_id = int(worker_id) if worker_id else None
        except (TypeError, ValueError):
            worker_id = None

        vehicles = self._build_filtered_vehicles(
            start=start,
            end=end,
            query=query,
            tenant=tenant,
            worker_id=worker_id,
            plate_number=plate_number,
            plate_type=plate_type,
        )

        rows = []
        worker_jobs = []
        job_ids = [vehicle.job.id for vehicle in vehicles if getattr(vehicle, 'job', None)]
        adjustment_map = {}
        if job_ids:
            adjustment_rows = (
                WorkerPayoutTransaction.objects
                .filter(tenant=tenant, vehicle_job_id__in=job_ids, kind__in=[
                    WorkerPayoutTransaction.Kind.BONUS,
                    WorkerPayoutTransaction.Kind.PENALTY,
                ])
                .values('vehicle_job_id', 'kind')
                .annotate(total=Coalesce(Sum('amount'), Value(Decimal('0'))))
            )
            for item in adjustment_rows:
                job_id = int(item['vehicle_job_id'])
                if job_id not in adjustment_map:
                    adjustment_map[job_id] = {'bonus_total': Decimal('0'), 'penalty_total': Decimal('0')}
                adjustment_map[job_id][f"{item['kind']}_total"] = _normalize_decimal(item['total'])
        for idx, vehicle in enumerate(vehicles, start=1):
            job = getattr(vehicle, 'job', None)
            if worker_id and job and _job_has_worker(job, worker_id):
                worker_jobs.append(job)
            job_adjustments = adjustment_map.get(job.id if job else 0, {'bonus_total': Decimal('0'), 'penalty_total': Decimal('0')})
            product_names = []
            service_names = []
            if job:
                for line in job.product_lines.all():
                    if line.quantity and line.quantity > 0 and line.product:
                        product_names.append(line.product.name)
                for line in job.service_lines.all():
                    if line.quantity and line.quantity > 0:
                        service_names.append(line.custom_service_name or (line.service.name if line.service else 'خدمت'))
            row = {
                'row': idx,
                'vehicle_id': vehicle.id,
                'driver_name': vehicle.driver_name,
                'driver_phone': vehicle.driver_phone,
                'car_model': vehicle.car_model,
                'car_color': vehicle.car_color,
                'plate_number': vehicle.plate_number,
                'plate_left': vehicle.plate_left,
                'plate_letter': vehicle.plate_letter,
                'plate_mid': vehicle.plate_mid,
                'plate_right': vehicle.plate_right,
                'plate_type': vehicle.plate_type,
                'status': vehicle.status,
                'carwash_share': float(job.carwash_share_amount) if job else 0,
                'worker_share': float(job.worker_share_amount) if job else 0,
                'bonus_total': float(job_adjustments['bonus_total']),
                'penalty_total': float(job_adjustments['penalty_total']),
                'discount_total': float(job.discount_total) if job else 0,
                'tip_amount': float(job.tip_amount) if job else 0,
                'worker_name': _worker_name(job.assigned_worker) if job else '-',
                'products': ', '.join(product_names),
                'services': ', '.join(service_names),
                'created_at': vehicle.check_in_at,
            }
            rows.append(row)

        total_carwash = sum((_normalize_decimal(getattr(vehicle.job, 'carwash_share_amount', 0)) for vehicle in vehicles if getattr(vehicle, 'job', None)), Decimal('0'))
        total_worker = sum((_normalize_decimal(getattr(vehicle.job, 'worker_share_amount', 0)) for vehicle in vehicles if getattr(vehicle, 'job', None)), Decimal('0'))
        total_tip = sum((_normalize_decimal(getattr(vehicle.job, 'tip_amount', 0)) for vehicle in vehicles if getattr(vehicle, 'job', None)), Decimal('0'))
        total_discount = sum((_normalize_decimal(getattr(vehicle.job, 'discount_total', 0)) for vehicle in vehicles if getattr(vehicle, 'job', None)), Decimal('0'))
        all_jobs = [vehicle.job for vehicle in vehicles if getattr(vehicle, 'job', None)]
        all_workers_totals = _compute_all_workers_totals(tenant, all_jobs)

        carwash_report = [{
            'row': i + 1,
            'vehicle_id': r['vehicle_id'],
            'driver_name': r['driver_name'],
            'driver_phone': r['driver_phone'],
            'car_model': r['car_model'],
            'car_color': r['car_color'],
            'plate_number': r['plate_number'],
            'plate_left': r['plate_left'],
            'plate_letter': r['plate_letter'],
            'plate_mid': r['plate_mid'],
            'plate_right': r['plate_right'],
            'plate_type': r['plate_type'],
            'carwash_share': r['carwash_share'],
            'worker_name': r['worker_name'],
            'created_at': r['created_at'],
        } for i, r in enumerate(rows)]

        worker_report = [{
            'row': i + 1,
            'vehicle_id': r['vehicle_id'],
            'driver_name': r['driver_name'],
            'driver_phone': r['driver_phone'],
            'car_model': r['car_model'],
            'plate_number': r['plate_number'],
            'plate_left': r['plate_left'],
            'plate_letter': r['plate_letter'],
            'plate_mid': r['plate_mid'],
            'plate_right': r['plate_right'],
            'plate_type': r['plate_type'],
            'worker_share': r['worker_share'],
            'bonus_total': r['bonus_total'],
            'penalty_total': r['penalty_total'],
            'worker_name': r['worker_name'],
            'created_at': r['created_at'],
        } for i, r in enumerate(rows)]

        tips_report = [{
            'row': i + 1,
            'vehicle_id': r['vehicle_id'],
            'driver_name': r['driver_name'],
            'driver_phone': r['driver_phone'],
            'car_model': r['car_model'],
            'plate_number': r['plate_number'],
            'plate_left': r['plate_left'],
            'plate_letter': r['plate_letter'],
            'plate_mid': r['plate_mid'],
            'plate_right': r['plate_right'],
            'plate_type': r['plate_type'],
            'tip_amount': r['tip_amount'],
            'worker_name': r['worker_name'],
            'products': r['products'],
            'created_at': r['created_at'],
        } for i, r in enumerate(rows)]

        revenue_report = []
        revenue_total = Decimal('0')
        for i, vehicle in enumerate(vehicles, start=1):
            payments = list(vehicle.payments.all()) if hasattr(vehicle, 'payments') else []
            payment = payments[0] if payments else None
            if not payment:
                continue
            received_amount = _normalize_decimal(payment.amount) if payment.status == Payment.Status.SUCCESS else Decimal('0')
            outstanding_amount = max(Decimal('0'), _normalize_decimal(payment.amount) - received_amount)
            revenue_total += received_amount
            revenue_report.append({
                'row': len(revenue_report) + 1,
                'vehicle_id': vehicle.id,
                'driver_name': vehicle.driver_name,
                'driver_phone': vehicle.driver_phone,
                'car_model': vehicle.car_model,
                'car_color': vehicle.car_color,
                'plate_number': vehicle.plate_number,
                'plate_left': vehicle.plate_left,
                'plate_letter': vehicle.plate_letter,
                'plate_mid': vehicle.plate_mid,
                'plate_right': vehicle.plate_right,
                'plate_type': vehicle.plate_type,
                'payment_method': payment.method,
                'payment_status': payment.status,
                'service_amount': float(payment.service_amount or 0),
                'product_amount': float(payment.product_amount or 0),
                'discount_amount': float(payment.discount_amount or 0),
                'tip_amount': float(payment.tip_amount or 0),
                'final_total': float(payment.amount or 0),
                'received_amount': float(received_amount),
                'outstanding_amount': float(outstanding_amount),
                'cheque_number': payment.cheque_number,
                'reminder_due_at': payment.reminder_due_at,
                'created_at': payment.created_at,
            })

        attendances = WorkerAttendance.objects.select_related('worker', 'worker__user').filter(tenant=tenant)
        if start:
            attendances = attendances.filter(event_at__gte=start)
        if end:
            attendances = attendances.filter(event_at__lte=end)
        if query:
            attendances = attendances.filter(
                Q(worker__user__full_name__icontains=query) | Q(worker__user__username__icontains=query)
            )
        if worker_id:
            attendances = attendances.filter(worker_id=worker_id)

        attendance_rows = [{
            'row': i,
            'worker_name': _worker_name(event.worker),
            'event_type': event.event_type,
            'event_at': event.event_at,
            'source': event.source,
        } for i, event in enumerate(attendances.order_by('-event_at'), start=1)]

        selected_worker_summary = None
        selected_worker_transactions = []
        if worker_id:
            worker = WorkerProfile.objects.select_related('user').filter(id=worker_id, tenant=tenant).first()
            if worker:
                worker_state = _compute_worker_financials(worker, worker_jobs)
                selected_worker_summary = {
                    'worker_id': worker.id,
                    'worker_name': _worker_name(worker),
                    'wage_total': float(worker_state['wage_total']),
                    'tip_total': float(worker_state['tip_total']),
                    'bonus_total': float(worker_state['bonus_total']),
                    'penalty_total': float(worker_state['penalty_total']),
                    'wage_paid_total': float(worker_state['wage_paid_total']),
                    'tip_paid_total': float(worker_state['tip_paid_total']),
                    'payable_total': float(worker_state['payable_total']),
                    'tip_balance': float(worker_state['tip_balance']),
                }
                selected_worker_transactions = [
                    {
                        'id': tx.id,
                        'kind': tx.kind,
                        'amount': float(tx.amount or 0),
                        'note': tx.note,
                        'vehicle_job_id': tx.vehicle_job_id,
                        'created_at': tx.created_at,
                    }
                    for tx in worker_state['transactions'][:100]
                ]

        return Response({
            'filters': {
                'start': request.query_params.get('start'),
                'end': request.query_params.get('end'),
                'q': query,
                'worker_id': worker_id,
                'plate_number': plate_number,
                'plate_left': plate_left,
                'plate_letter': plate_letter,
                'plate_mid': plate_mid,
                'plate_right': plate_right,
                'plate_type': plate_type,
            },
            'summary': {
                'vehicles_count': len(rows),
                'carwash_total': float(total_carwash),
                'worker_total': float(total_worker),
                'tips_total': float(total_tip),
                'discount_total': float(total_discount),
                'payable_worker_total': float(all_workers_totals['payable_total']),
                'payable_tip_total': float(selected_worker_summary['tip_balance']) if selected_worker_summary else 0,
                'bonus_total': float(all_workers_totals['bonus_total']),
                'penalty_total': float(all_workers_totals['penalty_total']),
            },
            'section_totals': {
                'overall': {
                    'vehicles_count': len(rows),
                    'carwash_total': float(total_carwash),
                    'worker_total': float(total_worker),
                    'tips_total': float(total_tip),
                    'discount_total': float(total_discount),
                },
                'carwash': {'carwash_total': float(total_carwash)},
                'worker': {
                    'worker_total': float(total_worker),
                    'payable_total': float(all_workers_totals['payable_total']),
                    'bonus_total': float(all_workers_totals['bonus_total']),
                    'penalty_total': float(all_workers_totals['penalty_total']),
                },
                'tips': {'tips_total': float(total_tip)},
                'attendance': {'count': len(attendance_rows)},
                'revenue': {'revenue_total': float(revenue_total), 'count': len(revenue_report)},
            },
            'overall_report': rows,
            'carwash_report': carwash_report,
            'worker_report': worker_report,
            'tips_report': tips_report,
            'attendance_report': attendance_rows,
            'revenue_report': revenue_report,
            'selected_worker_summary': selected_worker_summary,
            'selected_worker_transactions': selected_worker_transactions,
        })


class ReportsWorkerPayoutView(APIView):
    def post(self, request):
        tenant = getattr(request.user, 'tenant', None)
        worker_id = request.data.get('worker_id')
        mode = str(request.data.get('mode', 'full')).strip().lower()
        note = str(request.data.get('note', '')).strip()
        try:
            worker_id = int(worker_id)
        except (TypeError, ValueError):
            return Response({'worker_id': ['Invalid worker.']}, status=status.HTTP_400_BAD_REQUEST)
        if mode not in {'full', 'partial'}:
            return Response({'mode': ['Invalid mode.']}, status=status.HTTP_400_BAD_REQUEST)

        worker = WorkerProfile.objects.select_related('user').filter(id=worker_id, tenant=tenant).first()
        if not worker:
            return Response({'worker_id': ['Worker not found.']}, status=status.HTTP_404_NOT_FOUND)

        jobs = _get_worker_jobs(tenant, worker_id)
        worker_state = _compute_worker_financials(worker, jobs)
        payable_total = worker_state['payable_total']
        if payable_total <= 0:
            return Response({'detail': 'مانده حقوقی برای پرداخت وجود ندارد.'}, status=status.HTTP_400_BAD_REQUEST)

        if mode == 'full':
            amount = payable_total
        else:
            amount = _normalize_decimal(request.data.get('amount'))
            if amount <= 0:
                return Response({'amount': ['مبلغ باید بیشتر از صفر باشد.']}, status=status.HTTP_400_BAD_REQUEST)
            if amount > payable_total:
                amount = payable_total

        tx = WorkerPayoutTransaction.objects.create(
            tenant=tenant,
            worker=worker,
            kind=WorkerPayoutTransaction.Kind.WAGE_PAYMENT,
            amount=amount,
            note=note or ('پرداخت کامل حقوق' if mode == 'full' else 'پرداخت بخشی از حقوق'),
            created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
        )

        remaining = payable_total - amount
        if remaining < 0:
            remaining = Decimal('0')
        return Response({
            'detail': 'پرداخت حقوق ثبت شد.',
            'transaction_id': tx.id,
            'paid_amount': float(amount),
            'remaining_payable': float(remaining),
        })


class ReportsWorkerAdjustmentView(APIView):
    def post(self, request):
        tenant = getattr(request.user, 'tenant', None)
        worker_id = request.data.get('worker_id')
        vehicle_job_id = request.data.get('vehicle_job_id')
        kind = str(request.data.get('kind', '')).strip().lower()
        note = str(request.data.get('note', '')).strip()
        amount = _normalize_decimal(request.data.get('amount'))

        try:
            worker_id = int(worker_id)
        except (TypeError, ValueError):
            return Response({'worker_id': ['Invalid worker.']}, status=status.HTTP_400_BAD_REQUEST)
        if kind not in {WorkerPayoutTransaction.Kind.BONUS, WorkerPayoutTransaction.Kind.PENALTY}:
            return Response({'kind': ['Invalid adjustment kind.']}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({'amount': ['مبلغ باید بیشتر از صفر باشد.']}, status=status.HTTP_400_BAD_REQUEST)

        worker = WorkerProfile.objects.select_related('user').filter(id=worker_id, tenant=tenant).first()
        if not worker:
            return Response({'worker_id': ['Worker not found.']}, status=status.HTTP_404_NOT_FOUND)

        vehicle_job = None
        if vehicle_job_id:
            vehicle_job = VehicleJob.objects.filter(id=vehicle_job_id, tenant=tenant).first()

        if kind == WorkerPayoutTransaction.Kind.PENALTY:
            jobs = _get_worker_jobs(tenant, worker_id)
            worker_state = _compute_worker_financials(worker, jobs)
            amount = min(amount, worker_state['payable_total'])

        tx = WorkerPayoutTransaction.objects.create(
            tenant=tenant,
            worker=worker,
            vehicle_job=vehicle_job,
            kind=kind,
            amount=amount,
            note=note,
            created_by=request.user if getattr(request.user, 'is_authenticated', False) else None,
        )
        return Response({
            'detail': 'تعدیل حقوق ثبت شد.',
            'transaction_id': tx.id,
            'amount': float(amount),
            'kind': kind,
        }, status=status.HTTP_201_CREATED)


class ReportsPayoutSettleView(APIView):
    def post(self, request):
        return Response(
            {'detail': 'این endpoint منسوخ شده است. از /reports/workers/payouts/ استفاده کنید.'},
            status=status.HTTP_410_GONE,
        )
