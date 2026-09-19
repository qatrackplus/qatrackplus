# Local settings for customization - copy this file to qatrack/local_settings.py and customize as needed
# For developers, the purpose of this file is to allow for local settings specific to your development environment
# without having to modify settings.py which will be updated from time to time and would overwrite your changes.

# For production use, this file is intended to allow for local overrides of settings.py without having to modify it.
# This way you can update QATrack+ without losing your local changes, and keep your internal settings (e.g. database
# passwords) out of version control.

## Manditory settings:
### You must set at least the DATABASES setting here. 

DEBUG = False # Set to True to enable debug mode (not safe for regular use!)
TEMPLATE_DBG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db/default.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}
DATABASES['readonly'] = DATABASES['default']

# You can override anything in settings.py by defining it here
# I would recommend copying the portion of settings.py to this file and then modifying it
# as needed. This way it's easy to keep track of what has been changed, and they
# wont be lost when settings.py is updated in the future.
# Account and Email settings are a good place to start.

# Example:
#TIME_ZONE = 'America/Toronto'
#LANGUAGES = [('en', 'English'), ('fr', 'Français'), ('es', 'Español')]
#LANGUAGE_CODE = 'fr'

#AUTOSAVE_DAYS_TO_KEEP = 7
#MAX_TESTS_PER_TESTLIST = 100

#TODO - add default adfs settings here if needed

#CUSTOM_ROOT_PATH = "/path/to/your/qatrack/storage/directory"
#MEDIA_ROOT = os.path.join(CUSTOM_ROOT_PATH, "media")

#UPLOAD_PATH = "uploads"
#TMP_UPLOAD_PATH = os.path.join(UPLOAD_PATH, "tmp")
#UPLOAD_ROOT = os.path.join(MEDIA_ROOT, "uploads")
#TMP_UPLOAD_ROOT = os.path.join(UPLOAD_ROOT, "tmp")
#STATIC_ROOT = os.path.join(CUSTOM_ROOT_PATH, "static")


# ------------------------------------------------------------------------------
# Dates and times
#
# By default QATrack+ shows dates as YYYY-MM-DD HH:MM, in every language, and
# the date pickers write that same format into the field. ISO order is the
# default because it sorts correctly and cannot be misread - 03/04 is the 3rd
# of April to half the world and the 4th of March to the other half.
#
# To change it, set the format you want here. Everything follows from it: what
# is displayed, what the date pickers produce, and the help text under each
# date field. Use Python strptime syntax (%Y year, %m month, %d day, %H hour,
# %M minute).
#
# QATRACK_DATETIME_FORMAT = "%d %b %Y %H:%M"   # 31 May 2012 14:30
# QATRACK_DATE_FORMAT = "%d %b %Y"             # 31 May 2012
# QATRACK_TIME_FORMAT = "%H:%M"
#
# Typing a date is separate from displaying one. QATrack+ always accepts the
# format above, plus the ones listed below. Adding to this list lets people
# enter dates whichever way they are used to without changing what anybody
# sees - it only affects what is understood on the way in.
#
# QATRACK_EXTRA_DATETIME_INPUT_FORMATS = [
#     "%d %b %Y %H:%M",     # 31 May 2012 14:30
#     "%d/%m/%Y %H:%M",     # 31/05/2012 14:30
# ]
# QATRACK_EXTRA_DATE_INPUT_FORMATS = [
#     "%d %b %Y",
#     "%d/%m/%Y",
# ]
#
# Note the JSON API is deliberately unaffected by all of this - its date
# format is fixed so that changing your display preference cannot break an
# integration that parses it.
