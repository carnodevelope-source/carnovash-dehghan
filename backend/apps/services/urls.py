from django.urls import path

from .views import (
    GeneralSettingsRetrieveUpdateView,
    ServiceListCreateView,
    ServiceRetrieveUpdateDestroyView,
)

urlpatterns = [
    path('general-settings/', GeneralSettingsRetrieveUpdateView.as_view(), name='general-settings'),
    path('', ServiceListCreateView.as_view(), name='service-list-create'),
    path('<int:pk>/', ServiceRetrieveUpdateDestroyView.as_view(), name='service-detail'),
]
