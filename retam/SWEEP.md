# SWEEP.md - Commandes et Informations Utiles

## Structure du Projet
- **Répertoire principal**: `/Users/john/taxe/retam/`
- **Fichier manage.py**: `/Users/john/taxe/retam/manage.py`
- **Fichiers statiques**: `/Users/john/taxe/retam/staticfiles/`

## Commandes Django Utiles

### Collecter les fichiers statiques
```bash
cd /Users/john/taxe/retam && python manage.py collectstatic --noinput
```

### Démarrer le serveur de développement
```bash
cd /Users/john/taxe/retam && python manage.py runserver 0.0.0.0:8000
```

### Arrêter le serveur
```bash
pkill -f "python manage.py runserver"
```

### Migrations
```bash
cd /Users/john/taxe/retam && python manage.py makemigrations
cd /Users/john/taxe/retam && python manage.py migrate
```

## URLs Importantes
- **Carte des zones**: `http://localhost:8000/geolocalisation/zones/`
- **Admin Django**: `http://localhost:8000/admin/`

## Résolution des Problèmes

### Cache du navigateur
Pour forcer le rechargement des modifications CSS/JS:
1. Ouvrir les outils de développement (F12)
2. Clic droit sur le bouton de rechargement
3. Sélectionner "Vider le cache et recharger de force"
4. Ou utiliser Ctrl+Shift+R (Cmd+Shift+R sur Mac)

### Fichiers statiques non mis à jour
1. Exécuter `collectstatic`
2. Redémarrer le serveur Django
3. Vider le cache du navigateur

## Fonctionnalités Avancées de la Carte

### Problèmes Résolus (2025-01-04)
1. **Panel d'options masqué** : Le panel d'options avancées était masqué par défaut (`display: none`)
   - ✅ Corrigé : Panel maintenant visible par défaut
2. **Clé Google Maps** : Clé API potentiellement expirée
   - ✅ Corrigé : Ajout de fallbacks pour Street View et 3D
3. **Gestion d'erreurs** : Manque de gestion d'erreurs pour les bibliothèques externes
   - ✅ Corrigé : Ajout de vérifications pour Three.js et Google Maps

### Fonctionnalités Disponibles
- Vue 3D avec Three.js
- Street View intégré
- Overlays météo et trafic
- Outils de dessin
- Export de données
- Clustering de marqueurs
- Heatmaps
- Modes satellite, terrain, hybride

### Test des Fonctionnalités
```bash
# Vérifier les données
cd /Users/john/taxe/retam && python manage.py shell -c "
from geolocalisation.models import Zone, LocalisationContribuable
print('Zones:', Zone.objects.count())
print('Localisations:', LocalisationContribuable.objects.count())
"
```