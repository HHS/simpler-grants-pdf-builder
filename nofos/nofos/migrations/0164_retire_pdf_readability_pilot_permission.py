from django.db import migrations

PERMISSION = "use_pdf_readability_pilot"
GROUP = "PDF readability pilot participants"


def retire_pilot_access(apps, schema_editor):
    # Access to the Readability Checker is now controlled only by the public
    # and signed-in Constance switches (#1367). Deleting the permission also
    # removes it from every user and group that held it.
    db = schema_editor.connection.alias
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")
    Permission.objects.using(db).filter(
        content_type__app_label="nofos", codename=PERMISSION
    ).delete()
    Group.objects.using(db).filter(name=GROUP).delete()


def restore_pilot_access(apps, schema_editor):
    # Recreate the empty permission and group. Former memberships are not
    # restored; reassign participants manually after a rollback.
    db = schema_editor.connection.alias
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")
    content_type, _ = ContentType.objects.using(db).get_or_create(
        app_label="nofos", model="nofo"
    )
    permission, _ = Permission.objects.using(db).get_or_create(
        content_type=content_type,
        codename=PERMISSION,
        defaults={"name": "Can use the authenticated PDF readability pilot"},
    )
    group, _ = Group.objects.using(db).get_or_create(name=GROUP)
    group.permissions.add(permission)


class Migration(migrations.Migration):

    dependencies = [
        ("nofos", "0163_alter_externalsourcehandoff_group_alter_nofo_group_and_more"),
        ("auth", "0001_initial"),
        ("contenttypes", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(retire_pilot_access, restore_pilot_access),
        migrations.AlterModelOptions(
            name="nofo",
            options={
                "permissions": [
                    (
                        "view_builder_metrics",
                        "Can view NOFO Builder usage & quality metrics",
                    )
                ],
                "verbose_name": "NOFO",
                "verbose_name_plural": "NOFOs",
            },
        ),
    ]
