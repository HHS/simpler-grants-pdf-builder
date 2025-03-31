# Generated by Django 5.0.13 on 2025-03-31 19:16

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("nofos", "0094_alter_nofo_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="nofo",
            name="coach",
            field=models.CharField(
                blank=True,
                choices=[
                    ("aarti", "Aarti"),
                    ("alex", "Alex"),
                    ("emily", "Emily"),
                    ("hannah", "Hannah"),
                    ("julie", "Julie"),
                    ("july", "July"),
                    ("moira", "Moira"),
                ],
                help_text="The coach has the primary responsibility for editing this NOFO.",
                max_length=16,
                validators=[django.core.validators.MaxLengthValidator(16)],
            ),
        ),
        migrations.AlterField(
            model_name="nofo",
            name="designer",
            field=models.CharField(
                blank=True,
                choices=[
                    ("bloom-abbey", "Abbey"),
                    ("bloom-adam", "Adam"),
                    ("bloom-emily-b", "Emily\xa0B"),
                    ("bloom-emily-i", "Emily\xa0I"),
                    ("bloom-jackie", "Jackie"),
                    ("bloom-jana", "Jana"),
                    ("bloom-kevin", "Kevin"),
                    ("bloom-yasmine", "Yasmine"),
                    ("hrsa-betty", "Betty"),
                    ("hrsa-dvora", "Dvora"),
                    ("hrsa-ericka", "Ericka"),
                    ("hrsa-jene", "Jene"),
                    ("hrsa-jennifer", "Jennifer"),
                    ("hrsa-kieumy", "KieuMy"),
                    ("hrsa-lynda", "Lynda"),
                    ("hrsa-marco", "Marco"),
                    ("hrsa-randy", "Randy"),
                    ("hrsa-stephanie", "Stephanie\xa0V"),
                ],
                help_text="The designer is responsible for the layout of this NOFO.",
                max_length=16,
                validators=[django.core.validators.MaxLengthValidator(16)],
            ),
        ),
    ]
