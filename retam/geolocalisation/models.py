# models.py - Ajoutez ces index et méthodes
from django.contrib.gis.db import models
from django.utils import timezone
from django.conf import settings
# Import circulaire évité - utilisation de string reference
# from gestion_contribuables.models import Contribuable
import math

class Zone(models.Model):
    nom = models.CharField(max_length=100, unique=True, db_index=True)
    geom = models.PolygonField(spatial_index=True)  # Ajout d'index spatial
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Responsable de la zone"
    )
    # Nouveaux champs pour plus de fonctionnalités
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    couleur = models.CharField(max_length=7, default="#0a384f", verbose_name="Couleur d'affichage")
    active = models.BooleanField(default=True, verbose_name="Zone active")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Zone"
        verbose_name_plural = "Zones"
        ordering = ['nom']
        indexes = [
            models.Index(fields=['nom']),
            models.Index(fields=['responsable']),
        ]

    def __str__(self):
        return self.nom

    def get_centroid(self):
        """Retourne le centre de la zone"""
        return self.geom.centroid

    @property
    def nombre_contribuables(self):
        """Nombre de contribuables dans cette zone"""
        return self.localisationcontribuable_set.count()

    @property
    def superficie_km2(self):
        """Calcule la superficie de la zone en km²"""
        if self.geom:
            # Transformer en projection métrique pour calcul précis
            geom_transformed = self.geom.transform(3857, clone=True)  # Web Mercator
            return geom_transformed.area / 1000000  # Conversion m² -> km²
        return 0

    def get_bounds(self):
        """Retourne les limites de la zone (bbox)"""
        if self.geom:
            return self.geom.extent  # (xmin, ymin, xmax, ymax)
        return None

    def clean(self):
        """Validation personnalisée"""
        from django.core.exceptions import ValidationError
        if self.couleur and not self.couleur.startswith('#'):
            raise ValidationError({'couleur': 'La couleur doit être au format hexadécimal (#RRGGBB)'})

        # Vérifier que la géométrie est valide
        if self.geom and not self.geom.valid:
            raise ValidationError({'geom': 'La géométrie de la zone n\'est pas valide'})

class LocalisationContribuable(models.Model):
    contribuable = models.OneToOneField(
        'gestion_contribuables.Contribuable',
        on_delete=models.CASCADE,
        related_name='localisation'
    )
    zone = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Zone associée",
        db_index=True
    )
    geom = models.PointField("Localisation", blank=True, null=True, spatial_index=True)
    # Nouveaux champs pour améliorer la fonctionnalité
    adresse = models.CharField(max_length=255, blank=True, null=True, verbose_name="Adresse")
    precision = models.CharField(
        max_length=20,
        choices=[
            ('exact', 'Position exacte'),
            ('approximative', 'Position approximative'),
            ('zone', 'Zone générale'),
        ],
        default='approximative',
        verbose_name="Précision de la localisation"
    )
    source = models.CharField(
        max_length=50,
        choices=[
            ('gps', 'GPS'),
            ('manuel', 'Saisie manuelle'),
            ('geocodage', 'Géocodage d\'adresse'),
            ('import', 'Import de données'),
        ],
        default='manuel',
        verbose_name="Source de la localisation"
    )
    verifie = models.BooleanField(default=False, verbose_name="Localisation vérifiée")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        verbose_name = "Localisation contribuable"
        verbose_name_plural = "Localisations contribuables"
        indexes = [
            models.Index(fields=['zone']),
            models.Index(fields=['date_maj']),
        ]

    def __str__(self):
        return f"Localisation de {self.contribuable.nom}"

    @property
    def latitude(self):
        """Retourne la latitude depuis geom"""
        if self.geom:
            return self.geom.y
        return None

    @property
    def longitude(self):
        """Retourne la longitude depuis geom"""
        if self.geom:
            return self.geom.x
        return None

    def save(self, *args, **kwargs):
        """Déterminer automatiquement la zone si possible"""
        if self.geom and not self.zone:
            zone = Zone.objects.filter(geom__contains=self.geom, active=True).first()
            if zone:
                self.zone = zone
        super().save(*args, **kwargs)

    def distance_to_zone_center(self):
        """Calcule la distance au centre de la zone en mètres"""
        if self.geom and self.zone and self.zone.geom:
            center = self.zone.get_centroid()
            # Utiliser la projection Web Mercator pour un calcul précis
            geom_transformed = self.geom.transform(3857, clone=True)
            center_transformed = center.transform(3857, clone=True)
            return geom_transformed.distance(center_transformed)
        return None

    def clean(self):
        """Validation personnalisée"""
        from django.core.exceptions import ValidationError

        # Vérifier que la géométrie est dans les limites raisonnables
        if self.geom:
            if not (-180 <= self.geom.x <= 180) or not (-90 <= self.geom.y <= 90):
                raise ValidationError({'geom': 'Les coordonnées doivent être dans les limites géographiques valides'})

        # Vérifier la cohérence zone/géométrie
        if self.geom and self.zone and self.zone.geom:
            if not self.zone.geom.contains(self.geom):
                raise ValidationError({
                    'zone': 'La position ne se trouve pas dans la zone sélectionnée'
                })

class LocationManager(models.Manager):
    def nearby(self, lat, lon, radius_km=5, limit=100):
        lat, lon = float(lat), float(lon)
        lat_deg = radius_km / 111.32
        lon_deg = radius_km / (111.32 * max(1e-5, math.cos(math.radians(lat))))
        qs = self.get_queryset().filter(
            latitude__gte=lat-lat_deg, latitude__lte=lat+lat_deg,
            longitude__gte=lon-lon_deg, longitude__lte=lon+lon_deg
        )
        def haversine(a_lat,a_lon,b_lat,b_lon):
            R=6371.0
            dlat=math.radians(b_lat-a_lat); dlon=math.radians(b_lon-a_lon)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(a_lat))*math.cos(math.radians(b_lat))*math.sin(dlon/2)**2
            return 2*R*math.asin(math.sqrt(a))
        results=[]
        for obj in qs:
            try:
                d=haversine(lat,lon,obj.latitude,obj.longitude)
            except Exception:
                continue
            if d<=radius_km:
                results.append((d,obj))
        results.sort(key=lambda x:x[0])
        return [o for _,o in results[:limit]]

class Location(models.Model):
    name = models.CharField(max_length=200, blank=True)
    latitude = models.FloatField(db_index=True, null=True, blank=True)
    longitude = models.FloatField(db_index=True, null=True, blank=True)
    objects = LocationManager()