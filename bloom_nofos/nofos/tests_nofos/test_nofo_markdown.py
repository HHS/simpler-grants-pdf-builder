from django.test import TestCase
from nofos.nofo_markdown import md

#########################################################
############# MARKDOWNIFY CONVERTER TESTS ###############
#########################################################


class NofoMarkdownConverterTABLETest(TestCase):
    def test_table_no_colspan_or_rowspan(self):
        html = "<table><tr><td>Cell 1</td><td>Cell 2</td></tr></table>"
        expected_markdown = "|  |  |\n| --- | --- |\n| Cell 1 | Cell 2 |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_table_with_colspan(self):
        html = '<table><tr><td colspan="2">Cell 1</td></tr></table>'
        pretty_html = (
            '<table>\n <tr>\n  <td colspan="2">\n   Cell 1\n  </td>\n </tr>\n</table>'
        )
        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)

    def test_table_with_rowspan(self):
        html = '<table><tr><td rowspan="2">Cell 1</td><td>Cell 2</td></tr></table>'
        pretty_html = '<table>\n <tr>\n  <td rowspan="2">\n   Cell 1\n  </td>\n  <td>\n   Cell 2\n  </td>\n </tr>\n</table>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)

    def test_table_with_nested_html(self):
        html = '<table class="c229 c294"><tr class="c202"><th class="c170 c184" colspan="4" rowspan="1"><p class="c21 c205">Year 1 Work Plan </p></th></tr><tr class="c100"><td class="c170" colspan="4" rowspan="1"><p class="c18"><strong>Program goal</strong>: Provide targeted assistance to support program efforts for outreach, education, and enrollment in health insurance plans. </p></td></tr><tr class="c281"><td class="c155 c191" colspan="1" rowspan="1"><p class="c21"><strong>Activities</strong></p></td><td class="c155 c218" colspan="1" rowspan="1"><p class="c21"><strong>Target number</strong></p></td></tr><tr class="c303"><td class="c85" colspan="1" rowspan="1"><p class="c18">Publish marketing ads on tv, radio, and print to increase visibility in community. </p></td><td class="c145" colspan="1" rowspan="1"><ul class="c1 lst-kix_list_18-0 start"><li class="c12 li-bullet-0">3 billboards </li><li class="c12 li-bullet-0">6 radio ads  </li><li class="c12 li-bullet-0">8 TV ads </li></ul></td></tr></table>'
        pretty_html = """<table>
 <tr>
  <th colspan="4" rowspan="1">
   <p>
    Year 1 Work Plan
   </p>
  </th>
 </tr>
 <tr>
  <td colspan="4" rowspan="1">
   <p>
    <strong>
     Program goal
    </strong>
    : Provide targeted assistance to support program efforts for outreach, education, and enrollment in health insurance plans.
   </p>
  </td>
 </tr>
 <tr>
  <td colspan="1" rowspan="1">
   <p>
    <strong>
     Activities
    </strong>
   </p>
  </td>
  <td colspan="1" rowspan="1">
   <p>
    <strong>
     Target number
    </strong>
   </p>
  </td>
 </tr>
 <tr>
  <td colspan="1" rowspan="1">
   <p>
    Publish marketing ads on tv, radio, and print to increase visibility in community.
   </p>
  </td>
  <td colspan="1" rowspan="1">
   <ul>
    <li>
     3 billboards
    </li>
    <li>
     6 radio ads
    </li>
    <li>
     8 TV ads
    </li>
   </ul>
  </td>
 </tr>
</table>"""

        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)

    def test_table_0_ths(self):
        html = "<table><tr><td>TD 1</td><td>TD 2</td></tr><tr><td colspan='2'>Cell 1</td></th></table>"
        expected_html = """
<table>
 <tr>
  <td>
   TD 1
  </td>
  <td>
   TD 2
  </td>
 </tr>
 <tr>
  <td colspan="2">
   Cell 1
  </td>
 </tr>
</table>"""
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html.strip())

    def test_table_1_th(self):
        html = (
            "<table><tr><th>TH 1</th></tr><tr><td colspan='1'>Cell 1</td></th></table>"
        )
        expected_markdown = "| TH 1 |\n| --- |\n| Cell 1 |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_table_2_ths(self):
        html = "<table><tr><th>TH 1</th><th>TH 2</th></tr><tr><td colspan='2'>Cell 1</td></th></table>"
        expected_html = """<table>
 <tr>
  <th>
   TH 1
  </th>
  <th>
   TH 2
  </th>
 </tr>
 <tr>
  <td colspan="2">
   Cell 1
  </td>
 </tr>
</table>"""
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html.strip())

    def test_table_3_ths(self):
        html = "<table><tr><th>TH 1</th><th>TH 2</th><th>TH 3</th></tr><tr><td colspan='2'>Cell 1</td><td>Cell 3</td></th></table>"
        expected_html = """<table>
 <tr>
  <th class="w-33">
   TH 1
  </th>
  <th class="w-33">
   TH 2
  </th>
  <th class="w-33">
   TH 3
  </th>
 </tr>
 <tr>
  <td colspan="2">
   Cell 1
  </td>
  <td>
   Cell 3
  </td>
 </tr>
</table>"""
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html.strip())

    def test_table_3_ths_with_paragraphs(self):
        html = "<table><tr><th><p>TH 1.1</p><p>TH 1.2</p></th><th>TH 2</th><th>TH 3</th></tr><tr><td colspan='2'>Cell 1</td><td>Cell 3</td></th></table>"
        expected_html = """<table>
 <tr>
  <th class="w-33">
   <p>
    TH 1.1
   </p>
   <p>
    TH 1.2
   </p>
  </th>
  <th class="w-33">
   TH 2
  </th>
  <th class="w-33">
   TH 3
  </th>
 </tr>
 <tr>
  <td colspan="2">
   Cell 1
  </td>
  <td>
   Cell 3
  </td>
 </tr>
</table>"""
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html.strip())

    def test_table_4_ths(self):
        html = "<table><tr><th>TH 1</th><th>TH 2</th><th>TH 3</th><th>TH 4</th></tr><tr><td colspan='2'>Cell 1</td><td>Cell 3</td><td>Cell 4</td></th></table>"
        expected_html = """<table>
 <tr>
  <th class="w-25">
   TH 1
  </th>
  <th class="w-25">
   TH 2
  </th>
  <th class="w-25">
   TH 3
  </th>
  <th class="w-25">
   TH 4
  </th>
 </tr>
 <tr>
  <td colspan="2">
   Cell 1
  </td>
  <td>
   Cell 3
  </td>
  <td>
   Cell 4
  </td>
 </tr>
</table>"""
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html.strip())

    def test_table_5_ths(self):
        html = "<table><tr><th>TH 1</th><th>TH 2</th><th>TH 3</th><th>TH 4</th><th>TH 5</th></tr><tr><td colspan='2'>Cell 1</td><td>Cell 3</td><td>Cell 4</td><td>Cell 5</td></th></table>"
        expected_html = """<table>
 <tr>
  <th class="w-20">
   TH 1
  </th>
  <th class="w-20">
   TH 2
  </th>
  <th class="w-20">
   TH 3
  </th>
  <th class="w-20">
   TH 4
  </th>
  <th class="w-20">
   TH 5
  </th>
 </tr>
 <tr>
  <td colspan="2">
   Cell 1
  </td>
  <td>
   Cell 3
  </td>
  <td>
   Cell 4
  </td>
  <td>
   Cell 5
  </td>
 </tr>
</table>"""
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html.strip())

    def test_table_6_ths(self):
        # no classnames on this one
        html = "<table><tr><th>TH 1</th><th>TH 2</th><th>TH 3</th><th>TH 4</th><th>TH 5</th><th>TH 6</th></tr><tr><td colspan='2'>Cell 1</td><td>Cell 3</td><td>Cell 4</td><td>Cell 5</td><td>Cell 6</td></th></table>"
        expected_html = """<table>
 <tr>
  <th>
   TH 1
  </th>
  <th>
   TH 2
  </th>
  <th>
   TH 3
  </th>
  <th>
   TH 4
  </th>
  <th>
   TH 5
  </th>
  <th>
   TH 6
  </th>
 </tr>
 <tr>
  <td colspan="2">
   Cell 1
  </td>
  <td>
   Cell 3
  </td>
  <td>
   Cell 4
  </td>
  <td>
   Cell 5
  </td>
  <td>
   Cell 6
  </td>
 </tr>
</table>"""
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html.strip())


class NofoMarkdownConverterTHTest(TestCase):
    def test_table_0_ths(self):
        html = "<table><tr><td>TD 1</td><td>TD 2</td></tr><tr><td>Cell 1</td><td>Cell 2</td></th></table>"
        expected_markdown = (
            "|  |  |\n| --- | --- |\n| TD 1 | TD 2 |\n| Cell 1 | Cell 2 |"
        )
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_table_1_th(self):
        html = "<table><tr><th>TH 1</th></tr><tr><td>Cell 1</td></th></table>"
        expected_markdown = "| TH 1 |\n| --- |\n| Cell 1 |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_table_2_ths(self):
        html = "<table><tr><th>TH 1</th><th>TH 2</th></tr><tr><td>Cell 1</td><td>Cell 2</td></th></table>"
        expected_markdown = "| TH 1 | TH 2 |\n| --- | --- |\n| Cell 1 | Cell 2 |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_table_3_ths(self):
        html = "<table><tr><th>TH 1</th><th>TH 2</th><th>TH 3</th></tr><tr><td>Cell 1</td><td>Cell 2</td><td>Cell 3</td></th></table>"
        expected_markdown = "| TH 1 {: .w-33 } | TH 2 {: .w-33 } | TH 3 {: .w-33 } |\n| --- | --- | --- |\n| Cell 1 | Cell 2 | Cell 3 |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_table_3_ths_with_paragraphs(self):
        html = "<table><tr><th><p>TH 1.1</p><p>TH 1.2</p></th><th>TH 2</th><th>TH 3</th></tr><tr><td>Cell 1</td><td>Cell 2</td><td>Cell 3</td></th></table>"
        expected_markdown = "| <p>TH 1.1</p><p>TH 1.2</p> {: .w-33 } | TH 2 {: .w-33 } | TH 3 {: .w-33 } |\n| --- | --- | --- |\n| Cell 1 | Cell 2 | Cell 3 |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_table_4_ths(self):
        html = "<table><tr><th>TH 1</th><th>TH 2</th><th>TH 3</th><th>TH 4</th></tr><tr><td>Cell 1</td><td>Cell 2</td><td>Cell 3</td><td>Cell 4</td></th></table>"
        expected_markdown = "| TH 1 {: .w-25 } | TH 2 {: .w-25 } | TH 3 {: .w-25 } | TH 4 {: .w-25 } |\n| --- | --- | --- | --- |\n| Cell 1 | Cell 2 | Cell 3 | Cell 4 |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_table_5_ths(self):
        html = "<table><tr><th>TH 1</th><th>TH 2</th><th>TH 3</th><th>TH 4</th><th>TH 5</th></tr><tr><td>Cell 1</td><td>Cell 2</td><td>Cell 3</td><td>Cell 4</td><td>Cell 5</td></th></table>"
        expected_markdown = "| TH 1 {: .w-20 } | TH 2 {: .w-20 } | TH 3 {: .w-20 } | TH 4 {: .w-20 } | TH 5 {: .w-20 } |\n| --- | --- | --- | --- | --- |\n| Cell 1 | Cell 2 | Cell 3 | Cell 4 | Cell 5 |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_table_6_ths(self):
        # no classnames on this one
        html = "<table><tr><th>TH 1</th><th>TH 2</th><th>TH 3</th><th>TH 4</th><th>TH 5</th><th>TH 6</th></tr><tr><td>Cell 1</td><td>Cell 2</td><td>Cell 3</td><td>Cell 4</td><td>Cell 5</td><td>Cell 6</td></th></table>"
        expected_markdown = "| TH 1 | TH 2 | TH 3 | TH 4 | TH 5 | TH 6 |\n| --- | --- | --- | --- | --- | --- |\n| Cell 1 | Cell 2 | Cell 3 | Cell 4 | Cell 5 | Cell 6 |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_application_checklist_table(self):
        html = "<table><tr><th><p><strong>Component</strong></p></th><th><p><strong>How to upload </strong></p></th><th><p><strong>Page limit </strong></p></th></tr><tr><td><p>◻ <a href='  # _Project_abstract'><strong>Project abstract</strong></a> </p></td><td><p>Use the Project Abstract Summary Form. </p></td><td><p>1 page </p></td></tr></tbody></table>"
        expected_markdown = "| **Component** {: .w-45 } | **How to upload** {: .w-40 } | **Page limit** {: .w-15 } |\n| --- | --- | --- |\n| ◻ [**Project abstract**](  # _Project_abstract) | Use the Project Abstract Summary Form. | 1 page |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_application_checklist_table_variant(self):
        html = "<table><tr><th><p><strong>Component</strong></p></th><th><p><strong>How to Submit in Grants.gov </strong></p></th><th><p><strong>Included in the page limit? </strong></p></th></tr><tr><td><p>◻ <a href='  # _Project_abstract'><strong>Project abstract</strong></a> </p></td><td><p>Use the Project Abstract Summary Form. </p></td><td><p>1 page </p></td></tr></tbody></table>"
        expected_markdown = "| **Component** {: .w-45 } | **How to Submit in Grants.gov** {: .w-40 } | **Included in the page limit?** {: .w-15 } |\n| --- | --- | --- |\n| ◻ [**Project abstract**](  # _Project_abstract) | Use the Project Abstract Summary Form. | 1 page |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_application_checklist_table_with_colspan(self):
        html = "<table><tr><th colspan='2'><p><strong>Component</strong></p></th><th><p><strong>How to upload </strong></p></th><th><p><strong>Page limit </strong></p></th></tr><tr><td colspan='2'><p>◻ <a href='  # _Project_abstract'><strong>Project abstract</strong></a> </p></td><td><p>Use the Project Abstract Summary Form. </p></td><td><p>1 page </p></td></tr></tbody></table>"
        expected_html = '<table>\n <tr>\n  <th class="w-45" colspan="2">\n   <p>\n    <strong>\n     Component\n    </strong>\n   </p>\n  </th>\n  <th class="w-40">\n   <p>\n    <strong>\n     How to upload\n    </strong>\n   </p>\n  </th>\n  <th class="w-15">\n   <p>\n    <strong>\n     Page limit\n    </strong>\n   </p>\n  </th>\n </tr>\n <tr>\n  <td colspan="2">\n   <p>\n    ◻\n    <a href="  # _Project_abstract">\n     <strong>\n      Project abstract\n     </strong>\n    </a>\n   </p>\n  </td>\n  <td>\n   <p>\n    Use the Project Abstract Summary Form.\n   </p>\n  </td>\n  <td>\n   <p>\n    1 page\n   </p>\n  </td>\n </tr>\n</table>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html.strip())


class NofoMarkdownConverterOLTest(TestCase):
    maxDiff = None

    def test_ol_for_footnotes(self):
        html = '<ol><li id="footnote-0">Item 1</li><li id="footnote-1">Item 2</li></ol>'
        pretty_html = '<ol>\n <li id="footnote-0" tabindex="-1">\n  Item 1\n </li>\n <li id="footnote-1" tabindex="-1">\n  Item 2\n </li>\n</ol>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)

    def test_ol_for_endnotes(self):
        html = '<ol><li id="endnote-2">Item 1</li><li id="endnote-3">Item 2</li></ol>'
        pretty_html = '<ol>\n <li id="endnote-2" tabindex="-1">\n  Item 1\n </li>\n <li id="endnote-3" tabindex="-1">\n  Item 2\n </li>\n</ol>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)

    def test_ol_start_not_one(self):
        html = '<ol start="2"><li>Item 1</li><li>Item 2</li></ol>'
        pretty_html = '<ol start="2"><li>Item 1</li><li>Item 2</li></ol>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)

    def test_ol_inside_td(self):
        html = "<table><tr><th>Header</th></tr><tr><td><ol><li>Item 1</li><li>Item 2</li></ol></td></tr></table>"
        pretty_html = "| Header |\n| --- |\n| <ol><li>Item 1</li><li>Item 2</li></ol> |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)

    def test_ol_start_one(self):
        html = '<ol start="1"><li>Item 1</li><li>Item 2</li></ol>'
        expected_markdown = "1. Item 1\n2. Item 2"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_ol_inside_td_start_not_one(self):
        html = '<table><tr><th>Header</th></tr><tr><td><ol start="3"><li>Item 1</li><li>Item 2</li></ol></td></tr></table>'
        pretty_html = (
            '| Header |\n| --- |\n| <ol start="3"><li>Item 1</li><li>Item 2</li></ol> |'
        )
        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)

    def test_table_with_ol_strip_classes_nested_html(self):
        html = '<table class="c40"><tr class="c311"><td class="c68 c127" colspan="1" rowspan="1"><p class="c89"><span class="c6">Demonstrates the ability to comply with all applicable privacy and security standards by developing a PII plan that outlines the following:</span></p></td><td class="c168 c127" colspan="1" rowspan="1"><p class="c41 c104"><span class="c69 c67"></span></p></td></tr><tr class="c216"><td class="c31" colspan="1" rowspan="1"><ul class="c1 lst-kix_list_76-0"><li class="c33 li-bullet-0"><span class="c6">A process for ensuring compliance by all staff performing Navigator activities (as well as those who have access to sensitive information or PII related to your organization’s Navigator activities) with </span><span class="c7"><a class="c32" href="https://www.google.com">FFE privacy and security standards</a></span><span class="c6">, especially when using computers, laptops, tablets, smartphones, and other electronic devices.</span></li></ul></td><td class="c11" colspan="1" rowspan="1"><p class="c41"><span class="c51">5 points</span></p></td></tr></table>'
        pretty_html = """|  |  |\n| --- | --- |\n| Demonstrates the ability to comply with all applicable privacy and security standards by developing a PII plan that outlines the following: |  |\n| <ul><li><span>A process for ensuring compliance by all staff performing Navigator activities (as well as those who have access to sensitive information or PII related to your organization’s Navigator activities) with </span><span><a href="https://www.google.com">FFE privacy and security standards</a></span><span>, especially when using computers, laptops, tablets, smartphones, and other electronic devices.</span></li></ul> | 5 points |"""

        md_body = md(html)
        self.assertEqual(md_body.strip(), pretty_html)

    def test_ol_start_one(self):
        html = '<ol start="1"><li>Item 1</li><li>Item 2</li></ol>'
        expected_markdown = "1. Item 1\n2. Item 2"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_ol_asterisk_list(self):
        html = '<ol start="2"><li>Item 1*</li><li>Item 2</li></ol>'
        expected_markdown = '<ol start="2"><li>Item 1*</li><li>Item 2</li></ol>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_ol_asterisk_table(self):
        html = "<table><tr><th>Header 1</th><th>Header 2</th></tr><tr><td><ol><li>Item 1*</li><li>Item 2</li></ol></td><td>Cell 2</td></tr></table>"
        expected_markdown = "| Header 1 | Header 2 |\n| --- | --- |\n| <ol><li>Item 1&ast;</li><li>Item 2</li></ol> | Cell 2 |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_ol_asterisk_table_colspan(self):
        html = '<table><tr><th colspan="2">Header 1</th></tr><tr><td><ol><li>Item 1*</li><li>Item 2</li></ol></td><td>Cell 2</td></tr></table>'
        expected_markdown = '<table>\n <tr>\n  <th colspan="2">\n   Header 1\n  </th>\n </tr>\n <tr>\n  <td>\n   <ol>\n    <li>\n     Item 1*\n    </li>\n    <li>\n     Item 2\n    </li>\n   </ol>\n  </td>\n  <td>\n   Cell 2\n  </td>\n </tr>\n</table>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())


class NofoMarkdownConverterULTest(TestCase):
    maxDiff = None

    def test_ul_asterisk_list(self):
        html = "<ul><li>Item 1*</li><li>Item 2</li></ul>"
        expected_markdown = "* Item 1\\*\n* Item 2"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_ul_asterisk_table(self):
        html = "<table><tr><th>Header 1</th><th>Header 2</th></tr><tr><td><ul><li>Item 1*</li><li>Item 2</li></ul></td><td>Cell 2</td></tr></table>"
        expected_markdown = "| Header 1 | Header 2 |\n| --- | --- |\n| <ul><li>Item 1&ast;</li><li>Item 2</li></ul> | Cell 2 |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_ul_asterisk_table_colspan(self):
        html = '<table><tr><th colspan="2">Header 1</th></tr><tr><td><ul><li>Item 1*</li><li>Item 2</li></ul></td><td>Cell 2</td></tr></table>'
        expected_markdown = '<table>\n <tr>\n  <th colspan="2">\n   Header 1\n  </th>\n </tr>\n <tr>\n  <td>\n   <ul>\n    <li>\n     Item 1*\n    </li>\n    <li>\n     Item 2\n    </li>\n   </ul>\n  </td>\n  <td>\n   Cell 2\n  </td>\n </tr>\n</table>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())


class NofoMarkdownConverterLITest(TestCase):
    def test_five_level_nested_ul(self):
        html = """
        <ul>
            <li>Level 1
                <ul>
                    <li>Level 2
                        <ul>
                            <li>Level 3
                                <ul>
                                    <li>Level 4
                                        <ul>
                                            <li>Level 5</li>
                                        </ul>
                                    </li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>
            </li>
        </ul>
        """
        expected = """* Level 1
    + Level 2
        - Level 3
            * Level 4
                + Level 5"""
        self.assertEqual(md(html).strip(), expected.strip())

    def test_five_level_nested_ol(self):
        html = """
        <ol>
            <li>Step 1
                <ol>
                    <li>Step 2
                        <ol>
                            <li>Step 3
                                <ol>
                                    <li>Step 4
                                        <ol>
                                            <li>Step 5</li>
                                        </ol>
                                    </li>
                                </ol>
                            </li>
                        </ol>
                    </li>
                </ol>
            </li>
        </ol>
        """
        expected = """1. Step 1
    1. Step 2
        1. Step 3
            1. Step 4
                1. Step 5"""
        self.assertEqual(md(html).strip(), expected.strip())

    def test_mixed_ul_inside_ol(self):
        html = """
        <ol>
            <li>Do this
                <ul>
                    <li>First</li>
                    <li>Second</li>
                </ul>
            </li>
        </ol>
        """
        expected = """1. Do this
    * First
    * Second"""
        self.assertEqual(md(html).strip(), expected.strip())

    def test_mixed_ol_inside_ul(self):
        html = """
        <ul>
            <li>Start here
                <ol>
                    <li>Step A</li>
                    <li>Step B</li>
                </ol>
            </li>
        </ul>
        """
        expected = """* Start here
    1. Step A
    2. Step B"""
        self.assertEqual(md(html).strip(), expected.strip())


class NofoMarkdownConverterATest(TestCase):
    maxDiff = None

    def test_a_for_footnotes(self):
        html = '<a id="footnote-0" href="#footnote-0">1</a>'
        expected_html = '<sup><a href="#footnote-0" id="footnote-0">1</a></sup>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)

    def test_a_without_footnotes(self):
        html = '<a href="https://example.com">Example</a>'
        expected_markdown = "[Example](https://example.com)"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_a_with_classes(self):
        html = '<a class="link-class" href="https://example.com">Example</a>'
        expected_markdown = "[Example](https://example.com)"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_a_footnote_with_classes(self):
        html = '<a id="footnote-0" class="footnote-class" href="#footnote-0">1</a>'
        expected_html = '<sup><a href="#footnote-0" id="footnote-0">1</a></sup>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)


class NofoMarkdownConverterPTest(TestCase):
    maxDiff = None

    def test_p_with_bookmark_id(self):
        html = '<p id="bookmark-1">Bookmark Paragraph</p>'
        expected_html = '<p id="bookmark-1">Bookmark Paragraph</p>'
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)

    def test_regular_p(self):
        html = "<p>Regular Paragraph</p>"
        expected_markdown = "Regular Paragraph"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_regular_p_asterisk(self):
        html = "<p>Regular Paragraph with asterisk *</p>"
        expected_markdown = "Regular Paragraph with asterisk \\*"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_regular_p_in_td(self):
        html = "<table><tr><th><p>Header</p></th></tr><tr><td><p>Content</p></td></tr></table>"
        expected_markdown = "| Header |\n| --- |\n| Content |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_regular_p_asterisk_in_td(self):
        html = "<table><tr><th><p>Header</p></th></tr><tr><td><p>Content *</p></td></tr></table>"
        expected_markdown = "| Header |\n| --- |\n| Content \\* |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_regular_p_asterisk_in_th(self):
        html = "<table><tr><th><p>Header *</p></th></tr><tr><td><p>Content</p></td></tr></table>"
        expected_markdown = "| Header \\* |\n| --- |\n| Content |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_two_ps_in_th(self):
        html = "<table><tr><th><p>Header 1</p><p>Header 2</p></th></tr><tr><td><p>Content</p></td></tr></table>"
        expected_markdown = "| <p>Header 1</p><p>Header 2</p> |\n| --- |\n| Content |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_two_ps_in_th_asterisk(self):
        html = "<table><tr><th><p>Header 1</p><p>Header 2 *</p></th></tr><tr><td><p>Content</p></td></tr></table>"
        expected_markdown = (
            "| <p>Header 1</p><p>Header 2 &ast;</p> |\n| --- |\n| Content |"
        )
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_two_ps_in_td(self):
        html = "<table><tr><th><p>Header</p></th></tr><tr><td><p>Content 1</p><p>Content 2</p></td></tr></table>"
        expected_markdown = "| Header |\n| --- |\n| <p>Content 1</p><p>Content 2</p> |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_two_ps_in_td_asterisk(self):
        html = "<table><tr><th><p>Header</p></th></tr><tr><td><p>Content 1</p><p>Content 2 *</p></td></tr></table>"
        expected_markdown = (
            "| Header |\n| --- |\n| <p>Content 1</p><p>Content 2 &ast;</p> |"
        )
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())

    def test_two_ps_in_th_and_td(self):
        html = "<table><tr><th><p>Header 1</p><p>Header 2</p></th></tr><tr><td><p>Content 1</p><p>Content 2</p></td></tr></table>"
        expected_markdown = "| <p>Header 1</p><p>Header 2</p> |\n| --- |\n| <p>Content 1</p><p>Content 2</p> |"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_markdown.strip())


class NofoMarkdownConverterDIVTest(TestCase):
    maxDiff = None

    def test_div_role_heading(self):
        html = '<h6>Component funding</h6><div><div aria-level="7" role="heading">Overview</div><p>We fund all cooperative agreements using component funding.</p>'
        expected_html = '###### Component funding\n\n<div aria-level="7" role="heading">Overview</div>\n\nWe fund all cooperative agreements using component funding.'
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)

    def test_div_class_heading_8(self):
        html = '<h6>Component funding</h6><div class="heading-8">Overview</div><p>We fund all cooperative agreements using component funding.</p>'
        expected_html = '###### Component funding\n\n<div class="heading-8">Overview</div>\n\nWe fund all cooperative agreements using component funding.'
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)

    def test_div_class_heading_9(self):
        html = '<h6>Component funding</h6><div class="heading-9">Overview</div><p>We fund all cooperative agreements using component funding.</p>'
        expected_html = "###### Component funding\n\nOverview\n\nWe fund all cooperative agreements using component funding."
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)

    def test_div_class_empty(self):
        html = '<h6>Component funding</h6><div class="">Overview</div><p>We fund all cooperative agreements using component funding.</p>'
        expected_html = "###### Component funding\n\nOverview\n\nWe fund all cooperative agreements using component funding."
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)

    def test_div_no_role_heading_no_class(self):
        html = "<h6>Component funding</h6><div>Overview</div><p>We fund all cooperative agreements using component funding.</p>"
        expected_html = "###### Component funding\n\nOverview\n\nWe fund all cooperative agreements using component funding."
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)

    def test_div_role_heading_with_nested_elements(self):
        html = (
            '<div role="heading"><span>Overview</span><strong>Important</strong></div>'
        )
        expected_html = (
            '<div role="heading"><span>Overview</span><strong>Important</strong></div>'
        )
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)

    def test_div_no_role_heading_with_nested_elements(self):
        html = "<div><span>Overview</span><strong>Important</strong></div>"
        expected_html = "Overview**Important**"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)

    def test_div_role_heading_class_heading_8(self):
        html = '<h6>Component funding</h6><div aria-level="7" role="heading">Overview</div><div class="heading-8">Introduction</div><p>We fund all cooperative agreements using component funding.</p>'
        expected_html = '###### Component funding\n\n<div aria-level="7" role="heading">Overview</div><div class="heading-8">Introduction</div>\n\nWe fund all cooperative agreements using component funding.'
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)

    def test_combination_of_divs(self):
        html = """
        <div role="heading">Heading One</div><div>This is just a regular div.</div><p>Some paragraph text.</p>
        """
        expected_html = '<div role="heading">Heading One</div>This is just a regular div.\n\nSome paragraph text.'
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)

    def test_nested_div_with_role_heading(self):
        html = """
        <div><div><div role="heading">Nested Heading</div><p>Nested paragraph inside div.</p></div><p>Another paragraph.</p></div>
        """
        expected_html = '<div role="heading">Nested Heading</div>\n\nNested paragraph inside div.\n\nAnother paragraph.'
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)

    def test_div_with_attributes_no_role_heading(self):
        html = '<div class="some-class" id="div1" aria-level="7" role="main">This is a test div</div>'
        expected_html = "This is a test div"
        md_body = md(html)
        self.assertEqual(md_body.strip(), expected_html)
