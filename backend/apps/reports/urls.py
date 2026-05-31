from django.urls import path

from .views import ReportsDashboardView, ReportsPayoutSettleView

urlpatterns = [
    path('dashboard/', ReportsDashboardView.as_view(), name='reports-dashboard'),
    path('payouts/settle/', ReportsPayoutSettleView.as_view(), name='reports-payouts-settle'),
]
