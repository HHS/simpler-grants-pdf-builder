"""Bounded DOCX-to-HTML source adapter for ephemeral readability reports.

No framework setup, NOFO persistence, external file access or PDF conversion.
"""

from pathlib import Path
from zipfile import ZipFile

import mammoth
from bs4 import BeautifulSoup

from .import_transforms import _word_xml, transform_word_document
from .pdf_format_recognition import recognize_word_nofo

MAX_EXPANDED_BYTES = 45 * 1024 * 1024
MAX_ZIP_ENTRIES = 2000
DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
)


def word_html(path: Path) -> tuple[str, bool]:
    """Validate the container before the installed converter reads any members."""
    try:
        with ZipFile(path) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if (
                len(entries) > MAX_ZIP_ENTRIES
                or sum(entry.file_size for entry in entries) > MAX_EXPANDED_BYTES
            ):
                raise ValueError("word_expanded_limit")
            if (
                len(set(names)) != len(names)
                or any(entry.flag_bits & 1 for entry in entries)
                or "word/document.xml" not in names
                or "[Content_Types].xml" not in names
                or "_rels/.rels" not in names
                or any(name.lower().endswith("vbaproject.bin") for name in names)
            ):
                raise ValueError("invalid_word")
            # Relationships can select XML parts without .xml extensions. Scan
            # every bounded member, not just filenames that look like XML.
            for entry in entries:
                data = archive.read(entry)
                declarations = data.replace(b"\0", b"").upper()
                if b"<!DOCTYPE" in declarations or b"<!ENTITY" in declarations:
                    raise ValueError("invalid_word")
            # Do not validate a decoy canonical part while converting another
            # main document selected by the package's root relationship.
            relationships = _word_xml(archive.read("_rels/.rels"))
            main = [
                item
                for item in relationships.getElementsByTagNameNS(
                    "http://schemas.openxmlformats.org/package/2006/relationships",
                    "Relationship",
                )
                if item.getAttribute("Type")
                == "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
            ]
            if (
                len(main) != 1
                or main[0].getAttribute("TargetMode") == "External"
                or main[0].getAttribute("Target")
                not in {"word/document.xml", "/word/document.xml"}
            ):
                raise ValueError("invalid_word")
            types = _word_xml(archive.read("[Content_Types].xml"))
            overrides = types.getElementsByTagNameNS(
                "http://schemas.openxmlformats.org/package/2006/content-types",
                "Override",
            )
            if not any(
                item.getAttribute("PartName") == "/word/document.xml"
                and item.getAttribute("ContentType") == DOCX_CONTENT_TYPE
                for item in overrides
            ):
                raise ValueError("invalid_word")
        with path.open("rb") as stream:
            converted = mammoth.convert_to_html(
                stream,
                external_file_access=False,
                include_embedded_style_map=False,
                convert_image=lambda image: [],
                transform_document=transform_word_document,
            )
        html = converted.value
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        if not text:
            raise ValueError("word_no_text")
        # DOCX has no stable page boundaries. Reuse the same loose recognition
        # signals over a bounded leading text window, not a fictional page count.
        decision = recognize_word_nofo(text[:50000])
        if decision.status != "supported":
            raise ValueError("word_format_unsupported")
        return html, bool(converted.messages)
    except ValueError:
        raise
    except Exception:
        # Never return raw conversion errors or document fragments to the parent.
        raise ValueError("invalid_word") from None
