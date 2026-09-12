
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from qatrack.qatrack_core.sample_data import SmallCenterGenerator


class Command(BaseCommand):
    help = "Generates comprehensive, realistic sample test data for QATrack+ (QA, Service Log, Faults, Parts, Reports)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Number of days of rolling QA and maintenance history to generate (default: 90).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing QA, unit, service log, fault, parts, and report data before generating.",
        )
        parser.add_argument(
            "--no-input",
            action="store_true",
            help="Do not prompt for confirmation when clearing data.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        clear = options["clear"]
        no_input = options["no_input"]

        if days < 0:
            raise CommandError(f"--days must be zero or greater (got {days}).")

        generator = SmallCenterGenerator(days=days, stdout=self.stdout, stderr=self.stderr)

        if clear and not no_input:
            confirm = input("This will DELETE existing units, QA records, service events, faults, parts, and reports. Continue? [y/N]: ")
            if confirm.lower() != "y":
                self.stdout.write(self.style.WARNING("Aborted by user."))
                return

        # Clearing and generating share a transaction: a failure part way
        # through generation must not leave the database wiped.
        with transaction.atomic():
            if clear:
                generator.clear_database()

            self.stdout.write(self.style.MIGRATE_HEADING(f"Generating sample data with {days} days of history..."))
            generator.generate()

        self.stdout.write(self.style.SUCCESS("Successfully generated sample data!"))
