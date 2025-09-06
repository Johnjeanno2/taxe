#!/bin/sh
set -e

echo "Waiting for Postgres..."
# optional: use wait-for-it or similar; here we do simple sleep
sleep 2

# Run migrations and collectstatic
echo "Running migrations..."
python manage.py migrate --noinput

echo "Collectstatic..."
python manage.py collectstatic --noinput

# Exec the container command (passed from Dockerfile/CMD)
exec "$@"
