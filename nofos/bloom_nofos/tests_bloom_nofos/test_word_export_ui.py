from constance.test import override_config
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase, override_settings


@override_settings(
    ALLOWED_HOSTS=[
        "nofos.simpler.grants.gov",
        "nofos.dev.simpler.grants.gov",
    ],
    GRABZIT_APPLICATION_KEY="synthetic-key",
    GRABZIT_APPLICATION_SECRET="synthetic-secret",
    GRABZIT_WORD_EXPORT_ALLOWED_HOSTS=("nofos.simpler.grants.gov",),
)
@override_config(PANDOC_WORD_EXPORT_ENABLED=False)
class WordExportAvailabilityUITests(TestCase):
    def render_button(self, host):
        request = RequestFactory().get("/export", HTTP_HOST=host)
        return render_to_string(
            "includes/docx_download_button_form.html",
            {"action_url": "/export", "primary": True},
            request=request,
        )

    def test_allowed_host_renders_export_form(self):
        html = self.render_button("nofos.simpler.grants.gov")

        self.assertIn('class="docx-download-form"', html)
        self.assertIn("data-open-modal", html)
        self.assertNotIn("Word export is not available", html)

    def test_unconfigured_host_renders_disabled_explanation(self):
        html = self.render_button("nofos.dev.simpler.grants.gov")

        self.assertNotIn('class="docx-download-form"', html)
        self.assertIn("disabled", html)
        self.assertIn("Word export is not available in this environment.", html)

    @override_config(PANDOC_WORD_EXPORT_ENABLED=True)
    @override_settings(GRABZIT_APPLICATION_KEY="", GRABZIT_APPLICATION_SECRET="")
    def test_local_export_renders_form_without_vendor_configuration(self):
        html = self.render_button("nofos.dev.simpler.grants.gov")

        self.assertIn('class="docx-download-form"', html)
        self.assertIn("data-open-modal", html)
        self.assertNotIn("Word export is not available", html)
