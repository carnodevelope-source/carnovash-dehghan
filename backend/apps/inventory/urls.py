from django.urls import path

from .views import InventoryItemListCreateView, InventoryItemRetrieveUpdateDestroyView, InventoryPurchaseView

urlpatterns = [
    path('', InventoryItemListCreateView.as_view(), name='inventory-list-create'),
    path('purchase/', InventoryPurchaseView.as_view(), name='inventory-purchase'),
    path('<int:pk>/', InventoryItemRetrieveUpdateDestroyView.as_view(), name='inventory-detail'),
]
