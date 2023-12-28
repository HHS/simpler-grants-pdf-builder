from bs4 import BeautifulSoup
from freezegun import freeze_time


from django.test import TestCase


from .nofo import (
    add_caption_to_table,
    add_class_to_table,
    add_headings_to_nofo,
    add_newline_to_ref_numbers,
    create_nofo,
    overwrite_nofo,
    convert_table_first_row_to_header_row,
    get_sections_from_soup,
    get_subsections_from_sections,
    suggest_nofo_opportunity_number,
    suggest_nofo_tagline,
    suggest_nofo_theme,
    suggest_nofo_title,
)
from .utils import match_view_url


class MatchUrlTests(TestCase):
    def test_match_valid_urls(self):
        """
        Test the match_url function with valid URLs.
        """
        self.assertTrue(match_view_url("/nofos/123"))
        self.assertTrue(match_view_url("/nofos/1"))
        self.assertTrue(match_view_url("/nofos/0"))

    def test_match_invalid_urls(self):
        """
        Test the match_url function with invalid URLs.
        """
        self.assertFalse(match_view_url("/nofos"))
        self.assertFalse(match_view_url("/nofos/"))
        self.assertFalse(match_view_url("/nofos/abc"))
        self.assertFalse(match_view_url("/nofos/123/456"))
        self.assertFalse(match_view_url("/nofos/1/2"))


class HTMLTableTests(TestCase):
    def setUp(self):
        self.caption_text = "Physician Assistant Training Chart"
        self.html_filename = "nofos/fixtures/html/table.html"
        self.soup = BeautifulSoup(open(self.html_filename), "html.parser")

    def test_table_before_convert_table_first_row_to_header_row(self):
        table = self.soup.find("table")

        # Confirm no header cells
        header_cells = table.find_all("th")
        self.assertEqual(len(header_cells), 0)

        # Count the rows
        rows = table.find_all("tr")
        self.assertEqual(len(rows), 6)

        # Count the columns
        first_row = rows[0]
        columns = first_row.find_all("td")
        self.assertEqual(len(columns), 4)

        # Find the first cell and check its content
        first_cell = first_row.find("td")
        self.assertIn("Year", first_cell.text.strip())

    def test_table_after_convert_table_first_row_to_header_row(self):
        table = self.soup.find("table")
        # Convert first row of tds to ths
        convert_table_first_row_to_header_row(table)

        # Confirm no header cells
        header_cells = table.find_all("th")
        self.assertEqual(len(header_cells), 4)

        # Count the rows
        rows = table.find_all("tr")
        self.assertEqual(len(rows), 6)

        # Count the columns
        first_row = rows[0]
        columns = first_row.find_all("th")
        self.assertEqual(len(columns), 4)

        # Find the first cell and check its content
        first_cell = first_row.find("th")
        self.assertIn("Year", first_cell.text.strip())

    def test_table_before_add_caption_to_table(self):
        table = self.soup.find("table")

        # table doesn't have a caption
        self.assertIsNone(table.find("caption"))

        # there is a paragraph tag with the caption
        paragraph = self.soup.find("p", string=self.caption_text)
        self.assertIsNotNone(paragraph)

        # the paragraph tag has a span inside of it
        self.assertIsNotNone(paragraph.find("span"))

    def test_table_after_add_caption_to_table(self):
        table = self.soup.find("table")
        add_caption_to_table(table)

        # no paragraph tag with the caption
        paragraph = self.soup.find("p", string=self.caption_text)
        self.assertIsNone(paragraph)

        # table DOES have a caption
        caption = table.find("caption", string=self.caption_text)
        self.assertIsNotNone(caption)

        # the caption tag has a span inside of it
        self.assertIsNotNone(caption.find("span"))


class HTMLTableClassTests(TestCase):
    def _generate_cols(self, num_cols, cell="td"):
        cols = ""
        for i in range(num_cols):
            cols += "<{0}>Col {1}</{0}>".format(cell, i + 1)

        return cols

    def test_table_class_sm(self):
        table_html = "<table><tr>{}</tr></table>".format(self._generate_cols(2))
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--small")

    def test_table_class_md(self):
        table_html = "<table><tr>{}</tr></table>".format(self._generate_cols(4))
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--medium")

    def test_table_class_lg(self):
        table_html = "<table><tr>{}</tr></table>".format(self._generate_cols(5))
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--large")

    def test_table_class_lg_with_th(self):
        table_html = "<table><tr>{}</tr></table>".format(
            self._generate_cols(10, cell="th")
        )
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--large")

    def test_table_class_lg_with_th_2_rows(self):
        # generate a table with 2 rows
        table_html = "<table><tr>{}</tr><tr>{}</tr></table>".format(
            self._generate_cols(10, cell="th"), self._generate_cols(10)
        )
        soup = BeautifulSoup(table_html, "html.parser")

        self.assertEqual(add_class_to_table(soup.find("table")), "table--large")


class AddNewLineToRefsTest(TestCase):
    def test_ref_0(self):
        self.assertEqual(add_newline_to_ref_numbers("ref0)"), "ref0)\n")

    def test_ref_1(self):
        self.assertEqual(add_newline_to_ref_numbers("ref1)"), "ref1)\n")

    def test_ref_5(self):
        self.assertEqual(add_newline_to_ref_numbers("ref5)"), "ref5)\n")

    def test_ref_10(self):
        self.assertEqual(add_newline_to_ref_numbers("ref10)"), "ref10)\n")


class HTMLSuggestTitleTests(TestCase):
    def setUp(self):
        self.nofo_title = "Primary Care Training and Enhancement: Physician Assistant Rural Training in Mental and Behavioral Health (PCTE-PARM) Program"
        self.html_filename = "nofos/fixtures/html/nofo.html"
        self.soup = BeautifulSoup(open(self.html_filename), "html.parser")

    def test_suggest_nofo_title_returns_correct_title(self):
        self.assertEqual(suggest_nofo_title(self.soup), self.nofo_title)

    @freeze_time("1917-04-17")
    def test_suggest_nofo_title_returns_default_title_for_bad_html(self):
        default_name = "NOFO: 1917-04-17 00:00:00"
        self.assertEqual(
            suggest_nofo_title(
                BeautifulSoup(
                    "<html><title>THESES</title><body><h1>THESES</h1></body></html>",
                    "html.parser",
                )
            ),
            default_name,
        )


class HTMLSuggestNumberTests(TestCase):
    def setUp(self):
        self.nofo_opportunity_number = "HRSA-24-019"
        self.html_filename = "nofos/fixtures/html/nofo.html"
        self.soup = BeautifulSoup(open(self.html_filename), "html.parser")

    def test_suggest_nofo_title_returns_correct_title(self):
        self.assertEqual(
            suggest_nofo_opportunity_number(self.soup), self.nofo_opportunity_number
        )

    def test_suggest_nofo_number_returns_default_number_for_bad_html(self):
        default_number = "NOFO #1"
        self.assertEqual(
            suggest_nofo_opportunity_number(
                BeautifulSoup(
                    "<html><title>THESES</title><body><h1>THESES</h1></body></html>",
                    "html.parser",
                )
            ),
            default_number,
        )


class HTMLSuggestTagline(TestCase):
    def test_heading_with_valid_previous_sibling(self):
        html_content = "<p>Valid tagline</p><h2>Summary</h2>"
        soup = BeautifulSoup(html_content, "html.parser")
        result = suggest_nofo_tagline(soup)
        self.assertEqual(result, "Valid tagline")

    def test_heading_with_invalid_previous_sibling(self):
        html_content = "<p>Invalid: contains a colon</p><h2>Summary</h2>"
        soup = BeautifulSoup(html_content, "html.parser")
        result = suggest_nofo_tagline(soup)
        self.assertEqual(result, "")

    def test_no_summary_heading(self):
        html_content = "<p>Some text</p><h2>Other Heading</h2>"
        soup = BeautifulSoup(html_content, "html.parser")
        result = suggest_nofo_tagline(soup)
        self.assertEqual(result, "")

    def test_heading_with_non_paragraph_previous_sibling(self):
        html_content = "<div>Not a paragraph</div><h2>Summary</h2>"
        soup = BeautifulSoup(html_content, "html.parser")
        result = suggest_nofo_tagline(soup)
        self.assertEqual(result, "")

    def test_tagline_not_followed_by_a_heading(self):
        html_content = "<p>Not followed by a heading</p><p>Summary</p>"
        soup = BeautifulSoup(html_content, "html.parser")
        result = suggest_nofo_tagline(soup)
        self.assertEqual(result, "")


class HTMLSuggestThemeTests(TestCase):
    def test_suggest_nofo_number_returns_hrsa_theme(self):
        nofo_number = "HRSA-24-019"
        nofo_theme = "portrait-hrsa-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_returns_cdc_theme(self):
        nofo_number = "CDC-RFA-DP-24-0139"
        nofo_theme = "landscape-cdc-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_no_match_returns_hrsa_theme(self):
        nofo_number = "abc-def-ghi"
        nofo_theme = "portrait-hrsa-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_empty_returns_hrsa_theme(self):
        nofo_number = ""
        nofo_theme = "portrait-hrsa-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)


class HTMLSectionTests(TestCase):
    def test_get_sections_from_soup(self):
        soup = BeautifulSoup("<h1>Section 1</h1><p>Section 1 body</p>", "html.parser")
        sections = get_sections_from_soup(soup)
        self.assertEqual(len(sections), 1)

        section = sections[0]
        self.assertEqual(section.get("name"), "Section 1")
        self.assertEqual(section.get("html_id"), "")
        self.assertEqual(section.get("order"), 1)
        self.assertEqual(str(section.get("body")[0]), "<p>Section 1 body</p>")

    def test_get_sections_from_soup_length_zero(self):
        soup = BeautifulSoup("<p>Section 1 body</p>", "html.parser")
        sections = get_sections_from_soup(soup)
        self.assertEqual(sections, [])

    def test_get_sections_from_soup_length_two(self):
        soup = BeautifulSoup("<h1>Section 1</h1><h1>Section 2</h1>", "html.parser")
        sections = get_sections_from_soup(soup)
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0].get("order"), 1)
        self.assertEqual(sections[1].get("order"), 2)

    def test_get_sections_from_soup_with_html_id(self):
        soup = BeautifulSoup(
            '<h1 id="section-1">Section 1</h1><p>Section 1 body</p>', "html.parser"
        )
        sections = get_sections_from_soup(soup)
        self.assertEqual(sections[0].get("html_id"), "section-1")

    def test_get_sections_from_soup_no_body(self):
        soup = BeautifulSoup("<h1>Section 1</h1>", "html.parser")
        sections = get_sections_from_soup(soup)
        self.assertEqual(sections[0].get("body"), [])


class HTMLSubsectionTests(TestCase):
    def test_get_subsections_from_soup(self):
        soup = BeautifulSoup(
            "<h1>Section 1</h1><h2>Subsection 1</h2><p>Section 1 body</p>",
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        # 1 section
        self.assertEqual(len(sections), 1)

        # assert section values
        section = sections[0]
        self.assertEqual(section.get("name"), "Section 1")
        self.assertEqual(section.get("html_id"), "")
        self.assertEqual(section.get("order"), 1)

        # 1 subsection
        self.assertEqual(len(section.get("subsections")), 1)
        subsection = section.get("subsections")[0]

        # assert subsection values
        self.assertEqual(subsection.get("name"), "Subsection 1")
        self.assertEqual(subsection.get("html_id"), "")
        self.assertEqual(subsection.get("order"), 1)
        self.assertEqual(str(subsection.get("body")[0]), "<p>Section 1 body</p>")

    def test_get_subsections_from_soup_section_body_disappears(self):
        soup = BeautifulSoup(
            "<h1>Section 1</h1><h2>Subsection 1</h2><p>Section 1 body</p>",
            "html.parser",
        )
        sections = get_sections_from_soup(soup)
        self.assertEqual(
            [str(tag) for tag in sections[0].get("body")],
            ["<h2>Subsection 1</h2>", "<p>Section 1 body</p>"],
        )

        # body is gone after get_sections_from_soup
        sections = get_subsections_from_sections(sections)
        self.assertIsNone(sections[0].get("body", None))

    def test_get_subsections_from_soup_section_html_id(self):
        soup = BeautifulSoup(
            '<h1>Section 1</h1><h2 id="subsection-1">Subsection 1</h2><p>Section 1 body</p>',
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        subsection = sections[0].get("subsections")[0]
        self.assertEqual(subsection.get("html_id"), "subsection-1")

    def test_get_subsections_from_soup_section_heading_demoted(self):
        soup = BeautifulSoup(
            '<h1>Section 1</h1><h2 id="subsection-1">Subsection 1</h2><p>Section 1 body</p>',
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        subsection = sections[0].get("subsections")[0]
        self.assertEqual(subsection.get("tag"), "h3")

    def test_get_subsections_from_soup_nested_heading_not_a_section(self):
        soup = BeautifulSoup(
            '<h1>Section 1</h1><h2 id="subsection-1">Subsection 1</h2><p>Section 1 body</p><div><h2>Not a subsection</h2>',
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        subsections = sections[0].get("subsections")
        self.assertEqual(len(subsections), 1)

    def test_get_subsections_from_soup_no_body(self):
        soup = BeautifulSoup(
            '<h1>Section 1</h1><h2 id="subsection-1">Subsection 1</h2>',
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        subsection = sections[0].get("subsections")[0]
        self.assertEqual(subsection.get("body"), [])

    def test_get_subsections_from_soup_lost_paragraph_before_heading(self):
        soup = BeautifulSoup(
            "<h1>Section 1</h1><p>This paragraph disappears</p><h2>Subsection 1</h2><p>Section 1 body</p>",
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        subsection = sections[0].get("subsections")[0]
        self.assertEqual(str(subsection.get("body")[0]), "<p>Section 1 body</p>")

    def test_get_subsections_from_soup_two_subsections(self):
        soup = BeautifulSoup(
            '<h1>Section 1</h1><h2>Subsection 1</h2><p>Section 1 body</p><h3 id="subsection-2">Subsection 2</h3><p>Section 1 body continued</p>',
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        subsections = sections[0].get("subsections")
        self.assertEqual(len(subsections), 2)

        subsection_one = subsections[0]
        self.assertEqual(subsection_one.get("name"), "Subsection 1")
        self.assertEqual(subsection_one.get("html_id"), "")
        self.assertEqual(subsection_one.get("order"), 1)
        self.assertEqual(str(subsection_one.get("body")[0]), "<p>Section 1 body</p>")

        subsection_two = subsections[1]
        self.assertEqual(subsection_two.get("name"), "Subsection 2")
        self.assertEqual(subsection_two.get("html_id"), "subsection-2")
        self.assertEqual(subsection_two.get("tag"), "h4")
        self.assertEqual(subsection_two.get("order"), 2)
        self.assertEqual(
            str(subsection_two.get("body")[0]), "<p>Section 1 body continued</p>"
        )


class HTMLNofoFileTests(TestCase):
    def setUp(self):
        self.html_filename = "nofos/fixtures/html/nofo.html"
        self.soup = BeautifulSoup(open(self.html_filename), "html.parser")

    def test_get_sections_from_soup_html_file(self):
        sections = get_sections_from_soup(self.soup)
        self.assertEqual(len(sections), 7)

        section = sections[0]
        self.assertEqual(section.get("name"), "Step 1: Review the Opportunity")
        self.assertEqual(section.get("html_id"), "")
        self.assertEqual(section.get("order"), 1)
        self.assertIsNotNone(section.get("body", None))

    def test_get_subsections_from_soup_html_file(self):
        sections = get_subsections_from_sections(get_sections_from_soup(self.soup))
        self.assertEqual(len(sections), 7)

        section_info = [
            {
                "name": "Step 1: Review the Opportunity",
                "subsections_len": 24,
                "subsections_first_title": "Basic Information",
            },
            {
                "name": "Step 2: Get Ready to Apply",
                "subsections_len": 6,
                "subsections_first_title": "Get Registered",
            },
            {
                "name": "Step 3: Write Your Application",
                "subsections_len": 32,
                "subsections_first_title": "Application Contents & Format",
            },
            {
                "name": "Step 4: Learn About Review & Award",
                "subsections_len": 13,
                "subsections_first_title": "Application Review",
            },
            {
                "name": "Step 5: Submit Your Application",
                "subsections_len": 8,
                "subsections_first_title": "Application Submission & Deadlines",
            },
            {
                "name": "Learn What Happens After Award",
                "subsections_len": 4,
                "subsections_first_title": "Post-Award Requirements & Administration",
            },
            {
                "name": "Contacts & Support",
                "subsections_len": 8,
                "subsections_first_title": "Agency Contacts",
            },
        ]

        for index, section in enumerate(sections):
            self.assertEqual(section.get("name"), section_info[index].get("name"))
            self.assertEqual(
                len(section.get("subsections")),
                section_info[index].get("subsections_len"),
            )
            self.assertEqual(
                section.get("subsections")[0].get("name"),
                section_info[index].get("subsections_first_title"),
            )


def _get_sections_dict():
    return [
        {
            "name": "Section 1",
            "order": 1,
            "html_id": "",
            "subsections": [
                {
                    "name": "Subsection 1",
                    "order": 1,
                    "tag": "h3",
                    "html_id": "",
                    "body": ["<p>Section 1 body</p>"],
                },
                {
                    "name": "Subsection 2",
                    "order": 2,
                    "tag": "h4",
                    "html_id": "subsection-2",
                    "body": ["<p>Section 1 body continued</p>"],
                },
            ],
        }
    ]


class CreateNOFOTests(TestCase):
    def setUp(self):
        self.sections = _get_sections_dict()

    def test_create_nofo_success(self):
        """
        Test creating a nofo object successfully
        """
        nofo = create_nofo("Test Nofo", self.sections)
        self.assertEqual(nofo.title, "Test Nofo")
        self.assertEqual(nofo.number, "NOFO #999")
        self.assertEqual(nofo.theme, "portrait-hrsa-blue")
        self.assertEqual(len(nofo.sections.all()), 1)
        self.assertEqual(len(nofo.sections.first().subsections.all()), 2)

    def test_create_nofo_success_duplicate_nofos(self):
        """
        Test creating two duplicate nofo objects successfully
        """
        nofo = create_nofo("Test Nofo", self.sections)
        nofo2 = create_nofo("Test Nofo", self.sections)
        self.assertEqual(nofo.title, nofo2.title)
        self.assertEqual(nofo.number, nofo2.number)
        self.assertEqual(len(nofo.sections.all()), len(nofo2.sections.all()))
        self.assertEqual(
            len(nofo.sections.first().subsections.all()),
            len(nofo2.sections.first().subsections.all()),
        )

    def test_create_nofo_success_no_sections(self):
        """
        Test with empty nofo sections
        """
        nofo = create_nofo("Test Nofo", [])
        self.assertEqual(nofo.title, "Test Nofo")
        self.assertEqual(len(nofo.sections.all()), 0)

    def test_create_nofo_success_no_title(self):
        """
        Test with empty nofo title and empty sections
        """
        nofo = create_nofo("", [])
        self.assertEqual(nofo.title, "")
        self.assertEqual(len(nofo.sections.all()), 0)


class OverwriteNOFOTests(TestCase):
    def setUp(self):
        self.sections = _get_sections_dict()

        self.new_sections = [
            {
                "name": "New Section 100",
                "order": 1,
                "html_id": "",
                "subsections": [
                    {
                        "name": "New Subsection 100",
                        "order": 1,
                        "tag": "h3",
                        "html_id": "",
                        "body": ["<p>New Section 100 body</p>"],
                    }
                ],
            }
        ]

    def test_overwrite_nofo_success(self):
        """
        Test overwriting a nofo object successfully
        """
        nofo = create_nofo("Test Nofo", self.sections)
        self.assertEqual(nofo.title, "Test Nofo")
        self.assertEqual(nofo.number, "NOFO #999")
        self.assertEqual(nofo.sections.first().name, "Section 1")
        self.assertEqual(len(nofo.sections.first().subsections.all()), 2)
        self.assertEqual(nofo.sections.first().subsections.first().name, "Subsection 1")

        nofo = overwrite_nofo(nofo, self.new_sections)
        self.assertEqual(nofo.title, "Test Nofo")  # same name
        self.assertEqual(nofo.number, "NOFO #999")  # same number
        self.assertEqual(nofo.sections.first().name, "New Section 100")
        self.assertEqual(
            len(nofo.sections.first().subsections.all()), 1
        )  # only 1 subsection
        self.assertEqual(
            nofo.sections.first().subsections.first().name, "New Subsection 100"
        )

    def test_overwrite_nofo_success_empty_sections(self):
        """
        Test overwriting a nofo with empty sections also succeeds
        """
        nofo = create_nofo("Test Nofo", self.sections)
        self.assertEqual(nofo.title, "Test Nofo")
        self.assertEqual(nofo.number, "NOFO #999")
        self.assertEqual(nofo.sections.first().name, "Section 1")
        self.assertEqual(len(nofo.sections.first().subsections.all()), 2)
        self.assertEqual(nofo.sections.first().subsections.first().name, "Subsection 1")

        nofo = overwrite_nofo(nofo, [])
        self.assertEqual(nofo.title, "Test Nofo")  # same name
        self.assertEqual(nofo.number, "NOFO #999")  # same number
        self.assertEqual(len(nofo.sections.all()), 0)  # empty sections


class AddHeadingsTests(TestCase):
    def setUp(self):
        self.sections = _get_sections_dict()
        self.sections_with_link = [
            {
                "name": "Section 1",
                "order": 1,
                "html_id": "",
                "subsections": [
                    {
                        "name": "Subsection 1",
                        "order": 1,
                        "tag": "h3",
                        "html_id": "custom-link",
                        "body": [
                            '<p>Section 1 body with <a href="#custom-link">custom link</a>.</p>'
                        ],
                    }
                ],
            }
        ]

    def test_add_headings_success(self):
        nofo = create_nofo("Test Nofo", self.sections)
        self.assertEqual(nofo.title, "Test Nofo")

        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]
        subsection_2 = nofo.sections.first().subsections.all()[1]

        # check section heading has no id
        self.assertEqual(section.html_id, "")
        # check first subsection heading has no html_id
        self.assertEqual(subsection_1.html_id, "")
        # check second subsection heading has html_id
        self.assertEqual(subsection_2.html_id, "subsection-2")

        ################
        # ADD HEADINGS
        ################
        nofo = add_headings_to_nofo(nofo)
        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]
        subsection_2 = nofo.sections.first().subsections.all()[1]

        # check section heading has new html_id
        self.assertEqual(section.html_id, "section-1")
        # check subsection headings have new html_id
        self.assertEqual(subsection_1.html_id, "section-1--subsection-1")
        self.assertEqual(subsection_2.html_id, "section-1--subsection-2")

    def test_add_headings_success_replace_link(self):
        nofo = create_nofo("Test Nofo 2", self.sections_with_link)
        self.assertEqual(nofo.title, "Test Nofo 2")

        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]

        # check section heading has no id
        self.assertEqual(section.html_id, "")
        # check subsection heading has html_id
        self.assertEqual(subsection_1.html_id, "custom-link")
        # check the body of subsection includes link
        self.assertIn(
            "Section 1 body with [custom link](#custom-link)", subsection_1.body
        )

        ################
        # ADD HEADINGS
        ################
        nofo = add_headings_to_nofo(nofo)
        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]

        # check section heading has new html_id
        self.assertEqual(section.html_id, "section-1")
        # check subsection heading has new html_id
        self.assertEqual(subsection_1.html_id, "section-1--subsection-1")
        # check the body of subsection link is updated to new id
        self.assertIn(
            "Section 1 body with [custom link](#section-1--subsection-1)",
            subsection_1.body,
        )
