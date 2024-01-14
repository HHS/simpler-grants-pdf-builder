from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

from .utils import format_footnote_ref, is_footnote_ref

register = template.Library()


@register.filter()
def add_footnote_ids(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    for a in soup.find_all("a"):
        footnote_num = is_footnote_ref(a)
        if footnote_num:
            format_footnote_ref(a)
            if not a.get("href").startswith("#ftnt_"):
                a.wrap(soup.new_tag("sup"))

    return mark_safe(str(soup))
