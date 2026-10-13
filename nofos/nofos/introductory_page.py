"""Builder-owned introductory page selection and source destination capture."""

from bs4 import NavigableString

INTRO_ANCHOR = "section--before-you-begin"
FAMILY_ATTRIBUTE = "data-nofo-introductory-family"
HEADING_NAMES = {
    "before you begin": "legacy",
    "before you get started": "get_started",
}


def introductory_heading_name(tag):
    text = "".join(
        (
            str(node)
            if isinstance(node, NavigableString)
            else " " if node.name == "br" else ""
        )
        for node in tag.descendants
    )
    return " ".join(text.casefold().split()).strip(" :.-")


def introductory_family_from_soup(soup):
    body = soup.body
    return body.get(FAMILY_ATTRIBUTE, "") if body else ""


def capture_introductory_page(soup, *, page_enabled=True):
    """Capture only a unique structural destination, never visible link text.

    The private body attribute survives the existing confirmation serialization;
    it is not copied into stored sections or rendered output.
    """
    from .nofo import add_body_if_no_body, unwrap_heading_containers

    soup = add_body_if_no_body(soup)
    unwrap_heading_containers(soup)
    headings = [
        h
        for h in soup.body.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6"], recursive=False
        )
        if introductory_heading_name(h) in HEADING_NAMES
    ]
    soup.body[FAMILY_ATTRIBUTE] = ""
    if len(headings) == 1:
        name = introductory_heading_name(headings[0])
        soup.body[FAMILY_ATTRIBUTE] = HEADING_NAMES[name]
    targets = []
    # Mammoth can emit a named bookmark inside the heading, immediately
    # before it, or in an otherwise empty preceding paragraph.
    for heading in headings:
        targets.extend([heading] + heading.find_all(id=True))
        previous = heading.find_previous_sibling()
        if previous and not previous.get_text(strip=True):
            if previous.name == "a":
                targets.append(previous)
            elif previous.name == "p" and all(
                t.name == "a" for t in previous.find_all(recursive=False)
            ):
                targets.extend(previous.find_all("a", id=True))
    for target in targets:
        target_id = target.get("id")
        if not target_id:
            continue
        for link in soup.find_all("a", href=f"#{target_id}"):
            if (
                page_enabled
                and len(headings) == 1
                and len(soup.find_all(id=target_id)) == 1
            ):
                link["href"] = f"#{INTRO_ANCHOR}"
            else:
                link.unwrap()
    return soup
