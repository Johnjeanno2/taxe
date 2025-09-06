import os
import sys

# Modifie ces chemins selon ton installation cPanel/chemin utilisateur sur le serveur
APP_DIR = os.path.dirname(os.path.abspath(__file__))  # chemin du projet
PROJECT_DIR = APP_DIR
VENV_PYTHON = None  # ex: '/home/username/virtualenv/retam/3.9/bin/python' si tu veux forcer Python

if VENV_PYTHON:
    os.environ['PATH'] = os.path.dirname(VENV_PYTHON) + os.pathsep + os.environ.get('PATH', '')

# ajoute le projet au PYTHONPATH
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'retam.settings')
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()