from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from nofos.models import Nofo

User = get_user_model()


class NofoSearchViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cdc_user = User.objects.create_user(
            email="cdc-search@example.com",
            password="testpass123",
            group="cdc",
            force_password_reset=False,
        )
        cls.bloom_user = User.objects.create_user(
            email="bloom-search@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        cls.hrsa_user = User.objects.create_user(
            email="hrsa-search@example.com",
            password="testpass123",
            group="hrsa",
            force_password_reset=False,
        )
        cls.cdc_nofo = Nofo.objects.create(
            short_name="Shared search term - CDC",
            title="CDC search result",
            number="CDC-SEARCH-001",
            opdiv="CDC",
            group="cdc",
        )
        cls.hrsa_nofo = Nofo.objects.create(
            short_name="Shared search term - HRSA",
            title="HRSA search result",
            number="HRSA-SEARCH-001",
            opdiv="HRSA",
            group="hrsa",
        )
        cls.bloom_nofo = Nofo.objects.create(
            short_name="Shared search term - Bloom",
            title="Bloom search result",
            number="BLOOM-SEARCH-001",
            opdiv="CDC",
            group="bloom",
        )

    def search_as(self, user, query="shared search term"):
        self.client.force_login(user)
        return self.client.get(reverse("nofos:nofo_search"), {"query": query})

    def test_opdiv_users_can_search_their_own_group(self):
        for user, expected_nofo in (
            (self.cdc_user, self.cdc_nofo),
            (self.hrsa_user, self.hrsa_nofo),
        ):
            with self.subTest(group=user.group):
                response = self.search_as(user)

                self.assertEqual(response.status_code, 200)
                self.assertQuerySetEqual(response.context["nofo_list"], [expected_nofo])

    def test_opdiv_user_cannot_see_another_groups_matching_nofo(self):
        response = self.search_as(self.cdc_user)

        self.assertQuerySetEqual(response.context["nofo_list"], [self.cdc_nofo])
        self.assertNotContains(response, self.hrsa_nofo.short_name)
        self.assertNotContains(response, self.bloom_nofo.short_name)

    def test_bloom_user_can_search_across_groups(self):
        response = self.search_as(self.bloom_user)

        self.assertQuerySetEqual(
            response.context["nofo_list"],
            [self.bloom_nofo, self.hrsa_nofo, self.cdc_nofo],
            ordered=False,
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("nofos:nofo_search"))

        self.assertRedirects(
            response,
            f'{reverse("users:login")}?next={reverse("nofos:nofo_search")}',
        )
