import re

from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

from .utils import format_footnote_ref_html, get_footnote_type, is_footnote_ref

register = template.Library()


@register.filter()
def add_footnote_ids(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    repeated_returns = {}
    for link in soup.find_all("a", href=True):
        match = re.fullmatch(
            r"(#(?:footnote|endnote)-ref-(?!manual-).+)-repeat-([2-9][0-9]*|1[0-9]+)",
            link["href"],
        )
        if match and link.get_text(strip=True) == "↑":
            repeated_returns[match[1]] = True
            link["aria-label"] = f"Return to citation reference {match[2]}"
    for link in soup.find_all("a", href=True):
        if link["href"] in repeated_returns and link.get_text(strip=True) == "↑":
            link["aria-label"] = "Return to first citation reference"
    for a in soup.find_all("a"):
        footnote_num = is_footnote_ref(a)
        footnote_type = get_footnote_type(a)

        if footnote_type == "html" and footnote_num:
            format_footnote_ref_html(a)

        # The Markdown sanitizer intentionally strips arbitrary aria-labels.
        # Restore labels only for our generated notes after sanitization. Native
        # note IDs need not contain their visible numbers and are left alone.
        if a.get("id", "").startswith("endnote-ref-manual-"):
            match = re.fullmatch(r"\[([1-9][0-9]*)\]", a.get_text(strip=True))
            if match:
                a["aria-label"] = f"Endnote {match[1]}"
        elif a.get("href", "").startswith("#endnote-ref-manual-"):
            target = re.fullmatch(
                r"#endnote-ref-manual-([1-9][0-9]*)(?:-[0-9]+)?", a["href"]
            )
            if target:
                a["aria-label"] = f"Return to endnote {target[1]} reference"

    return mark_safe(str(soup))
