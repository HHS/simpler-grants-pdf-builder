"""Conservative matching of manually authored notes in imported HTML.

Analysis is read-only: it can also be used on saved content without migrating it.

Implements import rules IMPORT-049 through IMPORT-051 in
documentation/IMPORT_RULES.md (at the repo root). Update those entries if
you change this file's behavior. See also docs/endnote-import.md for the
author-facing authoring convention this module detects.
"""

import re
from collections import defaultdict
from copy import copy

from bs4 import NavigableString

MARKER = re.compile(r"\[([1-9][0-9]{0,8})\]")
HEADING = re.compile(r"^(?:endnotes?|footnotes?)\s*:?$", re.I)
BLOCK_NAMES = ["p", "li", "td", "th"]


def _heading(tag):
    return bool(re.fullmatch(r"h[1-7]", tag.name or "") or tag.get("role") == "heading")


def is_endnotes_heading(text):
    return bool(HEADING.fullmatch(text.strip()))


def _blocks(soup):
    return [t for t in soup.find_all(BLOCK_NAMES) if not t.find_parent(["pre", "code"])]


def _scan(soup):
    headings = [
        t for t in soup.find_all(_heading) if HEADING.fullmatch(t.get_text(strip=True))
    ]
    section = set()
    if len(headings) == 1:
        for tag in headings[0].find_all_next():
            if _heading(tag):
                break
            section.add(id(tag))
    refs, citations = defaultdict(list), defaultdict(list)
    entries = []
    blocks = _blocks(soup)
    for block in blocks:
        text = block.get_text()
        for match in MARKER.finditer(text):
            # Existing links retain their native relationship. They are validated
            # independently below, never rematched by their visible number.
            offset = 0
            linked = False
            for node in block.find_all(string=True):
                end = offset + len(node)
                if offset < match.end() and end > match.start():
                    if node.find_parent(BLOCK_NAMES) is not block or node.find_parent(
                        ["code", "pre"]
                    ):
                        linked = True
                    anchor = node.find_parent("a", href=True)
                    if anchor and not (
                        anchor.get("id", "").startswith("endnote-ref-manual-")
                        or anchor["href"].startswith("#endnote-ref-manual-")
                    ):
                        linked = True
                offset = end
            if linked:
                continue
            item = (block, match.start(), match.end())
            number = int(match[1])
            if id(block) in section:
                if not text[: match.start()].strip():
                    citations[number].append(item)
                    entries.append((number, block))
            else:
                refs[number].append(item)
    # Large bracketed numbers in prose are often years. A matching citation can
    # establish note intent without imposing a maximum supported note number.
    refs = defaultdict(
        list, {n: items for n, items in refs.items() if n < 1000 or n in citations}
    )
    return headings, section, blocks, refs, citations, entries


def _inspect(soup):
    headings, section, blocks, refs, citations, entries = _scan(soup)
    issues, invalid = [], set()

    def warn(tag, message, code):
        issues.append({"tag": tag, "message": message, "code": code})

    # Ordinary bracketed numbers in a document without note evidence are not notes.
    evidence = headings or any(
        HEADING.fullmatch(t.get_text(strip=True))
        for t in soup.find_all(["p", "strong", "b"])
    )
    if evidence and len(headings) != 1:
        tag = headings[0] if headings else next(iter(blocks), soup)
        warn(
            tag,
            "Use one structural Endnotes heading so citations can be identified.",
            "heading",
        )
        invalid.update(refs)

    native_numbers = set()
    native_refs = defaultdict(list)
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if anchor.find_parent(["code", "pre"]) or not re.match(
            r"^#(?:footnote-|endnote-|ftnt(?:_ref)?\d|ref\d)", href
        ):
            continue
        label = anchor.get_text(strip=True)
        if not (
            re.fullmatch(r"\[?\d{1,9}\]?", label)
            or label in ("↑", "↩", "↩︎", "↩️")
            or re.match(r"^(?:footnote|endnote)-ref-", anchor.get("id", ""))
        ):
            continue
        targets = soup.find_all(id=href[1:])
        if len(targets) != 1:
            warn(
                anchor,
                "An endnote link points to a missing or conflicting destination.",
                "destination",
            )
        match = re.fullmatch(r"\[?([0-9]{1,9})\]?", anchor.get_text(strip=True))
        if match and len(targets) == 1 and not re.search(r"(?:-ref|_ref|^#ref)", href):
            reference_id = anchor.get("id")
            target_container = targets[0]
            if target_container.name == "a":
                target_container = (
                    target_container.find_parent(["li", "p"]) or target_container
                )
            if not reference_id or not target_container.find(
                "a", href=f"#{reference_id}"
            ):
                warn(
                    anchor,
                    "An endnote citation is missing its return link.",
                    "return-link",
                )
        if match and not (
            anchor.get("id", "").startswith("endnote-ref-manual-")
            or href.startswith("#endnote-ref-manual-")
        ):
            native_numbers.add(int(match[1]))
            if not re.search(r"(?:-ref|_ref|^#ref)", href):
                native_refs[int(match[1])].append(anchor)
        if anchor.get("id") and len(soup.find_all(id=anchor["id"])) > 1:
            warn(
                anchor,
                "An endnote reference has a conflicting destination ID.",
                "destination",
            )
    for number, anchors in native_refs.items():
        if len(anchors) > 1:
            warn(
                anchors[0],
                f"[{number}] is used more than once in linked endnotes.",
                "duplicate",
            )
    for target in soup.find_all(id=re.compile(r"^(?:endnote|footnote)-(?!ref-).+")):
        if not soup.find("a", href=f'#{target["id"]}'):
            warn(
                target,
                "An endnote citation does not have a corresponding reference.",
                "missing-reference",
            )

    if evidence:
        for number in refs.keys() | citations.keys():
            r, c = refs[number], citations[number]
            tag = (r or c)[0][0]
            if len(r) > 1 or len(c) > 1:
                warn(tag, f"[{number}] is used more than once.", "duplicate")
                invalid.add(number)
            if not r:
                warn(
                    tag,
                    f"Citation [{number}] does not have a corresponding reference.",
                    "missing-reference",
                )
                invalid.add(number)
            if not c:
                warn(
                    tag,
                    f"[{number}] does not have a corresponding citation.",
                    "missing-citation",
                )
                invalid.add(number)
            if number in native_numbers:
                warn(
                    tag,
                    f"[{number}] conflicts with an existing linked endnote.",
                    "conflict",
                )
                invalid.add(number)

        for index, (number, block) in enumerate(entries):
            start = blocks.index(block)
            stop = (
                blocks.index(entries[index + 1][1])
                if index + 1 < len(entries)
                else len(blocks)
            )
            citation_copy = copy(block)
            for anchor in citation_copy.find_all(
                "a", href=re.compile(r"^#(?:endnote|footnote)-ref")
            ):
                if not MARKER.fullmatch(anchor.get_text(strip=True)):
                    anchor.decompose()
            content = MARKER.sub("", citation_copy.get_text(), count=1).strip()
            content += "".join(
                t.get_text(strip=True)
                for t in blocks[start + 1 : stop]
                if id(t) in section
            )
            if not content:
                warn(block, f"Citation [{number}] is empty.", "empty")
                invalid.add(number)

        # Parent blocks may contain both their own references and nested blocks.
        # Compare actual text positions, rather than element traversal order.
        text_positions = {}
        position = 0
        for node in soup.find_all(string=True):
            text_positions[id(node)] = position
            position += len(node)

        def text_start(tag):
            return text_positions[id(tag.find(string=True))]

        manual_events = sorted(
            (text_start(block) + start, n)
            for n, matches in refs.items()
            for block, start, _ in matches
        )
        sequence = [n for _, n in manual_events]
        combined_events = sorted(
            manual_events
            + [
                (text_start(anchor), n)
                for n, anchors in native_refs.items()
                for anchor in anchors
                if id(anchor) not in section
            ]
        )
        combined_sequence = [n for _, n in combined_events]
        if sequence and combined_sequence != list(range(1, len(combined_sequence) + 1)):
            warn(
                refs[sequence[0]][0][0],
                "Endnote references must be sequential from [1], without gaps or restarts.",
                "numbering",
            )
        if [n for n, _ in entries] != sequence and entries and sequence:
            warn(
                entries[0][1],
                "Citations are not in the same order as their references.",
                "order",
            )
        for block in blocks:
            # Restrict typo guesses to citation starts to avoid interpreting prose,
            # dates, and mathematical expressions as malformed endnote references.
            if id(block) in section and re.match(
                r"^\s*(?:(?:\[\d+(?![\d\]])|\d+\])(?:\s|$)|\[0\d*\]|\[\s+\d+\s*\]|\[\d+\s+\])",
                block.get_text(),
            ):
                warn(
                    block,
                    "Possible malformed citation marker; use [1] formatting.",
                    "malformed",
                )
            elif id(block) not in section:
                for typo in re.finditer(
                    r"\[([1-9][0-9]{0,8})(?![0-9\]])(?=\s|$)", block.get_text()
                ):
                    number = int(typo[1])
                    if number in citations and not refs.get(number):
                        warn(
                            block,
                            f"Possible malformed reference: {typo[0]}. Use [{number}] formatting.",
                            "malformed",
                        )
    return issues, invalid, (headings, section, blocks, refs, citations, entries)


def analyze_endnotes(soup):
    """Return actionable issues with their source Tag, without changing HTML."""
    return _inspect(soup)[0]


def _wrap_range(soup, block, start, end, wrapper):
    """Wrap a text interval while preserving inline formatting split across runs."""
    position = 0

    def split(node):
        nonlocal position
        if isinstance(node, NavigableString):
            a, b = position, position + len(node)
            position = b
            return [
                NavigableString(str(node)[max(0, low - a) : max(0, min(b, high) - a)])
                for low, high in ((0, start), (start, end), (end, b))
            ]
        if not node.contents:
            parts = [NavigableString("") for _ in range(3)]
            parts[0 if position <= start else 2 if position >= end else 1] = copy(node)
            return parts
        # Keep untouched subtrees intact. Copying a later nested citation here
        # would leave the conversion plan pointing at a detached original.
        length = sum(
            len(text) for text in node.descendants if isinstance(text, NavigableString)
        )
        if position + length <= start or position >= end:
            index = 0 if position + length <= start else 2
            position += length
            parts = [NavigableString("") for _ in range(3)]
            parts[index] = node
            return parts
        parts = [copy(node) for _ in range(3)]
        for part in parts:
            part.clear()
        for child in list(node.contents):
            for part, fragment in zip(parts, split(child)):
                if str(fragment):
                    part.append(fragment)
        kept_id = False
        for part in parts:
            if part.contents and part.has_attr("id"):
                if kept_id:
                    del part["id"]
                kept_id = True
        return [part if part.contents else NavigableString("") for part in parts]

    groups = [[], [], []]
    for child in list(block.contents):
        for group, fragment in zip(groups, split(child)):
            if str(fragment):
                group.append(fragment)
    block.clear()
    block.extend(groups[0])
    wrapper.extend(groups[1])
    block.append(wrapper)
    block.extend(groups[2])


def convert_bracketed_endnotes(soup):
    """Link only complete unambiguous pairs; preserve all unresolved content."""
    issues, invalid, data = _inspect(soup)
    headings, section, blocks, refs, citations, entries = data
    if len(headings) != 1:
        return issues
    used = {tag["id"] for tag in soup.find_all(id=True)}
    # Reverse offsets protect multiple different markers in the same paragraph.
    pairs = [
        (n, items[0])
        for n, items in refs.items()
        if n not in invalid and len(items) == len(citations[n]) == 1
    ]
    pairs.sort(
        key=lambda pair: (len(list(pair[1][0].parents)), pair[1][1]), reverse=True
    )
    for number, (block, start, end) in pairs:
        if block.find("a", id=re.compile(r"^endnote-ref-manual-")):
            # Skip just an already linked marker, not other raw markers sharing
            # its paragraph.
            existing = [
                a
                for a in block.find_all("a", id=True)
                if a.get_text() == f"[{number}]"
                and a["id"].startswith("endnote-ref-manual-")
            ]
            if existing:
                continue
        base = f"endnote-manual-{number}"
        ref_id = f"endnote-ref-manual-{number}"
        suffix = 1
        while base in used or ref_id in used:
            base = f"endnote-manual-{number}-{suffix}"
            ref_id = f"endnote-ref-manual-{number}-{suffix}"
            suffix += 1
        used.update((base, ref_id))
        citation = citations[number][0][0]
        # Keep existing source bookmarks while using a recognizable new target.
        if citation.get("id"):
            bookmark = soup.new_tag("a", id=citation["id"])
            citation.insert(0, bookmark)
        target = base
        citation["id"] = target
        citation["tabindex"] = "-1"
        link = soup.new_tag("a", href=f"#{target}", id=ref_id)
        link["aria-label"] = f"Endnote {number}"
        _wrap_range(soup, block, start, end, link)
        link.wrap(soup.new_tag("sup"))
        back = soup.new_tag("a", href=f"#{ref_id}")
        back["aria-label"] = f"Return to endnote {number} reference"
        back.string = "↑"
        citation.append(" ")
        citation.append(back)
        # Mark citation number as linked too, so subsequent analysis/import does
        # not mistake it for an orphaned manually authored citation.
        marker = MARKER.search(citation.get_text())
        citation_link = soup.new_tag("a", href=f"#{ref_id}")
        citation_link["aria-label"] = f"Return to endnote {number} reference"
        _wrap_range(soup, citation, marker.start(), marker.end(), citation_link)
    return issues
