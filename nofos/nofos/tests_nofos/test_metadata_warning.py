from bs4 import BeautifulSoup
from django.test import Client, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo


class NofoMetadataWarningTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="metadata-warning@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.nofo = Nofo.objects.create(
            title="Metadata warning test NOFO",
            short_name="metadata-warning-test",
            number="TEST-726",
            opdiv="TEST",
            group="bloom",
            status="draft",
        )
        self.edit_url = reverse("nofos:nofo_edit", kwargs={"pk": self.nofo.id})
        self.metadata_url = reverse(
            "nofos:nofo_edit_metadata", kwargs={"pk": self.nofo.id}
        )

    def _get_metadata_tab(self, response):
        soup = BeautifulSoup(response.content, "html.parser")
        return soup.find(id="tab-3")

    def _get_metadata_panel(self, response):
        soup = BeautifulSoup(response.content, "html.parser")
        return soup.find(id="tabpanel-3")

    def test_warning_lists_all_empty_metadata_fields(self):
        response = self.client.get(self.edit_url)

        tab = self._get_metadata_tab(response)
        panel = self._get_metadata_panel(response)
        self.assertIsNotNone(tab)
        self.assertEqual(tab.get("role"), "tab")
        self.assertEqual(tab.get("aria-controls"), "tabpanel-3")
        self.assertIn("Check PDF metadata (3)", tab.get_text(" ", strip=True))
        self.assertIsNotNone(panel)
        self.assertEqual(panel.get("role"), "tabpanel")
        self.assertEqual(panel.get("aria-labelledby"), "tab-3")
        self.assertEqual(
            [item.get_text(strip=True) for item in panel.select("li")],
            ["Author", "Subject", "Keywords"],
        )
        self.assertIn(
            "There are 3 missing metadata fields",
            panel.get_text(" ", strip=True),
        )
        self.assertEqual(
            panel.find("a").get("href"),
            self.metadata_url,
        )
        self.assertTrue(response.context["has_warnings"])

    def test_warning_only_lists_fields_that_are_missing(self):
        self.nofo.author = "HHS"
        self.nofo.keywords = "grants, funding"
        self.nofo.save()

        response = self.client.get(self.edit_url)

        tab = self._get_metadata_tab(response)
        panel = self._get_metadata_panel(response)
        self.assertIn("Check PDF metadata (1)", tab.get_text(" ", strip=True))
        self.assertEqual(
            [item.get_text(strip=True) for item in panel.select("li")],
            ["Subject"],
        )
        panel_text = panel.get_text(" ", strip=True)
        self.assertIn("There is 1 missing metadata field", panel_text)
        self.assertNotIn("There are 1 missing metadata fields", panel_text)

    def test_whitespace_only_metadata_is_treated_as_missing(self):
        self.nofo.author = "  "
        self.nofo.subject = "Accessible funding opportunity"
        self.nofo.keywords = "\n\t"
        self.nofo.save()

        response = self.client.get(self.edit_url)

        panel = self._get_metadata_panel(response)
        self.assertEqual(
            [item.get_text(strip=True) for item in panel.select("li")],
            ["Author", "Keywords"],
        )

    def test_warning_is_hidden_when_all_metadata_is_present(self):
        self.nofo.author = "HHS"
        self.nofo.subject = "Accessible funding opportunity"
        self.nofo.keywords = "grants, funding"
        self.nofo.save()

        response = self.client.get(self.edit_url)

        self.assertIsNone(self._get_metadata_tab(response))
        self.assertIsNone(self._get_metadata_panel(response))
        self.assertFalse(response.context["has_warnings"])

    def test_saving_complete_metadata_clears_the_warning(self):
        response = self.client.post(
            self.metadata_url,
            {
                "author": "HHS",
                "subject": "Accessible funding opportunity",
                "keywords": "grants, funding",
            },
            follow=True,
        )

        self.assertRedirects(response, self.edit_url)
        self.assertIsNone(self._get_metadata_tab(response))
        self.assertIsNone(self._get_metadata_panel(response))

    def test_metadata_edit_form_requires_all_fields(self):
        response = self.client.get(self.metadata_url)
        soup = BeautifulSoup(response.content, "html.parser")

        self.assertTrue(
            all(field.required for field in response.context["form"].fields.values())
        )
        self.assertEqual(
            [
                asterisk.get("aria-label")
                for asterisk in soup.select(".label--required")
            ],
            ["(required)", "(required)", "(required)"],
        )
        self.assertFalse(soup.select("[required]"))

    def test_incomplete_metadata_cannot_be_saved(self):
        response = self.client.post(
            self.metadata_url,
            {
                "author": "HHS",
                "subject": "",
                "keywords": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "subject", "This field is required."
        )
        self.assertFormError(
            response.context["form"], "keywords", "This field is required."
        )

        soup = BeautifulSoup(response.content, "html.parser")
        for field_name in ("subject", "keywords"):
            error = soup.find(id=f"{field_name}--error")
            field = soup.find(attrs={"name": field_name})
            self.assertEqual(
                error.get_text(" ", strip=True), "Error: This field is required."
            )
            self.assertIn("border-secondary-dark", field.get("class", []))
            self.assertIn(
                f"{field_name}--error", field.get("aria-describedby", "").split()
            )

        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.author, "")

    def test_whitespace_only_metadata_cannot_be_saved(self):
        response = self.client.post(
            self.metadata_url,
            {
                "author": "HHS",
                "subject": "   ",
                "keywords": "\n\t",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "subject", "This field is required."
        )
        self.assertFormError(
            response.context["form"], "keywords", "This field is required."
        )
        self.nofo.refresh_from_db()
        self.assertEqual(self.nofo.author, "")

    def test_warning_does_not_disable_pdf_actions(self):
        response = self.client.get(self.edit_url)
        soup = BeautifulSoup(response.content, "html.parser")
        buttons = {
            button.get_text(strip=True): button
            for button in soup.select(".usa-button-group--print-buttons button")
        }

        self.assertNotIn("disabled", buttons["Preview PDF"].attrs)
        self.assertNotIn("disabled", buttons["Download PDF"].attrs)
