import csv
import io
import json
import uuid
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from nofos.models import Nofo, Section, Subsection

from .models import CompareDocument, CompareSection, CompareSubsection
from .views import duplicate_compare_doc

User = get_user_model()


class DuplicateCompareTests(TestCase):
    def _make_nofo_with_content(
        self,
        *,
        title="NOFO title",
        short_name="NOFO short name",
        filename="file.docx",
        opdiv="HRSA",
        group="bloom",
        sections=2,
        subs_per_section=3,
    ) -> Nofo:
        nofo = Nofo.objects.create(
            title=title,
            short_name=short_name,
            filename=filename,
            opdiv=opdiv,
            group=group,
        )
        # sections
        for s in range(1, sections + 1):
            sec = Section.objects.create(
                nofo=nofo, name=f"Section {s}", html_id=f"{s}-sec", order=s
            )
            # subsections
            for i in range(1, subs_per_section + 1):
                Subsection.objects.create(
                    section=sec,
                    name=f"Sub {s}.{i}",
                    html_id=f"{s}-{i}",
                    order=i,
                    tag="h3",
                    callout_box=False,
                    body=f"Body {s}.{i}",
                )
        return nofo

    def _make_compare_doc_with_content(
        self,
        *,
        title="Compare Doc title",
        filename="compare.docx",
        opdiv="CDC",
        group="bloom",
        sections=2,
        subs_per_section=2,
    ) -> CompareDocument:
        document = CompareDocument.objects.create(
            title=title,
            filename=filename,
            opdiv=opdiv,
            group=group,
        )
        for s in range(1, sections + 1):
            sec = CompareSection.objects.create(
                document=document, name=f"GSection {s}", html_id=f"g{s}-sec", order=s
            )
            for i in range(1, subs_per_section + 1):
                CompareSubsection.objects.create(
                    section=sec,
                    name=f"GSub {s}.{i}",
                    html_id=f"g{s}-{i}",
                    order=i,
                    tag="h3",
                    callout_box=bool(i % 2),
                    body=f"GBody {s}.{i}",
                    comparison_type="diff_strings" if i == 1 else "name",
                    diff_strings=["must include", f"token-{s}-{i}"] if i == 1 else [],
                )
        return document

    def test_duplicate_from_compare_doc_copies_all_fields(self):
        source = self._make_compare_doc_with_content(
            title="Compare Doc title",
            filename="sg.docx",
            opdiv="ACF",
            sections=2,
            subs_per_section=2,
        )

        new = duplicate_compare_doc(source)

        # Top-level expectations
        self.assertIsInstance(new, CompareDocument)
        self.assertEqual(new.status, "draft")
        self.assertIsNone(new.archived)
        self.assertIsNone(new.successor)
        self.assertEqual(new.opdiv, "ACF")  # preserved from source
        self.assertEqual(new.title, "Compare Doc title")

        # Section count & order
        self.assertEqual(new.sections.count(), source.sections.count())
        new_secs = list(new.sections.order_by("order"))
        src_secs = list(source.sections.order_by("order"))
        for i, (ns, ss) in enumerate(zip(new_secs, src_secs), start=1):
            self.assertEqual(ns.order, ss.order)
            self.assertEqual(ns.name, ss.name)
            self.assertEqual(ns.html_id, ss.html_id)

            # Subsection parity & order
            new_subs = list(ns.subsections.order_by("order"))
            src_subs = list(ss.subsections.order_by("order"))
            self.assertEqual(len(new_subs), len(src_subs))
            for nsub, ssub in zip(new_subs, src_subs):
                # common fields
                self.assertEqual(nsub.name, ssub.name)
                self.assertEqual(nsub.html_id, ssub.html_id)
                self.assertEqual(nsub.html_class, ssub.html_class)
                self.assertEqual(nsub.order, ssub.order)
                self.assertEqual(nsub.tag, ssub.tag)
                self.assertEqual(nsub.callout_box, ssub.callout_box)
                self.assertEqual(nsub.body, ssub.body)
                # compare-specific fields should COPY
                self.assertEqual(nsub.comparison_type, ssub.comparison_type)
                self.assertEqual(nsub.diff_strings, ssub.diff_strings)

    def test_duplicate_from_nofo_sets_defaults_for_compare_only_fields(self):
        source = self._make_nofo_with_content(
            title="NOFO title",
            short_name="NOFO short name",
            filename="nofile.docx",
            opdiv="NIH",
            sections=2,
            subs_per_section=3,
        )

        new = duplicate_compare_doc(source)

        # Top-level expectations
        self.assertIsInstance(new, CompareDocument)
        self.assertEqual(new.status, "draft")
        self.assertIsNone(new.archived)
        self.assertIsNone(new.successor)
        self.assertEqual(new.opdiv, "NIH")
        self.assertEqual(new.title, "(Compare) NOFO short name")  # use short name

        # Section parity
        self.assertEqual(new.sections.count(), source.sections.count())

        new_secs = list(new.sections.order_by("order"))
        src_secs = list(source.sections.order_by("order"))
        for ns, ss in zip(new_secs, src_secs):
            self.assertEqual(ns.order, ss.order)
            self.assertEqual(ns.name, ss.name)
            self.assertEqual(ns.html_id, ss.html_id)

            new_subs = list(ns.subsections.order_by("order"))
            src_subs = list(ss.subsections.order_by("order"))
            self.assertEqual(len(new_subs), len(src_subs))

            for nsub, ssub in zip(new_subs, src_subs):
                # common fields copied
                self.assertEqual(nsub.name, ssub.name)
                self.assertEqual(nsub.html_id, ssub.html_id)
                self.assertEqual(nsub.html_class, ssub.html_class)
                self.assertEqual(nsub.order, ssub.order)
                self.assertEqual(nsub.tag, ssub.tag)
                self.assertEqual(nsub.callout_box, ssub.callout_box)
                self.assertEqual(nsub.body, ssub.body)

                # compare-only fields should be DEFAULTS on NOFO→compare_doc
                self.assertEqual(nsub.comparison_type, "body")
                self.assertEqual(nsub.diff_strings, [])

    def test_duplicate_from_nofo_sets_from_nofo(self):
        source = self._make_nofo_with_content(opdiv="NIH")
        new = duplicate_compare_doc(source)
        self.assertEqual(new.from_nofo, source)

    def test_duplicate_from_compare_doc_leaves_from_nofo_empty(self):
        source = self._make_compare_doc_with_content(opdiv="CDC")
        new = duplicate_compare_doc(source)
        self.assertIsNone(new.from_nofo)

    def test_duplicate_twice_from_nofo_sets_from_nofo_and_successor(self):
        source = self._make_nofo_with_content(opdiv="NIH")
        first_doc = duplicate_compare_doc(source)
        self.assertEqual(first_doc.from_nofo, source)
        self.assertIsNone(first_doc.successor)

        second_doc = duplicate_compare_doc(source)
        self.assertEqual(second_doc.from_nofo, source)
        self.assertIsNone(second_doc.successor)

        # Refresh to see updates made inside duplicate_compare_doc
        first_doc.refresh_from_db()
        # first doc should now have a successor now
        self.assertEqual(first_doc.successor, second_doc)

        # Only one open head for this NOFO
        open_heads = CompareDocument.objects.filter(
            from_nofo=source, successor__isnull=True
        )
        self.assertEqual(open_heads.count(), 1)
        self.assertEqual(open_heads.first().pk, second_doc.pk)


class CompareListViewTests(TestCase):
    def setUp(self):
        self.bloom_user = User.objects.create_user(
            email="bloom@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.hrsa_user = User.objects.create_user(
            email="hrsa@example.com",
            password="testpass123",
            group="hrsa",
            force_password_reset=False,
        )

        self.document_bloom = CompareDocument.objects.create(
            title="Bloom Compare Doc", group="bloom", opdiv="CDC"
        )
        self.document_hrsa = CompareDocument.objects.create(
            title="HRSA Compare Doc", group="hrsa", opdiv="CDC"
        )

        # default login is bloom user
        self.client.login(email="bloom@example.com", password="testpass123")

    def login_as(self, user):
        """Helper to switch users in tests."""
        self.client.logout()
        self.client.login(email=user.email, password="testpass123")

    def test_view_returns_200_for_logged_in_user(self):
        url = reverse("compare:compare_index")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_docs_are_ordered_by_updated_desc(self):
        url = reverse("compare:compare_index")
        response = self.client.get(url)
        docs = list(response.context["compare_docs"])
        self.assertEqual(docs, sorted(docs, key=lambda g: g.updated, reverse=True))

    def test_redirects_anonymous_user(self):
        self.client.logout()
        url = reverse("compare:compare_index")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_archived_docs_are_excluded(self):
        archived = CompareDocument.objects.create(
            title="Archived", group="bloom", opdiv="CDC", archived=timezone.now()
        )
        url = reverse("compare:compare_index")
        response = self.client.get(url)
        self.assertNotIn(archived, response.context["compare_docs"])

    def test_docs_with_successor_are_excluded(self):
        # Create a compare doc chain
        first = CompareDocument.objects.create(
            title="First", group="bloom", opdiv="CDC"
        )
        second = CompareDocument.objects.create(
            title="Second", group="bloom", opdiv="CDC", from_nofo=None
        )
        first.successor = second
        first.save()

        url = reverse("compare:compare_index")
        response = self.client.get(url)
        docs = list(response.context["compare_docs"])

        # "first" should be excluded because it has a successor
        self.assertNotIn(first, docs)
        # "second" (the current head) should still be visible
        self.assertIn(second, docs)

    # ---- NEW GROUP VISIBILITY TESTS ----

    def test_bloom_user_can_see_bloom_docs(self):
        self.login_as(self.bloom_user)
        response = self.client.get(reverse("compare:compare_index"))
        self.assertIn(self.document_bloom, response.context["compare_docs"])

    def test_hrsa_user_can_see_hrsa_docs(self):
        self.login_as(self.hrsa_user)
        response = self.client.get(reverse("compare:compare_index"))
        self.assertIn(self.document_hrsa, response.context["compare_docs"])

    def test_bloom_user_can_see_hrsa_docs(self):
        self.login_as(self.bloom_user)
        response = self.client.get(reverse("compare:compare_index"))
        self.assertIn(self.document_hrsa, response.context["compare_docs"])

    def test_hrsa_user_cannot_see_bloom_docs(self):
        self.login_as(self.hrsa_user)
        response = self.client.get(reverse("compare:compare_index"))
        self.assertNotIn(self.document_bloom, response.context["compare_docs"])


class CompareImportViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="importer@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="importer@example.com", password="testpass123")
        self.url = reverse("compare:compare_import")

    def test_view_renders_import_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<form")

    def test_view_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertIn(response.status_code, [302, 403])

    def test_post_with_invalid_file_returns_400(self):
        fake_doc = SimpleUploadedFile("bad.txt", b"not a Word file")
        response = self.client.post(self.url, {"file": fake_doc})

        # redirect back to import page and show an error
        self.assertEqual(response.status_code, 302)
        follow_response = self.client.get(response["Location"])
        self.assertEqual(follow_response.status_code, 200)
        self.assertContains(follow_response, "Error: Oops! No fos uploaded.")

    def test_post_missing_file_returns_400(self):
        response = self.client.post(self.url, {})  # no file at all

        # redirect back to import page and show an error
        self.assertEqual(response.status_code, 302)
        follow_response = self.client.get(response["Location"])
        self.assertEqual(follow_response.status_code, 200)
        self.assertContains(follow_response, "Error: Oops! No fos uploaded.")


# Edit the title right after importing
class CompareImportTitleViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.document = CompareDocument.objects.create(
            title="Original Title", opdiv="CDC", group="bloom"
        )
        self.url = reverse(
            "compare:compare_import_title", kwargs={"pk": self.document.pk}
        )
        self.redirect_url = reverse(
            "compare:compare_document", kwargs={"pk": self.document.pk}
        )

    def test_view_returns_200_for_authorized_user(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_valid_data_updates_title(self):
        response = self.client.post(self.url, {"title": "Updated Title"})
        self.document.refresh_from_db()
        self.assertEqual(self.document.title, "Updated Title")
        self.assertRedirects(response, self.redirect_url)

    def test_post_invalid_data_shows_errors(self):
        response = self.client.post(self.url, {"title": ""})  # empty title = invalid
        self.assertEqual(response.status_code, 200)

        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertIn("This field is required.", form.errors["title"])

    def test_unauthorized_user_redirected(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)
        self.assertIn(response.status_code, [302, 403])


class CompareDuplicateViewTests(TestCase):
    def _make_nofo(self):
        nofo = Nofo.objects.create(
            title="NOFO title",
            short_name="NOFO short name",
            filename="nofile.docx",
            opdiv="NIH",
            group="bloom",
        )
        s1 = Section.objects.create(nofo=nofo, name="Sec 1", html_id="s1", order=1)
        s2 = Section.objects.create(nofo=nofo, name="Sec 2", html_id="s2", order=2)
        Subsection.objects.create(
            section=s1, name="A", html_id="a", order=1, tag="h3", body="Body A"
        )
        Subsection.objects.create(
            section=s2, name="B", html_id="b", order=1, tag="h3", body="Body B"
        )
        return nofo

    def _make_compare_doc(self):
        document = CompareDocument.objects.create(
            title="Compare Doc", filename="g.docx", opdiv="ACF", group="bloom"
        )
        gs = CompareSection.objects.create(
            document=document, name="G1", html_id="g1", order=1
        )
        CompareSubsection.objects.create(
            section=gs,
            name="G1.1",
            html_id="g1-1",
            order=1,
            tag="h3",
            body="G body",
            comparison_type="name",
            diff_strings=["x"],
        )
        return document

    def test_view_duplicates_from_nofo_and_redirects(self):
        source = self._make_nofo()
        url = reverse("compare:compare_duplicate", args=[source.id])

        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        # One new doc created
        self.assertEqual(CompareDocument.objects.count(), 1)
        new = CompareDocument.objects.latest("created")
        # Redirect goes to edit page for new doc
        self.assertIn(
            reverse("compare:compare_document", args=[new.id]), resp["Location"]
        )
        # Sanity: sections/subsections copied
        self.assertEqual(new.sections.count(), 2)
        self.assertEqual(sum(s.subsections.count() for s in new.sections.all()), 2)

    def test_view_duplicates_from_compare_doc_and_redirects(self):
        source = self._make_compare_doc()
        url = reverse("compare:compare_duplicate", args=[source.id])

        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(CompareDocument.objects.count(), 2)  # original + new
        new = CompareDocument.objects.exclude(id=source.id).get()
        self.assertIn(
            reverse("compare:compare_document", args=[new.id]), resp["Location"]
        )
        # compare-specific fields preserved
        new_sub = new.sections.first().subsections.first()
        self.assertEqual(new_sub.comparison_type, "name")
        self.assertEqual(new_sub.diff_strings, ["x"])

    def test_get_acts_like_post(self):
        source = self._make_nofo()
        url = reverse("compare:compare_duplicate", args=[source.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(CompareDocument.objects.count(), 1)


# Edit the title from the "edit" screen
class CompareEditTitleViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.document = CompareDocument.objects.create(
            title="Original Title", opdiv="CDC", group="bloom"
        )
        self.url = reverse(
            "compare:compare_edit_title", kwargs={"pk": self.document.pk}
        )
        self.redirect_url = reverse(
            "compare:compare_edit", kwargs={"pk": self.document.pk}
        )

    def test_view_returns_200_for_authorized_user(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_valid_data_updates_title(self):
        response = self.client.post(self.url, {"title": "Updated Title"})
        self.document.refresh_from_db()
        self.assertEqual(self.document.title, "Updated Title")
        self.assertRedirects(response, self.redirect_url)

    def test_post_invalid_data_shows_errors(self):
        response = self.client.post(self.url, {"title": ""})  # empty title = invalid
        self.assertEqual(response.status_code, 200)

        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertIn("This field is required.", form.errors["title"])

    def test_unauthorized_user_redirected(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertIn(response.status_code, [302, 403])


class CompareArchiveViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.document = CompareDocument.objects.create(
            title="Test Compare Doc",
            opdiv="CDC",
            group="bloom",
        )
        self.url = reverse("compare:compare_archive", args=[self.document.id])

    def test_get_view_renders_confirmation_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Are you absolutely sure you want to delete “Test Compare Doc”?",
        )

    def test_post_archives_compare_doc(self):
        response = self.client.post(self.url)
        self.document.refresh_from_db()
        self.assertIsNotNone(self.document.archived)
        self.assertRedirects(response, reverse("compare:compare_index"))

    def test_cannot_archive_already_archived_compare_doc(self):
        self.document.archived = timezone.now()
        self.document.save()

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"already archived", response.content)

    def test_anonymous_user_forbidden(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"Permission denied", response.content)


class CompareEditViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="user@example.com", password="testpass123")

        self.document = CompareDocument.objects.create(
            title="Test Compare Doc",
            opdiv="CDC",
            group="bloom",
        )

        self.section1 = CompareSection.objects.create(
            name="Introduction",
            html_id="intro",
            order=1,
            document=self.document,
        )
        self.section2 = CompareSection.objects.create(
            name="Eligibility",
            html_id="eligibility",
            order=2,
            document=self.document,
        )

        self.url = reverse("compare:compare_edit", args=[self.document.pk])

    def test_view_displays_compare_doc_title(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Configure document: “{self.document.title}”")
        self.assertContains(response, "Ready to compare")

    def test_view_displays_section_names(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.section1.name)
        self.assertContains(response, self.section2.name)

    def test_view_shows_archived_warning_if_compare_doc_is_archived(self):
        self.document.archived = timezone.now()
        self.document.save()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Archived Compare Document")

    def test_compare_doc_edit_view_with_valid_new_nofo_param(self):
        new_nofo = Nofo.objects.create(
            title="Some NOFO",
            number="NOFO-123",
            opdiv="CDC",
            group="bloom",
        )

        url = reverse("compare:compare_edit", kwargs={"pk": self.document.pk})
        response = self.client.get(f"{url}?new_nofo={new_nofo.pk}")
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Return to comparison")
        self.assertContains(
            response,
            reverse(
                "compare:compare_document_result", args=[self.document.pk, new_nofo.pk]
            ),
        )

        # Upload new NOFO button is gone
        self.assertNotContains(response, "Upload NOFO to compare")

    def test_compare_doc_edit_view_with_invalid_new_nofo_param(self):
        url = reverse("compare:compare_edit", kwargs={"pk": self.document.pk})

        # malformed UUID
        response = self.client.get(f"{url}?new_nofo=not-a-real-id")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ready to compare")

        # well-formed UUID but not in DB
        missing_id = uuid.uuid4()
        response = self.client.get(f"{url}?new_nofo={missing_id}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ready to compare")

        # Return to comparison button is gone
        self.assertNotContains(response, "Return to comparison")

    def test_post_updates_subsections(self):
        """Test that POST request can handle multiple subsections at once"""
        # Create multiple subsections that need to be updated
        subsection1 = CompareSubsection.objects.create(
            section=self.section1,
            name="Test Subsection 1",
            order=1,
            tag="h3",
            comparison_type="none",
        )
        subsection2 = CompareSubsection.objects.create(
            section=self.section2,
            name="Test Subsection 2",
            order=1,
            tag="h3",
            comparison_type="body",
        )
        # Create a subsection that does not need to be updated
        subsection3 = CompareSubsection.objects.create(
            section=self.section1,
            name="Test Subsection 3",
            order=2,
            tag="h3",
            comparison_type="body",
        )

        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "subsections": {
                        str(subsection1.id): True,
                        str(subsection2.id): False,
                        str(subsection3.id): True,
                    }
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        # Check JSON response
        response_data = response.json()
        self.assertEqual(response_data["status"], "success")
        self.assertEqual(response_data["selections_count"], 3)
        self.assertEqual(response_data["updated_count"], 2)
        self.assertEqual(response_data["failed_subsection_ids"], [])

        subsection1.refresh_from_db()
        subsection2.refresh_from_db()
        subsection3.refresh_from_db()
        self.assertEqual(subsection1.comparison_type, "body")
        self.assertEqual(subsection2.comparison_type, "none")
        self.assertEqual(subsection3.comparison_type, "body")

    def test_post_with_invalid_subsection_ids_returns_partial_status(self):
        """Test that POST request handles invalid subsection IDs gracefully"""
        # Create one valid subsection
        subsection1 = CompareSubsection.objects.create(
            section=self.section1,
            name="Valid Subsection",
            order=1,
            tag="h3",
            comparison_type="none",
        )

        # Use one valid ID and one invalid ID
        invalid_id = "99999"

        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "subsections": {
                        str(subsection1.id): True,  # Valid subsection
                        invalid_id: False,  # Invalid subsection
                    }
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

        # Check JSON response for partial failure
        response_data = response.json()
        self.assertEqual(response_data["status"], "partial")
        self.assertEqual(response_data["selections_count"], 2)
        self.assertEqual(response_data["updated_count"], 1)
        self.assertEqual(response_data["failed_subsection_ids"], [invalid_id])
        self.assertIn("Some comparison selections failed", response_data["message"])

        # Verify valid subsection was updated
        subsection1.refresh_from_db()
        self.assertEqual(subsection1.comparison_type, "body")

    def test_post_with_all_invalid_subsection_ids_returns_fail_status(self):
        """Test that POST request with all invalid IDs returns fail status"""
        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "subsections": {
                        "99999": True,  # Invalid subsection
                        "88888": False,  # Invalid subsection
                    }
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

        # Check JSON response for complete failure
        response_data = response.json()
        self.assertEqual(response_data["status"], "fail")
        self.assertEqual(response_data["selections_count"], 2)
        self.assertEqual(response_data["updated_count"], 0)
        self.assertEqual(
            set(response_data["failed_subsection_ids"]), {"99999", "88888"}
        )
        self.assertIn("Comparison selections failed", response_data["message"])

    def test_post_with_invalid_json_returns_error(self):
        """Test that POST request with invalid JSON returns proper error"""
        response = self.client.post(
            self.url,
            data="invalid json data",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertEqual(response_data["message"], "Invalid JSON data.")


class CompareDocumentViewTests(TestCase):
    def setUp(self):
        # Bloom user (can see all docs)
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.document = CompareDocument.objects.create(
            title="Older", group="bloom", opdiv="CDC"
        )

    def test_compare_view_without_new_nofo_shows_upload_prompt(self):
        """
        Case 1: No new document ID provided -> prompt to upload another document should appear.
        """
        url = reverse("compare:compare_document", args=[self.document.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Upload another document to be able to compare.")

    @patch("compare.views.annotate_side_by_side_diffs")
    @patch("compare.views.compare_nofos")
    def test_compare_view_with_new_nofo_and_zero_not_none_subsections_shows_no_changes(
        self, mock_compare, mock_annotate
    ):
        """
        Case 2: There IS a new NOFO, but the compare doc has 0 subsections whose comparison_type != 'none'.
        Expect the 'No changes' message with both titles.
        """
        # Ensure not_none_subsection_count == 0 by making all compare doc subsections "none"
        section = CompareSection.objects.create(
            document=self.document, name="Step 1", order=1, html_id="step-1"
        )
        CompareSubsection.objects.create(
            section=section,
            name="Basic Information",
            tag="h3",
            body="Body text",
            comparison_type="none",  # <-- only 'none' types exist
            order=1,
        )

        new_nofo = Nofo.objects.create(title="Newer", group="bloom", opdiv="CDC")

        # Mock a comparison result with only MATCHed subsections
        sub = MagicMock()
        sub.status = "MATCH"
        sub.name = "Some subsection"
        sub.old_value = "Old"
        sub.new_value = "New"
        sub.comparison_type = "name"

        comparison = [{"name": "Step 1", "subsections": [sub]}]
        mock_compare.return_value = comparison
        mock_annotate.return_value = comparison

        url = reverse(
            "compare:compare_document_result", args=[self.document.pk, new_nofo.pk]
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # Expected “no changes” message
        expected = "<strong>No changes</strong>"
        self.assertContains(resp, expected)


class CompareDocumentCSVViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.document = CompareDocument.objects.create(
            title="Older", group="bloom", opdiv="CDC"
        )
        self.new_nofo = Nofo.objects.create(title="Newer", group="bloom", opdiv="CDC")

    def parse_csv(self, content):
        """Helper to parse CSV bytes into a list of rows"""
        return list(csv.reader(io.StringIO(content.decode("utf-8"))))

    @patch("compare.views.compare_nofos")
    @patch("compare.views.annotate_side_by_side_diffs")
    def test_csv_no_merged_subsections_add(self, mock_annotate, mock_compare):
        subsection = MagicMock()
        subsection.status = "ADD"
        subsection.old_name = ""
        subsection.new_name = "Summary added"
        subsection.old_value = ""
        subsection.new_value = "New body"

        comparison = [
            {
                "name": "Step 1: Review the Opportunity",
                "subsections": [subsection],
            }
        ]
        mock_compare.return_value = comparison
        mock_annotate.return_value = comparison

        url = reverse(
            "compare:compare_document_result_csv",
            args=[self.document.pk, self.new_nofo.pk],
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn(
            f"compare__{self.document.pk}__{self.new_nofo.pk}.csv",
            response["Content-Disposition"],
        )

        rows = self.parse_csv(response.content)
        self.assertEqual(
            rows[0], ["Status", "Step name", "Section name", "Old value", "New value"]
        )
        self.assertEqual(
            rows[1],
            ["ADD", "Step 1: Review the Opportunity", "Summary added", "", "New body"],
        )

    @patch("compare.views.compare_nofos")
    @patch("compare.views.annotate_side_by_side_diffs")
    def test_csv_no_merged_subsections_delete(self, mock_annotate, mock_compare):
        subsection = MagicMock()
        subsection.status = "DELETE"
        subsection.old_name = "Summary deleted"
        subsection.new_name = ""
        subsection.old_value = "Old body"
        subsection.new_value = ""

        comparison = [
            {
                "name": "Step 1: Review the Opportunity",
                "subsections": [subsection],
            }
        ]
        mock_compare.return_value = comparison
        mock_annotate.return_value = comparison

        url = reverse(
            "compare:compare_document_result_csv",
            args=[self.document.pk, self.new_nofo.pk],
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn(
            f"compare__{self.document.pk}__{self.new_nofo.pk}.csv",
            response["Content-Disposition"],
        )

        rows = self.parse_csv(response.content)
        self.assertEqual(
            rows[0], ["Status", "Step name", "Section name", "Old value", "New value"]
        )
        self.assertEqual(
            rows[1],
            [
                "DELETE",
                "Step 1: Review the Opportunity",
                "Summary deleted",
                "Old body",
                "",
            ],
        )

    @patch("compare.views.compare_nofos")
    @patch("compare.views.annotate_side_by_side_diffs")
    def test_csv_no_merged_subsections_update(self, mock_annotate, mock_compare):
        subsection = MagicMock()
        subsection.status = "UPDATE"
        subsection.old_name = "Summary"
        subsection.new_name = "Summary"
        subsection.old_value = "Old body"
        subsection.new_value = "New body"

        comparison = [
            {
                "name": "Step 1: Review the Opportunity",
                "subsections": [subsection],
            }
        ]
        mock_compare.return_value = comparison
        mock_annotate.return_value = comparison

        url = reverse(
            "compare:compare_document_result_csv",
            args=[self.document.pk, self.new_nofo.pk],
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn(
            f"compare__{self.document.pk}__{self.new_nofo.pk}.csv",
            response["Content-Disposition"],
        )

        rows = self.parse_csv(response.content)
        self.assertEqual(
            rows[0], ["Status", "Step name", "Section name", "Old value", "New value"]
        )
        self.assertEqual(
            rows[1],
            [
                "UPDATE",
                "Step 1: Review the Opportunity",
                "Summary",
                "Old body",
                "New body",
            ],
        )

    @patch("compare.views.compare_nofos")
    @patch("compare.views.annotate_side_by_side_diffs")
    def test_csv_with_merged_subsections(self, mock_annotate, mock_compare):
        subsection = MagicMock()
        subsection.status = "UPDATE"
        subsection.old_name = "Summary"
        subsection.new_name = "Updated Summary"
        subsection.old_value = "Old body"
        subsection.new_value = "New body"

        comparison = [
            {
                "name": "Step 1: Review the Opportunity",
                "subsections": [subsection],
            }
        ]
        mock_compare.return_value = comparison
        mock_annotate.return_value = comparison

        url = reverse(
            "compare:compare_document_result_csv",
            args=[self.document.pk, self.new_nofo.pk],
        )
        response = self.client.get(url)

        rows = self.parse_csv(response.content)
        self.assertEqual(
            rows[0],
            [
                "Status",
                "Step name",
                "Section name",
                "Old value",
                "New section name",
                "New value",
            ],
        )
        self.assertEqual(
            rows[1],
            [
                "UPDATE",
                "Step 1: Review the Opportunity",
                "Summary",
                "Old body",
                "Updated Summary",
                "New body",
            ],
        )
