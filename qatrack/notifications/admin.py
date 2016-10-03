from django.contrib import admin
from . import models
admin.site.register([models.NotificationSubscription], admin.ModelAdmin)
