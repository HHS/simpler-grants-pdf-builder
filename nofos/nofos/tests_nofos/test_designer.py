from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.forms import NofoCoachDesignerForm
from nofos.models import Nofo


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

    def _get_minimal_html(self, title="Test NOFO"):
        return (
            f"<html><body>"
            f"<h1>{title}</h1>"
            f"<h2>Step 1: Review the Opportunity</h2>"
            f"<h3>Basic Information</h3>"
            f"<p>Some content.</p>"
            f"</body></html>"
        )

    def _post_import(self, user, html_content=None):
        if html_content is None:
            html_content = self._get_minimal_html()
        self.client.force_login(user)
        uploaded = SimpleUploadedFile(
            "test.html",
            html_content.encode("utf-8"),
            content_type="text/html",
        )
        return self.client.post(
            reverse("nofos:nofo_import"),
            {"file": uploaded},
        )

    def test_nofo_creation_assigns_designer_from_user_full_name(self):
        """Importing a NOFO sets designer to the logged-in user's full_name."""
        user = self._make_user("jana@example.com", "Jana Smith", group="bloom")
        response = self._post_import(user)

        self.assertIn(response.status_code, [302, 200])
        nofo = Nofo.objects.order_by("-created").first()
        self.assertIsNotNone(nofo)
        self.assertEqual(nofo.designer, "Jana Smith")

    def test_nofo_creation_with_blank_full_name_leaves_designer_blank(self):
        """Importing a NOFO when user has no full_name leaves designer blank."""
        user = self._make_user("noname@example.com", "", group="hrsa")
        response = self._post_import(user)

        self.assertIn(response.status_code, [302, 200])
        nofo = Nofo.objects.order_by("-created").first()
        self.assertIsNotNone(nofo)
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
