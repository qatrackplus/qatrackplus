import os
import tempfile

from django.conf import settings
from django.core.checks import Error, register


@register()
def check_media_folder_permissions(app_configs, **kwargs):
    errors = []
    media_root = getattr(settings, 'MEDIA_ROOT', None)
    
    if not media_root:
        return errors
        
    if not os.path.exists(media_root):
        return errors
        
    uploads_dirs = [
        media_root,
        os.path.join(media_root, 'uploads'),
        os.path.join(media_root, 'uploads', 'tmp'),
    ]
    
    for directory in uploads_dirs:
        if os.path.exists(directory):
            if not os.access(directory, os.W_OK):
                errors.append(
                    Error(
                        f"The Django server process does not have write permissions to '{directory}'.",
                        hint=f"Check folder permissions. You may need to run `sudo chown -R www-data:www-data {media_root}` and `sudo chmod -R 775 {media_root}` (replace www-data with your web server user).",
                        id='qatrack.E001',
                    )
                )
            else:
                try:
                    fd, temp_path = tempfile.mkstemp(dir=directory)
                    os.close(fd)
                    os.remove(temp_path)
                except Exception as e:
                    errors.append(
                        Error(
                            f"The Django server process could not create a file in '{directory}': {e}",
                            hint="Check folder permissions and disk space.",
                            id='qatrack.E002',
                        )
                    )
        else:
            parent = os.path.dirname(directory)
            if os.path.exists(parent) and not os.access(parent, os.W_OK):
                errors.append(
                    Error(
                        f"The Django server process does not have write permissions to '{parent}' to create '{directory}'.",
                        hint=f"Check folder permissions. You may need to run `sudo chown -R www-data:www-data {media_root}`.",
                        id='qatrack.E001',
                    )
                )

    return errors
