from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

from .utils import convert_paragraph_to_searchable_hr

register = template.Library()


@register.filter()
def convert_paragraphs_to_hrs(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    for p in soup.find_all(
        "p",
        string=lambda text: text
        in [
            "page-break",
            "page-break-before",
            "page-break-after",
            "column-break-before",
            "column-break-after",
        ],
    ):
        convert_paragraph_to_searchable_hr(p)

    return mark_safe(str(soup))
