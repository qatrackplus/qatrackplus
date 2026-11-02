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

3. **The rule is wider than SQLite.** Cody, 2026-11-02: anything the suite creates
   carries ``test`` in its name. For the postgres, mysql and mssql templates
   ``TEST['NAME']`` is unset on purpose - Django derives ``test_`` + ``NAME`` - so
   the name to check is the one Django *derives*, not the one written down.

These tests read the templates with ``ast``, so the commented-out examples those
files keep inside string literals are ignored, and only real assignments count.
They check what is shipped, never a developer's own ``local_test_settings.py``, so
an existing local configuration cannot fail the build.

**They used to read each ``DATABASES`` dict whole, and that made three of the five
templates invisible.** ``ast.literal_eval`` raises ``ValueError`` on any
non-literal value, the caller skipped the file, and nothing reported the skip - so
once the engine templates took their host and credentials from ``os.environ.get``,
the guard was quietly checking two templates out of five. Measured 2026-11-01.
Values are now read key by key, and ``test_no_template_is_silently_unreadable``
fails if the two keys these tests depend on cannot be read.
"""

import ast
import pathlib

from django.test import SimpleTestCase

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
TEMPLATE_DIR = REPO_ROOT / 'deploy'


def _test_settings_templates():
    return sorted(TEMPLATE_DIR.glob('**/local_test_settings*.py'))


# django.db.backends.base.creation.TEST_DATABASE_PREFIX, which is what
# _get_test_db_name() prepends to NAME when TEST['NAME'] is unset.
TEST_DATABASE_PREFIX = 'test_'


def _default_database_node(path):
    """The `ast` node for `DATABASES['default']`'s dict, or None."""
    tree = ast.parse(path.read_text(encoding='utf-8'))
    found = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == 'DATABASES' for t in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        for key, value in zip(node.value.keys, node.value.values):
            if isinstance(key, ast.Constant) and key.value == 'default' and isinstance(value, ast.Dict):
                found = value
    return found


def _default_database(path):
    """`DATABASES['default']`'s literal values, and the keys that are not literals.

    Read key by key rather than as one dict, so that a template taking its host or
    password from `os.environ.get` still has its NAME and TEST read. See the module
    docstring for what reading the dict whole used to cost.
    """
    node = _default_database_node(path)
    if node is None:
        return None, []
    fields, unreadable = {}, []
    for key, value in zip(node.keys, node.values):
        if not isinstance(key, ast.Constant):
            unreadable.append('<computed key>')
            continue
        try:
            fields[key.value] = ast.literal_eval(value)
        except ValueError:
            unreadable.append(key.value)
    return fields, unreadable


def _effective_test_database(fields):
    """The database Django will create, per `BaseDatabaseCreation._get_test_db_name`."""
    test = fields.get('TEST') or {}
    return test.get('NAME') or (TEST_DATABASE_PREFIX + (fields.get('NAME') or ''))


class TestShippedTestSettingsTemplates(SimpleTestCase):

    def test_templates_were_found_at_all(self):
        """Guard the guard: a move must not leave this file vacuous."""
        assert _test_settings_templates(), (
            'no deploy/**/local_test_settings*.py found under %s' % TEMPLATE_DIR
        )

    def test_sqlite_templates_state_their_test_database(self):
        offenders = []
        for path in _test_settings_templates():
            default, _ = _default_database(path)
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
            default, _ = _default_database(path)
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

    def test_every_test_database_is_named_as_a_test_database(self):
        """Cody's rule, 2026-11-02: anything testing creates carries `test` in its name.

        Wider than the test above in both directions. It covers every engine rather
        than SQLite alone, and it checks the name Django *derives* - `test_` + `NAME`
        when `TEST['NAME']` is unset, which is how the postgres, mysql and mssql
        templates are written - so a template cannot satisfy the rule by leaving the
        decision to Django.
        """
        offenders = []
        for path in _test_settings_templates():
            default, _ = _default_database(path)
            if not default:
                continue
            name = _effective_test_database(default)
            if name == ':memory:' or 'memory' in name:
                continue
            if 'test' not in pathlib.PurePath(name).name.lower():
                offenders.append((path.relative_to(REPO_ROOT).as_posix(), name))
        assert not offenders, (
            "every database a test run creates must carry 'test' in its name, so that "
            "no run can be pointed at real data; these templates would create "
            "something else: %r" % offenders
        )

    def test_no_template_is_silently_unreadable(self):
        """Guard the guard: a skip these tests cannot see is the failure mode here.

        The checks above read `NAME` and `TEST` statically. A template that computes
        either - from the environment, or from anything else - would be skipped by
        every one of them while still appearing to be checked. Other keys may be
        computed freely: the engine templates take their host, port and credentials
        from `os.environ.get` by design.
        """
        unreadable = []
        for path in _test_settings_templates():
            default, computed = _default_database(path)
            rel = path.relative_to(REPO_ROOT).as_posix()
            if default is None:
                unreadable.append((rel, 'no DATABASES[\'default\'] dict found'))
                continue
            for key in ('NAME', 'TEST'):
                if key in computed:
                    unreadable.append((rel, '%s is computed, not a literal' % key))
        assert not unreadable, (
            'these templates cannot be checked by the tests in this file, which would '
            'pass without examining them: %r' % unreadable
        )
