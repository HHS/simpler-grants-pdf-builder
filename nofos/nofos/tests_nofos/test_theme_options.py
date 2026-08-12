from django.test import Client, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.forms import NIH_ALLOWED_CHOICES, NIH_THEME_DEFAULTS, NofoThemeOptionsForm
from nofos.models import Nofo


def _theme_choice_values(form):
    return [
        value for _, options in form.fields["theme"].choices for value, _ in options
    ]


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
        self.assertEqual(_theme_choice_values(form), ["portrait-nih-white"])

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

    def test_get_preserves_allowed_non_default_cover(self):
        # nofo--cover-page--medium is allowed for NIH but is not the default;
        # it must not be reset back to nofo--cover-page--text on page load.
        self.nofo.theme = NIH_THEME_DEFAULTS["theme"]
        self.nofo.cover = "nofo--cover-page--medium"
        self.nofo.icon_style = NIH_THEME_DEFAULTS["icon_style"]
        self.nofo.save()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.cover, "nofo--cover-page--medium")

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
            theme="portrait-hrsa-white",
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

    def test_hrsa_user_only_sees_hrsa_light_theme(self):
        form = NofoThemeOptionsForm(instance=self.nofo, user=self.user)
        self.assertEqual(_theme_choice_values(form), ["portrait-hrsa-white"])

    def test_bloom_user_does_not_see_retired_hrsa_theme(self):
        bloom_user = _make_user("bloom")
        form = NofoThemeOptionsForm(instance=self.nofo, user=bloom_user)
        theme_values = _theme_choice_values(form)
        self.assertIn("portrait-hrsa-white", theme_values)
        self.assertNotIn("portrait-hrsa-blue", theme_values)

    def test_new_nofo_cannot_select_retired_hrsa_theme(self):
        unsaved_nofo = Nofo(group="hrsa", theme="portrait-hrsa-blue")
        form = NofoThemeOptionsForm(instance=unsaved_nofo, user=self.user)
        self.assertNotIn("portrait-hrsa-blue", _theme_choice_values(form))

    def test_non_nih_user_sees_multiple_icon_style_choices(self):
        form = NofoThemeOptionsForm(instance=self.nofo, user=self.user)
        icon_values = [v for v, _ in form.fields["icon_style"].choices]
        # Non-NIH themes get at least the border and solid options
        self.assertGreater(len(icon_values), 1)

    def test_non_nih_user_get_does_not_change_nofo_fields(self):
        self.nofo.theme = "portrait-hrsa-blue"
        self.nofo.save()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.theme, "portrait-hrsa-blue")
        self.assertEqual(self.nofo.cover, "nofo--cover-page--hero")
        self.assertEqual(self.nofo.icon_style, "nofo--icons--border")

    def test_legacy_hrsa_theme_can_be_preserved_when_saving_other_options(self):
        self.nofo.theme = "portrait-hrsa-blue"
        self.nofo.save()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "HRSA (Default, legacy)")
        self.assertContains(
            response,
            '<option value="portrait-hrsa-blue" selected>',
        )

        response = self.client.post(
            self.url,
            {
                "theme": "portrait-hrsa-blue",
                "cover": "nofo--cover-page--medium",
                "icon_style": "nofo--icons--solid",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.theme, "portrait-hrsa-blue")
        self.assertEqual(self.nofo.cover, "nofo--cover-page--medium")
        self.assertEqual(self.nofo.icon_style, "nofo--icons--solid")

    def test_legacy_hrsa_theme_remains_model_valid_and_renderable(self):
        self.nofo.theme = "portrait-hrsa-blue"
        self.nofo.full_clean()
        self.nofo.save()
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.theme, "portrait-hrsa-blue")

        response = self.client.get(
            reverse("nofos:nofo_view", kwargs={"pk": self.nofo.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "portrait-hrsa-blue")

    def test_non_nih_user_can_submit_any_valid_cover(self):
        data = {
            "theme": "portrait-hrsa-white",
            "cover": "nofo--cover-page--hero",
            "icon_style": "nofo--icons--border",
        }
        form = NofoThemeOptionsForm(data, instance=self.nofo, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_retired_hrsa_theme_submission_is_rejected(self):
        data = {
            "theme": "portrait-hrsa-blue",
            "cover": "nofo--cover-page--hero",
            "icon_style": "nofo--icons--border",
        }
        form = NofoThemeOptionsForm(data, instance=self.nofo, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("theme", form.errors)


class RetiredCdcLandscapeThemeTests(TestCase):
    """
    The "CDC Landscape (Default)" and "CDC Landscape (Light)" themes
    (landscape-cdc-blue / landscape-cdc-white) were removed from the
    Builder's theme selection dropdown (issue #479) because they were
    unused. They must not be offered as a choice on any NOFO, but a NOFO
    that already has one of these themes assigned must still show/preserve
    that value instead of silently switching to something else.
    """

    def setUp(self):
        self.user = _make_user("cdc")

    def test_retired_themes_excluded_for_nofo_with_current_theme(self):
        nofo = _make_nofo("cdc", theme="portrait-cdc-blue")
        form = NofoThemeOptionsForm(instance=nofo, user=self.user)
        theme_values = _theme_choice_values(form)
        self.assertNotIn("landscape-cdc-blue", theme_values)
        self.assertNotIn("landscape-cdc-white", theme_values)

    def test_retired_theme_preserved_when_already_assigned(self):
        nofo = _make_nofo("cdc", theme="landscape-cdc-blue")
        form = NofoThemeOptionsForm(instance=nofo, user=self.user)
        theme_values = _theme_choice_values(form)
        # The NOFO's own (retired) theme is preserved as a choice...
        self.assertIn("landscape-cdc-blue", theme_values)
        # ...but the *other* retired theme is still not offered.
        self.assertNotIn("landscape-cdc-white", theme_values)

    def test_retired_theme_not_reintroduced_for_other_nofos(self):
        # Assigning the retired theme to one NOFO must not leak it back
        # into the choices offered for a different NOFO.
        _make_nofo("cdc", theme="landscape-cdc-blue")
        other_nofo = _make_nofo("cdc", theme="portrait-cdc-white")
        form = NofoThemeOptionsForm(instance=other_nofo, user=self.user)
        self.assertNotIn("landscape-cdc-blue", _theme_choice_values(form))

    def test_get_edit_view_preserves_retired_theme(self):
        nofo = _make_nofo(
            "cdc",
            theme="landscape-cdc-white",
            cover="nofo--cover-page--hero",
            icon_style="nofo--icons--border",
        )
        client = Client()
        client.login(email="cdc@example.com", password="testpass123")
        url = reverse("nofos:nofo_edit_theme_options", kwargs={"pk": nofo.id})

        response = client.get(url)

        self.assertEqual(response.status_code, 200)
        nofo.refresh_from_db()
        self.assertEqual(nofo.theme, "landscape-cdc-white")
        self.assertContains(response, "CDC Landscape (Light, legacy)")
        self.assertContains(response, 'value="landscape-cdc-white" selected')

    def test_valid_submission_can_keep_existing_retired_theme(self):
        # A user shouldn't be forced off a retired theme just because
        # it's no longer offered for *new* selections.
        nofo = _make_nofo("cdc", theme="landscape-cdc-blue")
        data = {
            "theme": "landscape-cdc-blue",
            "cover": "nofo--cover-page--text",
            "icon_style": "nofo--icons--solid",
        }
        form = NofoThemeOptionsForm(data, instance=nofo, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_retired_theme_submission_is_rejected_for_other_nofo(self):
        # Switching *into* a retired theme from a non-retired one must fail.
        nofo = _make_nofo("cdc", theme="portrait-cdc-blue")
        data = {
            "theme": "landscape-cdc-blue",
            "cover": "nofo--cover-page--text",
            "icon_style": "nofo--icons--solid",
        }
        form = NofoThemeOptionsForm(data, instance=nofo, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("theme", form.errors)
