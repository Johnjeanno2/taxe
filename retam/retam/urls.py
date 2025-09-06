from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from gestion_contribuables.admin import admin_site

urlpatterns = [
    path('', RedirectView.as_view(url='/admin/login', permanent=False)),
    path('admin/login', admin_site.urls),
    path('contribuables/', include('gestion_contribuables.urls')),
    path('geolocalisation/', include('geolocalisation.urls')),
    path('grappelli/', include('grappelli.urls')),
    path('select2/', include('django_select2.urls')),
    path('admin/', admin.site.urls),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
