from django.urls import path

from .views import (
    ReportsDashboardView,
    ReportsExportView,
    ReportsPayoutSettleView,
    ReportsWorkerAdjustmentView,
    ReportsWorkerPayoutView,
)

urlpatterns = [
    path('dashboard/', ReportsDashboardView.as_view(), name='reports-dashboard'),
    path('export/', ReportsExportView.as_view(), name='reports-export'),
    path('payouts/settle/', ReportsPayoutSettleView.as_view(), name='reports-payouts-settle'),
    path('workers/payouts/', ReportsWorkerPayoutView.as_view(), name='reports-worker-payouts'),
    path('workers/adjustments/', ReportsWorkerAdjustmentView.as_view(), name='reports-worker-adjustments'),
]
