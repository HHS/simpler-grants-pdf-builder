# guides/migrations/0006_populate_uuids.py
import uuid

from django.db import migrations


def regenerate_uuids(apps, schema_editor):
    for model_name in ["ContentGuide", "ContentGuideSection", "ContentGuideSubsection"]:
        Model = apps.get_model("guides", model_name)
        for obj in Model.objects.all():
            obj.uuid = uuid.uuid4()
            obj.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("guides", "0005_contentguide_uuid_contentguidesection_uuid_and_more"),
    ]

    operations = [
        migrations.RunPython(regenerate_uuids, reverse_code=migrations.RunPython.noop),
    ]
