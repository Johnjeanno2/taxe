from django.urls import path
from . import views

app_name = "gestion_contribuables"

urlpatterns = [
    # URLs pour les contribuables
    path('', views.ContribuableListView.as_view(), name='contribuable_list'),
    path('ajouter/', views.ContribuableCreateView.as_view(), name='contribuable_create'),
    path('<int:pk>/', views.ContribuableDetailView.as_view(), name='contribuable_detail'),
    path('fiche/<int:pk>/', views.fiche_contribuable, name='fiche_contribuable'),
    path('<int:pk>/modifier/', views.ContribuableUpdateView.as_view(), name='contribuable_update'),
    path('<int:pk>/supprimer/', views.ContribuableDeleteView.as_view(), name='contribuable_delete'),

    # URLs pour les paiements
    path('paiement/ajouter/', views.PaiementCreateView.as_view(), name='paiement_create'),
    path('paiement/<int:paiement_id>/quittance/', views.quittance_paiement, name='quittance_paiement'),

    # API Endpoints
    path('api/zones/geojson/', views.zones_geojson, name='zones_geojson'),
    path('admin/dashboard_stats/', views.dashboard_stats, name='dashboard_stats'),

    # Autres URLs
    path('historique/<int:pk>/', views.historique_contribuable, name='historique_contribuable'),
    path('repartition-stats/', views.repartition_stats, name='repartition_stats'),

    # URL pour la quittance signée
    path('s/quittance/', views.serve_quittance_signed, name='quittance_signed'),
    path('s/quittance/html/', views.serve_quittance_html, name='quittance_html_signed'),
    path('api/offline-sync/', views.api_offline_sync, name='api_offline_sync'),
    path('api/offline-sync/heartbeat', views.api_offline_sync_heartbeat, name='api_offline_sync_heartbeat'),  # optionnel
]
