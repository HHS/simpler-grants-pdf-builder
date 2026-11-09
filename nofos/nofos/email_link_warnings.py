import re
from urllib.parse import quote, unquote

from bs4 import BeautifulSoup, Comment
from martor.utils import markdownify

# Match common addresses in prose, while consuming bare URLs as a unit.
EMAIL_IN_TEXT = re.compile(
    r"(?i:https?)://[^\s<>]+|"
    r"(?<![\w.+%@-])"
    r"(?P<email>[A-Za-z0-9_+%-]+(?:\.[A-Za-z0-9_+%-]+)*"
    r"@(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,})"
    r"(?![\w%@-]|\.[\w-])"
)


def find_email_link_warnings(nofo):
    """Report each distinct address that needs an email link in a subsection."""
    warnings = []
    for section in nofo.sections.prefetch_related("subsections"):
        for subsection in section.subsections.all():
            soup = BeautifulSoup(markdownify(subsection.body or ""), "html.parser")
            reported = set()
            for text in soup.find_all(string=True):
                if isinstance(text, Comment) or text.find_parent(
                    ["code", "pre", "script", "style"]
                ):
                    continue

                anchor = text.find_parent("a")
                href = anchor.get("href", "").strip() if anchor else ""
                scheme, _, destination = href.partition(":")
                recipient = (
                    unquote(destination.partition("?")[0])
                    if scheme.lower() == "mailto"
                    else ""
                )
                for match in EMAIL_IN_TEXT.finditer(text):
                    address = match["email"]
                    if address is None or address in reported:
                        continue
                    if address.lower() == recipient.lower():
                        continue
                    reported.add(address)
                    label = address.replace("_", r"\_")
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
