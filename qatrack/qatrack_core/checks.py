import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Warning, register


def _permissions_hint(media_root):
    """How to fix an unwritable media tree, in terms of the deployment in use.

    The generic advice names a web server user, which is right for a Linux or
    Windows install and wrong inside a container: there the process is
    `uid 999` and the directory is a docker volume, so the fix is applied from
    the host to the volume, not with `chown www-data` inside the container.
    Upgrading a pre-existing Docker installation lands on exactly this error,
    with everything in the volume still owned by the root the old image ran
    as, so the hint is worth getting right.
    """
    if os.getenv('USE_DOCKER', '0').strip().lower() in ('1', 'true', 'yes', 'on'):
        return (
            "This is a container, so fix the volume from the host: stop the stack and run "
            "`docker run --rm -v <project>_media-volume:/media alpine chown -R %s:%s /media` "
            "(or `sudo chown -R %s:%s <dir>` if you use a bind mount). The upgrade guide "
            "covers this." % (os.getuid(), os.getgid(), os.getuid(), os.getgid())
        )
    return (
        "Check folder permissions. You may need to run `sudo chown -R www-data:www-data "
        "%s` and `sudo chmod -R 775 %s` (replace www-data with your web server user)."
        % (media_root, media_root)
    )


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
                        hint=_permissions_hint(media_root),
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
                        hint=_permissions_hint(media_root),
                        id='qatrack.E001',
                    )
                )
    return errors


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


@register()
def check_pdf_renderer(app_configs, **kwargs):
    """Report an unusable PDF_RENDERER, and an opt-in that did not take.

    Both are configuration problems that otherwise surface one report at a
    time, in `logs/debug.log`, on the day somebody needs a PDF.
    """
    from qatrack.qatrack_core.utils import PDF_RENDERERS, pdf_renderer

    configured = str(getattr(settings, 'PDF_RENDERER', 'auto') or 'auto').strip().lower()
    allowed = ('auto',) + PDF_RENDERERS

    if configured not in allowed:
        # A Warning, not an Error, and crane's measurement on Windows Server
        # 2022 is why: `manage.py check` failing on this blocks `migrate` and
        # makes `manage.py qcluster` exit immediately, so a typo in a
        # presentational setting stops every scheduled report and notice -
        # while the web server carries on rendering reports perfectly well
        # through the fallback. The severity has to match what the code does,
        # and what the code does is fall back.
        return [
            Warning(
                "PDF_RENDERER is %r, which is not one of %s." % (
                    getattr(settings, 'PDF_RENDERER', None),
                    ", ".join(repr(value) for value in allowed),
                ),
                hint=(
                    "Reports will be rendered as though it were 'auto'. Set it in "
                    "qatrack/local_settings.py to one of the values above, or remove it."
                ),
                id='qatrack.W015',
            )
        ]

    if pdf_renderer() != 'weasyprint':
        return []

    try:
        import weasyprint  # noqa: F401
    except Exception as e:  # noqa: BLE001
        # Deliberately broad, and the reason this check earns its place: a
        # missing pango raises OSError from the import, not ImportError, so
        # the usual narrow catch would miss the case an administrator most
        # needs told about - they installed the libraries, and it did not take.
        return [
            Warning(
                "PDF_RENDERER selects WeasyPrint, but importing it fails: %s: %s" % (
                    type(e).__name__, e,
                ),
                hint=(
                    "Every report will be rendered by Chrome instead. On Windows, "
                    "WeasyPrint needs the pango libraries from MSYS2 - see the Windows "
                    "install guide. Check with `python -m weasyprint --info`."
                ),
                id='qatrack.W016',
            )
        ]

    return []
