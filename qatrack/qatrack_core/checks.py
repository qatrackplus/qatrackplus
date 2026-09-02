import getpass
import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Warning, register


@register()
def check_media_folder_permissions(app_configs, **kwargs):
    errors = []

    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        errors.append(
            Warning(
                'Django system check is running as root (or with sudo). Directory write permission checks may not report actual permissions for the application user.',
                hint='Run `python manage.py check` as the regular QATrack+ system user.',
                id='qatrack.W001',
            )
        )

    media_root = getattr(settings, 'MEDIA_ROOT', None)

    # Check if MEDIA_ROOT is configured and if the directory exists
    # This check is very likely unnecessary, since Django appears to recreate the folder on manage.py check, but it is here for completeness.

    if not media_root:
        errors.append(Error('The Media folder is not configured', id='qatrack.E003'))
        return errors

    media_root_path = Path(media_root)

    if not media_root_path.exists():
        errors.append(Error(f"The Media folder '{media_root}' does not exist", id='qatrack.E004'))
        return errors
    # End of redundant check

    try:
        import pwd

        app_user = pwd.getpwuid(os.geteuid()).pw_name
    except (ImportError, KeyError, AttributeError):
        app_user = getpass.getuser()

    if app_user == 'root':
        app_user = '$USER'

    perm_hint = (
        f'Check folder permissions. You may need to run `sudo chown -R {app_user}:www-data {media_root}`, '
        f'`sudo find {media_root} -type d -exec chmod 2775 {{}} +`, and '
        f'`sudo find {media_root} -type f -exec chmod 664 {{}} +`.'
    )

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
                        hint=perm_hint,
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
                            hint='Check folder permissions and disk space.',
                            id='qatrack.E002',
                        )
                    )
        else:
            parent = directory.parent
            if parent.exists() and not os.access(parent, os.W_OK):
                errors.append(
                    Error(
                        f"The Django server process does not have write permissions to '{parent}' to create '{directory}'.",
                        hint=perm_hint,
                        id='qatrack.E001',
                    )
                )
    return errors
