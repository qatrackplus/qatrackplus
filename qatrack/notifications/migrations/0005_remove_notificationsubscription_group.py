# Generated by Django 2.1.7 on 2019-04-11 02:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0004_copy_group_to_groups'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='notificationsubscription',
            name='group',
        ),
    ]
