"""Processing must work outside the web application, including its dependencies."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, override_settings

from nofos import content_processing, document_processing
from nofos.nofo import process_nofo_html, resolve_section_heading_level


class IsolatedContentProcessingTests(SimpleTestCase):
    def test_fresh_runtime_blocks_application_imports_network_and_writes(self):
        program = r"""
import importlib.abc
import os
import sys

assert "DJANGO_SETTINGS_MODULE" not in os.environ
forbidden = (
    "django", "bloom_nofos", "constance", "easyaudit", "mammoth",
    "boto3", "botocore", "requests", "nofos.models", "nofos.nofo",
    "nofos.utils", "nofos.views", "nofos.document_processing",
    "nofos.import_transforms",
)

class BlockApplicationImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == name or fullname.startswith(name + ".") for name in forbidden):
            raise AssertionError("Forbidden processing dependency: " + fullname)

sys.meta_path.insert(0, BlockApplicationImports())

def guard(event, args):
    if event == "open":
        mode, flags = args[1], args[2]
        if (mode and any(letter in mode for letter in "wax+")) or (
            flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        ):
            raise AssertionError("Processing attempted a file write")
    if event in {
        "socket.connect", "socket.getaddrinfo", "urllib.Request", "subprocess.Popen",
        "os.mkdir", "os.remove", "os.rename", "os.rmdir", "os.link", "os.symlink",
    }:
        raise AssertionError("Processing attempted a side effect: " + event)

sys.addaudithook(guard)
from nofos.content_processing import (
    AmbiguousHeadingHierarchyError, ContentProcessingError, process_document_content,
)

html = (
    '<style>@import url("https://example.invalid/not-fetched.css");'
    '.bold {font-weight:700; font-size:12pt}</style>'
    '<p>Opdiv: CDC</p><p>Opportunity number: SYNTHETIC-001</p>'
    '<h1 id="intro">Before you get started</h1><p>Source instructions.</p>'
    '<div><h1>Step 1: Review the opportunity</h1><h2>Basic information</h2></div>'
    '<h3>Tagline</h3><p>Apply today.</p>'
    '<h2>Summary</h2><p class="bold">Applicant prose [1].</p>'
    '<p>de minimis <a href="#intro">Registration</a></p>'
    '<img src="synthetic.png"><ol><li id="target">Item</li></ol>'
    '<p><a href="#target">Read item</a></p>'
    '<table><caption>Funding</caption><tr><td>Program</td><td>Amount</td></tr>'
    '<tr><td>Training</td><td>0</td></tr></table>'
    '<table><tr><td><h4>Application due date</h4><p>October 30</p></td></tr></table>'
    '<h1>Endnotes</h1><p>[1] Source.</p>'
    '<h1>Metadata</h1><p>Opdiv: CDC</p><p>Opportunity number: SYNTHETIC-001</p>'
    '<h1>Appendix</h1><p>Keep appendix.</p>'
)
result = process_document_content(html, builder_import=True, extract_scoped_tagline=True)
assert result.imported_tagline == "Apply today."
assert result.soup.body["data-nofo-introductory-family"] == "get_started"
assert result.soup.find("a", href="#section--before-you-begin")
assert result.soup.find("strong")
assert result.soup.find("em", string="de minimis")
assert result.soup.find("a", href="#endnote-manual-1")
assert result.soup.img.has_attr("data-nofo-missing-alt-text")
assert result.soup.find("a", id="target")
assert result.soup.find("caption", string="Funding")
assert "Metadata" not in [section["name"] for section in result.sections]
assert "Keep appendix." in str(result.sections)
assert "Application due date" in str(result.sections)

# Existing ACF-specific repair remains available without metadata defaults or ORM.
from nofos.content_processing import repair_acf_required_alignment_lists
from bs4 import BeautifulSoup
acf = BeautifulSoup(
    '<p>Opportunity Number: HHS-ACF-001</p><h1>Step 1: Review the opportunity</h1>'
    '<h2>Agency priorities</h2><p>Ordinary priorities remain unchanged.</p>', "html.parser"
)
before = str(acf)
repair_acf_required_alignment_lists(acf)
assert str(acf) == before

try:
    process_document_content('<h2>Earlier</h2><h1>Later</h1>')
except AmbiguousHeadingHierarchyError as error:
    assert error.code == "ambiguous_heading_hierarchy"
    assert error.h2_text == "Earlier" and error.h1_text == "Later"
else:
    raise AssertionError("Ambiguous hierarchy accepted")
try:
    process_document_content('<p>No sections</p>')
except ContentProcessingError as error:
    assert error.code == "no_sections"
else:
    raise AssertionError("Missing sections accepted")
assert not any(
    name == blocked or name.startswith(blocked + ".")
    for name in sys.modules for blocked in forbidden
)
print("isolated content processing passed")
"""
        result = subprocess.run(
            [sys.executable, "-B", "-c", program],
            cwd=Path(__file__).resolve().parents[2],
            env={"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("isolated content processing passed", result.stdout)

    def test_core_errors_are_translated_with_existing_fields(self):
        with self.assertRaises(ValidationError) as caught:
            resolve_section_heading_level(
                BeautifulSoup("<h2>Earlier</h2><h1>Later</h1>", "html.parser")
            )
        self.assertEqual(caught.exception.code, "ambiguous_heading_hierarchy")
        self.assertEqual(caught.exception.h2_text, "Earlier")
        self.assertEqual(caught.exception.h1_text, "Later")

    @override_settings(DEBUG=False)
    def test_application_callback_exception_retains_identity(self):
        failure = ValidationError("Consumer failure", code="consumer_failure")

        def parser(soup, level):
            raise failure

        with self.assertRaises(ValidationError) as caught:
            document_processing.process_document_content(
                "<h1>Opportunity</h1>", section_parser=parser
            )
        self.assertIs(caught.exception, failure)

    @override_settings(DEBUG=True)
    def test_application_debug_capture_stays_before_instruction_removal(self):
        captures = []
        html = (
            "<h1>Opportunity</h1><h2>Summary</h2>"
            "<table><tr><td>Instructions for NOFO writers: synthetic</td></tr></table>"
            "<p>Applicant prose.</p>"
        )

        def capture(soup):
            captures.append(str(soup))

        with (
            patch("nofos.document_processing.capture_debug_soup", side_effect=capture),
            patch("nofos.nofo.capture_debug_soup", side_effect=capture),
        ):
            result = document_processing.process_document_content(html)
            process_nofo_html(BeautifulSoup(html, "html.parser"), "h1")
        self.assertEqual(len(captures), 2)
        self.assertEqual(captures[0], captures[1])
        self.assertIn("Instructions for NOFO writers", captures[0])
        self.assertNotIn("Instructions for NOFO writers", str(result.soup))
        self.assertTrue(result.instructions_tables)

    def test_css_import_is_not_part_of_local_bold_class_selection(self):
        # Existing selection examines only top-level rules, not imported sheets.
        styles = '@import url("https://example.invalid/remote.css"); .local {font-weight:700}'
        from nofos.content_processing import _get_classnames_for_font_weight_bold

        self.assertEqual(_get_classnames_for_font_weight_bold(styles), {"local"})
