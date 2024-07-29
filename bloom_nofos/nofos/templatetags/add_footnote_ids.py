from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

from .utils import format_footnote_ref_html, get_footnote_type, is_footnote_ref

register = template.Library()


@register.filter()
def add_footnote_ids(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    for a in soup.find_all("a"):
        footnote_num = is_footnote_ref(a)
        footnote_type = get_footnote_type(a)

        if footnote_num and footnote_type:
            if footnote_type == "html":
                format_footnote_ref_html(a)
            if not a.get("href").startswith("#ftnt_"):
                a.wrap(soup.new_tag("sup"))

    return mark_safe(str(soup))
