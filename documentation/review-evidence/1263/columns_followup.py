"""Second, synthetic-only Contents prototype. Never changes application files.

Reuses the first probe's fixture, real template and theme assets. A separate
caption experiment tests renderer continuation behavior, not production design.
"""

import argparse
import importlib.util
import json
from pathlib import Path

from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
OUT = HERE / "generated" / "followup"
spec = importlib.util.spec_from_file_location(
    "contents_comparison", HERE / "prototype.py"
)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
SAMPLES = (*base.SAMPLES, "wrapped_intro")
MODES = ("columns", "captions")

CSS = """
/* Probe-only. The application template and theme files remain unchanged. */
@media screen {
  .toc h2, .probe-targets h2 { overflow-wrap: anywhere; }
}
@media screen and (max-width: 40em) {
  section.toc { padding: 1rem; }
}
@media print {
  .toc > ol { columns: 2; column-gap: 10mm; }
  .toc > ol > .toc--before-you-begin {
    column-span: all; padding-left: 0; margin-top: 0; max-width: none; width: 100%;
  }
  .toc > ol > li { break-inside: avoid; }
  .toc .toc--section-name--wrapper { margin-top: 0; }
  .toc a { box-sizing: border-box; padding-right: 3em; }
  .toc .toc--subsection-name { break-inside: avoid; }
  .toc .toc--section-name--a { break-after: avoid; }
  .probe-targets { page: probe-target; }
  @page probe-target { counter-increment: page 17; }
  .probe-page-number::after { content: counter(page); }
}
.probe-page-number { font-size: 11pt; }
"""

CAPTIONS = """
@media screen { .probe-continued { display: none; } }
@media print {
  .toc > ol > .probe-table { display: table; table-layout: fixed; width: 100%; }
  .probe-table > .toc--section-name--img { display: none; }
  .probe-first, .probe-continued {
    display: table-caption; text-align: left; margin: 0 0 4.5px;
    font-size: 13pt; font-weight: 600; color: var(--color--black);
  }
  .probe-first { prince-caption-page: first; }
  .probe-continued { prince-caption-page: following; }
  .probe-table > ol { display: table-row-group; }
  .probe-table .toc--subsection-name { display: table-row; }
  .probe-table .toc--subsection-name > a {
    display: table-cell; padding-top: 4.5px;
  }
}
"""


def page(sample="fy27", theme="ihs", mode="columns"):
    """Retain labels and one destination per entry; no hard-coded column split."""
    original = "fy27" if sample == "wrapped_intro" else sample
    soup = BeautifulSoup(base.page("baseline", original, theme), "html.parser")
    soup.title.string = f"Contents follow-up: {sample} / {theme} / {mode}"
    soup.select_one(".probe-label").string = (
        f"Synthetic design prototype: {sample} / {theme} / {mode}. "
        "Not an approved master or an application change."
    )
    if sample == "wrapped_intro":
        # Deliberately invented wrapping stress text, not a renamed master label.
        label = "Before you get started: information for participating organizations and their partners"
        soup.select_one(".toc--before-you-begin a").string = label
        soup.select_one("#section--before-you-begin").string = label
    style = soup.new_tag("style")
    style.string = CSS + (CAPTIONS if mode == "captions" else "")
    soup.head.append(style)
    if mode == "captions":
        for step in soup.select(".toc > ol > li"):
            heading = step.select_one(".toc--section-name--a")
            if heading is None or not step.select(".toc--subsection-name"):
                continue
            step["class"].append("probe-table")
            first = soup.new_tag("div", attrs={"class": "probe-first"})
            first.append(heading.extract())
            continued = soup.new_tag("div", attrs={"class": "probe-continued"})
            continued.string = first.get_text(" ", strip=True) + " (continued)"
            # Intentionally NOT aria-hidden/artifact yet. Inspect resulting tags
            # before choosing a redundant-label treatment; no duplicate link.
            step.insert(0, first)
            step.insert(1, continued)
            wrapper = step.select_one(".toc--section-name--wrapper")
            step.append(wrapper.ol.extract())
            wrapper.decompose()
    # Vary actual target page numbers without sending a private document or
    # building a hundred-page fixture. Every target page increments by 17.
    target_container = soup.select_one(".probe-targets")
    headings = [heading.extract() for heading in target_container.select("h3")]
    target_container.decompose()
    for offset in range(0, len(headings), 7):
        target = soup.new_tag("section", attrs={"class": "probe-targets"})
        title = soup.new_tag("h2")
        title.string = "Synthetic destinations"
        target.append(title)
        for heading in headings[offset : offset + 7]:
            target.append(heading)
        number = soup.new_tag("p", attrs={"class": "probe-page-number"})
        number.string = "Printed page: "
        target.append(number)
        soup.main.append(target)
    return str(soup)


def expected(sample):
    original = "fy27" if sample == "wrapped_intro" else sample
    soup = BeautifulSoup(base.page("baseline", original, "ihs"), "html.parser")
    pairs = [(a["href"], a.get_text(" ", strip=True)) for a in soup.select(".toc a")]
    if sample == "wrapped_intro":
        pairs[0] = (
            pairs[0][0],
            "Before you get started: information for participating organizations and their partners",
        )
    return pairs


def check():
    count = 0
    for sample in SAMPLES:
        for theme in base.THEMES:
            for mode in MODES:
                soup = BeautifulSoup(page(sample, theme, mode), "html.parser")
                links = [
                    (a["href"], a.get_text(" ", strip=True))
                    for a in soup.select(".toc a")
                ]
                assert links == expected(sample), "Changed ordered labels/destinations"
                ids = [tag["id"] for tag in soup.select("[id]")]
                assert len(ids) == len(set(ids))
                assert all(ids.count(href[1:]) == 1 for href, _ in links)
                assert not soup.select("script, form, input")
                if mode == "captions":
                    for step in soup.select(".probe-table"):
                        assert step.select_one(".probe-continued").get_text() == (
                            step.select_one(".probe-first").get_text(" ", strip=True)
                            + " (continued)"
                        )
                        assert not step.select_one(".probe-continued").select("a")
                count += 1
    print(f"checks: {count}\nstatus: passed")


def generate(sample, theme, mode, render=False, *, content=None, output=None):
    output = OUT if output is None else output
    output.mkdir(parents=True, exist_ok=True)
    stem = f"{sample}-{theme}-{mode}"
    content = page(sample, theme, mode) if content is None else content
    (output / f"{stem}.html").write_text(content)
    if render:
        import docraptor

        client = docraptor.DocApi()
        client.api_client.configuration.username = "YOUR_API_KEY_HERE"
        client.api_client.configuration.debug = False
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
        (output / f"{stem}.pdf").write_bytes(result)
    print(f"output: {output / stem}\nstatus: generated")


def main():
    class Parser(argparse.ArgumentParser):
        def error(self, message):
            print("error: " + json.dumps(message))
            print(
                "help: commands check|generate|pdf; flags --sample, --theme, --mode, --help, --version"
            )
            raise SystemExit(2)

    parser = Parser(description=__doc__)
    parser.add_argument("-v", "-V", "--version", action="version", version="0.2.0")
    parser.add_argument(
        "command", nargs="?", default="check", choices=("check", "generate", "pdf")
    )
    parser.add_argument("--sample", choices=SAMPLES, default="fy27")
    parser.add_argument("--theme", choices=base.THEMES, default="ihs")
    parser.add_argument("--mode", choices=MODES, default="columns")
    args = parser.parse_args()
    try:
        if args.command == "check":
            check()
        else:
            generate(args.sample, args.theme, args.mode, args.command == "pdf")
    except Exception:
        print(
            "error: prototype failed\nhelp: use the locked Builder Python environment; provider payloads are not logged"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
