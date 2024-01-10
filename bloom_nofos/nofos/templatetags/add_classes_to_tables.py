from django import template
from django.utils.safestring import mark_safe

from bs4 import BeautifulSoup

from .utils import add_class_to_table

register = template.Library()


@register.filter()
def add_classes_to_tables(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    for table in soup.find_all("table"):
        table_class = add_class_to_table(table)
        table["class"] = table_class

    return mark_safe(str(soup))
