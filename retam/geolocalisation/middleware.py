# geolocalisation/middleware.py
import time
import logging
from django.db import connection
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

logger = logging.getLogger('geolocalisation.performance')

class GeolocationPerformanceMiddleware(MiddlewareMixin):
    """Middleware pour surveiller les performances des requêtes de géolocalisation"""

    def process_request(self, request):
        # Marquer le début de la requête
        request._geo_start_time = time.time()
        request._geo_initial_queries = len(connection.queries)
        return None

    def process_response(self, request, response):
        # Calculer le temps de traitement
        if hasattr(request, '_geo_start_time'):
            processing_time = time.time() - request._geo_start_time
            query_count = len(connection.queries) - getattr(request, '_geo_initial_queries', 0)

            # Alertes pour les performances
            if query_count > 15:
                logger.warning(
                    f"Trop de requêtes DB ({query_count}) pour {request.path} "
                    f"en {processing_time:.2f}s"
                )

            if processing_time > 2.0:  # Plus de 2 secondes
                logger.warning(
                    f"Requête lente: {request.path} a pris {processing_time:.2f}s "
                    f"avec {query_count} requêtes DB"
                )

            # Log pour les APIs de géolocalisation
            if '/geolocalisation/api/' in request.path:
                logger.info(
                    f"API Geo: {request.path} - {processing_time:.2f}s - "
                    f"{query_count} queries - Status: {response.status_code}"
                )

            # Ajouter des headers de debug en mode développement
            if settings.DEBUG:
                response['X-Geo-Processing-Time'] = f"{processing_time:.3f}s"
                response['X-Geo-Query-Count'] = str(query_count)

        return response

class GeolocationSecurityMiddleware(MiddlewareMixin):
    """Middleware de sécurité pour les fonctionnalités de géolocalisation"""

    def process_request(self, request):
        # Vérifier les tentatives d'accès aux APIs sensibles
        if '/geolocalisation/api/' in request.path:
            # Limiter l'accès aux APIs selon les permissions
            sensitive_apis = [
                '/geolocalisation/api/apply-improvements/',
                '/geolocalisation/api/create-backup/',
            ]

            if any(api in request.path for api in sensitive_apis):
                if not request.user.is_authenticated or not request.user.has_perm('geolocalisation.add_zone'):
                    logger.warning(
                        f"Tentative d'accès non autorisé à {request.path} "
                        f"par {request.user} depuis {request.META.get('REMOTE_ADDR')}"
                    )

        return None