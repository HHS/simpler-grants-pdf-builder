"""Join candidate review with readability file-category migrations."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("nofos", "0158_merge_candidate_review_and_history"),
        ("nofos", "0158_readability_attempt_file_category"),
    ]

    operations = []
