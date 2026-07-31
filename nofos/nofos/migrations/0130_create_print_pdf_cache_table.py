from django.db import migrations


def create_cache_table(apps, schema_editor):
    from django.core.management import call_command

    call_command("createcachetable")


def drop_cache_table(apps, schema_editor):
    schema_editor.execute('DROP TABLE IF EXISTS "django_cache"')


class Migration(migrations.Migration):

    dependencies = [
        ("nofos", "0129_alter_nofo_theme"),
    ]

    operations = [
        migrations.RunPython(create_cache_table, drop_cache_table),
    ]
