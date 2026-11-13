"""Recognize applicant note labels without rewriting their content."""

import re

from bs4 import NavigableString, Tag

_IMPORT_LABEL = re.compile(
    r"^\s*(?:(?:please\s+)?notes?\s*[:\-–—]|n\.\s*b\.(?:\s*[:\-–—])?(?=\s|$))\s*",
    re.IGNORECASE,
)
_RENDER_LABEL = re.compile(r"^\s*Note:")
_INLINE_WRAPPERS = {"b", "strong", "em", "i", "span"}


def normalize_note_labels(soup):
    """Normalize only the label, keeping the original inline body nodes."""
    for paragraph in soup.find_all("p"):
        match = _IMPORT_LABEL.match(paragraph.get_text())
        if not match:
            continue

        # Ignore linked labels, anchors and non-text objects in the prefix.
        # Formatting wrappers with attributes may carry a bookmark or style.
        remaining = match.end()
        edits = []
        wrappers = []
        for node in paragraph.descendants:
            if not remaining:
                break
            if isinstance(node, Tag):
                if node.name not in _INLINE_WRAPPERS or node.attrs:
                    break
                wrappers.append(node)
            elif type(node) is NavigableString:
                length = min(len(node), remaining)
                edits.append((node, node[length:]))
                remaining -= length
        if remaining:
            continue

        for node, suffix in edits:
            if suffix:
                node.replace_with(suffix)
            else:
                node.extract()
        for wrapper in reversed(wrappers):
            if not wrapper.contents:
                wrapper.extract()
        label = soup.new_tag("strong")
        label.string = "Note:"
        paragraph.insert(0, label)
        if paragraph.contents[1:]:
            paragraph.insert(1, " ")


def is_note_paragraph(element):
    return bool(_RENDER_LABEL.match(element.get_text()))
