import glob
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

# Subdirectories are loaded in this order to satisfy foreign-key dependencies.
# units must come before qa (Unit is referenced by UnitTestCollection, UnitTestInfo).
# service_log has no cross-app FK dependencies on qa/units objects in the defaults set.
FIXTURE_LOAD_ORDER = ['units', 'qa', 'service_log']


class Command(BaseCommand):
    help = 'Loads all default fixtures from fixtures/defaults/'

    def handle(self, *args, **kwargs):
        # PROJECT_ROOT is the qatrack/ package directory; go one level up for repo root
        repo_root = os.path.dirname(settings.PROJECT_ROOT)
        defaults_dir = os.path.join(repo_root, 'fixtures', 'defaults')

        # Collect subdirectories in dependency order, then any remaining ones alphabetically
        subdirs_ordered = []
        for name in FIXTURE_LOAD_ORDER:
            path = os.path.join(defaults_dir, name)
            if os.path.isdir(path):
                subdirs_ordered.append(path)

        # Append any subdirectories not listed in FIXTURE_LOAD_ORDER, alphabetically
        for path in sorted(glob.glob(os.path.join(defaults_dir, '*'))):
            if os.path.isdir(path) and path not in subdirs_ordered:
                subdirs_ordered.append(path)

        fixtures = []
        for subdir in subdirs_ordered:
            fixtures.extend(sorted(glob.glob(os.path.join(subdir, '*.json'))))

        if not fixtures:
            self.stdout.write(self.style.WARNING(f'No default fixtures found in {defaults_dir}'))
            return

        self.stdout.write(self.style.SUCCESS(f'Found {len(fixtures)} default fixtures. Loading...'))

        # Load all fixtures at once; loaddata handles natural-key deferred references
        call_command('loaddata', *fixtures)

        self.stdout.write(self.style.SUCCESS('Successfully loaded all default fixtures.'))
