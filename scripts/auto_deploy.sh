#!/bin/bash

# Script de déploiement automatique des patches de design
# Usage: ./auto_deploy.sh [--backup] [--rollback timestamp]

set -e  # Arrêter en cas d'erreur

PROJECT_ROOT="/Users/john/taxe"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction d'affichage avec couleurs
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Fonction de sauvegarde
create_backup() {
    log_info "Création de la sauvegarde..."
    
    mkdir -p "$BACKUP_DIR/design_backup_$TIMESTAMP"
    
    # Sauvegarder les fichiers templates
    if [ -f "$PROJECT_ROOT/retam/templates/admin/index.html" ]; then
        cp "$PROJECT_ROOT/retam/templates/admin/index.html" "$BACKUP_DIR/design_backup_$TIMESTAMP/"
        log_success "Sauvegarde créée: design_backup_$TIMESTAMP"
    else
        log_error "Fichier template non trouvé"
        exit 1
    fi
}

# Fonction de restauration
rollback() {
    local backup_timestamp=$1
    local backup_path="$BACKUP_DIR/design_backup_$backup_timestamp"
    
    if [ -d "$backup_path" ]; then
        log_info "Restauration depuis la sauvegarde: $backup_timestamp"
        
        if [ -f "$backup_path/index.html" ]; then
            cp "$backup_path/index.html" "$PROJECT_ROOT/retam/templates/admin/"
            log_success "Fichier restauré avec succès"
        else
            log_error "Fichier de sauvegarde non trouvé"
            exit 1
        fi
    else
        log_error "Sauvegarde non trouvée: $backup_timestamp"
        exit 1
    fi
}

# Fonction d'application des patches
apply_patches() {
    log_info "Application des patches de design..."
    
    # Vérifier que Python est disponible
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 n'est pas installé"
        exit 1
    fi
    
    # Exécuter le script Python
    cd "$SCRIPTS_DIR"
    python3 apply_design_patches.py
    
    if [ $? -eq 0 ]; then
        log_success "Patches appliqués avec succès"
    else
        log_error "Erreur lors de l'application des patches"
        exit 1
    fi
}

# Fonction de validation
validate_changes() {
    log_info "Validation des changements..."
    
    # Vérifier que le fichier existe et n'est pas vide
    if [ -f "$PROJECT_ROOT/retam/templates/admin/index.html" ] && [ -s "$PROJECT_ROOT/retam/templates/admin/index.html" ]; then
        log_success "Fichier template validé"
    else
        log_error "Fichier template invalide ou vide"
        exit 1
    fi
    
    # Vérifier la syntaxe HTML basique
    if grep -q "</html>" "$PROJECT_ROOT/retam/templates/admin/index.html"; then
        log_success "Structure HTML validée"
    else
        log_warning "Structure HTML potentiellement incomplète"
    fi
}

# Fonction de redémarrage du serveur Django (optionnel)
restart_django() {
    log_info "Redémarrage du serveur Django..."
    
    # Chercher le processus Django
    DJANGO_PID=$(pgrep -f "manage.py runserver" || true)
    
    if [ ! -z "$DJANGO_PID" ]; then
        kill $DJANGO_PID
        log_info "Serveur Django arrêté"
        
        # Attendre un peu puis redémarrer
        sleep 2
        cd "$PROJECT_ROOT"
        nohup python manage.py runserver > /dev/null 2>&1 &
        log_success "Serveur Django redémarré"
    else
        log_warning "Aucun serveur Django en cours d'exécution"
    fi
}

# Fonction principale
main() {
    echo "🎨 Déploiement automatique des patches de design"
    echo "================================================"
    
    case "${1:-}" in
        --rollback)
            if [ -z "${2:-}" ]; then
                log_error "Timestamp de sauvegarde requis pour le rollback"
                echo "Usage: $0 --rollback YYYYMMDD_HHMMSS"
                exit 1
            fi
            rollback "$2"
            ;;
        --backup)
            create_backup
            ;;
        *)
            # Déploiement normal
            create_backup
            apply_patches
            validate_changes
            
            # Demander si on veut redémarrer Django
            read -p "Voulez-vous redémarrer le serveur Django ? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                restart_django
            fi
            
            log_success "Déploiement terminé avec succès!"
            log_info "Sauvegarde disponible: design_backup_$TIMESTAMP"
            ;;
    esac
}

# Fonction d'aide
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --backup          Créer uniquement une sauvegarde"
    echo "  --rollback TIME   Restaurer depuis une sauvegarde (format: YYYYMMDD_HHMMSS)"
    echo "  --help           Afficher cette aide"
    echo ""
    echo "Exemples:"
    echo "  $0                      # Déploiement normal avec sauvegarde"
    echo "  $0 --backup            # Créer une sauvegarde uniquement"
    echo "  $0 --rollback 20241201_143022  # Restaurer une sauvegarde"
}

# Vérifier les arguments
if [ "${1:-}" = "--help" ]; then
    show_help
    exit 0
fi

# Exécuter la fonction principale
main "$@"