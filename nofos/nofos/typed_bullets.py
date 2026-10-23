"""Conservative import-only repair of literal bullet groups (IMPORT-071)."""

import re
from copy import copy

from bs4 import Comment, NavigableString, Tag

MARKER = re.compile(r"^\s*([•o])\s+(?=\S)")


def _lines(node):
    """Split at explicit line breaks while preserving inline markup."""
    if not isinstance(node, Tag):
        return [[copy(node)]]
    if node.name == "br":
        return [[], []]
    lines = [[]]
    for child in node.children:
        parts = _lines(child)
        lines[-1].extend(parts[0])
        lines.extend(parts[1:])
    if node.name == "p":
        return lines
    wrapped = []
    for index, line in enumerate(lines):
        wrapper = copy(node)
        wrapper.clear()
        if index:
            wrapper.attrs.pop("id", None)
        wrapper.extend(line)
        wrapped.append([wrapper])
    return wrapped


def _strip_prefix(tag, count):
    for text in list(tag.find_all(string=True)):
        if isinstance(text, Comment):
            continue
        take = min(count, len(text))
        text.replace_with(str(text)[take:])
        count -= take
        if not count:
            break


def repair_typed_bullets(soup):
    """Repair groups with >=2 • items; o children need a colon-ended parent.

    Never infer a hierarchy from an isolated o, or rewrite existing lists,
    tables, headings, code, or note targets. No persistence happens here.
    """
    for parent in [soup, *list(soup.find_all(True))]:
        if parent.name in {"p", "ul", "ol", "li", "table", "pre", "code"}:
            continue
        if parent.find_parent(["ul", "ol", "li", "table", "pre", "code"]):
            continue
        group = []

        def flush():
            if not group:
                return
            units = []
            origins = {}
            touched = set()
            for paragraph in group:
                for index, line in enumerate(_lines(paragraph)):
                    p = soup.new_tag("p", attrs=dict(paragraph.attrs))
                    if index:
                        p.attrs.pop("id", None)
                    p.extend(line)
                    units.append(p)
                    origins[id(p)] = paragraph
            output = []
            repaired = False
            index = 0
            while index < len(units):
                match = MARKER.match(units[index].get_text())
                if not match or match[1] != "•":
                    output.append(units[index])
                    index += 1
                    continue
                end = index
                roots = 0
                allow_children = False
                while end < len(units):
                    marker = MARKER.match(units[end].get_text())
                    if not marker:
                        break
                    if marker[1] == "•":
                        roots += 1
                        allow_children = units[end].get_text().rstrip().endswith(":")
                    elif not allow_children:
                        break
                    end += 1
                if roots < 2:
                    output.extend(units[index:end])
                else:
                    touched.update(id(origins[id(unit)]) for unit in units[index:end])
                    ul = soup.new_tag("ul")
                    child_list = None
                    for unit in units[index:end]:
                        marker = MARKER.match(unit.get_text())
                        _strip_prefix(unit, marker.end())
                        unit.name = "li"
                        if marker[1] == "•":
                            ul.append(unit)
                            child_list = None
                        else:
                            if child_list is None:
                                child_list = soup.new_tag("ul")
                                ul.find_all("li", recursive=False)[-1].append(
                                    child_list
                                )
                            child_list.append(unit)
                    output.append(ul)
                    repaired = True
                index = end
            if repaired:
                preserved = set()
                for item in output:
                    origin = origins.get(id(item))
                    if origin is not None and id(origin) not in touched:
                        if id(origin) in preserved:
                            continue
                        preserved.add(id(origin))
                        item = copy(origin)
                    group[0].insert_before(item)
                for paragraph in group:
                    paragraph.decompose()
            group.clear()

        for node in list(parent.children):
            if isinstance(node, NavigableString) and not node.strip():
                continue
            if (
                isinstance(node, Tag)
                and node.name == "p"
                and not node.find(["img", "sup"])
                and not node.has_attr("id")
                and not node.find(id=True)
            ):
                group.append(node)
            else:
                flush()
        flush()
