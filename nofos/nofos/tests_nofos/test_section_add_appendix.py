from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch

from bs4 import BeautifulSoup
from django.contrib.messages import get_messages
from django.db import close_old_connections, connections
from django.template.loader import render_to_string
from django.test import Client, TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Section, Subsection
from nofos.nofo import get_nofo_action_links


class NofoAddAppendixSectionViewTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="appendix@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.nofo = Nofo.objects.create(
            title="Test NOFO", number="NOFO-ACF-001", opdiv="ACF", group="bloom"
        )
        self.first = Section.objects.create(
            nofo=self.nofo, name="Contacts and Support", html_id="contacts", order=1
        )
        self.url = reverse("nofos:section_add_appendix", args=[self.nofo.pk])

    def test_menu_has_post_action_immediately_after_endnotes(self):
        links = get_nofo_action_links(self.nofo)
        keys = [link["key"] for link in links]
        self.assertEqual(keys.index("add_appendix"), keys.index("add_end_notes") + 1)
        self.assertEqual(links[keys.index("add_appendix")]["method"], "post")

        response = self.client.get(reverse("nofos:nofo_edit", args=[self.nofo.pk]))
        soup = BeautifulSoup(response.content, "html.parser")
        form = soup.find("form", action=self.url)
        self.assertIsNotNone(form)
        self.assertEqual(form.get("method"), "post")
        self.assertIsNotNone(form.find("input", attrs={"name": "csrfmiddlewaretoken"}))
        self.assertEqual(form.find("button").get_text(strip=True), "Add Appendix")

    def test_post_creates_fixed_empty_section_and_redirects_with_message(self):
        response = self.client.post(
            self.url,
            {"name": "User value", "html_id": "user-value", "has_section_page": "on"},
        )
        self.assertRedirects(
            response,
            reverse("nofos:nofo_edit", args=[self.nofo.pk]) + "#appendix",
            fetch_redirect_response=False,
        )
        appendix = self.nofo.sections.get(html_id="appendix")
        self.assertEqual(appendix.name, "Appendix")
        self.assertFalse(appendix.has_section_page)
        self.assertEqual(appendix.order, 2)
        self.assertEqual(appendix.subsections.count(), 0)
        self.assertEqual(self.nofo.sections.count(), 2)
        self.assertTrue(
            any(
                "Added new section" in msg.message and "href='#appendix'" in msg.message
                for msg in get_messages(response.wsgi_request)
            )
        )

    def test_post_orders_endnotes_appendix_modifications_in_both_creation_orders(self):
        for initial_tail in (
            ("endnotes", "modifications"),
            ("modifications", "endnotes"),
            ("modifications",),
            ("endnotes",),
        ):
            with self.subTest(initial_tail=initial_tail):
                self.nofo.sections.exclude(pk=self.first.pk).delete()
                for html_id in initial_tail:
                    Section.objects.create(
                        nofo=self.nofo,
                        name=html_id.title(),
                        html_id=html_id,
                        has_section_page=False,
                        order=Section.get_next_order(self.nofo),
                    )
                self.client.post(self.url)
                self.assertEqual(
                    list(
                        self.nofo.sections.order_by("order").values_list(
                            "html_id", flat=True
                        )
                    ),
                    ["contacts"]
                    + [
                        html_id
                        for html_id in ("endnotes", "appendix", "modifications")
                        if html_id == "appendix" or html_id in initial_tail
                    ],
                )

    def test_adding_endnotes_after_appendix_inserts_before_it(self):
        self.client.post(self.url)
        endnotes_url = reverse("nofos:section_add_end_notes", args=[self.nofo.pk])
        response = self.client.post(endnotes_url, {"body": "Reference"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(
                self.nofo.sections.order_by("order").values_list("html_id", flat=True)
            ),
            ["contacts", "endnotes", "appendix"],
        )

    def test_imported_modifications_with_numbered_id_stays_last(self):
        Section.objects.create(
            nofo=self.nofo,
            name="Modifications",
            html_id="7--modifications",
            has_section_page=False,
            order=2,
        )
        self.client.post(self.url)
        endnotes_url = reverse("nofos:section_add_end_notes", args=[self.nofo.pk])
        self.client.post(endnotes_url, {"body": "Reference"})
        self.assertEqual(
            list(
                self.nofo.sections.order_by("order").values_list("html_id", flat=True)
            ),
            ["contacts", "endnotes", "appendix", "7--modifications"],
        )

    def test_repeated_request_and_menu_hide_do_not_duplicate(self):
        self.client.post(self.url)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.nofo.sections.filter(html_id="appendix").count(), 1)
        self.assertNotIn(
            "add_appendix", [link["key"] for link in get_nofo_action_links(self.nofo)]
        )

    def test_existing_html_id_under_other_name_suppresses_action(self):
        Section.objects.create(
            nofo=self.nofo, name="References", html_id="appendix", order=2
        )
        self.assertNotIn(
            "add_appendix", [link["key"] for link in get_nofo_action_links(self.nofo)]
        )
        self.client.post(self.url)
        self.assertEqual(self.nofo.sections.filter(html_id="appendix").count(), 1)

    def test_get_cannot_create_section(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertFalse(self.nofo.sections.filter(html_id="appendix").exists())

    def test_status_and_archived_guards(self):
        for status, archived, modified in (
            ("published", False, False),
            ("published", False, True),
            ("cancelled", False, False),
            ("draft", True, False),
        ):
            with self.subTest(status=status, archived=archived, modified=modified):
                self.nofo.status = status
                self.nofo.archived = date(2026, 9, 23) if archived else None
                self.nofo.modifications = date(2026, 9, 22) if modified else None
                self.nofo.save()
                self.assertNotIn(
                    "add_appendix",
                    [link["key"] for link in get_nofo_action_links(self.nofo)],
                )
                with self.assertLogs("django.request", level="WARNING"):
                    response = self.client.post(self.url)
                self.assertEqual(response.status_code, 400)
                self.assertFalse(self.nofo.sections.filter(html_id="appendix").exists())

    def test_group_access_is_checked_before_duplicate_disclosure(self):
        self.nofo.group = "acf"
        self.nofo.save()
        Section.objects.create(
            nofo=self.nofo, name="Appendix", html_id="appendix", order=2
        )
        other_user = BloomUser.objects.create_user(
            email="other@example.com",
            password="testpass123",
            force_password_reset=False,
            group="hrsa",
        )
        self.client.force_login(other_user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)

    def test_html_view_has_no_title_page_and_indented_toc_entry(self):
        self.client.post(self.url)
        Subsection.objects.create(
            section=self.nofo.sections.get(html_id="appendix"),
            name="Supporting material",
            tag="h3",
            body="Appendix body",
            order=1,
        )
        response = self.client.get(reverse("nofos:nofo_view", args=[self.nofo.pk]))
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        appendix = soup.find("section", id="section--appendix")
        self.assertIsNotNone(appendix)
        self.assertIn("section--no-section-page", appendix.get("class", []))
        self.assertIsNone(appendix.select_one(".section--title-page"))
        self.assertIn("Appendix body", appendix.get_text())
        toc_entry = soup.select_one("#section--toc .toc--appendix")
        self.assertIsNotNone(toc_entry)
        self.assertIn("toc--no-icon", toc_entry.get("class", []))

    @patch("nofos.views.docraptor.DocApi")
    def test_pdf_source_and_word_export_include_appendix(self, mock_doc_api):
        self.client.post(self.url)
        Subsection.objects.create(
            section=self.nofo.sections.get(html_id="appendix"),
            name="Supporting material",
            tag="h3",
            body="Appendix body",
            order=1,
        )

        export_html = render_to_string(
            "nofos/includes/nofo_export_document.html", {"nofo": self.nofo}
        )
        export_soup = BeautifulSoup(export_html, "html.parser")
        appendix = export_soup.find("section", id="section--appendix")
        self.assertIsNotNone(appendix)
        self.assertIn("Appendix body", appendix.get_text())
        self.assertIsNone(appendix.select_one(".section--title-page"))

        mock_doc_api.return_value.create_doc.return_value = b"%PDF-1.4 fake pdf"
        response = self.client.post(reverse("nofos:print_pdf", args=[self.nofo.pk]))
        self.assertEqual(response.status_code, 200)
        pdf_source = mock_doc_api.return_value.create_doc.call_args.args[0][
            "document_content"
        ]
        pdf_soup = BeautifulSoup(pdf_source, "html.parser")
        appendix = pdf_soup.find("section", id="section--appendix")
        self.assertIsNotNone(appendix)
        self.assertIn("section--no-section-page", appendix.get("class", []))
        self.assertIsNone(appendix.select_one(".section--title-page"))
        self.assertIn("Appendix body", appendix.get_text())
        self.assertIsNotNone(pdf_soup.select_one("#section--toc .toc--appendix"))


class NofoAddAppendixConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_simultaneous_requests_create_only_one_appendix(self):
        user = BloomUser.objects.create_user(
            email="appendix-concurrent@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        nofo = Nofo.objects.create(
            title="Concurrent appendix", opdiv="ACF", group="bloom"
        )
        url = reverse("nofos:section_add_appendix", args=[nofo.pk])
        clients = [Client(), Client()]
        for client in clients:
            client.force_login(user)
        start = Barrier(3)

        def add_appendix(client):
            close_old_connections()
            try:
                start.wait(timeout=5)
                return client.post(url).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(add_appendix, client) for client in clients]
            start.wait(timeout=5)
            self.assertEqual(
                [future.result(timeout=20) for future in futures], [302, 302]
            )

        self.assertEqual(nofo.sections.filter(html_id="appendix").count(), 1)
