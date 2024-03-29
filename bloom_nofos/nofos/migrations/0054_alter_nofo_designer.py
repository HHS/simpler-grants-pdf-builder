# Generated by Django 4.2.10 on 2024-03-22 19:59

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nofos", "0053_remove_nofo_icon_path"),
    ]

    operations = [
        migrations.AlterField(
            model_name="nofo",
            name="designer",
            field=models.CharField(
                blank=True,
                choices=[
                    ("adam", "Adam"),
                    ("kevin", "Kevin"),
                    ("emily", "Emily"),
                    ("yasmine", "Yasmine"),
                ],
                help_text="The designer is responsible for the layout of this NOFO.",
                max_length=16,
            ),
        ),
    ]
