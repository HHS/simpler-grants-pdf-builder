"""Synthetic third Contents prototype: aligned entry and single-column fallback.

No automatic oversized-step detection is claimed. The roomy mode is an explicit
whole-Contents fallback, retaining the original list rather than reconstructing it.
"""

import argparse
import json

import columns_followup as previous
from bs4 import BeautifulSoup

OUT = previous.HERE / "generated" / "fallback"
SAMPLES = previous.base.SAMPLES
MODES = ("columns", "roomy")
CSS = """
@media print {
  .toc > ol > li.toc--before-you-begin { padding-left: 0; }
  .toc > ol > li.toc--before-you-begin > a { width: calc(50% - 5mm); }
}
"""
ROOMY = """
@media print {
  .toc { page: roomy-contents; }
  .toc > ol { columns: auto; }
  .toc > ol > li.toc--before-you-begin > a { width: 100%; }
  .toc .toc--section-name--a { string-set: contents-step content(); }
  .toc .toc--subsection-name { string-set: contents-step attr(data-probe-step); }
  .toc > ol > .toc--no-icon:not(.toc--before-you-begin) > a {
    string-set: contents-step content();
  }
  @page roomy-contents {
    @top-left {
      content: "Contents: " string(contents-step, first);
      font-size: 11pt;
      font-family: sans-serif;
      -prince-pdf-tag-type: Artifact;
    }
  }
  @page roomy-contents:first { @top-left { content: "Contents"; } }
}
"""


def page(sample="fy27", theme="ihs", mode="columns"):
    soup = BeautifulSoup(previous.page(sample, theme, "columns"), "html.parser")
    soup.title.string = f"Contents fallback: {sample} / {theme} / {mode}"
    soup.select_one(".probe-label").string = (
        f"Synthetic prototype: {sample} / {theme} / {mode}. "
        "Explicit layout choice, not automatic detection or a product change."
    )
    style = soup.new_tag("style")
    style.string = CSS + (ROOMY if mode == "roomy" else "")
    soup.head.append(style)
    if mode == "roomy":
        for step in soup.select(".toc > ol > li"):
            heading = step.select_one(".toc--section-name--a")
            if heading:
                for child in step.select(".toc--subsection-name"):
                    child["data-probe-step"] = heading.get_text(" ", strip=True)
    return str(soup)


def check():
    count = 0
    for sample in SAMPLES:
        for theme in previous.base.THEMES:
            before = BeautifulSoup(previous.page(sample, theme), "html.parser")
            for mode in MODES:
                soup = BeautifulSoup(page(sample, theme, mode), "html.parser")
                comparable = BeautifulSoup(str(soup.select_one(".toc")), "html.parser")
                for child in comparable.select("[data-probe-step]"):
                    assert child["data-probe-step"] == child.find_parent(
                        "li", class_="toc--section-name"
                    ).select_one(".toc--section-name--a").get_text(" ", strip=True)
                    del child["data-probe-step"]
                assert str(comparable.select_one(".toc")) == str(
                    before.select_one(".toc")
                )
                assert (
                    soup.select_one(".toc--before-you-begin a").get_text()
                    == "Before you get started"
                )
                assert [
                    (a["href"], a.get_text(" ", strip=True))
                    for a in soup.select(".toc a")
                ] == previous.expected(sample)
                assert not soup.select("script, form, .probe-continued, .probe-table")
                count += 1
    print(f"checks: {count}\nstatus: passed")


def verify():
    from pdf_followup import inspect
    from pypdf import PdfReader

    paths = sorted(OUT.glob("*.pdf"))
    assert paths, "Generate the documented PDF fixtures first"
    results = [inspect(path) for path in paths]
    for result in results:
        assert result["tag_types"]["/TOCI"] == result["links"]
        assert result["tag_types"]["/TOC"] == 7
        reader = PdfReader(OUT / result["file"])
        sample = result["file"].split("-")[0]
        locations = {}
        for page_number in result["contents_pages"]:
            for item in reader.pages[page_number - 1]["/Annots"]:
                item = item.get_object()
                label = str(item.get("/Contents", ""))
                if item.get("/Dest"):
                    locations.setdefault(label, []).append(
                        (page_number, list(map(float, item["/Rect"])))
                    )
        if result["mode"] == "roomy":
            parents = {}
            # Observe actual group fragmentation, not a guessed count threshold.
            for step in previous.base.fixture(sample).sections:
                labels = [step.name] + [
                    sub.name for sub in step.subsections if sub.tag == "h3"
                ]
                if "contacts" in step.name.lower():
                    labels = labels[:1]
                parents.update({label: step.name for label in labels})
                step_pages = sorted(
                    {p for label in labels for p, _ in locations[label]}
                )
                if len(step_pages) > 1:
                    for p in step_pages[1:]:
                        assert "Contents: " + step.name in " ".join(
                            reader.pages[p - 1].extract_text().split()
                        ), "Missing continuing-step page context"
            # Inspect the emitted marked-content sequence, not just requested
            # CSS: only the redundant running label may be an artifact.
            for p in result["contents_pages"][1:]:
                top_label = max(
                    (
                        (rect[3], label)
                        for label, rows in locations.items()
                        if label in parents
                        for number, rect in rows
                        if number == p
                    )
                )[1]
                assert "Contents: " + parents[top_label] in " ".join(
                    reader.pages[p - 1].extract_text().split()
                ), "Running label does not match first listed step"
                stack, header_artifacts = [], []

                def operand(op, args, cm, tm):
                    if op in (b"BMC", b"BDC"):
                        stack.append(str(args[0]))
                    elif op == b"EMC" and stack:
                        stack.pop()

                def text(value, cm, tm, font, size):
                    if "Contents: " in value:
                        header_artifacts.append("/Artifact" in stack)

                reader.pages[p - 1].extract_text(
                    visitor_operand_before=operand, visitor_text=text
                )
                assert header_artifacts and all(
                    header_artifacts
                ), "Running step context is not an artifact"
            result["continuation_context_verified"] = True
            result["running_headers_marked_artifact"] = True
        else:
            intro = locations["Before you get started"]
            first = locations[previous.base.STEPS[0]]
            assert (
                abs(max(r[2] for _, r in intro) - max(r[2] for _, r in first)) < 1
            ), "Introduction counter not aligned with left column"
            midpoint = float(reader.pages[0].mediabox.width) / 2
            tops = {"left": [], "right": []}
            for name in previous.base.STEPS:
                for p, rect in locations.get(name, []):
                    if p == 1:
                        tops["left" if rect[0] < midpoint else "right"].append(rect[3])
            assert tops["left"] and tops["right"]
            assert (
                abs(max(tops["left"]) - max(tops["right"])) < 1
            ), "First step headings are not aligned"
            assert min(r[1] for _, r in intro) > max(
                tops["left"]
            ), "Introduction is not above the steps"
            result["intro_aligned_left"] = True
    (OUT / "checks.json").write_text(json.dumps(results, indent=2) + "\n")
    print(
        f"pdfs: {len(results)}\nlinks: {sum(row['links'] for row in results)}\nstatus: passed"
    )


def main():
    class Parser(argparse.ArgumentParser):
        def error(self, message):
            print("error: " + json.dumps(message))
            print(
                "help: check|generate|pdf|verify; flags --sample, --theme, --mode, --help, --version"
            )
            raise SystemExit(2)

    parser = Parser(description=__doc__)
    parser.add_argument("-v", "-V", "--version", action="version", version="0.3.0")
    parser.add_argument(
        "command",
        nargs="?",
        default="check",
        choices=("check", "generate", "pdf", "verify"),
    )
    parser.add_argument("--sample", choices=SAMPLES, default="fy27")
    parser.add_argument("--theme", choices=previous.base.THEMES, default="ihs")
    parser.add_argument("--mode", choices=MODES, default="columns")
    args = parser.parse_args()
    try:
        if args.command == "check":
            check()
        elif args.command == "verify":
            verify()
        else:
            previous.generate(
                args.sample,
                args.theme,
                args.mode,
                args.command == "pdf",
                content=page(args.sample, args.theme, args.mode),
                output=OUT,
            )
    except Exception:
        print(
            "error: prototype failed\nhelp: use the locked Builder environment and generate the documented fixtures before verify; provider payloads are not logged"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
