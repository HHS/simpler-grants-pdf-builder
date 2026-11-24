"""One-time reset of readability checker usage records (#1427).

Deploys run migrations automatically, so this clears the usage page in each
environment on its next deploy without operator access to the environment.
Django records the migration as applied, so later deploys never clear the table
again. Saved Word comparisons are not touched. Reversing restores nothing.
"""

from django.db import migrations


def clear_attempts(apps, schema_editor):
    Attempt = apps.get_model("nofos", "PdfReadabilityAttempt")
    # Delete from the database being migrated, not whatever "default" is.
    Attempt.objects.using(schema_editor.connection.alias).all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("nofos", "0167_add_oash_group_and_theme"),
    ]

    operations = [
        migrations.RunPython(clear_attempts, migrations.RunPython.noop),
    ]
