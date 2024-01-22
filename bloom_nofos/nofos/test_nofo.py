from bs4 import BeautifulSoup
from django.test import TestCase
from freezegun import freeze_time

from .nofo import (
    add_headings_to_nofo,
    add_newline_to_ref_numbers,
    convert_table_first_row_to_header_row,
    create_nofo,
    get_sections_from_soup,
    get_subsections_from_sections,
    join_nested_lists,
    overwrite_nofo,
    suggest_nofo_agency,
    suggest_nofo_opdiv,
    suggest_nofo_opportunity_number,
    suggest_nofo_subagency,
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


class TableConvertFirstRowToHeaderRowTests(TestCase):
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


class AddNewLineToRefsTest(TestCase):
    def test_ref_0(self):
        self.assertEqual(add_newline_to_ref_numbers("ref0)"), "ref0)\n")

    def test_ref_1(self):
        self.assertEqual(add_newline_to_ref_numbers("ref1)"), "ref1)\n")

    def test_ref_5(self):
        self.assertEqual(add_newline_to_ref_numbers("ref5)"), "ref5)\n")

    def test_ref_10(self):
        self.assertEqual(add_newline_to_ref_numbers("ref10)"), "ref10)\n")


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

    def test_get_subsections_from_soup_section_heading_h6(self):
        soup = BeautifulSoup(
            '<h1>Section 1</h1><h6 id="subsection-1">Subsection 1</h6><p>Section 1 body</p>',
            "html.parser",
        )
        sections = get_subsections_from_sections(get_sections_from_soup(soup))
        subsection = sections[0].get("subsections")[0]
        self.assertEqual(subsection.get("tag"), "h7")


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
                    },
                    {
                        "name": "Subsection 2",
                        "order": 2,
                        "tag": "h4",
                        "html_id": "h.haapch",
                        "body": [
                            '<p>Section 2 body with 2 <a href="#custom-link">custom</a> <a href="#h.haapch">links</a></a>.</p>'
                        ],
                    },
                ],
            }
        ]

        self.sections_with_really_long_subsection_title = [
            {
                "name": "Program description",
                "order": 1,
                "html_id": "",
                "subsections": [
                    {
                        "name": "This opportunity provides financial and technical aid to help communities monitor behavioral risk factors and chronic health conditions among adults in the United States and territories.",
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
        self.assertEqual(subsection_1.html_id, "1--section-1--subsection-1")
        self.assertEqual(subsection_2.html_id, "2--section-1--subsection-2")

    def test_add_headings_success_replace_link(self):
        nofo = create_nofo("Test Nofo 2", self.sections_with_link)
        self.assertEqual(nofo.title, "Test Nofo 2")

        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]
        subsection_2 = nofo.sections.first().subsections.all()[1]

        # check section 1 heading has no id
        self.assertEqual(section.html_id, "")
        # check subsection 1 heading has html_id
        self.assertEqual(subsection_1.html_id, "custom-link")
        # check the body of subsection 1 includes link
        self.assertIn(
            "Section 1 body with [custom link](#custom-link)", subsection_1.body
        )
        # check subsection 2 heading has html_id
        self.assertEqual(subsection_2.html_id, "h.haapch")
        # check the body of subsection 2 includes links
        self.assertIn(
            "Section 2 body with 2 [custom](#custom-link) [links](#h.haapch).",
            subsection_2.body,
        )

        ################
        # ADD HEADINGS
        ################
        nofo = add_headings_to_nofo(nofo)
        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]
        subsection_2 = nofo.sections.first().subsections.all()[1]

        # check section heading has new html_id
        self.assertEqual(section.html_id, "section-1")
        # check subsection1 heading has new html_id
        self.assertEqual(subsection_1.html_id, "1--section-1--subsection-1")
        # check the body of subsection 1 link is updated to new id
        self.assertIn(
            "Section 1 body with [custom link](#1--section-1--subsection-1)",
            subsection_1.body,
        )
        # check subsection 2 heading has new html_id
        self.assertEqual(subsection_2.html_id, "2--section-1--subsection-2")
        # check the body of subsection link is updated to new id
        self.assertIn(
            "Section 2 body with 2 [custom](#1--section-1--subsection-1) [links](#2--section-1--subsection-2).",
            subsection_2.body,
        )

    def test_add_headings_with_really_long_title_replace_link(self):
        nofo = create_nofo(
            "Test Nofo 2", self.sections_with_really_long_subsection_title
        )
        self.assertEqual(nofo.title, "Test Nofo 2")

        section = nofo.sections.first()
        subsection_1 = nofo.sections.first().subsections.all()[0]

        # check section 1 heading has no id
        self.assertEqual(section.html_id, "")
        # check subsection 1 heading has html_id
        self.assertEqual(subsection_1.html_id, "custom-link")
        # check the body of subsection 1 includes link
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
        self.assertEqual(section.html_id, "program-description")
        # check subsection1 heading has new html_id
        self.assertEqual(
            subsection_1.html_id,
            "1--program-description--this-opportunity-provides-financial-and-technical-aid-to-help-communities-monitor-behavioral-risk-factors-and-chronic-health-conditions-among-adults-in-the-united-states-and-territories",
        )
        # check the body of subsection 1 link is updated to new id
        self.assertIn(
            "Section 1 body with [custom link](#1--program-description--this-opportunity-provides-financial-and-technical-aid-to-help-communities-monitor-behavioral-risk-factors-and-chronic-health-conditions-among-adults-in-the-united-states-and-territories)",
            subsection_1.body,
        )


#########################################################
#################### SUGGEST X TESTS ####################
#########################################################


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

    def test_suggest_nofo_title_returns_default_title_for_p_span(self):
        name = "Primary Care Training and Enhancement: Physician Assistant Rural Training in Mental and Behavioral Health (PCTE-PARM) Program"
        self.assertEqual(
            suggest_nofo_title(
                BeautifulSoup(
                    '<html><title>THESES</title><body><h1>THESES</h1><p class="c0"><span>Opportunity Name: Primary Care Training and Enhancement: Physician Assistant Rural Training in Mental and Behavioral Health (PCTE-PARM) Program</span></p></body></html>',
                    "html.parser",
                )
            ),
            name,
        )

    def test_suggest_nofo_title_returns_default_title_for_p_span_span(self):
        name = "Improving Adolescent Health and Well-Being Through School-Based Surveillance and the What Works in Schools Program"
        self.assertEqual(
            suggest_nofo_title(
                BeautifulSoup(
                    '<html><title>THESES</title><body><h1>THESES</h1><p class="c0"><span class="c24">Opportunity Name: </span><span class="c1">Improving Adolescent Health and Well-Being Through School-Based Surveillance and the What Works in Schools Program</span></p></body></html>',
                    "html.parser",
                )
            ),
            name,
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

    def test_suggest_nofo_number_returns_default_title_for_p_span(self):
        name = "HRSA-24-019"
        self.assertEqual(
            suggest_nofo_opportunity_number(
                BeautifulSoup(
                    '<html><title>THESES</title><body><h1>THESES</h1><p class="c0"><span class="c3">Opportunity Number: HRSA-24-019</span></p></body></html>',
                    "html.parser",
                )
            ),
            name,
        )

    def test_suggest_nofo_number_returns_default_title_for_p_span_span(self):
        name = "CDC-RFA-DP-24-0139"
        self.assertEqual(
            suggest_nofo_opportunity_number(
                BeautifulSoup(
                    '<html><title>THESES</title><body><h1>THESES</h1><p class="c0"><span class="c180">Opportunity Number: </span><span class="c7">CDC-RFA-DP-24-0139</span><span class="c53 c7 c192">&nbsp;</span></p></body></html>',
                    "html.parser",
                )
            ),
            name,
        )


class HTMLSuggestThemeTests(TestCase):
    def test_suggest_nofo_number_hrsa_returns_hrsa_theme(self):
        nofo_number = "HRSA-24-019"
        nofo_theme = "portrait-hrsa-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_cdc_returns_cdc_theme(self):
        nofo_number = "CDC-RFA-DP-24-0139"
        nofo_theme = "landscape-cdc-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_acf_returns_acf_theme(self):
        nofo_number = "HHS-2024-ACF-ANA-NB-0050"
        nofo_theme = "portrait-acf-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_acl_returns_hrsa_theme(self):
        nofo_number = "HHS-2024-ACL-NIDILRR-REGE-0078"
        nofo_theme = "portrait-hrsa-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_no_match_returns_hrsa_theme(self):
        nofo_number = "abc-def-ghi"
        nofo_theme = "portrait-hrsa-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)

    def test_suggest_nofo_number_empty_returns_hrsa_theme(self):
        nofo_number = ""
        nofo_theme = "portrait-hrsa-blue"
        self.assertEqual(suggest_nofo_theme(nofo_number), nofo_theme)


class SuggestNofoOpDivTests(TestCase):
    def test_opdiv_present_in_paragraph(self):
        html = "<div><p>Opdiv: Center for Awesome NOFOs</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_opdiv(soup), "Center for Awesome NOFOs")

    def test_opdiv_present_not_in_paragraph(self):
        html = "<div><span>Opdiv: Center for Awesome NOFOs</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_opdiv(soup), "Center for Awesome NOFOs")

    def test_opdiv_not_present(self):
        html = "<div><p>Center for Awesome NOFOs</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_opdiv(soup), "")

    def test_opdiv_present_but_no_parent_paragraph(self):
        html = "<div>Opdiv: Center for Awesome NOFOs</div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_opdiv(soup), "Center for Awesome NOFOs")

    def test_opdiv_present_weird_casing(self):
        html = "<div><p><span>OPdiV: </span><span>Center for </span><span>Awesome NOFOs</span></p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_opdiv(soup), "Center for Awesome NOFOs")

    def test_opdiv_present_broken_up_by_spans(self):
        html = "<div><p><span>Opdiv: </span><span>Center for </span><span>Awesome NOFOs</span></p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_opdiv(soup), "Center for Awesome NOFOs")


class SuggestNofoAgencyTests(TestCase):
    def test_agency_present_in_paragraph(self):
        html = "<div><p>Agency: Agency for Weird Tables</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_agency(soup), "Agency for Weird Tables")

    def test_agency_present_not_in_paragraph(self):
        html = "<div><span>Agency: Agency for Weird Tables</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_agency(soup), "Agency for Weird Tables")

    def test_agency_not_present(self):
        html = "<div><p>Agency for Weird Tables</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_agency(soup), "")

    def test_agency_present_but_no_parent_paragraph(self):
        html = "<div>Agency: Agency for Weird Tables</div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_agency(soup), "Agency for Weird Tables")

    def test_agency_present_broken_up_by_spans(self):
        html = "<div><p><span>Agency: </span><span>Agency for </span><span>Weird Tables</span></p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_agency(soup), "Agency for Weird Tables")


class SuggestNofoSubagencyTests(TestCase):
    def test_subagency_present_in_paragraph(self):
        html = "<div><p>Subagency: Subagency for Multiple Header Rows</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(
            suggest_nofo_subagency(soup), "Subagency for Multiple Header Rows"
        )

    def test_subagency_present_not_in_paragraph(self):
        html = "<div><span>Subagency: Subagency for Multiple Header Rows</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(
            suggest_nofo_subagency(soup), "Subagency for Multiple Header Rows"
        )

    def test_subagency_not_present(self):
        html = "<div><p>Subagency for Multiple Header Rows</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_subagency(soup), "")

    def test_subagency_present_but_no_parent_paragraph(self):
        html = "<div>Subagency: Subagency for Multiple Header Rows</div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(
            suggest_nofo_subagency(soup), "Subagency for Multiple Header Rows"
        )

    def test_subagency_present_broken_up_by_spans(self):
        html = "<div><p><span>Subagency: </span><span>Subagency for </span><span>Multiple Header Rows</span></p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(
            suggest_nofo_subagency(soup), "Subagency for Multiple Header Rows"
        )


class SuggestNofoTaglineTests(TestCase):
    def test_tagline_present_in_paragraph(self):
        html = "<div><p>Tagline: The best NOFO ever</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_tagline(soup), "The best NOFO ever")

    def test_tagline_present_not_in_paragraph(self):
        html = "<div><span>Tagline: The best NOFO ever</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_tagline(soup), "The best NOFO ever")

    def test_tagline_not_present(self):
        html = "<div><p>The best NOFO ever</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_tagline(soup), "")

    def test_tagline_present_but_no_parent_paragraph(self):
        html = "<div>Tagline: The best NOFO ever</div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_tagline(soup), "The best NOFO ever")

    def test_tagline_present_broken_up_by_spans(self):
        html = "<div><p><span>Tagline: </span><span>The best </span><span>NOFO ever</span></p></div>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(suggest_nofo_tagline(soup), "The best NOFO ever")


###########################################################
################### NESTED LIST TESTS #####################
###########################################################


class NestedListTests(TestCase):
    def setUp(self):
        self.html_single_list = """
            <h4 class="c1"><span class="c35">Funding strategy</span></h4>
            <p class="c9"><span class="c4">Funding may differ based on demonstration of need such as burden data, reach of proposed activities, and availability of funds.</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 1:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 35 organizations for Component 1.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 2:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 5 organizations for Component 2.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 3:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 50 states, 7 U.S. territories, and 2 tribal nations for Component 3. We will fund only one Component 3 application per state, territory, or tribal nation. </span></li>
            </ul>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_nested_list = """
            <h6 class="c27" id="h.3rdcrjn"><span class="c77 c54">Strategy 1A – Health education (HED)</span></h6>
            <p class="c9"><span class="c4">You will implement a technical assistance plan and provide professional development to support the delivery of quality health education through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HED1. Develop, implement, and review a technical assistance plan. Its goal is to support and improve teacher and school staff’s knowledge, comfort, and skills for delivering health education to students in secondary grades (6 to 12). This includes sexual and mental health education.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HED2. Each year, provide professional development for teachers and school staff delivering health education instructional programs to students in secondary grades (6 to 12). This includes sexual health and mental health education. Prioritize instructional competencies needed for culturally responsive and inclusive education.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HED3. Each year, implement a health education instructional program for students in grades K to 12. Health education instructional programs should: </span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0 start">
                <li class="c91 c80 li-bullet-0"><span class="c4">Align with a district or school scope and sequence</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Be culturally responsive, inclusive, developmentally appropriate, and focused on meeting the needs of students who have been marginalized, including students from racial and ethnic minority groups, students who identify as LGBTQ+, and students with intellectual and developmental disabilities</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Incorporate sexual and mental health content</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Prioritize skills to identify and access health services</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Assess student performance</span></li>
            </ul>
        """

        self.html_nested_list_followed_by_li = """
            <h6 class="c27" id="h.26in1rg"><span class="c77 c54">Strategy 1B – Health services (HS)</span></h6>
            <p class="c9"><span class="c4">You will assess district and school capacity and implement a plan to increase access to school- and community-based services through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HS1. Each year, assess district and school capacity, infrastructure, and partnerships. The assessment reviews the ability to implement activities that increase student access to youth-friendly and inclusive sexual, behavioral, and mental health services.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HS2. Build partnerships with health care providers. The goal is to support student access to youth-friendly and inclusive sexual, behavioral, and mental health services.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HS3. Provide annual professional development to help staff support student access to health services, specifically sexual, behavioral, and mental health services. Each year, you must provide professional development to both: </span></li>
            </ul>
            <ul class="c34 lst-kix_list_22-0 start">
                <li class="c9 c80 li-bullet-0"><span class="c4">Staff who provide health services, and </span></li>
                <li class="c9 c80 li-bullet-0"><span class="c4">Other school staff</span></li>
            </ul>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HS4. Implement or enhance school-based activities that increase access to services. The goal is to increase student access to youth-friendly and inclusive school- and community-based sexual, behavioral, and mental health services. Activities must include at least one of the following:</span></li>
            </ul>
        """

        self.html_2_nested_lists = """
            <h6 class="c27" id="h.26in1rg"><span class="c77 c54">Strategy 1B – Health services (HS)</span></h6>
            <p class="c9"><span class="c4">You will assess district and school capacity and implement a plan to increase access to school- and community-based services through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HS1. Each year, assess district and school capacity, infrastructure, and partnerships. The assessment reviews the ability to implement activities that increase student access to youth-friendly and inclusive sexual, behavioral, and mental health services.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HS2. Build partnerships with health care providers. The goal is to support student access to youth-friendly and inclusive sexual, behavioral, and mental health services.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HS3. Provide annual professional development to help staff support student access to health services, specifically sexual, behavioral, and mental health services. Each year, you must provide professional development to both: </span></li>
            </ul>
            <ul class="c34 lst-kix_list_22-0 start">
                <li class="c9 c80 li-bullet-0"><span class="c4">Staff who provide health services, and </span></li>
                <li class="c9 c80 li-bullet-0"><span class="c4">Other school staff</span></li>
            </ul>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HS4. Implement or enhance school-based activities that increase access to services. The goal is to increase student access to youth-friendly and inclusive school- and community-based sexual, behavioral, and mental health services. Activities must include at least one of the following:</span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0">
                <li class="c91 c80 li-bullet-0"><span class="c4">Create a referral system to link students to sexual, behavioral, and mental health services.</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Provide school-based sexual, behavioral, and mental health services to students. For example, STI screening, making condoms available, school-based counseling, and mental health supports.</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Provide school-based health center services that support sexual, behavioral, and mental health services for students.</span></li>
            </ul>
        """

        self.html_2_nested_lists_followed_by_li = """
            <h6 class="c27" id="h.26in1rg"><span class="c77 c54">Strategy 1B – Health services (HS)</span></h6>
            <p class="c9"><span class="c4">You will assess district and school capacity and implement a plan to increase access to school- and community-based services through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HS1. Each year, assess district and school capacity, infrastructure, and partnerships. The assessment reviews the ability to implement activities that increase student access to youth-friendly and inclusive sexual, behavioral, and mental health services.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HS2. Build partnerships with health care providers. The goal is to support student access to youth-friendly and inclusive sexual, behavioral, and mental health services.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">HS3. Provide annual professional development to help staff support student access to health services, specifically sexual, behavioral, and mental health services. Each year, you must provide professional development to both: </span></li>
            </ul>
            <ul class="c34 lst-kix_list_22-0 start">
                <li class="c9 c80 li-bullet-0"><span class="c4">Staff who provide health services, and </span></li>
                <li class="c9 c80 li-bullet-0"><span class="c4">Other school staff</span></li>
            </ul>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">HS4. Implement or enhance school-based activities that increase access to services. The goal is to increase student access to youth-friendly and inclusive school- and community-based sexual, behavioral, and mental health services. Activities must include at least one of the following:</span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0">
                <li class="c91 c80 li-bullet-0"><span class="c4">Create a referral system to link students to sexual, behavioral, and mental health services.</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Provide school-based sexual, behavioral, and mental health services to students. For example, STI screening, making condoms available, school-based counseling, and mental health supports.</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Provide school-based health center services that support sexual, behavioral, and mental health services for students.</span></li>
            </ul>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">Last bullet by itself</span></li>
            </ul>
        """

        self.html_double_nested_list = """
            <h6 class="c27"><span class="c77 c54">Strategy 1C – Safe and supportive environments (SSE)</span></h6>
            <p class="c9"><span class="c4">You will foster safe and supportive school environments and support the mental health and well-being of students and staff through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE2. Each year, provide professional development to school staff on fostering safe and supportive school environments. Professional development topics may include supporting youth with LGBTQ+ identities and racial and ethnic minority youth, classroom management, and mental health awareness and crisis response.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE3. Implement activities to support school staff’s mental health and well-being.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE4. Implement school-wide practices to support the behavioral and mental health and social and emotional well-being of students.</span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0">
                <li class="c91 c80 li-bullet-0"><span class="c4">Establish dedicated time within the school schedule for students to connect with teachers and peers. The goal is to hold structured discussions that promote social-emotional well-being and strengthen relationships. These might include advisory programs or periods and morning meetings.</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Implement schoolwide positive behavioral interventions and support for student and teacher well-being. This includes:</span></li>
            </ul>
            <ul class="c34 lst-kix_list_13-1 start">
                <li class="c91 c143 li-bullet-0"><span class="c4">Setting positive behavioral expectations for students</span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Teaching academic and social behaviors that students need to meet school expectations</span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Defining behaviors that negatively affect school environments </span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Using positive disciplinary practices to respond to negative behaviors</span></li>
            </ul>
        """

        self.html_double_nested_list_followed_by_li = """
            <h6 class="c27"><span class="c77 c54">Strategy 1C – Safe and supportive environments (SSE)</span></h6>
            <p class="c9"><span class="c4">You will foster safe and supportive school environments and support the mental health and well-being of students and staff through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE2. Each year, provide professional development to school staff on fostering safe and supportive school environments. Professional development topics may include supporting youth with LGBTQ+ identities and racial and ethnic minority youth, classroom management, and mental health awareness and crisis response.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE3. Implement activities to support school staff’s mental health and well-being.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE4. Implement school-wide practices to support the behavioral and mental health and social and emotional well-being of students.</span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0">
                <li class="c91 c80 li-bullet-0"><span class="c4">Establish dedicated time within the school schedule for students to connect with teachers and peers. The goal is to hold structured discussions that promote social-emotional well-being and strengthen relationships. These might include advisory programs or periods and morning meetings.</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">Implement schoolwide positive behavioral interventions and support for student and teacher well-being. This includes:</span></li>
            </ul>
            <ul class="c34 lst-kix_list_13-1 start">
                <li class="c91 c143 li-bullet-0"><span class="c4">Setting positive behavioral expectations for students</span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Teaching academic and social behaviors that students need to meet school expectations</span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Defining behaviors that negatively affect school environments </span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Using positive disciplinary practices to respond to negative behaviors</span></li>
            </ul>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE5. Implement positive youth development approaches. Specifically, provide school-based mentoring, service learning, or other positive youth development programs or connect students to community-based programs.</span></li>
            </ul>
        """

        self.html_2_lists_to_join = """
            <h4 class="c1"><span class="c35">Funding strategy</span></h4>
            <p class="c9"><span class="c4">Funding may differ based on demonstration of need such as burden data, reach of proposed activities, and availability of funds.</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 1:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 35 organizations for Component 1.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 2:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 5 organizations for Component 2.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 3:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 50 states, 7 U.S. territories, and 2 tribal nations for Component 3. We will fund only one Component 3 application per state, territory, or tribal nation. </span></li>
            </ul>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 4:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 35 organizations for Component 1.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 5:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 5 organizations for Component 2.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c77 c58 c96">Component 6:</span><span class="c4">&nbsp;If funding allows, we intend to fund up to 50 states, 7 U.S. territories, and 2 tribal nations for Component 3. We will fund only one Component 3 application per state, territory, or tribal nation. </span></li>
            </ul>
            <p class="c9"><span class="c4">Sidebar: To help you find what you need, this NOFO uses internal links. In Adobe Reader, you can go back to where you were by pressing Alt + Backspace. </span></p>
        """

        self.html_2_nested_lists_to_join = """
            <h6 class="c27"><span class="c77 c54">Strategy 1C – Safe and supportive environments (SSE)</span></h6>
            <p class="c9"><span class="c4">You will foster safe and supportive school environments and support the mental health and well-being of students and staff through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE2. Each year, provide professional development to school staff on fostering safe and supportive school environments. Professional development topics may include supporting youth with LGBTQ+ identities and racial and ethnic minority youth, classroom management, and mental health awareness and crisis response.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE3. Implement activities to support school staff’s mental health and well-being.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE4. Implement school-wide practices to support the behavioral and mental health and social and emotional well-being of students.</span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0">
                <li class="c91 c80 li-bullet-0"><span class="c4">1. Establish dedicated time within the school schedule for students to connect with teachers and peers. The goal is to hold structured discussions that promote social-emotional well-being and strengthen relationships. These might include advisory programs or periods and morning meetings.</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">2. Implement schoolwide positive behavioral interventions and support for student and teacher well-being. This includes:</span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0">
                <li class="c91 c143 li-bullet-0"><span class="c4">3. Setting positive behavioral expectations for students</span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">4. Teaching academic and social behaviors that students need to meet school expectations</span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">5. Defining behaviors that negatively affect school environments </span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">6. Using positive disciplinary practices to respond to negative behaviors</span></li>
            </ul>
        """

        self.html_2_nested_lists_to_join_after_double_nested_list = """
            <h6 class="c27"><span class="c77 c54">Strategy 1C – Safe and supportive environments (SSE)</span></h6>
            <p class="c9"><span class="c4">You will foster safe and supportive school environments and support the mental health and well-being of students and staff through the following activities:</span></p>
            <ul class="c34 lst-kix_list_25-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE2. Each year, provide professional development to school staff on fostering safe and supportive school environments. Professional development topics may include supporting youth with LGBTQ+ identities and racial and ethnic minority youth, classroom management, and mental health awareness and crisis response.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE3. Implement activities to support school staff’s mental health and well-being.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">SSE4. Implement school-wide practices to support the behavioral and mental health and social and emotional well-being of students.</span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0">
                <li class="c91 c80 li-bullet-0"><span class="c4">1. Establish dedicated time within the school schedule for students to connect with teachers and peers. The goal is to hold structured discussions that promote social-emotional well-being and strengthen relationships. These might include advisory programs or periods and morning meetings.</span></li>
                <li class="c91 c80 li-bullet-0"><span class="c4">2. Implement schoolwide positive behavioral interventions and support for student and teacher well-being. This includes:</span></li>
            </ul>
            <ul class="c34 lst-kix_list_13-1 start">
                <li class="c91 c143 li-bullet-0"><span class="c4">Setting positive behavioral expectations for students</span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Teaching academic and social behaviors that students need to meet school expectations</span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Defining behaviors that negatively affect school environments </span></li>
                <li class="c91 c143 li-bullet-0"><span class="c4">Using positive disciplinary practices to respond to negative behaviors</span></li>
            </ul>
            <ul class="c34 lst-kix_list_7-0">
                <li class="c9 c17 li-bullet-0"><span class="c4">3. Implement positive youth development approaches. Specifically, provide school-based mentoring, service learning, or other positive youth development programs or connect students to community-based programs.</span></li>
                <li class="c9 c17 li-bullet-0"><span class="c4">4. Implement positive youth development approaches. Specifically, provide school-based mentoring, service learning, or other positive youth development programs or connect students to community-based programs.</span></li>
            </ul>
        """

    def test_single_list_nothing_happens(self):
        soup = join_nested_lists(BeautifulSoup(self.html_single_list, "html.parser"))
        self.assertEqual(len(soup.select("ul")), 1)

        # last li of first list DOES NOT HAVE a nested ul
        last_li = soup.find("ul").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 0)

    def test_nested_list_becomes_nested(self):
        soup = join_nested_lists(BeautifulSoup(self.html_nested_list, "html.parser"))
        # two uls
        self.assertEqual(len(soup.select("ul")), 2)
        # one nested list
        self.assertEqual(len(soup.select("ul > li > ul")), 1)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # last li of first list HAS a nested ul
        last_li = soup.find("ul").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 1)

    def test_nested_list_becomes_nested_and_last_item_added_to_first_list(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_nested_list_followed_by_li, "html.parser")
        )

        # two uls
        self.assertEqual(len(soup.select("ul")), 2)
        # one nested list
        self.assertEqual(len(soup.select("ul > li > ul")), 1)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # first ul has 4 li children
        first_ul = soup.find("ul")
        self.assertEqual(len(first_ul.find_all("li", recursive=False)), 4)

    def test_2_nested_lists_become_nested(self):
        soup = join_nested_lists(BeautifulSoup(self.html_2_nested_lists, "html.parser"))
        # three uls
        self.assertEqual(len(soup.select("ul")), 3)
        # two nested lists
        self.assertEqual(len(soup.select("ul > li > ul")), 2)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # first ul has 4 li children
        first_ul = soup.find("ul")
        self.assertEqual(len(first_ul.find_all("li", recursive=False)), 4)

        # last li of first list HAS a nested ul
        last_li = first_ul.find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 1)

    def test_2_nested_lists_becomes_nested_and_last_item_added_to_first_list(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_2_nested_lists_followed_by_li, "html.parser")
        )
        # three uls
        self.assertEqual(len(soup.select("ul")), 3)
        # two nested lists
        self.assertEqual(len(soup.select("ul > li > ul")), 2)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # first ul has 5 li children
        first_ul = soup.find("ul")
        self.assertEqual(len(first_ul.find_all("li", recursive=False)), 5)

        # last li of first list DOES NOT HAVE a nested ul
        last_li = first_ul.find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 0)

    def test_double_nested_list_becomes_nested(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_double_nested_list, "html.parser")
        )
        # three uls
        self.assertEqual(len(soup.select("ul")), 3)
        # two single nested lists
        self.assertEqual(len(soup.select("ul > li > ul")), 2)
        # one double nested list
        self.assertEqual(len(soup.select("ul > li > ul > li > ul")), 1)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # first ul has 3 li children
        first_ul = soup.find("ul")
        self.assertEqual(len(first_ul.find_all("li", recursive=False)), 3)

        # last li of first list HAS 2 uls
        last_li = first_ul.find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 2)

    def test_double_nested_list_becomes_nested_and_last_item_added_to_first_list(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_double_nested_list_followed_by_li, "html.parser")
        )
        # three uls
        self.assertEqual(len(soup.select("ul")), 3)
        # two single nested lists
        self.assertEqual(len(soup.select("ul > li > ul")), 2)
        # one double nested list
        self.assertEqual(len(soup.select("ul > li > ul > li > ul")), 1)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # first ul has 4 li children
        first_ul = soup.find("ul")
        self.assertEqual(len(first_ul.find_all("li", recursive=False)), 4)

        # last li of first list DOES NOT HAVE uls
        last_li = first_ul.find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 0)

    def test_join_2_lists_with_same_classname(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_2_lists_to_join, "html.parser")
        )
        # two uls
        self.assertEqual(len(soup.select("ul")), 1)
        # one nested list
        self.assertEqual(len(soup.select("ul > li > ul")), 0)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # first ul has 6 li children
        first_ul = soup.find("ul")
        self.assertEqual(len(first_ul.find_all("li", recursive=False)), 6)

    def test_join_2_nested_lists_with_same_classname(self):
        soup = join_nested_lists(
            BeautifulSoup(self.html_2_nested_lists_to_join, "html.parser")
        )
        # two uls
        self.assertEqual(len(soup.select("ul")), 2)
        # one nested list
        self.assertEqual(len(soup.select("ul > li > ul")), 1)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # last li of first list HAS a nested ul
        last_li = soup.find("ul").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 1)
        # nested ul has 5 lis
        self.assertEqual(len(last_li.find("ul").find_all("li")), 6)

    def test_join_2_nested_lists_with_same_classname_after_a_double_nested_list(self):
        soup = join_nested_lists(
            BeautifulSoup(
                self.html_2_nested_lists_to_join_after_double_nested_list, "html.parser"
            )
        )
        # three uls
        self.assertEqual(len(soup.select("ul")), 3)
        # two nested lists
        self.assertEqual(len(soup.select("ul > li > ul")), 2)
        # one double nested list
        self.assertEqual(len(soup.select("ul > li > ul > li > ul")), 1)
        # no uls are siblings
        self.assertEqual(len(soup.select("ul + ul")), 0)

        # last li of first list HAS a nested ul
        last_li = soup.find("ul").find_all("li", recursive=False)[-1]
        self.assertEqual(len(last_li.find_all("ul")), 2)
        # nested ul has 5 lis
        self.assertEqual(len(last_li.find("ul").find_all("li", recursive=False)), 4)
