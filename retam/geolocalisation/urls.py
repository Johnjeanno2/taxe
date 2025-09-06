from django.urls import path
from . import views

app_name = "geolocalisation"

urlpatterns = [
    # Pages principales
    path('zones/', views.carte_zones, name='carte_zones'),
    path('localisation/<int:pk>/', views.detail_localisation, name='detail_localisation'),
    path('ajouter-localisation/', views.ajouter_localisation, name='ajouter_localisation'),
    path('create-zone/', views.create_zone, name='create_zone'),

    # APIs de données géographiques
    path('api/zones/geojson/', views.zones_geojson, name='zones_geojson'),
    path('api/zones/all-geojson/', views.all_zones_geojson, name='all_zones_geojson'),
    path('api/localisations/geojson/', views.localisations_geojson, name='localisations_geojson'),

    # APIs de recherche et géocodage
    path('api/search/', views.search_location, name='search_location'),
    path('api/geocoder/', views.geocoder_adresse, name='geocoder_adresse'),

    # APIs de statistiques
    path('api/zones/statistiques/', views.zones_statistiques, name='zones_statistiques'),

    # URLs pour la gestion des améliorations
    path('admin/map-improvements/', views.map_improvements_admin, name='map_improvements_admin'),
    path('api/apply-improvements/', views.apply_improvements_ajax, name='apply_improvements_ajax'),
    path('api/create-backup/', views.create_backup_ajax, name='create_backup_ajax'),

    # Nouvelle URL pour la vue de la carte Google
    path('carte/', views.google_map_view, name='map'),
]