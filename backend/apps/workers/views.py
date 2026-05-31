from rest_framework import generics

from .models import WorkerProfile
from .serializers import WorkerProfileCreateUpdateSerializer, WorkerProfileListSerializer


class WorkerProfileListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return WorkerProfileCreateUpdateSerializer
        return WorkerProfileListSerializer

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        return WorkerProfile.objects.select_related('user').filter(tenant=tenant).order_by('user__full_name', 'user__username')


class WorkerProfileRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        return WorkerProfile.objects.select_related('user').filter(tenant=tenant).order_by('user__full_name', 'user__username')

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return WorkerProfileCreateUpdateSerializer
        return WorkerProfileListSerializer

    def perform_destroy(self, instance):
        user = instance.user
        instance.delete()
        if user:
            user.delete()
