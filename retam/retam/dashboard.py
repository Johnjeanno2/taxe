from grappelli.dashboard import modules, Dashboard
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from geolocalisation.models import Zone, LocalisationContribuable
from gestion_contribuables.models import Contribuable, Paiement

class CustomIndexDashboard(Dashboard):
    def init_with_context(self, context):
        # Récupérer les statistiques
        zones_stats = LocalisationContribuable.objects.values('zone__nom').annotate(
            count=Count('contribuable')
        ).order_by('-count')
        
        total_contribuables = Contribuable.objects.count()
        total_zones = Zone.objects.count()
        contribuables_localises = LocalisationContribuable.objects.count()
        
        # Calculer le taux de localisation
        taux_localisation = 0
        if total_contribuables > 0:
            taux_localisation = round((contribuables_localises / total_contribuables) * 100, 1)
        
        # Ajouter les statistiques au contexte
        context.update({
            'zones_stats': zones_stats,
            'total_contribuables': total_contribuables,
            'total_zones': total_zones,
            'contribuables_localises': contribuables_localises,
            'taux_localisation': taux_localisation,
        })
        
        # Modules du dashboard
        self.children.append(modules.AppList(
            title="Trésorerie",
            models=('tresorerie.models.*',),
            icon='fa fa-money-bill',
        ))
        
        # Ajouter d'autres modules si nécessaire
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