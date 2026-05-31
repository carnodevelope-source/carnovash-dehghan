from django.urls import path

from .views import CsrfView, LoginView, LogoutView, MeView, TenantRegisterView, UserManagementView

urlpatterns = [
    path('csrf/', CsrfView.as_view(), name='csrf'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', MeView.as_view(), name='me'),
    path('users/', UserManagementView.as_view(), name='users'),
    path('tenants/register/', TenantRegisterView.as_view(), name='tenant-register'),
]
