from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("easyaudit", "0019_alter_crudevent_changed_fields_and_more"),
    ]

    operations = [
        # 1) Remove admin log rows that reference 'guides' content types
        migrations.RunSQL("""
            DELETE FROM django_admin_log
            WHERE content_type_id IN (
              SELECT id FROM django_content_type WHERE app_label = 'guides'
            );
        """),
        # 2) Remove EasyAudit rows that reference 'guides' content types
        migrations.RunSQL("""
            DELETE FROM easyaudit_crudevent
            WHERE content_type_id IN (
              SELECT id FROM django_content_type WHERE app_label = 'guides'
            );
        """),
        # 3) Remove auth permissions tied to 'guides' content types
        migrations.RunSQL("""
            DELETE FROM auth_permission
            WHERE content_type_id IN (
              SELECT id FROM django_content_type WHERE app_label = 'guides'
            );
        """),
        # 4) Drop legacy tables (child → parent). No CASCADE for SQLite compatibility.
        migrations.RunSQL("DROP TABLE IF EXISTS guides_contentguidesubsection;"),
        migrations.RunSQL("DROP TABLE IF EXISTS guides_contentguidesection;"),
        migrations.RunSQL("DROP TABLE IF EXISTS guides_contentguide;"),
        # 5) Remove the content types themselves
        migrations.RunSQL(
            "DELETE FROM django_content_type WHERE app_label = 'guides';"
        ),
        # 6) Remove migration history rows for the retired app label
        migrations.RunSQL("DELETE FROM django_migrations WHERE app = 'guides';"),
    ]
