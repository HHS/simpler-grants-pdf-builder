import re

from django import template

register = template.Library()


@register.filter
def subsection_name_or_placeholder(subsection) -> str:
    if subsection.name:
        return subsection.name

    # 1. Strip out markdown syntax for bold and italics so it doesn't end up in the placeholder
    without_markdown = re.sub(r"(\*\*|__)(.*?)\1", r"\2", subsection.body)  # bold
    without_markdown = re.sub(r"(\*|_)(.*?)\1", r"\2", without_markdown)  # italics

    # 2. Get the first three words
    first_three_words = " ".join(without_markdown.split()[:3])

    # 3. Check for punctuation within the first three words
    match = re.match(r"^(.*?)([.,;:!?]|$)", first_three_words)
    if match:
        first_part = match.group(1)
        punctuation = match.group(2)
        # If no punctuation, placeholder will be first three words + "..."
        if punctuation == "":
            return f"{first_part}..."

        # Otherwise, return up to the punctuation, but not the punctuation itself
        return f"{first_part}"

    # Fallback to "Section {order}" if for some reason the above fails
    return f"Section {subsection.order}"
