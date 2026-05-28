from django.urls import path

from .views import (
    AccountDetailView,
    AccountListCreateView,
    AccountingBootstrapView,
    InventoryDetailView,
    InventoryListCreateView,
    PartyDetailView,
    PartyListCreateView,
    PurchaseConfirmView,
    PurchaseDetailView,
    PurchaseListCreateView,
    SalesConfirmView,
    SalesDetailView,
    SalesListCreateView,
    VoucherDetailView,
    VoucherListCreateView,
)

urlpatterns = [
    path('bootstrap/', AccountingBootstrapView.as_view(), name='accounting-bootstrap'),
    path('inventory/', InventoryListCreateView.as_view(), name='accounting-inventory'),
    path('inventory/<int:pk>/', InventoryDetailView.as_view(), name='accounting-inventory-detail'),
    path('purchases/', PurchaseListCreateView.as_view(), name='accounting-purchases'),
    path('purchases/<int:pk>/', PurchaseDetailView.as_view(), name='accounting-purchase-detail'),
    path('purchases/<int:pk>/confirm/', PurchaseConfirmView.as_view(), name='accounting-purchase-confirm'),
    path('sales/', SalesListCreateView.as_view(), name='accounting-sales'),
    path('sales/<int:pk>/', SalesDetailView.as_view(), name='accounting-sales-detail'),
    path('sales/<int:pk>/confirm/', SalesConfirmView.as_view(), name='accounting-sales-confirm'),
    path('vouchers/', VoucherListCreateView.as_view(), name='accounting-vouchers'),
    path('vouchers/<int:pk>/', VoucherDetailView.as_view(), name='accounting-voucher-detail'),
    path('accounts/', AccountListCreateView.as_view(), name='accounting-accounts'),
    path('accounts/<int:pk>/', AccountDetailView.as_view(), name='accounting-account-detail'),
    path('parties/', PartyListCreateView.as_view(), name='accounting-parties'),
    path('parties/<int:pk>/', PartyDetailView.as_view(), name='accounting-party-detail'),
]
