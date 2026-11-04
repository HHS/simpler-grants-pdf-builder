"""Join candidate tool access with the current design-pilot/history schema."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("nofos", "0155_design_candidate_tool_access"),
        ("nofos", "0156_merge_20261026_1349"),
    ]

    operations = []
