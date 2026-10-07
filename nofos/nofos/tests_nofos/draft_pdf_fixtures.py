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
    """Create a one-page PDF with identical reading order in both variants."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
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
    content = []
    for index, (tag, text) in enumerate((*IDENTIFIERS, *blocks)):
        assert text.isascii() and not any(c in text for c in "()\\")
        children.append(
            writer._add_object(
                DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/StructElem"),
                        NameObject("/S"): NameObject(f"/{tag}"),
                        NameObject("/P"): root,
                        NameObject("/Pg"): page.indirect_reference,
                        NameObject("/K"): NumberObject(index),
                    }
                )
            )
        )
        line = f"BT /F1 {font_size} Tf 50 {700-index*40} Td ({text}) Tj ET"
        if tagged:
            line = f"/{tag} <</MCID {index}>> BDC {line} EMC"
        content.append(line.encode("ascii"))
    if tagged:
        writer._root_object[NameObject("/StructTreeRoot")] = root
        writer._root_object[NameObject("/MarkInfo")] = DictionaryObject(
            {NameObject("/Marked"): BooleanObject(True)}
        )
    stream = DecodedStreamObject()
    stream.set_data(b"\n".join(content))
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
