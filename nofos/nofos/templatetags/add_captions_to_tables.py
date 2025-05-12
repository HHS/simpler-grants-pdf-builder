from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

from .utils import add_caption_to_table, is_callout_box_table_markdown

register = template.Library()


@register.filter()
def add_captions_to_tables(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    for table in soup.find_all("table"):
        if not is_callout_box_table_markdown(table):
            add_caption_to_table(table)

    return mark_safe(str(soup))
