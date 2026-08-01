from decimal import Decimal

from django.test import SimpleTestCase

from apps.auth.support_tickets import (
    WALLET_CARD_DEPOSIT_TAX_PERCENT,
    calculate_wallet_card_deposit_amounts,
)


class WalletCardDepositTaxTests(SimpleTestCase):
    def test_tax_percent_is_ten(self):
        self.assertEqual(WALLET_CARD_DEPOSIT_TAX_PERCENT, Decimal('10'))

    def test_two_million_deposit_credits_net_after_ten_percent_tax(self):
        gross, tax, net = calculate_wallet_card_deposit_amounts(2_000_000)
        self.assertEqual(gross, Decimal('2000000'))
        self.assertEqual(tax, Decimal('200000.00'))
        self.assertEqual(net, Decimal('1800000.00'))

    def test_zero_and_negative_return_zeros(self):
        self.assertEqual(calculate_wallet_card_deposit_amounts(0), (Decimal('0'), Decimal('0'), Decimal('0')))
        self.assertEqual(calculate_wallet_card_deposit_amounts(-100), (Decimal('0'), Decimal('0'), Decimal('0')))
