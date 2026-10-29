"""The shipped test-settings templates must state their test database.

Django does not use ``NAME`` for the test database on SQLite. It uses
``TEST['NAME']``, and when that is unset it silently substitutes an in-memory
database::

    # django/db/backends/sqlite3/creation.py
    test_database_name = self.connection.settings_dict["TEST"]["NAME"] or ":memory:"

Two problems follow from relying on that substitution, which is why Cody asked for
these to be explicit:

1. **It misleads.** ``deploy/dev/local_test_settings.dev.py`` named
   ``db/default.db`` - the *development* database - in a file whose only job is to
   configure tests. A reader reasonably concludes the suite runs against that file.
   It does not; it runs in memory, and nothing says so.
2. **It hides a destructive path.** When ``TEST['NAME']`` *is* a real file,
   ``_create_test_db()`` erases it before the run. So the moment anybody makes the
   file-backed case work by setting ``TEST['NAME']``, a name without ``test`` in it
   points the test runner at real data.

These tests read the templates with ``ast``, so the commented-out examples those
files keep inside string literals are ignored, and only real assignments count.
They check what is shipped, never a developer's own ``local_test_settings.py``, so
an existing local configuration cannot fail the build.
"""

import ast
import pathlib

from django.test import SimpleTestCase

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
TEMPLATE_DIR = REPO_ROOT / 'deploy'


def _test_settings_templates():
    return sorted(TEMPLATE_DIR.glob('**/local_test_settings*.py'))


def _default_database(path):
    """The `DATABASES['default']` dict from a template, or None."""
    tree = ast.parse(path.read_text(encoding='utf-8'))
    found = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == 'DATABASES' for t in node.targets):
            continue
        try:
            databases = ast.literal_eval(node.value)
        except ValueError:
            continue
        if isinstance(databases, dict) and 'default' in databases:
            found = databases['default']
    return found


class TestShippedTestSettingsTemplates(SimpleTestCase):

    def test_templates_were_found_at_all(self):
        """Guard the guard: a move must not leave this file vacuous."""
        assert _test_settings_templates(), (
            'no deploy/**/local_test_settings*.py found under %s' % TEMPLATE_DIR
        )

    def test_sqlite_templates_state_their_test_database(self):
        offenders = []
        for path in _test_settings_templates():
            default = _default_database(path)
            if not default or 'sqlite' not in default.get('ENGINE', ''):
                continue
            test = default.get('TEST') or {}
            if not test.get('NAME'):
                offenders.append(path.relative_to(REPO_ROOT).as_posix())
        assert not offenders, (
            "these SQLite test-settings templates do not set TEST['NAME'], so Django "
            "silently substitutes an in-memory database and the file they name is not "
            "the one used: %r" % offenders
        )

    def test_a_file_backed_test_database_is_named_as_a_test_database(self):
        offenders = []
        for path in _test_settings_templates():
            default = _default_database(path)
            if not default:
                continue
            name = ((default.get('TEST') or {}).get('NAME') or '')
            if not name or name == ':memory:' or 'memory' in name:
                continue
            if 'test' not in pathlib.PurePath(name).name.lower():
                offenders.append((path.relative_to(REPO_ROOT).as_posix(), name))
        assert not offenders, (
            "a file-backed test database is erased by _create_test_db() before every "
            "run, so its name must contain 'test' and must never be the development "
            "database: %r" % offenders
        )
