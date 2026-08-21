from django.contrib.auth import get_user_model
from django.test.utils import CaptureQueriesContext
from django.db import connection
from rest_framework.test import APIClient, APITestCase

from apps.auth.models import CarWash
from apps.vehicles.models import VehicleEntry, VehicleJob
from apps.workers.models import WorkerProfile


class VehicleListQueryBudgetTests(APITestCase):
    """Guards the operator dashboard against per-row query regressions.

    The vehicle list is unpaginated and refreshed on a timer, so a lookup that
    runs once per card is what turns a busy day into a multi-second load.
    """

    def setUp(self):
        user_model = get_user_model()
        self.client = APIClient()
        self.tenant = CarWash.objects.create(name='Budget Wash', slug='budget-wash')
        self.manager = user_model.objects.create_user(
            username='budget_manager',
            password='pass12345',
            phone='09121110001',
            role='manager',
            tenant=self.tenant,
        )
        worker_user = user_model.objects.create_user(
            username='budget_worker',
            password='pass12345',
            phone='09121110002',
            role='worker',
            tenant=self.tenant,
            full_name='Budget Worker',
        )
        self.worker = WorkerProfile.objects.create(user=worker_user, tenant=self.tenant)

    def _create_vehicles(self, count):
        for index in range(count):
            vehicle = VehicleEntry.objects.create(
                tenant=self.tenant,
                plate_number=f'11 ب {index:03d} 11',
                plate_left='11',
                plate_letter='ب',
                plate_mid=f'{index:03d}',
                plate_right='11',
                car_model='Pride',
                car_color='White',
                driver_name=f'Driver {index}',
                driver_phone=f'0912000{index:04d}',
                status=VehicleEntry.Status.RELEASED,
                loyalty_score_snapshot=0,
                loyalty_visit_count_snapshot=1,
                loyalty_discount_percent_snapshot=0,
            )
            VehicleJob.objects.create(
                tenant=self.tenant,
                vehicle=vehicle,
                assigned_worker=self.worker,
                assigned_workers_snapshot=[{
                    'id': self.worker.id,
                    'name': 'Budget Worker',
                    'worker_share_percent': 100,
                }],
            )

    def _count_queries_for_list(self):
        self.client.force_authenticate(self.manager)
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get('/api/vehicles/')
        self.assertEqual(response.status_code, 200)
        return len(captured), len(response.data)

    def test_query_count_does_not_grow_with_vehicle_count(self):
        self._create_vehicles(5)
        small_queries, small_rows = self._count_queries_for_list()
        self.assertEqual(small_rows, 5)

        self._create_vehicles(25)
        large_queries, large_rows = self._count_queries_for_list()
        self.assertEqual(large_rows, 30)

        # 25 extra cards may add a little work, but nowhere near a lookup each.
        self.assertLess(large_queries - small_queries, 10)

    def test_listing_does_not_write(self):
        self._create_vehicles(5)
        self.client.force_authenticate(self.manager)
        with CaptureQueriesContext(connection) as captured:
            self.client.get('/api/vehicles/')
        writes = [
            query['sql'] for query in captured
            if query['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE'))
        ]
        self.assertEqual(writes, [])
