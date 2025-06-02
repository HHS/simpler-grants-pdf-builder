import re
from django import template
from django.utils.html import escape, mark_safe

register = template.Library()

# Allow <br>, <br />, <BR>, <BR />
BR_TAG_RE = re.compile(r'<br\s*/?>', flags=re.IGNORECASE)

@register.filter
def safe_br(value):
    if not isinstance(value, str):
        return value

    # First, temporarily replace any real <br> tags with a placeholder
    placeholder = '___BR_TAG___'
    br_preserved = BR_TAG_RE.sub(placeholder, value)

    # Escape everything else
    escaped = escape(br_preserved)

    # Restore the <br> placeholder
    result = escaped.replace(placeholder, '<br>')

    return mark_safe(result)

