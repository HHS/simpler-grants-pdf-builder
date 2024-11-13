from bs4 import BeautifulSoup
from markdownify import MarkdownConverter


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

    def convert_a(self, el, text, convert_as_inline):
        # keep the in-text footnote links as HTML so that the ids aren't lost
        if el and el.attrs.get("id", "").startswith(("footnote", "endnote")):
            self._remove_classes_recursive(el)
            # wrap these links in <sup> element
            el.wrap(BeautifulSoup("", "html.parser").new_tag("sup"))
            # return link AND parent (which is <sup>)
            return str(el.parent)

        return super().convert_a(el, text, convert_as_inline)

    def convert_div(self, el, text, convert_as_inline):
        # Output raw HTML if the div has role="heading" attribute
        if el.get("role") == "heading":
            return str(el)

        # Else, return text, which is what process_text would return
        return text

    def convert_ol(self, el, text, convert_as_inline):
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

        return super().convert_ol(el, text, convert_as_inline)

    def convert_ul(self, el, text, convert_as_inline):
        for parent in el.parents:
            if parent.name == "td":
                self._remove_classes_recursive(el)
                return str(el).replace("*", "&ast;")

        return super().convert_ul(el, text, convert_as_inline)

    def convert_p(self, el, text, convert_as_inline):
        # if we are in a table cell, and that table cell contains multiple children, return the string
        if el.parent.name == "td" or el.parent.name == "th":
            if len(list(el.parent.children)) > 1:
                return str(el).replace("*", "&ast;")

        # if the paragraph has an id that includes the string "bookmark", keep the paragraph as-is
        p_id = el.attrs.get("id") if el else None
        if p_id:
            if "bookmark" in p_id or "table-heading" in p_id:
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

    def convert_th(self, el, text, convert_as_inline):
        # automatically add width classes to table headers based on number of <th> elements
        def _determine_width_class_from_th_siblings(th_count=0):
            # Determine the width class based on the number of <th> elements in the first table row
            width_class = ""
            if th_count == 3:
                width_class = "w-33"
            elif th_count == 4:
                width_class = "w-25"
            elif th_count == 5:
                width_class = "w-20"

            return width_class

        def _determine_width_class_if_application_checklist_th(el):
            # grab the text and lowercase please
            th_text = el.get_text(strip=True).lower()

            # Applying specific rules based on the header content
            if th_text == "component":
                return "w-45"
            if th_text.startswith(("how to upload", "how to submit")):
                return "w-40"
            if "page limit" in th_text:
                return "w-15"

            # default to w-33
            return "w-33"

        th_count = len(el.parent.find_all("th"))
        # Add the class to the text if a class was determined
        width_class = _determine_width_class_from_th_siblings(th_count)

        if th_count == 3:
            width_class = _determine_width_class_if_application_checklist_th(el)

        if width_class:
            text = f"{text.strip()} {{: .{width_class} }}"

        return super().convert_th(el, text, convert_as_inline)


# Create shorthand method for conversion
def md(html, **options):
    return NofoMarkdownConverter(**options).convert(html)
