from xml.etree import ElementTree as ET

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor

r"""
Curly brace variable syntax highlighter for Markdown.

This extension finds and wraps placeholders like {Variable name}
in a <span> element so they can be styled in the rendered HTML.

----------------------------------------------------------------
Regex pattern used:
    (?<!\\)\{(?![:.#])([^{}]*\S[^{}]*)\}

Explanation:
    (?<!\\)        Negative lookbehind — ensure the "{" is not escaped
                   (e.g., "\{" is ignored)

    \{             Match literal opening brace

    (?![:.#])      Negative lookahead — do NOT match if the very next
                   character is ':', '.', or '#'.
                   This lets us ignore attribute list syntax like:
                     {: #an_id .a_class }
                     {.a_class}
                     {#an_id}

    [^{}]*         Allow any number of non-brace characters

    \S             Require at least one non-whitespace character
                   (prevents matching "{   }")

    [^{}]*         Allow more non-brace characters after that

    \}             Match literal closing brace

Matches:
    {variable}
    { variable with spaces }
    {List: items}
    {Prompt text here}

Ignores:
    \{escaped\}                ← escaped braces
    {   }                      ← only whitespace inside
    {: #an_id .a_class }       ← attribute lists (start with "{:")
    {.class}                   ← attribute lists (start with "{.")
    {#id}                      ← attribute lists (start with "{#")
    {nested {braces}}          ← nested braces are not supported

The same regex is also reused in Django model logic for variable extraction.

We also have a JavaScript file at
`nofos/bloom_nofos/static/js/composer/martor-curly-variables.js`
that implements this same regex logic in JS (used for highlighting in
the Ace markdown editor). Keep them in sync.
----------------------------------------------------------------
"""

CURLY_VARIABLE_PATTERN = r"(?<!\\)\{(?![:.#])([^{}]*\S[^{}]*)\}"


class CurlyVarInlineProcessor(InlineProcessor):
    """
    Markdown inline processor that finds {curly variables}
    and wraps them in a <span class="md-curly-variable"> element.

    Example:
        Input:  "Your total is {Amount}."
        Output: "Your total is <span class='md-curly-variable'>{Amount}</span>."
    """

    def handleMatch(self, m, data):
        el = ET.Element("span", {"class": "md-curly-variable"})
        el.text = m.group(0)
        return el, m.start(0), m.end(0)


class CurlyVarExtension(Extension):
    """
    Markdown extension that registers the CurlyVarInlineProcessor.

    The processor runs fairly early (priority 185) so that variable
    placeholders are wrapped before other inline elements (e.g., emphasis).
    """

    def extendMarkdown(self, md):
        proc = CurlyVarInlineProcessor(CURLY_VARIABLE_PATTERN, md)
        md.inlinePatterns.register(proc, "composer_curly_variables", 185)


def makeExtension(**kwargs):
    return CurlyVarExtension(**kwargs)
