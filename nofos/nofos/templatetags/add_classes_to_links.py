from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

from ..nofo import is_dangling_link_anchor

register = template.Library()


@register.filter()
def add_classes_to_broken_links(html_string, broken_links):
    """
    Adds "nofo_edit--broken-link" class to links with href matching my broken links array, and a tooltip for broken links.
    Also flags links whose href names no destination at all ("", whitespace, or "about:blank"): those are reported on the
    external-links page rather than in the broken-links panel, so they never appear in `broken_links`, but they still get
    highlighted in place so a designer can find them. They get their own pop-up message.
    Also adds "nofo_edit--broken-link" class to links with NO href but WITH visible text and no `id`/`name`, as these
    are broken bookmark links (e.g. martor stripped the href of a disallowed URL scheme). Anchors with no href that
    have an `id`/`name` (e.g. <a id="...">), or no text at all, are bookmark targets, not links, and are not flagged
    -- even if they have visible text (some bookmark targets carry over their original visible label; see
    preserve_bookmark_links in nofo.py). These share the "no destination" pop-up message with the case above: martor
    strips the href for both "bookmark://" and "about:", so this branch cannot tell which one it is looking at, and
    naming either scheme specifically would be a guess that is wrong half the time.

    Args:
        html_string (str): The HTML content of a subsection as a string.
        broken_links (list of dict): A list of broken links dicts returned from "find_broken_links" function nofo.py.

    Example:
        html = '<p><a href="#_Purpose">Visit</a></p>'
        broken_links = [{'link_href': '#_Purpose'}]
        result = add_classes_to_broken_links(html, broken_links)
        # Output: '<p><a href="#_Purpose" class="nofo_edit--broken-link usa-tooltip" data-position="bottom" title="Broken link">Visit</a></p>'
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
        elif is_dangling_link_anchor(link):
            # An href that names no destination: "", whitespace, or
            # "about:blank". These are reported on the external-links page
            # rather than in the broken-links panel (they point outside the
            # NOFO, not at one of its anchors), so they never appear in
            # "link_hrefs" -- but a designer still needs to see them in place.
            link["class"] = link.get("class", []) + [
                "nofo_edit--broken-link",
                "usa-tooltip",
            ]
            link["data-position"] = "bottom"
            link["title"] = "Link with no destination"

    # bookmark links show up with no href because of martor
    #
    # only flag <a> tags with visible text AND no id/name: that's the
    # signature of a martor-stripped link (e.g. a disallowed "bookmark://"
    # scheme gets its href stripped by bleach, leaving the link text behind
    # with no href). An <a> tag with an id or name is a bookmark *target*
    # (e.g. <a id="...">), not a link -- some targets carry over their
    # original visible text (see preserve_bookmark_links in nofo.py, which
    # only merges/removes *empty* bookmark targets and leaves non-empty ones
    # like this alone) -- so text alone isn't enough to call it broken.
    for link2 in soup.find_all("a", href=False):
        if not link2.get_text(strip=True):
            continue
        if link2.get("id") or link2.get("name"):
            continue

        link2["class"] = link2.get("class", []) + [
            "nofo_edit--broken-link",
            "usa-tooltip",
        ]
        link2["data-position"] = "bottom"
        link2["title"] = "Link with no destination"

    return mark_safe(str(soup))
