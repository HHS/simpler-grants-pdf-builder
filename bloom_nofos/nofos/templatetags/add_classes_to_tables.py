from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

from .utils import _add_class_if_not_exists_to_tag, add_class_to_table

register = template.Library()


@register.filter()
def add_classes_to_tables(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    for table in soup.find_all("table"):
        table_class = add_class_to_table(table)
        _add_class_if_not_exists_to_tag(table, table_class, "table")

    return mark_safe(str(soup))
