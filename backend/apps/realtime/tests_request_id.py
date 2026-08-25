from django.test import TestCase


class RequestIdMiddlewareTests(TestCase):
    def test_health_generates_and_echoes_a_safe_request_id(self):
        generated = self.client.get('/api/health/')
        self.assertRegex(generated['X-Request-ID'], r'^[a-f0-9]{32}$')
        supplied = self.client.get('/api/health/', HTTP_X_REQUEST_ID='staging-run-20260825')
        self.assertEqual(supplied['X-Request-ID'], 'staging-run-20260825')
