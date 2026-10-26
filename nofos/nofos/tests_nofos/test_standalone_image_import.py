"""Standalone and paragraph image preservation through real import (#1051)."""

from unittest.mock import patch

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from martor.templatetags.martortags import safe_markdown

from nofos.models import Nofo
from nofos.nofo import decompose_empty_tags
from nofos.tests_nofos.test_import_characterization import html_upload


class EmptyTagImageTests(SimpleTestCase):
    def test_cleanup_retains_bare_images_and_existing_exceptions(self):
        soup = BeautifulSoup(
            '<body><h1>Figures</h1><img src="synthetic.png" alt="Logo">'
            '<p><img src="wrapped.png" alt=""></p><br><hr><p> </p><div> </div><ul><li> </li></ul></body>',
            "html.parser",
        )
        decompose_empty_tags(soup)
        self.assertEqual(len(soup.find_all("img")), 2)
        self.assertIsNotNone(soup.br)
        self.assertIsNotNone(soup.hr)
        self.assertIsNone(soup.div)
        self.assertIsNone(soup.li)
        self.assertEqual(len(soup.find_all("p")), 1)


@override_settings(DEBUG=False)
class StandaloneImagePersistenceTests(TestCase):
    def test_alt_states_survive_bare_and_paragraph_wrapped_imports(self):
        user = get_user_model().objects.create_user(
            email="image-import@example.com",
            password="local-test",
            group="bloom",
            force_password_reset=False,
        )
        self.client.force_login(user)
        for wrapped in (False, True):
            for alt in ("Agency logo", "", None):
                with self.subTest(wrapped=wrapped, alt=alt):
                    alt_attribute = f' alt="{alt}"' if alt is not None else ""
                    image = f'<img src="https://example.invalid/synthetic.png"{alt_attribute}>'
                    if wrapped:
                        image = f"<p>{image}</p>"
                    html = (
                        "<p>Opdiv: CDC</p><p>Opportunity number: SYNTHETIC-1051</p>"
                        "<p>Opportunity Name: Synthetic image validation</p>"
                        "<h1>Opportunity</h1><h2>Figures</h2><p>Body before.</p>"
                        + image
                        + "<p>Body after.</p>"
                    )
                    # Import should never need to retrieve the referenced image.
                    with patch(
                        "requests.get",
                        side_effect=AssertionError("Image download attempted"),
                    ):
                        response = self.client.post(
                            reverse("nofos:nofo_import"),
                            {"nofo-import": html_upload(html)},
                        )
                    self.assertEqual(response.status_code, 302)
                    nofo = Nofo.objects.latest("created")
                    subsection = nofo.sections.get().subsections.get(name="Figures")
                    rendered = BeautifulSoup(
                        safe_markdown(subsection.body), "html.parser"
                    )
                    images = rendered.find_all("img")
                    self.assertEqual(len(images), 1)
                    self.assertEqual(
                        images[0]["src"], "https://example.invalid/synthetic.png"
                    )
                    self.assertEqual(images[0]["alt"], alt or "")
                    self.assertNotIn("data-nofo-missing-alt-text", subsection.body)
                    self.assertEqual("<img " in subsection.body, alt is None)
                    self.assertIn("Body before.", rendered.get_text())
                    self.assertIn("Body after.", rendered.get_text())
                    self.assertContains(
                        self.client.get(reverse("nofos:nofo_edit", args=[nofo.id])),
                        "synthetic.png",
                    )
