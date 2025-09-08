from pathlib import Path
import os
import environ  
import dj_database_url

# --- BASE DIR ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- SÉCURITÉ ---
# Read sensitive settings from environment for Render
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-gq@t!$mw00yw2q4750n$gg79derm5$)_xvqvae@&(f%bt59*la')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost,retam.limitedsn.com,91.234.195.123').split(',')

# --- APPLICATIONS ---
INSTALLED_APPS = [
    'grappelli',              # <- ajouté : doit être avant 'django.contrib.admin'
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.humanize',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'gestion_contribuables',
    'geolocalisation',
    
    # Libs tierces
    'crispy_forms',
    'crispy_bootstrap5',
    'django_extensions',
    'django_filters',
    'leaflet',  # Ajouter cette ligne
    'django_select2',
    'api',
]

# --- MIDDLEWARE ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise should come after SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# --- URLS ---
ROOT_URLCONF = 'retam.urls'

# --- TEMPLATES ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'geolocalisation.context_processors.google_maps_api_key',
            ],
        },
    },
]

WSGI_APPLICATION = 'retam.wsgi.application'

# --- BASE DE DONNÉES ---
# DATABASE configuration: prefer DATABASE_URL / Render, else detect cPanel/MySQL env and
# fallback to a local PostGIS for development. Note: GeoDjango features require PostGIS.
import dj_database_url

# Common env vars that may contain a full URL
DATABASE_URL = (
    os.environ.get('DATABASE_URL')
    or os.environ.get('RENDER_DATABASE_URL')
    or os.environ.get('RENDER_INTERNAL_DATABASE_URL')
    or os.environ.get('CPANEL_DATABASE_URL')
)

def _use_mysql_env():
    # detect common cPanel/MySQL env variables
    return any([
        os.environ.get('CPANEL_DB_HOST'),
        os.environ.get('CPANEL_MYSQL_HOST'),
        os.environ.get('MYSQL_HOST'),
        os.environ.get('MYSQL_DB'),
        os.environ.get('USE_MYSQL') == 'True',
    ])

if DATABASE_URL:
    # prefer a URL (assume Postgres/PostGIS when URL indicates postgres)
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, engine='django.contrib.gis.db.backends.postgis')
    }
else:
    # Prefer PostGIS/Postgres for GeoDjango. If no DATABASE_URL provided, build config
    # from POSTGRES_* env vars or fall back to sensible local defaults for development.
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': os.environ.get('POSTGRES_DB', 'c2461288c_retam_db'),
            'USER': os.environ.get('POSTGRES_USER', 'c2461288c_retam'),
            'PASSWORD': os.environ.get('ret@m-@dmin-1234', ''),
            'HOST': os.environ.get('POSTGRES_HOST', '127.0.0.1'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        }
    }

# --- VALIDATION MOT DE PASSE ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- INTERNATIONALISATION ---
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Dakar'
USE_I18N = True
USE_TZ = True

# --- FICHIERS STATIQUES & MÉDIAS ---
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# CSS personnalisé pour l'admin
ADMIN_MEDIA_PREFIX = '/static/admin/'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# --- CONFIGURATION GRAPPELLI ---
GRAPPELLI_ADMIN_TITLE = 'Administration RETAM'
GRAPPELLI_INDEX_DASHBOARD = 'retam.dashboard.CustomIndexDashboard'
GRAPPELLI_SWITCH_USER = True

# --- CONFIGURATION OSM ---
OSM_CONFIG = {
    'DEFAULT_CENTER': (14.7167, -17.4677),  # Sénégal
    'DEFAULT_ZOOM': 10,
    'MIN_ZOOM': 3,
    'MAX_ZOOM': 19,
    
    # Couches de cartes OSM disponibles
    'TILE_LAYERS': {
        'osm': {
            'url': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            'attribution': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            'maxZoom': 19,
            'name': 'OpenStreetMap'
        },
        'carto_light': {
            'url': 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            'attribution': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            'subdomains': 'abcd',
            'maxZoom': 19,
            'name': 'Carto Light'
        },
        'carto_dark': {
            'url': 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
            'attribution': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            'subdomains': 'abcd',
            'maxZoom': 19,
            'name': 'Carto Dark'
        },
        'satellite': {
            'url': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            'attribution': 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
            'maxZoom': 19,
            'name': 'Satellite'
        }
    },
    
    # Configuration de la recherche Nominatim
    'NOMINATIM': {
        'base_url': 'https://nominatim.openstreetmap.org',
        'country_codes': 'sn',  # Sénégal
        'limit': 10,
        'address_details': True,
        'accept_language': 'fr'
    },
    
    # Configuration des marqueurs
    'MARKERS': {
        'default_color': '#e74c3c',
        'zone_color': '#3388ff',
        'cluster_enabled': True,
        'cluster_options': {
            'maxClusterRadius': 50,
            'spiderfyOnMaxZoom': True,
            'showCoverageOnHover': True,
            'zoomToBoundsOnClick': True
        }
    },
    
    # Configuration des zones
    'ZONES': {
        'default_color': '#3388ff',
        'default_opacity': 0.2,
        'border_color': '#3388ff',
        'border_weight': 2
    }
}

# --- AUTRES CONFIGURATIONS ---
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Configuration pour les fichiers statiques en développement
if DEBUG:
    import mimetypes
    mimetypes.add_type("application/javascript", ".js", True)

DEFAULT_PHONE_COUNTRY_CODE = "221"

# --- CACHE CONFIGURATION ---
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/tmp/django_cache_retam',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    }
}

# --- OPTIMISATIONS SÉCURITÉ ---
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# --- CONFIGURATION GDAL/GEOS ---
if os.name == 'posix':  # macOS/Linux
    GDAL_LIBRARY_PATH = os.environ.get('GDAL_LIBRARY_PATH', '/usr/local/lib/libgdal.dylib')
    GEOS_LIBRARY_PATH = os.environ.get('GEOS_LIBRARY_PATH', '/usr/local/lib/libgeos_c.dylib')
elif os.name == 'nt':   # Windows
    GDAL_LIBRARY_PATH = os.environ.get('GDAL_LIBRARY_PATH', '')
    GEOS_LIBRARY_PATH = os.environ.get('GEOS_LIBRARY_PATH', '')

# --- LOGGING CONFIGURATION ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'geolocalisation': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
# --- LEAFLET CONFIGURATION ---
LEAFLET_CONFIG = {
    'DEFAULT_CENTER': (14.5, -14.5),  # Centre du Sénégal
    'DEFAULT_ZOOM': 7,  # Zoom pour voir tout le Sénégal
    'MIN_ZOOM': 6,  # Zoom minimum pour voir le Sénégal
    'MAX_ZOOM': 20,
    'SCALE': 'both',
    'RESET_VIEW': False,
    'NO_GLOBALS': False,
    
    # Couches OSM par défaut
    'TILES': [
        (
            'OpenStreetMap',
            'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            {
                'attribution': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                'maxZoom': 19
            }
        ),
        (
            'Carto Light',
            'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            {
                'attribution': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                'subdomains': 'abcd',
                'maxZoom': 19
            }
        ),
        (
            'Carto Dark',
            'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
            {
                'attribution': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                'subdomains': 'abcd',
                'maxZoom': 19
            }
        ),
        (
            'Satellite',
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            {
                'attribution': 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
                'maxZoom': 19
            }
        )
    ],
    
    # Configuration des plugins
    'PLUGINS': {
        'markercluster': {
            'css': [
                'https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.css',
                'https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.Default.css'
            ],
            'js': 'https://unpkg.com/leaflet.markercluster@1.4.1/dist/leaflet.markercluster.js'
        },
        'geosearch': {
            'css': ['https://unpkg.com/leaflet-geosearch@3.0.6/dist/geosearch.css'],
            'js': ['https://unpkg.com/leaflet-geosearch@3.0.6/dist/geosearch.umd.js']
        }
    },
    
    # Configuration des overlays
    'OVERLAYS': [
        ('Zones RETAM', '/geolocalisation/api/zones/geojson/', {'attribution': 'RETAM'}),
        ('Contribuables', '/geolocalisation/api/localisations/geojson/', {'attribution': 'RETAM'}),
    ]
}

# clé par défaut (préférer définir GOOGLE_MAPS_API_KEY dans l'environnement)
GOOGLE_MAPS_API_KEY = os.environ.get(
    'GOOGLE_MAPS_API_KEY',
    'AIzaSyCkcKUyv5VgfXokyxOk3x7MOBMykowbGkA'
)