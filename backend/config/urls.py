from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from apps.live import live_events_view, live_revision_view, live_sync_view


def health(_request):
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health, name='health'),
    path('api/live/events/', live_events_view, name='live-events'),
    path('api/live/revision/', live_revision_view, name='live-revision'),
    path('api/live/sync/', live_sync_view, name='live-sync'),
    path('api/auth/', include('apps.auth.urls')),
    path('api/vehicles/', include('apps.vehicles.urls')),
    path('api/workers/', include('apps.workers.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/services/', include('apps.services.urls')),
    path('api/products/', include('apps.products.urls')),
    path('api/payments/', include('apps.payments.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/subscriptions/', include('apps.subscriptions.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
