from django.urls import path

from .views import (
    CustomerClubDashboardView,
    CustomerGroupDetailView,
    CustomerGroupListCreateView,
    SimpleSmsSendView,
    SmsCampaignSendView,
    SmsTemplateDetailView,
    SmsTemplateListCreateView,
)


urlpatterns = [
    path('customer-club/', CustomerClubDashboardView.as_view(), name='notifications-customer-club'),
    path('customer-groups/', CustomerGroupListCreateView.as_view(), name='notifications-customer-groups'),
    path('customer-groups/<int:pk>/', CustomerGroupDetailView.as_view(), name='notifications-customer-group-detail'),
    path('sms/templates/', SmsTemplateListCreateView.as_view(), name='notifications-sms-templates'),
    path('sms/templates/<int:pk>/', SmsTemplateDetailView.as_view(), name='notifications-sms-template-detail'),
    path('sms/send/', SmsCampaignSendView.as_view(), name='notifications-sms-send'),
    path('sms/simple/', SimpleSmsSendView.as_view(), name='notifications-sms-simple'),
]
