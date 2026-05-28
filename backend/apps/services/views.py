from rest_framework import generics

from .models import Service
from .serializers import ServiceSerializer


class ServiceListCreateView(generics.ListCreateAPIView):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        return Service.objects.select_related('category').order_by('display_order', 'name')

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)


class ServiceRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        return Service.objects.select_related('category').order_by('display_order', 'name')
