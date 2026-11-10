import re
from urllib.parse import quote, unquote

from bs4 import BeautifulSoup, Comment
from markdown import markdown
from martor.settings import (
    MARTOR_MARKDOWN_EXTENSION_CONFIGS,
    MARTOR_MARKDOWN_EXTENSIONS,
)

# Match common addresses in prose. Consume bare URLs and unsupported quoted
# addresses whole; the left boundary also rules out partial local-part matches.
EMAIL_IN_TEXT = re.compile(
    r"(?i:https?)://[^\s<>]+|"
    r'"(?:[^"\\\r\n]|\\.)*"@[^\s<>]*|'
    r"(?<![\w.!#$%&'*+/=?^`{|}~@’–—-])"
    r"(?P<email>[A-Za-z0-9_+%&-]+(?:[.'][A-Za-z0-9_+%&-]+)*"
    r"@(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,})"
    r"(?![\w%@-]|\.[\w-])"
)


def _parse_markdown_for_email_check(body):
    # Keep the editor's Markdown syntax, but do not let smart quotes and dashes
    # change the address before checking it. This HTML is inspected, not served.
    html = markdown(
        body,
        extensions=[
            name
            for name in MARTOR_MARKDOWN_EXTENSIONS
            if name != "markdown.extensions.smarty"
        ],
        extension_configs=MARTOR_MARKDOWN_EXTENSION_CONFIGS,
    )
    return BeautifulSoup(html, "html.parser")


def find_email_link_warnings(nofo):
    """Report each distinct address that needs an email link in a subsection."""
    warnings = []
    for section in nofo.sections.prefetch_related("subsections"):
        for subsection in section.subsections.all():
            soup = _parse_markdown_for_email_check(subsection.body or "")
            reported = set()
            for text in soup.find_all(string=True):
                if isinstance(text, Comment) or text.find_parent(
                    ["code", "pre", "script", "style"]
                ):
                    continue

                anchor = text.find_parent("a")
                href = anchor.get("href", "").strip() if anchor else ""
                scheme, _, destination = href.partition(":")
                recipients = (
                    {
                        unquote(recipient).lower()
                        for recipient in destination.partition("?")[0].split(",")
                    }
                    if scheme.lower() == "mailto"
                    else set()
                )
                for match in EMAIL_IN_TEXT.finditer(text):
                    address = match["email"]
                    if address is None or address in reported:
                        continue
                    if address.lower() in recipients:
                        continue
                    reported.add(address)
                    # Preserve the visible address through the editor's smart
                    # typography when the suggested Markdown is pasted back.
                    label = (
                        address.replace("_", r"\_")
                        .replace("'", "&#39;")
                        .replace("--", "&#45;&#45;")
                    )
                    target = quote(address, safe="@+")
                    warnings.append(
                        {
                            "section": section,
                            "subsection": subsection,
                            "address": address,
                            "markdown": f"[{label}](mailto:{target})",
                        }
                    )
    return warnings
