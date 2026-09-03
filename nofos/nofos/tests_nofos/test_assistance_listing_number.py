from constance.test import override_config
from django.test import Client, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Section, Subsection


class AssistanceListingNumberModelTests(TestCase):
    def test_field_defaults_to_blank(self):
        nofo = Nofo.objects.create(
            title="Test NOFO",
            short_name="test-nofo",
            number="NOFO-TEST-001",
            opdiv="TEST",
            group="bloom",
            status="draft",
        )
        self.assertEqual(nofo.assistance_listing_number, "")

    def test_field_stores_value(self):
        nofo = Nofo.objects.create(
            title="Test NOFO",
            short_name="test-nofo",
            number="NOFO-TEST-001",
            opdiv="TEST",
            group="bloom",
            status="draft",
            assistance_listing_number="93.884",
        )
        nofo.refresh_from_db()
        self.assertEqual(nofo.assistance_listing_number, "93.884")


class NofoEditAssistanceListingNumberViewTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client = Client()
        self.client.login(email="test@example.com", password="testpass123")

        self.nofo = Nofo.objects.create(
            title="Test NOFO",
            short_name="test-nofo",
            number="NOFO-TEST-001",
            opdiv="TEST",
            group="bloom",
            status="draft",
            assistance_listing_number="93.884",
        )

        self.url = reverse(
            "nofos:nofo_edit_assistance_listing_number", kwargs={"pk": self.nofo.id}
        )

    @override_config(HHS_NOFO_ASSISTANCE_LISTING_ENABLED=False)
    def test_flag_off_404s_even_on_direct_visit(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    @override_config(HHS_NOFO_ASSISTANCE_LISTING_ENABLED=True)
    def test_flag_on_get_returns_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"].initial.get("assistance_listing_number"),
            "93.884",
        )

    @override_config(HHS_NOFO_ASSISTANCE_LISTING_ENABLED=True)
    def test_flag_on_post_updates_value(self):
        response = self.client.post(self.url, {"assistance_listing_number": "12.ABC"})
        self.assertEqual(response.status_code, 302)

        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.assistance_listing_number, "12.ABC")

    @override_config(HHS_NOFO_ASSISTANCE_LISTING_ENABLED=True)
    def test_flag_on_post_offers_matching_subsections(self):
        section = Section.objects.create(
            nofo=self.nofo, name="Key facts", html_id="key-facts", order=1
        )
        subsection = Subsection.objects.create(
            section=section,
            name="Key facts",
            order=1,
            body="<p>Assistance listing: 93.884</p>",
            tag="h4",
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        matches = response.context["subsection_matches"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["subsection"].id, subsection.id)

    @override_config(HHS_NOFO_ASSISTANCE_LISTING_ENABLED=True)
    def test_flag_on_post_syncs_checked_subsection(self):
        section = Section.objects.create(
            nofo=self.nofo, name="Key facts", html_id="key-facts", order=1
        )
        subsection = Subsection.objects.create(
            section=section,
            name="Key facts",
            order=1,
            body="<p>Assistance listing: 93.884</p>",
            tag="h4",
        )

        self.client.post(
            self.url,
            {
                "assistance_listing_number": "12.ABC",
                "replace_subsections": [str(subsection.id)],
            },
        )

        subsection.refresh_from_db()
        self.assertIn("12.ABC", subsection.body)
        self.assertNotIn("93.884", subsection.body)


class BasicInformationRowVisibilityTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client = Client()
        self.client.login(email="test@example.com", password="testpass123")

        self.nofo = Nofo.objects.create(
            title="Test NOFO",
            short_name="test-nofo",
            number="NOFO-TEST-001",
            opdiv="TEST",
            group="bloom",
            status="draft",
        )

        self.url = reverse("nofos:nofo_edit", kwargs={"pk": self.nofo.id})

    @override_config(HHS_NOFO_ASSISTANCE_LISTING_ENABLED=False)
    def test_flag_off_hides_row(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, "Assistance&nbsp;listing&nbsp;number")

    @override_config(HHS_NOFO_ASSISTANCE_LISTING_ENABLED=True)
    def test_flag_on_shows_row(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Assistance&nbsp;listing&nbsp;number")


class CoverPageDisplayTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client = Client()
        self.client.login(email="test@example.com", password="testpass123")

        self.nofo = Nofo.objects.create(
            title="Test NOFO",
            short_name="test-nofo",
            number="NOFO-TEST-001",
            opdiv="TEST",
            group="bloom",
            status="published",
            theme="landscape-cdc-blue",
            assistance_listing_number="93.884",
        )
        self.url = reverse("nofos:nofo_view", kwargs={"pk": self.nofo.id})

    @override_config(HHS_NOFO_ASSISTANCE_LISTING_ON_COVER_ENABLED=False)
    def test_flag_off_hides_value_from_cover(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, "93.884")

    @override_config(HHS_NOFO_ASSISTANCE_LISTING_ON_COVER_ENABLED=True)
    def test_flag_on_shows_value_on_cover(self):
        response = self.client.get(self.url)
        self.assertContains(response, "93.884")

    @override_config(HHS_NOFO_ASSISTANCE_LISTING_ON_COVER_ENABLED=True)
    def test_flag_on_but_no_value_shows_nothing(self):
        self.nofo.assistance_listing_number = ""
        self.nofo.save()

        response = self.client.get(self.url)
        self.assertNotContains(response, "Assistance listing number:")
