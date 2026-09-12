import glob
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Loads all default fixtures from fixtures/defaults/'

    def handle(self, *args, **kwargs):
        base_dir = getattr(settings, 'BASE_DIR', os.path.abspath(os.path.join(settings.PROJECT_ROOT, '..')))
        fixtures_pattern = os.path.join(base_dir, 'fixtures', 'defaults', '*', '*.json')
        fixtures = glob.glob(fixtures_pattern)
        
        if not fixtures:
            self.stdout.write(self.style.WARNING(f'No default fixtures found at {fixtures_pattern}'))
            return
            
        self.stdout.write(self.style.SUCCESS(f'Found {len(fixtures)} default fixtures. Loading...'))
        
        # Load all fixtures at once
        call_command('loaddata', *fixtures)
        
        self.stdout.write(self.style.SUCCESS('Successfully loaded all default fixtures.'))
