from django.template.loader import render_to_string
from django.test import SimpleTestCase


class CalloutBoxContactIconTests(SimpleTestCase):
    def render_callout(self, body, *, name="", icon_style="", break_colons=None):
        return render_to_string(
            "includes/callout_box.html",
            {
                "subsection": {
                    "body": body,
                    "name": name,
                    "tag": "h4",
                    "html_id": "help",
                    "html_class": "",
                },
                "nofo": {"icon_style": icon_style},
                **({"break_colons": break_colons} if break_colons is not None else {}),
            },
        )

    def assert_contact_icon(self, html, *, thin=False):
        self.assertIn("callout-box--questions", html)
        contact_icon = 'stroke-width=".5"' if thin else 'stroke-width="2"'
        self.assertIn(contact_icon, html)
        self.assertLess(html.index("<svg"), html.index("<p>"))

    def test_inline_help_directing_to_contacts_and_support_gets_icon(self):
        examples = (
            "Need help? See Contacts and Support.",
            "**Need help?** Visit [Contacts and Support](#contacts-and-support).",
            "Need any help? Please refer to the Contact and Support section.",
        )
        for body in examples:
            with self.subTest(body=body):
                self.assert_contact_icon(self.render_callout(body))

        html = self.render_callout(examples[1], icon_style="thin", break_colons=False)
        self.assert_contact_icon(html, thin=True)
        self.assertIn('href="#contacts-and-support"', html)

    def test_similar_wording_does_not_get_icon(self):
        examples = (
            ("Need help? Visit Grants.gov.", ""),
            ("Need help? Email the Contacts and Support team.", ""),
            ("See Contacts and Support.", "Need help?"),
            ("Send us an email.", "Questions?"),
            ("See [our guide](#contacts-and-support) if you need help.", ""),
        )
        for body, name in examples:
            with self.subTest(body=body, name=name):
                html = self.render_callout(body, name=name)
                self.assertNotIn("callout-box--questions", html)
                self.assertNotIn("<svg", html)

    def test_existing_questions_and_adobe_icons(self):
        self.assert_contact_icon(self.render_callout("Have questions? Contact us."))
        html = self.render_callout("Download Adobe Reader.")
        self.assertIn("callout-box--keyboard", html)
        self.assertIn("<svg", html)

    def test_new_rule_applies_to_inline_callouts(self):
        html = self.render_callout(
            "Need help? See Contacts and Support.", break_colons=True
        )
        self.assertNotIn("<svg", html)
