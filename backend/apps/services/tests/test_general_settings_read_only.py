from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.auth.models import CarWash
from apps.services.models import GeneralSettings


class GeneralSettingsReadOnlyTests(TestCase):
    def setUp(self):
        self.tenant = CarWash.objects.create(name='Read Only Settings Wash', slug='read-only-settings-wash')
        self.tenant.trial_started_at = timezone.now() - timedelta(minutes=1)
        self.tenant.trial_ends_at = timezone.now() + timedelta(days=1)
        self.tenant.save(update_fields=['trial_started_at', 'trial_ends_at'])
        self.user = get_user_model().objects.create_user(
            username='settings-read-only', password='pass12345', phone='09121110141', tenant=self.tenant,
        )
        self.client.force_login(self.user)

    def test_get_returns_defaults_without_creating_or_normalizing_a_row(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/api/services/general-settings/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(GeneralSettings.objects.filter(tenant=self.tenant).count(), 0)
        writes = [
            query['sql'] for query in queries.captured_queries
            if query['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE'))
        ]
        self.assertEqual(writes, [])
        self.assertIn('sms_vehicle_assigned_template', response.json())
