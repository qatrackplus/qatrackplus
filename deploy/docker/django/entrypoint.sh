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

# The cache table used to be created here, before migrate. It is now created by
# qatrack_core.0002_cache_table, so migrate covers it and running the command
# first is redundant. qatrack.W013 reports a cache table that is still missing -
# a router that keeps it off the application database, for instance.
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

# Without SECRET_KEY in .env, the key QATrack+ generated lives only in the
# user-data volume, which the nightly backup does not include. Say so once per
# start, here rather than in the settings, which every process imports. The
# notice names the file and never shows the key; with SECRET_KEY set it is empty.
# It is only information, so a failure here must not stop QATrack+ starting.
python -c '
from qatrack.docker_settings import secret_key_notice
notice = secret_key_notice()
if notice:
    print(notice)
' || echo "Could not check where the secret key is kept." >&2

echo "Starting Gunicorn..."
exec gunicorn qatrack.wsgi:application -w 2 -b 0.0.0.0:8000
