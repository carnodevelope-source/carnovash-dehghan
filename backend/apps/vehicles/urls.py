from django.urls import path

from .views import (
    BlockedPlateStatusView,
    BlockedPlateUnblockView,
    VehicleEntryDetailView,
    VehicleBlockPlateView,
    VehicleEntryListCreateView,
    VehiclePlateRecognitionView,
    VehiclePlateLookupView,
    VehicleEntryStatusUpdateView,
    VehicleFreeWorkersView,
    VehicleJobAdjustView,
    VehicleReleaseCheckoutView,
)

urlpatterns = [
    path('', VehicleEntryListCreateView.as_view(), name='vehicle-list-create'),
    path('plate-lookup/', VehiclePlateLookupView.as_view(), name='vehicle-plate-lookup'),
    path('plate-recognition/', VehiclePlateRecognitionView.as_view(), name='vehicle-plate-recognition'),
    path('plate-status/', BlockedPlateStatusView.as_view(), name='vehicle-plate-status'),
    path('blocked-plates/<int:pk>/unblock/', BlockedPlateUnblockView.as_view(), name='vehicle-blocked-plate-unblock'),
    path('<int:pk>/', VehicleEntryDetailView.as_view(), name='vehicle-detail'),
    path('<int:pk>/block-plate/', VehicleBlockPlateView.as_view(), name='vehicle-block-plate'),
    path('<int:pk>/status/', VehicleEntryStatusUpdateView.as_view(), name='vehicle-status-update'),
    path('<int:pk>/free-workers/', VehicleFreeWorkersView.as_view(), name='vehicle-free-workers'),
    path('<int:pk>/job-adjust/', VehicleJobAdjustView.as_view(), name='vehicle-job-adjust'),
    path('<int:pk>/release/', VehicleReleaseCheckoutView.as_view(), name='vehicle-release-checkout'),
]
