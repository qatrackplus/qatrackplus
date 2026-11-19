"""Add the table that stops a scheduled email being sent twice (issue #919).

django-q can hand the same scheduled task out a second time while the first
copy is still waiting in the queue or running. Each scheduled report and
notice now claims a row here, keyed by its schedule and due time, before it
sends, and only the copy that wins the claim sends the email.

This creates one new, empty table and changes nothing else. Rows older than
30 days are removed as new ones are created.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("qatrack_core", "0002_cache_table"),
    ]

    operations = [
        migrations.CreateModel(
            name="ScheduledDelivery",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("kind", models.CharField(max_length=100)),
                ("object_id", models.PositiveIntegerField()),
                ("occurrence", models.CharField(max_length=255)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("claimed_at", models.DateTimeField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name="scheduleddelivery",
            constraint=models.UniqueConstraint(
                fields=("kind", "object_id", "occurrence"),
                name="qatrack_core_scheduleddelivery_unique_occurrence",
            ),
        ),
    ]
