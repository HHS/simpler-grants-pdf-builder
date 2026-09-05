from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone
from easyaudit.models import CRUDEvent
from users.models import BloomUser

from nofos.metrics import (
    active_users_by_month,
    avg_warnings_by_month,
    import_error_rate_by_month,
    month_boundaries,
    nofos_created_by_month,
    time_to_first_live_pdf_by_month,
    total_users_by_month,
)
from nofos.models import ImportAttempt, Nofo


class MetricsExcludeInternalGroupsTests(TestCase):
    """
    BloomUser.group / Nofo.group values of "bloom" (Bloomworks staff/admins)
    and "staging" (the staging test environment) aren't real OpDiv end-users,
    so every metric excludes them - otherwise internal activity would inflate
    numbers meant to describe actual product usage. See metrics.py's
    EXCLUDED_GROUPS.
    """

    def setUp(self):
        self.months = month_boundaries(timezone.now(), 1)

    def test_total_users_excludes_bloom_and_staging(self):
        BloomUser.objects.create_user(
            email="cdc@example.com", password="x", group="cdc"
        )
        BloomUser.objects.create_user(
            email="bloom@example.com", password="x", group="bloom"
        )
        BloomUser.objects.create_user(
            email="staging@example.com", password="x", group="staging"
        )

        self.assertEqual(total_users_by_month(self.months), [1])

    def test_active_users_excludes_bloom_and_staging(self):
        cdc_user = BloomUser.objects.create_user(
            email="cdc@example.com", password="x", group="cdc"
        )
        bloom_user = BloomUser.objects.create_user(
            email="bloom@example.com", password="x", group="bloom"
        )
        nofo_content_type = ContentType.objects.get_for_model(Nofo)

        for user in (cdc_user, bloom_user):
            CRUDEvent.objects.create(
                event_type=CRUDEvent.CREATE,
                object_id="1",
                content_type=nofo_content_type,
                user=user,
            )

        self.assertEqual(active_users_by_month(self.months), [1])

    def test_nofos_created_excludes_bloom_and_staging(self):
        Nofo.objects.create(title="CDC Nofo", number="CDC-001", opdiv="CDC", group="cdc")
        Nofo.objects.create(
            title="Bloom Nofo", number="BLOOM-001", opdiv="ACF", group="bloom"
        )

        self.assertEqual(nofos_created_by_month(self.months), [1])

    def test_import_error_rate_excludes_bloom_and_staging(self):
        cdc_user = BloomUser.objects.create_user(
            email="cdc@example.com", password="x", group="cdc"
        )
        bloom_user = BloomUser.objects.create_user(
            email="bloom@example.com", password="x", group="bloom"
        )

        ImportAttempt.objects.create(
            user=cdc_user, filename="a.html", error_code="IMPORT-UNEXPECTED"
        )
        ImportAttempt.objects.create(user=bloom_user, filename="b.html", error_code="")

        # Only the CDC attempt counts, and it failed - 100%, not 50%.
        self.assertEqual(import_error_rate_by_month(self.months), [100.0])

    def test_avg_warnings_excludes_bloom_and_staging(self):
        cdc_user = BloomUser.objects.create_user(
            email="cdc@example.com", password="x", group="cdc"
        )
        bloom_user = BloomUser.objects.create_user(
            email="bloom@example.com", password="x", group="bloom"
        )

        ImportAttempt.objects.create(user=cdc_user, filename="a.html", warning_count=2)
        ImportAttempt.objects.create(
            user=bloom_user, filename="b.html", warning_count=100
        )

        self.assertEqual(avg_warnings_by_month(self.months), [2.0])

    def test_time_to_first_live_pdf_excludes_bloom_and_staging(self):
        Nofo.objects.create(
            title="Bloom Nofo", number="BLOOM-002", opdiv="ACF", group="bloom"
        )

        # No non-excluded NOFOs exist, so there's nothing to measure.
        self.assertEqual(time_to_first_live_pdf_by_month(self.months), [None])
