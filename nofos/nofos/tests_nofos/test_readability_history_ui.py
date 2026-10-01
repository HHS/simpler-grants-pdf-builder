from datetime import timedelta
from unittest.mock import patch

from constance.test import override_config
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from users.models import BloomUser

from nofos.models import Nofo, NofoReadabilityCheckpoint, NofoReadabilityScore
from nofos.readability import (
    INPUT_CONTRACT_VERSION,
    PROFILE_REFERENCE,
    get_metrics_package_version,
)
from nofos.readability_history_views import NofoReadabilityHistoryView


class ReadabilityHistoryUiTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="history@example.com", password="synthetic", group="cdc"
        )
        self.nofo = Nofo.objects.create(
            title="History test", opdiv="CDC", group="cdc", status="draft"
        )
        self.factory = RequestFactory()

    def checkpoint(self, index=0, partial=False, user=None):
        score = NofoReadabilityScore.objects.create(
            nofo=self.nofo,
            nofo_revision=self.nofo.updated + timedelta(seconds=index),
            profile_reference=PROFILE_REFERENCE,
            package_version=get_metrics_package_version(),
            input_contract_version=INPUT_CONTRACT_VERSION,
            schema_version="1",
            result_basis="structured",
            is_complete=not partial,
            result={
                "metrics": {
                    "word_count": {"value": 100 + index, "status": "calculated"}
                }
            },
        )
        return NofoReadabilityCheckpoint.objects.create(
            score=score, saved_by=user, nofo_status_at_save="review"
        )

    def get_context(self, query="", user=None):
        request = self.factory.get("/history" + query)
        request.user = user or self.user
        with patch(
            "nofos.readability_history_views.render", return_value=HttpResponse()
        ) as renderer:
            response = NofoReadabilityHistoryView.as_view()(request, pk=self.nofo.pk)
        return renderer.call_args.args[2], response

    @override_config(HHS_NOFO_METRICS_ENABLED=True)
    def test_recent_fragment_shows_only_five_and_compares_sixth(self):
        for index in range(6):
            self.checkpoint(index)
        context, response = self.get_context("?fragment=1")
        self.assertEqual(len(context["readability_checkpoints"]), 5)
        self.assertNotEqual(
            context["readability_checkpoints"][-1]["change_summary"]["label"],
            "First snapshot",
        )
        self.assertEqual(response["Cache-Control"], "private, no-store")

    @override_config(HHS_NOFO_METRICS_ENABLED=True)
    def test_pagination_predecessor_across_page_boundary(self):
        for index in range(51):
            self.checkpoint(index)
        first, _ = self.get_context()
        self.assertEqual(len(first["readability_checkpoints"]), 50)
        self.assertNotEqual(
            first["readability_checkpoints"][-1]["change_summary"]["label"],
            "First snapshot",
        )
        second, _ = self.get_context("?page=2")
        self.assertEqual(
            second["readability_checkpoints"][0]["change_summary"]["label"],
            "First snapshot",
        )

    @override_config(HHS_NOFO_METRICS_ENABLED=True)
    def test_metrics_viewer_outside_group_is_read_only_and_can_read_archive(self):
        viewer = BloomUser.objects.create_user(
            email="viewer@example.com", password="synthetic", group="hrsa"
        )
        viewer.user_permissions.add(
            Permission.objects.get(codename="view_builder_metrics")
        )
        self.nofo.archived = self.nofo.updated
        self.nofo.save()
        context, _ = self.get_context(user=viewer)
        self.assertFalse(context["can_edit_nofo"])

    @override_config(HHS_NOFO_METRICS_ENABLED=True)
    def test_other_group_denied(self):
        outsider = BloomUser.objects.create_user(
            email="outsider@example.com", password="synthetic", group="hrsa"
        )
        with self.assertRaises(PermissionDenied):
            self.get_context(user=outsider)

    @override_config(HHS_NOFO_METRICS_ENABLED=False)
    def test_disabled_history_not_found(self):
        with self.assertRaises(Http404):
            self.get_context()

    @override_config(HHS_NOFO_METRICS_ENABLED=True)
    def test_partial_deleted_user_and_unavailable_values_in_fragment(self):
        self.checkpoint(partial=True)
        context, _ = self.get_context("?fragment=1")
        # Avoid depending on root's URL integration while testing this include.
        with patch("django.urls.reverse", return_value="/history"):
            html = render_to_string(
                "nofos/includes/readability_saved_snapshots.html", context
            )
        self.assertIn("Deleted user", html)
        self.assertIn("Partial results", html)
        self.assertIn("Unavailable", html)
        self.assertIn("Flesch Reading Ease", html)
        self.assertIn("Current version", html)
