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
echo "
If you will use a remote Postgres with PostGIS, prefer setting DATABASE_URL or POSTGRES_* vars:
  DATABASE_URL=postgres://USER:PASSWORD@HOST:PORT/NAME
  or POSTGRES_DB/POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_HOST/POSTGRES_PORT
"

echo "Tester la connexion à la base Postgres distante (si DATABASE_URL défini)"
python3 - <<'PY'
import os
from urllib.parse import urlparse
try:
	import psycopg2
except Exception as e:
	print('psycopg2 non installé dans le virtualenv:', e)
	raise SystemExit(1)

url = os.environ.get('DATABASE_URL')
if url:
	parsed = urlparse(url)
	try:
		conn = psycopg2.connect(dbname=parsed.path.lstrip('/'), user=parsed.username, password=parsed.password, host=parsed.hostname, port=parsed.port)
		print('Connexion Postgres OK')
		cur = conn.cursor()
		try:
			cur.execute("SELECT PostGIS_Full_Version();")
			print('PostGIS disponible:', cur.fetchone())
		except Exception as e:
			print('PostGIS non disponible ou accès refusé:', e)
		cur.close()
		conn.close()
	except Exception as e:
		print('Connexion Postgres échouée:', e)
		raise SystemExit(2)
else:
	echo('DATABASE_URL non défini, vous pouvez définir POSTGRES_* vars à la place')
PY

