from datetime import datetime, time
from decimal import Decimal

from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.vehicles.models import VehicleEntry, VehicleJob
from apps.workers.models import WorkerAttendance


def _parse_dt(value, end_of_day=False):
    if not value:
        return None
    dt = datetime.strptime(value, '%Y-%m-%d')
    if end_of_day:
        dt = datetime.combine(dt.date(), time.max)
    else:
        dt = datetime.combine(dt.date(), time.min)
    return timezone.make_aware(dt)


class ReportsDashboardView(APIView):
    @staticmethod
    def _build_filtered_vehicles(start, end, query, tenant):
        vehicles = VehicleEntry.objects.select_related(
            'job',
            'job__assigned_worker',
            'job__assigned_worker__user',
        ).prefetch_related('job__product_lines__product').filter(tenant=tenant)
        if start:
            vehicles = vehicles.filter(check_in_at__gte=start)
        if end:
            vehicles = vehicles.filter(check_in_at__lte=end)
        if query:
            search_filter = (
                Q(driver_name__icontains=query)
                | Q(driver_phone__icontains=query)
                | Q(car_model__icontains=query)
                | Q(plate_number__icontains=query)
                | Q(job__assigned_worker__user__full_name__icontains=query)
                | Q(job__assigned_worker__user__username__icontains=query)
            )
            vehicles = vehicles.filter(search_filter).distinct()
        return vehicles

    def get(self, request):
        start = _parse_dt(request.query_params.get('start'))
        end = _parse_dt(request.query_params.get('end'), end_of_day=True)
        query = request.query_params.get('q', '').strip()
        tenant = getattr(request.user, 'tenant', None)

        vehicles = self._build_filtered_vehicles(start=start, end=end, query=query, tenant=tenant)

        rows = []
        for idx, vehicle in enumerate(vehicles.order_by('-check_in_at'), start=1):
            job = getattr(vehicle, 'job', None)
            product_names = []
            if job:
                for line in job.product_lines.all():
                    if line.quantity and line.quantity > 0 and line.product:
                        product_names.append(line.product.name)
            rows.append({
                'row': idx,
                'vehicle_id': vehicle.id,
                'driver_name': vehicle.driver_name,
                'driver_phone': vehicle.driver_phone,
                'car_model': vehicle.car_model,
                'plate_number': vehicle.plate_number,
                'carwash_share': float(job.carwash_share_amount) if job else 0,
                'worker_share': float(job.worker_share_amount) if job else 0,
                'tip_amount': float(job.tip_amount) if job else 0,
                'worker_name': (job.assigned_worker.user.full_name or job.assigned_worker.user.username) if job and job.assigned_worker and job.assigned_worker.user else '-',
                'products': ', '.join(product_names),
                'created_at': vehicle.check_in_at,
            })

        totals = vehicles.aggregate(
            total_carwash=Coalesce(Sum('job__carwash_share_amount'), Value(Decimal('0'))),
            total_worker=Coalesce(Sum('job__worker_share_amount'), Value(Decimal('0'))),
            total_tip=Coalesce(Sum('job__tip_amount'), Value(Decimal('0'))),
        )
        payout_scope = VehicleJob.objects.filter(
            vehicle__in=vehicles,
            vehicle__status=VehicleEntry.Status.RELEASED,
        )
        payout_totals = payout_scope.aggregate(
            payable_worker_total=Coalesce(
                Sum(
                    'worker_share_amount',
                    filter=Q(worker_share_paid_at__isnull=True),
                ),
                Value(Decimal('0')),
            ),
            payable_tip_total=Coalesce(
                Sum(
                    Coalesce('workers_tip_share_amount', 'tip_amount'),
                    filter=Q(tip_paid_at__isnull=True),
                ),
                Value(Decimal('0')),
            ),
        )

        carwash_report = [{
            'row': i + 1,
            'driver_name': r['driver_name'],
            'driver_phone': r['driver_phone'],
            'car_model': r['car_model'],
            'plate_number': r['plate_number'],
            'carwash_share': r['carwash_share'],
            'worker_name': r['worker_name'],
            'created_at': r['created_at'],
        } for i, r in enumerate(rows)]

        worker_report = [{
            'row': i + 1,
            'driver_name': r['driver_name'],
            'driver_phone': r['driver_phone'],
            'car_model': r['car_model'],
            'plate_number': r['plate_number'],
            'worker_share': r['worker_share'],
            'worker_name': r['worker_name'],
            'created_at': r['created_at'],
        } for i, r in enumerate(rows)]

        tips_report = [{
            'row': i + 1,
            'driver_name': r['driver_name'],
            'driver_phone': r['driver_phone'],
            'car_model': r['car_model'],
            'plate_number': r['plate_number'],
            'tip_amount': r['tip_amount'],
            'worker_name': r['worker_name'],
            'products': r['products'],
            'created_at': r['created_at'],
        } for i, r in enumerate(rows)]

        attendances = WorkerAttendance.objects.select_related('worker', 'worker__user').filter(tenant=tenant)
        if start:
            attendances = attendances.filter(event_at__gte=start)
        if end:
            attendances = attendances.filter(event_at__lte=end)
        if query:
            attendances = attendances.filter(worker__user__full_name__icontains=query)

        attendance_rows = []
        for i, event in enumerate(attendances.order_by('-event_at'), start=1):
            user = event.worker.user if event.worker else None
            attendance_rows.append({
                'row': i,
                'worker_name': (user.full_name or user.username) if user else '-',
                'event_type': event.event_type,
                'event_at': event.event_at,
                'source': event.source,
            })

        return Response({
            'filters': {'start': request.query_params.get('start'), 'end': request.query_params.get('end'), 'q': query},
            'summary': {
                'vehicles_count': len(rows),
                'carwash_total': float(totals['total_carwash']),
                'worker_total': float(totals['total_worker']),
                'tips_total': float(totals['total_tip']),
                'payable_worker_total': float(payout_totals['payable_worker_total']),
                'payable_tip_total': float(payout_totals['payable_tip_total']),
            },
            'overall_report': rows,
            'carwash_report': carwash_report,
            'worker_report': worker_report,
            'tips_report': tips_report,
            'attendance_report': attendance_rows,
        })


class ReportsPayoutSettleView(APIView):
    def post(self, request):
        kind = str(request.data.get('kind', '')).strip().lower()
        if kind not in {'worker', 'tips'}:
            return Response(
                {'kind': ['Invalid settlement kind. Use "worker" or "tips".']},
                status=400,
            )

        start = _parse_dt(request.data.get('start') or request.query_params.get('start'))
        end = _parse_dt(
            request.data.get('end') or request.query_params.get('end'),
            end_of_day=True,
        )
        query = str(request.data.get('q', request.query_params.get('q', ''))).strip()

        vehicles = ReportsDashboardView._build_filtered_vehicles(
            start=start,
            end=end,
            query=query,
            tenant=getattr(request.user, 'tenant', None),
        )
        jobs = VehicleJob.objects.filter(
            vehicle__in=vehicles,
            vehicle__status=VehicleEntry.Status.RELEASED,
        )

        if kind == 'worker':
            target_jobs = jobs.filter(
                worker_share_paid_at__isnull=True,
                worker_share_amount__gt=0,
            )
            settled_total = target_jobs.aggregate(
                total=Coalesce(Sum('worker_share_amount'), Value(Decimal('0')))
            )['total']
            target_jobs.update(worker_share_paid_at=timezone.now())
        else:
            target_jobs = jobs.filter(
                tip_paid_at__isnull=True,
            ).filter(
                Q(workers_tip_share_amount__gt=0) | Q(tip_amount__gt=0)
            )
            settled_total = target_jobs.aggregate(
                total=Coalesce(
                    Sum(Coalesce('workers_tip_share_amount', 'tip_amount')),
                    Value(Decimal('0')),
                )
            )['total']
            target_jobs.update(tip_paid_at=timezone.now())

        remaining_totals = jobs.aggregate(
            payable_worker_total=Coalesce(
                Sum('worker_share_amount', filter=Q(worker_share_paid_at__isnull=True)),
                Value(Decimal('0')),
            ),
            payable_tip_total=Coalesce(
                Sum(
                    Coalesce('workers_tip_share_amount', 'tip_amount'),
                    filter=Q(tip_paid_at__isnull=True),
                ),
                Value(Decimal('0')),
            ),
        )

        return Response(
            {
                'kind': kind,
                'settled_total': float(settled_total or 0),
                'payable_worker_total': float(
                    remaining_totals['payable_worker_total'] or 0
                ),
                'payable_tip_total': float(remaining_totals['payable_tip_total'] or 0),
            }
        )
