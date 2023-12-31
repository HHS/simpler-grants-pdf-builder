# Generated by Django 4.2.7 on 2023-12-19 06:17

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nofos", "0009_alter_nofo_number"),
    ]

    operations = [
        migrations.AlterField(
            model_name="nofo",
            name="coach",
            field=models.CharField(
                blank=True,
                choices=[
                    ("emily", "Emily"),
                    ("hannah", "Hannah"),
                    ("july", "July"),
                    ("laura", "Laura"),
                    ("moira", "Moira"),
                    ("morgan", "Morgan"),
                ],
                help_text="The coach has the primary responsibility for editing this NOFO.",
                max_length=16,
            ),
        ),
    ]
