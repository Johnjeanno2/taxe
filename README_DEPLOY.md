Déploiement pour RETAM (Django + GeoDjango + PostGIS)

Prérequis
- Docker & docker-compose
- PostGIS (version compatible, recommandée: 3.x)
- Clé Google Maps (restreinte par origine si possible)

Étapes (Docker / compositition)
1. Copier .env.example en .env et mettre à jour les valeurs.
   cp .env.example .env
2. Construire et démarrer les services en production:
   docker compose -f docker-compose.prod.yml up --build -d
3. Exécuter les migrations et collectstatic:
   docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate
   docker compose -f docker-compose.prod.yml run --rm web python manage.py collectstatic --noinput
4. Créer un superutilisateur:
   docker compose -f docker-compose.prod.yml run --rm web python manage.py createsuperuser

Notes PostGIS
- L'image utilisée dans docker-compose utilise PostGIS préinstallé.
- Si vous migrez une base existante, exportez/importez via pg_dump/pg_restore.

Notes Google Maps
- Assurez-vous que la clé `GOOGLE_MAPS_API_KEY` est activée pour les APIs JavaScript et Places.
- Si vous voyez l'overlay "Impossible de charger Google Maps correctement", regardez la console réseau et l'URL de la requête `maps/api/js?key=...`.

Heroku
- Utilisez le `Procfile` fourni.
- Configurez les variables d'environnement via le dashboard Heroku.
- PostGIS nécessite un add-on (par ex. Heroku Postgres + PostGIS buildpack) ou une base externe.

Sécurité
- Ne commitez pas `.env` contenant des secrets.
- Restreignez la clé Google Maps par HTTP referrers et activez la facturation pour éviter quotas bloquants.

Support
- Pour assistance, fournissez les logs `docker compose logs web` et la sortie d'erreurs du navigateur si Google Maps échoue.
