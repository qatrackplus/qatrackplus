import os

from django.core.management.base import BaseCommand, CommandError

from qatrack.qa.testpack import load_testpack


class Command(BaseCommand):
    """A management command to load a test pack from the command line"""

    help = 'Load a testpack from the command linecommands to enable/disable auto scheduling and set due dates'

    def add_arguments(self, parser):
        parser.add_argument("path", nargs=1, type=str)

    def handle(self, *args, **kwargs):

        if not os.path.exists(kwargs['path'][0]):
            raise CommandError("Usage: python manage.py load_testpack /path/to/testpack.tpk")

        load_testpack(kwargs['path'][0])
        self.stdout.write("Successfully imported")
