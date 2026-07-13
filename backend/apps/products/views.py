from django.utils import timezone
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response

from .models import Product
from .serializers import ProductSerializer


class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        return Product.objects.filter(tenant=tenant, is_deleted=False).order_by('name')

    def perform_create(self, serializer):
        serializer.save(
            tenant=getattr(self.request.user, 'tenant', None),
            created_by=self.request.user if self.request.user.is_authenticated else None,
        )


class ProductRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        return Product.objects.filter(tenant=tenant, is_deleted=False).order_by('name')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.is_deleted:
            instance.is_active = False
            instance.is_deleted = True
            instance.deleted_at = timezone.now()
            instance.deleted_by = request.user if request.user.is_authenticated else None
            instance.save(update_fields=['is_active', 'is_deleted', 'deleted_at', 'deleted_by', 'updated_at'])
        return Response({'soft_deleted': True, 'is_active': False}, status=status.HTTP_200_OK)
