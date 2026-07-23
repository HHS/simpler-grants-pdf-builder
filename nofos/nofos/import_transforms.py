from mammoth import documents

APPLICATION_CHECKLIST_CHILD_CLASS = "application-list--left-indent"
APPLICATION_CHECKLIST_CHILD_STYLE_NAME = "Application Checklist Child"
APPLICATION_CHECKLIST_CHILD_STYLE_MAP = (
    f"p[style-name='{APPLICATION_CHECKLIST_CHILD_STYLE_NAME}'] "
    f"=> p.{APPLICATION_CHECKLIST_CHILD_CLASS}:fresh"
)

CHECKBOX_PREFIXES = ("\u00a8", "\u007f", "\u2610", "\u25fb")


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
