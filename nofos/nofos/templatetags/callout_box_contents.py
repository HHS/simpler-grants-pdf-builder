import re

from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

from .utils import wrap_text_before_colon_in_strong

register = template.Library()


HELP_CONTACTS_CALLOUT = re.compile(
    r"^need (?:any )?help\? (?:please )?(?:see|visit|go to|refer to) "
    r"(?:the )?contacts? and support(?= (?:section|for)\b|[.!?,;:]|$)",
    re.IGNORECASE,
)


@register.simple_tag
def show_contact_callout_icon(markdown_body, rendered_body, break_colons):
    if "uestions?" in markdown_body:
        return True
    if break_colons:
        return False

    soup = BeautifulSoup(rendered_body, "html.parser")
    first_block = soup.find()
    if first_block is None or first_block.name != "p":
        return False

    text = " ".join(first_block.get_text().split())
    return bool(HELP_CONTACTS_CALLOUT.match(text))


@register.filter()
def callout_box_contents(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    for paragraph in soup.find_all("p"):
        text = paragraph.get_text()
        if ":" in text:
            wrap_text_before_colon_in_strong(paragraph, soup)
        if text.startswith("Have questions?"):
            strong_with_questions = paragraph.find(
                "strong", text=re.compile("questions?", flags=re.IGNORECASE)
            )
            if strong_with_questions:
                strong_with_questions.insert_after(soup.new_tag("br"))

    return mark_safe(str(soup))
