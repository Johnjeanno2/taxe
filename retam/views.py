from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from geolocalisation.models import Zone, LocalisationContribuable
from gestion_contribuables.models import Contribuable, Paiement
from django.utils.dateparse import parse_date
from django.db import models
from grappelli.dashboard import modules, Dashboard
import json

def dashboard(request):
    zones = Zone.objects.all()
    localisations = LocalisationContribuable.objects.select_related('contribuable').all()
    geojson = serialize('geojson', localisations, geometry_field='geom',
                        fields=('contribuable', 'zone', 'date_maj', 'type_contribuable'))

    # Préparation des données pour les graphiques
    types_data = list(
        Contribuable.objects.values('type_contribuable')
        .annotate(count=Count('id'))
    )
    zones_data = list(
        LocalisationContribuable.objects.values('zone__nom')
        .annotate(count=Count('contribuable'))
    )
    stats = {
        'show_stats_dashboard': True,
        'total_contribuables': Contribuable.objects.count(),
        'paiements_mois': 234700,  # exemple
        'contribuables_actifs': 4, # exemple
        'retards': 1,              # exemple
        'taux_recouvrement': 85,   # exemple
        'paiements_a_temps': 3,    # exemple
        'paiements_en_retard': 1,  # exemple
        'montant_moyen': 58700,    # exemple
    }

    return render(request, "admin/index.html", {
        "zones": zones,
        "localisations_geojson": geojson,
        "types_data": types_data,
        "zones_data": zones_data,
        "paiements_data": [],
        "taxes_data": [],
        "nouveaux_contribuables_data": [],
        "statut_contribuable_data": [],
        "stats": stats,
    })

def dashboard_stats(request):
    if request.method == "POST" and request.is_ajax():
        debut = request.POST.get('debut')
        fin = request.POST.get('fin')
        type_contribuable = request.POST.get('type')
        zone = request.POST.get('zone')

        queryset = Contribuable.objects.all()

        # Filtre par type de contribuable
        if type_contribuable and type_contribuable != "all":
            queryset = queryset.filter(type_contribuable=type_contribuable)

        # Filtre par zone
        if zone and zone != "all":
            queryset = queryset.filter(localisationcontribuable__zone__nom=zone)

        # Filtre par date
        if debut:
            queryset = queryset.filter(date_ajout__gte=debut)
        if fin:
            queryset = queryset.filter(date_ajout__lte=fin)

        total_contribuables = queryset.count()
        contribuables_actifs = queryset.filter(is_actif=True).count()
        paiements_mois = queryset.aggregate(total=Sum('paiement__montant'))['total'] or 0
        retards = queryset.filter(paiement__en_retard=True).count()

        data = {
            "total_contribuables": total_contribuables,
            "paiements_mois": paiements_mois,
            "contribuables_actifs": contribuables_actifs,
            "retards": retards,
        }
        return render(request, 'dashboard_stats.html') 

class CustomIndexDashboard(Dashboard):
    def init_with_context(self, context):
        from django.core.paginator import Paginator
        from django.http import HttpRequest

        # Récupérer la requête depuis le contexte
        request = context.get('request')
        page_number = 1
        if request and hasattr(request, 'GET'):
            page_number = request.GET.get('page', 1)

        # Récupérer toutes les zones avec leurs statistiques
        zones_stats_all = LocalisationContribuable.objects.values('zone__nom').annotate(
            count=Count('contribuable')
        ).order_by('-count')

        # Pagination des zones (15 par page)
        paginator = Paginator(zones_stats_all, 15)
        zones_stats_page = paginator.get_page(page_number)

        total_contribuables = Contribuable.objects.count()
        total_zones = Zone.objects.count()
        contribuables_localises = LocalisationContribuable.objects.count()
        
        # Calculer le taux de localisation
        taux_localisation = 0
        if total_contribuables > 0:
            taux_localisation = round((contribuables_localises / total_contribuables) * 100, 1)
        
        # Ajouter les statistiques au contexte
        context.update({
            'zones_stats': zones_stats_page,  # Page paginée
            'zones_stats_all': zones_stats_all,  # Toutes les zones pour référence
            'total_contribuables': total_contribuables,
            'total_zones': total_zones,
            'contribuables_localises': contribuables_localises,
            'taux_localisation': taux_localisation,
            'zones_paginator': paginator,
            'zones_page_number': page_number,
            'zones_has_previous': zones_stats_page.has_previous(),
            'zones_has_next': zones_stats_page.has_next(),
            'zones_previous_page': zones_stats_page.previous_page_number() if zones_stats_page.has_previous() else None,
            'zones_next_page': zones_stats_page.next_page_number() if zones_stats_page.has_next() else None,
        })
        
        # Modules du dashboard
        self.children.append(modules.AppList(
            title="Trésorerie",
            models=('tresorerie.models.*',),
            icon='fa fa-money-bill',
        ))
        
        self.children.append(modules.AppList(
            title="Gestion des contribuables",
            models=('gestion_contribuables.models.*',),
            icon='fa fa-users',
        ))
        
        self.children.append(modules.AppList(
            title="Géolocalisation",
            models=('geolocalisation.models.*',),
            icon='fa fa-map-marker-alt',
        ))

@staff_member_required
def custom_admin_index(request):
    """Vue personnalisée pour l'index admin avec statistiques"""
    
    # Statistiques par zone (depuis les localisations) -> retourne uniquement les zones ayant au moins 1 localisation
    raw_counts = (
        LocalisationContribuable.objects
        .values('zone__nom')
        .annotate(count=Count('contribuable'))
        .order_by('-count')
    )
    # Normaliser les clés pour le template (utilise item.nom et item.count)
    zones_stats = [
        {'nom': item['zone__nom'] or 'Non spécifiée', 'count': item['count']}
        for item in raw_counts
    ]
    
    # Statistiques générales
    total_contribuables = Contribuable.objects.count()
    total_zones = Zone.objects.count()
    contribuables_localises = LocalisationContribuable.objects.count()
    
    # Calculer le taux de localisation
    taux_localisation = 0
    if total_contribuables > 0:
        taux_localisation = round((contribuables_localises / total_contribuables) * 100, 1)
    
    # Statistiques des paiements du mois en cours
    mois_courant = timezone.now().month
    annee_courante = timezone.now().year
    paiements_mois = Paiement.objects.filter(
        date_paiement__month=mois_courant,
        date_paiement__year=annee_courante
    ).aggregate(total=models.Sum('montant'))['total'] or 0
    
    # Total des paiements
    paiements_total = Paiement.objects.aggregate(total=models.Sum('montant'))['total'] or 0
    
    # Données pour le graphique des zones (facultatif) - adapté au nouveau format
    zones_chart_data = {
        'labels': [item['nom'] for item in zones_stats],
        'data': [item['count'] for item in zones_stats],
        'colors': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#FF6384', '#36A2EB']
    }
    
    # Répartition par type de contribuable
    types_contribuables = Contribuable.objects.values('type_contribuable').annotate(
        count=Count('id')
    ).order_by('-count')
    
    context = {
        'zones_stats': zones_stats,
        'total_contribuables': total_contribuables,
        'total_zones': total_zones,
        'contribuables_localises': contribuables_localises,
        'taux_localisation': taux_localisation,
        'paiements_mois': paiements_mois,
        'paiements_total': paiements_total,
        'zones_chart_data_json': json.dumps(zones_chart_data),  # JSON stringifié
        'types_contribuables': types_contribuables,
        'stats': {
            'show_stats_dashboard': True,
            'total_contribuables': total_contribuables,
            'paiements_mois': paiements_mois,
            'paiements_total': paiements_total,
        }
    }
    
    return render(request, 'admin/index.html', context)