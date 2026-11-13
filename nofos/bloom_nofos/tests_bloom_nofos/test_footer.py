"""Shared application footer: HHS identifier and two rows of links (#1343)."""

import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

NEW_WINDOW = " (opens in a new window)"

ROW_1 = [
    (
        "About Office of Grants",
        "https://www.hhs.gov/about/agencies/asfr/grants/index.html",
    ),
    (
        "Latest updates",
        "https://github.com/HHS/simpler-grants-pdf-builder/blob/main/CHANGELOG.md",
    ),
]

ROW_2 = [
    ("About HHS", "https://www.hhs.gov/about/index.html"),
    ("Accessibility support", "https://www.grants.gov/accessibility-compliance"),
    ("FOIA requests", "https://www.hhs.gov/foia/index.html"),
    (
        "No FEAR Act data",
        "https://www.hhs.gov/about/agencies/asa/eeo/no-fear-act/index.html",
    ),
    ("Office of the Inspector General", "https://oig.hhs.gov/"),
    (
        "Performance reports",
        "https://www.hhs.gov/about/budget/budget-in-brief/index.html",
    ),
    ("Privacy policy", "https://www.hhs.gov/privacy/privacy-policy/index.html"),
]


def nav_links(html, label):
    """Return (text, href, target) for each link in the footer nav named label."""
    match = re.search(
        rf'<nav class="builder-footer__container" aria-label="{label}">(.*?)</nav>',
        html,
        re.S,
    )
    assert match, f"missing footer nav {label!r}"
    links = []
    for attrs, body in re.findall(r"<a\b([^>]*)>(.*?)</a>", match.group(1), re.S):
        href = re.search(r'href="([^"]*)"', attrs).group(1).replace("&amp;", "&")
        target = re.search(r'target="([^"]*)"', attrs)
        text = re.sub(r"<[^>]+>", "", body)
        links.append((" ".join(text.split()), href, target and target.group(1)))
    return links


class FooterTests(TestCase):
    def assertFooter(self, response, support_link):
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        footer = html[html.index('<footer class="usa-footer builder-footer">') :]

        # Identifier, then row 1, then row 2.
        self.assertLess(
            footer.index('aria-label="Agency identifier"'),
            footer.index("builder-footer__primary"),
        )
        self.assertLess(
            footer.index("builder-footer__primary"),
            footer.index("builder-footer__secondary"),
        )

        row_1 = nav_links(footer, "Footer navigation")
        expected_texts = [ROW_1[0][0] + NEW_WINDOW]
        if support_link:
            expected_texts.append("Submit a support ticket" + NEW_WINDOW)
        expected_texts += [ROW_1[1][0] + NEW_WINDOW, "Back to top"]
        self.assertEqual([text for text, _, _ in row_1], expected_texts)
        self.assertEqual(row_1[0][1], ROW_1[0][1])
        self.assertEqual(row_1[-2][1], ROW_1[1][1])
        self.assertEqual(row_1[-1][1:], ("#back-to-top", None))
        if support_link:
            self.assertTrue(row_1[1][1].startswith("https://forms.office.com/"))

        row_2 = nav_links(footer, "HHS policies and resources")
        self.assertEqual(
            row_2,
            [(text + NEW_WINDOW, href, "_blank") for text, href in ROW_2],
        )
        for _, _, target in row_1[:-1]:
            self.assertEqual(target, "_blank")

    def test_signed_out_builder_footer(self):
        self.assertFooter(self.client.get(reverse("users:login")), support_link=False)

    def test_signed_in_builder_footer_has_support_link(self):
        User.objects.create_user(
            email="footer-test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="footer-test@example.com", password="testpass123")
        self.assertFooter(
            self.client.get(reverse("nofos:nofo_index")), support_link=True
        )

    def test_readability_checker_footer_matches_without_support_link(self):
        self.assertFooter(
            self.client.get(reverse("pdf_readability")), support_link=False
        )
