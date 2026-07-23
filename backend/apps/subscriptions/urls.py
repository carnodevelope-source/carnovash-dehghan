from django.urls import path

from . import views

urlpatterns = [
    path('hq/catalog/', views.CatalogListView.as_view(), name='subscriptions-hq-catalog'),
    path('hq/summary/', views.ServicesSummaryView.as_view(), name='subscriptions-hq-summary'),
    path('hq/subscriptions/', views.SubscriptionListView.as_view(), name='subscriptions-hq-list'),
    path('hq/subscriptions/<int:pk>/', views.SubscriptionDetailView.as_view(), name='subscriptions-hq-detail'),
    path('hq/subscriptions/<int:pk>/actions/', views.SubscriptionActionView.as_view(), name='subscriptions-hq-actions'),
    path('hq/clients/<int:tenant_id>/services/', views.ClientServicesView.as_view(), name='subscriptions-hq-client'),
    path('hq/orders/', views.ManualOrderCreateView.as_view(), name='subscriptions-hq-orders'),
    path('hq/bulk/', views.BulkJobCreateView.as_view(), name='subscriptions-hq-bulk'),
    path('hq/alerts/', views.AlertsListView.as_view(), name='subscriptions-hq-alerts'),
    path('hq/reports/<str:report_key>/', views.SpecializedReportView.as_view(), name='subscriptions-hq-specialized'),
    path('hq/revenue/', views.RevenueMatrixView.as_view(), name='subscriptions-hq-revenue'),
    path('hq/export/', views.ExportSubscriptionsView.as_view(), name='subscriptions-hq-export'),
    path('hq/seed/', views.SeedCatalogView.as_view(), name='subscriptions-hq-seed'),
    path('catalog/', views.TenantCatalogView.as_view(), name='subscriptions-tenant-catalog'),
]
