# Generated by Django 4.2.9 on 2024-01-29 22:51

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nofos", "0031_rename_is_page_break_subsection_has_page_break"),
    ]

    operations = [
        migrations.AddField(
            model_name="section",
            name="has_section_page",
            field=models.BooleanField(
                default=True,
                help_text="If true, this section will have its own page and icon in the ToC.",
                verbose_name="Has section page?",
            ),
        ),
    ]
