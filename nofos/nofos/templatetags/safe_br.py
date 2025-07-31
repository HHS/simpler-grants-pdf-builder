import re

from django import template
from django.utils.html import escape, mark_safe

register = template.Library()

# Allow <br>, <br />, <BR>, <BR />
BR_TAG_RE = re.compile(r"<br\s*/?>", flags=re.IGNORECASE)


# This filter escapes all HTML except <br> tags
@register.filter
def safe_br(value):
    if not isinstance(value, str):
        return value

    # First, temporarily replace any real <br> tags with a placeholder
    placeholder = "___BR_TAG___"
    br_preserved = BR_TAG_RE.sub(placeholder, value)

    # Escape everything else
    escaped = escape(br_preserved)

    # Restore the <br> placeholder
    result = escaped.replace(placeholder, "<br>")

    return mark_safe(result)


# This filter removes <br> tags from a string
@register.filter
def strip_br(value):
    if not isinstance(value, str):
        return value

    # Just remove all <br>, <br/>, <br />, <BR>, etc.
    return BR_TAG_RE.sub("", value)


@register.filter
def safe_br_ins_del(value):
    if not isinstance(value, str):
        return value

    # Define tag placeholders
    placeholders = {
        "<br>": "___BR___",
        "<br/>": "___BR___",
        "<br />": "___BR___",
        "<ins>": "___INS_OPEN___",
        "</ins>": "___INS_CLOSE___",
        "<del>": "___DEL_OPEN___",
        "</del>": "___DEL_CLOSE___",
    }

    # Regex to find all allowed tags, case-insensitive
    TAG_RE = re.compile(r"</?(br\s*/?|ins|del)>", flags=re.IGNORECASE)

    # Replace all allowed tags with placeholders
    def replace_tag(match):
        tag = match.group(0).lower().replace(" ", "")
        if tag == "<br/>":
            tag = "<br>"
        return placeholders.get(tag, "")

    replaced = TAG_RE.sub(replace_tag, value)

    # Escape everything else
    escaped = escape(replaced)

    # Restore placeholders to real tags
    restored = (
        escaped.replace("___BR___", "<br>")
        .replace("___INS_OPEN___", "<ins>")
        .replace("___INS_CLOSE___", "</ins>")
        .replace("___DEL_OPEN___", "<del>")
        .replace("___DEL_CLOSE___", "</del>")
    )

    return mark_safe(restored)


@register.filter
def strip_br_ins_del(value):
    if not isinstance(value, str):
        return value

    TAG_RE = re.compile(r"</?(br\s*/?|ins|del)>", flags=re.IGNORECASE)

    # Just remove all <br>, <br/>, <br />, <BR>, etc.
    return TAG_RE.sub("", value)
