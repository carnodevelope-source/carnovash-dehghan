from django.test import TestCase

from apps.auth.models import CarWash, CarWashFeaturePurchase
from apps.auth.views import _build_hq_report_snapshot
from apps.payments.models import CashflowTransaction, Payment, Wallet
from apps.vehicles.models import VehicleEntry


class HqReportsShareSplitTests(TestCase):
    def test_hq_report_exposes_final_and_before_discount_totals(self):
        tenant = CarWash.objects.create(name='تهران', slug='tehran-report')
        vehicle = VehicleEntry.objects.create(
            tenant=tenant,
            plate_number='12ب34567',
            plate_left='12',
            plate_letter='ب',
            plate_mid='345',
            plate_right='67',
            car_model='206',
            car_color='سفید',
            driver_name='رضا',
            driver_phone='09120000000',
            status=VehicleEntry.Status.RELEASED,
        )
        Payment.objects.create(
            tenant=tenant,
            vehicle_entry=vehicle,
            method=Payment.Method.CASH,
            status=Payment.Status.SUCCESS,
            amount=1000000,
            service_amount=950000,
            product_amount=0,
            tip_amount=50000,
            discount_amount=125000,
        )

        payload = _build_hq_report_snapshot()
        row = next(item for item in payload['rows'] if item['tenant_id'] == tenant.id)

        self.assertEqual(int(row['final_total']), 1000000)
        self.assertEqual(int(row['before_discount_total']), 1125000)
        self.assertEqual(int(payload['summary']['final_total']), 1000000)
        self.assertEqual(int(payload['summary']['before_discount_total']), 1125000)

    def test_karno_share_counts_only_wallet_out_for_features_and_sms(self):
        tenant = CarWash.objects.create(name='میلان', slug='milan-share')
        regular_wallet = Wallet.objects.create(
            tenant=tenant,
            name='کیف پول اصلی',
            wallet_type=Wallet.WalletType.BANK,
            balance=0,
            is_active=True,
        )
        sms_wallet = Wallet.objects.create(
            tenant=tenant,
            name='کیف پول پیامک',
            wallet_type=Wallet.WalletType.SMS,
            balance=0,
            is_active=True,
        )
        CarWashFeaturePurchase.objects.create(
            tenant=tenant,
            feature_key=CarWashFeaturePurchase.FeatureKey.EXCEL_IMPORT,
            is_active=True,
            payment_plan=CarWashFeaturePurchase.PaymentPlan.CASH,
            total_amount=500000,
            paid_amount=500000,
            remaining_amount=0,
        )
        CarWashFeaturePurchase.objects.create(
            tenant=tenant,
            feature_key=CarWashFeaturePurchase.FeatureKey.ACCOUNTING,
            is_active=True,
            payment_plan=CarWashFeaturePurchase.PaymentPlan.CASH,
            total_amount=3000000,
            paid_amount=3000000,
            remaining_amount=0,
        )
        CashflowTransaction.objects.create(
            tenant=tenant,
            wallet=sms_wallet,
            direction=CashflowTransaction.Direction.IN,
            amount=200000,
            description='شارژ کیف پول پیامک',
            reference_type='wallet_deposit',
        )
        CashflowTransaction.objects.create(
            tenant=tenant,
            wallet=sms_wallet,
            direction=CashflowTransaction.Direction.OUT,
            amount=50000,
            description='ارسال پیامک',
            reference_type='sms_campaign_send',
        )
        CashflowTransaction.objects.create(
            tenant=tenant,
            wallet=regular_wallet,
            direction=CashflowTransaction.Direction.OUT,
            amount=100000,
            description='وارد کردن مشتریان با اکسل',
            reference_type='customer_import_excel',
        )
        CashflowTransaction.objects.create(
            tenant=tenant,
            wallet=regular_wallet,
            direction=CashflowTransaction.Direction.OUT,
            amount=3000000,
            description='feature option purchase',
            reference_type='feature_option_purchase',
        )
        CashflowTransaction.objects.create(
            tenant=tenant,
            wallet=regular_wallet,
            direction=CashflowTransaction.Direction.OUT,
            amount=400000,
            description='bank withdrawal',
            reference_type='wallet_bank_withdrawal_ticket',
        )
        CashflowTransaction.objects.create(
            tenant=tenant,
            wallet=regular_wallet,
            direction=CashflowTransaction.Direction.IN,
            amount=900000,
            description='شارژ کیف پول اصلی',
            reference_type='wallet_deposit',
        )

        payload = _build_hq_report_snapshot()
        row = next(item for item in payload['rows'] if item['tenant_id'] == tenant.id)

        self.assertEqual(int(row['hq_share_total']), 3150000)
        self.assertEqual(int(row['rah_share_total']), 400000)
        self.assertEqual(int(row['unallocated_wallet_total']), 1100000)
        self.assertIn(
            CarWashFeaturePurchase.FeatureKey.EXCEL_IMPORT,
            {item['key'] for item in payload['feature_summary']},
        )
        excel_transaction = next(
            item for item in payload['wallet_transactions']
            if item['reference_type'] == 'customer_import_excel'
        )
        sms_charge = next(
            item for item in payload['wallet_transactions']
            if item['wallet_type'] == Wallet.WalletType.SMS and item['direction'] == CashflowTransaction.Direction.IN
        )
        sms_send = next(
            item for item in payload['wallet_transactions']
            if item['wallet_type'] == Wallet.WalletType.SMS and item['direction'] == CashflowTransaction.Direction.OUT
        )
        self.assertEqual(excel_transaction['share_group'], 'hq')
        self.assertEqual(int(excel_transaction['share_amount']), 100000)
        self.assertEqual(sms_charge['share_group'], 'none')
        self.assertEqual(int(sms_charge['share_amount']), 0)
        self.assertEqual(sms_send['share_group'], 'hq')
        self.assertEqual(int(sms_send['share_amount']), 50000)
        self.assertEqual(int(payload['summary']['sms_cost_total']), 50000)

    def test_inactive_carwash_is_excluded_from_hq_reports(self):
        active = CarWash.objects.create(name='فعال', slug='active-hq-report', is_active=True)
        inactive = CarWash.objects.create(name='غیرفعال', slug='inactive-hq-report', is_active=False)
        for tenant in (active, inactive):
            vehicle = VehicleEntry.objects.create(
                tenant=tenant,
                plate_number='12ب34567',
                plate_left='12',
                plate_letter='ب',
                plate_mid='345',
                plate_right='67',
                car_model='206',
                car_color='سفید',
                driver_name='رضا',
                driver_phone='09120000000',
                status=VehicleEntry.Status.RELEASED,
            )
            Payment.objects.create(
                tenant=tenant,
                vehicle_entry=vehicle,
                method=Payment.Method.CASH,
                status=Payment.Status.SUCCESS,
                amount=1000000,
                service_amount=1000000,
                product_amount=0,
                tip_amount=0,
                discount_amount=0,
            )

        payload = _build_hq_report_snapshot()
        tenant_ids = {item['tenant_id'] for item in payload['rows']}

        self.assertIn(active.id, tenant_ids)
        self.assertNotIn(inactive.id, tenant_ids)
        self.assertEqual(int(payload['summary']['paid_amount']), 1000000)
