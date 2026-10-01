import re

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Section, Subsection


class SharedThemeHeadingSpacingTests(SimpleTestCase):
    def test_h3_has_extra_space_before_following_content(self):
        css_path = finders.find("theme-base.css")
        self.assertIsNotNone(
            css_path, "theme-base.css not found by staticfiles finders"
        )

        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        rule_match = re.search(r"^h3\s*\{([^}]*)\}", css, re.MULTILINE)
        self.assertIsNotNone(rule_match, "No h3 rule found")
        self.assertIn("margin-bottom: 10px", rule_match.group(1))

    def test_intro_without_tagline_has_matching_bottom_spacing(self):
        css_path = finders.find("theme-base.css")
        self.assertIsNotNone(
            css_path, "theme-base.css not found by staticfiles finders"
        )

        with open(css_path, encoding="utf-8") as css_file:
            css = css_file.read()

        rule_match = re.search(
            r"\.section--content--intro--without-tagline\s*\{([^}]*)\}", css
        )
        self.assertIsNotNone(rule_match, "No empty-tagline intro rule found")
        self.assertIn("margin-bottom: 25px", rule_match.group(1))


class BasicInformationSpacingTests(TestCase):
    def setUp(self):
        BloomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")
        self.nofo = Nofo.objects.create(
            title="Test NOFO",
            number="TEST-001",
            opdiv="Test OpDiv",
            agency="Test Agency",
            group="bloom",
        )
        section = Section.objects.create(
            nofo=self.nofo,
            name="Step 1 Review the Opportunity",
            order=1,
        )
        Subsection.objects.create(
            section=section,
            name="Basic information",
            tag="h3",
            order=1,
        )
        Subsection.objects.create(
            section=section,
            name="Important Resources",
            tag="h3",
            body="Resource details",
            order=2,
        )
        self.url = reverse("nofos:nofo_view", kwargs={"pk": self.nofo.pk})

    def test_empty_tagline_adds_intro_spacing_class(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'class="section--content--intro section--content--intro--without-tagline"',
        )

    def test_present_tagline_keeps_existing_intro_layout(self):
        self.nofo.tagline = "A useful tagline"
        self.nofo.save(update_fields=["tagline"])

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="section--content--intro"')
        self.assertNotContains(response, "section--content--intro--without-tagline")
        self.assertContains(response, 'class="nofo--tagline"')
