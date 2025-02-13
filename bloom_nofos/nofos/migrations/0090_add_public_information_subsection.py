# Generated manually

from django.db import migrations

PUBLIC_INFORMATION_SUBSECTION = {
    "name": "Important: public information",
    "tag": "h5",
    "html_id": "",
    "is_callout_box": True,
    "body": """
When filling out your SF-424 form, pay attention to Box 15: Descriptive Title of Applicant's Project.

We share what you put there with [USAspending](https://www.usaspending.gov). This is where the public goes to learn how the federal government spends their money.

Instead of just a title, insert a short description of your project and what it will do.

[See instructions and examples](https://www.hhs.gov/sites/default/files/hhs-writing-award-descriptions.pdf).
""",
}


def add_public_information_subsection(apps, schema_editor):
    """
    Add the public information subsection to Step 3 of existing NOFOs if it doesn't already exist.
    """
    Section = apps.get_model("nofos", "Section")
    Subsection = apps.get_model("nofos", "Subsection")

    # The target section names to search for
    step_3_names = [
        "Step 3: Prepare Your Application",
        "Step 3: Write Your Application",
    ]

    # Find all Step 3 sections
    step_3_sections = Section.objects.filter(
        name__iregex=r"^Step 3: (Prepare|Write) Your Application$"
    )

    for section in step_3_sections:
        # Check if public information subsection already exists
        if not Subsection.objects.filter(
            section=section, name=PUBLIC_INFORMATION_SUBSECTION["name"]
        ).exists():
            # Get the highest order number in this section
            last_order = (
                Subsection.objects.filter(section=section).order_by("-order").first()
            )
            new_order = (last_order.order + 1) if last_order else 1

            # Create new subsection
            Subsection.objects.create(
                section=section,
                name=PUBLIC_INFORMATION_SUBSECTION["name"],
                tag=PUBLIC_INFORMATION_SUBSECTION["tag"],
                html_id="",  # This will be set by add_headings_to_nofo later
                callout_box=PUBLIC_INFORMATION_SUBSECTION["is_callout_box"],
                body=PUBLIC_INFORMATION_SUBSECTION["body"],
                order=new_order,
            )


def reverse_func(apps, schema_editor):
    """
    Reverse the migration by removing all public information subsections.
    """
    Subsection = apps.get_model("nofos", "Subsection")
    Subsection.objects.filter(name=PUBLIC_INFORMATION_SUBSECTION["name"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        (
            "nofos",
            "0089_alter_nofo_theme",
        ),
    ]

    operations = [
        migrations.RunPython(add_public_information_subsection, reverse_func),
    ]
