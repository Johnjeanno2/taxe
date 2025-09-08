README pour déploiement sur cPanel

But: guider le déploiement sur un hébergement cPanel sans PostGIS. Ce guide suppose que vous utiliserez une base de données MySQL fournie par cPanel/Remote DB.

Pré-requis côté hébergeur:
- Python 3.10+ disponible (ou 3.9 selon votre environnement)
- possibilité d'installer des paquets Python (pip) et compiler des extensions C (ou wheels précompilés), pour mysqlclient
- accès SSH (fortement recommandé)
- config du VirtualEnv ou gestionnaire d'applications (Passenger)

Étapes rapides:
1. Copier le dépôt sur le serveur (git clone ou upload).
2. Créer et activer un virtualenv:
   python3 -m venv venv
   source venv/bin/activate
3. Installer dépendances:
   pip install --upgrade pip
   pip install -r requirements.txt
   # note: si l'installation de mysqlclient échoue, installez les headers mysql côté système ou utilisez une wheel
4. Configurer variables d'environnement via cPanel (ou .bashrc):
   DJANGO_SECRET_KEY, DEBUG (False), ALLOWED_HOSTS, CPANEL_DB_NAME, CPANEL_DB_USER, CPANEL_DB_PASSWORD, CPANEL_DB_HOST, CPANEL_DB_PORT
5. Appliquer migrations et collectstatic:
   python manage.py migrate --noinput
   python manage.py collectstatic --noinput
6. Configurer Passenger/Wsgi selon cPanel pour pointer sur retam/passenger_wsgi.py

Limitations:
- GeoDjango/PostGIS n'est pas supporté sur MySQL: les modèles utilisant PolygonField/PointField fonctionneront mais certaines fonctions spatiales et fonctions dépendantes de PostGIS seront indisponibles.
- Pour les fonctionnalités géospatiales complètes, utilisez un hébergement offrant PostGIS (Dedibox/Render/DigitalOcean/AWS RDS avec PostGIS) ou conteneurisez l'application.

Dépannage:
- Erreur d'installation mysqlclient: installez les "dev" headers (libmysqlclient-dev sur Debian/Ubuntu) ou utilisez une wheel pré-compilée.
- Erreur lors de collectstatic: vérifiez les permissions et que STATIC_ROOT est accessible.

Si vous voulez, je peux générer un script d'installation automatisé (`cpanel_setup.sh`) pour SSH.
