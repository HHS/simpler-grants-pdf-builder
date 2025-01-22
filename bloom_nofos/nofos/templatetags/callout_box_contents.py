import re

from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

from .utils import wrap_text_before_colon_in_strong

register = template.Library()


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
