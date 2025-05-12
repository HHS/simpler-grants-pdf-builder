from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from nofos.models import Nofo, Section, Subsection

User = get_user_model()


class NofoSubsectionCreateViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.nofo = Nofo.objects.create(
            title="Test NOFO", short_name="test", group="bloom", opdiv="ACF"
        )
        self.section = Section.objects.create(nofo=self.nofo, name="Section", order=1)

        self.sub_with_tag = Subsection.objects.create(
            section=self.section, name="Subsection 1", order=1, tag="h2"
        )
        # subsection 2 does not have a name or a tag
        self.sub_no_tag = Subsection.objects.create(
            section=self.section, order=2, body="Hello, I am subsection 2"
        )

    def test_missing_prev_subsection_returns_400(self):
        url = reverse(
            "nofos:subsection_create",
            kwargs={
                "pk": self.nofo.id,
                "section_pk": self.nofo.sections.first().id,
            },
        )

        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 400)

    def test_valid_get_request_renders_template(self):
        url = reverse(
            "nofos:subsection_create",
            kwargs={"pk": self.nofo.id, "section_pk": self.nofo.sections.first().id},
        )
        url += f"?prev_subsection={self.sub_with_tag.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "nofos/subsection_create.html")

    def test_finds_previous_subsection(self):
        url = reverse(
            "nofos:subsection_create",
            kwargs={"pk": self.nofo.id, "section_pk": self.nofo.sections.first().id},
        )
        url += f"?prev_subsection={self.sub_with_tag.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # includes "with a heading"
        self.assertNotContains(response, "Previous subsection with a heading")
        self.assertContains(response, "Subsection 1")  # Subsection 1 is previous

    def test_finds_previous_subsection_with_tag(self):
        url = reverse(
            "nofos:subsection_create",
            kwargs={"pk": self.nofo.id, "section_pk": self.nofo.sections.first().id},
        )
        url += f"?prev_subsection={self.sub_no_tag.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # includes "with a heading"
        self.assertContains(response, "Previous subsection with a heading")
        self.assertContains(response, "Subsection 1")  # Subsection 1 is previous

    def test_successfully_creates_subsection(self):
        url = reverse(
            "nofos:subsection_create",
            kwargs={"pk": self.nofo.id, "section_pk": self.nofo.sections.first().id},
        )
        url += f"?prev_subsection={self.sub_with_tag.id}"
        response = self.client.post(
            url,
            {
                "name": "New Subsection",
                "tag": "h3",
                "body": "Test content",
                "html_class": "",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Created new subsection:")
        self.assertEqual(Subsection.objects.filter(section=self.section).count(), 3)
