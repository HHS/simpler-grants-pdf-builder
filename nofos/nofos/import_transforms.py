"""
Preserve supported Word-only semantics before Mammoth emits HTML.

Implements import rules IMPORT-001, IMPORT-060 and IMPORT-005 in documentation/IMPORT_RULES.md.
Update those entries if you change this file's behavior.
"""

from io import BytesIO
from xml.dom import minidom
from zipfile import ZipFile

from mammoth import documents

from .content_constants import APPLICATION_CHECKLIST_CHILD_CLASS

APPLICATION_CHECKLIST_CHILD_STYLE_NAME = "Application Checklist Child"
APPLICATION_CHECKLIST_CHILD_STYLE_MAP = (
    f"p[style-name='{APPLICATION_CHECKLIST_CHILD_STYLE_NAME}'] "
    f"=> p.{APPLICATION_CHECKLIST_CHILD_CLASS}:fresh"
)

CHECKBOX_PREFIXES = ("\u00a8", "\u007f", "\u2610", "\u25fb")
WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _word_xml(data):
    declarations = data.replace(b"\0", b"").upper()
    if b"<!DOCTYPE" in declarations or b"<!ENTITY" in declarations:
        raise ValueError("Unsupported XML declaration")
    return minidom.parseString(data)


def _word_child(node, name):
    return (
        next(
            (
                child
                for child in node.childNodes
                if child.nodeType == child.ELEMENT_NODE
                and child.namespaceURI == WORD_NAMESPACE
                and child.localName == name
            ),
            None,
        )
        if node is not None
        else None
    )


def _is_supported_strong1_style(style):
    """Recognize a direct, bold-only definition, not a name-based guess.

    Inheritance and additional formatting stay on Mammoth's existing path,
    including its unrecognized-style warning. Do not remove their style link.
    """
    name = _word_child(style, "name")
    if (
        style.getAttributeNS(WORD_NAMESPACE, "type") != "character"
        or not style.getAttributeNS(WORD_NAMESPACE, "styleId")
        or name is None
        or name.getAttributeNS(WORD_NAMESPACE, "val") != "Strong1"
    ):
        return False
    # These describe the style in Word's UI, not inherited/run formatting.
    metadata = {
        "name",
        "aliases",
        "uiPriority",
        "semiHidden",
        "unhideWhenUsed",
        "qFormat",
        "rsid",
    }
    children = [
        child for child in style.childNodes if child.nodeType == child.ELEMENT_NODE
    ]
    if any(
        child.namespaceURI != WORD_NAMESPACE
        or child.localName not in metadata | {"rPr"}
        for child in children
    ):
        return False
    properties = [child for child in children if child.localName == "rPr"]
    if len(properties) != 1:
        return False
    formatting = [
        child
        for child in properties[0].childNodes
        if child.nodeType == child.ELEMENT_NODE
    ]
    return (
        len(formatting) == 1
        and formatting[0].namespaceURI == WORD_NAMESPACE
        and formatting[0].localName == "b"
        and formatting[0].getAttributeNS(WORD_NAMESPACE, "val")
        in ("", "1", "true", "on")
    )


def normalize_strong1_runs(upload):
    """Materialize Strong1 bold on a conversion copy, preserving run overrides.

    Mammoth does not resolve custom character-style bold and treats both an
    absent w:b and w:b=0 as False. Resolve the style before that distinction is
    lost, then remove its run reference so it cannot add a second bold wrapper.
    """
    upload.seek(0)
    with ZipFile(upload) as archive:
        if "word/styles.xml" not in archive.namelist():
            upload.seek(0)
            return upload
        styles = _word_xml(archive.read("word/styles.xml"))
        style_ids = set()
        for style in styles.getElementsByTagNameNS(WORD_NAMESPACE, "style"):
            if _is_supported_strong1_style(style):
                style_ids.add(style.getAttributeNS(WORD_NAMESPACE, "styleId"))
        replacements = {}
        if style_ids:
            for part in (
                "word/document.xml",
                "word/footnotes.xml",
                "word/endnotes.xml",
            ):
                if part not in archive.namelist():
                    continue
                document = _word_xml(archive.read(part))
                changed = False
                for run in document.getElementsByTagNameNS(WORD_NAMESPACE, "r"):
                    properties = _word_child(run, "rPr")
                    style = _word_child(properties, "rStyle")
                    if (
                        style is None
                        or style.getAttributeNS(WORD_NAMESPACE, "val") not in style_ids
                    ):
                        continue
                    bold = _word_child(properties, "b")
                    if bold is None:
                        bold = document.createElementNS(
                            WORD_NAMESPACE, f"{style.prefix}:b" if style.prefix else "b"
                        )
                        properties.appendChild(bold)
                    elif bold.getAttributeNS(WORD_NAMESPACE, "val") == "off":
                        # Word accepts "off"; Mammoth recognizes "0"/"false".
                        bold.setAttributeNS(
                            WORD_NAMESPACE,
                            bold.getAttributeNodeNS(WORD_NAMESPACE, "val").name,
                            "0",
                        )
                    properties.removeChild(style)
                    changed = True
                if changed:
                    replacements[part] = document.toxml(encoding="UTF-8")
        if not replacements:
            upload.seek(0)
            return upload
        result = BytesIO()
        with ZipFile(result, "w") as output:
            for entry in archive.infolist():
                output.writestr(
                    entry,
                    (
                        replacements[entry.filename]
                        if entry.filename in replacements
                        else archive.read(entry)
                    ),
                )
    result.seek(0)
    return result


def omit_leading_word_title(upload):
    """Omit one Title paragraph from a conversion copy, never the source upload.

    Inspect original body elements: Mammoth can omit unsupported elements before
    its document transform, which must not make a later Title look like the first.
    Preserve namespace prefixes, including those named by mc:Ignorable.
    """
    upload.seek(0)
    with ZipFile(upload) as archive:
        document = _word_xml(archive.read("word/document.xml"))
        bodies = document.getElementsByTagNameNS(WORD_NAMESPACE, "body")
        first = (
            next(
                (
                    node
                    for node in bodies[0].childNodes
                    if node.nodeType == node.ELEMENT_NODE
                    and not (
                        node.namespaceURI == WORD_NAMESPACE
                        and node.localName == "sectPr"
                    )
                ),
                None,
            )
            if bodies
            else None
        )
        style_id = None
        if (
            first is not None
            and first.namespaceURI == WORD_NAMESPACE
            and first.localName == "p"
        ):
            style = _word_child(_word_child(first, "pPr"), "pStyle")
            if style is not None:
                style_id = style.getAttributeNS(WORD_NAMESPACE, "val")
        # Style IDs may be localized or renamed; verify the paragraph style's
        # actual name and type, not the text, font, run style, or basedOn chain.
        is_title = False
        if style_id and "word/styles.xml" in archive.namelist():
            styles = _word_xml(archive.read("word/styles.xml"))
            for style in styles.getElementsByTagNameNS(WORD_NAMESPACE, "style"):
                if (
                    style.getAttributeNS(WORD_NAMESPACE, "styleId") == style_id
                    and style.getAttributeNS(WORD_NAMESPACE, "type") == "paragraph"
                ):
                    name = _word_child(style, "name")
                    is_title = bool(
                        name
                        and name.getAttributeNS(WORD_NAMESPACE, "val").casefold()
                        == "title"
                    )
                    break
        has_drawing = first is not None and any(
            first.getElementsByTagNameNS(WORD_NAMESPACE, name)
            for name in ("drawing", "pict", "object")
        )
        if not is_title or has_drawing:
            upload.seek(0)
            return upload
        first.parentNode.removeChild(first)
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
    return result


def transform_word_document(document):
    """Preserve supported Word-only semantics before Mammoth emits HTML."""
    return _transform_element(document)


def _transform_element(element):
    if isinstance(element, documents.Table):
        return _transform_table(element)

    if isinstance(element, (documents.HasChildren, documents.TableCellUnmerged)):
        return element.copy(
            children=[_transform_element(child) for child in element.children]
        )

    return element


def _transform_table(table):
    baseline_indent = None
    previous_checkbox_indent = None
    child_run_active = False
    transformed_children = []

    for child in table.children:
        if not isinstance(child, documents.TableRow):
            transformed_children.append(_transform_element(child))
            continue

        checkbox_paragraph = _first_column_checkbox_paragraph(child)
        paragraph_to_mark = None

        if checkbox_paragraph is None:
            previous_checkbox_indent = None
            child_run_active = False
        else:
            indent = _paragraph_start_indent(checkbox_paragraph)
            if baseline_indent is None or indent < baseline_indent:
                baseline_indent = indent

            starts_child_run = (
                previous_checkbox_indent is not None
                and previous_checkbox_indent < indent
            )
            is_child = indent > baseline_indent and (
                starts_child_run or child_run_active
            )

            if is_child:
                paragraph_to_mark = checkbox_paragraph

            previous_checkbox_indent = indent
            child_run_active = is_child

        transformed_children.append(
            _transform_table_row(child, paragraph_to_mark=paragraph_to_mark)
        )

    return table.copy(children=transformed_children)


def _transform_table_row(row, paragraph_to_mark):
    transformed_children = []

    for child in row.children:
        if isinstance(child, documents.TableCell):
            transformed_children.append(
                _transform_table_cell(
                    child,
                    paragraph_to_mark=paragraph_to_mark,
                )
            )
        else:
            transformed_children.append(_transform_element(child))

    return row.copy(children=transformed_children)


def _transform_table_cell(cell, paragraph_to_mark):
    transformed_children = []

    for child in cell.children:
        transformed_child = _transform_element(child)
        if child is paragraph_to_mark:
            transformed_child = transformed_child.copy(
                style_name=APPLICATION_CHECKLIST_CHILD_STYLE_NAME
            )
        transformed_children.append(transformed_child)

    return cell.copy(children=transformed_children)


def _first_column_checkbox_paragraph(row):
    first_cell = next(
        (child for child in row.children if isinstance(child, documents.TableCell)),
        None,
    )
    if first_cell is None:
        return None

    return next(
        (
            child
            for child in first_cell.children
            if isinstance(child, documents.Paragraph)
            and _paragraph_text(child).lstrip().startswith(CHECKBOX_PREFIXES)
        ),
        None,
    )


def _paragraph_text(element):
    if isinstance(element, documents.Text):
        return element.value

    return "".join(_paragraph_text(child) for child in getattr(element, "children", []))


def _paragraph_start_indent(paragraph):
    start = getattr(getattr(paragraph, "indent", None), "start", None)
    try:
        return int(start)
    except (TypeError, ValueError):
        return 0
