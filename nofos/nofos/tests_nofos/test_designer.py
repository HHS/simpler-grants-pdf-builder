from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase
from users.models import BloomUser

from nofos.forms import NofoCoachDesignerForm
from nofos.models import Nofo
from nofos.views import NofosImportNewView


class NofoDesignerAutoAssignTest(TestCase):
    """Tests for auto-assigning designer on NOFO creation via import."""

    def _make_user(self, email, full_name, group="bloom"):
        return BloomUser.objects.create_user(
            email=email,
            password="testpass123",
            full_name=full_name,
            group=group,
            force_password_reset=False,
        )

    def _call_handle_nofo_create(self, user):
        """Call handle_nofo_create directly, mocking the import pipeline.

        This bypasses the HTTP layer and the HTML-parsing pipeline entirely so
        that the test focuses solely on the designer auto-assignment logic.
        """
        # Pre-create the Nofo that the mocked create_nofo will return.
        nofo = Nofo.objects.create(title="Test NOFO", opdiv="HHS")

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
            "nofos.views.suggest_all_nofo_fields"
        ), patch(
            "nofos.views.create_nofo_audit_event"
        ):
            view.handle_nofo_create(request, MagicMock(), [], "test.html")

        nofo.refresh_from_db()
        return nofo

    def test_nofo_creation_assigns_designer_from_user_full_name(self):
        """handle_nofo_create sets designer to the logged-in user's full_name."""
        user = self._make_user("jana@example.com", "Jana Smith", group="bloom")
        nofo = self._call_handle_nofo_create(user)
        self.assertEqual(nofo.designer, "Jana Smith")

    def test_nofo_creation_with_blank_full_name_leaves_designer_blank(self):
        """handle_nofo_create leaves designer blank when user has no full_name."""
        user = self._make_user("noname@example.com", "", group="hrsa")
        nofo = self._call_handle_nofo_create(user)
        self.assertEqual(nofo.designer, "")

    def test_nofo_creation_strips_whitespace_only_full_name(self):
        """handle_nofo_create stores '' when user full_name is whitespace only."""
        user = self._make_user("spaces@example.com", "   ", group="bloom")
        nofo = self._call_handle_nofo_create(user)
        self.assertEqual(nofo.designer, "")


class NofoCoachDesignerFormTest(TestCase):
    """Tests for the NofoCoachDesignerForm designer dropdown filtering."""

    def _make_user(self, email, full_name, group, is_active=True):
        user = BloomUser.objects.create_user(
            email=email,
            password="testpass123",
            full_name=full_name,
            group=group,
            force_password_reset=False,
        )
        if not is_active:
            BloomUser.objects.filter(pk=user.pk).update(is_active=False)
            user.refresh_from_db()
        return user

    def _make_nofo(self):
        return Nofo.objects.create(title="Test NOFO", opdiv="Test OpDiv")

    def setUp(self):
        self.nofo = self._make_nofo()

    def test_designer_dropdown_includes_only_same_group_users(self):
        """Dropdown only shows users whose group matches the logged-in user's group."""
        bloom_user = self._make_user("bloom1@example.com", "Bloom Alice", group="bloom")
        self._make_user("bloom2@example.com", "Bloom Bob", group="bloom")
        self._make_user("hrsa1@example.com", "HRSA Carol", group="hrsa")

        form = NofoCoachDesignerForm(instance=self.nofo, user=bloom_user)
        choices = dict(form.fields["designer"].choices)

        self.assertIn("Bloom Alice", choices)
        self.assertIn("Bloom Bob", choices)
        self.assertNotIn("HRSA Carol", choices)

    def test_designer_dropdown_excludes_inactive_users(self):
        """Dropdown excludes users where is_active=False."""
        active_user = self._make_user("active@example.com", "Active User", group="hrsa")
        self._make_user(
            "inactive@example.com", "Inactive User", group="hrsa", is_active=False
        )

        form = NofoCoachDesignerForm(instance=self.nofo, user=active_user)
        choices = dict(form.fields["designer"].choices)

        self.assertIn("Active User", choices)
        self.assertNotIn("Inactive User", choices)

    def test_designer_dropdown_sorted_alphabetically(self):
        """Dropdown options are sorted A–Z by full_name."""
        requesting_user = self._make_user(
            "requester@example.com", "Zebra Zee", group="cdc"
        )
        self._make_user("charlie@example.com", "Charlie Chen", group="cdc")
        self._make_user("alice@example.com", "Alice Adams", group="cdc")
        self._make_user("bob@example.com", "Bob Brown", group="cdc")

        form = NofoCoachDesignerForm(instance=self.nofo, user=requesting_user)
        # Skip the empty sentinel choice at index 0
        names = [
            label
            for _, label in form.fields["designer"].choices
            if label != "---------"
        ]

        self.assertEqual(names, sorted(names))
        self.assertEqual(names[0], "Alice Adams")

    def test_designer_dropdown_uses_full_name_as_stored_value(self):
        """The stored value (option value) equals the user's full_name."""
        user = self._make_user("designer@example.com", "Jana Smith", group="bloom")

        form = NofoCoachDesignerForm(instance=self.nofo, user=user)
        choices = dict(form.fields["designer"].choices)

        self.assertIn("Jana Smith", choices)
        self.assertEqual(choices["Jana Smith"], "Jana Smith")

    def test_designer_dropdown_empty_when_no_user_provided(self):
        """When user=None, the dropdown has only the empty sentinel."""
        self._make_user("anyone@example.com", "Anyone", group="bloom")

        form = NofoCoachDesignerForm(instance=self.nofo, user=None)
        non_empty_choices = [
            (v, l) for v, l in form.fields["designer"].choices if v != ""
        ]

        self.assertEqual(non_empty_choices, [])

    def test_designer_dropdown_bloom_user_sees_only_bloom_users(self):
        """Bloomworks users see only other Bloomworks users, not OpDiv users."""
        bloom_user = self._make_user(
            "bloom@example.com", "Bloom Designer", group="bloom"
        )
        self._make_user("hrsa@example.com", "HRSA Designer", group="hrsa")
        self._make_user("cdc@example.com", "CDC Designer", group="cdc")

        form = NofoCoachDesignerForm(instance=self.nofo, user=bloom_user)
        choices = dict(form.fields["designer"].choices)

        self.assertIn("Bloom Designer", choices)
        self.assertNotIn("HRSA Designer", choices)
        self.assertNotIn("CDC Designer", choices)

    def test_designer_dropdown_preserves_legacy_slug_for_existing_nofo(self):
        """An existing NOFO with a legacy slug value keeps it selectable."""
        Nofo.objects.filter(pk=self.nofo.pk).update(designer="bloom-adam")
        self.nofo.refresh_from_db()

        user = self._make_user("bloom@example.com", "Active Bloom", group="bloom")
        form = NofoCoachDesignerForm(instance=self.nofo, user=user)
        choice_values = [v for v, _ in form.fields["designer"].choices]

        self.assertIn("bloom-adam", choice_values)

    def test_designer_dropdown_legacy_slug_displays_human_label(self):
        """A legacy slug in the choices list is labelled with its human-readable name."""
        Nofo.objects.filter(pk=self.nofo.pk).update(designer="bloom-adam")
        self.nofo.refresh_from_db()

        user = self._make_user("bloom@example.com", "Active Bloom", group="bloom")
        form = NofoCoachDesignerForm(instance=self.nofo, user=user)
        choices = dict(form.fields["designer"].choices)

        self.assertEqual(choices.get("bloom-adam"), "Adam")
