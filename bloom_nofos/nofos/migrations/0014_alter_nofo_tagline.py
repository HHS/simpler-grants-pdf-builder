# Generated by Django 4.2.7 on 2023-12-22 03:55

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nofos", "0013_nofo_tagline"),
    ]

    operations = [
        migrations.AlterField(
            model_name="nofo",
            name="tagline",
            field=models.TextField(
                blank=True,
                help_text="A short sentence that outlines the high-level goal of this NOFO.",
                verbose_name="NOFO tagline",
            ),
        ),
    ]
