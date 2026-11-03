"""Read-only checks of synthetic PDFs; requires pypdf and Poppler pdftotext."""

import collections
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

# Handle metadata/usage before loading optional PDF dependencies.
if __name__ == "__main__" and len(sys.argv) > 1:
    if len(sys.argv) == 2 and sys.argv[1] in {"-v", "-V", "--version"}:
        print("0.2.0")
        raise SystemExit(0)
    if len(sys.argv) == 2 and sys.argv[1] in {"-h", "--help"}:
        print(
            "Check generated fixed Contents PDFs and save a JSON receipt. No arguments. Flags: --help, --version."
        )
        raise SystemExit(0)
    print(
        "error: no fixture arguments accepted\nhelp: run with no arguments; flags --help, --version"
    )
    raise SystemExit(2)

import columns_followup as probe
from pypdf import PdfReader


def structure(node, labels, types):
    if isinstance(node, list):
        for child in node:
            structure(child, labels, types)
        return
    if not hasattr(node, "get_object"):
        return
    node = node.get_object()
    if not hasattr(node, "get"):
        return
    if node.get("/S"):
        types[str(node["/S"])] += 1
    if node.get("/Type") == "/OBJR":
        annotation = node["/Obj"].get_object()
        if annotation.get("/Dest"):
            labels.append(str(annotation.get("/Contents", "")))
    if "/K" in node:
        structure(node["/K"], labels, types)


def inspect(path):
    sample, _, mode = path.stem.split("-")
    expected = [label for _, label in probe.expected(sample)]
    reader = PdfReader(path)
    bbox = subprocess.check_output(["pdftotext", "-bbox", str(path), "-"], timeout=30)
    pages = ET.fromstring(bbox).findall(".//{*}page")
    observed = set()
    contents_pages = set()
    printed_numbers = set()
    for index, page in enumerate(reader.pages):
        words = pages[index].findall(".//{*}word")
        for annotation in (
            page.get("/Annots", []).get_object() if page.get("/Annots") else []
        ):
            annotation = annotation.get_object()
            label = str(annotation.get("/Contents", ""))
            if label not in expected or "/Dest" not in annotation:
                continue
            target = reader.get_page_number(annotation["/Dest"][0].get_object())
            text = " ".join(reader.pages[target].extract_text().split())
            assert label in text, "Wrong target page"
            printed = re.search(r"Printed page: (\d+)", text).group(1)
            # Wrapped labels have several rectangles. Require the correct
            # numeric counter in at least one rectangle for each unique label.
            x1, y1, x2, y2 = map(float, annotation["/Rect"])
            height = float(page.mediabox.height)
            rect_words = [
                w.text
                for w in words
                if x1 - 1 <= (float(w.get("xMin")) + float(w.get("xMax"))) / 2 <= x2 + 1
                and abs(float(w.get("xMax")) - x2) <= 2
                and float(w.get("xMin")) >= x1 - 1
                and height - y2 - 1
                <= (float(w.get("yMin")) + float(w.get("yMax"))) / 2
                <= height - y1 + 1
            ]
            if printed in rect_words:
                printed_numbers.add(label)
            observed.add(label)
            contents_pages.add(index + 1)
    assert observed == set(expected), "Missing PDF link labels"
    assert printed_numbers == set(expected), "Missing or wrong printed page number"
    order, types = [], collections.Counter()
    structure(reader.trailer["/Root"]["/StructTreeRoot"], order, types)
    # One logical OBJR per link is expected, even when the visible link wraps.
    assert order == expected, "Tagged link sequence differs from source"
    return {
        "file": path.name,
        "contents_pages": sorted(contents_pages),
        "links": len(expected),
        "correct_page_numbers": len(printed_numbers),
        "tagged_link_order": "matches source",
        "tag_types": dict(types),
        "continued_labels": sum(
            p.extract_text().count("(continued)") for p in reader.pages
        ),
        "mode": mode,
    }


def main():
    files = sorted(probe.OUT.glob("*.pdf"))
    assert files, "Generate the four documented PDF fixtures first"
    results = [inspect(path) for path in files]
    (probe.OUT / "pdf-followup-checks.json").write_text(
        json.dumps(results, indent=2) + "\n"
    )
    for result in results:
        print(
            f"file: {result['file']}\nlinks: {result['links']}\npage_numbers: {result['correct_page_numbers']}\ncontents_pages: {len(result['contents_pages'])}\ncontinued_labels: {result['continued_labels']}"
        )
    print(
        "status: passed\nlimits: structural checks, not screen-reader speech or WCAG conformance"
    )


if __name__ == "__main__":
    main()
