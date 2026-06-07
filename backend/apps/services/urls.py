from django.urls import path

from .views import (
    GeneralSettingsRetrieveUpdateView,
    ServiceHistoryView,
    ServiceListCreateView,
    ServiceRetrieveUpdateDestroyView,
)

urlpatterns = [
    path('general-settings/', GeneralSettingsRetrieveUpdateView.as_view(), name='general-settings'),
    path('<int:pk>/history/', ServiceHistoryView.as_view(), name='service-history'),
    path('', ServiceListCreateView.as_view(), name='service-list-create'),
    path('<int:pk>/', ServiceRetrieveUpdateDestroyView.as_view(), name='service-detail'),
]
