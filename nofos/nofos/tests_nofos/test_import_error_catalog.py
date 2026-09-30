"""
Guardrails for the import error catalog (see #913).

The point of these tests is that a new import error code cannot ship without
the two things that make it useful: real copy for the person who hit it, and a
row in documentation/IMPORT_ERROR_CODES.md for the person supporting them.
"""

import re
from pathlib import Path

from bloom_nofos.import_errors import IMPORT_ERROR_CATALOG
from django.conf import settings
from django.test import TestCase

VIEWS_PATH = Path(settings.BASE_DIR) / "nofos" / "views.py"
DOCS_PATH = Path(settings.BASE_DIR).parent / "documentation" / "IMPORT_ERROR_CODES.md"

# Codes belonging to NOFO Builder's own import flow. Composer and Compare
# import different kinds of document and namespace their codes separately
# (COMPOSER-*, COMPARE-*); they are out of this catalog's scope.
CODE_PATTERN = re.compile(r'error_code="((?:RE)?IMPORT-[A-Z-]+)"')

# Copy that says nothing. A summary or step matching one of these means the
# code regressed to "it didn't work", which is the thing #913 set out to fix.
# The only placeholder any call site fills, for REIMPORT-STATUS-BLOCKED.
ALLOWED_SUMMARY_PLACEHOLDERS = {"status"}

EMPTY_PHRASES = (
    "an error occurred",
    "something went wrong.",
    "please try again.",
    "invalid document",
)


class ImportErrorCatalogTests(TestCase):
    def test_every_logged_code_has_a_catalog_entry(self):
        """
        Any code the import views record is a code a user can be shown and can
        quote to support, so it needs an entry with real copy behind it.
        """
        logged_codes = set(CODE_PATTERN.findall(VIEWS_PATH.read_text()))

        self.assertTrue(
            logged_codes, "Found no import error codes in views.py - check CODE_PATTERN"
        )
        self.assertEqual(
            logged_codes - set(IMPORT_ERROR_CATALOG),
            set(),
            "These codes are logged but missing from IMPORT_ERROR_CATALOG. Add an "
            "entry (title, summary, recovery steps, when, support) for each.",
        )

    def test_every_catalog_entry_is_documented(self):
        """
        documentation/IMPORT_ERROR_CODES.md is what support works from, so it
        has to cover every code we can actually show someone.
        """
        documented = DOCS_PATH.read_text()

        for code in IMPORT_ERROR_CATALOG:
            with self.subTest(code=code):
                self.assertIn(
                    code,
                    documented,
                    f"{code} is in the catalog but not in IMPORT_ERROR_CODES.md",
                )

    def test_documentation_has_no_codes_the_catalog_dropped(self):
        """The reverse drift: a code documented but no longer real."""
        # Only the per-code section headings count, so prose that mentions a
        # code shape (or another document's IMPORT-NNN rule IDs) doesn't
        # register as a code claim.
        documented_codes = set(
            re.findall(
                r"^### `((?:RE)?IMPORT-[A-Z-]+)`$",
                DOCS_PATH.read_text(),
                re.MULTILINE,
            )
        )

        self.assertEqual(
            documented_codes - set(IMPORT_ERROR_CATALOG),
            set(),
            "These codes are documented but no longer in the catalog. Remove "
            "them from IMPORT_ERROR_CODES.md or add them back.",
        )

    def test_every_entry_is_complete(self):
        for code, entry in IMPORT_ERROR_CATALOG.items():
            with self.subTest(code=code):
                for field in ("title", "summary", "when", "support"):
                    self.assertTrue(
                        entry.get(field, "").strip(),
                        f"{code} has no {field}",
                    )
                self.assertTrue(
                    entry.get("recovery_steps"),
                    f"{code} has no recovery steps - every error tells the user "
                    "what to do next, even if that is who to ask",
                )
                self.assertIsInstance(entry.get("status"), int)

    def test_no_entry_falls_back_to_empty_copy(self):
        for code, entry in IMPORT_ERROR_CATALOG.items():
            with self.subTest(code=code):
                text = " ".join(
                    [entry["title"], entry["summary"], *entry["recovery_steps"]]
                ).lower()
                for phrase in EMPTY_PHRASES:
                    self.assertNotIn(
                        phrase,
                        text,
                        f"{code} uses filler copy ({phrase!r}). Say what happened "
                        "to this document and what to do about it.",
                    )

    def test_summaries_have_no_stray_placeholders(self):
        """
        Summaries are run through str.format() when a call site passes context.
        A stray brace would either crash or print literally, so the only
        placeholder allowed is one we know a caller fills.
        """
        for code, entry in IMPORT_ERROR_CATALOG.items():
            with self.subTest(code=code):
                placeholders = set(re.findall(r"{(\w*)}", entry["summary"]))
                self.assertLessEqual(
                    placeholders,
                    ALLOWED_SUMMARY_PLACEHOLDERS,
                    f"{code}'s summary uses a placeholder nothing fills",
                )
