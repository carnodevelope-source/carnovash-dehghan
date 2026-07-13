from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from openpyxl import Workbook

from apps.auth.models import CarWash, CarWashFeaturePurchase
from apps.notifications.models import ImportedCustomer
from apps.payments.models import CashflowTransaction, Wallet


def customer_import_file(*, phone='09123456789'):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(['نام مشتری', 'شماره تلفن', 'پلاک', 'مدل خودرو', 'رنگ خودرو', 'توضیحات'])
    sheet.append(['علی رضایی', phone, '12 ب 345 67', 'پژو 206', 'سفید', ''])
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return SimpleUploadedFile(
        'customers.xlsx',
        stream.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


class CustomerImportTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.tenant = CarWash.objects.create(name='سونامی', slug='sonami-import')
        self.user = user_model.objects.create_user(
            username='import-manager',
            password='pass12345',
            phone='09129990003',
            role='manager',
            tenant=self.tenant,
        )
        CarWashFeaturePurchase.objects.create(
            tenant=self.tenant,
            feature_key=CarWashFeaturePurchase.FeatureKey.CORE_SOFTWARE,
            is_active=True,
            payment_plan=CarWashFeaturePurchase.PaymentPlan.CASH,
            total_amount=7000000,
            paid_amount=7000000,
            remaining_amount=0,
        )
        self.wallet = Wallet.objects.create(
            tenant=self.tenant,
            name='کیف پول اصلی',
            wallet_type=Wallet.WalletType.BANK,
            balance=600000,
            is_active=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_confirm_customer_import_debits_wallet_per_conversion(self):
        response = self.client.post(
            reverse('notifications-customer-import-confirm'),
            {'file': customer_import_file()},
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        self.wallet.refresh_from_db()
        self.assertEqual(int(self.wallet.balance), 100000)
        self.assertEqual(int(response.data['charged_amount']), 500000)
        self.assertEqual(ImportedCustomer.objects.filter(tenant=self.tenant).count(), 1)
        transaction = CashflowTransaction.objects.get(
            tenant=self.tenant,
            reference_type='customer_import_excel',
        )
        self.assertEqual(int(transaction.amount), 500000)
        self.assertEqual(transaction.direction, CashflowTransaction.Direction.OUT)

    def test_confirm_customer_import_rejects_when_wallet_balance_is_not_enough(self):
        self.wallet.balance = 499999
        self.wallet.save(update_fields=['balance'])

        response = self.client.post(
            reverse('notifications-customer-import-confirm'),
            {'file': customer_import_file(phone='09123456780')},
            format='multipart',
        )

        self.assertEqual(response.status_code, 402)
        self.wallet.refresh_from_db()
        self.assertEqual(int(self.wallet.balance), 499999)
        self.assertFalse(ImportedCustomer.objects.filter(tenant=self.tenant).exists())
        self.assertFalse(
            CashflowTransaction.objects.filter(
                tenant=self.tenant,
                reference_type='customer_import_excel',
            ).exists()
        )
