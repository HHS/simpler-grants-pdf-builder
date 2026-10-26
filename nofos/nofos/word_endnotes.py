"""Preserve explicit Word NOTEREF relationships before Mammoth flattens fields.

IMPORT-076 in documentation/IMPORT_RULES.md. Only an in-memory import copy
is rewritten; the uploaded source is never modified.
"""

import re
from collections import Counter
from io import BytesIO
from xml.dom import minidom
from zipfile import ZIP_DEFLATED, ZipFile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NOTEREF = re.compile(
    r'^\s*NOTEREF\s+(?:"([^"\s]+)"|([^\s]+))'
    r"((?:\s+(?:\\[fh]|\\\*\s+MERGEFORMAT))*)\s*$",
    re.I,
)


def _elements(node, name):
    return node.getElementsByTagNameNS(W, name)


def _text(node, name="t"):
    return "".join(
        child.data
        for element in _elements(node, name)
        for child in element.childNodes
        if child.nodeType == child.TEXT_NODE
    )


def _bookmark_notes(document):
    """Resolve only complete bookmarks enclosing exactly one native note mark."""
    starts = _elements(document, "bookmarkStart")
    name_counts = Counter(n.getAttributeNS(W, "name") for n in starts)
    id_counts = Counter(n.getAttributeNS(W, "id") for n in starts)
    active, found = {}, {}
    for element in document.getElementsByTagName("*"):
        if element.namespaceURI != W:
            continue
        if element.localName == "bookmarkStart":
            if (
                name_counts[element.getAttributeNS(W, "name")] != 1
                or id_counts[element.getAttributeNS(W, "id")] != 1
            ):
                continue
            active[element.getAttributeNS(W, "id")] = (
                element.getAttributeNS(W, "name"),
                [],
            )
        elif element.localName in ("endnoteReference", "footnoteReference"):
            note = (
                element.localName.removesuffix("Reference"),
                element.getAttributeNS(W, "id"),
            )
            for _, notes in active.values():
                notes.append(note)
        elif element.localName == "bookmarkEnd":
            entry = active.pop(element.getAttributeNS(W, "id"), None)
            if entry:
                name, notes = entry
                found.setdefault(name, []).append(notes)
    return {
        name: ranges[0][0]
        for name, ranges in found.items()
        if len(ranges) == 1 and len(ranges[0]) == 1
    }


def _link(document, instruction, runs, bookmarks):
    match = NOTEREF.fullmatch(instruction)
    if not match or not re.fullmatch(
        r"\s*\[?\d+\]?\s*", "".join(_text(r) for r in runs)
    ):
        return None
    note = bookmarks.get(match[1] or match[2])
    if note is None:
        return None
    # Restrict results to plain Word runs: no nested fields, drawings or links.
    if any(
        run.namespaceURI != W
        or run.localName != "r"
        or any(
            e.localName not in ("rPr", "t")
            for e in run.childNodes
            if e.nodeType == e.ELEMENT_NODE
        )
        for run in runs
    ):
        return None
    link = document.createElementNS(W, "w:hyperlink")
    link.setAttributeNS(W, "w:anchor", "-".join(note))
    for run in runs:
        link.appendChild(run.cloneNode(True))
    return link


def _control_run(node):
    """Do not discard bookmarks, drawings, tabs or other field-adjacent content."""
    return (
        node.namespaceURI == W
        and node.localName == "r"
        and not _text(node).strip()
        and all(
            child.namespaceURI == W
            and child.localName in ("rPr", "instrText", "fldChar", "t")
            for child in node.childNodes
            if child.nodeType == child.ELEMENT_NODE
        )
    )


def preserve_word_note_cross_references(uploaded_file):
    """Convert supported simple/complex NOTEREF fields to explicit hyperlinks.

    Unsupported, nested, incomplete, or unresolved fields retain Mammoth's
    existing behavior. No cached number is used to guess a destination.
    """
    uploaded_file.seek(0)
    with ZipFile(uploaded_file) as source:
        xml = source.read("word/document.xml")
        if b"NOTEREF" not in xml.upper():
            uploaded_file.seek(0)
            return uploaded_file
        declarations = xml.replace(b"\0", b"").upper()
        if b"<!DOCTYPE" in declarations or b"<!ENTITY" in declarations:
            raise ValueError("Unsupported XML declaration")
        document = minidom.parseString(xml)
        bookmarks = _bookmark_notes(document)
        changed = False
        for field in list(_elements(document, "fldSimple")):
            runs = [n for n in field.childNodes if n.nodeType == n.ELEMENT_NODE]
            link = _link(document, field.getAttributeNS(W, "instr"), runs, bookmarks)
            if link is not None:
                field.parentNode.replaceChild(link, field)
                changed = True
        for paragraph in _elements(document, "p"):
            children = [n for n in paragraph.childNodes if n.nodeType == n.ELEMENT_NODE]
            start, separator, depth = None, None, 0
            nested = False
            for index, child in enumerate(children):
                marks = _elements(child, "fldChar")
                if len(marks) != 1:
                    if marks:
                        nested = True
                    continue
                kind = marks[0].getAttributeNS(W, "fldCharType")
                if kind == "begin":
                    if depth == 0:
                        start, separator, nested = index, None, False
                    else:
                        nested = True
                    depth += 1
                elif kind == "separate" and depth == 1:
                    separator = index
                elif kind == "end" and depth:
                    depth -= 1
                    if depth or nested or separator is None:
                        continue
                    instruction = "".join(
                        _text(n, "instrText") for n in children[start:separator]
                    )
                    link = _link(
                        document,
                        instruction,
                        children[separator + 1 : index],
                        bookmarks,
                    )
                    # Field boundary/instruction runs must not carry prose.
                    controls = children[start : separator + 1] + [child]
                    if link is not None and all(_control_run(n) for n in controls):
                        paragraph.insertBefore(link, children[start])
                        for node in children[start : index + 1]:
                            paragraph.removeChild(node)
                        changed = True
        if not changed:
            uploaded_file.seek(0)
            return uploaded_file
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as target:
            for info in source.infolist():
                target.writestr(
                    info,
                    (
                        document.toxml(encoding="utf-8")
                        if info.filename == "word/document.xml"
                        else source.read(info.filename)
                    ),
                )
    output.seek(0)
    return output
