from django.db import migrations

CACHE_TABLE_NAME = "django_cache"


def create_cache_table(apps, schema_editor):
    from django.core.management import call_command

    call_command(
        "createcachetable", CACHE_TABLE_NAME, database=schema_editor.connection.alias
    )


def drop_cache_table(apps, schema_editor):
    schema_editor.execute(
        "DROP TABLE IF EXISTS %s" % schema_editor.quote_name(CACHE_TABLE_NAME)
    )


class Migration(migrations.Migration):

    dependencies = [
        ("nofos", "0129_alter_nofo_theme"),
    ]

    operations = [
        migrations.RunPython(create_cache_table, drop_cache_table),
    ]
