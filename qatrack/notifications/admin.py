from django.contrib import admin
import models
admin.site.register([models.NotificationSubscription], admin.ModelAdmin)
