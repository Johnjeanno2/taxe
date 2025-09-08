Déployer RETAM sur cPanel en utilisant une base Postgres + PostGIS distante

Contexte
- cPanel classique fournit souvent MySQL en natif. Pour garder les fonctionnalités GeoDjango, il faut une base Postgres avec l'extension PostGIS. Dans ce guide, on suppose que vous avez accès à une instance Postgres distante (chez votre fournisseur cloud) ou un service DB externe qui offre PostGIS.

Options
1) Utiliser une base Postgres distante gérée (recommandé)
   - Fournisseurs: Render, Aiven, AWS RDS, DigitalOcean Managed DB (vérifier PostGIS), etc.
   - Avantage: PostGIS géré, pas besoin d'installer d'extensions sur cPanel.
2) Installer Postgres/PostGIS sur le même serveur cPanel (rare, exige privilèges root)
   - Pas recommandé pour cPanel partagé.

Étapes pour la configuration (cPanel + Postgres distant)
1. Obtenez les paramètres de connexion Postgres distant : HOST, PORT, NAME, USER, PASSWORD. Assurez-vous que l'IP du serveur cPanel est autorisée dans les règles firewall de la base.
2. Dans cPanel, configurez les variables d'environnement (ou exportez-les dans le profil shell utilisé par Passenger). Variables requises:
   - DATABASE_URL=postgres://USER:PASSWORD@HOST:PORT/NAME
   - OU définir séparément: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT
3. Sur le serveur cPanel (via SSH), activez le virtualenv et installez les dépendances:

   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt

4. Test de connexion DB (depuis le serveur cPanel):

   python - <<'PY'
import os
from urllib.parse import urlparse
import psycopg2

url = os.environ.get('DATABASE_URL')
if url:
    parsed = urlparse(url)
    conn = psycopg2.connect(dbname=parsed.path.lstrip('/'), user=parsed.username, password=parsed.password, host=parsed.hostname, port=parsed.port)
    print('Connexion OK')
    conn.close()
else:
    print('DATABASE_URL non défini')
PY

5. Appliquer migrations et collectstatic:
   python manage.py migrate --noinput
   python manage.py collectstatic --noinput

6. Vérifier PostGIS
- Depuis votre instance Postgres, connectez-vous et lancez:
  CREATE EXTENSION IF NOT EXISTS postgis;
  -- puis vérifier: SELECT PostGIS_Full_Version();

- Si la commande CREATE EXTENSION échoue, votre instance n'autorise pas l'installation d'extensions : contactez votre prestataire.

Notes / Dépannage
- Autorisation réseau: assurez-vous que le serveur cPanel peut atteindre la base distante sur le port 5432.
- Si vous ne pouvez pas autoriser la sortie réseau, envisagez d'héberger l'application ailleurs (Render, Docker sur VPS) ou configurer un tunnel SSH sécurisé.
- Pour la sécurité, configurez les variables d'environnement via l'interface cPanel (Application Manager) ou via le profil shell et évitez de stocker les secrets dans le repo.

Si vous voulez, j'ajoute des commandes automatiques dans `cpanel_setup.sh` pour tester la connexion et indiquer les étapes à suivre — confirmez et je modifie le script.
