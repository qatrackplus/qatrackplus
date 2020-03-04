from django.contrib import admin

from qatrack.contacts.models import Contact
from qatrack.qatrack_core.admin import BaseQATrackAdmin

admin.site.register([Contact], BaseQATrackAdmin)
