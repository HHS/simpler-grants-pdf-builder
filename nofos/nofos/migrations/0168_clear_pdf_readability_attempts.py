"""One-time reset of readability checker usage records (#1427).

Deploys run migrations automatically, so this clears the usage page in each
environment on its next deploy without operator access to the environment.
Django records the migration as applied, so later deploys don't clear the table
again while 0168 remains applied. Reversing restores nothing, and reversing to
0167 then reapplying 0168 deletes every attempt again, including ones recorded
since the first reset. Saved Word comparisons are not touched.
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
