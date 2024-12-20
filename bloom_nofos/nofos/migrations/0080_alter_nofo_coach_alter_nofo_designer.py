# Generated by Django 5.0.8 on 2024-12-16 17:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("nofos", "0079_cleanup_update_print_logs"),
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
                    ("idit", "Idit"),
                    ("julie", "Julie"),
                    ("july", "July"),
                    ("mick", "Mick"),
                    ("moira", "Moira"),
                    ("morgan", "Morgan"),
                    ("sara", "Sara"),
                    ("shane", "Shane"),
                ],
                help_text="The coach has the primary responsibility for editing this NOFO.",
                max_length=16,
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
                    ("bloom-kevin", "Kevin"),
                    ("bloom-yasmine", "Yasmine"),
                    ("hrsa-betty", "Betty"),
                    ("hrsa-doretha", "Doretha"),
                    ("hrsa-gwen", "Gwen"),
                    ("hrsa-ericka", "Ericka"),
                    ("hrsa-jene", "Jene"),
                    ("hrsa-randy", "Randy"),
                    ("hrsa-stephanie", "Stephanie\xa0V"),
                    ("hrsa-kieumy", "KieuMy"),
                ],
                help_text="The designer is responsible for the layout of this NOFO.",
                max_length=16,
            ),
        ),
    ]
