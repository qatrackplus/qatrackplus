from south.v2 import DataMigration


class Migration(DataMigration):
    def forwards(self, orm):
        Modality = orm['units.Modality']
        for m in Modality.objects.all():
            if m.type == 'photon':
                unit, particle = 'MV', 'Photon'
            else:
                unit, particle = 'MeV', 'Electron'
            m.name = f'{m.energy:g}{unit} {particle}'
            m.save()

    def backwards(self, orm):
        "Write your backwards methods here."

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
    symmetrical = True
