from unittest.mock import patch

from bs4 import BeautifulSoup
from django.contrib.messages.storage.fallback import FallbackStorage
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.forms import NofoCoverImageForm, NofoThemeOptionsForm
from nofos.models import Nofo
from nofos.nofo import DEFAULT_NOFO_OPPORTUNITY_NUMBER
from nofos.views import NofosImportNewView, NofosImportOverwriteView, duplicate_nofo


class HrsaBeforeYouBeginTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="hrsa-review@example.com",
            password=None,
            group="bloom",
            force_password_reset=False,
        )
        self.client.force_login(self.user)
        self.request = RequestFactory().post("/")
        self.request.user = self.user
        self.request.session = {}
        self.request._messages = FallbackStorage(self.request)
        self.sections = [
            {
                "name": "Step 1: Review the Opportunity",
                "order": 1,
                "has_section_page": True,
                "subsections": [
                    {
                        "name": "Basic information",
                        "tag": "h3",
                        "order": 1,
                        "html_id": "basic-information",
                        "body": ["<p>Representative program information.</p>"],
                    }
                ],
            }
        ]

    def soup(self, number="HRSA-27-001", opdiv="HRSA"):
        return BeautifulSoup(
            f"<p>Opportunity Number: {number}</p><p>Opdiv: {opdiv}</p>"
            "<p>Opportunity Name: HRSA test opportunity</p>"
            "<p>Application Deadline: May 6, 2027</p>",
            "html.parser",
        )

    def new_import(self, number="HRSA-27-001", opdiv="HRSA"):
        response = NofosImportNewView().handle_nofo_create(
            self.request, self.soup(number, opdiv), self.sections, "hrsa.html"
        )
        self.assertEqual(response.status_code, 302)
        return Nofo.objects.latest("created")

    def test_new_import_uses_document_metadata_not_uploaders_group(self):
        for number, opdiv in [
            ("HRSA-27-001", "HHS"),
            ("HHS-27-001", "Health Resources and Services Administration"),
        ]:
            with self.subTest(number=number):
                nofo = self.new_import(number, opdiv)
                self.assertEqual(nofo.before_you_begin, "hrsa")
                self.assertEqual(nofo.cover, "nofo--cover-page--text")
                form = NofoThemeOptionsForm(instance=nofo, user=self.user)
                self.assertEqual(
                    [v for v, _ in form.fields["cover"].choices],
                    ["nofo--cover-page--text"],
                )

    def test_non_hrsa_import_keeps_existing_defaults_and_cover_choices(self):
        # CDC also defaults to the text-only cover (IMPORT-043), but unlike HRSA
        # it keeps every cover choice selectable.
        nofo = self.new_import("CDC-27-001", "CDC")
        self.assertEqual(nofo.before_you_begin, "full")
        self.assertEqual(nofo.cover, "nofo--cover-page--text")
        form = NofoThemeOptionsForm(instance=nofo, user=self.user)
        self.assertEqual(list(form.fields["cover"].choices), Nofo.COVER_CHOICES)

    def test_non_hrsa_import_without_text_cover_rule_keeps_medium_cover(self):
        # An OpDiv with no text-only rule still starts on the image cover.
        nofo = self.new_import("CMS-27-001", "CMS")
        self.assertEqual(nofo.cover, "nofo--cover-page--medium")
        form = NofoThemeOptionsForm(instance=nofo, user=self.user)
        self.assertEqual(list(form.fields["cover"].choices), Nofo.COVER_CHOICES)

    def test_reimport_preserves_legacy_settings_even_with_placeholder_number(self):
        for variant, number, cover, image in [
            ("full", "HRSA-27-001", "medium", "img/cover-img/hrsa-25-066.jpg"),
            ("none", DEFAULT_NOFO_OPPORTUNITY_NUMBER, "hero", ""),
            ("sole_source", "", "text", ""),
            ("hrsa", "HRSA-27-001", "text", "img/cover-img/hrsa-25-066.jpg"),
        ]:
            with self.subTest(variant=variant):
                nofo = Nofo.objects.create(
                    title="Existing HRSA",
                    opdiv="HRSA",
                    group="bloom",
                    number=number,
                    theme="portrait-hrsa-white",
                    before_you_begin=variant,
                    cover=f"nofo--cover-page--{cover}",
                    cover_image=image,
                )
                with patch(
                    "nofos.nofo.suggest_nofo_cover_image", return_value="new-image.jpg"
                ):
                    response = NofosImportOverwriteView.reimport_nofo(
                        self.request,
                        nofo,
                        self.soup(),
                        self.sections,
                        "reimport.html",
                        False,
                    )
                self.assertEqual(response.status_code, 302)
                nofo.refresh_from_db()
                self.assertEqual(nofo.before_you_begin, variant)
                self.assertEqual(nofo.cover, f"nofo--cover-page--{cover}")
                self.assertEqual(nofo.cover_image, image)

    def test_hrsa_cover_validation_preserves_only_current_legacy_selection(self):
        for cover in ["text", "hero", "medium"]:
            nofo = Nofo.objects.create(
                title="Existing HRSA",
                opdiv="HRSA",
                group="bloom",
                theme="portrait-hrsa-white",
                cover=f"nofo--cover-page--{cover}",
            )
            for submitted in ["text", "hero", "medium"]:
                with self.subTest(cover=cover, submitted=submitted):
                    nofo.refresh_from_db()
                    form = NofoThemeOptionsForm(
                        {
                            "theme": nofo.theme,
                            "cover": f"nofo--cover-page--{submitted}",
                            "icon_style": "nofo--icons--solid",
                        },
                        instance=nofo,
                        user=self.user,
                    )
                    self.assertEqual(
                        form.is_valid(), submitted in ["text", cover], form.errors
                    )

    def test_get_never_writes_and_post_can_preserve_legacy_cover(self):
        nofo = Nofo.objects.create(
            title="Existing HRSA",
            opdiv="HRSA",
            group="bloom",
            theme="portrait-hrsa-blue",
            cover="nofo--cover-page--hero",
            before_you_begin="full",
        )
        original = Nofo.objects.values().get(pk=nofo.pk)
        url = reverse("nofos:nofo_edit_theme_options", kwargs={"pk": nofo.pk})
        for path in [url, reverse("nofos:nofo_view", kwargs={"pk": nofo.pk})]:
            self.assertEqual(self.client.get(path).status_code, 200)
            self.assertEqual(Nofo.objects.values().get(pk=nofo.pk), original)
        response = self.client.post(
            url,
            {
                "theme": nofo.theme,
                "cover": nofo.cover,
                "icon_style": "nofo--icons--solid",
            },
        )
        self.assertEqual(response.status_code, 302)
        nofo.refresh_from_db()
        self.assertEqual(nofo.cover, "nofo--cover-page--hero")
        self.assertEqual(nofo.before_you_begin, "full")
        self.assertEqual(nofo.icon_style, "nofo--icons--solid")

    def test_hrsa_template_has_peer_headings_before_final_callout_and_toc_link(self):
        nofo = self.new_import()
        response = self.client.get(reverse("nofos:nofo_view", kwargs={"pk": nofo.pk}))
        soup = BeautifulSoup(response.content, "html.parser")
        page = soup.select_one(".before-you-begin--hrsa")
        self.assertEqual(page.h2.get_text(), "Before you begin")
        self.assertEqual(
            [heading.get_text() for heading in page.find_all("h3")],
            [
                "SAM.gov registration (this can take several weeks)",
                "Grants.gov registration (this can take several days)",
                "Apply by the application due date",
                "Application and funding requirements",
            ],
        )
        heading = page.select_one(".before-you-begin--requirements")
        self.assertEqual(heading.get_text(), "Application and funding requirements")
        paragraph_tag = heading.find_next_sibling("p")
        self.assertEqual(
            paragraph_tag.find_next_sibling(), page.select_one(".callout-box")
        )
        self.assertIsNone(page.select_one(".callout-box").find_next_sibling())
        paragraph = paragraph_tag.get_text()
        self.assertTrue(
            paragraph.startswith("All activities proposed in your application")
        )
        self.assertTrue(paragraph.endswith("applicable court orders."))
        self.assertIn(
            "Grants.gov registration (this can take several days)", page.get_text()
        )
        self.assertIsNotNone(
            soup.select_one('.toc a[href="#section--before-you-begin"]')
        )

    def test_legacy_variants_do_not_receive_hrsa_paragraph(self):
        for variant in ["full", "era", "sole_source", "none"]:
            with self.subTest(variant=variant):
                html = render_to_string(
                    "includes/byb_page.html",
                    {
                        "nofo": Nofo(
                            theme="portrait-hrsa-white", before_you_begin=variant
                        )
                    },
                )
                self.assertNotIn("Application and funding requirements", html)
                self.assertNotIn("before-you-begin--hrsa", html)
                self.assertNotIn("<h3", html)

    def test_cover_image_can_still_be_saved_for_text_only_hrsa_record(self):
        nofo = self.new_import()
        form = NofoCoverImageForm(
            {
                "cover_image": "img/cover-img/hrsa-25-066.jpg",
                "cover_image_alt_text": "A cover photo",
            },
            instance=nofo,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        nofo.refresh_from_db()
        self.assertEqual(nofo.cover_image, "img/cover-img/hrsa-25-066.jpg")
        self.assertEqual(nofo.cover, "nofo--cover-page--text")


class BeforeYouBeginOnDuplicateTests(TestCase):
    """
    Duplicating a NOFO copies its "Before you begin" variant as-is. Nothing is
    re-suggested, so a copy of a record that predates the HRSA variant still
    says "full".

    These pin the current behaviour rather than change it. The behaviour was
    incidental - `duplicate_nofo()` clones the row and never calls the suggest
    functions - so nothing stopped a later change to those functions from
    quietly altering what a copy looks like. Whether an HRSA duplicate *should*
    move to the HRSA page is an open product question (see IMPORT-044); if it
    is answered yes, these are the tests to change, deliberately.
    """

    def make_nofo(self, **overrides):
        fields = {
            "title": "HRSA Legacy NOFO",
            "number": "HRSA-26-014",
            "opdiv": "HRSA",
            "group": "hrsa",
            "theme": "portrait-hrsa-blue",
            # What every pre-#911 record has: the variant that was the default
            # for everyone except NIH.
            "before_you_begin": "full",
        }
        fields.update(overrides)
        return Nofo.objects.create(**fields)

    def test_duplicating_a_legacy_hrsa_nofo_keeps_the_legacy_page(self):
        nofo = self.make_nofo()

        copy = duplicate_nofo(nofo)

        self.assertEqual(copy.before_you_begin, "full")
        self.assertEqual(Nofo.objects.get(pk=copy.pk).before_you_begin, "full")

    def test_duplicating_a_post_911_hrsa_nofo_keeps_the_hrsa_page(self):
        """The copy carries the variant forward, whichever one that is."""
        nofo = self.make_nofo(before_you_begin="hrsa")

        copy = duplicate_nofo(nofo)

        self.assertEqual(copy.before_you_begin, "hrsa")

    def test_every_variant_is_copied_as_is(self):
        for variant in ["full", "hrsa", "era", "sole_source", "none"]:
            with self.subTest(variant=variant):
                nofo = self.make_nofo(
                    number=f"HRSA-26-{variant}", before_you_begin=variant
                )

                copy = duplicate_nofo(nofo)

                self.assertEqual(copy.before_you_begin, variant)

    def test_the_original_record_is_left_alone(self):
        nofo = self.make_nofo()

        duplicate_nofo(nofo)
        nofo.refresh_from_db()

        self.assertEqual(nofo.before_you_begin, "full")

    def test_a_reimports_archive_snapshot_keeps_the_saved_variant(self):
        """
        The is_successor copy records the NOFO as it was before a re-import, so
        it must never be re-suggested - that would put a page in the archive
        that never existed.
        """
        nofo = self.make_nofo()

        snapshot = duplicate_nofo(nofo, is_successor=True)

        self.assertEqual(snapshot.before_you_begin, "full")

    def test_cover_settings_are_copied_as_is_too(self):
        """#911 also narrowed HRSA cover choices; duplication re-suggests none of it."""
        nofo = self.make_nofo(
            cover="nofo--cover-page--medium", cover_image="img/cover-img/legacy.png"
        )

        copy = duplicate_nofo(nofo)

        self.assertEqual(copy.cover, "nofo--cover-page--medium")
        self.assertEqual(copy.cover_image, "img/cover-img/legacy.png")
