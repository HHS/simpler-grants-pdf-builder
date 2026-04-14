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
            title="Test NOFO",
            short_name="test",
            group="bloom",
            opdiv="ACF",
        )

        self.section = Section.objects.create(
            nofo=self.nofo,
            name="Section",
            order=1,
        )

        self.sub_with_tag = Subsection.objects.create(
            section=self.section,
            name="Subsection 1",
            order=1,
            tag="h2",
        )
        # subsection 2 does not have a name or a tag
        self.sub_no_tag = Subsection.objects.create(
            section=self.section,
            order=2,
            body="Hello, I am subsection 2",
        )

        self.url = reverse(
            "nofos:subsection_create",
            kwargs={
                "pk": self.nofo.id,
                "section_pk": self.section.id,
            },
        )

    def test_missing_insert_order_returns_400(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "No insert order provided.", status_code=400)

    def test_non_integer_insert_order_returns_400(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(f"{self.url}?insert_order=abc")

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Invalid insert order.", status_code=400)

    def test_zero_insert_order_returns_400(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(f"{self.url}?insert_order=0")

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Insert order must be 1 or greater.",
            status_code=400,
        )

    def test_negative_insert_order_returns_400(self):
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(f"{self.url}?insert_order=-5")

        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Insert order must be 1 or greater.",
            status_code=400,
        )

    def test_valid_get_request_renders_template(self):
        response = self.client.get(
            f"{self.url}?insert_order=2&prev_subsection_id={self.sub_with_tag.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "nofos/subsection_create.html")

    def test_finds_previous_subsection(self):
        response = self.client.get(
            f"{self.url}?insert_order=2&prev_subsection_id={self.sub_with_tag.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Previous subsection with a heading")
        self.assertContains(response, "Subsection 1")

    def test_finds_previous_subsection_with_tag(self):
        response = self.client.get(
            f"{self.url}?insert_order=3&prev_subsection_id={self.sub_no_tag.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Previous subsection with a heading")
        self.assertContains(response, "Subsection 1")

    def test_successfully_creates_subsection(self):
        response = self.client.post(
            f"{self.url}?insert_order=2&prev_subsection_id={self.sub_with_tag.id}",
            {
                "name": "New Subsection",
                "tag": "h3",
                "body": "Test content",
                "html_class": "",
                "insert_order": "2",
                "prev_subsection_id": str(self.sub_with_tag.id),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Created new subsection:")
        self.assertEqual(Subsection.objects.filter(section=self.section).count(), 3)

        new_subsection = Subsection.objects.get(name="New Subsection")
        self.assertEqual(new_subsection.order, 2)

    def test_successfully_creates_first_subsection_at_order_1(self):
        # Clear existing subsections so we can test the first position cleanly
        self.section.subsections.all().delete()

        response = self.client.post(
            f"{self.url}?insert_order=1",
            {
                "name": "First Subsection",
                "tag": "h3",
                "body": "First content",
                "html_class": "",
                "insert_order": "1",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        new_subsection = Subsection.objects.get(name="First Subsection")
        self.assertEqual(new_subsection.order, 1)

    def test_successfully_creates_subsection_at_large_order(self):
        response = self.client.post(
            f"{self.url}?insert_order=1000",
            {
                "name": "Late Subsection",
                "tag": "h3",
                "body": "Late content",
                "html_class": "",
                "insert_order": "1000",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        new_subsection = Subsection.objects.get(name="Late Subsection")
        self.assertEqual(new_subsection.order, 1000)

    def test_inserting_at_existing_order_pushes_existing_subsections_forward(self):
        response = self.client.post(
            f"{self.url}?insert_order=2",
            {
                "name": "Inserted Subsection",
                "tag": "h3",
                "body": "Inserted content",
                "html_class": "",
                "insert_order": "2",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        inserted = Subsection.objects.get(name="Inserted Subsection")
        original_second = Subsection.objects.get(pk=self.sub_no_tag.pk)

        self.assertEqual(inserted.order, 2)
        self.assertGreater(original_second.order, 2)

    def test_sparse_orders_are_supported(self):
        self.section.subsections.all().delete()

        first = Subsection.objects.create(
            section=self.section,
            name="First",
            order=1,
            tag="h2",
        )
        second = Subsection.objects.create(
            section=self.section,
            name="Second",
            order=100,
            tag="h3",
        )

        response = self.client.post(
            f"{self.url}?insert_order=50&prev_subsection_id={first.id}",
            {
                "name": "Middle",
                "tag": "h4",
                "body": "Middle content",
                "html_class": "",
                "insert_order": "50",
                "prev_subsection_id": str(first.id),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        middle = Subsection.objects.get(name="Middle")
        second.refresh_from_db()

        self.assertEqual(middle.order, 50)
        # All future subsection orders are bumped by 1
        self.assertEqual(second.order, 101)
