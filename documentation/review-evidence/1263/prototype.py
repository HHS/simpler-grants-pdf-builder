"""Synthetic Contents design probe; never loads settings, a DB or user files.

Reuses the actual Contents template, icon includes, density filter and CSS.
Nothing here changes application behavior. The optional pdf command submits only
these invented fixtures and repository assets to DocRaptor's public test account.
"""

import argparse
import base64
import html
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
STATIC = ROOT / "nofos/bloom_nofos/static"
OUT = Path(__file__).resolve().parent / "generated"
sys.path.insert(0, str(ROOT / "nofos"))

MODES = ("baseline", "compact", "columns", "inline")
SAMPLES = ("sparse", "fy27", "long", "overflow")
THEMES = ("ihs", "hrsa", "cdc")
STEPS = (
    "Step 1: Review the opportunity",
    "Step 2: Get ready to apply",
    "Step 3: Prepare your application",
    "Step 4: Learn about review and award",
    "Step 5: Submit your application",
    "Step 6: Learn what happens after the award",
    "Contacts and support",
)
LABELS = (
    (
        "Basic information",
        "Eligibility",
        "Program description",
    ),
    (
        "Get registered",
        "Find the application package",
        "Join the webinar",
        "Submit your {choose between: required or optional} letter of intent",
    ),
    (
        "Application contents and format",
        "Project narrative",
        "Budget and budget narrative",
        "Attachments",
        "Other required forms",
        "Application checklist",
    ),
    (
        "Review criteria",
        "Review and selection process",
        "Risk review",
        "Award notices",
        "Award administration",
    ),
    ("Application submission", "Other submissions"),
    ("Administrative requirements",),
    (),
)

# Rebalance space around complete step groups; keep existing font sizes and
# nested-list structure. These rules are only applied to generated prototypes.
COMPACT = """
.toc > ol > li { padding-bottom: 5px; margin-bottom: 5px; }
.toc .toc--section-name--wrapper { margin-top: 0; }
.toc .toc--section-name--img, .toc .toc--section-name--img svg {
  width: 24px; height: 24px;
}
.toc a { box-sizing: border-box; padding-right: 2.5em; }
.toc > ol > li { break-inside: avoid; }
.toc li a { break-inside: avoid; }
"""
COLUMNS = COMPACT + """
@media print {
  .toc > ol { columns: 2; column-gap: 10mm; }
  .toc > ol > li { break-inside: avoid; }
}
"""
INLINE = COMPACT + """
@media print {
  .toc .toc--section-name--wrapper > ol { margin-top: 4.5px; }
  .toc .toc--subsection-name { display: inline; }
  .toc .toc--subsection-name a {
    display: inline; width: auto; padding-right: 0;
  }
  .toc .toc--subsection-name a::after {
    position: static; content: " (" target-counter(attr(href, url), page) ")";
  }
  .toc .toc--subsection-name:not(:last-child)::after { content: "; "; }
}
"""


class Rows(list):
    def all(self):
        return self

    def order_by(self, name):
        return Rows(sorted(self, key=lambda row: getattr(row, name)))


def fixture(sample):
    sections = Rows()
    # Invented content; only the issue's explicitly quoted heading labels are
    # reused. This is not the IHS draft or authoritative master template.
    for index, (name, labels) in enumerate(zip(STEPS, LABELS), 1):
        if sample == "sparse":
            labels = labels[:1]
        if sample == "long":
            labels = tuple(
                label + " for participating organizations and their partners"
                for label in labels
            )
        if sample == "overflow" and index == 3:
            labels = tuple(
                f"Required attachment {n}: information for participating organizations"
                for n in range(1, 39)
            )
        sections.append(
            SimpleNamespace(
                name=name,
                order=index,
                html_id=f"step-{index}",
                has_section_page=True,
                is_introduction=False,
                subsections=Rows(
                    SimpleNamespace(
                        name=label, order=n, tag="h3", html_id=f"step-{index}-item-{n}"
                    )
                    for n, label in enumerate(labels, 1)
                ),
            )
        )
    if sample != "fy27":
        sections.append(
            SimpleNamespace(
                name="Appendix: Reference information",
                order=8,
                html_id="appendix-reference",
                has_section_page=False,
                is_introduction=False,
                subsections=Rows(),
            )
        )
    return SimpleNamespace(
        sections=sections,
        has_imported_introduction=False,
        number="SYNTHETIC-1263",
        before_you_begin="full",
        introductory_page_family="get_started",
        introductory_page_title="Before you get started",
        icon_style="nofo--icons--border",
    )


def toc(sample):
    from django.conf import settings
    from django.template import Context, Engine

    if not settings.configured:
        settings.configure(
            STATIC_URL="/static/", INSTALLED_APPS=[], SECRET_KEY="synthetic-only"
        )
    source = (ROOT / "nofos/nofos/templates/nofos/nofo_view.html").read_text()
    start = source.index("  <!-- TABLE OF CONTENTS -->")
    end = source.index("  <!-- BEFORE YOU BEGIN PAGE -->", start)
    engine = Engine(
        dirs=[str(ROOT / "nofos/bloom_nofos/templates")],
        libraries={
            "add_classes_to_toc": "nofos.templatetags.add_classes_to_toc",
            "safe_br": "nofos.templatetags.safe_br",
        },
    )
    template = engine.from_string(
        "{% load add_classes_to_toc safe_br %}" + source[start:end]
    )
    return template.render(Context({"nofo": fixture(sample)}))


def inline_assets(css):
    def asset(match):
        raw = match.group(1).strip("\"'")
        if not raw.startswith("/static/"):
            return match.group(0)
        path = STATIC / raw.removeprefix("/static/")
        if not path.is_file():
            return match.group(0)
        mime = {
            ".woff2": "font/woff2",
            ".woff": "font/woff",
            ".svg": "image/svg+xml",
        }.get(path.suffix, "application/octet-stream")
        return (
            'url("data:'
            + mime
            + ";base64,"
            + base64.b64encode(path.read_bytes()).decode()
            + '")'
        )

    return re.sub(r"url\(([^)]+)\)", asset, css)


def page(mode, sample, theme):
    from bs4 import BeautifulSoup

    rendered = toc(sample)
    files = (
        "uswds/uswds.css",
        "shared.css",
        "theme-base.css",
        "theme-orientation-portrait.css",
        f"theme-opdiv-{theme}.css",
        f"theme-opdiv-{theme}-white.css",
    )
    css = "\n".join(inline_assets((STATIC / file).read_text()) for file in files)
    css += {"baseline": "", "compact": COMPACT, "columns": COLUMNS, "inline": INLINE}[
        mode
    ]
    css += """
/* Probe-only wrapper and synthetic destination pages, not product styles. */
@media screen {
  .probe-label { padding: 1rem; background: #edf1f3; }
  .grid-container { max-width: 216mm; }
  .toc { max-width: 100%; }
  .toc a { overflow-wrap: anywhere; }
  .toc a::after { content: none; }
  .toc a:focus-visible { outline: 3px solid #005ea2; outline-offset: 2px; }
}
@media print { .probe-label { display: none; } }
.probe-targets { page-break-before: always; }
.probe-targets h3 { font-size: 11pt; margin: 3px 0; }
.probe-targets p { margin: 0; font-size: 9pt; }
"""
    links = BeautifulSoup(rendered, "html.parser").select("a[href]")
    targets = '<section class="probe-targets"><h2>Synthetic destinations</h2><p>Invented navigation targets only, not a complete NOFO.</p>'
    for link in links:
        targets += (
            '<h3 id="'
            + html.escape(link["href"][1:])
            + '">'
            + html.escape(link.get_text(" ", strip=True))
            + "</h3>"
        )
    targets += "</section>"
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Synthetic Contents: {mode}, {sample}, {theme}</title><style>{css}</style></head>"
        f'<body class="portrait {theme} {theme}-white nofo--icons--border">'
        f'<p class="probe-label">Design prototype only: {mode} / {sample} / {theme}. Invented sample, not the IHS draft. PDF links lead to synthetic destinations.</p>'
        '<main class="grid-container">' + rendered + targets + "</main></body></html>"
    )


def check():
    from bs4 import BeautifulSoup

    count = 0
    expected_counts = {"sparse": 15, "fy27": 29, "long": 30, "overflow": 62}
    for sample in SAMPLES:
        expected_targets = ["#section--before-you-begin"]
        for section in fixture(sample).sections:
            expected_targets.append(
                "#" + section.html_id
                if section.has_section_page
                else "#section--" + section.html_id
            )
            if "contacts" not in section.name.lower():
                expected_targets.extend(
                    "#" + sub.html_id for sub in section.subsections
                )
        assert len(expected_targets) == expected_counts[sample]
        expected = None
        for mode in MODES:
            for theme in THEMES:
                soup = BeautifulSoup(page(mode, sample, theme), "html.parser")
                links = [
                    (a.get_text(" ", strip=True), a["href"])
                    for a in soup.select(".toc a[href]")
                ]
                assert (
                    len(links) == expected_counts[sample]
                ), "Missing navigation entries"
                assert [href for _, href in links] == expected_targets
                expected = expected or links
                assert links == expected, "A variant changed navigation"
                ids = [tag["id"] for tag in soup.select("[id]")]
                assert len(ids) == len(set(ids)), "Duplicate destination"
                assert all(ids.count(href[1:]) == 1 for _, href in links)
                assert not soup.select(
                    "script, form, input"
                ), "Unexpected active content"
                count += 1
    print(f"checks: {count} sample/mode/theme combinations passed")


def generate(sample, theme):
    OUT.mkdir(exist_ok=True)
    links = []
    for mode in MODES:
        name = f"{sample}-{theme}-{mode}.html"
        (OUT / name).write_text(page(mode, sample, theme))
        links.append(f'<li><a href="{name}">{sample} / {theme} / {mode}</a></li>')
    (OUT / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Contents prototypes #1263</title><h1>Contents prototypes #1263</h1><p>Synthetic local design comparison. No application changes.</p><ul>'
        + "".join(links)
        + "</ul></html>"
    )
    print(f"html_files: {len(links)}\noutput: {OUT}")


def verify_pdfs():
    from bs4 import BeautifulSoup
    from pypdf import PdfReader

    rows = []
    for path in sorted(OUT.glob("*.pdf")):
        sample, theme, mode = path.stem.split("-")
        if sample not in SAMPLES or theme not in THEMES or mode not in MODES:
            continue
        soup = BeautifulSoup(toc(sample), "html.parser")
        expected = {a.get_text(" ", strip=True) for a in soup.select("a")}
        reader = PdfReader(path)
        observed = set()
        contents_pages = set()
        for number, pdf_page in enumerate(reader.pages, 1):
            for item in pdf_page.get("/Annots", []):
                annotation = item.get_object()
                label = str(annotation.get("/Contents", ""))
                if label not in expected or "/Dest" not in annotation:
                    continue
                destination = annotation["/Dest"]
                target_page = reader.get_page_number(destination[0].get_object())
                target_text = " ".join(reader.pages[target_page].extract_text().split())
                assert label in target_text, "PDF destination lacks its label"
                observed.add(label)
                contents_pages.add(number)
        assert observed == expected, "PDF dropped navigation links"
        rows.append(
            {
                "file": path.name,
                "contents_pages": len(contents_pages),
                "total_pages": len(reader.pages),
                "distinct_link_labels": len(observed),
                "tag_tree_present": "/StructTreeRoot" in reader.trailer["/Root"],
                "producer": str(reader.metadata.producer),
            }
        )
    assert rows, "No generated PDFs to verify"
    (OUT / "pdf-checks.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(
        f"pdf_checks: {len(rows)} files retained all expected link labels and destination-page text"
    )
    print(
        "limits: not a tagged-reading-order, multi-digit page-number or accessibility-conformance check"
    )


def pdf(sample, theme, selected_mode):
    import docraptor

    OUT.mkdir(exist_ok=True)
    client = docraptor.DocApi()
    client.api_client.configuration.username = "YOUR_API_KEY_HERE"
    client.api_client.configuration.debug = False
    for mode in MODES if selected_mode == "all" else (selected_mode,):
        content = page(mode, sample, theme)
        try:
            result = client.create_doc(
                {
                    "test": True,
                    "document_type": "pdf",
                    "document_content": content,
                    "javascript": False,
                    "pipeline": 11,
                    "prince_options": {"media": "print", "profile": "PDF/UA-1"},
                }
            )
        except Exception:
            print(
                f"error: PDF generation failed for {mode}; no provider payload logged"
            )
            return 1
        target = OUT / f"{sample}-{theme}-{mode}.pdf"
        target.write_bytes(result)
        print(f"pdf: {target.name}", flush=True)
    return 0


def main():
    class ProbeParser(argparse.ArgumentParser):
        def error(self, message):
            print("error: " + json.dumps(message))
            print(
                "help: use check, generate, pdf or verify; valid options are --sample, --theme, --mode, --help and --version"
            )
            raise SystemExit(2)

    parser = ProbeParser(
        description="Invented-input Contents design probe. Default: offline checks only."
    )
    parser.add_argument("-v", "-V", "--version", action="version", version="0.1.0")
    parser.add_argument(
        "command",
        nargs="?",
        default="check",
        choices=("check", "generate", "pdf", "verify"),
    )
    parser.add_argument("--sample", choices=SAMPLES, default="fy27")
    parser.add_argument("--theme", choices=THEMES, default="ihs")
    parser.add_argument("--mode", choices=("all", *MODES), default="all")
    args = parser.parse_args()
    try:
        if args.command == "check":
            check()
        elif args.command == "generate":
            generate(args.sample, args.theme)
        elif args.command == "verify":
            verify_pdfs()
        else:
            return pdf(args.sample, args.theme, args.mode)
    except Exception:
        print(
            "error: Prototype generation/check failed; use the documented locked Builder Python environment"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
