from decimal import Decimal

from django.test import SimpleTestCase

from apps.vehicles.shares import carwash_remainder, net_services_pool, worker_commission_pool


class ShareSplitTests(SimpleTestCase):
    def test_loyalty_discount_does_not_reduce_worker_pool(self):
        worker_pool = worker_commission_pool(1000000, manual_discount_total=0)
        self.assertEqual(worker_pool, Decimal('1000000.00'))

        net_pool = net_services_pool(
            1000000,
            loyalty_discount_total=200000,
            manual_discount_total=0,
        )
        self.assertEqual(net_pool, Decimal('800000.00'))

        worker_share = worker_pool * Decimal('40') / Decimal('100')
        carwash = carwash_remainder(
            worker_pool,
            worker_share,
            loyalty_discount_total=200000,
        )
        self.assertEqual(worker_share, Decimal('400000'))
        self.assertEqual(carwash, Decimal('400000.00'))

    def test_manual_discount_still_reduces_worker_pool(self):
        worker_pool = worker_commission_pool(1000000, manual_discount_total=100000)
        self.assertEqual(worker_pool, Decimal('900000.00'))

    def test_loyalty_can_zero_carwash_without_cutting_worker(self):
        worker_pool = worker_commission_pool(1000000, manual_discount_total=0)
        worker_share = Decimal('800000.00')
        carwash = carwash_remainder(
            worker_pool,
            worker_share,
            loyalty_discount_total=300000,
        )
        self.assertEqual(carwash, Decimal('0.00'))
