# Generated by Django 4.2.9 on 2024-02-15 16:57

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nofos", "0042_alter_nofo_theme"),
    ]

    operations = [
        migrations.AlterField(
            model_name="nofo",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("active", "Active"),
                    ("review", "In review"),
                    ("published", "Published"),
                ],
                default="draft",
                help_text="The status of this NOFO in the NOFO builder.",
                max_length=32,
            ),
        ),
    ]