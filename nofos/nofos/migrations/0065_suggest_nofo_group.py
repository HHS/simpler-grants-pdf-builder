from django.db import migrations


def update_nofo_groups(apps, schema_editor):
    Nofo = apps.get_model("nofos", "Nofo")
    groups = [
        ("bloom", "Bloomworks (Placeholder)"),
        ("acf", "ACF: Administration for Children and Families"),
        ("acl", "ACL: Administration for Community Living"),
        ("aspr", "ASPR: Administration for Strategic Preparedness and Response"),
        ("cdc", "CDC: Centers for Disease Control and Prevention"),
        ("cms", "CMS: Centers for Medicare & Medicaid Services"),
        ("hrsa", "HRSA: Health Resources and Services Administration"),
        ("ihs", "IHS: Indian Health Service"),
    ]
    for nofo in Nofo.objects.all():
        for code, _ in groups:
            if nofo.number:
                if code in nofo.number.lower():
                    nofo.group = code
                    nofo.save()
                    break  # Break after the first match to prevent overwriting by subsequent matches


def reverse_func(apps, schema_editor):
    Nofo = apps.get_model("nofos", "Nofo")
    Nofo.objects.update(group="bloom")  # Reset to default value


class Migration(migrations.Migration):
    dependencies = [
        (
            "nofos",
            "0064_nofo_group",
        ),
    ]

    operations = [
        migrations.RunPython(update_nofo_groups, reverse_func),
    ]
