# Generated by Django 5.0.8 on 2025-01-14 17:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("nofos", "0087_alter_nofo_designer"),
    ]

    operations = [
        migrations.AddField(
            model_name="nofo",
            name="sole_source_justification",
            field=models.BooleanField(
                default=False,
                help_text="An SSJ NOFO is intended for only 1 applicant.",
                verbose_name="Sole source justification",
            ),
        ),
    ]
