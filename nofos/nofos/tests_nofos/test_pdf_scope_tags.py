"""Producer-side tagging contract; actual Prince output needs render verification."""

import re
from pathlib import Path

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase


class PdfScopeTagTests(SimpleTestCase):
    def test_cover_and_contents_keep_semantic_tags(self):
        css = Path(finders.find("theme-base.css")).read_text()
        print_css = css.split("@media print", 1)[1]
        self.assertIn('"HHSNofoCover" Sect', print_css)
        self.assertIn('"HHSNofoContents" Sect', print_css)
        cover = re.search(r"\.nofo--cover-page\s*\{([^}]+)\}", print_css).group(1)
        self.assertIn('-prince-pdf-tag-type: "HHSNofoCover"', cover)
        self.assertNotIn("Artifact", cover)
        self.assertRegex(
            print_css,
            r'\.toc,\s*\.section--title-page--toc\s*\{\s*-prince-pdf-tag-type: "HHSNofoContents";',
        )
        self.assertRegex(
            print_css,
            r"\.toc ol,\s*\.section--title-page--toc ul\s*\{\s*-prince-pdf-tag-type: TOC;",
        )
        self.assertRegex(
            print_css,
            r"\.toc li,\s*\.section--title-page--toc li\s*\{\s*-prince-pdf-tag-type: TOCI;",
        )
