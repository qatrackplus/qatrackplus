import os
import re
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Warning, register


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


def _directives(fmt):
    """The strptime directives in ``fmt``, in the order they appear."""
    return re.findall(r'%(.)', fmt)


def order_is_ambiguous(fmt):
    """True if this format's day and month could be read either way round.

    Ambiguity needs two things: a numeric day *and* a numeric month, with
    neither preceded by the year. ``%d %b %Y`` is safe because the month is a
    name. ``%Y-%m-%d`` is safe because nothing anywhere writes year-day-month,
    so seeing the year first settles the rest.
    """
    directives = _directives(fmt)
    if 'd' not in directives or 'm' not in directives:
        return False

    for directive in directives:
        if directive in ('Y', 'y'):
            return False
        if directive in ('d', 'm'):
            return True
    return False


def _day_first(fmt):
    for directive in _directives(fmt):
        if directive == 'd':
            return True
        if directive == 'm':
            return False
    return False


@register()
def check_ambiguous_date_formats(app_configs, **kwargs):
    """Warn about all-numeric date formats that do not lead with the year.

    QATrack+ defaults to ISO 8601 and deliberately does not suggest
    day/month/year or month/day/year anywhere in its examples. The reason is
    not tidiness. 03/05/2026 is the 3rd of May to most of the world and March
    5th in the United States, the string carries nothing that distinguishes
    them, and the US convention is entrenched enough that both readings turn
    up in the same datasets.

    In most software that is an annoyance. In a clinical QA record it is a
    date on which a machine was or was not verified, read by people trained in
    different conventions and by regulators who were not in the room. The
    profession's own habit of writing dates unambiguously exists for that
    reason, and the software should not quietly make it harder.

    So this is a warning rather than an error: a site that has decided it
    knows its own data can carry on. It should be a decision though, not
    something discovered later from a record that was read as the wrong day.

    **It is not a report about stored data, and the wording must not read like
    one.** Dates live in `DateField` and `DateTimeField` columns, so every date
    already in the database means exactly one day; there is nothing ambiguous
    to repair and this setting does not alter any of it. The exposure is at the
    boundary - what a person types and what a page shows - which is why the
    hint says so first. An upgrading site reading a warning as "your records
    may be wrong" would be being frightened by a warning about a setting.

    An upgrade also does not raise this by itself: the shipped default is ISO,
    which is unambiguous, so the check is silent unless somebody has chosen a
    numeric day/month format.
    """
    settings_to_check = [
        ('QATRACK_DATE_FORMAT', [getattr(settings, 'QATRACK_DATE_FORMAT', None)]),
        ('QATRACK_DATETIME_FORMAT', [getattr(settings, 'QATRACK_DATETIME_FORMAT', None)]),
        ('QATRACK_EXTRA_DATE_INPUT_FORMATS', getattr(settings, 'QATRACK_EXTRA_DATE_INPUT_FORMATS', [])),
        ('QATRACK_EXTRA_DATETIME_INPUT_FORMATS', getattr(settings, 'QATRACK_EXTRA_DATETIME_INPUT_FORMATS', [])),
    ]

    ambiguous = []
    for name, formats in settings_to_check:
        for fmt in formats or []:
            if fmt and order_is_ambiguous(fmt):
                ambiguous.append((name, fmt))

    if not ambiguous:
        return []

    listed = ', '.join('%s in %s' % (fmt, name) for name, fmt in ambiguous)
    orders = {_day_first(fmt) for _, fmt in ambiguous}

    if len(orders) > 1:
        # Both orders accepted at once: the same string now has two possible
        # meanings and QATrack+ resolves it by whichever is configured for
        # display. That is defined behaviour, but it is not a safe thing to
        # rely on when the data came from somewhere else.
        return [
            Warning(
                "Both day/month and month/day date formats are configured (%s). A date "
                "like 03/05/2026 is accepted by both and will be read using whichever "
                "one is your display format, so the same text entered by two people can "
                "mean two different days." % listed,
                hint="Nothing already saved is affected: QATrack+ stores dates as "
                     "dates, not as text. This is about what is typed in from now on.\n\n"
                     "Use the default ISO format (%Y-%m-%d), which cannot be read two "
                     "ways, or accept only one of the two numeric orders.",
                id='qatrack.W004',
            )
        ]

    return [
        Warning(
            "An ambiguous date format is configured (%s). 03/05/2026 is the 3rd of May "
            "in most of the world and March 5th in the United States, and nothing in "
            "the date itself says which, so someone typing or reading a date can mean "
            "a different day from the one QATrack+ records." % listed,
            hint="Nothing already saved is affected: QATrack+ stores dates as dates, "
                 "not as text, so every date in your database means exactly one day "
                 "and this setting does not change any of them. It affects only what "
                 "is typed in and shown from now on.\n\n"
                 "You are seeing this because a numeric day/month format is set; the "
                 "shipped default, ISO 8601 (%Y-%m-%d), does not raise it, and a month "
                 "name (%d %b %Y) is unambiguous too. This is a warning, not an error "
                 "- keep your format if your site wants it.",
            id='qatrack.W004',
        )
    ]


@register()
def check_translation_catalogues(app_configs, **kwargs):
    """Warn when a committed .mo no longer matches the .po beside it.

    A Warning rather than an Error on purpose. System checks run before
    `migrate` unless --skip-checks is passed, and a site part-way through
    editing its own translations should not be locked out of its migrations
    for it.
    """
    from qatrack.qatrack_core.translation_catalogues import catalogue_problems

    try:
        problems = catalogue_problems()
    except Exception:  # noqa: BLE001
        # Deliberately broad. This runs during system checks, which run before
        # `migrate`, and the docstring above promises it will not lock a site out
        # of its migrations. `OSError` alone was not enough: a malformed .po can
        # raise from the parser, and `locale_root` can raise AttributeError if
        # PROJECT_ROOT is unset. A diagnostic that cannot report is worth less
        # than a `migrate` that cannot run.
        return []

    return [
        Warning(
            problem,
            hint=(
                "The .po is what translators edit; the .mo is what Django reads. "
                "Recompile so the two agree."
            ),
            id='qatrack.W010',
        )
        for problem in problems
    ]


# A PEM certificate starts with a line like this. GnuTLS, which libldap uses on
# Debian and Ubuntu, also reads the older "X509 CERTIFICATE" and "TRUSTED
# CERTIFICATE" forms, so any word before CERTIFICATE is accepted.
PEM_CERTIFICATE = re.compile(rb'-----BEGIN [A-Z0-9 ]*CERTIFICATE-----')

AD_CERT_FILE_DOCS = (
    'See "Signing in with Active Directory over LDAPS" in the Docker installation guide, '
    'or AD_CERT_FILE in the configuration guide.'
)


@register()
def check_ad_cert_file(app_configs, **kwargs):
    """Warn when AD_CERT_FILE is set but QATrack+ cannot use the file it names.

    AD_CERT_FILE is the certificate authority (CA) that signed the directory
    server's certificate, for sign-in over LDAPS. When libldap cannot use it -
    the file is missing, unreadable, or in DER rather than PEM format - every
    LDAPS sign-in fails with "Unable to contact LDAP server" in auth.log, which
    reads like a network problem and sends people looking in the wrong place.
    This names the real cause once, at startup.

    A Warning, never an Error: system checks run before `migrate`, and a
    mistake in the sign-in settings must not stop the site starting. Local
    QATrack+ accounts keep working while it is fixed.

    The messages name the file and never include anything read from it. A CA
    certificate is public, but nothing here needs its contents.
    """
    path = getattr(settings, 'AD_CERT_FILE', None)
    if not path:
        return []

    path = Path(path)
    effect = (
        'Active Directory sign-in over LDAPS will fail, logged as "Unable to contact LDAP server" in auth.log, '
        'until this is fixed.'
    )

    if not path.exists():
        return [
            Warning(
                f'AD_CERT_FILE is set to {path}, but there is no file there. {effect}',
                hint=(
                    'Check the path, and that the file is where QATrack+ can see it. On Docker, the '
                    'certificate goes in deploy/docker/user-data/ldap/ on the server, and AD_CERT_FILE '
                    f'should be /etc/qatrack/ldap/ca.pem. {AD_CERT_FILE_DOCS}'
                ),
                id='qatrack.W011',
            )
        ]

    if not path.is_file():
        return [
            Warning(
                f'AD_CERT_FILE is set to {path}, which is a folder, not a certificate file. {effect}',
                hint=f'Set AD_CERT_FILE to the certificate file inside that folder. {AD_CERT_FILE_DOCS}',
                id='qatrack.W011',
            )
        ]

    try:
        with path.open('rb') as f:
            contents = f.read()
    except OSError as e:
        return [
            Warning(
                f'QATrack+ cannot read AD_CERT_FILE ({path}): {e.strerror or e}. {effect}',
                hint=(
                    'The file must be readable by the user QATrack+ runs as. A CA certificate is public, '
                    'not secret, so it is safe to make it readable by everyone: on Docker, run '
                    '`sudo chmod 644` on the file in deploy/docker/user-data/ldap/. '
                    f'{AD_CERT_FILE_DOCS}'
                ),
                id='qatrack.W012',
            )
        ]

    if not PEM_CERTIFICATE.search(contents):
        return [
            Warning(
                f'AD_CERT_FILE ({path}) does not hold a certificate in PEM format. {effect}',
                hint=(
                    'A PEM certificate is a text file starting with -----BEGIN CERTIFICATE-----. A .cer '
                    'file from Windows is often in DER format instead; convert it with '
                    '`openssl x509 -inform der -in ca.cer -out ca.pem`. '
                    f'{AD_CERT_FILE_DOCS}'
                ),
                id='qatrack.W013',
            )
        ]

    return []
