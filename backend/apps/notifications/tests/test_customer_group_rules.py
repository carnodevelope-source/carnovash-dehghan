from django.test import SimpleTestCase

from apps.notifications.services import customer_matches_rules


class CustomerGroupRulesTests(SimpleTestCase):
    def test_min_spent_rule_uses_direct_amount(self):
        customer = {
            'orders_count': 3,
            'total_spent': 1_500_000,
            'score': 4.2,
            'carwash_name': 'کارواش یک',
        }

        self.assertTrue(customer_matches_rules(customer, {'minSpent': 1_000_000}))
        self.assertFalse(customer_matches_rules(customer, {'minSpent': 2_000_000}))
