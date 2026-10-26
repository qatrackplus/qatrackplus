#!/bin/sh
set -e

# Wait for database
echo "Waiting for postgres..."
DB_HOST="${POSTGRES_HOST:-postgres}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-qatrackplus}"
DB_WAIT_TIMEOUT="${DB_WAIT_TIMEOUT:-60}"
elapsed=0
while ! pg_isready -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME"; do
  elapsed=$((elapsed + 1))
  if [ "$elapsed" -ge "$DB_WAIT_TIMEOUT" ]; then
    echo "PostgreSQL not ready after ${DB_WAIT_TIMEOUT}s" >&2
    exit 1
  fi
  sleep 1
done
echo "PostgreSQL started"

export USE_DOCKER=true

echo "Creating cache table..."
python manage.py createcachetable

echo "Running migrations..."
python manage.py migrate --noinput

# The Site record's domain is what links in emails and reports point to, and
# its name is shown at the top of each page. SITE_DOMAIN and SITE_NAME in .env
# are applied on every start; without them, a record still at Django's default
# (example.com) is filled in once from ALLOWED_HOSTS.
echo "Configuring the site's domain and name..."
python manage.py configure_site --domain "${SITE_DOMAIN:-}" --name "${SITE_NAME:-}"

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gunicorn qatrack.wsgi:application -w 2 -b 0.0.0.0:8000
