# Accessibility

NOFO Builder helps agencies publish Notices of Funding Opportunity (NOFOs).
This guide covers published NOFO PDFs and the NOFO Builder and Composer web app.
For Composer's Word exports, see the [Word export design record](adr/2026-01-12-html-to-docx-solution.md).

## Report a problem or request an accessible copy

- **Published notice:** Contact the agency listed in the notice. Tell them which
  notice you are trying to use and ask for an accessible copy if needed. If you
  need more help, see the [HHS accessibility contacts](https://www.hhs.gov/accessibility/hhs-digital-accessibility-statement/index.html).
- **NOFO Builder support:** Start with your grants policy office. If you need more
  help, contact the SimplerNOFOs team.
- **NOFO Builder or repository issue:** Search [existing issues](https://github.com/HHS/simpler-grants-pdf-builder/issues),
  then [open a GitHub issue](https://github.com/HHS/simpler-grants-pdf-builder/issues/new/choose).
  Ask the team to add the `A11y` label. Describe what you were trying to do,
  where you ran into a problem, and what happened. If relevant, include the
  browser or assistive technology you used. Include only information approved
  for public sharing.

## Standards

Published NOFO PDFs and the web app must meet the applicable
[Revised Section 508 Standards](https://www.access-board.gov/ict/). These
standards include applicable Level A and AA criteria from version 2.0 of the
Web Content Accessibility Guidelines (WCAG). The project's goal is
[WCAG 2.2 Level AA](https://www.w3.org/TR/WCAG22/) where practical.

Follow your agency's clearance process before publishing. The
[NOFO design standards](DESIGN_STANDARDS.md) summarize selected HHS guidance
and include a checklist.

## What NOFO Builder does

- NOFO Builder uses headings, lists, and tables from the source document to help
  preserve its structure. See the [import rules](IMPORT_RULES.md).
- NOFO Builder requests a tagged PDF. Tags help assistive technology identify
  headings, lists, and other parts of the document. Check the tags and the order
  in which assistive technology reads the content in the exported file.
- NOFO Builder marks images that are missing a text description (alt text) in the
  imported content. Add a description for images that convey information.
  Screen readers can skip images with empty alt text. Editors can also
  [add a description to the cover image](EDITOR_TASKS.md#task-cover-alt-text).
- The edit page flags possible problems with headings, links, endnotes,
  document details, list numbering, and leftover template instructions.
  See [editor tasks](EDITOR_TASKS.md) for help making fixes.

## How output is checked

1. Review NOFO Builder's warnings, preview the PDF, and use the
   [before you publish checklist](DESIGN_STANDARDS.md#before-you-publish).
2. Open the exported PDF in Adobe Acrobat Pro. Go to **All tools**, then
   **Prepare for accessibility**, and select **Check for accessibility**. Review
   findings and items marked **Needs Manual Check**, which can include reading
   order, color contrast, and navigation links. The checker is one part of the
   review. See [Adobe's accessibility checker instructions](https://helpx.adobe.com/acrobat/using/create-verify-pdf-accessibility.html)
   and [Section508.gov testing guidance](https://www.section508.gov/test/).
3. In **Document Properties**, confirm that Title, Author, Subject, and
   Keywords are filled in and correct. In NOFO Builder, edit the title under
   [Basic information](EDITOR_TASKS.md#task-basic-info) and the other fields
   under [NOFO metadata](EDITOR_TASKS.md#task-pdf-metadata).
4. Fix document problems in NOFO Builder or in Word if you plan to import the
   document again. Export a new PDF and repeat the checks. Ask your grants
   policy office for help with findings you cannot resolve.

Aim for a PDF of 5 MB or less so applicants with slower connections can download
it more easily. This is a SimplerNOFOs target. If you compress the PDF, keep the
original, check that text and images are still readable, and repeat the
accessibility checks on the copy you plan to publish. See **How do I check and
reduce my NOFO PDF’s file size?** in the SharePoint NOFO Builder FAQ for steps.

Reviewers can use [quality review and triage](QUALITY_REVIEW_AND_TRIAGE.md#review-design-accessibility)
to investigate findings and route them to the right team.

## Known gaps

- NOFO Builder does not check the exported PDF for accessibility. See
  [issue #980](https://github.com/HHS/simpler-grants-pdf-builder/issues/980)
  for research on adding those checks.
- The web app does not run automated accessibility scans in its test pipeline.
- The project has no documented contrast review covering every NOFO theme and
  the web app. Check contrast in the PDF you plan to publish.
- The subsection menu offers **Heading 7**. Use [Heading 1 through Heading 6 in
  order](EDITOR_TASKS.md#task-heading-level).
- Imported documents may still need fixes to image descriptions, complex
  tables, or lists created by typing bullets or numbers. See the
  [NOFO design standards](DESIGN_STANDARDS.md).

## For contributors

- Follow the [contribution workflow](CONTRIBUTION_WORKFLOW.md) and reuse
  [UI patterns](UI_PATTERNS.md) and
  [U.S. Web Design System components](https://designsystem.digital.gov/).
- NOFO Builder requests the `PDF/UA-1` profile from DocRaptor to produce tagged
  PDFs. See [how to validate the exported PDF](SCALABLE_NOFO_DESIGN_SYSTEM.md#4-validate-the-pdf-not-just-the-authoring-screen).
  Record changes to the profile, heading checks, or alt text handling in the
  [decision log](DECISIONS.md) or a [design record](adr/README.md).
- For changes to screens, themes, or PDF output, describe which accessibility
  checks you ran and which still need review.
