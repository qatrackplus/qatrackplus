# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'UnitType'
        db.create_table('units_unittype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('vendor', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('model', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
        ))
        db.send_create_signal('units', ['UnitType'])

        # Adding unique constraint on 'UnitType', fields ['name', 'model']
        db.create_unique('units_unittype', ['name', 'model'])

        # Adding model 'Modality'
        db.create_table('units_modality', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('energy', self.gf('django.db.models.fields.FloatField')()),
        ))
        db.send_create_signal('units', ['Modality'])

        # Adding unique constraint on 'Modality', fields ['type', 'energy']
        db.create_unique('units_modality', ['type', 'energy'])

        # Adding model 'Unit'
        db.create_table('units_unit', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('number', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('serial_number', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('location', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('install_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['units.UnitType'])),
        ))
        db.send_create_signal('units', ['Unit'])

        # Adding M2M table for field modalities on 'Unit'
        db.create_table('units_unit_modalities', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('unit', models.ForeignKey(orm['units.unit'], on_delete=models.CASCADE, null=False)),
            ('modality', models.ForeignKey(orm['units.modality'], on_delete=models.CASCADE, null=False))
        ))
        db.create_unique('units_unit_modalities', ['unit_id', 'modality_id'])

    def backwards(self, orm):
        # Removing unique constraint on 'Modality', fields ['type', 'energy']
        db.delete_unique('units_modality', ['type', 'energy'])

        # Removing unique constraint on 'UnitType', fields ['name', 'model']
        db.delete_unique('units_unittype', ['name', 'model'])

        # Deleting model 'UnitType'
        db.delete_table('units_unittype')

        # Deleting model 'Modality'
        db.delete_table('units_modality')

        # Deleting model 'Unit'
        db.delete_table('units_unit')

        # Removing M2M table for field modalities on 'Unit'
        db.delete_table('units_unit_modalities')

    models = {
        'units.modality': {
            'Meta': {'unique_together': "[('type', 'energy')]", 'object_name': 'Modality'},
            'energy': ('django.db.models.fields.FloatField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'units.unit': {
            'Meta': {'ordering': "['number']", 'object_name': 'Unit'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'install_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'modalities': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['units.Modality']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'number': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True'}),
            'serial_number': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['units.UnitType']"})
        },
        'units.unittype': {
            'Meta': {'unique_together': "[('name', 'model')]", 'object_name': 'UnitType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vendor': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['units']
