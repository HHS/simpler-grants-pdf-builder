"""Offline, invented-input evidence for #1197, not a rendering or inventory service.

Run directly with Builder's locked Python environment. No project settings,
database, credentials, private inputs or network requests are used.
"""

import html
import re
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from bs4 import BeautifulSoup
from django.conf import settings
from django.template import Context, Engine

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "nofos"))
STATIC = ROOT / "nofos/bloom_nofos/static"
TEMPLATES = ROOT / "nofos/bloom_nofos/templates"
if not settings.configured:
    settings.configure(STATIC_URL="/static/", INSTALLED_APPS=[], SECRET_KEY="invented")


def render_callout():
    names = (
        "callout_box_contents",
        "add_classes_to_tables",
        "is_floating_callout_box",
        "add_classes_to_headings",
        "safe_br",
    )
    libraries = {name: "nofos.templatetags." + name for name in names}
    libraries.update(
        static="django.templatetags.static", martortags="martor.templatetags.martortags"
    )
    engine = Engine(dirs=[str(TEMPLATES)], libraries=libraries)
    return engine.get_template("includes/callout_box.html").render(
        Context(
            {
                "subsection": SimpleNamespace(
                    name="Invented application notice",
                    html_id="invented-notice",
                    html_class="",
                    tag="h3",
                    body="Read the [invented instructions](#invented-instructions).",
                ),
                "nofo": SimpleNamespace(icon_style="nofo--icons--border"),
                "break_colons": False,
            }
        )
    )


def radius(css):
    """Read one exact selector/declaration, not implement the CSS cascade.

    Restrict the example to plain .callout-box rules and border-radius. A full
    stylesheet, specificity, media or !important analysis is outside this probe.
    """
    values = re.findall(
        r"(?m)^\.callout-box\s*\{[^}]*?border-radius:\s*(\d+px)\s*;", css
    )
    return values[-1] if values else None


def example():
    original = (STATIC / "theme-base.css").read_text()
    needle = ".callout-box {\n  border-radius: 10px;"
    assert original.count(needle) == 1, "Reassess example after shared CSS changes"
    changed = original.replace(needle, ".callout-box {\n  border-radius: 12px;")
    rows = []
    for label, theme, custom in (
        ("current", "portrait-hrsa-white", ""),
        ("exception", "portrait-hrsa-white", ".callout-box { border-radius: 2px; }"),
        ("older-stored", "portrait-hrsa-blue", ""),
    ):
        orientation, opdiv, colour = theme.split("-")
        other_layers = [
            (STATIC / filename).read_text()
            for filename in (
                "shared.css",
                f"theme-orientation-{orientation}.css",
                f"theme-opdiv-{opdiv}.css",
                f"theme-opdiv-{opdiv}-{colour}.css",
            )
        ]
        # For these particular layers, the exact selector has no radius change.
        assert not any(radius(layer) for layer in other_layers)
        rows.append(
            {
                "case": label,
                "theme": theme,
                "before": radius(custom) or radius(original),
                "after": radius(custom) or radius(changed),
                "html": render_callout(),
                "custom": custom,
            }
        )
    return rows


def html_example(case, phase):
    """Emit a local fragment page for optional browser checks, never a PDF."""
    row = next(row for row in example() if row["case"] == case)
    orientation, opdiv, colour = row["theme"].split("-")
    filenames = (
        "uswds/uswds.css",
        "shared.css",
        "theme-base.css",
        f"theme-orientation-{orientation}.css",
        f"theme-opdiv-{opdiv}.css",
        f"theme-opdiv-{opdiv}-{colour}.css",
    )
    css = []
    for filename in filenames:
        text = (STATIC / filename).read_text()
        if phase == "after" and filename == "theme-base.css":
            text = text.replace(
                ".callout-box {\n  border-radius: 10px;",
                ".callout-box {\n  border-radius: 12px;",
            )
        css.append(text)
    css.append(row["custom"])
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        f"<title>Invented {html.escape(case)}: {html.escape(phase)}</title>"
        "<style>" + "\n".join(css) + "</style>"
        f'<body class="{row["theme"]} {orientation} {opdiv} {opdiv}-{colour}">'
        "<p>Synthetic callout fragment only. External font loading omitted. "
        "Not a complete Builder document or PDF.</p>" + row["html"] + "</body></html>"
    )


class ExampleChecks(unittest.TestCase):
    def test_shared_change_and_exception(self):
        rows = example()
        self.assertEqual(
            [(r["case"], r["before"], r["after"]) for r in rows],
            [
                ("current", "10px", "12px"),
                ("exception", "2px", "2px"),
                ("older-stored", "10px", "12px"),
            ],
        )

    def test_real_template_preserves_meaning(self):
        for row in example():
            with self.subTest(case=row["case"]):
                soup = BeautifulSoup(row["html"], "html.parser")
                self.assertIsNotNone(soup.select_one(".callout-box"))
                heading = soup.select_one("h3#invented-notice")
                self.assertEqual(heading.get_text(), "Invented application notice")
                self.assertEqual(soup.select_one("a")["href"], "#invented-instructions")
                self.assertIn("Read the invented instructions.", soup.get_text())

    def test_stylesheet_order_matches_current_document_template(self):
        source = (ROOT / "nofos/nofos/templates/nofos/nofo_view.html").read_text()
        positions = [
            source.index(marker)
            for marker in (
                '"theme-orientation-"',
                '"theme-opdiv-"|add:nofo_opdiv',
                '"theme-opdiv-"|add:nofo_theme_base',
                "{{ nofo.inline_css|safe }}",
            )
        ]
        self.assertEqual(positions, sorted(positions))

    def test_old_theme_is_retired_but_available_in_source(self):
        source = (ROOT / "nofos/nofos/models.py").read_text()
        self.assertIn('"portrait-hrsa-blue": "HRSA (Default, legacy)"', source)
        self.assertTrue((STATIC / "theme-opdiv-hrsa-blue.css").is_file())


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--html":
        case, phase = sys.argv[2:]
        if case not in {"current", "exception", "older-stored"} or phase not in {
            "before",
            "after",
        }:
            raise SystemExit("Use --html current|exception|older-stored before|after")
        print(html_example(case, phase))
    else:
        unittest.main(verbosity=2)
