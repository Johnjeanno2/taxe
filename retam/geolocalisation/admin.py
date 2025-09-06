from django.contrib import admin
from django import forms
from django.db import models

from django.contrib import admin
from django import forms
from django.db import models
from .models import Zone, LocalisationContribuable
from .forms import LocalisationContribuableForm, ZoneForm

# Nous remplaçons LeafletGeoAdmin par ModelAdmin standard et injectons nos scripts Google Maps
from .models import Zone, LocalisationContribuable
from .forms import LocalisationContribuableForm

@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    form = ZoneForm
    list_display = ('nom', 'responsable', 'active', 'date_creation')
    search_fields = ('nom',)
    list_filter = ('responsable', 'active', 'date_creation')
    list_editable = ('active',)

    fields = ('nom', 'responsable', 'active', 'geom')


    
    # Permissions de suppression
    actions = ['delete_selected']
    
    def has_delete_permission(self, request, obj=None):
        return True
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' not in actions:
            actions['delete_selected'] = self.get_action('delete_selected')
        return actions
    
    class Media:
        css = {'all': ('geolocalisation/css/admin_map.css',)}
        js = (
            'geolocalisation/js/admin_map_search.js',
            'geolocalisation/js/admin_zone_google.js',
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        return obj

# Le formulaire LocalisationContribuableForm est maintenant importé depuis forms.py

@admin.register(LocalisationContribuable)
class LocalisationContribuableAdmin(admin.ModelAdmin):
    form = LocalisationContribuableForm
    list_display = ('contribuable', 'zone', 'adresse_courte', 'precision', 'source', 'verifie', 'date_maj')
    search_fields = ('contribuable__nom', 'adresse')
    list_filter = ('zone', 'precision', 'source', 'verifie', 'date_creation')
    list_editable = ('verifie',)

    fields = ('contribuable', 'zone', 'geom', 'adresse', 'precision', 'source', 'verifie')

    def adresse_courte(self, obj):
        if obj.adresse:
            return obj.adresse[:50] + "..." if len(obj.adresse) > 50 else obj.adresse
        return "-"
    adresse_courte.short_description = 'Adresse'
    
    # Permissions de suppression
    actions = ['delete_selected']
    
    def has_delete_permission(self, request, obj=None):
        return True
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' not in actions:
            actions['delete_selected'] = self.get_action('delete_selected')
        return actions

    class Media:
        css = {'all': ('geolocalisation/css/admin_map.css',)}
        js = (
            'geolocalisation/js/admin_map_search.js',
            'geolocalisation/js/admin_localisation_google.js',
        )
    
    # Configuration pour éviter la redirection
    def response_add(self, request, obj, post_url_continue=None):
        """Empêche la redirection après l'ajout"""
        if "_continue" in request.POST:
            return super().response_add(request, obj, post_url_continue)
        return super().response_add(request, obj, post_url_continue="../")
    
    def response_change(self, request, obj):
        """Empêche la redirection après la modification"""
        if "_continue" in request.POST:
            return super().response_change(request, obj)
        return super().response_change(request, obj)

# Ajouter un lien vers l'interface d'améliorations dans l'admin
from django.urls import reverse
from django.utils.html import format_html
from django.contrib import admin

def get_admin_urls():
    """Ajouter des URLs personnalisées à l'admin"""
    from django.urls import path
    from . import views
    
    return [
        path('map-improvements/', views.map_improvements_admin, name='map_improvements'),
    ]

# Enregistrer les URLs personnalisées
original_get_urls = admin.site.get_urls
admin.site.get_urls = lambda: get_admin_urls() + original_get_urls()