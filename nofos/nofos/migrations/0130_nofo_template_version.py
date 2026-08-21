from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nofos", "0129_alter_nofo_theme"),
    ]

    operations = [
        migrations.AddField(
            model_name="nofo",
            name="template_version",
            field=models.CharField(
                choices=[
                    ("unknown", "Unknown"),
                    ("pre_fy27", "Pre-FY27"),
                    ("fy27", "FY27"),
                ],
                default="unknown",
                help_text=(
                    "The HHS NOFO template generation used by this document. Builder "
                    "detects this during import, and you can correct it when needed."
                ),
                max_length=16,
                verbose_name="Template version",
            ),
        ),
        migrations.AddField(
            model_name="nofo",
            name="template_version_detection",
            field=models.JSONField(
                blank=True,
                default=dict,
                editable=False,
                help_text=(
                    "Diagnostic evidence from automatic template-version detection, "
                    "including any later manual override."
                ),
                verbose_name="Template version detection",
            ),
        ),
    ]
