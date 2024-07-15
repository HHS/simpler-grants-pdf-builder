import re

from django import template
from django.template import Node
from django.utils.functional import keep_lazy_text

register = template.Library()


@register.tag
def whitespaceless(parser, token):
    """
    Remove whitespace within HTML tags,
    including tab, newline and extra space
    characters.

    Example usage::

        {% whitespaceless %}
            <p class="  test
                        test2
                        test3  ">
                <a href="foo/">Foo</a>
            </p>
        {% endwhitespaceless %}

    This example returns this HTML::

        <p class="test test2 test3"><a href="foo/">Foo</a></p>

    This affects all text within the
    `whitespaceless` command without prejudice.
    Use with caution.
    """
    nodelist = parser.parse(("endwhitespaceless",))
    parser.delete_first_token()
    return WhitespacelessNode(nodelist)


class WhitespacelessNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        return strip_whitespace(self.nodelist.render(context).strip())


@keep_lazy_text
def strip_whitespace(value):
    """
    Return the given HTML with any newlines,
    duplicate whitespace, or trailing spaces
    are removed .
    """
    # Process duplicate whitespace occurrences or
    # *any* newline occurrences and reduce to a single space
    value = re.sub(r"\s{2,}|[\n]+", " ", str(value))
    # After processing all of the above,
    # any trailing spaces should also be removed
    # Trailing space examples:
    #   - <div >                    Matched by: \s(?=[<>"])
    #   - < div>                    Matched by: (?<=[<>])\s
    #   - <div class="block ">      Matched by: \s(?=[<>"])
    #   - <div class=" block">      Matched by: (?<==\")\s
    #   - <span> text               Matched by: (?<=[<>])\s
    #   - text </span>              Matched by: \s(?=[<>"])
    value = re.sub(r'\s(?=[<>"])|(?<==\")\s|(?<=[<>])\s', "", str(value))
    return value
