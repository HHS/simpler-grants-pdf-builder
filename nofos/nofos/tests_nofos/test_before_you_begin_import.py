from unittest.mock import patch

from bs4 import BeautifulSoup
from django.test import RequestFactory, TestCase
from users.models import BloomUser

from nofos.models import Nofo
from nofos.views import NofosImportNewView


class NofoBeforeYouBeginAutoAssignTest(TestCase):
    """Tests that importing a NOFO sets 'before_you_begin' based on the importing user's group.

    This exercises the real handle_nofo_create() -> suggest_all_nofo_fields()
    call, rather than mocking suggest_all_nofo_fields() away, because the
    behavior under test depends on nofo.group being assigned *before*
    suggest_all_nofo_fields() runs.
    """

    def _make_user(self, email, group):
        return BloomUser.objects.create_user(
            email=email,
            password="testpass123",
            full_name="Test User",
            group=group,
            force_password_reset=False,
        )

    def _call_handle_nofo_create(self, user):
        # Pre-create the Nofo that the mocked create_nofo will return.
        nofo = Nofo.objects.create(title="Test NOFO", opdiv="HHS")
        # suggest_all_nofo_fields() re-derives opdiv from the soup, so it must
        # be present here too, or the NOFO fails full_clean() (opdiv is required).
        soup = BeautifulSoup("<html><body><p>OpDiv: HHS</p></body></html>", "html.parser")

        request = RequestFactory().post("/")
        request.user = user

        view = NofosImportNewView()

        with patch("nofos.views.create_nofo", return_value=nofo), patch(
            "nofos.views.suggest_nofo_title", return_value="Test NOFO"
        ), patch("nofos.views.suggest_nofo_opdiv", return_value="HHS"), patch(
            "nofos.views.add_headings_to_document"
        ), patch(
            "nofos.views.add_page_breaks_to_headings"
        ), patch(
            "nofos.views.create_nofo_audit_event"
        ):
            view.handle_nofo_create(request, soup, [], "test.html")

        nofo.refresh_from_db()
        return nofo

    def test_nih_group_import_defaults_before_you_begin_to_era(self):
        user = self._make_user("nih@example.com", group="nih")
        nofo = self._call_handle_nofo_create(user)

        self.assertEqual(nofo.group, "nih")
        self.assertEqual(nofo.before_you_begin, "era")

    def test_non_nih_group_import_leaves_before_you_begin_full(self):
        user = self._make_user("bloom@example.com", group="bloom")
        nofo = self._call_handle_nofo_create(user)

        self.assertEqual(nofo.group, "bloom")
        self.assertEqual(nofo.before_you_begin, "full")
