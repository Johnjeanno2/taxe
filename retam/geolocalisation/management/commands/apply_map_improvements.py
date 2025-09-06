"""
Commande Django pour appliquer automatiquement les améliorations de carte
Usage: python manage.py apply_map_improvements
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import subprocess
import sys
from pathlib import Path

class Command(BaseCommand):
    help = 'Applique automatiquement les améliorations de carte'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui serait fait sans appliquer les changements',
        )
        parser.add_argument(
            '--backup-only',
            action='store_true',
            help='Crée uniquement une sauvegarde sans appliquer les changements',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Démarrage de l\'application des améliorations de carte...')
        )

        # Chemin vers le script d'automatisation
        script_path = Path(settings.BASE_DIR) / 'scripts' / 'auto_implement_map_improvements.py'
        
        if not script_path.exists():
            self.stdout.write(
                self.style.ERROR(f'❌ Script non trouvé: {script_path}')
            )
            return

        try:
            # Construire la commande
            cmd = [sys.executable, str(script_path)]
            
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('🔍 Mode dry-run activé - aucun changement ne sera appliqué')
                )
                cmd.append('--dry-run')
            
            if options['backup_only']:
                self.stdout.write(
                    self.style.WARNING('💾 Mode backup uniquement')
                )
                cmd.append('--backup-only')

            # Exécuter le script
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=settings.BASE_DIR
            )

            if result.returncode == 0:
                self.stdout.write(
                    self.style.SUCCESS('✅ Améliorations appliquées avec succès!')
                )
                if result.stdout:
                    self.stdout.write(result.stdout)
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Erreur lors de l\'application des améliorations')
                )
                if result.stderr:
                    self.stdout.write(self.style.ERROR(result.stderr))

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erreur d\'exécution: {e}')
            )