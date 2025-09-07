web: gunicorn retam.wsgi:application --bind 0.0.0.0:$PORT
web: gunicorn retam.wsgi:application --bind 0.0.0.0:$PORT
worker: celery -A retam worker -l info
beat: celery -A retam beat -l info
