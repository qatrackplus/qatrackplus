from django.core.management.commands.makemessages import Command as BaseCommand


class Command(BaseCommand):
    help = "Django's makemessages, with xgettext also extracting the _l() alias QATrack+ uses for lazy translation"

    # Get xgettext to recognize _l() pattern used throughout the code base.
    xgettext_options = BaseCommand.xgettext_options + ["--keyword=_l"]
