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
                hint="Use the default ISO format (%Y-%m-%d), which cannot be read two "
                     "ways, or accept only one of the two numeric orders.",
                id='qatrack.W004',
            )
        ]

    return [
        Warning(
            "An ambiguous date format is configured (%s). 03/05/2026 is the 3rd of May "
            "in most of the world and March 5th in the United States, and nothing in "
            "the date itself says which - a QC record read by someone using the other "
            "convention is silently off by months." % listed,
            hint="QATrack+ defaults to ISO 8601 (%Y-%m-%d, or %Y/%m/%d) for this "
                 "reason. A month name (%d %b %Y) is also unambiguous. This is a "
                 "warning, not an error - set it deliberately if your site needs it.",
            id='qatrack.W004',
        )
    ]
