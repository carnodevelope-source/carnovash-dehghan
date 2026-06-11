from django.urls import path

from .views import (
    ExpenseEntryListCreateView,
    ExpenseEntryRetrieveUpdateDestroyView,
    InventoryItemListCreateView,
    InventoryItemRetrieveUpdateDestroyView,
    InventoryPurchaseView,
    ProductPurchaseHistoryView,
)

urlpatterns = [
    path('', InventoryItemListCreateView.as_view(), name='inventory-list-create'),
    path('expenses/', ExpenseEntryListCreateView.as_view(), name='expense-list-create'),
    path('expenses/<int:pk>/', ExpenseEntryRetrieveUpdateDestroyView.as_view(), name='expense-detail'),
    path('purchase/', InventoryPurchaseView.as_view(), name='inventory-purchase'),
    path('product-history/<int:product_id>/', ProductPurchaseHistoryView.as_view(), name='inventory-product-history'),
    path('<int:pk>/', InventoryItemRetrieveUpdateDestroyView.as_view(), name='inventory-detail'),
]
