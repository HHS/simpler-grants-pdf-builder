import datetime
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import parse_qs, urlparse

import cssutils
import markdown
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from django.db import transaction
from markdownify import MarkdownConverter
from slugify import slugify

from .models import Nofo, Section, Subsection
from .utils import clean_string, create_subsection_html_id

DEFAULT_NOFO_OPPORTUNITY_NUMBER = "NOFO #999"


class TablesAndStuffInTablesConverter(MarkdownConverter):
    """
    Leave ULs and OLs TDs as HTML
    """

    def _remove_classes_recursive(self, container_el):
        if container_el.has_attr("class"):
            del container_el["class"]

        for el in container_el.find_all(True):
            if el.has_attr("class"):
                del el["class"]

    def convert_a(self, el, text, convert_as_inline):
        # keep the in-text footnote links as HTML so that the ids aren't lost
        if el and el.attrs.get("id") and "footnote" in el.attrs.get("id"):
            self._remove_classes_recursive(el)
            return str(el)

        return super().convert_a(el, text, convert_as_inline)

    def convert_ol(self, el, text, convert_as_inline):
        # return as HMTL to preserve "start" attribute if anything other than "1"
        start = el.get("start", "1")
        if start and start != "1":
            self._remove_classes_recursive(el)
            return str(el)

        for parent in el.parents:
            if parent.name == "td":
                self._remove_classes_recursive(el)
                return str(el)

        # save the footnote list as HTML so that the ids aren't lost
        first_li = el.find("li")
        if (
            first_li
            and first_li.attrs.get("id")
            and "footnote" in first_li.attrs.get("id")
        ):
            self._remove_classes_recursive(el)
            [li.attrs.update({"tabindex": "-1"}) for li in el.find_all("li")]
            return str(el.prettify())

        return super().convert_ol(el, text, convert_as_inline)

    def convert_ul(self, el, text, convert_as_inline):
        for parent in el.parents:
            if parent.name == "td":
                self._remove_classes_recursive(el)
                return str(el)

        return super().convert_ul(el, text, convert_as_inline)

    def convert_p(self, el, text, convert_as_inline):
        # if we are in a table cell, and that table cell contains multiple children, return the string
        if el.parent.name == "td":
            if len(list(el.parent.children)) > 1:
                return str(el)

        # if the paragraph has an id that includes the string "bookmark", keep the paragraph as-is
        if el and el.attrs.get("id") and "bookmark" in el.attrs.get("id"):
            return str(el)

        return super().convert_p(el, text, convert_as_inline)

    def convert_table(self, el, text, convert_as_inline):
        def _has_colspan_or_rowspan_not_one(tag):
            # Check for colspan/rowspan attributes not equal to '1'
            colspan = tag.get("colspan", "1")
            rowspan = tag.get("rowspan", "1")
            return colspan != "1" or rowspan != "1"

        cells = el.find_all(["td", "th"])
        for cell in cells:
            # return table as HTML if we find colspan/rowspan != 1 for any cell
            if _has_colspan_or_rowspan_not_one(cell):
                self._remove_classes_recursive(el)
                return str(el.prettify()) + "\n"

        return super().convert_table(el, text, convert_as_inline)


# Create shorthand method for conversion
def md(html, **options):
    return TablesAndStuffInTablesConverter(**options).convert(html)


def replace_chars(file_content):
    replacement_chars = [
        # both of these are nonbreaking space
        ("\xa0", " "),
        ("&nbsp;", " "),
        # from (☐) U+2610 BALLOT BOX to (◻) U+25FB WHITE MEDIUM SQUARE
        ("\u2610", "\u25FB"),
        # from (¨) U+00A8 DIAERESIS to (◻) U+25FB WHITE MEDIUM SQUARE
        ("\u00A8", "\u25FB"),
        # from () U+007F DELETE to (◻) U+25FB WHITE MEDIUM SQUARE
        ("\u007F", "\u25FB"),
    ]

    for _from, _to in replacement_chars:
        file_content = file_content.replace(_from, _to)

    return file_content


@transaction.atomic
def add_headings_to_nofo(nofo):
    new_ids = []
    # add counter because subheading titles can repeat, resulting in duplicate IDs
    counter = 1

    # add ids to all section headings
    for section in nofo.sections.all():
        section_id = "{}".format(slugify(section.name))

        if section.html_id and len(section.html_id):
            new_ids.append({"old_id": section.html_id, "new_id": section_id})

        section.html_id = section_id

        if not section.html_id or len(section.html_id) == 0:
            raise ValueError("html_id blank for section: {}".format(section.name))

        section.save()

        # add ids to all subsection headings
        for subsection in section.subsections.all():
            subsection_id = create_subsection_html_id(counter, subsection)

            if subsection.html_id:
                new_ids.append({"old_id": subsection.html_id, "new_id": subsection_id})

            subsection.html_id = subsection_id
            subsection.save()
            counter += 1

    # replace all old ids with new ids
    for section in nofo.sections.all():
        for subsection in section.subsections.all():
            for ids in new_ids:
                subsection.body = subsection.body.replace(ids["old_id"], ids["new_id"])

            subsection.save()


def add_page_breaks_to_headings(nofo):
    page_break_headings = [
        "eligibility",
        "program description",
        "application checklist",
    ]

    for section in nofo.sections.all():
        for subsection in section.subsections.all():
            if subsection.name and subsection.name.lower() in page_break_headings:
                subsection.html_class = "page-break-before"
                subsection.save()


def _build_nofo(nofo, sections):
    for section in sections:
        model_section = Section(
            name=section.get("name", "Section X"),
            order=section.get("order", ""),
            html_id=section.get("html_id", None),
            has_section_page=section.get("has_section_page"),
            nofo=nofo,
        )
        model_section.save()

        for subsection in section.get("subsections", []):
            md_body = ""
            html_body = [str(tag).strip() for tag in subsection.get("body", [])]

            if html_body:
                md_body = md("".join(html_body))
                md_body = md_body.replace("\\\\", "\\")

            model_subsection = Subsection(
                name=subsection.get("name", ""),
                order=subsection.get("order", ""),
                tag=subsection.get("tag", ""),
                html_id=subsection.get("html_id"),
                callout_box=subsection.get("is_callout_box", False),
                body=md_body,  # body can be empty
                section=model_section,
            )
            model_subsection.save()

    return nofo


def create_nofo(title, sections):
    nofo = Nofo(title=title)
    nofo.number = "NOFO #999"
    nofo.save()
    return _build_nofo(nofo, sections)


def overwrite_nofo(nofo, sections):
    nofo.sections.all().delete()
    nofo.save()
    return _build_nofo(nofo, sections)


def convert_table_first_row_to_header_row(table):
    # Converts the first row of cells in the given table
    # to header cells by changing the <td> tags to <th>.
    # Assumes the first row is a header row.
    first_row = table.find("tr")
    if first_row:
        first_row_cells = first_row.find_all("td")
        for cell in first_row_cells:
            cell.name = "th"


def convert_table_with_all_ths_to_a_regular_table(table):
    """
    Converts a table with all rows in the thead and th cells to a standard table structure.

    This function checks if the table has a thead, no tbody, and more than one row in the thead.
    If these conditions are met, it creates a tbody after the thead and moves all rows except
    the first one to the tbody. Additionally, it converts all th cells in the tbody to td cells.
    """
    # if there are cells with "rowspan" not equal to 1, return early
    cells_with_rowspan = table.find_all(
        lambda tag: (tag.name == "td" or tag.name == "th") and tag.has_attr("rowspan")
    )
    for cell in cells_with_rowspan:
        if cell["rowspan"] != "1":
            return

    thead = table.find("thead")
    tbody = table.find("tbody")

    # Check if thead exists, tbody does not exist, and thead contains more than one row
    if thead and not tbody and len(thead.find_all("tr")) > 1:
        # Create a new tbody element as a string and parse it into a BeautifulSoup tag
        new_tbody = BeautifulSoup("<tbody></tbody>", "html.parser").tbody
        table.append(new_tbody)

        # Move all rows except the first one to the new tbody
        rows = thead.find_all("tr")
        for row in rows[1:]:
            # Convert th cells to td cells
            for th in row.find_all("th"):
                th.name = "td"
            new_tbody.append(row.extract())


def get_sections_from_soup(soup, top_heading_level="h1"):
    # build a structure that looks like our model
    sections = []
    section_num = -1

    for tag in soup.find_all(True):
        if tag.name == top_heading_level:
            section_num += 1

        if section_num >= 0:
            if len(sections) == section_num:
                # add an empty array at a new index
                section_name = clean_string(tag.text)

                has_section_page = not any(
                    word.lower() in section_name.lower()
                    for word in [
                        "Appendix",
                        "Appendices",
                        "Glossary",
                        "Endnotes",
                        "References",
                    ]
                )

                sections.append(
                    {
                        "name": section_name,
                        "order": section_num + 1,
                        "html_id": tag.get("id", ""),
                        "has_section_page": has_section_page,
                        "body": [],
                    }
                )
            else:
                sections[section_num]["body"].append(tag)

    return sections


def is_callout_box_table(table):
    """
    Determines if a given HTML table element represents a callout box.
    This function checks the following conditions:
    - The table contains exactly one row.
    - The row contains exactly one cell, which must be either all 'th' or all 'td' but not a mix.
    - There is either one 'th' or one 'td' in the entire table.

    NOTE: after this goes through the markdown parser, it has 2 rows, but for now it is just 1

    Returns:
    - bool: True if the table matches the criteria for a callout box table, False otherwise.
    """

    rows = table.find_all("tr")

    if not rows:
        return False

    cols = rows[0].find_all("th") + rows[0].find_all("td")
    ths = table.find_all("th")
    tds = table.find_all("td")

    return (
        len(cols) == 1  # 1 column
        and len(rows) == 1  # 1 row
        and (
            (len(tds) == 1 and not len(ths)) or (len(ths) == 1 and not len(tds))
        )  # 1 th OR 1 td, not both
    )


def get_subsections_from_sections(sections, top_heading_level="h1"):
    if_demote_headings = top_heading_level == "h1"
    heading_tags = ["h3", "h4", "h5", "h6"]

    # if top_heading_level is h1, then include h2s in the list
    if if_demote_headings:
        heading_tags = ["h2"] + heading_tags

    def _demote_tag(tag_name):
        newTags = {"h2": "h3", "h3": "h4", "h4": "h5", "h5": "h6", "h6": "h7"}

        return newTags[tag_name]

    def extract_first_header(td):
        for tag_name in heading_tags:
            header_element = td.find(tag_name)
            if header_element:
                # remove from the dom
                return header_element.extract()
        return False

    def get_subsection_dict(heading_tag, order, is_callout_box, body=None):
        if heading_tag:
            return {
                "name": clean_string(heading_tag.text),
                "order": order,
                "tag": (
                    _demote_tag(heading_tag.name)
                    if if_demote_headings
                    else heading_tag.name
                ),
                "html_id": heading_tag.get("id", ""),
                "is_callout_box": is_callout_box,
                "body": body or [],
            }

        return {
            "name": "",
            "order": order,
            "tag": "",
            "html_id": "",
            "is_callout_box": is_callout_box,
            "body": body or [],
        }

    def get_empty_subsection(order):
        return get_subsection_dict(heading_tag=None, order=order, is_callout_box=False)

    for section in sections:
        section["subsections"] = []
        # remove 'body' key
        body = section.pop("body", None)

        body_descendents = [
            tag for tag in body if tag.parent.name in ["body", "[document]"]
        ]

        for tag in body_descendents:
            if tag.name == "table" and is_callout_box_table(tag):
                # Grab the first td or th
                cell = tag.find("td")
                if not cell:
                    cell = tag.find("th")

                # make the td a div so that it can live on its own
                cell.name = "div"
                callout_box_subsection = get_subsection_dict(
                    heading_tag=extract_first_header(cell),
                    order=len(section["subsections"]) + 1,
                    is_callout_box=True,
                    body=cell,
                )
                section["subsections"].append(callout_box_subsection)

            elif tag.name in heading_tags:
                # create new subsection
                heading_subsection = get_subsection_dict(
                    heading_tag=tag,
                    order=len(section["subsections"]) + 1,
                    is_callout_box=False,
                )

                section["subsections"].append(heading_subsection)

            # if not a heading or callout_box table add to existing subsection
            else:
                # convert first row of header cells into th elements
                if tag.name == "table":
                    # make sure the first row is a header row
                    convert_table_first_row_to_header_row(tag)
                    # if all rows are in a thead, move them to a tbody
                    convert_table_with_all_ths_to_a_regular_table(tag)

                if not len(section["subsections"]):
                    # create new empty subsection if there are no other ones in this section
                    section["subsections"].append(get_empty_subsection(1))

                # get latest subsection
                subsection = section["subsections"][-1]
                if subsection.get("is_callout_box", False):
                    # create new empty subsection after a callout box
                    section["subsections"].append(
                        get_empty_subsection(len(section["subsections"]) + 1)
                    )

                section["subsections"][-1]["body"].append(tag)

    return sections


def _update_link_statuses(all_links):
    def check_link_status(link):
        try:
            response = requests.head(link["url"], timeout=5, allow_redirects=True)
            link["status"] = response.status_code
            if len(response.history):
                link["redirect_url"] = response.url
        except requests.RequestException as e:
            link["error"] = "Error: " + str(e)
        return link

    with ThreadPoolExecutor(max_workers=8) as executor:
        # Submit all tasks and create a dictionary to track future to link mapping
        future_to_link = {
            executor.submit(check_link_status, link): link for link in all_links
        }

        for future in as_completed(future_to_link):
            link = future_to_link[future]
            try:
                result = future.result()
                # Update the link in all_links with the result
                link.update(result)
            except Exception as e:
                print(f"Error checking link {link['url']}: {e}")


def find_external_links(nofo, with_status=False):
    all_links = []

    sections = nofo.sections.all().order_by("order")
    for section in sections:
        subsections = section.subsections.all().order_by("order")

        for subsection in subsections:
            soup = BeautifulSoup(
                markdown.markdown(subsection.body, extensions=["extra"]),
                "html.parser",
            )
            links = soup.find_all("a")
            for link in links:
                link_text = link.get("href", "#")

                if link_text.startswith("http"):
                    if not "nofo.rodeo" in link_text:
                        all_links.append(
                            {
                                "url": link_text,
                                "domain": urlparse(link_text).hostname,
                                "section": section,
                                "subsection": subsection,
                                "status": "",
                                "error": "",
                                "redirect_url": "",
                            }
                        )

    if with_status:
        _update_link_statuses(all_links)

    return all_links


###########################################################
#################### SUGGEST VAR FUNCS ####################
###########################################################


def _suggest_by_startswith_string(soup, startswith_string):
    suggestion = ""
    regex = re.compile("^{}".format(startswith_string), re.IGNORECASE)
    element = soup.find(string=regex)

    # look for the paragraph
    if element and element.name != "p":
        for parent in element.parents:
            if parent.name == "p":
                element = parent
                break

    if element:
        suggestion = regex.sub("", element.text)

    return suggestion.strip()


def suggest_nofo_opportunity_number(soup):
    opportunity_number_default = DEFAULT_NOFO_OPPORTUNITY_NUMBER
    suggestion = _suggest_by_startswith_string(soup, "Opportunity Number:")
    return suggestion or opportunity_number_default


def suggest_nofo_application_deadline(soup):
    nofo_application_deadline_default = "[WEEKDAY, MONTH DAY, YEAR]"

    suggestion = _suggest_by_startswith_string(soup, "Application Deadline:")
    return suggestion or nofo_application_deadline_default


def suggest_nofo_cover(nofo_theme):
    if any(prefix in nofo_theme.lower() for prefix in ["acf-", "acl-", "hrsa-"]):
        return "nofo--cover-page--text"

    return "nofo--cover-page--medium"


def suggest_nofo_theme(nofo_number):
    if "cdc-" in nofo_number.lower():
        return "portrait-cdc-blue"

    if "acf-" in nofo_number.lower():
        return "portrait-acf-white"

    if "acl-" in nofo_number.lower():
        return "portrait-acl-white"

    if "cms-" in nofo_number.lower():
        return "portrait-cms-white"

    if "ihs-" in nofo_number.lower():
        return "portrait-ihs-white"

    return "portrait-hrsa-blue"


def suggest_nofo_title(soup):
    nofo_title_default = "NOFO: {}".format(
        datetime.datetime.now().replace(microsecond=0).isoformat().replace("T", " ")
    )

    suggestion = _suggest_by_startswith_string(soup, "Opportunity Name:")
    return suggestion or nofo_title_default


def suggest_nofo_opdiv(soup):
    suggestion = _suggest_by_startswith_string(soup, "Opdiv:")
    return suggestion or ""


def suggest_nofo_agency(soup):
    suggestion = _suggest_by_startswith_string(soup, "Agency:")
    return suggestion or ""


def suggest_nofo_subagency(soup):
    suggestion = _suggest_by_startswith_string(soup, "Subagency:")
    return suggestion or ""


def suggest_nofo_subagency2(soup):
    suggestion = _suggest_by_startswith_string(soup, "Subagency2:")
    return suggestion or ""


def suggest_nofo_tagline(soup):
    suggestion = _suggest_by_startswith_string(soup, "Tagline:")
    return suggestion or ""


def suggest_nofo_author(soup):
    suggestion = _suggest_by_startswith_string(soup, "Metadata Author:")
    return suggestion or ""


def suggest_nofo_subject(soup):
    suggestion = _suggest_by_startswith_string(soup, "Metadata Subject:")
    return suggestion or ""


def suggest_nofo_keywords(soup):
    suggestion = _suggest_by_startswith_string(soup, "Metadata Keywords:")
    return suggestion or ""


def suggest_all_nofo_fields(nofo, soup):
    first_time_import = (
        not nofo.number or nofo.number == DEFAULT_NOFO_OPPORTUNITY_NUMBER
    )

    nofo.number = suggest_nofo_opportunity_number(soup)  # guess the NOFO number
    nofo.application_deadline = suggest_nofo_application_deadline(
        soup
    )  # guess the NOFO application deadline
    nofo.opdiv = suggest_nofo_opdiv(soup)  # guess the NOFO OpDiv
    nofo.agency = suggest_nofo_agency(soup)  # guess the NOFO Agency
    nofo.subagency = suggest_nofo_subagency(soup)  # guess the NOFO Subagency
    nofo.subagency2 = suggest_nofo_subagency2(soup)  # guess NOFO Subagency 2
    nofo.tagline = suggest_nofo_tagline(soup)  # guess the NOFO tagline
    nofo.author = suggest_nofo_author(soup)  # guess the NOFO author
    nofo.subject = suggest_nofo_subject(soup)  # guess the NOFO subject
    nofo.keywords = suggest_nofo_keywords(soup)  # guess the NOFO keywords

    nofo_title = suggest_nofo_title(soup)  # guess the NOFO title
    # reset title only if there is a title and it's not the default title, or current nofo.title is empty
    if nofo_title:
        if not nofo.title or not nofo_title.startswith("NOFO: "):
            nofo.title = nofo_title

    # do not reset these during import
    if first_time_import:
        nofo.theme = suggest_nofo_theme(nofo.number)  # guess the NOFO theme
    if first_time_import:
        nofo.cover = suggest_nofo_cover(nofo.theme)  # guess the NOFO cover


###########################################################
#################### MUTATE HTML FUNCS ####################
###########################################################


def add_body_if_no_body(soup):
    """
    This function mutates the soup!

    Checks for a body tag. If there is no body, it wraps all the html in a body tag.
    """
    if not soup.body:
        soup = BeautifulSoup("<body>{}</body>".format(str(soup)), "html.parser")

    return soup


def join_nested_lists(soup):
    """
    This function mutates the soup!

    Joins nested unordered lists (UL tags) in the provided BeautifulSoup soup.

    Iterates through all UL tags in the soup. For each UL tag, checks if the previous sibling is also a UL tag.
    If so, calls _join_lists() to join the two lists by:

    1. If the two UL tags have the same "class" attribute, extends the previous UL with the current UL's LI tags, then decomposes the current UL.

    2. If the classes differ, finds the last LI tag in the previous UL. If that LI contains a nested UL, recursively calls _join_lists on that nested UL and the current UL. Otherwise, appends the current UL to the previous LI.

    This mutates the original soup to remove nested ULs and join ULs with the same class.

    Returns the mutated soup.
    """

    def _get_list_classname(tag):
        for classname in tag.get("class"):
            if classname.startswith("lst-"):
                return classname
        return None

    def _get_previous_element(tag):
        for ps in tag.previous_siblings:
            if isinstance(ps, Tag):
                return ps
        return None

    def _join_lists(lst, previous_lst):
        if _get_list_classname(lst) == _get_list_classname(previous_lst):
            # if classes match, join these lists
            previous_lst.extend(lst.find_all("li"))
            lst.decompose()
            return

        # okay: classes do not match
        # get the last li in the previous list
        last_tag_in_previous_list = previous_lst.find_all("li", recursive=False)[-1]

        # see if there is a ul/ol in there
        nested_lst = last_tag_in_previous_list.find(["ul", "ol"])
        if nested_lst:
            return _join_lists(lst, nested_lst)

        # if there is not, append to the last li
        last_tag_in_previous_list.append(lst)
        return

    for lst in soup.find_all(["ul", "ol"]):
        if lst.get("class"):
            # check previous sibling
            previous_element = _get_previous_element(lst)
            if previous_element and previous_element.name in ["ul", "ol"]:
                _join_lists(lst, previous_element)

    return soup


def remove_google_tracking_info_from_links(soup):
    """
    This function mutates the soup!

    It looks through all the link elements and whenever it finds one with
    Google tracking information, it returns the original URL.

    For example:
    - Before: https://www.google.com/url?q=https://www.cdc.gov/grants/additional-requirements/ar-25.html&sa=D&source=editors&ust=1706211338137807&usg=AOvVaw3QRecqJEvdFcL93eoqk6HD
    - After: https://www.cdc.gov/grants/additional-requirements/ar-25.html

    URLs that don't start with "https://www.google.com/url?" aren't modified
    """

    def _get_original_url(modified_url):
        parsed_url = urlparse(modified_url)
        query_params = parse_qs(parsed_url.query)
        original_url = query_params.get("q", [None])[0]
        return original_url

    for a in soup.find_all("a"):
        href = a.get("href", "")
        if href.startswith("https://www.google.com/url?"):
            a["href"] = _get_original_url(href)


def _get_all_id_attrs_for_nofo(nofo):
    """
    Extracts all unique HTML 'id' attributes from a given Nofo.
    This includes 'id' attributes defined in the 'html_id' field of sections and subsections,
    as well as any 'id' attributes found within the HTML content of the subsection.body.
    """
    # Initialize a set to collect all unique ids
    all_ids = set()

    for section in nofo.sections.all():
        all_ids.add(section.html_id)

        for subsection in section.subsections.all():
            if subsection.html_id:
                all_ids.add(subsection.html_id)

            # Use BeautifulSoup to parse the HTML body and find all ids
            if subsection.body:
                soup = BeautifulSoup(markdown.markdown(subsection.body), "html.parser")
                for element in soup.find_all(id=True):
                    all_ids.add(element["id"])

    return {"#" + item for item in all_ids}


def find_broken_links(nofo):
    """
    This function mutates the soup!

    Identifies and returns a list of broken links within a given Nofo.

    A broken link is defined as an anchor (`<a>`) element whose `href` attribute value starts with "#h.", "#id.", "/", "https://docs.google.com", "#_heading", or "_bookmark".
    This means that someone created an internal link to a header, and then later the header was deleted or otherwise
    modified so the original link doesn't point anywhere.

    Args:
        nofo (Nofo): A Nofo object which contains sections and subsections. Each subsection's body is expected
                     to be in markdown format.

    Returns:
        list of dict: A list of dictionaries, where each dictionary contains information about a broken link,
                      including the section and subsection it was found in, the text of the link, and the `href`
                      attribute of the link. The structure is as follows:
                      [
                          {
                              "section": <Section object>,
                              "subsection": <Subsection object>,
                              "link_text": "text of the link",
                              "link_href": "href of the link"
                          },
                          ...
                      ]
    """

    # Define a function that checks if an 'href' attribute starts with any of these
    def _href_starts_with_h(tag):
        return tag.name == "a" and (
            tag.get("href", "").startswith("/")
            or tag.get("href", "").startswith("#")
            or tag.get("href", "").startswith("https://docs.google.com")
            or tag.get("href", "") == "about:blank"
        )

    broken_links = []
    all_ids = _get_all_id_attrs_for_nofo(nofo)

    for section in nofo.sections.all().order_by("order"):
        for subsection in section.subsections.all().order_by("order"):
            soup = BeautifulSoup(
                markdown.markdown(subsection.body, extensions=["extra"]), "html.parser"
            )

            all_links = soup.find_all("a")

            for link in all_links:
                if link.attrs.get("href") in all_ids:
                    # skip all '#' ids that exist (if not, they are caught in the next step)
                    pass
                elif _href_starts_with_h(link):
                    broken_links.append(
                        {
                            "section": section,
                            "subsection": subsection,
                            "link_text": link.get_text(),
                            "link_href": link["href"],
                        }
                    )

    return broken_links


def combine_consecutive_links(soup):
    """
    This function mutates the soup!

    Modifies the BeautifulSoup object by combining consecutive <a> tags with the same href into a single <a> tag
    and ensures there's no whitespace between an <a> tag and following punctuation.

    This function performs three main tasks:
    1. It unwraps <span> tags that contain only an <a> tag, removing unnecessary <span> wrappers.
    2. It merges consecutive <a> tags that share the same href attribute, optionally inserting a space between merged text if
       the original tags were separated by whitespace. This helps maintain natural spacing in the text.
    3. After merging <a> tags, the function also removes any whitespace between the end of an <a> tag and the following
       punctuation (.,;!?), if present. This is crucial for ensuring correct grammar and readability in the resulting HTML.

    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the HTML to be processed.
    """

    # First, unwrap <span> tags that only contain <a> tags
    for span in soup.find_all("span"):
        if len(span.contents) == 1 and span.a:
            span.unwrap()

    def _append_next_sibling(link):
        next_sibling = link.next_sibling

        # Determine if there's whitespace between this and the next <a> tag
        whitespace_between = False
        if isinstance(next_sibling, NavigableString) and next_sibling.strip() == "":
            whitespace_between = True
            if next_sibling.next_sibling and next_sibling.next_sibling.name == "a":
                next_sibling = next_sibling.next_sibling

        if (
            next_sibling
            and next_sibling.name == "a"
            and link.get("href") == next_sibling.get("href")
        ):
            # If there's whitespace, add a space before merging texts
            separator = " " if whitespace_between else ""
            link.string = link.get_text() + separator + next_sibling.get_text()
            # Remove the next link
            next_sibling.extract()
            return True

        return False

    # Now, merge consecutive <a> tags with the same href
    # Keep looping on the link so that multiple consecutive links will all be joined together
    links = soup.find_all("a")
    for link in links:
        while _append_next_sibling(link):
            pass

    # Remove spaces between the end a link and punctuation
    punctuation = {".", ",", ";", "!", "?"}
    for link in soup.find_all("a"):
        # Check if the link has a next sibling and it's a NavigableString containing only whitespace
        if (
            link.next_sibling
            and isinstance(link.next_sibling, NavigableString)
            and link.next_sibling.strip() == ""
        ):
            # Now check if there's another sibling after the whitespace and it's a punctuation mark
            next_to_whitespace = link.next_sibling.next_sibling
            if (
                next_to_whitespace
                and next_to_whitespace.string
                and next_to_whitespace.string[0] in punctuation
            ):
                # Remove the whitespace by replacing it with an empty string
                link.next_sibling.replace_with("")


def decompose_empty_tags(soup):
    """
    This function mutates the soup!

    Removes empty HTML tags from the BeautifulSoup `soup`.

    Iterates over all body descendants, `p`, and `li` tags, removing any that have no textual content.
    Intended to clean up HTML extracted from PDFs or other sources that may contain many meaningless tags.

    It will, however, keep in place: brs, hrs, and tags that contain imgs.
    """
    body_descendents = soup.select("body > *")

    for tag in body_descendents:
        if not tag.get_text().strip() and tag.name not in ["br", "hr"]:
            # images have no content but should not be stripped out
            if len(tag.find_all("img")) == 0:
                tag.decompose()

    def _decompose_empty_elements(element):
        if not element.get_text().strip():
            element.decompose()

    # remove all list items and paragraphs that are empty
    elements = soup.find_all(["li", "p"])
    for element in elements:
        _decompose_empty_elements(element)


def unwrap_empty_elements(soup):
    """
    This function mutates the soup!

    Unwraps empty span, strong, sup, a, and em tags from the BeautifulSoup `soup`.
    """
    elements = soup.find_all(["em", "span", "strong", "sup"])
    for el in elements:
        if not el.get_text().strip():
            el.unwrap()


def clean_table_cells(soup):
    """
    This function mutates the soup!

    Cleans the content of all table cells in a Nofo.

    This function performs two main operations on each table cell (`<td>` and `<th>` elements) within a given BeautifulSoup object:
    1. Unwraps all `<span>` elements, effectively removing the `<span>` tags but keeping their contents intact in the cell.

    These operations are applied to ensure that the text within table cells is normalized for further processing or display, without unnecessary `<span>` tags or non-standard whitespace characters.

    Parameters:
    soup (BeautifulSoup): A BeautifulSoup object containing the HTML content to be cleaned. This object is modified in place.

    Returns:
    None: The function modifies the BeautifulSoup object in place and does not return a value.

    Example:
    >>> from bs4 import BeautifulSoup
    >>> html_content = "<table><tr><td><span>Example</span> Text and <a href='https://groundhog-day.com'>a link</a></td></tr></table>"
    >>> soup = BeautifulSoup(html_content, 'html.parser')
    >>> clean_table_cells(soup)
    >>> str(soup)
    '<table><tr><td>Example Text and <a href='https://groundhog-day.com'>a link</a></td></tr></table>'
    """
    for cell in soup.find_all(["td", "th"]):
        # strip spans but keep their content
        for span in cell.find_all("span"):
            span.unwrap()


def replace_src_for_inline_images(soup):
    """
    This function mutates the soup!

    Replaces the src attribute for inline images in the soup to use static image paths based on the NOFO number.

    Iterates over all img tags in the soup. If an img has a src attribute, it extracts the filename, and replaces the src with a path prefixed by the NOFO number from suggest_nofo_opportunity_number().

    For example with NOFO number "HRSA-24-017":

    - Before: images/image1.png
    - After: /static/img/inline/hrsa-24-017/image1.png
    """
    nofo_number = suggest_nofo_opportunity_number(soup)

    if nofo_number and nofo_number != DEFAULT_NOFO_OPPORTUNITY_NUMBER:
        for img in soup.find_all("img"):
            if img.get("src"):
                img_src = img["src"]
                img_filename = img_src.split(
                    "/"
                ).pop()  # get the last part of the filename
                img["src"] = "/static/img/inline/{}/{}".format(
                    nofo_number.lower(), img_filename
                )


def add_endnotes_header_if_exists(soup):
    """
    This function mutates the soup!

    If no "Endnotes" header exists, look for a list of endnotes and add a header if found.

    If this is the Google Docs HTML export, we look for a final <hr> without a style tag.
        Adds a header for endnotes if final <hr> tag has no style attribute.

        Checks if the last <hr> tags in the soup has no style attribute.
        If so, takes the last <hr> tag, converts it to a <h1> tag with the text
        "Endnotes" to add a header before the endnotes.

    If this is a docx export, we look for a final <ol> where the first <li> has an id of "footnote-0".
        In this case, we create a new h1 with the text "Endnotes" and
        insert it before the ol.
    """

    def _match_endnotes(tag):
        return (tag.name == "h1" or tag.name == "h2") and tag.text == "Endnotes"

    def _find_google_doc_html_endnotes(soup):
        hrs = soup.find_all("hr")
        if len(hrs):
            last_hr = hrs.pop()
            if not last_hr.get("style"):
                return last_hr

        return False

    def _find_docx_html_endnotes(soup):
        # Find the endnotes in a docx export
        ols = soup.find_all("ol")
        if ols:
            last_ol = ols.pop()
            # Check if the first li in the ol contains the id "footnote-0"
            first_li = last_ol.find("li")
            if first_li and first_li.get("id") == "footnote-0":
                return last_ol

        return False

    if soup.find(_match_endnotes):
        return

    # Find the endnotes in Google Docs HTML export
    last_hr = _find_google_doc_html_endnotes(soup)
    if last_hr:
        # Repurpose the hr element as an h1 element
        last_hr.name = "h1"
        last_hr.string = "Endnotes"

    else:
        # Else, find the endnotes in Google Docs HTML export
        last_ol = _find_docx_html_endnotes(soup)
        if last_ol:
            # Create the h1 element
            h1_tag = soup.new_tag("h1")
            h1_tag.string = "Endnotes"

            # Insert the h1 element before the ol
            last_ol.insert_before(h1_tag)


def escape_asterisks_in_table_cells(soup):
    """
    This function mutates the soup!

    Replaces "*" with "\*" in table cells, unless the asterisk is already preceded by a backslash.

    This is to solve the problem where "required" elements in tables end up becoming <em> elements by accident.
    """

    # Match asterisks not preceded by a backslash
    pattern = re.compile(r"(?<!\\)\*")

    for cell in soup.find_all(["td", "th"]):
        for content in cell.find_all(text=True):
            # Use the regex pattern to replace '*' with '\*' only if '*' is not already preceded by '\'
            escaped_content = pattern.sub(r"\\*", content)
            content.replace_with(escaped_content)


def _get_font_size_from_cssText(cssText):
    """
    Extracts the font-size value from a CSS text block.

    This function parses a CSS text block and extracts the font size specified in it.
    If the font size is specified in points (pt), it returns the size as an integer.
    Otherwise, it returns the font size as a string.

    Note that the font-size rule definitely exists when the block is passed in.
    """
    font_size = [rule for rule in cssText.split("\n") if "font-size" in rule]

    font_size = font_size.pop().split(":")[1].strip(" ;")
    if "pt" in font_size:
        try:
            return int(font_size.strip("pt"))
        except ValueError:
            pass

    return font_size


def _get_classnames_for_font_weight_bold(styles_as_text):
    """
    Extracts class names from CSS text that have a font-weight: 700
    and filters out classes with a font size of 18pt or larger.

    Returns a set of class names that match the criteria
    (bold font weight and optionally font size less than 18pt).
    """
    cssutils.log.setLevel(logging.CRITICAL)
    stylesheet = cssutils.parseString(styles_as_text)

    include_rule = "font-weight: 700"
    matching_classes = set()

    for rule in stylesheet:
        if isinstance(rule, cssutils.css.CSSStyleRule):
            for selector in rule.selectorList:
                if selector.selectorText.startswith(
                    "."
                ):  # Make sure it's a class selector
                    class_name = selector.selectorText[1:]
                    if include_rule in rule.style.cssText:
                        font_size = ""

                        if "font-size" in rule.style.cssText:
                            font_size = _get_font_size_from_cssText(rule.style.cssText)

                        # exclude classes with font-size >= 18pt
                        if font_size and isinstance(font_size, int) and font_size >= 18:
                            pass
                        else:
                            matching_classes.add(class_name)

    return matching_classes


def add_strongs_to_soup(soup):
    """
    This function mutates the soup!

    Wraps elements with a specified class in a <strong> tag, excluding elements
    in the first row of a table.

    This function searches for elements with class names that indicate bold font
    weight (as determined by the _get_classnames_for_font_weight_bold function) and
    wraps them in a <strong> tag to preserve them once we convert the HTML to markdown.
    Elements in the first row of a table (inside a <td> within the first <tr>) are excluded
    from this because table headings are already bolded.
    """
    style_tag = soup.find("style")
    if style_tag:
        matching_classes = _get_classnames_for_font_weight_bold(style_tag.get_text())

        for class_name in matching_classes:
            for element in soup.find_all(class_=class_name):
                # Check if the element is inside a <td> in the first row of a table
                parent_tr = element.find_parent("tr")
                if parent_tr and parent_tr.find_previous_sibling() is None:
                    continue
                element.wrap(soup.new_tag("strong"))


def add_em_to_de_minimis(soup):
    """
    This function mutates the soup!

    Transforms all <span> elements containing the exact text 'de minimis' (case insensitive)
    into <em> elements within the provided BeautifulSoup object.
    """

    spans = soup.findAll("span", text=re.compile("^de minimis$", re.I))
    for span in spans:
        span.name = "em"


def clean_heading_tags(soup):
    """
    This function mutates the soup!

    Finds all headings, it will:
    - Unwrap span tags in the heading
    - Collapse multiple spaces into one
    - Trim leading and trailing spaces
    """
    # Find all headings (h1, h2, ..., h6)
    headings = soup.find_all(re.compile("^h[1-6]$"))

    for heading in headings:
        # Unwrap spans
        for span in heading.find_all("span"):
            span.unwrap()

        # Get the text content of the heading
        text = heading.get_text()

        # Collapse multiple spaces into one
        text = re.sub(r"\s+", " ", text)

        # Trim whitespace from the front and back
        text = text.strip()

        # Replace the original heading text with the cleaned text
        heading.string = text


def _change_existing_anchor_links_to_new_id(soup, element, new_id):
    """
    Update all anchor links in the provided BeautifulSoup object that point to
    the original ID of the specified element to point to new_id.

    Example:
        Given an element <div id="section1"> and a new_id "section2", all
        links in the document with href="#section1" will be changed to
        href="#section2".
    """
    old_id = element.attrs.get("id")
    if old_id:
        links_to_old_id = soup.find_all("a", href="#{}".format(old_id))
        for old_link in links_to_old_id:
            old_link["href"] = "#{}".format(new_id)


def preserve_bookmark_links(soup):
    """
    This function mutates the soup!

    Preserves bookmark links by transferring the 'name' attribute from empty <a> tags to be the ID of the following paragraph elements.

    This function searches for all <a> tags with an ID that starts with "#bookmark". If such an <a> tag is empty (i.e., contains no text),
    the function transfers the 'id' attribute to the 'id' attribute on the next element if that element is a paragraph.

    Empty <a> tags are removed in a later step.
    """
    # Find all <a> tags with an id starting with "#bookmark"
    bookmark_id_anchors = soup.find_all(
        "a", href=lambda x: x and x.startswith("#bookmark")
    )

    bookmark_ids = set([link["href"][1:] for link in bookmark_id_anchors])

    for bookmark_id in bookmark_ids:
        # Find the corresponding anchor tag with the same name, and check if it's empty
        a = soup.find("a", id=bookmark_id)
        if a and not a.text.strip():
            next_elem = a.find_next()
            if next_elem and next_elem.name == "p":
                _change_existing_anchor_links_to_new_id(soup, next_elem, a["id"])
                # Transfer the id to the next paragraph element, replacing any existing id
                next_elem["id"] = a["id"]

                # Find the closest preceding heading
                prev_elem = a.find_previous()
                while prev_elem:
                    if prev_elem.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                        # we want the heading level to be 1 more than the last heading
                        level = int(prev_elem.name[1]) + 1
                        next_elem["class"] = next_elem.get("class", []) + [
                            "bookmark-level-{}".format(level)
                        ]
                        break
                    prev_elem = prev_elem.find_previous()

                # If no preceding heading is found, assign a generic class
                if not prev_elem:
                    next_elem["class"] = next_elem.get("class", []) + ["bookmark"]

                a.decompose()  # Remove the empty <a> tag
        if not a:
            broken_link = next(
                (
                    link
                    for link in bookmark_id_anchors
                    if bookmark_id in link.get("href")
                )
            )

            # add two underscores so that we can identify this link later as a dead link
            broken_link["href"] = "#__{}".format(bookmark_id)


def preserve_heading_links(soup):
    """
    This function mutates the soup!

    Preserves heading links by transferring IDs from empty <a> tags to their parent elements.
    The <a> tags are presumed to be inside heading tags, although this isn't explicit in the function.

    This function searches for all <a> tags with an ID that starts with "_". If such an <a> tag is empty (i.e., contains no text),
    the function transfers the ID to the parent element and removes the empty <a> tag.

    Empty <a> tags are removed in a later step, so these were getting screened out and then we were losing the link to the heading.
    """
    # Find all <a> tags with an id starting with "_heading"
    heading_id_anchors = soup.find_all("a", id=lambda x: x and x.startswith("_"))

    for a in heading_id_anchors:
        # Check if the <a> tag is empty
        if not a.text.strip():
            parent = a.parent
            if parent:
                _change_existing_anchor_links_to_new_id(soup, parent, a["id"])
                # Transfer the id to the parent element, replacing any existing id
                parent["id"] = a["id"]
                a.decompose()  # Remove the empty <a> tag


def unwrap_nested_lists(soup):
    def _has_only_nested_ul(li):
        # Check if li has exactly one child which is a ul
        children = li.find_all(recursive=False)
        if len(children) == 1 and children[0].name == "ul":
            # Ensure there is no direct text in the li
            for content in li.contents:
                if isinstance(content, NavigableString) and content.strip():
                    return False
            return True
        return False

    for li in soup.find_all("li"):
        if _has_only_nested_ul(li):
            li.unwrap()

    for ul in soup.select("ul > ul"):
        ul.unwrap()
