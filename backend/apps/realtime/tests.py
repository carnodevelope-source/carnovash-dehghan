from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from django.test import RequestFactory, TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.auth.models import CarWash
from apps.live import _Subscriber, _event_stream, _deliver, publish_live_event
from apps.realtime.idempotency import IdempotencyMiddleware, _request_hash
from apps.realtime.models import IdempotencyRecord, LiveOutbox
from apps.realtime.transactions import TransactionalLiveModelMixin
from apps.vehicles.models import VehicleEntry
from apps.vehicles.models import BlockedPlate, VehicleStatusLog
from apps.workers.models import WorkerAttendance, WorkerProfile
from apps.services.models import GeneralSettings, Service, ServiceCategory
from apps.inventory.models import ExpenseEntry, InventoryItem, StockMovement
from apps.products.models import Product, ProductCategory
from apps.subscriptions.models import ServiceOrder, ServicePaymentRecord, ServiceSubscription
from apps.auth.models import CarWashFeaturePurchase, SupportTicket, SupportTicketMessage
from apps.notifications.models import CustomerGroup, ImportedCustomer, NotificationLog, SmsTemplate
from apps.payments.models import CashflowTransaction, Payment, WalletGatewayRequest


@override_settings(LIVE_OUTBOX_ENABLED=True, LIVE_V2_ENABLED=True, LIVE_REPLAY_ENABLED=True)
class LiveOutboxTests(TestCase):
    def setUp(self):
        self.tenant = CarWash.objects.create(name='Realtime Wash', slug='realtime-wash')
        self.tenant.trial_started_at = timezone.now() - timedelta(minutes=1)
        self.tenant.trial_ends_at = timezone.now() + timedelta(days=1)
        self.tenant.save(update_fields=['trial_started_at', 'trial_ends_at'])
        self.other_tenant = CarWash.objects.create(name='Other Realtime Wash', slug='other-realtime-wash')
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='realtime-user', password='pass12345', phone='09121110088', tenant=self.tenant, role='manager',
        )

    def test_outbox_write_and_publish_are_discarded_with_rollback(self):
        with patch('apps.live._deliver') as deliver:
            with self.assertRaisesRegex(RuntimeError, 'rollback'):
                with transaction.atomic():
                    self._create_vehicle('11 ب 101 11')
                    raise RuntimeError('rollback')
        self.assertEqual(VehicleEntry.objects.count(), 0)
        self.assertEqual(LiveOutbox.objects.count(), 0)
        deliver.assert_not_called()

    def test_outbox_envelope_has_durable_cursor(self):
        with patch('apps.live._deliver') as deliver:
            with self.captureOnCommitCallbacks(execute=True):
                vehicle = self._create_vehicle('11 ب 077 11')
        row = LiveOutbox.objects.get()
        event = deliver.call_args.args[0]
        self.assertEqual(event['event_id'], str(row.id))
        self.assertEqual(event['entity'], 'vehicle')
        self.assertEqual(event['entity_id'], str(vehicle.id))
        self.assertEqual(event['data']['tenant_id'], self.tenant.id)

    def test_outbox_publish_fails_fast_without_a_shared_transaction(self):
        connection = type('Connection', (), {'in_atomic_block': False})()
        with patch('apps.live.transaction.get_connection', return_value=connection):
            with self.assertRaisesRegex(RuntimeError, 'transaction.atomic'):
                publish_live_event('vehicle.updated', {'tenant_id': self.tenant.id, 'id': 1})
        self.assertEqual(LiveOutbox.objects.count(), 0)

    def test_every_signal_producer_uses_the_transactional_mixin(self):
        producers = (
            VehicleEntry, BlockedPlate, VehicleStatusLog, WorkerProfile, WorkerAttendance,
            ServiceCategory, Service, GeneralSettings, InventoryItem, StockMovement, ExpenseEntry,
            ProductCategory, Product, ServiceSubscription, ServiceOrder, ServicePaymentRecord,
            SupportTicket, SupportTicketMessage, CarWashFeaturePurchase, NotificationLog, SmsTemplate,
            CustomerGroup, ImportedCustomer, Payment, WalletGatewayRequest, CashflowTransaction,
        )
        self.assertTrue(all(issubclass(model, TransactionalLiveModelMixin) for model in producers))

    def test_sync_and_sse_replay_are_tenant_scoped(self):
        own = LiveOutbox.objects.create(
            tenant_id=self.tenant.id, event_type='vehicle.updated', entity_type='vehicle', entity_id='1', payload={'tenant_id': self.tenant.id, 'id': 1},
        )
        LiveOutbox.objects.create(
            tenant_id=self.other_tenant.id, event_type='vehicle.updated', entity_type='vehicle', entity_id='2', payload={'tenant_id': self.other_tenant.id, 'id': 2},
        )
        self.client.force_login(self.user)
        sync = self.client.get('/api/live/sync/?after=0')
        self.assertEqual(sync.status_code, 200)
        self.assertEqual([event['event_id'] for event in sync.json()['events']], [str(own.id)])
        revision = self.client.get('/api/live/revision/')
        self.assertEqual(revision.json()['latest_event_id'], str(own.id))

    def _create_vehicle(self, plate_number):
        return VehicleEntry.objects.create(
            tenant=self.tenant,
            plate_number=plate_number,
            car_model='Pride',
            car_color='White',
            driver_name='Realtime Driver',
            driver_phone='09121110077',
        )


@override_settings(LIVE_OUTBOX_ENABLED=True, LIVE_V2_ENABLED=True, LIVE_REPLAY_ENABLED=True)
class LiveReplayStreamTests(TransactionTestCase):
    reset_sequences = True

    def test_unwrapped_producer_save_opens_shared_business_and_outbox_transaction(self):
        tenant = CarWash.objects.create(name='Standalone Transaction Wash', slug='standalone-transaction-wash')
        with patch('apps.live._deliver') as deliver:
            vehicle = VehicleEntry.objects.create(
                tenant=tenant,
                plate_number='11 ب 808 11',
                car_model='Pride',
                car_color='White',
                driver_name='Standalone Driver',
                driver_phone='09121110111',
            )
        row = LiveOutbox.objects.get(entity_id=str(vehicle.id))
        self.assertEqual(row.tenant_id, tenant.id)
        deliver.assert_called_once()

    def test_sse_stream_replays_durable_events_after_cursor(self):
        row = LiveOutbox.objects.create(
            tenant_id=7, event_type='vehicle.updated', entity_type='vehicle', entity_id='8', payload={'tenant_id': 7, 'id': 8},
        )
        stream = _event_stream(_Subscriber(is_hq=False, tenant_id='7', user_id='1'), after_id=0)
        self.assertEqual(next(stream), 'retry: 5000\n\n')
        self.assertIn('live.connected', next(stream))
        self.assertIn(f'id: {row.id}', next(stream))
        stream.close()

    def test_redis_publish_failure_falls_back_to_local_delivery(self):
        relay = type('FailingRelay', (), {'publish': lambda _self, _event: False})()
        with patch('apps.live._relay', relay), patch('apps.live._fan_out') as fan_out:
            _deliver({'id': '1', 'type': 'vehicle.updated', 'data': {'tenant_id': 7}})
        fan_out.assert_called_once()


class IdempotencyMiddlewareTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.tenant = CarWash.objects.create(name='Idempotency Wash', slug='idempotency-wash')
        self.user = user_model.objects.create_user(
            username='idem-user', password='pass12345', phone='09121110099', tenant=self.tenant,
        )
        self.factory = RequestFactory()

    def _request(self, body):
        request = self.factory.post('/api/example/', data=body, content_type='application/json', HTTP_IDEMPOTENCY_KEY='key-1')
        request.user = self.user
        return request

    def test_same_key_and_body_replays_completed_json_response(self):
        calls = 0

        def view(_request):
            nonlocal calls
            calls += 1
            return JsonResponse({'ok': True}, status=201)

        handler = IdempotencyMiddleware(view)
        first = handler(self._request('{"amount":1}'))
        # A fresh middleware instance models a process restart between an
        # ambiguous timeout and the caller retrying the same request/key.
        replay = IdempotencyMiddleware(view)(self._request('{"amount":1}'))
        self.assertEqual(first.status_code, 201)
        self.assertEqual(replay.status_code, 201)
        self.assertEqual(replay['Idempotency-Replayed'], 'true')
        self.assertEqual(calls, 1)
        self.assertEqual(IdempotencyRecord.objects.count(), 1)

    def test_same_key_with_different_body_is_conflict(self):
        handler = IdempotencyMiddleware(lambda _request: JsonResponse({'ok': True}))
        handler(self._request('{"amount":1}'))
        conflict = handler(self._request('{"amount":2}'))
        self.assertEqual(conflict.status_code, 409)

    def test_pending_key_rejects_parallel_duplicate_before_view_runs(self):
        request = self._request('{"amount":1}')
        IdempotencyRecord.objects.create(
            tenant_id=self.tenant.id,
            user=self.user,
            key='key-1',
            method='POST',
            path='/api/example/',
            request_hash=_request_hash(request),
        )
        called = False

        def view(_request):
            nonlocal called
            called = True
            return JsonResponse({'ok': True})

        response = IdempotencyMiddleware(view)(request)
        self.assertEqual(response.status_code, 409)
        self.assertFalse(called)
