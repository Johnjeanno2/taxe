from django.apps import AppConfig

class GeolocalisationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'geolocalisation'

    def ready(self):
        # Force l'enregistrement des modèles admin
        from . import admin