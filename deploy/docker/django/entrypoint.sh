#!/bin/sh
set -e

export USE_DOCKER=true

echo "Creating cache table..."
python manage.py createcachetable

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Creating superuser..."
python manage.py createsuperuser --noinput || true

echo "Starting application..."

case "${DEBUG:-false}" in
    1|true|True|TRUE|yes|Yes|YES|on|On|ON)
        echo "Development mode, starting Django development server"
        exec python manage.py runserver 0.0.0.0:8000
        ;;
    *)
        echo "Production mode, starting Gunicorn..."
        exec gunicorn qatrack.wsgi:application -w 2 -b 0.0.0.0:8000
        ;;
esac
