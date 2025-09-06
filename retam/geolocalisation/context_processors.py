from django.conf import settings

def google_maps_api_key(request):
    """
    Expose la clé Google Maps aux templates via le contexte.
    """
    return {
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    }