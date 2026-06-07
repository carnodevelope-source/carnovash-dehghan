from django.urls import path

from .views import InventoryItemListCreateView, InventoryItemRetrieveUpdateDestroyView, InventoryPurchaseView, ProductPurchaseHistoryView

urlpatterns = [
    path('', InventoryItemListCreateView.as_view(), name='inventory-list-create'),
    path('purchase/', InventoryPurchaseView.as_view(), name='inventory-purchase'),
    path('product-history/<int:product_id>/', ProductPurchaseHistoryView.as_view(), name='inventory-product-history'),
    path('<int:pk>/', InventoryItemRetrieveUpdateDestroyView.as_view(), name='inventory-detail'),
]
