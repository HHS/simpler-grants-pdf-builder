import uuid

from django.db import migrations


def regenerate_uuids(apps, schema_editor):
    for model_name in ["Nofo", "Section", "Subsection"]:
        Model = apps.get_model("nofos", model_name)
        for obj in Model.objects.all():
            obj.uuid = uuid.uuid4()
            obj.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("nofos", "0099_nofo_uuid_section_uuid_subsection_uuid"),
    ]

    operations = [
        migrations.RunPython(regenerate_uuids, reverse_code=migrations.RunPython.noop),
    ]
