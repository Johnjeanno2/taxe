# Makefile pour l'automatisation des tâches de design
# Usage: make <command>

.PHONY: help design-backup design-deploy design-rollback design-validate

# Variables
PROJECT_ROOT := /Users/john/taxe
SCRIPTS_DIR := $(PROJECT_ROOT)/scripts
TIMESTAMP := $(shell date +"%Y%m%d_%H%M%S")

# Couleurs pour l'affichage
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

help: ## Afficher l'aide
	@echo "🎨 Commandes disponibles pour les patches de design:"
	@echo "=================================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

design-backup: ## Créer une sauvegarde des fichiers de design
	@echo "$(YELLOW)📁 Création d'une sauvegarde...$(NC)"
	@cd $(SCRIPTS_DIR) && ./auto_deploy.sh --backup
	@echo "$(GREEN)✅ Sauvegarde créée avec succès$(NC)"

design-deploy: ## Déployer tous les patches de design
	@echo "$(YELLOW)🚀 Déploiement des patches de design...$(NC)"
	@cd $(SCRIPTS_DIR) && ./auto_deploy.sh
	@echo "$(GREEN)✅ Patches déployés avec succès$(NC)"

design-rollback: ## Restaurer depuis une sauvegarde (usage: make design-rollback BACKUP=20241201_143022)
	@if [ -z "$(BACKUP)" ]; then \
		echo "$(RED)❌ Veuillez spécifier un timestamp de sauvegarde$(NC)"; \
		echo "Usage: make design-rollback BACKUP=20241201_143022"; \
		echo "Sauvegardes disponibles:"; \
		ls -la $(PROJECT_ROOT)/backups/ 2>/dev/null || echo "Aucune sauvegarde trouvée"; \
		exit 1; \
	fi
	@echo "$(YELLOW)🔄 Restauration depuis la sauvegarde $(BACKUP)...$(NC)"
	@cd $(SCRIPTS_DIR) && ./auto_deploy.sh --rollback $(BACKUP)
	@echo "$(GREEN)✅ Restauration terminée$(NC)"

design-validate: ## Valider les fichiers de design actuels
	@echo "$(YELLOW)🔍 Validation des fichiers de design...$(NC)"
	@python3 $(SCRIPTS_DIR)/apply_design_patches.py --validate-only 2>/dev/null || echo "$(RED)❌ Erreurs de validation détectées$(NC)"
	@echo "$(GREEN)✅ Validation terminée$(NC)"

design-status: ## Afficher le statut des sauvegardes
	@echo "$(YELLOW)📊 Statut des sauvegardes de design:$(NC)"
	@echo "Dossier de sauvegarde: $(PROJECT_ROOT)/backups/"
	@if [ -d "$(PROJECT_ROOT)/backups" ]; then \
		echo "Sauvegardes disponibles:"; \
		ls -la $(PROJECT_ROOT)/backups/ | grep design_backup || echo "Aucune sauvegarde de design trouvée"; \
	else \
		echo "$(RED)❌ Dossier de sauvegarde non trouvé$(NC)"; \
	fi

design-clean: ## Nettoyer les anciennes sauvegardes (garde les 5 plus récentes)
	@echo "$(YELLOW)🧹 Nettoyage des anciennes sauvegardes...$(NC)"
	@if [ -d "$(PROJECT_ROOT)/backups" ]; then \
		cd $(PROJECT_ROOT)/backups && \
		ls -t | grep design_backup | tail -n +6 | xargs -r rm -rf && \
		echo "$(GREEN)✅ Nettoyage terminé$(NC)"; \
	else \
		echo "$(RED)❌ Dossier de sauvegarde non trouvé$(NC)"; \
	fi

design-quick: ## Déploiement rapide sans confirmation
	@echo "$(YELLOW)⚡ Déploiement rapide des patches...$(NC)"
	@cd $(SCRIPTS_DIR) && python3 apply_design_patches.py
	@echo "$(GREEN)✅ Déploiement rapide terminé$(NC)"

design-dev: ## Mode développement avec rechargement automatique
	@echo "$(YELLOW)🔧 Mode développement activé...$(NC)"
	@echo "Surveillance des changements dans $(SCRIPTS_DIR)/design_patches.json"
	@while true; do \
		inotifywait -e modify $(SCRIPTS_DIR)/design_patches.json 2>/dev/null && \
		echo "$(YELLOW)🔄 Changement détecté, redéploiement...$(NC)" && \
		make design-quick; \
	done || echo "$(RED)❌ inotifywait non disponible, installez inotify-tools$(NC)"

# Commandes Django intégrées
django-restart: ## Redémarrer le serveur Django
	@echo "$(YELLOW)🔄 Redémarrage du serveur Django...$(NC)"
	@pkill -f "manage.py runserver" 2>/dev/null || true
	@sleep 2
	@cd $(PROJECT_ROOT) && nohup python manage.py runserver > /dev/null 2>&1 &
	@echo "$(GREEN)✅ Serveur Django redémarré$(NC)"

django-collectstatic: ## Collecter les fichiers statiques
	@echo "$(YELLOW)📦 Collection des fichiers statiques...$(NC)"
	@cd $(PROJECT_ROOT) && python manage.py collectstatic --noinput
	@echo "$(GREEN)✅ Fichiers statiques collectés$(NC)"

# Commandes pour les améliorations de carte
map-improvements: ## Appliquer automatiquement les améliorations de carte
	@echo "$(YELLOW)🗺️  Application des améliorations de carte...$(NC)"
	@cd $(SCRIPTS_DIR) && python3 auto_implement_map_improvements.py
	@echo "$(GREEN)✅ Améliorations de carte appliquées$(NC)"

map-backup: ## Créer une sauvegarde avant les améliorations de carte
	@echo "$(YELLOW)💾 Création d'une sauvegarde pour les améliorations de carte...$(NC)"
	@cd $(PROJECT_ROOT) && python manage.py apply_map_improvements --backup-only
	@echo "$(GREEN)✅ Sauvegarde créée$(NC)"

map-test: ## Tester les améliorations de carte (dry-run)
	@echo "$(YELLOW)🧪 Test des améliorations de carte (dry-run)...$(NC)"
	@cd $(PROJECT_ROOT) && python manage.py apply_map_improvements --dry-run
	@echo "$(GREEN)✅ Test terminé$(NC)"

# Commandes combinées
full-deploy: design-backup design-deploy django-collectstatic django-restart ## Déploiement complet (sauvegarde + patches + static + restart)
	@echo "$(GREEN)🎉 Déploiement complet terminé avec succès!$(NC)"

complete-map-deploy: map-backup map-improvements django-collectstatic django-restart ## Déploiement complet des améliorations de carte
	@echo "$(GREEN)🗺️  Déploiement complet des améliorations de carte terminé!$(NC)"

# Commandes de développement
dev-setup: ## Configuration initiale pour le développement
	@echo "$(YELLOW)⚙️  Configuration de l'environnement de développement...$(NC)"
	@mkdir -p $(PROJECT_ROOT)/backups
	@chmod +x $(SCRIPTS_DIR)/auto_deploy.sh
	@echo "$(GREEN)✅ Environnement configuré$(NC)"

# Tests et validation
test-patches: ## Tester les patches sans les appliquer
	@echo "$(YELLOW)🧪 Test des patches de design...$(NC)"
	@cd $(SCRIPTS_DIR) && python3 -c "import apply_design_patches; print('✅ Syntaxe Python valide')"
	@cd $(SCRIPTS_DIR) && python3 -c "import json; json.load(open('design_patches.json')); print('✅ JSON valide')"
	@echo "$(GREEN)✅ Tous les tests passent$(NC)"

# Informations système
info: ## Afficher les informations système
	@echo "$(YELLOW)ℹ️  Informations système:$(NC)"
	@echo "Projet: $(PROJECT_ROOT)"
	@echo "Scripts: $(SCRIPTS_DIR)"
	@echo "Python: $$(python3 --version 2>/dev/null || echo 'Non installé')"
	@echo "Bash: $$(bash --version | head -1)"
	@echo "Timestamp: $(TIMESTAMP)"