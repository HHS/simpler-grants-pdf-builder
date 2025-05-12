import re

from bs4 import BeautifulSoup
from markdownify import MarkdownConverter

# this is copied from __init__.py in markdownify
# https://github.com/matthewwithanm/python-markdownify/blob/2d654a6b7e822e1547199da855c9d304d162cb27/markdownify/__init__.py#L9
re_line_with_content = re.compile(r"^(.*)", flags=re.MULTILINE)


def get_width_class(th):
    def _get_num_columns_th(th):
        return len(th.parent.find_all("th"))

    def _get_width_class_from_num_columns(num_cols=0):
        # Determine the width class based on the number of <th> elements in the first table row
        width_class = ""
        if num_cols == 3:
            width_class = "w-33"
        elif num_cols == 4:
            width_class = "w-25"
        elif num_cols == 5:
            width_class = "w-20"

        return width_class

    def _get_width_class_if_application_checklist_th(th):
        # grab the text and lowercase please
        th_text = th.get_text(strip=True).lower()

        # Applying specific rules based on the header content
        if th_text == "component":
            return "w-45"
        if th_text.startswith(("how to upload", "how to submit")):
            return "w-40"
        if "page limit" in th_text:
            return "w-15"

        # default to w-33
        return "w-33"

    num_cols = _get_num_columns_th(th)
    width_class = _get_width_class_from_num_columns(num_cols)

    if num_cols == 3:
        width_class = _get_width_class_if_application_checklist_th(th)

    return width_class


class NofoMarkdownConverter(MarkdownConverter):
    """
    Leave ULs and OLs TDs as HTML
    """

    def _remove_classes_recursive(self, container_el):
        if container_el.has_attr("class"):
            del container_el["class"]

        for el in container_el.find_all(True):
            if el.has_attr("class"):
                del el["class"]

    def convert_a(self, el, text, parent_tags):
        # keep the in-text footnote links as HTML so that the ids aren't lost
        if el and el.attrs.get("id", "").startswith(("footnote", "endnote")):
            self._remove_classes_recursive(el)
            # wrap these links in <sup> element
            el.wrap(BeautifulSoup("", "html.parser").new_tag("sup"))
            # return link AND parent (which is <sup>)
            return str(el.parent)

        return super().convert_a(el, text, parent_tags)

    def convert_div(self, el, text, parent_tags):
        # Output raw HTML if the div has role="heading" attribute
        if el.get("role") == "heading":
            return str(el)

        if el.get("class") and "heading-8" in el.get("class"):
            return str(el)

        # Else, return text, which is what process_text would return
        return text

    def convert_ol(self, el, text, parent_tags):
        # return as HMTL to preserve "start" attribute if anything other than "1"
        start = el.get("start", "1")
        if start and start != "1":
            self._remove_classes_recursive(el)
            return str(el)

        for parent in el.parents:
            if parent.name == "td":
                self._remove_classes_recursive(el)
                return str(el).replace("*", "&ast;")

        # save the footnote list as HTML so that the ids aren't lost
        first_li = el.find("li")
        if first_li and first_li.attrs.get("id", "").startswith(
            ("footnote", "endnote")
        ):
            self._remove_classes_recursive(el)
            [li.attrs.update({"tabindex": "-1"}) for li in el.find_all("li")]
            return str(el.prettify())

        return super().convert_ol(el, text, parent_tags)

    def convert_ul(self, el, text, parent_tags):
        for parent in el.parents:
            if parent.name == "td":
                self._remove_classes_recursive(el)
                return str(el).replace("*", "&ast;")

        return super().convert_ul(el, text, parent_tags)

    def convert_li(self, el, text, parent_tags):
        # handle some early-exit scenarios
        text = (text or "").strip()
        if not text:
            return "\n"

        # determine list item bullet character to use
        parent = el.parent
        if parent is not None and parent.name == "ol":
            if parent.get("start") and str(parent.get("start")).isnumeric():
                start = int(parent.get("start"))
            else:
                start = 1
            # For ordered lists, calculate based on sibling count
            bullet = "%s." % (start + len(el.find_previous_siblings("li")))
        else:
            # For unordered lists, calculate nested depth (if needed)
            depth = -1
            tmp_el = el
            while tmp_el:
                if tmp_el.name == "ul":
                    depth += 1
                tmp_el = tmp_el.parent
            bullets = self.options["bullets"]
            bullet = bullets[depth % len(bullets)]

        # Add a trailing space to the bullet marker
        bullet = bullet + " "

        # Instead of calculating indent from bullet length, use fixed 4 spaces
        fixed_indent = "    "  # 4 spaces, as required by CommonMark
        bullet_indent = fixed_indent

        # Indent the content lines with a fixed indent of 4 spaces
        def _indent_for_li(match):
            line_content = match.group(1)
            return bullet_indent + line_content if line_content else ""

        text = re_line_with_content.sub(_indent_for_li, text)

        # Replace the first 4 spaces with the bullet (preserving any extra characters beyond the 4-char indent)
        text = bullet + text[len(fixed_indent) :]

        return "%s\n" % text

    def convert_p(self, el, text, parent_tags):
        # if we are in a table cell, and that table cell contains multiple children, return the string
        if el.parent.name == "td" or el.parent.name == "th":
            if len(list(el.parent.children)) > 1:
                return str(el).replace("*", "&ast;")

        # if the paragraph has an id that includes the string "bookmark", keep the paragraph as-is
        p_id = el.attrs.get("id") if el else None
        if p_id:
            if "bookmark" in p_id or "table-heading" in p_id:
                return str(el)

        return super().convert_p(el, text, parent_tags)

    def convert_table(self, el, text, parent_tags):
        def _has_colspan_or_rowspan_not_one(tag):
            # Check for colspan/rowspan attributes not equal to '1'
            colspan = tag.get("colspan", "1")
            rowspan = tag.get("rowspan", "1")
            return colspan != "1" or rowspan != "1"

        def _get_first_row_ths(table):
            # get the ths in the first row, or empty array
            first_row = table.find("tr")
            if not first_row:
                return []

            return first_row.find_all("th")

        cells = el.find_all(["td", "th"])
        for cell in cells:
            # return table as HTML if we find colspan/rowspan != 1 for any cell
            if _has_colspan_or_rowspan_not_one(cell):
                self._remove_classes_recursive(el)

                for th in _get_first_row_ths(table=el):
                    width_class = get_width_class(th)
                    if width_class:
                        th["class"] = [width_class]

                return str(el.prettify()) + "\n"

        return super().convert_table(el, text, parent_tags)

    def convert_th(self, el, text, parent_tags):
        # automatically add width classes to table headers based on number of <th> elements
        width_class = get_width_class(th=el)
        if width_class:
            text = f"{text.strip()} {{: .{width_class} }}"

        return super().convert_th(el, text, parent_tags)


# Create shorthand method for conversion
def md(html, **options):
    return NofoMarkdownConverter(**options).convert(html)
