from django.urls import path

from .views import (
    AttendanceDashboardView,
    AttendanceManagerEventCreateView,
    AttendancePublicView,
    AttendanceTokenRefreshView,
    WorkerProfileListCreateView,
    WorkerProfileRetrieveUpdateDestroyView,
)

urlpatterns = [
    path('', WorkerProfileListCreateView.as_view(), name='worker-list-create'),
    path('attendance/dashboard/', AttendanceDashboardView.as_view(), name='worker-attendance-dashboard'),
    path('attendance/events/', AttendanceManagerEventCreateView.as_view(), name='worker-attendance-event-create'),
    path('attendance/public/<str:token>/', AttendancePublicView.as_view(), name='worker-attendance-public'),
    path('<int:pk>/', WorkerProfileRetrieveUpdateDestroyView.as_view(), name='worker-detail'),
    path('<int:pk>/attendance-token/refresh/', AttendanceTokenRefreshView.as_view(), name='worker-attendance-token-refresh'),
]
