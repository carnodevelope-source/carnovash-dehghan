from rest_framework import generics, status
from rest_framework.response import Response
from django.db.models import F

from .models import WorkerProfile
from .serializers import (
    WorkerProfileCreateUpdateSerializer,
    WorkerProfileListSerializer,
    _resolve_request_tenant,
)


class WorkerProfileListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return WorkerProfileCreateUpdateSerializer
        return WorkerProfileListSerializer

    def get_queryset(self):
        tenant = _resolve_request_tenant(self.request)
        return WorkerProfile.objects.select_related('user').filter(tenant=tenant).order_by(F('last_assigned_at').asc(nulls_first=True), 'user__full_name', 'user__username')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        output = WorkerProfileListSerializer(instance, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)


class WorkerProfileRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    def get_queryset(self):
        tenant = _resolve_request_tenant(self.request)
        return WorkerProfile.objects.select_related('user').filter(tenant=tenant).order_by(F('last_assigned_at').asc(nulls_first=True), 'user__full_name', 'user__username')

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return WorkerProfileCreateUpdateSerializer
        return WorkerProfileListSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()
        output = WorkerProfileListSerializer(updated_instance, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        user = instance.user
        instance.delete()
        if user:
            user.delete()
