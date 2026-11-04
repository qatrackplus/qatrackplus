from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Clear every entry in Django's default cache"

    def handle(self, *args, **kwargs):
        cache.clear()
        self.stdout.write('Cleared cache\n')
