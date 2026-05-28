from django.urls import path

from .views import InventoryItemListCreateView, InventoryItemRetrieveUpdateDestroyView

urlpatterns = [
    path('', InventoryItemListCreateView.as_view(), name='inventory-list-create'),
    path('<int:pk>/', InventoryItemRetrieveUpdateDestroyView.as_view(), name='inventory-detail'),
]
