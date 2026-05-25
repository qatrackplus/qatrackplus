from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):
    def forwards(self, orm):
        # Adding field 'Modality.name'
        db.add_column(
            'units_modality',
            'name',
            self.gf('django.db.models.fields.CharField')(default='temp modality name', max_length=255),
            keep_default=False,
        )

    def backwards(self, orm):
        # Deleting field 'Modality.name'
        db.delete_column('units_modality', 'name')

    models = {
        'units.modality': {
            'Meta': {'unique_together': "[('type', 'energy')]", 'object_name': 'Modality'},
            'energy': ('django.db.models.fields.FloatField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
        },
        'units.unit': {
            'Meta': {'ordering': "['number']", 'object_name': 'Unit'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'install_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'location': (
                'django.db.models.fields.CharField',
                [],
                {'max_length': '256', 'null': 'True', 'blank': 'True'},
            ),
            'modalities': (
                'django.db.models.fields.related.ManyToManyField',
                [],
                {'to': "orm['units.Modality']", 'symmetrical': 'False'},
            ),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'number': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True'}),
            'serial_number': (
                'django.db.models.fields.CharField',
                [],
                {'max_length': '256', 'null': 'True', 'blank': 'True'},
            ),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['units.UnitType']"}),
        },
        'units.unittype': {
            'Meta': {'unique_together': "[('name', 'model')]", 'object_name': 'UnitType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'vendor': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
        },
    }

    complete_apps = ['units']
