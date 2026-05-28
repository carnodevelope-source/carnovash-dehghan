from django.urls import path

from .views import WorkerProfileListCreateView, WorkerProfileRetrieveUpdateDestroyView

urlpatterns = [
    path('', WorkerProfileListCreateView.as_view(), name='worker-list-create'),
    path('<int:pk>/', WorkerProfileRetrieveUpdateDestroyView.as_view(), name='worker-detail'),
]
