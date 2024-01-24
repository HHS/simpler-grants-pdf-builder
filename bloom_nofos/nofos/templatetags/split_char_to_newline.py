from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter()
def split_char_to_newline(text, character="|", maxsplit=-1):
    if character in text:
        split_text = text.split(character, maxsplit)
        # strip whitespace
        split_text = map(str.strip, split_text)
        return mark_safe("<br>".join(split_text))

    return text
