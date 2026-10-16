"""Preserve native Word list semantics around Mammoth's lossy numbering model.

The conversion copy carries temporary paragraph styles, never source text
markers. Mammoth still owns runs, hyperlinks, bookmarks, tables and notes.
"""

from dataclasses import dataclass, field
from io import BytesIO
from secrets import token_hex
from xml.dom import minidom
from zipfile import ZipFile

from bs4 import BeautifulSoup, NavigableString, Tag

from .import_transforms import CHECKBOX_PREFIXES

WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
SOURCE_LIST_ATTR = "data-nofo-source-list"
FORMATS = {
    "decimal": "1",
    "lowerLetter": "a",
    "upperLetter": "A",
    "lowerRoman": "i",
    "upperRoman": "I",
    "bullet": None,
}
UNSUPPORTED_WARNING = (
    "Some Word list numbering could not be preserved automatically. "
    "Review custom list markers and list continuation in the imported document."
)


def _xml(data):
    declarations = data.replace(b"\0", b"").upper()
    if b"<!DOCTYPE" in declarations or b"<!ENTITY" in declarations:
        raise ValueError("Unsupported XML declaration")
    return minidom.parseString(data)


def _children(node, name):
    if node is None:
        return []
    return [
        child
        for child in node.childNodes
        if child.nodeType == child.ELEMENT_NODE
        and child.namespaceURI == WORD_NS
        and child.localName == name
    ]


def _child(node, name):
    return next(iter(_children(node, name)), None)


def _val(node, default=None):
    if node is not None and node.hasAttributeNS(WORD_NS, "val"):
        return node.getAttributeNS(WORD_NS, "val")
    return default


def _integer(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _number_properties(properties):
    numbering = _child(properties, "numPr")
    return {
        name: value
        for name in ("numId", "ilvl")
        if (value := _val(_child(numbering, name))) is not None
    }


def _indent(properties):
    indent = _child(properties, "ind")
    if indent is None:
        return None
    for name in ("start", "left"):
        if indent.hasAttributeNS(WORD_NS, name):
            return _integer(indent.getAttributeNS(WORD_NS, name))
    return None


@dataclass(frozen=True)
class _Item:
    num_id: str
    level: int
    marker: str | None
    ordinal: int
    indent: int | None
    continuation: bool = False


@dataclass
class WordListPlan:
    """Ephemeral sidecar for one conversion; no database or framework required."""

    style_map: str = ""
    warnings: list[str] = field(default_factory=list)
    _items: dict[str, _Item] = field(default_factory=dict, repr=False)

    def restore_html(self, html):
        if not self._items:
            return html
        soup = BeautifulSoup(html, "html.parser")
        # Each container is independent. A table boundary or ordinary paragraph
        # ends a list tree, but its Word numbering instance may continue later.
        for first in list(soup.find_all("p")):
            if first.parent is None or self._item_for(first) is None:
                continue
            group = []
            node = first
            while node is not None:
                following = node.next_sibling
                if isinstance(node, NavigableString) and not node.strip():
                    node = following
                    continue
                item = self._item_for(node)
                if item is None:
                    break
                group.append((node, item))
                node = following
            self._restore_group(soup, group)
        return str(soup)

    def _item_for(self, node):
        if not isinstance(node, Tag) or node.name != "p":
            return None
        for classname in node.get("class", []):
            if classname in self._items:
                return self._items[classname]
        return None

    def _restore_group(self, soup, group):
        stack = []
        for paragraph, item in group:
            classes = [c for c in paragraph.get("class", []) if c not in self._items]
            if classes:
                paragraph["class"] = classes
            else:
                paragraph.attrs.pop("class", None)
            if item.continuation and stack:
                stack[-1]["item"].append(paragraph.extract())
                continue
            while stack and stack[-1]["level"] > item.level:
                stack.pop()
            same = bool(
                stack
                and stack[-1]["level"] == item.level
                and stack[-1]["num_id"] == item.num_id
                and stack[-1]["marker"] == item.marker
                and (item.marker is None or stack[-1]["next"] == item.ordinal)
            )
            if not same:
                if stack and stack[-1]["level"] == item.level:
                    stack.pop()
                listing = soup.new_tag("ul" if item.marker is None else "ol")
                listing[SOURCE_LIST_ATTR] = "true"
                if item.marker is not None:
                    listing["type"] = item.marker
                    if item.ordinal != 1:
                        listing["start"] = str(item.ordinal)
                if stack:
                    stack[-1]["item"].append(listing)
                else:
                    paragraph.insert_before(listing)
                stack.append(
                    {
                        "level": item.level,
                        "num_id": item.num_id,
                        "marker": item.marker,
                        "list": listing,
                        "item": None,
                        "next": item.ordinal,
                    }
                )
            li = soup.new_tag("li")
            # Retain IDs/other semantic paragraph attributes. The ordinary
            # paragraph can disappear only when it has no attributes left.
            if paragraph.attrs:
                li.append(paragraph.extract())
            else:
                for child in list(paragraph.contents):
                    li.append(child.extract())
                paragraph.decompose()
            stack[-1]["list"].append(li)
            stack[-1]["item"] = li
            stack[-1]["next"] = item.ordinal + 1


class _Numbering:
    def __init__(self, styles, numbering):
        self.styles = {}
        self.default_style = None
        if styles is not None:
            for style in styles.getElementsByTagNameNS(WORD_NS, "style"):
                style_id = style.getAttributeNS(WORD_NS, "styleId")
                self.styles.setdefault(style_id, style)
                if style.getAttributeNS(
                    WORD_NS, "type"
                ) == "paragraph" and style.getAttributeNS(WORD_NS, "default") in {
                    "1",
                    "true",
                }:
                    self.default_style = style_id
        self.abstract = {}
        self.nums = {}
        if numbering is not None:
            self.abstract = {
                node.getAttributeNS(WORD_NS, "abstractNumId"): node
                for node in numbering.getElementsByTagNameNS(WORD_NS, "abstractNum")
            }
            self.nums = {
                node.getAttributeNS(WORD_NS, "numId"): node
                for node in numbering.getElementsByTagNameNS(WORD_NS, "num")
            }
        self.counters = {}
        self.associated_styles = {}
        for num_id in self.nums:
            for index in range(9):
                definition = self.level(num_id, index)
                if definition and definition["paragraph_style"]:
                    self.associated_styles.setdefault(
                        definition["paragraph_style"], []
                    ).append((num_id, str(index)))

    def style_chain(self, style_id):
        seen = set()
        chain = []
        while style_id and style_id not in seen:
            seen.add(style_id)
            style = self.styles.get(style_id)
            if style is None:
                break
            chain.append(style)
            style_id = _val(_child(style, "basedOn"))
        return list(reversed(chain))

    def paragraph_properties(self, paragraph):
        properties = _child(paragraph, "pPr")
        style_id = _val(_child(properties, "pStyle"), self.default_style)
        number = {}
        indent = None
        heading = False
        chain = self.style_chain(style_id)
        for style in chain:
            props = _child(style, "pPr")
            number.update(_number_properties(props))
            if _indent(props) is not None:
                indent = _indent(props)
            name = _val(_child(style, "name"), "").casefold()
            heading |= (
                name.startswith("heading") or _child(props, "outlineLvl") is not None
            )
        number.update(_number_properties(properties))
        if _indent(properties) is not None:
            indent = _indent(properties)
        heading |= _child(properties, "outlineLvl") is not None
        # Explicitly disabled numbering is not inherited back from a style.
        if number.get("numId") == "0":
            number = {}
        elif not number.get("numId"):
            # A numbering level may name the paragraph style instead of the
            # paragraph/style carrying numPr. Use it only when a single actual
            # numbering instance can be selected. Multiple numIds are distinct
            # restart histories, even if they share an abstract definition.
            style_ids = [
                style.getAttributeNS(WORD_NS, "styleId") for style in reversed(chain)
            ]
            if style_id not in style_ids:
                style_ids.insert(0, style_id)
            for candidate in style_ids:
                matches = self.associated_styles.get(candidate, [])
                if not matches:
                    continue
                if len(matches) == 1:
                    num_id, index = matches[0]
                    number.setdefault("numId", num_id)
                    number.setdefault("ilvl", index)
                else:
                    number["numId"] = "ambiguous-style-numbering"
                break
        return number, indent, heading

    def level(self, num_id, index, seen=None):
        seen = set() if seen is None else seen
        if num_id in seen:
            return None
        seen.add(num_id)
        num = self.nums.get(num_id)
        abstract = self.abstract.get(_val(_child(num, "abstractNumId")))
        if abstract is None:
            return None
        override = next(
            (
                node
                for node in _children(num, "lvlOverride")
                if _integer(node.getAttributeNS(WORD_NS, "ilvl")) == index
            ),
            None,
        )
        style_link = _val(_child(abstract, "numStyleLink"))
        if style_link and _child(override, "lvl") is None:
            props = {}
            for style in self.style_chain(style_link):
                props.update(_number_properties(_child(style, "pPr")))
            inherited = self.level(props.get("numId"), index, seen)
            if inherited is None:
                return None
            start = _integer(_val(_child(override, "startOverride")))
            return {**inherited, **({"start": start} if start is not None else {})}
        levels = [
            node
            for node in _children(abstract, "lvl")
            if _integer(node.getAttributeNS(WORD_NS, "ilvl"), 0) == index
        ]
        # A full lvl override replaces that level's definition, rather than
        # guessing missing properties from an unrelated abstract level.
        level = _child(override, "lvl") or next(iter(levels), None)
        if level is None:
            return None
        start = _integer(_val(_child(override, "startOverride")))
        if start is None:
            start = _integer(_val(_child(level, "start")), 1)
        return {
            "format": _val(_child(level, "numFmt")),
            "text": _val(_child(level, "lvlText")),
            "start": start,
            "restart": _integer(_val(_child(level, "lvlRestart")), index),
            "indent": _indent(_child(level, "pPr")),
            "paragraph_style": _val(_child(level, "pStyle")),
        }

    def item(self, paragraph):
        number, indent, heading = self.paragraph_properties(paragraph)
        if not number or heading:
            return None, False
        num_id = number.get("numId")
        index = _integer(number.get("ilvl"), 0)
        if not num_id or not 0 <= index <= 8:
            return None, True
        definition = self.level(num_id, index)
        if definition is None:
            return None, True
        fmt = definition["format"]
        for other_num, other_level in list(self.counters):
            if other_num != num_id or other_level <= index:
                continue
            other = self.level(num_id, other_level)
            # lvlRestart is one-based; zero disables restarting. Absence
            # means restart after the immediately preceding Word level.
            if other and 0 < other["restart"] and index < other["restart"]:
                del self.counters[(other_num, other_level)]
        key = (num_id, index)
        ordinal = self.counters.get(key, definition["start"] - 1) + 1
        self.counters[key] = ordinal
        # Count unsupported items too, so supported later levels in the same
        # numbering instance do not silently restart after the fallback.
        if fmt not in FORMATS or (
            fmt != "bullet"
            and definition["text"] not in {f"%{index + 1}.", f"%{index + 1})"}
        ):
            return None, True
        return (
            _Item(
                num_id=num_id,
                level=index,
                marker=FORMATS[fmt],
                ordinal=ordinal,
                indent=indent if indent is not None else definition["indent"],
            ),
            False,
        )


def prepare_word_lists(upload):
    """Return an in-memory conversion copy and its ephemeral numbering plan.

    Unsupported numbering keeps Mammoth's existing behavior with a content-free
    review advisory. Only document-body/table paragraphs are touched; note parts
    retain their independent Mammoth conversion and native reference IDs.
    """
    upload.seek(0)
    plan = WordListPlan()
    with ZipFile(upload) as archive:
        document = _xml(archive.read("word/document.xml"))
        styles = (
            _xml(archive.read("word/styles.xml"))
            if "word/styles.xml" in archive.namelist()
            else None
        )
        numbering = (
            _xml(archive.read("word/numbering.xml"))
            if "word/numbering.xml" in archive.namelist()
            else None
        )
        resolver = _Numbering(styles, numbering)
        prefix = "nofo-native-list-" + token_hex(8) + "-"
        rules = []
        paragraphs = []
        for paragraph in document.getElementsByTagNameNS(WORD_NS, "p"):
            ancestor = paragraph.parentNode
            while ancestor is not None and not (
                ancestor.namespaceURI == WORD_NS
                and ancestor.localName in {"txbxContent", "drawing", "pict", "object"}
            ):
                ancestor = ancestor.parentNode
            # Text-box conversion is owned by the instruction-container adapter,
            # not by Mammoth's ordinary paragraph traversal.
            if ancestor is None:
                paragraphs.append(paragraph)
        records = {}
        for paragraph in paragraphs:
            cell = paragraph.parentNode
            if (
                cell.namespaceURI == WORD_NS
                and cell.localName == "tc"
                and _children(cell.parentNode, "tc")[0] is cell
            ):
                text = "".join(
                    child.firstChild.data
                    for child in paragraph.getElementsByTagNameNS(WORD_NS, "t")
                    if child.firstChild is not None
                ).lstrip()
                if text.startswith(CHECKBOX_PREFIXES):
                    # IMPORT-001 deliberately infers checklist child paragraphs
                    # from row indentation. Leave its styles/numbering intact.
                    continue
            item, unsupported = resolver.item(paragraph)
            if unsupported and UNSUPPORTED_WARNING not in plan.warnings:
                plan.warnings.append(UNSUPPORTED_WARNING)
            if item is not None:
                records[paragraph] = item
        # Attach only bounded, explicitly indented continuation paragraphs.
        # An ordinary unindented paragraph, heading or table is never swallowed.
        for paragraph in paragraphs:
            if paragraph in records:
                continue
            number, indent, heading = resolver.paragraph_properties(paragraph)
            if number or heading or indent is None or indent <= 0:
                continue
            previous = paragraph.previousSibling
            while previous is not None and previous.nodeType != previous.ELEMENT_NODE:
                previous = previous.previousSibling
            previous_item = records.get(previous)
            if (
                previous_item is None
                or previous_item.indent is None
                or indent < previous_item.indent
            ):
                continue
            following = paragraph.nextSibling
            while following is not None:
                if following.nodeType != following.ELEMENT_NODE:
                    following = following.nextSibling
                    continue
                if following in records:
                    break
                if following.namespaceURI != WORD_NS or following.localName != "p":
                    break
                following_number, following_indent, following_heading = (
                    resolver.paragraph_properties(following)
                )
                if (
                    following_number
                    or following_heading
                    or following_indent is None
                    or following_indent < previous_item.indent
                ):
                    break
                following = following.nextSibling
            next_item = records.get(following)
            if next_item is None or next_item.num_id != previous_item.num_id:
                continue
            records[paragraph] = _Item(
                **{**previous_item.__dict__, "continuation": True}
            )
        if not records:
            upload.seek(0)
            return upload, plan
        if styles is None:
            styles = _xml(f'<w:styles xmlns:w="{WORD_NS}"/>'.encode())
        for paragraph, item in records.items():
            marker = prefix + str(len(plan._items))
            plan._items[marker] = item
            properties = _child(paragraph, "pPr")
            if properties is None:
                properties = document.createElementNS(WORD_NS, "w:pPr")
                paragraph.insertBefore(properties, paragraph.firstChild)
            old_style = _val(_child(properties, "pStyle"))
            for node in _children(properties, "pStyle") + _children(
                properties, "numPr"
            ):
                properties.removeChild(node)
            style_reference = document.createElementNS(WORD_NS, "w:pStyle")
            style_reference.setAttributeNS(WORD_NS, "w:val", marker)
            properties.insertBefore(style_reference, properties.firstChild)
            disabled = document.createElementNS(WORD_NS, "w:numPr")
            num_id = document.createElementNS(WORD_NS, "w:numId")
            num_id.setAttributeNS(WORD_NS, "w:val", "0")
            disabled.appendChild(num_id)
            properties.appendChild(disabled)
            style = styles.createElementNS(WORD_NS, "w:style")
            style.setAttributeNS(WORD_NS, "w:type", "paragraph")
            style.setAttributeNS(WORD_NS, "w:styleId", marker)
            for name, value in (("name", marker), ("basedOn", old_style)):
                if value:
                    child = styles.createElementNS(WORD_NS, "w:" + name)
                    child.setAttributeNS(WORD_NS, "w:val", value)
                    style.appendChild(child)
            styles.documentElement.appendChild(style)
            rules.append(f"p[style-name='{marker}'] => p.{marker}:fresh")
        plan.style_map = "\n".join(rules)
        result = BytesIO()
        with ZipFile(result, "w") as output:
            for entry in archive.infolist():
                data = archive.read(entry)
                if entry.filename == "word/document.xml":
                    data = document.toxml(encoding="UTF-8")
                elif entry.filename == "word/styles.xml":
                    data = styles.toxml(encoding="UTF-8")
                output.writestr(entry, data)
            if "word/styles.xml" not in archive.namelist():
                output.writestr("word/styles.xml", styles.toxml(encoding="UTF-8"))
    result.seek(0)
    return result, plan
