# Every language deliberately gets the same date formats: a date should not
# change meaning because someone switched the interface language. The formats
# themselves are configurable - see the QATRACK_*_FORMAT settings - and are
# derived in one place so that the parser, the display, the date pickers and
# the help text cannot disagree.
from qatrack.formats.base import *  # noqa: F401,F403
