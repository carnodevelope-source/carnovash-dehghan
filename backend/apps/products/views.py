from rest_framework import generics

from .models import Product
from .serializers import ProductSerializer


class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        return Product.objects.filter(tenant=tenant).order_by('name')

    def perform_create(self, serializer):
        serializer.save(
            tenant=getattr(self.request.user, 'tenant', None),
            created_by=self.request.user if self.request.user.is_authenticated else None,
        )


class ProductRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', None)
        return Product.objects.filter(tenant=tenant).order_by('name')
