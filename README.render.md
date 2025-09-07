Déploiement sur Render

1) Créez un nouveau service Web (Python) sur Render et liez-le à votre repository GitHub.
2) Dans les variables d'environnement du service, ajoutez :
   - DATABASE_URL (format postgres://user:pass@host:5432/dbname)
   - DJANGO_SECRET_KEY
   - GOOGLE_MAPS_API_KEY
   - DEBUG (False pour production)

3) Build et Start commands sont gérés par `render.yaml` / `Procfile`.

Notes:
- Assurez-vous d'utiliser une base Postgres avec PostGIS si vous avez besoin des fonctionnalités GeoDjango.
- Si vous utilisez la base Relation (Render managed DB), Render fournit un hostname et un port ; utilisez le `DATABASE_URL` complet.
- Vérifiez que `requirements.txt` contient `gunicorn` et `dj-database-url`.
