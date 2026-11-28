"""Recognize applicant note labels without rewriting their content."""

import re

from bs4 import NavigableString, Tag

from .nofo_markdown import PRESERVE_BOOKMARK_TARGET_ATTR

# IMPORT-080: "Note", "Notes", "Please note" or "N.B.", optionally followed by
# an audience ("for" plus up to eight words) and/or a bracketed audience, then a
# colon or dash. Ordinary sentences such as "Note that…" never match.
_IMPORT_LABEL = re.compile(
    r"""^\s*(?:
        (?:please\s+)?notes?
        (?P<audience>
            (?:\s+for(?:\s+(?![-–—](?:\s|$))[^\s:()–—]+(?=[\s:()–—]|$)){1,8})?
            (?:\s*\([^()]{1,80}\))?
        )
        \s*[:\-–—]
      |
        n\.\s*b\.(?:\s*[:\-–—])?(?=\s|$)
    )\s*""",
    re.IGNORECASE | re.VERBOSE,
)
_RENDER_LABEL = re.compile(r"^\s*Note:")
_INLINE_WRAPPERS = {"b", "strong", "em", "i", "span"}
_TOP_LEVEL_PARENTS = {"body", "[document]"}

# Marks a standalone note paragraph for the section parser. Set and removed
# during Builder import only; it is never stored.
NOTE_CALLOUT_MARKER = "data-nofo-note-callout"


def _label_text(match):
    """ "Note:" plus any audience, kept as written apart from whitespace."""
    audience = re.sub(r"\s+", " ", match.group("audience") or "").strip()
    return f"Note {audience}:" if audience else "Note:"


def _is_empty_paragraph(tag):
    return tag.name == "p" and not tag.get_text(strip=True) and not tag.find(True)


def _next_block(tag):
    """The next sibling element, skipping whitespace and empty spacer paragraphs."""
    for sibling in tag.next_siblings:
        if isinstance(sibling, Tag):
            if _is_empty_paragraph(sibling):
                continue
            return sibling
        if str(sibling).strip():
            return None
    return None


def _previous_block(tag):
    for sibling in tag.previous_siblings:
        if isinstance(sibling, Tag):
            if _is_empty_paragraph(sibling):
                continue
            return sibling
        if str(sibling).strip():
            return None
    return None


def is_between_list_items(element):
    """True when a paragraph interrupts a list: a list of the same kind on both sides."""
    previous, following = _previous_block(element), _next_block(element)
    return (
        previous is not None
        and following is not None
        and previous.name in {"ol", "ul"}
        and previous.name == following.name
    )


def is_in_list_or_table(element):
    return bool(element.find_parent(["li", "td", "th"]))


def _join_following_paragraph(soup, paragraph):
    """Give a bare "Note:" label line the text of the paragraph that follows it."""
    following = _next_block(paragraph)
    if (
        following is None
        or following.name != "p"
        or _IMPORT_LABEL.match(following.get_text())
        or not following.get_text(strip=True)
    ):
        return
    paragraph.append(" ")
    if following.get("id"):
        # Keep link targets: the Markdown converter retains marked empty anchors.
        target = soup.new_tag("a", id=following["id"])
        target[PRESERVE_BOOKMARK_TARGET_ATTR] = ""
        paragraph.append(target)
    for child in list(following.contents):
        paragraph.append(child.extract())
    following.decompose()


def _strip_trailing_breaks(paragraph):
    """Drop line breaks and whitespace at the end of a paragraph."""
    while paragraph.contents:
        last = paragraph.contents[-1]
        if (isinstance(last, Tag) and last.name == "br") or (
            isinstance(last, NavigableString) and not last.strip()
        ):
            last.extract()
        else:
            break


def _has_body(paragraph):
    """True when a labelled paragraph has text or an image after its label."""
    for node in paragraph.contents[1:]:
        if isinstance(node, NavigableString):
            if node.strip():
                return True
        elif node.name == "img" or node.get_text(strip=True) or node.find("img"):
            return True
    return False


def normalize_note_labels(soup):
    """Normalize only the label, keeping the original inline body nodes.

    Standalone top-level notes are also marked so the section parser can make
    each one its own "Note" callout subsection.
    """
    for paragraph in soup.find_all("p"):
        if not _IMPORT_LABEL.match(paragraph.get_text()):
            continue
        # A trailing break must not make a bare "Note:" line look like a note.
        _strip_trailing_breaks(paragraph)
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
        label.string = _label_text(match)
        paragraph.insert(0, label)
        if _has_body(paragraph):
            paragraph.insert(1, " ")

        if paragraph.parent is None or paragraph.parent.name not in _TOP_LEVEL_PARENTS:
            continue
        if not _has_body(paragraph):
            # A bare label line: drop leftover breaks and take the next paragraph.
            for leftover in paragraph.contents[1:]:
                leftover.extract()
            _join_following_paragraph(soup, paragraph)
        if _has_body(paragraph) and not is_between_list_items(paragraph):
            paragraph[NOTE_CALLOUT_MARKER] = "true"


def has_note_label(markdown):
    """True when Markdown content starts with a note label such as "Note:" or
    "**Note for applicants:**". Markdown emphasis markers are ignored."""
    # Drop Markdown emphasis markers so "**Note**:" and "**N.B.**" also count.
    first_line = (markdown or "").lstrip().split("\n", 1)[0]
    return bool(_IMPORT_LABEL.match(re.sub(r"\*+|_+", "", first_line)))


def is_note_paragraph(element):
    return bool(_RENDER_LABEL.match(element.get_text()))
