# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):
    def forwards(self, orm):
        # Removing unique constraint on 'Modality', fields ['type', 'energy']
        db.delete_unique("units_modality", ["type", "energy"])

        # Deleting field 'Modality.energy'
        db.delete_column("units_modality", "energy")

        # Deleting field 'Modality.type'
        db.delete_column("units_modality", "type")

        # Adding unique constraint on 'Modality', fields ['name']
        db.create_unique("units_modality", ["name"])

    def backwards(self, orm):
        # Removing unique constraint on 'Modality', fields ['name']
        db.delete_unique("units_modality", ["name"])

        # Adding field 'Modality.energy'
        db.add_column(
            "units_modality", "energy", self.gf("django.db.models.fields.FloatField")(default=0), keep_default=False
        )

        # Adding field 'Modality.type'
        db.add_column(
            "units_modality",
            "type",
            self.gf("django.db.models.fields.CharField")(default="photon", max_length=20),
            keep_default=False,
        )

        # Adding unique constraint on 'Modality', fields ['type', 'energy']
        db.create_unique("units_modality", ["type", "energy"])

    models = {
        "units.modality": {
            "Meta": {"object_name": "Modality"},
            "id": ("django.db.models.fields.AutoField", [], {"primary_key": "True"}),
            "name": ("django.db.models.fields.CharField", [], {"unique": "True", "max_length": "255"}),
        },
        "units.unit": {
            "Meta": {"ordering": "['number']", "object_name": "Unit"},
            "id": ("django.db.models.fields.AutoField", [], {"primary_key": "True"}),
            "install_date": ("django.db.models.fields.DateField", [], {"null": "True", "blank": "True"}),
            "location": (
                "django.db.models.fields.CharField",
                [],
                {"max_length": "256", "null": "True", "blank": "True"},
            ),
            "modalities": (
                "django.db.models.fields.related.ManyToManyField",
                [],
                {"to": "orm['units.Modality']", "symmetrical": "False"},
            ),
            "name": ("django.db.models.fields.CharField", [], {"max_length": "256"}),
            "number": ("django.db.models.fields.PositiveIntegerField", [], {"unique": "True"}),
            "serial_number": (
                "django.db.models.fields.CharField",
                [],
                {"max_length": "256", "null": "True", "blank": "True"},
            ),
            "type": ("django.db.models.fields.related.ForeignKey", [], {"to": "orm['units.UnitType']"}),
        },
        "units.unittype": {
            "Meta": {"unique_together": "[('name', 'model')]", "object_name": "UnitType"},
            "id": ("django.db.models.fields.AutoField", [], {"primary_key": "True"}),
            "model": ("django.db.models.fields.CharField", [], {"max_length": "50", "null": "True", "blank": "True"}),
            "name": ("django.db.models.fields.CharField", [], {"max_length": "50"}),
            "vendor": ("django.db.models.fields.CharField", [], {"max_length": "50"}),
        },
    }

    complete_apps = ["units"]
