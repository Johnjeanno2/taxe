#!/usr/bin/env python
"""
Script de test pour diagnostiquer les problèmes de la carte avancée
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retam.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from geolocalisation.models import Zone, LocalisationContribuable

def test_carte_access():
    """Test d'accès à la carte avancée"""
    print("=== TEST D'ACCÈS À LA CARTE AVANCÉE ===")

    # Créer un client de test
    client = Client()

    # Test sans authentification
    print("\n1. Test sans authentification:")
    response = client.get('/geolocalisation/zones/')
    print(f"   Status: {response.status_code}")
    if response.status_code == 302:
        print(f"   Redirection vers: {response.url}")

    # Test avec authentification
    print("\n2. Test avec authentification:")
    user = User.objects.first()
    if user:
        client.force_login(user)
        response = client.get('/geolocalisation/zones/')
        print(f"   Status: {response.status_code}")
        print(f"   Template utilisé: {response.templates[0].name if response.templates else 'Aucun'}")

        # Vérifier le contenu
        content = response.content.decode('utf-8')
        print(f"   Contient 'toggleAdvancedPanel': {'toggleAdvancedPanel' in content}")
        print(f"   Contient 'osm_map_integration.js': {'osm_map_integration.js' in content}")
        print(f"   Contient 'advanced-map-panel': {'advanced-map-panel' in content}")
    else:
        print("   Aucun utilisateur trouvé")

def test_data():
    """Test des données"""
    print("\n=== TEST DES DONNÉES ===")
    zones_count = Zone.objects.count()
    localisations_count = LocalisationContribuable.objects.count()
    users_count = User.objects.count()

    print(f"Zones: {zones_count}")
    print(f"Localisations: {localisations_count}")
    print(f"Utilisateurs: {users_count}")

    if zones_count > 0:
        zone = Zone.objects.first()
        print(f"Première zone: {zone.nom} (geom: {'Oui' if zone.geom else 'Non'})")

    if localisations_count > 0:
        loc = LocalisationContribuable.objects.first()
        print(f"Première localisation: {loc.contribuable.nom if loc.contribuable else 'N/A'}")

def test_static_files():
    """Test des fichiers statiques"""
    print("\n=== TEST DES FICHIERS STATIQUES ===")

    files_to_check = [
        'geolocalisation/js/osm_map_integration.js',
        'geolocalisation/js/admin_map_search.js',
        'geolocalisation/css/admin_map.css'
    ]

    for file_path in files_to_check:
        full_path = f'/Users/john/taxe/retam/geolocalisation/static/{file_path}'
        exists = os.path.exists(full_path)
        print(f"   {file_path}: {'✅' if exists else '❌'}")
        if exists:
            size = os.path.getsize(full_path)
            print(f"      Taille: {size} bytes")

if __name__ == '__main__':
    test_data()
    test_static_files()
    test_carte_access()