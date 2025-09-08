#!/usr/bin/env bash
# Script d'aide pour déployer l'application sur un hébergement cPanel via SSH
# Usage: ssh user@host 'bash -s' < cpanel_setup.sh
set -euo pipefail

echo "Début du déploiement cPanel helper script"
# Variables à configurer: exportez-les dans l'environnement ou modifiez ici
: "${DJANGO_PROJECT_DIR:=/home/$USER/taxe/retam}"
: "${VENV_DIR:=venv}"
: "${PYTHON:=python3}"

cd "$DJANGO_PROJECT_DIR"

echo "Création et activation du virtualenv"
$PYTHON -m venv "$VENV_DIR"
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

echo "Mise à jour pip et installation des dépendances"
pip install --upgrade pip
pip install -r requirements.txt

echo "Appliquer les migrations"
python manage.py migrate --noinput

echo "Collectstatic"
python manage.py collectstatic --noinput

echo "Déploiement terminé. Configurez Passenger/Wsgi via cPanel pour pointer vers retam/passenger_wsgi.py"

echo "Rappel: définissez les variables d'environnement suivantes via cPanel ou le profil shell:\nDJANGO_SECRET_KEY, DEBUG, ALLOWED_HOSTS, CPANEL_DB_NAME, CPANEL_DB_USER, CPANEL_DB_PASSWORD, CPANEL_DB_HOST, CPANEL_DB_PORT"
