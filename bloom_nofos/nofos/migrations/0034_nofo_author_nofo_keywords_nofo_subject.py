# Generated by Django 4.2.9 on 2024-02-06 00:03

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nofos", "0033_alter_nofo_theme"),
    ]

    operations = [
        migrations.AddField(
            model_name="nofo",
            name="author",
            field=models.TextField(
                blank=True,
                help_text="The author of this NOFO.",
                verbose_name="NOFO author",
            ),
        ),
        migrations.AddField(
            model_name="nofo",
            name="keywords",
            field=models.TextField(
                blank=True,
                help_text="Keywords for this NOFO.",
                verbose_name="NOFO keywords",
            ),
        ),
        migrations.AddField(
            model_name="nofo",
            name="subject",
            field=models.TextField(
                blank=True,
                help_text="The subject of this NOFO.",
                verbose_name="NOFO subject",
            ),
        ),
    ]
