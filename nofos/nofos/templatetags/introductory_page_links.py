from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

from nofos.introductory_page import INTRO_ANCHOR

register = template.Library()


@register.filter
def introductory_page_links(html, nofo):
    """A disabled page is not a link destination; keep its authored text.

    Rendering only: the stored body and legacy records are never rewritten.
    """
    if (
        nofo.has_imported_introduction
        or nofo.before_you_begin != "none"
        or nofo.number == "hrsa-application-guide"
    ):
        return html
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.find_all("a", href=f"#{INTRO_ANCHOR}"):
        link.unwrap()
    return mark_safe(str(soup))
