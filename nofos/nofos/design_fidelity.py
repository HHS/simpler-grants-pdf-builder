"""Bounded, offline evidence about converted content in filtered local HTML.

Not Word extraction validation or a complete fidelity/acceptance determination.
Exact matches deliberately avoid text-normalization waivers. Generated output
may contain extra elements; missing exact matches require reconciliation, not an
automatic claim that Builder has a defect.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup
from django.contrib.staticfiles import finders

MAX_HTML_BYTES = 4 * 1024 * 1024
MAX_ITEMS = 1000
MAX_ASSET_BYTES = 5 * 1024 * 1024
MAX_TOTAL_ASSET_BYTES = 16 * 1024 * 1024


def _signature(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _input_digest(*inputs):
    digest = hashlib.sha256()
    for value in inputs:
        if not isinstance(value, str):
            raise ValueError("Fidelity inspection requires stored HTML text")
        digest.update(len(value).to_bytes(8, "big"))
        for offset in range(0, len(value), 65536):
            digest.update(value[offset : offset + 65536].encode())
    return digest.hexdigest()


def inventory(html):
    if not isinstance(html, str) or len(html.encode()) > MAX_HTML_BYTES:
        raise ValueError("HTML evidence exceeds the bounded inspection size")
    soup = BeautifulSoup(html, "html.parser")
    if any(
        "list-style" in str(node.get("style", "")).lower()
        for node in soup.find_all(["ol", "li"])
    ):
        raise ValueError("CSS-driven list marker comparison is not supported")
    tables = []
    for table in soup.find_all("table"):
        if table.find("table"):
            raise ValueError("Nested table comparison is not supported")
        tables.append(
            _signature(
                [
                    [
                        (
                            cell.name,
                            cell.get_text(),
                            cell.get("rowspan", "1"),
                            cell.get("colspan", "1"),
                            cell.get("scope", ""),
                            cell.get("headers", []),
                            cell.get("id", ""),
                        )
                        for cell in row.find_all(["td", "th"], recursive=False)
                    ]
                    for row in table.find_all("tr")
                ]
            )
        )
    lists = [
        _signature(
            {
                "start": node.get("start", "1"),
                "type": node.get("type", "1"),
                "reversed": node.has_attr("reversed"),
                "items": [
                    (li.get("value", ""), li.get_text())
                    for li in node.find_all("li", recursive=False)
                ],
            }
        )
        for node in soup.find_all("ol")
    ]
    links = [str(a.get("href", "")) for a in soup.find_all("a")]
    images = [str(img.get("src", "")) for img in soup.find_all("img")]
    assets = sorted(
        {
            str(node.get(attr))
            for tag, attr in (("link", "href"), ("img", "src"))
            for node in soup.find_all(tag)
            if str(node.get(attr, "")).startswith("/static/")
        }
    )
    if sum(map(len, (tables, lists, links, images, assets))) > MAX_ITEMS:
        raise ValueError("Document evidence exceeds the bounded item count")
    return {
        "tables": tables,
        "ordered_lists": lists,
        "links": links,
        "images": images,
        "assets": assets,
    }


def _local_asset(url, remaining):
    parsed = urlsplit(url)
    path = unquote(parsed.path)
    relative = path.removeprefix("/static/")
    if (
        parsed.scheme
        or parsed.netloc
        or not path.startswith("/static/")
        or not relative
        or any(p in {"", ".", ".."} for p in relative.split("/"))
        or "\\" in relative
        or "%" in relative
    ):
        raise ValueError("Unsupported local asset path")
    found = finders.find(relative)
    if not found:
        raise ValueError("Local asset was not found")
    file = Path(found)
    if (
        file.is_symlink()
        or any(parent.is_symlink() for parent in file.parents)
        or not file.is_file()
        or file.stat().st_size > min(MAX_ASSET_BYTES, remaining)
    ):
        raise ValueError("Local asset cannot be inspected within this scope")
    with file.open("rb") as stream:
        data = stream.read(min(MAX_ASSET_BYTES, remaining) + 1)
    if len(data) > min(MAX_ASSET_BYTES, remaining):
        raise ValueError("Local asset exceeds the remaining inspection budget")
    return hashlib.sha256(data).hexdigest(), len(data)


def inspect(conversion_html, rendered_html):
    """Return small evidence rows; never fetch a URL or mutate source/content."""
    input_digest = _input_digest(conversion_html, rendered_html)
    try:
        source, rendered = inventory(conversion_html), inventory(rendered_html)
    except ValueError as exc:
        return [
            {
                "id": "inventory",
                "status": "not_assessed",
                "target": "Converted content inventory",
                "evidence": str(exc),
                "action": "Keep the fidelity blocker open; inspect this unsupported document separately.",
                "input_digest": input_digest,
            }
        ]
    rows = []
    for key, label in (
        ("tables", "Converted table cells and spans"),
        ("ordered_lists", "Converted ordered lists and starts"),
        ("links", "Converted link destinations"),
        ("images", "Converted image sources"),
    ):
        expected, observed = source[key], rendered[key]
        # Empty input is not proof that the original Word had no such content.
        if not expected:
            status, detail = (
                "not_assessed",
                "No corresponding elements were present in the retained conversion. Original Word coverage is not established.",
            )
        else:
            missing = Counter(expected) - Counter(observed)
            # Count checks alone would miss reordering. Match converted elements
            # in order while allowing generated tables/navigation between them.
            cursor = iter(observed)
            in_order = all(
                any(actual == wanted for actual in cursor) for wanted in expected
            )
            status = "pass" if not missing and in_order and all(expected) else "fail"
            detail = (
                f"Converted elements: {len(expected)}. HTML elements: {len(observed)}. "
                f"Unmatched occurrences: {sum(missing.values())}. Exact converted sequence observed: {'yes' if in_order else 'no'}. "
                "Only the documented table/list attributes or href/src values are compared; generated extras are allowed and text whitespace is not normalized."
            )
        rows.append(
            {
                "id": key,
                "status": status,
                "target": label,
                "evidence": detail,
                "action": "Reconcile unmatched or reordered elements against import/render rules. Internal IDs may be remapped; a mismatch is not by itself proof of a defect. This does not clear overall source fidelity.",
            }
        )
    asset_rows = []
    remaining = MAX_TOTAL_ASSET_BYTES
    for url in rendered["assets"]:
        try:
            digest, size = _local_asset(url, remaining)
            remaining -= size
            asset_rows.append((url, digest))
        except (ValueError, OSError):
            asset_rows.append((url, None))
    missing = sum(digest is None for _, digest in asset_rows)
    rows.append(
        {
            "id": "static-assets",
            "status": "fail" if missing else "pass" if asset_rows else "not_assessed",
            "target": "Direct local HTML resources",
            "evidence": f"Direct local resources: {len(asset_rows)}. Missing or unsupported: {missing}. Manifest SHA-256: {hashlib.sha256(_signature(asset_rows).encode()).hexdigest()}.",
            "action": "This checks direct local stylesheet/image bytes only. CSS imports, CSS URLs, fonts, external resources, image meaning and final PDF layout are not verified. Keep complete asset/link verification open.",
        }
    )
    # Exact input bytes, not only summary counts, bind findings and stale forms.
    for row in rows:
        row["input_digest"] = input_digest
    return rows
