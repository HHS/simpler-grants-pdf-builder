from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter()
def add_classes_to_broken_links(html_string, broken_links):
    """
    Adds "nofo_edit--broken-link" class to links with href matching my broken links array, and a tooltip for broken links.
    Also adds "nofo_edit--broken-link" class to links with NO href but WITH visible text, as these are broken bookmark
    links (e.g. martor stripped the href of a disallowed URL scheme). Anchors with no href and no text are bookmark
    targets (e.g. <a id="...">), not links, and are not flagged. Broken bookmark links get a more specific pop-up message.

    Args:
        html_string (str): The HTML content of a subsection as a string.
        broken_links (list of dict): A list of broken links dicts returned from "find_broken_links" function nofo.py.

    Example:
        html = '<p><a href="http://example.com">Visit</a></p>'
        broken_links = [{'href': 'http://example.com'}]
        result = add_classes_to_broken_links(html, broken_links)
        # Output: '<p><a href="http://example.com" class="nofo_edit--broken-link usa-tooltip" data-position="top" title="Broken link">Visit</a></p>'
    """
    soup = BeautifulSoup(html_string, "html.parser")
    link_hrefs = [link["link_href"] for link in broken_links]

    for link in soup.find_all("a", href=True):
        if link["href"] in link_hrefs:
            # Add "nofo_edit--broken-link" class to links with a matching href (and tooltip)
            link["class"] = link.get("class", []) + [
                "nofo_edit--broken-link",
                "usa-tooltip",
            ]
            link["data-position"] = "bottom"
            link["title"] = "Broken link"

    # bookmark links show up with no href because of martor
    # add the same classes, but a different popup message
    #
    # only flag <a> tags with visible text: that's the signature of a martor-
    # stripped link (e.g. a disallowed "bookmark://" scheme gets its href
    # stripped by bleach, leaving the link text behind with no href). An <a>
    # tag with no text and no href is a bookmark *target* (e.g. <a id="...">),
    # not a link, and is not broken just because it lacks an href.
    for link2 in soup.find_all("a", href=False):
        if not link2.get_text(strip=True):
            continue

        link2["class"] = link2.get("class", []) + [
            "nofo_edit--broken-link",
            "usa-tooltip",
        ]
        link2["data-position"] = "bottom"
        link2["title"] = "Broken bookmark link"

    return mark_safe(str(soup))
