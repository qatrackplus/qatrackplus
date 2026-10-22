"""CI only: make a database job's tests run on that job's database, and prove it.

Since "Make a test run safe with no local_test_settings.py", qatrack/test_settings.py
pins the test database to in-memory SQLite unless qatrack/local_test_settings.py says
otherwise. That is the right default for a developer, but a CI job that only copies a
PostgreSQL, MySQL or SQL Server local_settings.py then quietly tests SQLite.

This writes local_test_settings.py from the job's own local_settings.py, resolves the
settings the way a pytest run does, and exits non-zero if they still name SQLite - so the
job fails instead of passing on the wrong database.

    uv run python scripts/ci_test_database.py
"""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

(ROOT / 'qatrack' / 'local_test_settings.py').write_text(
    "# Written by scripts/ci_test_database.py for a CI database job: run the tests on the\n"
    "# database local_settings.py names, not test_settings.py's in-memory SQLite default.\n"
    "from .local_settings import DATABASES as _job_databases  # noqa: E402\n"
    "\n"
    "DATABASES = {'default': _job_databases['default']}\n"
    "DATABASES['readonly'] = DATABASES['default']\n",
    encoding='utf-8',
)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qatrack.settings')
sys.argv = ['pytest']  # settings.py loads test_settings.py only for a pytest run

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

engine = settings.DATABASES['default']['ENGINE']
print('the tests will use:', engine)
sys.exit(1 if 'sqlite' in engine else 0)
