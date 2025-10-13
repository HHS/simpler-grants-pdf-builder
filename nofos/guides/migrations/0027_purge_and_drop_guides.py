from django.db import migrations


def purge_content_guides(apps, schema_editor):
    ContentGuide = apps.get_model("guides", "ContentGuide")
    # Deleting ContentGuides will cascade to sections and subsections automatically
    ContentGuide.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("guides", "0026_contentguide_updated_by"),
    ]

    operations = [
        # 1. Purge all data
        migrations.RunPython(
            purge_content_guides, reverse_code=migrations.RunPython.noop
        ),
        # 2. Drop the models (which drops the tables)
        migrations.DeleteModel(name="ContentGuideSubsection"),
        migrations.DeleteModel(name="ContentGuideSection"),
        migrations.DeleteModel(name="ContentGuide"),
    ]
