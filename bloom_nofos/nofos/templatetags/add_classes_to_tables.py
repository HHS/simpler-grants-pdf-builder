from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

from .utils import (
    _add_class_if_not_exists_to_tag,
    add_class_to_table,
    add_class_to_table_rows,
)

register = template.Library()


@register.filter()
def add_classes_to_tables(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    for table in soup.find_all("table"):
        table_class = add_class_to_table(table)
        _add_class_if_not_exists_to_tag(table, table_class, "table")

        for table_row in table.find_all("tr"):
            table_row_class = add_class_to_table_rows(table_row)
            if table_row_class:
                _add_class_if_not_exists_to_tag(table_row, table_row_class, "tr")

    return mark_safe(str(soup))


@register.filter(name="has_heading_error")
def has_heading_error(subsection, heading_errors):
    heading_errors_ids = [error["subsection"].html_id for error in heading_errors]
    return subsection.html_id in heading_errors_ids


@register.filter(name="get_heading_error")
def get_heading_error(subsection, heading_errors):
    heading_error = next(
        he for he in heading_errors if he["subsection"].html_id == subsection.html_id
    )
    if heading_error:
        return heading_error["error"]
    return ""
