Checklist déploiement cPanel (retam.limitedsn.com)

1) Préparer le dépôt
   - push sur le serveur / uploader les fichiers (project root contient manage.py et passenger_wsgi.py).

2) Créer l’application Python dans cPanel
   - cPanel > Setup Python App
   - Choisir la version Python compatible (ex: 3.11/3.10)
   - Document root: /home/USER/path/to/retam
   - Entrée WSGI: passenger_wsgi.py
   - Activer virtualenv (cPanel créera un virtualenv)

3) Installer les dépendances
   - Dans l’environnement virtuel cPanel, run:
     python -m pip install -r /home/USER/path/to/retam/requirements.txt

4) Variables d’environnement
   - Dans l’interface Python App de cPanel, définir:
     DJANGO_SETTINGS_MODULE=retam.settings
     SECRET_KEY=changeme_REPLACE_WITH_STRONG_SECRET
     DEBUG=False
     ALLOWED_HOSTS=retam.limitedsn.com
     DATABASE_URL=postgres://dbuser:dbpass@dbhost:5432/retamdb
     DEFAULT_PHONE_COUNTRY_CODE=221
     TWILIO_ACCOUNT_SID=
     TWILIO_AUTH_TOKEN=
     TWILIO_WHATSAPP_FROM=

5) Collectstatic / Migrations
   - depuis venv:
     python manage.py migrate --noinput
     python manage.py collectstatic --noinput

6) Permissions
   - chmod -R u+rwX, g+rX, o-rw sur les fichiers sensibles
   - media/ et static/ en writable par l’utilisateur

7) Configuration Apache (si nécessaire)
   - Utiliser .htaccess pour rediriger /static vers le dossier static (ex. rule fournie ci‑dessus)
   - Alternativement régler Alias dans Apache si tu as accès

8) Tests
   - Ouvrir https://retam.limitedsn.com/
   - Vérifier logs (cPanel error_log), /home/USER/tmp/passenger.log

9) Sécurité
   - Forcer HTTPS via cPanel SSL/TLS (Let's Encrypt)
   - DEBUG=False
   - Révoquer accès distant DB si possible

10) Optionnel
   - Activer cron pour tâches périodiques (celery / cron jobs)
   - Configurer sauvegardes et monitoring

