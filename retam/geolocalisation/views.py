# geolocalisation/views.py
from django.shortcuts import render, get_object_or_404, redirect
from .models import Location, Zone, LocalisationContribuable
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.core.serializers import serialize
from django.db.models import Q
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from .forms import ZoneForm
import json
from django.core.serializers.json import DjangoJSONEncoder

# Vue pour l'API GeoJSON des zones
def zones_geojson(request):
    try:
        # zones ayant au moins 1 contribuable
        zones = Zone.objects.all()
        features = []
        for z in zones:
            features.append({
                "type": "Feature",
                "geometry": json.loads(z.geom.geojson),
                "properties": {
                    "id": z.id,
                    "nom": z.nom,
                },
            })
        return JsonResponse({"type": "FeatureCollection", "features": features})
    except Exception as e:
        return JsonResponse({'erreur': str(e)}, status=500)

# Vue pour l'API GeoJSON de toutes les zones (pour l'admin)
def all_zones_geojson(request):
    """API pour récupérer toutes les zones avec leurs délimitations pour l'interface admin"""
    try:
        # Filtrer par zones actives si demandé
        actives_seulement = request.GET.get('actives_seulement', 'false').lower() == 'true'

        zones_qs = Zone.objects.all()
        if actives_seulement:
            zones_qs = zones_qs.filter(active=True)

        zones = zones_qs.all()

        features = []
        for zone in zones:
            centroid = zone.get_centroid()
            
            features.append({
                "type": "Feature",
                "geometry": json.loads(zone.geom.geojson),
                "properties": {
                    "id": zone.id,
                    "nom": zone.nom,
                    "active": zone.active,
                    "responsable": zone.responsable.username if zone.responsable else None,
                    "centroid": {
                        "lat": centroid.y,
                        "lng": centroid.x
                    },
                    "date_creation": zone.date_creation.isoformat(),
                    "date_maj": zone.date_maj.isoformat(),
                }
            })
        
        return JsonResponse({
            "type": "FeatureCollection", 
            "features": features
        })
    except Exception as e:
        return JsonResponse({'erreur': str(e)}, status=500)
    
# Vue pour l'API GeoJSON des localisations
def localisations_geojson(request):
    try:
        # Filtres optionnels
        zone_id = request.GET.get('zone_id')
        verifie_seulement = request.GET.get('verifie_seulement', 'false').lower() == 'true'
        precision = request.GET.get('precision')

        localisations_qs = LocalisationContribuable.objects.select_related(
            'contribuable', 'zone'
        ).filter(geom__isnull=False)

        if zone_id:
            localisations_qs = localisations_qs.filter(zone_id=zone_id)
        if verifie_seulement:
            localisations_qs = localisations_qs.filter(verifie=True)
        if precision:
            localisations_qs = localisations_qs.filter(precision=precision)

        features = []
        for loc in localisations_qs:
            features.append({
                "type": "Feature",
                "geometry": json.loads(loc.geom.geojson),
                "properties": {
                    "id": loc.id,
                    "contribuable__nom": loc.contribuable.nom,
                    "zone__nom": loc.zone.nom if loc.zone else None,
                    "adresse": loc.adresse,
                    "precision": loc.get_precision_display(),
                    "source": loc.get_source_display(),
                    "verifie": loc.verifie,
                    "date_creation": loc.date_creation.isoformat(),
                    "date_maj": loc.date_maj.isoformat(),
                }
            })

        return JsonResponse({
            "type": "FeatureCollection",
            "features": features
        })
    except Exception as e:
        return JsonResponse({'erreur': str(e)}, status=500)

# Vue pour la création de zone
@permission_required('geolocalisation.add_zone')
def create_zone(request):
    if request.method == 'POST':
        form = ZoneForm(request.POST)
        if form.is_valid():
            try:
                zone = form.save(commit=False)
                zone.responsable = request.user
                zone.save()
                messages.success(request, "La zone a été créée avec succès.")
                return redirect(reverse('admin:geolocalisation_zone_changelist'))
            except Exception as e:
                messages.error(request, f"Erreur lors de la création : {str(e)}")
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = ZoneForm()

    return render(request, "admin/geolocalisation/zone/add_form.html", {
        'form': form,
        'title': "Créer une nouvelle zone"
    })

# Vue principale de la carte
@login_required
def carte_zones(request):
    from django.core.paginator import Paginator

    # Pagination pour les zones
    zones_list = Zone.objects.all().order_by('nom')
    paginator = Paginator(zones_list, 15)  # 15 zones par page
    page_number = request.GET.get('page', 1)
    zones_page = paginator.get_page(page_number)

    # Toutes les localisations pour la carte
    localisations = LocalisationContribuable.objects.select_related(
        'contribuable', 'zone'
    ).filter(geom__isnull=False).only('geom', 'contribuable__nom', 'zone__nom')

    # Préparer les données GeoJSON (toutes les zones pour la carte)
    zones_geojson = serialize('geojson', Zone.objects.all(),
                            geometry_field='geom',
                            fields=('nom', 'responsable'))
    
    localisations_geojson = serialize('geojson', localisations,
                                    geometry_field='geom',
                                    fields=('contribuable__nom', 'zone__nom'))

    # Calculer les statistiques
    total_zones = zones_list.count()
    total_contribuables = sum(zone.localisationcontribuable_set.count() for zone in zones_list)

    return render(request, "geolocalisation/carte_zones.html", {
        "zones_page": zones_page,
        "zones": zones_list,  # Pour compatibilité
        "localisations": localisations,
        "zones_geojson": zones_geojson,
        "localisations_geojson": localisations_geojson,
        "total_zones": total_zones,
        "total_contribuables": total_contribuables,
        "current_page": page_number,
        "has_previous": zones_page.has_previous(),
        "has_next": zones_page.has_next(),
        "previous_page": zones_page.previous_page_number() if zones_page.has_previous() else None,
        "next_page": zones_page.next_page_number() if zones_page.has_next() else None,
    })

# Vue pour le détail d'une localisation
@login_required
def detail_localisation(request, pk):
    """
    Affiche une localisation (détail).
    """
    loc = get_object_or_404(LocalisationContribuable, pk=pk)
    return render(request, "geolocalisation/detail_localisation.html", {"location": loc})

# API simplifiée pour les zones (sans statistiques)
@login_required
def zones_statistiques(request):
    """API pour récupérer les zones sans statistiques"""
    try:
        zones = Zone.objects.filter(active=True)

        zones_data = []
        for zone in zones:
            zones_data.append({
                'id': zone.id,
                'nom': zone.nom,
                'responsable': zone.responsable.username if zone.responsable else None,
                'date_creation': zone.date_creation.isoformat(),
                'date_maj': zone.date_maj.isoformat(),
            })

        return JsonResponse({
            'zones': zones_data
        })
    except Exception as e:
        return JsonResponse({'erreur': str(e)}, status=500)

# API de géocodage d'adresse
@login_required
def geocoder_adresse(request):
    """API pour géocoder une adresse en coordonnées"""
    adresse = request.GET.get('adresse', '').strip()

    if not adresse:
        return JsonResponse({'erreur': 'Adresse requise'}, status=400)

    try:
        # Ici vous pouvez intégrer un service de géocodage
        # Pour l'exemple, on retourne une réponse basique
        # En production, utilisez un service comme Nominatim, Google Geocoding, etc.

        import requests
        from urllib.parse import quote

        # Utilisation de Nominatim (OpenStreetMap)
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={quote(adresse)}&limit=5"

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        results = response.json()

        if not results:
            return JsonResponse({'erreur': 'Aucun résultat trouvé pour cette adresse'}, status=404)

        # Formater les résultats
        suggestions = []
        for result in results:
            suggestions.append({
                'adresse': result.get('display_name', ''),
                'lat': float(result.get('lat', 0)),
                'lon': float(result.get('lon', 0)),
                'type': result.get('type', ''),
                'importance': result.get('importance', 0)
            })

        return JsonResponse({
            'suggestions': suggestions,
            'total': len(suggestions)
        })

    except requests.RequestException as e:
        return JsonResponse({'erreur': f'Erreur de géocodage: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'erreur': str(e)}, status=500)

# API de recherche
def search_location(request):
    q = request.GET.get('q', '').strip()
    
    if not q:
        return JsonResponse({'erreur': 'Terme de recherche requis'}, status=400)
    
    # Recherche dans les zones
    zone = Zone.objects.filter(nom__icontains=q).first()
    if zone and zone.geom:
        coords = zone.geom.centroid.coords
        return JsonResponse({
            'lat': coords[1], 
            'lng': coords[0], 
            'label': zone.nom,
            'type': 'zone'
        })
    
    # Recherche dans les localisations contribuables
    loc = LocalisationContribuable.objects.filter(
        contribuable__nom__icontains=q
    ).first()
    
    if loc and loc.geom:
        coords = loc.geom.coords
        return JsonResponse({
            'lat': coords[1], 
            'lng': coords[0], 
            'label': loc.contribuable.nom,
            'type': 'contribuable'
        })
    
    return JsonResponse({'erreur': 'Aucun résultat trouvé'}, status=404)

# Vue pour ajouter une localisation
@login_required
def ajouter_localisation(request):
    zones = Zone.objects.all()
    zones_geojson = serialize('geojson', zones, 
                            geometry_field='geom', 
                            fields=('nom',))
    
    return render(request, "geolocalisation/ajouter_localisation.html", {
        "zones_geojson": zones_geojson,
    })

# Vue pour l'interface d'administration des améliorations
@permission_required('geolocalisation.add_zone')
def map_improvements_admin(request):
    """Interface d'administration pour gérer les améliorations de carte"""
    return render(request, "admin/geolocalisation/map_improvements.html", {
        'title': 'Gestion des Améliorations de Carte',
    })

# Vue pour appliquer les améliorations via AJAX
@permission_required('geolocalisation.add_zone')
def apply_improvements_ajax(request):
    """Appliquer les améliorations via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'erreur': 'Méthode non autorisée'}, status=405)
    
    try:
        import subprocess
        import sys
        from django.conf import settings
        from pathlib import Path
        
        # Chemin vers le script d'automatisation
        script_path = Path(settings.BASE_DIR) / 'scripts' / 'auto_implement_map_improvements.py'
        
        if not script_path.exists():
            return JsonResponse({
                'succès': False,
                'erreur': f'Script non trouvé: {script_path}'
            }, status=404)
        
        # Exécuter le script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=settings.BASE_DIR
        )
        
        if result.returncode == 0:
            return JsonResponse({
                'succès': True,
                'message': 'Améliorations appliquées avec succès!',
                'output': result.stdout
            })
        else:
            return JsonResponse({
                'succès': False,
                'erreur': 'Erreur lors de l\'application des améliorations',
                'details': result.stderr
            }, status=500)
            
    except Exception as e:
        return JsonResponse({
            'succès': False,
            'erreur': f'Erreur d\'exécution: {str(e)}'
        }, status=500)

# Vue pour créer une sauvegarde
@permission_required('geolocalisation.add_zone')
def create_backup_ajax(request):
    """Créer une sauvegarde via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'erreur': 'Méthode non autorisée'}, status=405)
    
    try:
        from datetime import datetime
        import shutil
        from pathlib import Path
        from django.conf import settings
        
        # Créer le dossier de sauvegarde
        backup_dir = Path(settings.BASE_DIR) / "backups" / f"manual_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Fichiers à sauvegarder
        files_to_backup = [
            'retam/geolocalisation/admin.py',
            'retam/geolocalisation/views.py',
            'retam/geolocalisation/urls.py',
            # ancien script Leaflet sauvegardé en .old
            'retam/geolocalisation/static/geolocalisation/js/admin_localisation.old.js',
            'retam/geolocalisation/static/geolocalisation/css/admin_map.css',
        ]
        
        backed_up_files = []
        for file_path in files_to_backup:
            source = Path(settings.BASE_DIR) / file_path
            if source.exists():
                dest = backup_dir / Path(file_path).name
                shutil.copy2(source, dest)
                backed_up_files.append(file_path)
        
        return JsonResponse({
            'succès': True,
            'message': f'Sauvegarde créée: {backup_dir.name}',
            'backup_dir': str(backup_dir),
            'files_backed_up': backed_up_files
        })
        
    except Exception as e:
        return JsonResponse({
            'succès': False,
            'erreur': f'Erreur lors de la sauvegarde: {str(e)}'
        }, status=500)

def google_map_view(request):
    """
    Fournit la vue contenant la carte Google Maps et les marqueurs (conserve les données existantes).
    """
    locations = []
    qs = LocalisationContribuable.objects.all()
    for obj in qs:
        lat = None
        lng = None

        # cas champs explicites
        if hasattr(obj, 'latitude') and hasattr(obj, 'longitude'):
            lat = getattr(obj, 'latitude')
            lng = getattr(obj, 'longitude')
        elif hasattr(obj, 'lat') and hasattr(obj, 'lng'):
            lat = getattr(obj, 'lat')
            lng = getattr(obj, 'lng')
        # GeoDjango PointField
        elif hasattr(obj, 'point') and obj.point:
            try:
                # point.y = latitude, point.x = longitude
                lat = obj.point.y
                lng = obj.point.x
            except Exception:
                pass

        if lat is None or lng is None:
            continue

        # nom/label à afficher
        name = None
        for attr in ('nom', 'name', 'adresse', 'label', 'contribuable_nom'):
            if hasattr(obj, attr):
                name = getattr(obj, attr)
                if name:
                    break
        if not name:
            name = str(obj)

        locations.append({
            'id': getattr(obj, 'pk', None),
            'name': name,
            'lat': float(lat),
            'lng': float(lng),
        })

    context = {
        'locations_json': json.dumps(locations, cls=DjangoJSONEncoder),
        # la clé API est disponible via le context processor
        # 'GOOGLE_MAPS_API_KEY' sera injectée automatiquement dans le template
    }
    return render(request, 'geolocalisation/google_map.html', context)