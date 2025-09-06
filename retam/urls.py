from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import custom_admin_index

urlpatterns = [
    # Index admin personnalisé
    path('admin/', custom_admin_index, name='admin_index'),
    
    # URLs des applications
    path('geolocalisation/', include('geolocalisation.urls')),
    path('gestion_contribuables/', include('gestion_contribuables.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
