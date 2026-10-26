"""Join candidate review decisions with the current access/history schema."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("nofos", "0156_design_pilot_review_decision"),
        ("nofos", "0157_merge_candidate_access_and_history"),
    ]

    operations = []
