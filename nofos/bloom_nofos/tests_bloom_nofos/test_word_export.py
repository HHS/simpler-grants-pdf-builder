import io
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock, patch
from zipfile import ZipFile

from bloom_nofos.word_export import (
    ExportError,
    conversion_slot,
    convert_html,
    embed_image,
    normalize_docx,
    pandoc_download_response,
    render_export_html,
)
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase


class WordExportTests(SimpleTestCase):
    def test_bundled_image_embedded_without_network(self):
        result = embed_image("/static/img/logo-img.png", "testserver")
        self.assertTrue(result.startswith("data:image/png;base64,"))
        self.assertEqual(
            result,
            embed_image("https://testserver/static/img/logo-img.png", "testserver"),
        )

    def test_untrusted_image_paths_are_rejected_before_file_lookup(self):
        for source in (
            "https://other.test/static/img/logo-img.png",
            "//169.254.169.254/static/img/logo-img.png",
            "file:///static/img/logo-img.png",
            "/static/../settings.py",
            "/static/%2e%2e/settings.py",
            "/static/%2fetc/passwd",
            "/static/img/../../settings.py",
            "/private/image.png",
        ):
            with self.subTest(source=source), patch(
                "bloom_nofos.word_export.finders.find"
            ) as lookup, self.assertRaises(ExportError):
                embed_image(source, "testserver")
            lookup.assert_not_called()

    def test_invalid_embedded_image_is_rejected(self):
        for source in (
            "data:image/png;base64,not base64",
            "data:image/png;base64,YWJj",
            "data:image/svg+xml;base64,PHN2Zz4=",
        ):
            with self.subTest(source=source), self.assertRaises(ExportError):
                embed_image(source, "testserver")

    def test_feature_flag_routes_only_when_enabled(self):
        from bloom_nofos.utils import generate_docx_download_response

        for enabled in (False, True):
            with self.subTest(enabled=enabled), patch(
                "constance.config",
                SimpleNamespace(PANDOC_WORD_EXPORT_ENABLED=enabled),
            ), patch("bloom_nofos.word_export.pandoc_download_response") as local:
                response = generate_docx_download_response(
                    request=self.request(),
                    export_url="https://testserver/export",
                    target_element="#download_target",
                    filename_base="test",
                    tmp_name="test",
                )
                self.assertEqual(local.called, enabled)
                if enabled:
                    self.assertIs(response, local.return_value)
                else:
                    self.assertIn(b"Missing session/csrf", response.content)

    def test_missing_binary_is_actionable(self):
        with patch(
            "bloom_nofos.word_export.subprocess.Popen", side_effect=FileNotFoundError
        ), self.assertRaisesMessage(ExportError, "unavailable"):
            convert_html("<p>Content</p>")

    def test_timeout_kills_group_and_reaps_process(self):
        process = Mock(pid=12345)
        process.communicate.side_effect = [
            subprocess.TimeoutExpired("pandoc", 45),
            (b"", b""),
        ]
        with patch(
            "bloom_nofos.word_export.subprocess.Popen", return_value=process
        ), patch("bloom_nofos.word_export.os.killpg") as kill, self.assertRaisesMessage(
            ExportError, "timed out"
        ):
            convert_html("<p>Content</p>")
        kill.assert_called_once()
        self.assertEqual(process.communicate.call_count, 2)

    def test_style_normalization_preserves_numbering(self):
        output = io.BytesIO()
        with ZipFile(output, "w") as archive:
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:pPr><w:pStyle w:val="Compact"/><w:numPr><w:ilvl w:val="1"/></w:numPr></w:pPr><w:r><w:t>Content</w:t></w:r></w:p></w:body></w:document>',
            )
        with ZipFile(io.BytesIO(normalize_docx(output.getvalue()))) as result:
            xml = result.read("word/document.xml")
        self.assertIn(b"BodyText", xml)
        self.assertIn(b"numPr", xml)
        self.assertIn(b"Content", xml)

    def request(self):
        request = RequestFactory().post("/export", HTTP_HOST="testserver")
        request.user = SimpleNamespace(is_authenticated=True)
        return request

    def test_slots_are_shared_and_released(self):
        with conversion_slot() as first, conversion_slot() as second:
            self.assertTrue(first)
            self.assertFalse(second)
        with conversion_slot() as available:
            self.assertTrue(available)

    def test_oversized_conversion_rejected_before_process_start(self):
        with patch("bloom_nofos.word_export.MAX_INPUT", 10), patch(
            "bloom_nofos.word_export.subprocess.Popen"
        ) as popen, self.assertRaisesMessage(ExportError, "size limit"):
            convert_html("é" * 6)
        popen.assert_not_called()

    def test_heap_and_stack_limits_are_always_passed(self):
        with patch(
            "bloom_nofos.word_export.subprocess.Popen", side_effect=FileNotFoundError
        ) as popen:
            with self.assertRaises(ExportError):
                convert_html("<p>Content</p>")
        self.assertEqual(
            popen.call_args.args[0][1:5], ["+RTS", "-M192m", "-K16m", "-RTS"]
        )

    def test_oversized_render_rejected_before_parsing(self):
        match = SimpleNamespace(
            url_name="nofo_export",
            func=lambda *a, **k: HttpResponse("x" * 11),
            args=(),
            kwargs={},
        )
        with patch("bloom_nofos.word_export.resolve", return_value=match), patch(
            "bloom_nofos.word_export.MAX_INPUT", 10
        ), patch(
            "bloom_nofos.word_export.BeautifulSoup"
        ) as parse, self.assertRaisesMessage(
            ExportError, "size limit"
        ):
            render_export_html(
                self.request(), "http://testserver/export", "#download_target"
            )
        parse.assert_not_called()

    def test_invalid_and_empty_outputs_rejected(self):
        with self.assertRaises(ExportError):
            normalize_docx(b"not a zip")
        output = io.BytesIO()
        with ZipFile(output, "w") as archive:
            archive.writestr("word/document.xml", "<document/>")
        with self.assertRaises(ExportError):
            normalize_docx(output.getvalue())

    def test_aggregate_images_rejected_during_embedding(self):
        match = SimpleNamespace(
            url_name="nofo_export",
            func=lambda *a, **k: HttpResponse(
                '<div id="download_target"><p>Content</p><img src="a"><img src="b"><img src="c"></div>'
            ),
            args=(),
            kwargs={},
        )
        with patch("bloom_nofos.word_export.resolve", return_value=match), patch(
            "bloom_nofos.word_export.MAX_INPUT", 200
        ), patch(
            "bloom_nofos.word_export.embed_image", return_value="x" * 150
        ) as embed:
            with self.assertRaisesMessage(ExportError, "size limit"):
                render_export_html(
                    self.request(), "http://testserver/export", "#download_target"
                )
        self.assertEqual(embed.call_count, 2)

    def test_external_destination_rejected(self):
        with self.assertRaises(ExportError):
            render_export_html(
                self.request(), "https://other.test/export", "#download_target"
            )

    def test_only_target_is_rendered_and_query_is_preserved(self):
        seen = []

        def view(request):
            seen.append(request.GET.get("policy_stripped"))
            return HttpResponse(
                '<p>secret outside target</p><div id="download_target"><p>Safe text</p><form>private form</form></div>'
            )

        match = SimpleNamespace(url_name="nofo_export", func=view, args=(), kwargs={})
        with patch("bloom_nofos.word_export.resolve", return_value=match):
            result = render_export_html(
                self.request(),
                "https://testserver/export?policy_stripped=1",
                "#download_target",
            )
        self.assertEqual(seen, ["1"])
        self.assertIn("Safe text", result)
        self.assertNotIn("secret", result)
        self.assertNotIn("private", result)

    def test_external_images_fail_instead_of_disappearing(self):
        match = SimpleNamespace(
            url_name="nofo_export",
            args=(),
            kwargs={},
            func=lambda request: HttpResponse(
                '<div id="download_target">Content<img src="https://example.org/private.png"></div>'
            ),
        )
        with patch(
            "bloom_nofos.word_export.resolve", return_value=match
        ), self.assertRaises(ExportError):
            render_export_html(
                self.request(), "https://testserver/export", "#download_target"
            )

    def test_busy_is_retryable(self):
        with conversion_slot(), conversion_slot():
            response = pandoc_download_response(
                self.request(), "https://testserver/export", "#download_target", "test"
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response["Retry-After"], "5")

    def test_anonymous_is_denied(self):
        request = self.request()
        request.user.is_authenticated = False
        self.assertEqual(
            pandoc_download_response(
                request, "https://testserver/export", "#download_target", "test"
            ).status_code,
            403,
        )
