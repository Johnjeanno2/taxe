Guide Passenger/WSGI pour déployer RETAM sur cPanel

Prérequis
- Accès SSH sur le compte cPanel (recommandé)
- Python 3.10+ disponible
- Passenger (Application Manager) installé sur le serveur cPanel (la plupart des cPanel gérés l'ont)
- Variables d'environnement configurables via l'interface "Setup Python App" ou via le profil shell

Étapes détaillées
1) Déployez le code sur le serveur
   - git clone <votre_repo> ~/retam
   - cd ~/retam/retam

2) Créez l'application Python dans cPanel (Setup Python App)
   - Application root: /home/<user>/retam/retam
   - Application URL: https://retam.limitedsn.com
   - Application startup file: `passenger_wsgi.py`
   - Python version: 3.10 (ou 3.x compatible)

3) Virtualenv et dépendances
   - Si cPanel fournit une interface pour le virtualenv, utilisez-la; sinon via SSH:
     ```bash
     cd ~/retam/retam
     python3 -m venv venv
     source venv/bin/activate
     pip install --upgrade pip
     pip install -r ../requirements.txt
     ```
   - Remarque: `requirements.txt` contient `psycopg2-binary` et d'autres paquets natifs; si l'installation échoue, installez les headers requis ou demandez au support cPanel de fournir une image/packagé.

4) Variables d'environnement dans l'interface cPanel (Environment variables)
   - DJANGO_SECRET_KEY
   - DEBUG (False en production)
   - ALLOWED_HOSTS (ou laisser vide pour utiliser la valeur par défaut dans `settings.py`)
   - DATABASE_URL ou POSTGRES_DB/POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_HOST/POSTGRES_PORT
   - GOOGLE_MAPS_API_KEY

5) Fichier `passenger_wsgi.py`
Le dépôt contient `retam/passenger_wsgi.py`. Exemple minimal (vérifiez le chemin du projet et du venv):

```python
import os
import sys

# Chemin vers le répertoire retam (contenant manage.py)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# Activer le virtualenv (si vous utilisez un venv nommé 'venv' à la racine retam)
VENV_PATH = os.path.join(PROJECT_DIR, 'venv')
ACTIVATE = os.path.join(VENV_PATH, 'bin', 'activate_this.py')
if os.path.exists(ACTIVATE):
    with open(ACTIVATE) as f:
        code = compile(f.read(), ACTIVATE, 'exec')
        exec(code, dict(__file__=ACTIVATE))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retam.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

6) Static files
- Dans cPanel, définissez `STATIC_ROOT` (déjà défini dans `settings.py` comme `staticfiles` à la racine du projet).
- Exécutez `python manage.py collectstatic --noinput` (via SSH ou via la console cPanel si disponible).
- Assurez-vous que `staticfiles/` est lisible par le serveur web.

7) SSL
- Configurez un certificat SSL pour `retam.limitedsn.com` via cPanel (Let’s Encrypt ou autre).

8) Redémarrer l'application
- Utilisez l'interface cPanel pour redémarrer l'application Python; ou `touch tmp/restart.txt` si Passenger l'exige.

Dépannage rapide
- Erreurs d'import lors du démarrage: vérifiez `sys.path` et que le `venv` est activé dans `passenger_wsgi.py`.
- Erreurs psycopg2: installez les headers PostgreSQL côté serveur ou utilisez `psycopg2-binary` (déjà présent), mais attention aux environnements qui interdisent les wheels binaires.
- 500 interne après migration: vérifier les logs Passenger (cPanel) et `django` logs (STDERR) pour la trace.

Si vous voulez, j'ajoute une section `passenger_restart.sh` ou j'insère une note dans `cpanel_setup.sh` pour appeler `touch tmp/restart.txt` après `collectstatic`. Voulez-vous que j'ajoute cela ?
