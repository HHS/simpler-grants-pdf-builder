from io import BytesIO
from unittest import TestCase
from zipfile import ZipFile

from .word_endnotes import preserve_word_note_cross_references


class WordNoteCrossReferenceTests(TestCase):
    def document(self, body):
        output = BytesIO()
        with ZipFile(output, "w") as archive:
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                f"<w:body>{body}</w:body></w:document>",
            )
        output.seek(0)
        return output

    def test_unsupported_or_ambiguous_fields_preserve_original_bytes(self):
        bookmark = (
            '<w:bookmarkStart w:id="1" w:name="note"/>'
            '<w:r><w:endnoteReference w:id="2"/></w:r>'
            '<w:bookmarkEnd w:id="1"/>'
        )
        for instruction, result, target in (
            (r"NOTEREF note \p", "<w:r><w:t>1</w:t></w:r>", bookmark),
            (r"NOTEREF note \h", "<w:r><w:t>above</w:t></w:r>", bookmark),
            (r"NOTEREF missing \h", "<w:r><w:t>1</w:t></w:r>", bookmark),
            (r"NOTEREF note \h", "<w:r><w:t>1</w:t></w:r>", bookmark + bookmark),
            (
                r"NOTEREF note \h",
                "<w:r><w:t>1</w:t></w:r>",
                bookmark.replace(
                    "<w:bookmarkEnd",
                    '<w:r><w:endnoteReference w:id="3"/></w:r><w:bookmarkEnd',
                ),
            ),
            (
                r"NOTEREF note \h",
                '<w:fldSimple w:instr="REF other"><w:r><w:t>1</w:t></w:r></w:fldSimple>',
                bookmark,
            ),
        ):
            with self.subTest(instruction=instruction, target=target, result=result):
                source = self.document(
                    f'<w:p>{target}<w:fldSimple w:instr="{instruction}">{result}</w:fldSimple></w:p>'
                )
                before = source.getvalue()
                self.assertIs(preserve_word_note_cross_references(source), source)
                self.assertEqual(source.read(), before)

    def test_incomplete_complex_field_is_not_rewritten(self):
        source = self.document(
            '<w:p><w:bookmarkStart w:id="1" w:name="note"/>'
            '<w:r><w:footnoteReference w:id="2"/></w:r>'
            '<w:bookmarkEnd w:id="1"/>'
            '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
            "<w:r><w:instrText>NOTEREF note</w:instrText></w:r>"
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            "<w:r><w:t>1</w:t></w:r></w:p>"
        )
        before = source.getvalue()
        self.assertIs(preserve_word_note_cross_references(source), source)
        self.assertEqual(source.read(), before)

    def test_complex_field_with_drawing_in_control_run_is_not_discarded(self):
        source = self.document(
            '<w:p><w:bookmarkStart w:id="1" w:name="note"/>'
            '<w:r><w:endnoteReference w:id="2"/></w:r>'
            '<w:bookmarkEnd w:id="1"/>'
            '<w:r><w:fldChar w:fldCharType="begin"/><w:drawing/></w:r>'
            "<w:r><w:instrText>NOTEREF note</w:instrText></w:r>"
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            "<w:r><w:t>1</w:t></w:r>"
            '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
        )
        before = source.getvalue()
        self.assertIs(preserve_word_note_cross_references(source), source)
        self.assertEqual(source.read(), before)
