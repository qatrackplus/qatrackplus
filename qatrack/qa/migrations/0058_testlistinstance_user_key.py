# Generated by Django 2.2.18 on 2021-03-16 15:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('qa', '0057_auto_20200825_2233'),
    ]

    operations = [
        migrations.AddField(
            model_name='testlistinstance',
            name='user_key',
            field=models.CharField(blank=True, default=None, help_text='Optional field that can be used to ensure uniqueness when posting results via the API', max_length=255, null=True, unique=True),
        ),
    ]
