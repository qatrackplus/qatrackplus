import glob
import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Loads all default fixtures from fixtures/defaults/'

    def handle(self, *args, **kwargs):
        # Construct the path to the fixtures directory
        fixtures_pattern = os.path.join(settings.BASE_DIR, 'fixtures', 'defaults', '*', '*.json')
        fixtures = glob.glob(fixtures_pattern)
        
        if not fixtures:
            self.stdout.write(self.style.WARNING(f'No default fixtures found at {fixtures_pattern}'))
            return
            
        self.stdout.write(self.style.SUCCESS(f'Found {len(fixtures)} default fixtures. Loading...'))
        
        # Load all fixtures at once
        call_command('loaddata', *fixtures)
        
        self.stdout.write(self.style.SUCCESS('Successfully loaded all default fixtures.'))
