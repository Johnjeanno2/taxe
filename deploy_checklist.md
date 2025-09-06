Checklist de déploiement (rapide)

- [ ] Copier `.env.example` → `.env` et remplir
- [ ] Configurer la base PostGIS et vérifier la connexion
- [ ] Exécuter `makemigrations` / `migrate`
- [ ] Collectstatic
- [ ] Créer superuser
- [ ] Vérifier la clé Google Maps côté GCP (APIs activées, restrictions)
- [ ] Lancer les workers si nécessaire (celery)
- [ ] Configurer sauvegardes et monitoring
