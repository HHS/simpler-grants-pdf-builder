"""Synthetic drafting-stage PDFs, unrelated to private source documents.

Each block is one source-declared paragraph, heading, or table cell. The
plain-text reference is kept here so a reader can check content and counts
without running the parser. These minimal tags test semantics, not PDF/UA.
"""

from io import BytesIO

from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    BooleanObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)

IDENTIFIERS = (
    ("H1", "Opportunity number: HHS-2027-TEST-0001"),
    ("H2", "Assistance listing: 93.123"),
)
# 17 words, three complete sentences, two paragraphs, one passive sentence.
PROSE = (
    ("P", "The agency funds local work. Teams can send a clear plan."),
    ("P", "The plan was approved by staff."),
)
WRITER_INSTRUCTION = "Writers must remove this note before they share the notice."


def draft_pdf(blocks=PROSE, *, tagged=True, font_size=12):
    """Create a PDF; newline wraps a block, form feed continues it on a page.

    Continuations retain one structure element, rather than assigning a new
    paragraph to each physical line or page. This models semantic continuity.
    """
    writer = PdfWriter()
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    children = ArrayObject()
    root = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/StructTreeRoot"),
                NameObject("/K"): children,
            }
        )
    )
    pages = []

    def new_page():
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        content = []
        pages.append((page, content))
        return page, content

    page, content = new_page()
    y = 700
    for tag, text in (*IDENTIFIERS, *blocks):
        assert text.isascii() and not any(c in text for c in "()\\")
        parent = root
        siblings = children
        ancestors = {"LBody": ("L", "LI"), "TD": ("Table", "TR"), "TH": ("Table", "TR")}
        for ancestor in ancestors.get(tag, ()):
            descendants = ArrayObject()
            container = writer._add_object(
                DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/StructElem"),
                        NameObject("/S"): NameObject(f"/{ancestor}"),
                        NameObject("/P"): parent,
                        NameObject("/K"): descendants,
                    }
                )
            )
            siblings.append(container)
            parent, siblings = container, descendants
        references = ArrayObject()
        siblings.append(
            writer._add_object(
                DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/StructElem"),
                        NameObject("/S"): NameObject(f"/{tag}"),
                        NameObject("/P"): parent,
                        NameObject("/K"): references,
                    }
                )
            )
        )
        for part_index, part in enumerate(text.split("\f")):
            if part_index:
                page, content = new_page()
                y = 700
            for line_text in part.split("\n"):
                mcid = len(content)
                references.append(
                    DictionaryObject(
                        {
                            NameObject("/Type"): NameObject("/MCR"),
                            NameObject("/Pg"): page.indirect_reference,
                            NameObject("/MCID"): NumberObject(mcid),
                        }
                    )
                )
                line = f"BT /F1 {font_size} Tf 50 {y} Td ({line_text}) Tj ET"
                if tagged:
                    line = f"/{tag} <</MCID {mcid}>> BDC {line} EMC"
                content.append(line.encode("ascii"))
                y -= 20
            y -= 20
    if tagged:
        writer._root_object[NameObject("/StructTreeRoot")] = root
        writer._root_object[NameObject("/MarkInfo")] = DictionaryObject(
            {NameObject("/Marked"): BooleanObject(True)}
        )
    for page, content in pages:
        stream = DecodedStreamObject()
        stream.set_data(b"\n".join(content))
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
