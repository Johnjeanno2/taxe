#!/usr/bin/env python3
"""
Script d'automatisation pour appliquer les patches de design CSS
Usage: python apply_design_patches.py
"""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path

class DesignPatcher:
    def __init__(self, project_root="/Users/john/taxe"):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backups" / f"design_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def create_backup(self, file_path):
        """Créer une sauvegarde du fichier avant modification"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = self.backup_dir / Path(file_path).name
        shutil.copy2(file_path, backup_file)
        print(f"✅ Sauvegarde créée: {backup_file}")
        
    def apply_stat_card_patches(self, file_path):
        """Appliquer les patches pour les cartes de statistiques"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        patches = [
            # Patch 1: Améliorer les cartes de statistiques
            {
                'old': r'\.stat-card\s*{[^}]*}',
                'new': '''    .stat-card {
        background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
        border-radius: 24px;
        padding: 36px;
        box-shadow: 0 12px 40px rgba(30, 58, 92, 0.12), 0 4px 16px rgba(0, 0, 0, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.8);
        margin-bottom: 28px;
        transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(10px);
    }'''
            },
            # Patch 2: Améliorer les icônes
            {
                'old': r'\.stat-icon\s*{[^}]*}',
                'new': '''    .stat-icon {
        font-size: 2.2em;
        margin-bottom: 20px;
        color: var(--white);
        background: linear-gradient(135deg, var(--accent-color) 0%, var(--primary-color) 100%);
        width: 72px;
        height: 72px;
        border-radius: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 8px 24px rgba(121, 174, 200, 0.3);
        transition: all 0.3s ease;
        position: relative;
    }'''
            }
        ]
        
        for patch in patches:
            content = re.sub(patch['old'], patch['new'], content, flags=re.DOTALL)
            
        return content
        
    def apply_table_patches(self, file_path):
        """Appliquer les patches pour les tableaux"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Ajouter les animations et effets pour les tableaux
        table_animations = '''
    /* Animations pour tableaux */
    @keyframes shimmer {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    .stat-table tr:hover td::before {
        opacity: 1;
    }
    
    .count-badge::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
        transition: left 0.5s ease;
    }
'''
        
        # Insérer avant la fermeture du style
        content = content.replace('</style>', table_animations + '</style>')
        return content
        
    def apply_all_patches(self):
        """Appliquer tous les patches automatiquement"""
        template_files = [
            self.project_root / "retam/templates/admin/index.html",
            # Ajouter d'autres fichiers template si nécessaire
        ]
        
        for file_path in template_files:
            if file_path.exists():
                print(f"🔄 Application des patches à: {file_path}")
                
                # Créer une sauvegarde
                self.create_backup(file_path)
                
                # Appliquer les patches
                content = self.apply_stat_card_patches(file_path)
                content = self.apply_table_patches(file_path)
                
                # Écrire le fichier modifié
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                print(f"✅ Patches appliqués avec succès à: {file_path}")
            else:
                print(f"⚠️  Fichier non trouvé: {file_path}")
                
    def rollback(self, backup_timestamp):
        """Restaurer depuis une sauvegarde"""
        backup_path = self.project_root / "backups" / f"design_backup_{backup_timestamp}"
        if backup_path.exists():
            for backup_file in backup_path.glob("*"):
                original_path = self.project_root / "retam/templates/admin" / backup_file.name
                shutil.copy2(backup_file, original_path)
                print(f"🔄 Restauré: {original_path}")
        else:
            print(f"❌ Sauvegarde non trouvée: {backup_path}")

def main():
    patcher = DesignPatcher()
    
    print("🎨 Démarrage de l'application des patches de design...")
    print("=" * 50)
    
    try:
        patcher.apply_all_patches()
        print("\n🎉 Tous les patches ont été appliqués avec succès!")
        print(f"📁 Sauvegardes disponibles dans: {patcher.backup_dir}")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'application des patches: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())