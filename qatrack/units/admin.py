from django.contrib import admin
from models import Unit, Modality, UnitType

admin.site.register([Modality, Unit, UnitType])
