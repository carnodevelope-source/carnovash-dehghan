from rest_framework import generics

from .models import InventoryItem
from .serializers import InventoryItemSerializer


class InventoryItemListCreateView(generics.ListCreateAPIView):
    serializer_class = InventoryItemSerializer

    def get_queryset(self):
        return InventoryItem.objects.select_related('product').order_by('product__name')


class InventoryItemRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = InventoryItemSerializer

    def get_queryset(self):
        return InventoryItem.objects.select_related('product').order_by('product__name')
