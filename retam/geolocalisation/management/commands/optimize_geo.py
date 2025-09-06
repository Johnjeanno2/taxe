# geolocalisation/management/commands/optimize_geo.py
from django.core.management.base import BaseCommand
from django.db import connection
from geolocalisation.models import Zone, LocalisationContribuable

class Command(BaseCommand):
    help = 'Optimise les données géographiques'
    
    def handle(self, *args, **options):
        # Créer les index spatiaux si nécessaire
        with connection.cursor() as cursor:
            # Pour PostgreSQL/PostGIS
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS zone_geom_idx 
                ON geolocalisation_zone USING GIST (geom);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS localisation_geom_idx 
                ON geolocalisation_localisationcontribuable USING GIST (geom);
            """)
        
        self.stdout.write(
            self.style.SUCCESS('Index spatiaux optimisés avec succès')
        )