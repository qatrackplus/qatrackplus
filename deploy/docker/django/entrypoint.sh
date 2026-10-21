#!/bin/sh
set -e

export USE_DOCKER=true

echo "Creating cache table..."
python manage.py createcachetable

echo "Running migrations..."
python manage.py migrate --noinput

# Django's site record ships as name and domain "example.com", and nothing in
# this deployment changed either, which costs more than the branding:
#
#   * the pages show "example.com" in the title and navigation bar, because the
#     context processor reads the *record* - `settings.SITE_NAME` is read
#     nowhere in the codebase, so setting it alone does nothing;
#   * `site_base_url()` builds absolute URLs from the record's domain, and
#     `qatrack/reports/reports.py` uses it for report links - so a scheduled
#     report emails its recipients links to http://example.com/reports.
#
# The domain comes from SITE_DOMAIN when set, otherwise the first entry of
# ALLOWED_HOSTS, which is the hostname people reach this deployment on. Taken
# from the raw environment rather than settings.ALLOWED_HOSTS, because settings
# appends localhost and de-duplicates through a set and so does not preserve
# the order. SITE_DOMAIN exists for the case where the public hostname differs
# from what Django is told to accept, which is normal behind a proxy.
#
# Applied after migrate, because django_site exists only once the sites app has
# migrated.
#
# **It is applied on every start, not only the first.** So in this deployment
# the environment is the source of truth for those two fields: editing the site
# record in the Django admin will be undone by the next restart. That is the
# intended behaviour for a container whose configuration lives in .env - the
# alternative is a deployment whose displayed name silently depends on what
# somebody typed into the admin of a database that has since been restored
# elsewhere - but it is a behaviour change from 4.0.1, where this record was
# only ever set by hand, so it is said out loud here and in .env.example.
# Raised by CodeRabbit on PR crcrewso#18.
#
# To manage the record from the admin instead, leave SITE_NAME and SITE_DOMAIN
# unset: with neither set this block does nothing at all.
site_domain="${SITE_DOMAIN:-$(printf '%s' "${ALLOWED_HOSTS:-}" | cut -d, -f1)}"
if [ -n "${SITE_NAME:-}" ] || [ -n "$site_domain" ]; then
    echo "Applying the site name and domain to the site record..."
    SITE_RECORD_DOMAIN="$site_domain" python manage.py shell -c "
import os
from django.conf import settings
from django.contrib.sites.models import Site

fields = {}
if getattr(settings, 'SITE_NAME', ''):
    fields['name'] = settings.SITE_NAME
domain = (os.environ.get('SITE_RECORD_DOMAIN') or '').strip()
if domain:
    fields['domain'] = domain
if fields:
    Site.objects.filter(pk=settings.SITE_ID).update(**fields)
    site = Site.objects.get(pk=settings.SITE_ID)
    print('  site record: name=%r domain=%r' % (site.name, site.domain))
" || echo "WARNING: could not apply the site name or domain; the record is unchanged"
fi

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Only when the deployment asked for one. Run unconditionally, this printed
# "CommandError: You must use --username with --noinput." into the log of
# every boot of every installation that does not set these - the first thing
# a new operator sees, and it looks like the install has failed.
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ]; then
    echo "Creating superuser ${DJANGO_SUPERUSER_USERNAME}..."
    python manage.py createsuperuser --noinput || true
fi

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
