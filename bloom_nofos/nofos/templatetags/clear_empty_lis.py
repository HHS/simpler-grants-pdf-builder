from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter()
def clear_empty_lis(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    for li in soup.find_all("li"):
        if not len(li.get_text().strip()):
            li.decompose()

    return mark_safe(str(soup))
