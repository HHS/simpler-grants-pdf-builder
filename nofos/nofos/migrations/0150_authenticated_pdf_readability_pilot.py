from django.db import migrations, models


def prepare_pilot(apps, schema_editor):
    # Before this migration, the only application recording entry point is
    # bloom_nofos.views.pdf_readability. It always records public-route traffic,
    # even when the browser has a signed-in session. New unattributed rows keep
    # the unknown default rather than guessing their provenance.
    Attempt = apps.get_model("nofos", "PdfReadabilityAttempt")
    Attempt.objects.using(schema_editor.connection.alias).filter(
        source="unknown"
    ).update(source="public")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")
    db = schema_editor.connection.alias
    content_type, _ = ContentType.objects.using(db).get_or_create(
        app_label="nofos", model="nofo"
    )
    permission, _ = Permission.objects.using(db).get_or_create(
        content_type=content_type,
        codename="use_pdf_readability_pilot",
        defaults={"name": "Can use the authenticated PDF readability pilot"},
    )
    group, _ = Group.objects.using(db).get_or_create(
        name="PDF readability pilot participants"
    )
    group.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [
        ("nofos", "0149_readability_checkpoint_download_trigger"),
        ("auth", "0001_initial"),
        ("contenttypes", "0001_initial"),
    ]
    operations = [
        migrations.AddField(
            model_name="pdfreadabilityattempt",
            name="source",
            field=models.CharField(
                max_length=16,
                db_index=True,
                default="unknown",
                choices=[
                    ("public", "Public"),
                    ("authenticated", "Authenticated"),
                    ("unknown", "Unknown"),
                ],
            ),
        ),
        migrations.AlterModelOptions(
            name="nofo",
            options={
                "verbose_name": "NOFO",
                "verbose_name_plural": "NOFOs",
                "permissions": [
                    (
                        "view_builder_metrics",
                        "Can view NOFO Builder usage & quality metrics",
                    ),
                    (
                        "use_pdf_readability_pilot",
                        "Can use the authenticated PDF readability pilot",
                    ),
                ],
            },
        ),
        migrations.RunPython(prepare_pilot, migrations.RunPython.noop),
    ]
