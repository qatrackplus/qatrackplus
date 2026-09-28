import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register()
def check_media_folder_permissions(app_configs, **kwargs):
    errors = []
    media_root = getattr(settings, 'MEDIA_ROOT', None)
    
    # Check if MEDIA_ROOT is configured and if the directory exists
    # This check is very likely unnecessary, since Django appears to recreate the folder on manage.py check, but it is here for completeness.

    if not media_root:
        errors.append(Error("The Media folder is not configured"))
        return errors
        
    media_root_path = Path(media_root)

    if not media_root_path.exists():
        errors.append(Error(f"The Media folder '{media_root}' does not exist"))
        return errors
    # End of redundant check    
    
    uploads_dirs = [
        media_root_path,
        media_root_path / 'uploads',
        media_root_path / 'uploads' / 'tmp',
    ]
    

    for directory in uploads_dirs:
        if directory.exists():
            if not directory.is_dir() or not os.access(directory, os.W_OK):
                errors.append(
                    Error(
                        f"The Django server process does not have write permissions to '{directory}'.",
                        hint=f"Check folder permissions. You may need to run `sudo chown -R www-data:www-data {media_root}` and `sudo chmod -R 775 {media_root}` (replace www-data with your web server user).",
                        id='qatrack.E001',
                    )
                )
            else:
                try:
                    fd, temp_path = tempfile.mkstemp(dir=str(directory))
                    os.close(fd)
                    Path(temp_path).unlink()
                except Exception as e:
                    errors.append(
                        Error(
                            f"The Django server process could not create a file in '{directory}': {e}",
                            hint="Check folder permissions and disk space.",
                            id='qatrack.E002',
                        )
                    )
        else:
            parent = directory.parent
            if parent.exists() and not os.access(parent, os.W_OK):
                errors.append(
                    Error(
                        f"The Django server process does not have write permissions to '{parent}' to create '{directory}'.",
                        hint=f"Check folder permissions. You may need to run `sudo chown -R www-data:www-data {media_root}`.",
                        id='qatrack.E001',
                    )
                )
    return errors


@register(Tags.database)
def check_site_domain(app_configs, databases=None, **kwargs):
    """Warn when the Django `Site` row holds something that is not a bare host.

    Django documents `Site.domain` as the fully qualified domain name: a host,
    with no scheme and no path. QATrack+ interpolates it into every absolute link
    it generates - report links, scheduled report emails, password reset mail and
    the `SITE_URL` template variable - so a value that is not a bare host
    produces links that are *well formed* and point somewhere else. Nothing
    raises, no log line appears, and the only symptom is that a link a user
    clicked did not go where they expected.

    Django does not validate this field, and the value survives a restore from
    another deployment, which is how a wrong one is most likely to arrive.

    The path case is the one that needs saying out loud, because QATrack+ already
    has a setting for it. `<host>/<appname>` looks like a reasonable way to say
    "the app is served under /<appname>", but the mechanism for that is
    `FORCE_SCRIPT_NAME` (docs/install/config.rst). Putting the prefix in the
    domain instead bypasses it and corrupts the host at the same time.

    `qatrack.qatrack_core.utils.site_url` already tolerates a scheme at runtime,
    so a scheme here is not fatal - but `context_processors.py` hands the raw
    value to templates as `SITE_URL` without going through that helper, so it is
    still worth reporting rather than relying on the rescue.

    Registered under `Tags.database` because it reads a row. That means it runs
    when the database is being checked - notably during `migrate`, so an upgrade
    reports it - rather than on every management command. It is a Warning rather
    than an Error on purpose: the value is wrong, but refusing to start is a
    worse outcome than a wrong link, and an Error here would block the very
    `migrate` a site runs to fix it.
    """

    if not databases:
        return []

    try:
        from django.contrib.sites.models import Site

        sites = list(Site.objects.values_list('pk', 'domain'))
    except Exception:
        # The table may not exist yet - this check runs during `migrate`, and on
        # a fresh install django_site is created by that very run. Any database
        # problem is something the database checks themselves will report far
        # more usefully than a re-raise from here.
        return []

    warnings = []
    for pk, domain in sites:
        raw = domain or ''

        if raw != raw.strip():
            warnings.append(
                Warning(
                    "Site %d's domain %r has leading or trailing whitespace." % (pk, raw),
                    hint="Set it to the bare host name, e.g. 'qatrack.example.com'.",
                    id='qatrack.W003',
                )
            )

        value = raw.strip()
        if not value:
            warnings.append(
                Warning(
                    "Site %d has an empty domain, so every absolute link QATrack+ "
                    "generates is missing its host." % pk,
                    hint="Set it to the bare host name, e.g. 'qatrack.example.com'.",
                    id='qatrack.W004',
                )
            )
            continue

        if '://' in value:
            warnings.append(
                Warning(
                    "Site %d's domain %r includes a URL scheme. Site.domain is a "
                    "host name, not a URL." % (pk, value),
                    hint=(
                        "Set it to the bare host name and let HTTP_OR_HTTPS choose "
                        "the scheme. QATrack+ tolerates a scheme when it builds "
                        "links, but the raw value also reaches templates as "
                        "SITE_URL, which does not."
                    ),
                    id='qatrack.W005',
                )
            )
            # Everything after the scheme is a URL, so the path test below would
            # fire on the same value for a second reason. One report is enough.
            continue

        if '/' in value.strip('/'):
            host, _, path = value.strip('/').partition('/')
            warnings.append(
                Warning(
                    "Site %d's domain %r contains a path. Every absolute link "
                    "QATrack+ generates will use %r as the host and carry %r as a "
                    "spurious path segment." % (pk, value, host, '/' + path),
                    hint=(
                        "Site.domain is the host only. If QATrack+ really is served "
                        "under a path prefix, that is what FORCE_SCRIPT_NAME is for "
                        "(see docs/install/config.rst); set the domain to %r and the "
                        "prefix separately." % host
                    ),
                    id='qatrack.W006',
                )
            )

    return warnings
