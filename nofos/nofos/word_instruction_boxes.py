"""Upload-only cleanup of the verified HHS pale-blue instruction container.

Do not infer intent from prose, paragraph styles, dates or saved NOFO metadata.
Unknown shapes survive conversion for human review. Source uploads are never
modified. Composer deliberately keeps its existing conversion contract.
"""

import colorsys
import posixpath
import re
from io import BytesIO
from xml.dom import minidom
from zipfile import ZipFile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
WPS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
V = "urn:schemas-microsoft-com:vml"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
R = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PALE_BLUE = (220, 234, 247)  # DCEAF7, verified HHS master container fill.
REVIEW_MESSAGE = (
    "Some Word text boxes have an unrecognized or conflicting fill. "
    "Their content was kept. Review the imported text against the source Word "
    "document for writer instructions and applicant-facing content."
)


def _xml(data):
    # Preserve namespace prefixes and mc:Ignorable values when serializing.
    # Reject declarations rather than expanding uploaded entities or fetching DTDs.
    declarations = data.replace(b"\0", b"").upper()
    if b"<!DOCTYPE" in declarations or b"<!ENTITY" in declarations:
        raise ValueError("Unsupported XML declaration")
    return minidom.parseString(data)


def _nodes(node, namespace, name):
    return list(node.getElementsByTagNameNS(namespace, name))


def _children(node):
    return [child for child in node.childNodes if child.nodeType == child.ELEMENT_NODE]


def _rgb(value):
    if value.strip().lower() == "white":
        return (255, 255, 255)
    # VML can append a palette index, e.g. '#dceaf7 [351]'.
    match = re.fullmatch(r"#?([0-9a-fA-F]{6})(?:\s+\[\d+\])?", value)
    if not match:
        return None
    return tuple(int(match[1][i : i + 2], 16) for i in (0, 2, 4))


def _theme(archive):
    colors = {}
    mapping = {"tx1": "dk1", "tx2": "dk2", "bg1": "lt1", "bg2": "lt2"}
    names = set(archive.namelist())
    if "word/settings.xml" in names:
        settings = _xml(archive.read("word/settings.xml"))
        maps = _nodes(settings, W, "clrSchemeMapping")
        aliases = {
            "dark1": "dk1",
            "dark2": "dk2",
            "light1": "lt1",
            "light2": "lt2",
            "hyperlink": "hlink",
            "followedHyperlink": "folHlink",
        }
        if maps:
            for key, attribute in (
                ("tx1", "t1"),
                ("tx2", "t2"),
                ("bg1", "bg1"),
                ("bg2", "bg2"),
                *((f"accent{i}", f"accent{i}") for i in range(1, 7)),
                ("hlink", "hyperlink"),
                ("folHlink", "followedHyperlink"),
            ):
                value = maps[0].getAttributeNS(W, attribute)
                if value:
                    mapping[key] = aliases.get(value, value)
    if "word/_rels/document.xml.rels" in names:
        rels = _xml(archive.read("word/_rels/document.xml.rels"))
        for rel in _nodes(rels, R, "Relationship"):
            if (
                not rel.getAttribute("Type").endswith("/theme")
                or rel.getAttribute("TargetMode") == "External"
            ):
                continue
            target = rel.getAttribute("Target")
            path = (
                posixpath.normpath(posixpath.join("word", target))
                if not target.startswith("/")
                else target.lstrip("/")
            )
            if path not in names:
                continue
            scheme = _nodes(_xml(archive.read(path)), A, "clrScheme")
            if scheme:
                for entry in _children(scheme[0]):
                    values = _children(entry)
                    if len(values) == 1:
                        color = values[0]
                        # Theme-level transforms also affect the rendered fill.
                        # Preserve such entries rather than guessing a base RGB.
                        colors[entry.localName] = (
                            None
                            if _children(color)
                            else _rgb(
                                color.getAttribute("lastClr")
                                if color.localName == "sysClr"
                                else color.getAttribute("val")
                            )
                        )
    return colors, mapping


def _drawing_fill(shape, colors, mapping):
    if _nodes(shape, A, "clrMapOvr"):
        return "unknown"
    properties = [
        child
        for child in _children(shape)
        if child.namespaceURI == WPS and child.localName == "spPr"
    ]
    if len(properties) != 1:
        return "unknown"
    fills = [
        child
        for child in _children(properties[0])
        if child.namespaceURI == A and child.localName.endswith("Fill")
    ]
    if not fills:
        return "unknown" if _nodes(shape, WPS, "style") else "unfilled"
    if len(fills) != 1:
        return "unknown"
    fill = fills[0]
    if fill.localName == "noFill":
        return "unfilled"
    if fill.localName != "solidFill" or len(_children(fill)) != 1:
        return "unknown"
    color = _children(fill)[0]
    if color.namespaceURI != A:
        return "unknown"
    if color.localName == "schemeClr":
        key = color.getAttribute("val")
        rgb = colors.get(mapping.get(key, key))
    elif color.localName == "srgbClr":
        rgb = _rgb(color.getAttribute("val"))
    elif color.localName == "sysClr":
        rgb = _rgb(color.getAttribute("lastClr"))
    else:
        return "unknown"
    if rgb is None:
        return "unknown"
    rgb = tuple(c / 255 for c in rgb)
    for transform in _children(color):
        if transform.namespaceURI != A:
            return "unknown"
        try:
            amount = int(transform.getAttribute("val")) / 100000
        except ValueError:
            return "unknown"
        if not 0 <= amount <= 1:
            return "unknown"
        if transform.localName == "alpha":
            if amount == 0:
                return "unfilled"
            if amount != 1:
                return "unknown"
        elif transform.localName in ("lumMod", "lumOff"):
            h, lightness, saturation = colorsys.rgb_to_hls(*rgb)
            lightness = (
                lightness * amount
                if transform.localName == "lumMod"
                else lightness + amount
            )
            rgb = colorsys.hls_to_rgb(h, min(1, lightness), saturation)
        elif transform.localName == "tint":
            # OOXML tint is the retained source fraction: zero is white,
            # 100000 is unchanged. It is not the fraction of white added.
            rgb = tuple(c * amount + (1 - amount) for c in rgb)
        elif transform.localName == "shade":
            rgb = tuple(c * amount for c in rgb)
        else:
            return "unknown"
    return tuple(round(c * 255) for c in rgb)


def _vml_fill(shape):
    if shape.getAttribute("filled").lower() in ("f", "false", "0"):
        return "unfilled"
    fills = _nodes(shape, V, "fill")
    if len(fills) > 1:
        return "unknown"
    if fills:
        fill = fills[0]
        if fill.getAttribute("on").lower() in ("f", "false", "0") or fill.getAttribute(
            "opacity"
        ) in ("0", "0%"):
            return "unfilled"
        if fill.getAttribute("type") not in ("", "solid") or fill.getAttribute(
            "opacity"
        ) not in ("", "1", "100%"):
            return "unknown"
        value = fill.getAttribute("color") or shape.getAttribute("fillcolor")
    else:
        value = shape.getAttribute("fillcolor")
    return _rgb(value) or ("unknown" if value else "unfilled")


def _fill(box, colors, mapping):
    parent = box.parentNode
    while parent.nodeType == parent.ELEMENT_NODE:
        if parent.namespaceURI == WPS and parent.localName == "wsp":
            return _drawing_fill(parent, colors, mapping)
        if parent.namespaceURI == V and parent.localName in (
            "shape",
            "rect",
            "roundrect",
        ):
            return _vml_fill(parent)
        parent = parent.parentNode
    return "unknown"


def _blue(fill):
    # One RGB level accommodates equivalent Word rounding, not a broad hue range.
    return isinstance(fill, tuple) and all(
        abs(a - b) <= 1 for a, b in zip(fill, PALE_BLUE)
    )


def _link_keys(box, relationships):
    result = []
    for link in _nodes(box, W, "hyperlink"):
        attributes = []
        for attribute in link.attributes.values():
            namespace = attribute.namespaceURI or ""
            name = attribute.localName
            if namespace == "http://www.w3.org/2000/xmlns/" or (
                namespace == W and name == "history"
            ):
                continue
            value = attribute.value
            if namespace == OFFICE_R and name == "id":
                value = repr(relationships.get(value, ("unresolved", value)))
            attributes.append((namespace, name, value))
        result.append(tuple(sorted(attributes)))
    return result


def clean_instruction_boxes(upload):
    """Return a seekable conversion copy and content-free review warnings.

    Remove only the shape/compatibility container, never its enclosing paragraph
    or run. No text boxes: return the original stream without rewriting its ZIP.
    """
    upload.seek(0)
    with ZipFile(upload) as archive:
        document = _xml(archive.read("word/document.xml"))
        boxes = _nodes(document, W, "txbxContent")
        if not boxes:
            upload.seek(0)
            return upload, ()
        colors, mapping = _theme(archive)
        relationships = {}
        if "word/_rels/document.xml.rels" in archive.namelist():
            rels = _xml(archive.read("word/_rels/document.xml.rels"))
            relationships = {
                rel.getAttribute("Id"): (
                    rel.getAttribute("TargetMode"),
                    rel.getAttribute("Target"),
                )
                for rel in _nodes(rels, R, "Relationship")
            }
        units = []
        uncontained = False
        for box in boxes:
            parent = box.parentNode
            unit = None
            while parent.nodeType == parent.ELEMENT_NODE:
                if parent.namespaceURI == W and parent.localName in ("drawing", "pict"):
                    unit = parent
                if parent.namespaceURI == MC and parent.localName == "AlternateContent":
                    unit = parent
                    break
                parent = parent.parentNode
            if unit is not None and unit not in units:
                units.append(unit)
            if unit is None:
                uncontained = True
        review = uncontained
        removed = False
        for unit in units:
            contents = _nodes(unit, W, "txbxContent")
            fills = [_fill(box, colors, mapping) for box in contents]
            texts = [
                " ".join(
                    " ".join(
                        t.firstChild.data if t.firstChild else ""
                        for t in _nodes(box, W, "t")
                    ).split()
                )
                for box in contents
            ]
            content_tags = (
                (W, "t"),
                (W, "bookmarkStart"),
                (W, "bookmarkEnd"),
                (W, "hyperlink"),
                (A, "blip"),
                (V, "imagedata"),
            )
            contained = {
                id(node)
                for box in contents
                for namespace, name in content_tags
                for node in _nodes(box, namespace, name)
            }
            adjacent_text = any(
                id(node) not in contained
                for namespace, name in content_tags
                for node in _nodes(unit, namespace, name)
            )
            fallbacks = _nodes(unit, MC, "Fallback")
            choices = _nodes(unit, MC, "Choice")
            paired = (
                unit.namespaceURI == MC
                and len(contents) == 2
                and len(fallbacks) == len(choices) == 1
                and len(_nodes(fallbacks[0], W, "txbxContent")) == 1
                and len(_nodes(choices[0], W, "txbxContent")) == 1
            )
            link_keys = [_link_keys(box, relationships) for box in contents]
            paired_agreement = (
                paired and len(set(texts)) == 1 and link_keys[0] == link_keys[1]
            )
            supported_count = paired if unit.namespaceURI == MC else len(contents) == 1
            if (
                supported_count
                and all(_blue(fill) for fill in fills)
                and len(set(texts)) == 1
                and (unit.namespaceURI != MC or paired_agreement)
                and not adjacent_text
            ):
                unit.parentNode.removeChild(unit)
                removed = True
            elif (unit.namespaceURI == MC and not paired_agreement) or any(
                _blue(fill)
                or fill == "unknown"
                or (isinstance(fill, tuple) and fill != (255, 255, 255))
                for fill in fills
            ):
                review = True
            if unit.parentNode is not None:
                # Mammoth reads AlternateContent's VML fallback, but silently
                # ignores standalone DrawingML text. Supply only missing text
                # copies as VML, retaining paragraphs, lists and relationships.
                rendered_boxes = [
                    box
                    for fallback in fallbacks
                    for box in _nodes(fallback, W, "txbxContent")
                ]
                if unit.namespaceURI != MC:
                    rendered_boxes = [
                        box for box in contents if box.parentNode.namespaceURI == V
                    ]
                for box in contents:
                    if box in rendered_boxes or paired_agreement:
                        continue
                    # Independent boxes can have identical labels but distinct
                    # links/content. Only a verified Choice/Fallback pair is a
                    # duplicate; never deduplicate standalone/grouped boxes.
                    prefix = box.prefix
                    pict = document.createElementNS(
                        W, f"{prefix}:pict" if prefix else "pict"
                    )
                    pict.setAttributeNS(
                        "http://www.w3.org/2000/xmlns/",
                        f"xmlns:{prefix}" if prefix else "xmlns",
                        W,
                    )
                    pict.appendChild(box.cloneNode(deep=True))
                    unit.parentNode.insertBefore(pict, unit)
                    removed = True  # conversion copy must be serialized
                # Do not remove unsupported drawings: they may also contain
                # images or other non-text content. Only their text is copied.
        if not removed:
            upload.seek(0)
            return upload, (REVIEW_MESSAGE,) if review else ()
        result = BytesIO()
        with ZipFile(result, "w") as output:
            for entry in archive.infolist():
                output.writestr(
                    entry,
                    (
                        document.toxml(encoding="UTF-8")
                        if entry.filename == "word/document.xml"
                        else archive.read(entry)
                    ),
                )
    result.seek(0)
    return result, (REVIEW_MESSAGE,) if review else ()
