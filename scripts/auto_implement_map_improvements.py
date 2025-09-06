#!/usr/bin/env python3
"""
Script d'automatisation pour implémenter les améliorations de carte
Usage: python auto_implement_map_improvements.py
"""

import os
import re
import shutil
import json
from datetime import datetime
from pathlib import Path

class MapImprovementAutomator:
    def __init__(self, project_root="/Users/john/taxe"):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backups" / f"map_improvements_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.improvements_applied = []
        
    def create_backup(self, file_path):
        """Créer une sauvegarde du fichier avant modification"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = self.backup_dir / Path(file_path).relative_to(self.project_root)
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_file)
        print(f"✅ Sauvegarde créée: {backup_file}")
        
    def apply_admin_improvements(self):
        """Améliorer les fichiers admin.py pour la géolocalisation"""
        admin_file = self.project_root / "retam/geolocalisation/admin.py"
        
        if not admin_file.exists():
            print(f"❌ Fichier non trouvé: {admin_file}")
            return
            
        self.create_backup(admin_file)
        
        with open(admin_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Amélioration 1: Ajouter des configurations avancées pour les cartes
        advanced_config = '''
    # Configuration avancée de la carte
    settings_overrides = {
        'DEFAULT_CENTER': [14.7167, -16.9667],  # Mbour, Sénégal
        'DEFAULT_ZOOM': 12,
        'MIN_ZOOM': 8,
        'MAX_ZOOM': 18,
        'TILES': [
            ('OpenStreetMap', 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                'attribution': '&copy; OpenStreetMap contributors'
            }),
            ('Satellite', 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                'attribution': '&copy; Esri'
            })
        ]
    }
'''
        
        # Insérer la configuration après les imports
        if 'settings_overrides' not in content:
            import_section = content.find('from .models import')
            if import_section != -1:
                end_imports = content.find('\n\n', import_section)
                content = content[:end_imports] + '\n' + advanced_config + content[end_imports:]
                self.improvements_applied.append("Configuration avancée de carte ajoutée")
        
        # Amélioration 2: Ajouter des méthodes personnalisées aux classes Admin
        zone_admin_methods = '''
    
    def get_map_widget(self, db_field):
        """Personnaliser le widget de carte pour les zones"""
        if db_field.name == 'geom':
            return super().get_map_widget(db_field)
        return super().get_map_widget(db_field)
    
    def save_model(self, request, obj, form, change):
        """Actions personnalisées lors de la sauvegarde"""
        if not change:  # Nouveau objet
            obj.responsable = request.user
        super().save_model(request, obj, form, change)
        
        # Log de l'action
        action = "modifiée" if change else "créée"
        print(f"Zone '{obj.nom}' {action} par {request.user.username}")
'''
        
        # Ajouter les méthodes à ZoneAdmin si elles n'existent pas
        if 'def get_map_widget' not in content:
            zone_admin_class = content.find('class ZoneAdmin(LeafletGeoAdmin):')
            if zone_admin_class != -1:
                # Trouver la fin de la classe
                next_class = content.find('\nclass ', zone_admin_class + 1)
                if next_class == -1:
                    next_class = content.find('\n@admin.register', zone_admin_class + 1)
                
                if next_class != -1:
                    content = content[:next_class] + zone_admin_methods + content[next_class:]
                    self.improvements_applied.append("Méthodes personnalisées ajoutées à ZoneAdmin")
        
        # Amélioration 3: Améliorer LocalisationContribuableAdmin
        localisation_admin_methods = '''
    
    def get_queryset(self, request):
        """Optimiser les requêtes avec select_related"""
        return super().get_queryset(request).select_related('contribuable', 'zone')
    
    def get_readonly_fields(self, request, obj=None):
        """Champs en lecture seule selon les permissions"""
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.has_perm('geolocalisation.change_zone'):
            readonly.append('zone')
        return readonly
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Personnaliser les champs de clé étrangère"""
        if db_field.name == "zone":
            kwargs["queryset"] = Zone.objects.filter(
                responsable__isnull=False
            ).order_by('nom')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
'''
        
        # Ajouter les méthodes à LocalisationContribuableAdmin
        if 'def get_queryset' not in content:
            localisation_class = content.find('class LocalisationContribuableAdmin(LeafletGeoAdmin):')
            if localisation_class != -1:
                # Trouver la fin du fichier ou la prochaine définition
                end_of_file = len(content)
                content = content[:end_of_file] + localisation_admin_methods
                self.improvements_applied.append("Méthodes personnalisées ajoutées à LocalisationContribuableAdmin")
        
        # Amélioration 4: Corriger la récursion infinie dans get_urls
        recursion_fix = '''
# Enregistrer les URLs personnalisées
original_get_urls = admin.site.get_urls
admin.site.get_urls = lambda: get_admin_urls() + original_get_urls()'''

        # Chercher et remplacer la ligne problématique
        old_recursion_pattern = r'admin\.site\.get_urls\s*=\s*lambda:\s*get_admin_urls\(\)\s*\+\s*admin\.site\.get_urls\(\)'
        if re.search(old_recursion_pattern, content):
            content = re.sub(old_recursion_pattern, recursion_fix.strip(), content)
            self.improvements_applied.append("Correction de la récursion infinie dans get_urls")
            print("✅ Récursion infinie corrigée dans admin.py")

        # Sauvegarder le fichier modifié
        with open(admin_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ Améliorations appliquées à {admin_file}")
        
    def apply_views_improvements(self):
        """Améliorer les vues pour la géolocalisation"""
        views_file = self.project_root / "retam/geolocalisation/views.py"
        
        if not views_file.exists():
            print(f"❌ Fichier non trouvé: {views_file}")
            return
            
        self.create_backup(views_file)
        
        with open(views_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Amélioration 1: Ajouter une vue pour la gestion automatique des zones
        auto_zone_view = '''

# Vue pour la gestion automatique des zones
@login_required
def auto_assign_zones(request):
    """Assigner automatiquement les contribuables aux zones selon leur position"""
    if request.method == 'POST':
        try:
            # Récupérer toutes les localisations sans zone assignée
            localisations_sans_zone = LocalisationContribuable.objects.filter(
                zone__isnull=True,
                geom__isnull=False
            )
            
            assigned_count = 0
            for localisation in localisations_sans_zone:
                # Trouver la zone qui contient ce point
                zone = Zone.objects.filter(
                    geom__contains=localisation.geom
                ).first()
                
                if zone:
                    localisation.zone = zone
                    localisation.save()
                    assigned_count += 1
            
            return JsonResponse({
                'success': True,
                'assigned_count': assigned_count,
                'message': f'{assigned_count} contribuables assignés automatiquement'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

# Vue pour les statistiques de zones
@login_required
def zones_statistics(request):
    """Statistiques détaillées des zones"""
    try:
        zones_stats = Zone.objects.annotate(
            count_contribuables=Count('localisationcontribuable'),
            area=Area('geom')
        ).values(
            'id', 'nom', 'count_contribuables', 'area',
            'responsable__username', 'date_creation'
        )
        
        return JsonResponse({
            'zones': list(zones_stats),
            'total_zones': zones_stats.count(),
            'total_contribuables': sum(z['count_contribuables'] for z in zones_stats)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
'''
        
        # Ajouter les nouvelles vues si elles n'existent pas
        if 'def auto_assign_zones' not in content:
            # Ajouter à la fin du fichier
            content += auto_zone_view
            self.improvements_applied.append("Vues d'automatisation ajoutées")
            
        # Amélioration 2: Ajouter des imports nécessaires
        required_imports = [
            'from django.db.models import Area',
            'from django.contrib.auth.decorators import login_required'
        ]
        
        for import_line in required_imports:
            if import_line not in content:
                # Ajouter après les autres imports
                import_section = content.find('from django.http import')
                if import_section != -1:
                    end_line = content.find('\n', import_section)
                    content = content[:end_line] + '\n' + import_line + content[end_line:]
                    self.improvements_applied.append(f"Import ajouté: {import_line}")
        
        # Sauvegarder le fichier modifié
        with open(views_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ Améliorations appliquées à {views_file}")
        
    def apply_urls_improvements(self):
        """Améliorer les URLs pour la géolocalisation"""
        urls_file = self.project_root / "retam/geolocalisation/urls.py"
        
        if not urls_file.exists():
            print(f"❌ Fichier non trouvé: {urls_file}")
            return
            
        self.create_backup(urls_file)
        
        with open(urls_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Ajouter les nouvelles URLs
        new_urls = [
            "    path('api/auto-assign-zones/', views.auto_assign_zones, name='auto_assign_zones'),",
            "    path('api/zones/statistics/', views.zones_statistics, name='zones_statistics'),"
        ]
        
        for url in new_urls:
            if url.strip() not in content:
                # Ajouter avant la fermeture de urlpatterns
                closing_bracket = content.rfind(']')
                if closing_bracket != -1:
                    content = content[:closing_bracket] + url + '\n' + content[closing_bracket:]
                    self.improvements_applied.append(f"URL ajoutée: {url.strip()}")
        
        # Sauvegarder le fichier modifié
        with open(urls_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ Améliorations appliquées à {urls_file}")
        
    def apply_javascript_improvements(self):
        """Améliorer les fichiers JavaScript"""
        js_file = self.project_root / "retam/geolocalisation/static/geolocalisation/js/admin_localisation.js"
        
        if not js_file.exists():
            print(f"❌ Fichier non trouvé: {js_file}")
            return
            
        self.create_backup(js_file)
        
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Amélioration: Ajouter des fonctions utilitaires
        utility_functions = '''

        // Fonctions utilitaires pour la gestion des zones
        window.MapUtils = {
            // Centrer la carte sur une zone spécifique
            centerOnZone: function(zoneId) {
                if (zonesLayer) {
                    zonesLayer.eachLayer(function(layer) {
                        if (layer.zoneId === zoneId) {
                            map.fitBounds(layer.getBounds(), {padding: [20, 20]});
                            layer.openPopup();
                        }
                    });
                }
            },
            
            // Assigner automatiquement toutes les zones
            autoAssignZones: function() {
                fetch('/geolocalisation/api/auto-assign-zones/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification(data.message, 'success');
                        // Recharger les zones pour voir les changements
                        loadZones();
                    } else {
                        showNotification('Erreur: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    showNotification('Erreur de connexion: ' + error, 'error');
                });
            },
            
            // Obtenir les statistiques des zones
            getZoneStatistics: function() {
                return fetch('/geolocalisation/api/zones/statistics/')
                    .then(response => response.json());
            },
            
            // Exporter les données de la carte
            exportMapData: function() {
                this.getZoneStatistics().then(data => {
                    const blob = new Blob([JSON.stringify(data, null, 2)], {
                        type: 'application/json'
                    });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `zones_statistics_${new Date().toISOString().split('T')[0]}.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                });
            }
        };
        
        // Ajouter des boutons d'action dans l'interface
        function addActionButtons() {
            const mapContainer = document.querySelector('.leaflet-container');
            if (mapContainer && mapContainer.parentElement) {
                const buttonContainer = document.createElement('div');
                buttonContainer.className = 'map-action-buttons';
                buttonContainer.innerHTML = `
                    <div class="btn-group" style="margin: 15px 0; display: flex; gap: 10px; flex-wrap: wrap;">
                        <button onclick="MapUtils.autoAssignZones()" class="btn btn-primary">
                            <i class="fas fa-magic"></i> Assigner automatiquement
                        </button>
                        <button onclick="MapUtils.exportMapData()" class="btn btn-secondary">
                            <i class="fas fa-download"></i> Exporter données
                        </button>
                        <button onclick="loadZones()" class="btn btn-info">
                            <i class="fas fa-refresh"></i> Actualiser zones
                        </button>
                    </div>
                `;
                
                mapContainer.parentElement.insertBefore(buttonContainer, mapContainer);
            }
        }
'''
        
        # Ajouter les fonctions utilitaires si elles n'existent pas
        if 'window.MapUtils' not in content:
            # Ajouter avant la fermeture du script
            closing_brace = content.rfind('});')
            if closing_brace != -1:
                content = content[:closing_brace] + utility_functions + '\n        // Ajouter les boutons d\'action\n        addActionButtons();\n' + content[closing_brace:]
                self.improvements_applied.append("Fonctions utilitaires JavaScript ajoutées")
        
        # Sauvegarder le fichier modifié
        with open(js_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ Améliorations appliquées à {js_file}")
        
    def apply_css_improvements(self):
        """Améliorer les styles CSS"""
        css_file = self.project_root / "retam/geolocalisation/static/geolocalisation/css/admin_map.css"
        
        if not css_file.exists():
            print(f"❌ Fichier non trouvé: {css_file}")
            return
            
        self.create_backup(css_file)
        
        with open(css_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Ajouter des styles pour les nouveaux boutons d'action
        action_buttons_css = '''

/* Styles pour les boutons d'action de la carte */
.map-action-buttons {
    background: rgba(255, 255, 255, 0.95);
    padding: 15px;
    border-radius: 10px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    border-left: 4px solid #79aec8;
    margin-bottom: 15px;
}

.map-action-buttons .btn-group {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
}

.map-action-buttons .btn {
    padding: 10px 18px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    gap: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.map-action-buttons .btn-primary {
    background: linear-gradient(135deg, #79aec8, #0a384f);
    color: white;
}

.map-action-buttons .btn-primary:hover {
    background: linear-gradient(135deg, #0a384f, #79aec8);
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(121, 174, 200, 0.4);
}

.map-action-buttons .btn-secondary {
    background: linear-gradient(135deg, #6c757d, #495057);
    color: white;
}

.map-action-buttons .btn-secondary:hover {
    background: linear-gradient(135deg, #495057, #6c757d);
    transform: translateY(-2px);
}

.map-action-buttons .btn-info {
    background: linear-gradient(135deg, #17a2b8, #138496);
    color: white;
}

.map-action-buttons .btn-info:hover {
    background: linear-gradient(135deg, #138496, #17a2b8);
    transform: translateY(-2px);
}

/* Animation de chargement pour les boutons */
.btn.loading {
    position: relative;
    color: transparent;
}

.btn.loading::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 16px;
    height: 16px;
    border: 2px solid transparent;
    border-top: 2px solid currentColor;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: translate(-50%, -50%) rotate(0deg); }
    100% { transform: translate(-50%, -50%) rotate(360deg); }
}

/* Responsive pour les boutons d'action */
@media (max-width: 768px) {
    .map-action-buttons .btn-group {
        flex-direction: column;
        gap: 8px;
    }
    
    .map-action-buttons .btn {
        width: 100%;
        justify-content: center;
    }
}
'''
        
        # Ajouter les styles si ils n'existent pas
        if '.map-action-buttons' not in content:
            content += action_buttons_css
            self.improvements_applied.append("Styles CSS pour boutons d'action ajoutés")
        
        # Sauvegarder le fichier modifié
        with open(css_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ Améliorations appliquées à {css_file}")
        
    def apply_all_improvements(self):
        """Appliquer toutes les améliorations automatiquement"""
        print("🚀 Démarrage de l'implémentation automatique des améliorations de carte...")
        print("=" * 70)
        
        try:
            # Appliquer les améliorations dans l'ordre
            self.apply_admin_improvements()
            self.apply_views_improvements()
            self.apply_urls_improvements()
            self.apply_javascript_improvements()
            self.apply_css_improvements()
            
            # Créer un rapport des améliorations
            self.create_improvement_report()
            
            print("\n🎉 Toutes les améliorations ont été appliquées avec succès!")
            print(f"📁 Sauvegardes disponibles dans: {self.backup_dir}")
            print(f"📊 {len(self.improvements_applied)} améliorations appliquées")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'application des améliorations: {e}")
            return False
            
        return True
        
    def create_improvement_report(self):
        """Créer un rapport des améliorations appliquées"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'improvements_applied': self.improvements_applied,
            'backup_location': str(self.backup_dir),
            'total_improvements': len(self.improvements_applied)
        }
        
        report_file = self.backup_dir / "improvement_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        print(f"📋 Rapport créé: {report_file}")

def main():
    automator = MapImprovementAutomator()
    success = automator.apply_all_improvements()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())