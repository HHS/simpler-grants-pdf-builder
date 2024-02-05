from bs4 import BeautifulSoup, NavigableString
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def wrap_text_before_colon_in_strong(p, soup):
    # Initialize a flag to track when the colon is found
    found_colon = False
    # Create a strong tag
    strong_tag = soup.new_tag("strong")
    span_tag = soup.new_tag("span")

    # Iterate over contents, moving elements before the colon to the strong tag
    for content in p.contents[:]:

        if found_colon:
            span_tag.append(content.extract())

        if ":" in content:
            before_colon, after_colon = content.split(":", 1)
            strong_tag.append(before_colon + ":")
            # Replace the original content with what's after the colon
            span_tag.append(after_colon)
            found_colon = True  # Mark colon as found
        else:
            # Move content to strong tag if colon not yet found
            strong_tag.append(content.extract())

    # Insert the strong tag at the beginning of the paragraph
    p.clear()
    p.append(strong_tag)
    p.append(span_tag)


@register.filter()
def callout_box_contents(html_string):
    soup = BeautifulSoup(html_string, "html.parser")
    for paragraph in soup.find_all("p"):
        text = paragraph.get_text()
        if ":" in text:
            wrap_text_before_colon_in_strong(paragraph, soup)

    return mark_safe(str(soup))
