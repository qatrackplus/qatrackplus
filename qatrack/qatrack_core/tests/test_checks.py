from pathlib import Path
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from qatrack.qatrack_core.checks import check_media_folder_permissions


class TestCheckMediaFolderPermissions(SimpleTestCase):
    def test_media_folder_configured_and_writable(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            media_path = Path(temp_dir)
            (media_path / 'uploads').mkdir()
            (media_path / 'uploads' / 'tmp').mkdir()
            with override_settings(MEDIA_ROOT=str(media_path)):
                errors = check_media_folder_permissions(None)
                assert errors == []

    def test_writable_parent_with_no_uploads_directory(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            media_path = Path(temp_dir) / 'media'
            media_path.mkdir()
            # media exists and is writable, but 'uploads' does not exist
            with override_settings(MEDIA_ROOT=str(media_path)):
                errors = check_media_folder_permissions(None)
                assert errors == []

    def test_media_root_is_file_not_directory(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / 'file.txt'
            file_path.write_text('not a directory')
            with override_settings(MEDIA_ROOT=str(file_path)):
                errors = check_media_folder_permissions(None)
                assert len(errors) >= 1
                assert errors[0].id == 'qatrack.E001'
                assert 'does not have write permissions' in errors[0].msg

    def test_root_user_warning(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            media_path = Path(temp_dir)
            (media_path / 'uploads').mkdir()
            (media_path / 'uploads' / 'tmp').mkdir()
            with override_settings(MEDIA_ROOT=str(media_path)):
                with patch('os.geteuid', return_value=0, create=True):
                    errors = check_media_folder_permissions(None)
                    assert any(e.id == 'qatrack.W001' for e in errors)

    def test_media_root_not_configured(self):
        with override_settings(MEDIA_ROOT=None):
            errors = check_media_folder_permissions(None)
            assert len(errors) == 1
            assert errors[0].id == 'qatrack.E003'
            assert errors[0].msg == 'The Media folder is not configured'

    def test_media_root_does_not_exist(self):
        non_existent_path = '/non/existent/path/to/media'
        with override_settings(MEDIA_ROOT=non_existent_path):
            errors = check_media_folder_permissions(None)
            assert len(errors) == 1
            assert errors[0].id == 'qatrack.E004'
            assert f"The Media folder '{non_existent_path}' does not exist" in errors[0].msg

    def test_media_root_not_writable(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            media_path = Path(temp_dir)
            with override_settings(MEDIA_ROOT=str(media_path)):
                with patch('os.access', return_value=False):
                    errors = check_media_folder_permissions(None)
                    assert len(errors) >= 1
                    assert errors[0].id == 'qatrack.E001'
                    assert ':www-data' in errors[0].hint
                    assert 'chmod 2775' in errors[0].hint
                    assert 'chmod 664' in errors[0].hint

    def test_dynamic_hint_with_pwd(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            media_path = Path(temp_dir)
            with override_settings(MEDIA_ROOT=str(media_path)):
                mock_pwd = Mock()
                mock_pwd.getpwuid.return_value.pw_name = 'custom_user'
                with (
                    patch.dict('sys.modules', {'pwd': mock_pwd}),
                    patch('os.geteuid', return_value=1000, create=True),
                    patch('os.access', return_value=False),
                ):
                    errors = check_media_folder_permissions(None)
                    assert any(
                        'custom_user:www-data' in e.hint
                        and 'chmod 2775' in e.hint
                        and 'chmod 664' in e.hint
                        for e in errors
                    )

    def test_dynamic_hint_with_getpass_fallback(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            media_path = Path(temp_dir)
            with override_settings(MEDIA_ROOT=str(media_path)):
                with (
                    patch.dict('sys.modules', {'pwd': None}),
                    patch('getpass.getuser', return_value='fallback_user'),
                    patch('os.access', return_value=False),
                ):
                    errors = check_media_folder_permissions(None)
                    assert any(
                        'fallback_user:www-data' in e.hint and 'chmod 2775' in e.hint and 'chmod 664' in e.hint
                        for e in errors
                    )

    def test_file_creation_error(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            media_path = Path(temp_dir)
            (media_path / 'uploads').mkdir()
            (media_path / 'uploads' / 'tmp').mkdir()
            with override_settings(MEDIA_ROOT=str(media_path)):
                with patch('tempfile.mkstemp', side_effect=OSError('Disk full')):
                    errors = check_media_folder_permissions(None)
                    assert len(errors) >= 1
                    assert errors[0].id == 'qatrack.E002'
                    assert 'Disk full' in errors[0].msg

    def test_parent_not_writable_for_missing_dir(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            media_path = Path(temp_dir) / 'media'
            media_path.mkdir()
            # media exists, but uploads does not exist
            with override_settings(MEDIA_ROOT=str(media_path)):
                original_access = __import__('os').access

                def mock_access(path, mode):
                    if Path(path) == media_path:
                        return False
                    return original_access(path, mode)

                with patch('os.access', side_effect=mock_access):
                    errors = check_media_folder_permissions(None)
                    assert any(
                        e.id == 'qatrack.E001'
                        and ':www-data' in e.hint
                        and 'chmod 2775' in e.hint
                        and 'chmod 664' in e.hint
                        for e in errors
                    )
