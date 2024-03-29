# Generated by Django 4.2.9 on 2024-01-22 17:15

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nofos", "0024_nofo_cover"),
    ]

    operations = [
        migrations.AlterField(
            model_name="nofo",
            name="short_name",
            field=models.CharField(
                blank=True,
                help_text="A name to make it easier to see this NOFO in a list. It won’t be public.",
                max_length=511,
            ),
        ),
        migrations.AlterField(
            model_name="section",
            name="html_id",
            field=models.CharField(blank=True, max_length=511),
        ),
        migrations.AlterField(
            model_name="subsection",
            name="html_id",
            field=models.CharField(blank=True, max_length=511),
        ),
    ]
