# Generated by Django 4.2.7 on 2023-11-30 21:20

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_bloomuser_force_password_reset"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bloomuser",
            name="force_password_reset",
            field=models.BooleanField(
                default=False,
                help_text="Require this user to reset their password the next time they log in",
            ),
        ),
    ]