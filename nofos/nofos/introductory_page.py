"""Builder-owned introductory page selection and source destination capture."""

from bs4 import NavigableString

INTRO_ANCHOR = "section--before-you-begin"
FAMILY_ATTRIBUTE = "data-nofo-introductory-family"
HEADING_NAMES = {
    "before you begin": "legacy",
    "before you get started": "get_started",
}
CONTENT_MODE_ATTRIBUTE = "data-nofo-introductory-content-mode"


def imported_introduction(soup):
    return bool(soup.body and soup.body.get(CONTENT_MODE_ATTRIBUTE) == "imported")


def prepare_editable_introduction(soup, policy="generated"):
    """Opt in only a new, recognized Word structure, or safely reimport a saved mode.

    Names identify a wording family, not a template version. The new-record gate
    also requires Step 1 / Basic information and a trailing recognized Metadata
    block, matching the cleared FY27 master. Reimports need a uniquely bounded
    introduction, not a second fiscal-year inference.
    """
    from .content_processing import (
        ContentProcessingError,
        _looks_like_metadata_line,
        _metadata_block,
        metadata_block_fields,
    )

    soup.body.attrs.pop(CONTENT_MODE_ATTRIBUTE, None)
    if policy == "generated":
        return soup
    headings = soup.body.find_all(["h1", "h2", "h3", "h4", "h5", "h6"], recursive=False)
    intros = [h for h in headings if introductory_heading_name(h) in HEADING_NAMES]
    steps = [h for h in headings if introductory_heading_name(h).startswith("step 1:")]
    selected = len(intros) == len(steps) == 1 and headings.index(
        intros[0]
    ) < headings.index(steps[0])
    if selected:
        intro, step = intros[0], steps[0]
        prior_headings = [
            h
            for h in headings[: headings.index(intro)]
            if metadata_block_fields(h) is None
        ]
        between = list(intro.find_next_siblings())
        between = between[: between.index(step)]
        has_body = any(
            (t.get_text(strip=True) or t.find("img"))
            and t.name not in {"h1", "h2", "h3", "h4", "h5", "h6"}
            for t in between
        )
        basic = next(
            (
                h
                for h in step.find_next_siblings()
                if h.name in {"h1", "h2", "h3", "h4", "h5", "h6"}
            ),
            None,
        )
        metadata = [h for h in headings if metadata_block_fields(h) is not None]
        fy27 = (
            introductory_heading_name(intro) == "before you get started"
            and basic is not None
            and introductory_heading_name(basic) == "basic information"
            and any(headings.index(h) > headings.index(step) for h in metadata)
        )
        consumed_metadata_ids = {
            id(element) for h in headings for element in _metadata_block(h)[1]
        }
        unsafe_prelude = [
            tag
            for tag in reversed(intro.find_previous_siblings())
            if id(tag) not in consumed_metadata_ids
            and not _looks_like_metadata_line(tag)
            and (tag.get_text(strip=True) or tag.find("img"))
        ]
        if (fy27 or policy == "required") and (unsafe_prelude or prior_headings):
            first = (unsafe_prelude or prior_headings)[0]
            excerpt = " ".join(first.get_text(" ", strip=True).split())
            if len(excerpt) > 160:
                excerpt = excerpt[:157] + "..."
            location = (
                f"The first content begins: “{excerpt}”. "
                if excerpt
                else "The first item is an image or an empty heading. "
            )
            raise ContentProcessingError(
                f'Builder found content before “{intro.get_text(" ", strip=True)}” '
                "that it could not safely place in an editable section. "
                f"{location}"
                "Remove template guidance from your import copy, or move "
                "applicant-facing content into the appropriate section. "
                "This check does not mean your heading styles are incorrect. "
                "No content was saved or replaced.",
                code="introductory_content_unsafe",
            )
        # Recognized sources must not fall back to generated-text cleanup when
        # an introductory child accidentally uses a main-section heading level.
        unsafe_headings = [
            t
            for t in between
            if t.name in {"h1", "h2", "h3", "h4", "h5", "h6"}
            and int(t.name[1]) <= int(intro.name[1])
        ]
        if (fy27 or policy == "required") and unsafe_headings:
            heading = unsafe_headings[0]
            intro_level = int(intro.name[1])
            raise ContentProcessingError(
                f'“{heading.get_text(" ", strip=True)}” uses Heading {heading.name[1]}, '
                f'which is the same or a higher level than “{intro.get_text(" ", strip=True)}” '
                f'(Heading {intro_level}), but appears before “{step.get_text(" ", strip=True)}”. '
                "All headings within the introduction must be lower-level headings "
                "(with a larger heading number) than its main heading. "
                f'In Word, select “{heading.get_text(" ", strip=True)}” and apply '
                f"Heading {intro_level + 1} if it is a direct subsection, or a lower "
                "level if it belongs within another subsection. Save the document, "
                "then import it again. No content was saved or replaced.",
                code="introductory_content_unsafe",
            )
        safe = has_body and not prior_headings and not unsafe_headings
        selected = safe and (policy == "required" or fy27)
    if not selected:
        if policy == "required":
            raise ContentProcessingError(
                "This NOFO keeps its introductory text as editable content. The new document must contain one Before You Begin or Before You Get Started heading, its content, and Step 1. Restore that structure before reimporting. Your saved content has not changed.",
                code="introductory_content_unsafe",
            )
        return soup
    # Normalize only the retained introduction to the main-section hierarchy.
    # Its actual child headings keep their relative levels through normal parsing.
    target_level = int(step.name[1])
    if target_level not in (1, 2):
        if policy == "required" or fy27:
            raise ContentProcessingError(
                "Use Heading 1 or Heading 2 for Step 1 before reimporting. Your saved content has not changed.",
                code="introductory_content_unsafe",
            )
        return soup
    delta = target_level - int(intro.name[1])
    for tag in [intro] + [
        h
        for node in between
        for h in ([node] + node.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]))
        if h.name in {"h1", "h2", "h3", "h4", "h5", "h6"}
    ]:
        level = int(tag.name[1]) + delta
        if not 1 <= level <= 6:
            raise ContentProcessingError(
                "The introductory headings cannot be mapped safely. Use consecutive heading levels before reimporting. Your saved content has not changed.",
                code="introductory_content_unsafe",
            )
        tag.name = f"h{level}"
    intro.string = "Before you get started"
    intro["id"] = INTRO_ANCHOR
    soup.body[CONTENT_MODE_ATTRIBUTE] = "imported"
    return soup


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


def capture_introductory_page(soup):
    """Capture only a unique structural destination, never visible link text.

    The private body attribute survives the existing confirmation serialization;
    it is not copied into stored sections or rendered output.
    """
    from .content_processing import add_body_if_no_body, unwrap_heading_containers

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
            if len(headings) == 1 and len(soup.find_all(id=target_id)) == 1:
                link["href"] = f"#{INTRO_ANCHOR}"
            else:
                link.unwrap()
    return soup
