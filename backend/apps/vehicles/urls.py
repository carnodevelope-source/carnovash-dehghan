from django.urls import path

from .views import (
    VehicleEntryDetailView,
    VehicleEntryListCreateView,
    VehicleEntryStatusUpdateView,
    VehicleReleaseCheckoutView,
)

urlpatterns = [
    path('', VehicleEntryListCreateView.as_view(), name='vehicle-list-create'),
    path('<int:pk>/', VehicleEntryDetailView.as_view(), name='vehicle-detail'),
    path('<int:pk>/status/', VehicleEntryStatusUpdateView.as_view(), name='vehicle-status-update'),
    path('<int:pk>/release/', VehicleReleaseCheckoutView.as_view(), name='vehicle-release-checkout'),
]
