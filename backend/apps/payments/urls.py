from django.urls import path

from .views import (
    WalletDashboardView,
    WalletDepositCheckoutView,
    WalletDepositStartView,
    WalletDepositView,
    WalletWithdrawView,
    WalletOptionsView,
)

urlpatterns = [
    path('wallet/dashboard/', WalletDashboardView.as_view(), name='wallet-dashboard'),
    path('wallet/options/', WalletOptionsView.as_view(), name='wallet-options'),
    path('wallet/deposit/start/', WalletDepositStartView.as_view(), name='wallet-deposit-start'),
    path('wallet/deposit/checkout/', WalletDepositCheckoutView.as_view(), name='wallet-deposit-checkout'),
    path('wallet/deposit/', WalletDepositView.as_view(), name='wallet-deposit'),
    path('wallet/withdraw/', WalletWithdrawView.as_view(), name='wallet-withdraw'),
]
