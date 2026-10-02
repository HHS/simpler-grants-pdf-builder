import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nofos", "0146_alter_externalsourcehandoff_group_alter_nofo_group"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="NofoReadabilityCheckpoint",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("saved_at", models.DateTimeField(auto_now_add=True)),
                (
                    "nofo_status_at_save",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("active", "Active"),
                            ("ready-for-qa", "Ready for QA"),
                            ("review", "In review"),
                            ("doge", "Dep Sec"),
                            ("published", "Published"),
                            ("paused", "Paused"),
                            ("cancelled", "Cancelled"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "saved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "score",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="checkpoint",
                        to="nofos.noforeadabilityscore",
                    ),
                ),
            ],
            options={"ordering": ["-saved_at", "-pk"]},
        ),
    ]
