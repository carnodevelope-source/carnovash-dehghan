from decimal import Decimal

from django.test import SimpleTestCase

from apps.auth.support_tickets import (
    WALLET_CARD_DEPOSIT_TAX_PERCENT,
    calculate_wallet_card_deposit_amounts,
)


class WalletCardDepositTaxTests(SimpleTestCase):
    def test_card_deposit_uses_current_zero_tax_policy(self):
        self.assertEqual(WALLET_CARD_DEPOSIT_TAX_PERCENT, Decimal('0'))

    def test_two_million_deposit_credits_full_amount_without_tax(self):
        gross, tax, net = calculate_wallet_card_deposit_amounts(2_000_000)
        self.assertEqual(gross, Decimal('2000000'))
        self.assertEqual(tax, Decimal('0.00'))
        self.assertEqual(net, Decimal('2000000.00'))

    def test_zero_and_negative_return_zeros(self):
        self.assertEqual(calculate_wallet_card_deposit_amounts(0), (Decimal('0'), Decimal('0'), Decimal('0')))
        self.assertEqual(calculate_wallet_card_deposit_amounts(-100), (Decimal('0'), Decimal('0'), Decimal('0')))
