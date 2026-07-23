from django.test import SimpleTestCase
from mammoth import documents

from nofos.import_transforms import (
    APPLICATION_CHECKLIST_CHILD_STYLE_NAME,
    transform_word_document,
)


def paragraph(text, indent=None):
    return documents.paragraph(
        [documents.run([documents.text(text)])],
        style_id="Table",
        style_name="Table",
        indent=documents.paragraph_indent(start=indent),
    )


def row(first_column_paragraph, second_column_text="Instructions"):
    return documents.table_row(
        [
            documents.table_cell([first_column_paragraph]),
            documents.table_cell([paragraph(second_column_text)]),
        ]
    )


def transform_rows(rows):
    document = documents.document([documents.table(rows)])
    return transform_word_document(document).children[0].children


def first_paragraph(table_row, column=0):
    cells = [
        child for child in table_row.children if isinstance(child, documents.TableCell)
    ]
    return next(
        child
        for child in cells[column].children
        if isinstance(child, documents.Paragraph)
    )


class TransformIndentedChecklistParagraphsTests(SimpleTestCase):
    def test_marks_contiguous_indented_checkbox_rows_after_parent(self):
        rows = transform_rows(
            [
                row(paragraph("¨ Other Attachments Form")),
                row(paragraph("¨ Report on overlap", indent="720")),
                row(paragraph("¨ Indirect cost agreement", indent="720")),
            ]
        )

        self.assertEqual(first_paragraph(rows[0]).style_name, "Table")
        self.assertEqual(
            first_paragraph(rows[1]).style_name,
            APPLICATION_CHECKLIST_CHILD_STYLE_NAME,
        )
        self.assertEqual(
            first_paragraph(rows[2]).style_name,
            APPLICATION_CHECKLIST_CHILD_STYLE_NAME,
        )

    def test_compares_indentation_relative_to_sibling_rows(self):
        rows = transform_rows(
            [
                row(paragraph("☐ Parent", indent="120")),
                row(paragraph("☐ Child", indent="240")),
            ]
        )

        self.assertEqual(
            first_paragraph(rows[1]).style_name,
            APPLICATION_CHECKLIST_CHILD_STYLE_NAME,
        )

    def test_leaves_unindented_checkbox_rows_unchanged(self):
        rows = transform_rows(
            [
                row(paragraph("◻ First form")),
                row(paragraph("◻ Second form")),
            ]
        )

        self.assertEqual(first_paragraph(rows[0]).style_name, "Table")
        self.assertEqual(first_paragraph(rows[1]).style_name, "Table")

    def test_leaves_indented_non_checkbox_paragraph_unchanged(self):
        rows = transform_rows(
            [
                row(paragraph("◻ Parent")),
                row(paragraph("Supporting explanation", indent="720")),
            ]
        )

        self.assertEqual(first_paragraph(rows[1]).style_name, "Table")

    def test_does_not_start_child_run_without_preceding_checkbox_row(self):
        rows = transform_rows(
            [
                row(paragraph("◻ Parent")),
                row(paragraph("Supporting explanation")),
                row(paragraph("◻ Isolated indented row", indent="720")),
                row(paragraph("◻ Same-level continuation", indent="720")),
            ]
        )

        self.assertEqual(first_paragraph(rows[2]).style_name, "Table")
        self.assertEqual(first_paragraph(rows[3]).style_name, "Table")

    def test_only_considers_first_column(self):
        second_column_checkbox = paragraph("◻ Second-column item", indent="720")
        rows = transform_rows(
            [
                row(paragraph("◻ Parent")),
                documents.table_row(
                    [
                        documents.table_cell([paragraph("Ordinary first column")]),
                        documents.table_cell([second_column_checkbox]),
                    ]
                ),
            ]
        )

        self.assertEqual(first_paragraph(rows[1], column=1).style_name, "Table")

    def test_leaves_indented_checkbox_outside_table_unchanged(self):
        source_paragraph = paragraph("◻ Outside table", indent="720")
        transformed = transform_word_document(documents.document([source_paragraph]))

        self.assertEqual(transformed.children[0].style_name, "Table")

    def test_preserves_non_row_table_children(self):
        bookmark = documents.bookmark("_Application_Checklist")
        transformed_rows = transform_rows(
            [
                bookmark,
                row(paragraph("◻ Parent")),
                row(paragraph("◻ Child", indent="720")),
            ]
        )

        self.assertIsInstance(transformed_rows[0], documents.Bookmark)
        self.assertEqual(transformed_rows[0].name, "_Application_Checklist")
