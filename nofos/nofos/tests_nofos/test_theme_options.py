from django.test import Client, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.forms import NIH_ALLOWED_CHOICES, NIH_THEME_DEFAULTS, NofoThemeOptionsForm
from nofos.models import Nofo


def _make_nofo(group, **overrides):
    defaults = dict(
        title="Test NOFO",
        short_name="test-nofo",
        number="TEST-001",
        opdiv="TEST",
        group=group,
        status="draft",
    )
    defaults.update(overrides)
    return Nofo.objects.create(**defaults)


def _make_user(group):
    return BloomUser.objects.create_user(
        email=f"{group}@example.com",
        password="testpass123",
        group=group,
        force_password_reset=False,
    )


class NIHUserThemeOptionsFormTests(TestCase):
    def setUp(self):
        self.user = _make_user("nih")
        self.nofo = _make_nofo("nih")

    def test_theme_choices_restricted_to_nih_only(self):
        form = NofoThemeOptionsForm(instance=self.nofo, user=self.user)
        all_values = [v for _, opts in form.fields["theme"].choices for v, _ in opts]
        self.assertEqual(all_values, ["portrait-nih-white"])

    def test_cover_choices_exclude_hero(self):
        form = NofoThemeOptionsForm(instance=self.nofo, user=self.user)
        cover_values = [v for v, _ in form.fields["cover"].choices]
        self.assertIn("nofo--cover-page--text", cover_values)
        self.assertIn("nofo--cover-page--medium", cover_values)
        self.assertNotIn("nofo--cover-page--hero", cover_values)

    def test_icon_style_choices_restricted_to_outlined(self):
        form = NofoThemeOptionsForm(instance=self.nofo, user=self.user)
        icon_values = [v for v, _ in form.fields["icon_style"].choices]
        self.assertEqual(icon_values, ["nofo--icons--solid"])

    def test_valid_submission_with_nih_defaults(self):
        data = {
            "theme": "portrait-nih-white",
            "cover": "nofo--cover-page--text",
            "icon_style": "nofo--icons--solid",
        }
        form = NofoThemeOptionsForm(data, instance=self.nofo, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_submission_with_standard_image_cover(self):
        data = {
            "theme": "portrait-nih-white",
            "cover": "nofo--cover-page--medium",
            "icon_style": "nofo--icons--solid",
        }
        form = NofoThemeOptionsForm(data, instance=self.nofo, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_disallowed_theme_rejected(self):
        data = {
            "theme": "portrait-hrsa-blue",
            "cover": "nofo--cover-page--text",
            "icon_style": "nofo--icons--solid",
        }
        form = NofoThemeOptionsForm(data, instance=self.nofo, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("theme", form.errors)

    def test_disallowed_cover_rejected(self):
        data = {
            "theme": "portrait-nih-white",
            "cover": "nofo--cover-page--hero",
            "icon_style": "nofo--icons--solid",
        }
        form = NofoThemeOptionsForm(data, instance=self.nofo, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("cover", form.errors)

    def test_disallowed_icon_style_rejected(self):
        data = {
            "theme": "portrait-nih-white",
            "cover": "nofo--cover-page--text",
            "icon_style": "nofo--icons--border",
        }
        form = NofoThemeOptionsForm(data, instance=self.nofo, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("icon_style", form.errors)


class NIHUserThemeOptionsViewTests(TestCase):
    def setUp(self):
        self.user = _make_user("nih")
        self.nofo = _make_nofo(
            "nih",
            theme="portrait-hrsa-blue",
            cover="nofo--cover-page--hero",
            icon_style="nofo--icons--border",
        )
        self.client = Client()
        self.client.login(email="nih@example.com", password="testpass123")
        self.url = reverse("nofos:nofo_edit_theme_options", kwargs={"pk": self.nofo.id})

    def test_get_auto_sets_nih_defaults(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.theme, NIH_THEME_DEFAULTS["theme"])
        self.assertEqual(self.nofo.cover, NIH_THEME_DEFAULTS["cover"])
        self.assertEqual(self.nofo.icon_style, NIH_THEME_DEFAULTS["icon_style"])

    def test_get_does_not_resave_when_already_correct(self):
        self.nofo.theme = NIH_THEME_DEFAULTS["theme"]
        self.nofo.cover = NIH_THEME_DEFAULTS["cover"]
        self.nofo.icon_style = NIH_THEME_DEFAULTS["icon_style"]
        self.nofo.save()
        original_updated = Nofo.objects.get(pk=self.nofo.pk).updated

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Nofo.objects.get(pk=self.nofo.pk).updated, original_updated)

    def _set_nih_defaults(self):
        for field, value in NIH_THEME_DEFAULTS.items():
            setattr(self.nofo, field, value)
        self.nofo.save()

    def test_post_disallowed_theme_rejected(self):
        self._set_nih_defaults()
        response = self.client.post(
            self.url,
            {
                "theme": "portrait-hrsa-blue",  # not in NIH_ALLOWED_CHOICES
                "cover": "nofo--cover-page--text",
                "icon_style": "nofo--icons--solid",
            },
        )
        # Form invalid: re-renders, does not redirect
        self.assertEqual(response.status_code, 200)
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.theme, NIH_THEME_DEFAULTS["theme"])

    def test_post_disallowed_cover_rejected(self):
        self._set_nih_defaults()
        response = self.client.post(
            self.url,
            {
                "theme": "portrait-nih-white",
                "cover": "nofo--cover-page--hero",  # not in NIH_ALLOWED_CHOICES
                "icon_style": "nofo--icons--solid",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.cover, NIH_THEME_DEFAULTS["cover"])

    def test_post_disallowed_icon_style_rejected(self):
        self._set_nih_defaults()
        response = self.client.post(
            self.url,
            {
                "theme": "portrait-nih-white",
                "cover": "nofo--cover-page--text",
                "icon_style": "nofo--icons--border",  # not in NIH_ALLOWED_CHOICES
            },
        )
        self.assertEqual(response.status_code, 200)
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.icon_style, NIH_THEME_DEFAULTS["icon_style"])

    def test_post_valid_nih_values_saved(self):
        response = self.client.post(
            self.url,
            {
                "theme": "portrait-nih-white",
                "cover": "nofo--cover-page--medium",
                "icon_style": "nofo--icons--solid",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.theme, "portrait-nih-white")
        self.assertEqual(self.nofo.cover, "nofo--cover-page--medium")
        self.assertEqual(self.nofo.icon_style, "nofo--icons--solid")


class NonNIHUserThemeOptionsTests(TestCase):
    def setUp(self):
        self.user = _make_user("hrsa")
        self.nofo = _make_nofo(
            "hrsa",
            theme="portrait-hrsa-blue",
            cover="nofo--cover-page--hero",
            icon_style="nofo--icons--border",
        )
        self.client = Client()
        self.client.login(email="hrsa@example.com", password="testpass123")
        self.url = reverse("nofos:nofo_edit_theme_options", kwargs={"pk": self.nofo.id})

    def test_non_nih_user_sees_all_cover_choices(self):
        form = NofoThemeOptionsForm(instance=self.nofo, user=self.user)
        cover_values = [v for v, _ in form.fields["cover"].choices]
        self.assertIn("nofo--cover-page--hero", cover_values)
        self.assertIn("nofo--cover-page--medium", cover_values)
        self.assertIn("nofo--cover-page--text", cover_values)

    def test_non_nih_user_sees_multiple_icon_style_choices(self):
        form = NofoThemeOptionsForm(instance=self.nofo, user=self.user)
        icon_values = [v for v, _ in form.fields["icon_style"].choices]
        # Non-NIH themes get at least the border and solid options
        self.assertGreater(len(icon_values), 1)

    def test_non_nih_user_get_does_not_change_nofo_fields(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.theme, "portrait-hrsa-blue")
        self.assertEqual(self.nofo.cover, "nofo--cover-page--hero")
        self.assertEqual(self.nofo.icon_style, "nofo--icons--border")

    def test_non_nih_user_can_submit_any_valid_cover(self):
        data = {
            "theme": "portrait-hrsa-blue",
            "cover": "nofo--cover-page--hero",
            "icon_style": "nofo--icons--border",
        }
        form = NofoThemeOptionsForm(data, instance=self.nofo, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
