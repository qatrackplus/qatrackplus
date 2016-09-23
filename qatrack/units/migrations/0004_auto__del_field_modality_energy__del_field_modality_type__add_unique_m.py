# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Modality', fields ['type', 'energy']
        db.delete_unique(u'units_modality', ['type', 'energy'])

        # Deleting field 'Modality.energy'
        db.delete_column(u'units_modality', 'energy')

        # Deleting field 'Modality.type'
        db.delete_column(u'units_modality', 'type')

        # Adding unique constraint on 'Modality', fields ['name']
        db.create_unique(u'units_modality', ['name'])


    def backwards(self, orm):
        # Removing unique constraint on 'Modality', fields ['name']
        db.delete_unique(u'units_modality', ['name'])

        # Adding field 'Modality.energy'
        db.add_column(u'units_modality', 'energy',
                      self.gf('django.db.models.fields.FloatField')(default=0),
                      keep_default=False)

        # Adding field 'Modality.type'
        db.add_column(u'units_modality', 'type',
                      self.gf('django.db.models.fields.CharField')(default='photon', max_length=20),
                      keep_default=False)

        # Adding unique constraint on 'Modality', fields ['type', 'energy']
        db.create_unique(u'units_modality', ['type', 'energy'])


    models = {
        u'units.modality': {
            'Meta': {'object_name': 'Modality'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        u'units.unit': {
            'Meta': {'ordering': "['number']", 'object_name': 'Unit'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'install_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'modalities': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['units.Modality']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'number': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True'}),
            'serial_number': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['units.UnitType']"})
        },
        u'units.unittype': {
            'Meta': {'unique_together': "[('name', 'model')]", 'object_name': 'UnitType'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vendor': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['units']