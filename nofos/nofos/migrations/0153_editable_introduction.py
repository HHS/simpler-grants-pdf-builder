from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("nofos", "0152_readability_checkpoint_per_trigger")]

    operations = [
        migrations.AddField(
            model_name="nofo",
            name="introductory_content_mode",
            field=models.CharField(
                max_length=20,
                default="generated",
                editable=False,
                choices=[
                    ("generated", "Generated template"),
                    ("imported", "Editable imported content"),
                ],
            ),
        ),
        migrations.AddField(
            model_name="section",
            name="role",
            field=models.CharField(
                max_length=20,
                default="",
                blank=True,
                editable=False,
                choices=[
                    ("", "Ordinary section"),
                    ("introduction", "Editable introduction"),
                ],
            ),
        ),
        migrations.AddConstraint(
            model_name="section",
            constraint=models.UniqueConstraint(
                fields=("nofo",),
                condition=models.Q(role="introduction"),
                name="one_imported_introduction_per_nofo",
            ),
        ),
    ]
