# Generated by Django 4.2.9 on 2024-02-13 17:31

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nofos", "0041_alter_nofo_theme"),
    ]

    operations = [
        migrations.AlterField(
            model_name="nofo",
            name="theme",
            field=models.CharField(
                choices=[
                    ("landscape-cdc-blue", "CDC Landscape (Default)"),
                    ("landscape-cdc-white", "CDC Landscape (Light)"),
                    ("portrait-cdc-dop", "CDC Portrait (DOP)"),
                    ("portrait-cdc-blue", "CDC Portrait (Default)"),
                    ("portrait-cdc-white", "CDC Portrait (Light)"),
                    ("portrait-hrsa-blue", "HRSA (Default)"),
                    ("portrait-hrsa-white", "HRSA (Light)"),
                    ("portrait-acf-blue", "ACF (Default)"),
                    ("portrait-acf-white", "ACF (Light)"),
                    ("portrait-cms-white", "CMS (Light)"),
                    ("portrait-ihs-white", "IHS (Light)"),
                ],
                default="portrait-hrsa-blue",
                help_text="The theme sets the orientation and colour pallete for this NOFO.",
                max_length=32,
            ),
        ),
    ]
