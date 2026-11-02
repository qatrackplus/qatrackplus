import importlib.util
import os
from pathlib import Path
from unittest import skipUnless
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from qatrack.qatrack_core.checks import _running_user_name, check_media_folder_permissions

# Windows has no passwd database, so the tests that create a uid without an entry in it
# cannot run there - and they are the ones that cover the Docker failure.
HAS_PWD = importlib.util.find_spec('pwd') is not None


class TestCheckMediaFolderPermissions(SimpleTestCase):
    def setUp(self):
        # Pin a non-root euid so qatrack.W001 does not appear when the suite runs as root
        # (Docker, CI containers). Tests that need root patch os.geteuid again.
        patcher = patch('os.geteuid', return_value=1000, create=True)
        patcher.start()
        self.addCleanup(patcher.stop)

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
                    assert any(
                        e.id == 'qatrack.W001' and 'local OS user for QATrack+ services' in e.hint for e in errors
                    )

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

    def test_dynamic_hint_without_a_passwd_database(self):
        """With no `pwd` module, the name comes from the environment.

        This test used to patch `getpass.getuser` and assert that name appeared in
        the hint. That passed while the code was wrong: on Python 3.12
        `getpass.getuser()` is `pwd.getpwuid(os.getuid())[0]`, so it is not a
        fallback for a failed `pwd` lookup at all - it raises the same KeyError, and
        in the Docker development overlay it did, stopping `migrate`.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            media_path = Path(temp_dir)
            with override_settings(MEDIA_ROOT=str(media_path)):
                with (
                    patch.dict('sys.modules', {'pwd': None}),
                    patch.dict(os.environ, {'LOGNAME': 'fallback_user'}, clear=False),
                    patch('os.access', return_value=False),
                ):
                    errors = check_media_folder_permissions(None)
                    assert any(
                        'fallback_user:www-data' in e.hint and 'chmod 2775' in e.hint and 'chmod 664' in e.hint
                        for e in errors
                    )

    def test_hint_quotes_media_root_containing_spaces(self):
        """A MEDIA_ROOT with a space must stay a single shell argument in the hint.

        Unquoted, `find /srv/QATrack media -type d ...` splits into two paths and the
        remediation the operator pastes silently does the wrong thing.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            media_path = Path(temp_dir) / 'QATrack media'
            media_path.mkdir()
            with override_settings(MEDIA_ROOT=str(media_path)):
                with patch('os.access', return_value=False):
                    errors = check_media_folder_permissions(None)
                    hints = [e.hint for e in errors if e.id == 'qatrack.E001']
                    assert hints
                    assert all(f"'{media_path}'" in h for h in hints)
                    assert not any(f' {media_path} ' in h for h in hints)

    def test_root_hint_uses_non_expandable_placeholder(self):
        """The root fallback must not be a shell-expandable variable.

        `$USER` expands to `root` in a root shell, so pasting the hint would chown the
        media tree to root and make the original failure worse.

        Every user-resolution path is pinned to `root`, because which one runs is
        platform-dependent: on POSIX `pwd.getpwuid(os.geteuid())` answers, and on
        Windows there is no `pwd` and no `os.geteuid`, so the environment does.
        Patching only one of them left this test passing on Linux and failing on
        Windows the moment `getpass.getuser()` stopped being the fallback.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            media_path = Path(temp_dir)
            with override_settings(MEDIA_ROOT=str(media_path)):
                with (
                    patch('os.geteuid', return_value=0, create=True),
                    patch.dict(os.environ, {'LOGNAME': 'root', 'USER': 'root', 'USERNAME': 'root'}, clear=False),
                    patch('os.access', return_value=False),
                ):
                    errors = check_media_folder_permissions(None)
                    hints = [e.hint for e in errors if e.id == 'qatrack.E001']
                    assert hints
                    assert all('<qatrack-os-user>:www-data' in h for h in hints)
                    assert not any('$USER' in h for h in hints)

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
                        and f"to '{media_path}' to create" in e.msg
                        and ':www-data' in e.hint
                        and 'chmod 2775' in e.hint
                        and 'chmod 664' in e.hint
                        for e in errors
                    )


class TestRunningUserName(SimpleTestCase):
    """The ownership hint must never be able to stop a deployment.

    `migrate` runs the system checks, so an exception escaping a check stops the
    container from starting. Measured 2026-11-02 in the Docker development overlay,
    where the container runs as the host user's uid and that uid has no passwd entry
    in the image: `KeyError: 'getpwuid(): uid not found: 1001'` escaped
    `check_media_folder_permissions` and the django service never came up.
    """

    def test_the_passwd_database_is_used_when_it_has_an_entry(self):
        assert _running_user_name()

    @skipUnless(HAS_PWD, 'no pwd module: a uid with no passwd entry cannot be created here')
    def test_a_uid_with_no_passwd_entry_falls_back_to_the_environment(self):
        """`getpass.getuser()` was the old fallback and is not one: on 3.12 it is
        the same `pwd.getpwuid(os.getuid())` call, so it raised the same KeyError."""
        with patch('pwd.getpwuid', side_effect=KeyError('uid not found: 1001')):
            with patch.dict(os.environ, {'LOGNAME': 'qatrack'}, clear=False):
                assert _running_user_name() == 'qatrack'

    @skipUnless(HAS_PWD, 'no pwd module: a uid with no passwd entry cannot be created here')
    def test_with_neither_passwd_nor_environment_it_returns_the_uid(self):
        """A number is still useful: `chown 1001:www-data` works."""
        env = {k: '' for k in ('LOGNAME', 'USER', 'LNAME', 'USERNAME')}
        with patch('pwd.getpwuid', side_effect=KeyError('uid not found: 1001')):
            with patch.dict(os.environ, env, clear=False):
                assert _running_user_name() == str(os.geteuid())

    @skipUnless(HAS_PWD, 'no pwd module: a uid with no passwd entry cannot be created here')
    def test_the_check_itself_does_not_raise_for_such_a_uid(self):
        """The regression, asserted on the check rather than on the helper."""
        with patch('pwd.getpwuid', side_effect=KeyError('uid not found: 1001')):
            with patch.dict(os.environ, {k: '' for k in ('LOGNAME', 'USER', 'LNAME', 'USERNAME')}, clear=False):
                result = check_media_folder_permissions(app_configs=None)
        assert isinstance(result, list)
