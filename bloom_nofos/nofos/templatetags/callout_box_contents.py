from django import template
from django.utils.safestring import mark_safe

from bs4 import BeautifulSoup

register = template.Library()


@register.filter()
def callout_box_contents(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    for paragraph in soup.find_all("p"):
        text = paragraph.get_text()
        if ":" not in text:
            paragraph.extract()

        else:
            split_text = text.split(":")
            strong_tag = soup.new_tag("strong")
            strong_tag.string, paragraph.string = split_text[0] + ":", split_text[1]
            paragraph.insert(0, strong_tag)

    return mark_safe(soup.prettify())
