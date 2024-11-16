from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser as User
from nofos.models import Nofo, Section, Subsection
from django.test.utils import override_settings
from unittest.mock import patch


import unittest
import logging


class NofoExportJsonViewTest(TestCase):

    def setUp(self):
        # disable logging otherwise test_regular_user_cannot_export_nofo emits a PermissionDenied stack trace
        logging.disable(logging.CRITICAL)

        # Create a superuser
        self.superuser = User.objects.create_superuser(
            email="admin@groundhog-day.com", password="superpassword", group="bloom"
        )

        # Create a regular user
        self.regular_user = User.objects.create_user(
            email="regular@groundhog-day.com", password="password", group="bloom"
        )

        # Create test NOFO object
        self.nofo = Nofo.objects.create(
            title="JSON Export NOFO",
            number="00000",
            tagline="Export me as data!",
            theme="landscape-cdc-blue",
        )

        # Create related Sections and Subsections
        self.section = Section.objects.create(
            nofo=self.nofo, name="JSON Export NOFO: Section 1", order=1
        )
        self.subsection = Subsection.objects.create(
            section=self.section,
            name="JSON Export NOFO: Subsection 1",
            order=1,
            tag="h3",
        )

    def tearDown(self):
        # enable logging again
        logging.disable(logging.NOTSET)

    def test_superuser_can_export_nofo(self):
        # Log in as superuser
        self.client.login(email="admin@groundhog-day.com", password="superpassword")

        # Make request to export NOFO
        response = self.client.get(
            reverse("nofos:export_nofo_json", args=[self.nofo.id])
        )

        # Assert success response and JSON structure
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        data = response.json()
        self.assertEqual(data["id"], self.nofo.id)
        self.assertEqual(data["title"], self.nofo.title)
        self.assertEqual(data["sections"][0]["name"], self.section.name)
        self.assertEqual(
            data["sections"][0]["subsections"][0]["name"], self.subsection.name
        )

    def test_regular_user_cannot_export_nofo(self):
        # Log in as regular user
        self.client.login(username="regular@groundhog-day.com", password="password")

        # Make request to export NOFO
        response = self.client.get(
            reverse("nofos:export_nofo_json", args=[self.nofo.id])
        )

        # Assert forbidden response
        self.assertEqual(response.status_code, 403)

    def test_export_nonexistent_nofo(self):
        # Log in as superuser
        self.client.login(email="admin@groundhog-day.com", password="superpassword")

        # Make request to export a NOFO that doesn't exist
        response = self.client.get(reverse("nofos:export_nofo_json", args=[9999]))

        # Assert 404 response
        self.assertEqual(response.status_code, 404)
