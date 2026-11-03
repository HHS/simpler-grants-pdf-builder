from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from nofos.models import Nofo

User = get_user_model()


class NofoIndexViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="index-test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="index-test@example.com", password="testpass123")

    def test_import_action_appears_at_top_and_bottom_of_page(self):
        response = self.client.get(reverse("nofos:nofo_index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'href="{reverse("nofos:nofo_import")}"',
            count=2,
        )
        self.assertContains(response, "Import NOFO", count=2)

    def test_bloom_group_filter_preserves_status_and_excludes_archived(self):
        bloom = Nofo.objects.create(
            title="Example NOFO", opdiv="hrsa", group="bloom", status="published"
        )
        hrsa = Nofo.objects.create(
            title="Example NOFO", opdiv="hrsa", group="hrsa", status="published"
        )
        Nofo.objects.create(
            title="Example NOFO", opdiv="hrsa", group="hrsa", status="paused"
        )
        Nofo.objects.create(
            title="Example NOFO",
            opdiv="hrsa",
            group="hrsa",
            status="published",
            archived=timezone.localdate(),
        )

        for group, expected in [
            ("hrsa", {hrsa}),
            ("all", {bloom, hrsa}),
            ("unknown", {bloom}),
            (None, {bloom}),
        ]:
            with self.subTest(group=group):
                params = {"status": "published"}
                if group is not None:
                    params["group"] = group
                response = self.client.get(reverse("nofos:nofo_index"), params)
                self.assertEqual(set(response.context["nofo_list"]), expected)
                for value, _ in [*settings.GROUP_CHOICES, ("all", "All")]:
                    self.assertContains(response, f"status=published&amp;group={value}")

    def test_non_bloom_user_cannot_use_group_filter(self):
        self.user.group = "hrsa"
        self.user.save(update_fields=["group"])
        hrsa = Nofo.objects.create(
            title="Example NOFO", opdiv="hrsa", group="hrsa", status="published"
        )
        Nofo.objects.create(
            title="Example NOFO", opdiv="hrsa", group="bloom", status="published"
        )

        response = self.client.get(
            reverse("nofos:nofo_index"), {"status": "published", "group": "all"}
        )

        self.assertEqual(list(response.context["nofo_list"]), [hrsa])
        self.assertNotContains(response, 'id="group-filter"')

    @override_settings(IS_PROD=True)
    def test_production_excludes_staging_from_group_choices(self):
        response = self.client.get(reverse("nofos:nofo_index"), {"group": "staging"})

        self.assertEqual(response.context["nofo_group"], "bloom")
        self.assertNotContains(response, "Staging environment")
        self.assertContains(response, "&amp;group=all")
