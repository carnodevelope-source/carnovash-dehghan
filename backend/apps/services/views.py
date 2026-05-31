from rest_framework import generics

from .models import GeneralSettings, Service
from .serializers import GeneralSettingsSerializer, ServiceSerializer


class ServiceListCreateView(generics.ListCreateAPIView):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        return Service.objects.select_related('category').filter(tenant=tenant).order_by('display_order', 'name')

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user, tenant=getattr(user, 'tenant', None))


class ServiceRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        return Service.objects.select_related('category').filter(tenant=tenant).order_by('display_order', 'name')


class GeneralSettingsRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = GeneralSettingsSerializer
    queryset = GeneralSettings.objects.all()

    def get_object(self):
        settings_obj, _ = GeneralSettings.objects.get_or_create(
            tenant=self.request.user.tenant,
            defaults={'discount_percent_per_half_star': 0},
        )
        return settings_obj
