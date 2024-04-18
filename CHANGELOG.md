# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning since version 1.0.0.

## Unreleased

### Added

- Add "superuser status" to the users add + edit page
- Cover image for CDC-RFA-DP-24-0025
- Add thin icons now that somebody has asked for them
  - Only visible for NOFOs using the ACF theme
- Added new button to open nofos in a new tab
  - We can print them using a little drop-down
  - TODO: disable buttons on localhost
- Allow images as background of section pages
  - Don't actually add the image in CSS, we will do that using inline CSS for now

### Changed

- Harmonize the page-break-befores and make them searchable
  - page-break-after
  - column-break-before
  - column-break-after
- Change the header nav
  - Add a link to the admin backend for the NOFO for superusers
  - Remove the "Logout" link which nobody uses

### Fixed

- Application checklist borders weren't computing properly for ballot boxes, hmmm

## [1.18.0] - 2023-04-08

### Added

- Added section ids to the table captions on hover in edit mode
- Nested lists now work with ols as well as uls
  - Supports intermixing them as well (eg: ul, ol, ul)
  - nested ols use "a,b,c" instead of "1,2,3"
  - double-nested ols use "i,ii,iii"
    - also include new ol styling on edit pages
- Add "align-top"/"align-bottom" classes for table headings and cells
- Added new styling for "page-break-after|before" elements in edit view

### Changed

- Longer timeout time in gunicorn
- Changed NOFO number for ACF 0039
- Lengthen final list items that don't need the avoid-page-break class to 85 chars

### Fixed

- Removed a bunch of custom CSS rules now that we have NOFO-specific CSS
- Checklist icons are usually "◻" (medium square) but sometimes "☐" (ballot box)
- Solve weird page break bug affecting section 4 headings
- "Get Ready" in nav to match the section title (uppercase "R")
- Smaller padding for v v big table in ACL 0029

## [1.17.0] - 2023-03-29

### Added

- New theme: ASPR (white)
  - Removed the blue theme because we don't need it

### Changed

- Remove all nbsps on import, rather than piecemeal
- Only newline `<strong>` tags in right column callout boxes
- Add "page-break-before: avoid" to short final list items
- Bigger CMS logo
- Swap out `<img>` logos for `<svg>` logos
  - ACF
  - ACL
  - ASPR
  - CDC
  - CMS
  - HHS
  - HRSA
  - IHS
- Swap out the alert `<img>` for an `<svg>` on the HRSA 14 cover

### Fixed

- Add subsection order number to page title if there is no subsection name
- Update the date on the little callout box for HRSA 14
- Move the CMS logo down so that it aligns better with text baseline on cover page
- Clean up cover page for ACF medium image
- Show the right heading level for callout boxes with headings
- Never show "Contacts and support" sublinks in ToC, no matter the capitalization

## [1.16.0] - 2023-03-25

### Added

- Added cover image for HHS-2024-ACF-ACYF-EV-0039
- Added (back) the little callout box for HRSA 14

### Changed

- Use "Write" in the running nav for section 3 if the section name inclues "Write"
- Change ACL line-height to 1.4
- Bigger logo for CDC all-text
- Use SVG icons instead of img icons for table of contents
  - Finally, I can get rid of all those hardcoded images
- H7 'headings' in ACF are now 13pt
- Slightly less padding on the main NOFO index page table
- Remove the name of the subagency from the CMS cover page
- Default to text covers for ACF and ACL
- Default to standard icons for ACL
  - Also hide the edit link
- Smaller h1 font size for HHS-2024-ACF-ACYF-EV-0039

### Fixed

- The check for Basic information headings is more robust
- Handle HTML in strings for the wrap_text_before_colon_in_strong function
- Remove static_icon function and all static images associated with it
- Shipped a fix for NBSP tags in headings
- Properly tag the TOC and TOCI after seeing some error logs

## [1.15.0] - 2023-03-09

### Added

- Add utility classes for table rows
- Edit links float now for improved clickability
- New "icon style" attribute for NOFOs

### Changed

- New default image for the preview NOFOs
- Double default timeout to 59 seconds
- Allow markdown content in taglines
- Ensmallen the H5 and H6 headings for the CMS theme
- Use <svg> icons instead of <img>s in section cover pages

### Fixed

- Rename folder for CDC-RFA-EH24-0044
- Smaller h1 on the title page if the title is too long
- All sections should trigger a page break before
- Stop sequential tables eating each other
- Remove 65% width for criteria tables
- Use official version of martor, no longer relying on a forked version
- Add pale blue background to CMS medium cover header
- Small CSS tweak to avoid orphan on HHS-2024-ACF-OPRE-YE-0195
- Fix double backslashes in table cells on import
- Application table fixes
  - Better understanding of when a cell is in a sublist
  - CSS is more precise

## [1.14.0] - 2023-03-08

### Added

- Add "page-break-before" class on import to 3 subsections:
  - "eligibility", "program description", and "application checklist"
- Add "designer" field to Nofo object
- Add "created" field to Nofo object
  - Updates whenever the Nofo is changed or its (sub)sections
- Show Nofo number on the "title" page
- Added another one-off: a callout box to the cover page of HRSA 014
- Cover image for CMS-1W1-24-001

### Changed

- Tag the table of contents list as a TOC
- Replace "before you begin" icon with SVG, not image
- Hide BYB Adobe Reader callout box on ACL 0025
- Nofo listing table on the main page
  - Show Coach and Designer
  - Show "Updated" instead of "Created"
  - Flip the "Edit" and "View" links
- Only show NOFO last updated times in table if they were updated today
- Remove ACF blue theme, since it is not allowed right now
- Rename "Medium image" to "Small image" for cover page options
- Light Blue icon for HRSA blue theme on ByB page

### Fixed

- Pencil icon SVG should show up for "write" or "prepare"
- Adjustments to fit the table of contents on one page
- Absolutely position checkbox svg to emulate bullets
- HRSA section pages now have white icons again
- Headings in first row of HTML tables (not markdown) have proper CSS styling
  - Borders are back!
- Links in table headings (what) should be currentColor
- Sort nofo table by last updated
  - Limit first column to 25% width otherwise it's ugly
- Smaller H6 size for ACF
- Allow importing Nofos with <a> tags with no href
- Fix adjusting icons in the ToC for the ACF default theme

## [1.13.0] - 2023-03-01

### Added

- It is now possible to switch between "Test" and "live" from the UI
- Cover image for CDC-RFA-EH-24-0044
- Add `<strong>` tags to classes with `font-size: 700` on import
  - skip table headings, and large font classes, but otherwise strong ’em up
- Add ids to page headings for table of contents and before you begin
- Added a new class for ACF white callout boxes (applied manually)
- Added link from subsection edit page to admin page and vice versa
  - Only for superusers
- Add class to empty table rows
- Add "Appendicies" to list of headings without section pages
- Add HRSA blue border svg images

### Changed

- For ACF Nofos, move the "Adobe Reader" annoucement to the Before you Begin page
  - For all Nofos except HRSA
- Two more href patterns for the "broken links" widget: "/" links and google docs domains
- Extra margin above running footer

### Fixed

- Add custom classnames to callout box subsections
- Fixed imports when font sizes contain decimal pt sizes
- Hotfix: CSS update for moving table of contents up in 1 Nofo
- Shaved off the fill on the checkbox SVG which was fatter than the others

## [1.12.0] - 2023-02-26

### Added

- Add link checker to looks for bad external links
  - Add button to the NOFO edit page for the broken link checker
- Add 'print' button to NOFO edit view
- Text only cover page for HRSA light theme
- Add new NOFO field: icon_path
  - Can be used to change ToC colour
- Added inline images for HRSA 016

### Changed

- Allow for importing tables with colspans or rowspans
  - (They will just be rendered as HTML rather than markdown)
- Change the azure callout boxes to grey in ORR theme
- Show NOFOs that have not been published as the default view
- No red tagline in ORR theme
- Return error messages to users for 400-level errors

### Fixed

- Fix application checklist styles for HRSA
- When section 3 said "prepare" instead of "write", the icon didn't show up
- FIXED: martor’s busted markdown link regex
  - https://github.com/pcraig3/django-markdown-editor/commit/9d78dd0bab9a4bfebcc4841794f6f5d54ad6d91a
- "Border" icons rather than "filled" for ORR theme
- Solid cover background for ORR theme
- Indent application checklists in portrait mode

## [1.11.0] - 2023-02-16

### Added

- Added ACL theme
  - With all-text cover
- Added HTML id to the headers
  - also a little 'copy' button
- Add new NOFO status: "In review"
  - In review NOFOs can’t be edited

### Changed

- Change cover image folder for NOFO whose number changed
- Hide header column configuration options for portrait NOFOs
- Change IHS tagline to blue
- Change small headings to black
- Group the themes together in the theme select widget

### Fixed

- Text only cover page: application date does not break line
- IHS logo smaller than HHS logo
- IHS smaller headings are Arial Bold
- Fix top white bar for CDC blue theme
  - Fix top white bar for CDC blue theme (hero)

## [1.10.0] - 2023-02-13

### Added

- Allow importing docs here callout boxes are not followed by headings
- Add numbers to empty sections in the edit view
- Add callout box indicator in edit view
- Callout box indicator to individual subsection edit view
- Add IHS theme (white)
  - With big text cover page
- Add visual indicator to the NOFO edit page for page/column breaks

### Changed

- Add white band to cover page DOP theme heading
- Allow for colspan header rows with blue backgrounds
- We can give tables classes and they keep them

### Fixed

- Longer width for subsection cover page in-section nav links

## [1.9.0] - 2023-02-12

### Added

- Create get_logo function so that logic for returning logos is contained
  - Get it to work for HRSA and ACF
- Added ACF white theme
- Added "big text cover" versions for ACF in both colours
- Cover for CDC-RFA-TU24-0137
- New form to add spaces in the order of a section
- Generate ID automatically when generating a new subsection with a name
- Really bad last-minute fixes for the CDC DOP NOFOs

### Changed

- Kind of new theme: CDC Portrait DOP with a dark teal colour
- Changes to big-text covers
  - Don't break line for (sub)agency
  - Unbold the Opportunity number
  - More top padding
- Blue tagline for ACF
- Application checklist for ACF
- Preserve "start" attribute in ols on import
- Changed name of the Django Admin area
- No name needed to create new subsections now
- Show NOFO number in the admin next to the sections, to make navigation easier
- Less weight "opportunity number" on cover pages

### Fixed

- Add scroll-margin-top to header cells on NOFO edit page
- Mostly fixed the neglected ACF theme
- Fix the landscape medium image cover for CDC
- Hide sub-bullets for 'Contacts and Support'
- Nudge header nav for section headers down a bit
- Allow "start" attribute in markdown so lists don't always have to start at 1
- Show subsections in admin ordered by the "order" property

## [1.8.0] - 2023-02-08

### Added

- Added an "avoid column break" value to subsections
- Added a little alert box on the edit nofo page to list broken links
  - A broken link has an href that starts with "#h." or "#id."

### Changed

- Removed Yes/No column CSS
- Combine <a> tags on import if they are consecutive and have the same href

### Fixed

- Add white line to the cover page for medium image landscape theme CDC
- Adding page breaks to headings overrides other CSS rules we might have

## [1.7.0] - 2023-02-07

### Added

- New theme: CDC Landscape DOP with a dark teal colour
- Cover images for CDC-RFA-CE-24-0068, CDC-RFA-CE-24-0120
- Add "References" to section titles that don't need section page
- Added utility width classes we can use for table headings

### Changed

- 65% first-column width for all tables after "Criteria" in Step 4
- Keep "Table: " in table captions
- Remove grey top border over tables in landscape mode
- Hardcode "Yes/No" table headers to 17% width
- Stop merit paragraphs from flowing into a new column

### Fixed

- Remove blue line from the cover page for Hero image landscape CDC

## [1.6.0] - 2023-02-06

### Added

- Added Subagency2
- Add classnames to subsection headers arbitrarily
  - In the UI, we allow page-breaks, column-breaks, or None
- Add visual indicators for page breaks and column breaks
  - Only apply page/column break rules for "@media screen"

### Changed

- Darker table borders
- Smaller vertical padding on header in portrait cover page
- Tables with captions all have bolded captions and a line on top
- Empty tables are 100% still and have 25px height rows
- Pale blue background on cover page footer in landscape mode
  - Still on cover page header in portrait mode
- Tables which are 4 columns or over will now always be large, even if they are empty
- Remove single column layout for Step 4
  - But make sure "criteria" tables are col-span: all
- In landscape mode, small tables without captions are 100% width

### Fixed

- Add HTML ids and classes to callout box headers
- Un-indent application checklist table cells with links in them
- Small tables with captions don't need col-span: all
- Single asterisks in table cells now escaped automatically

## [1.5.0] - 2023-02-05

### Added

- Find for metadata tags in the imported doc, add to meta tags

### Fixed

- Preserve p tags in imported table cells with more than 1 child
- CDC landscape medium image is normal again

## [1.4.0] - 2023-02-05

### Added

- Add 'white' and 'blue' variant of CDC logo
- Cover image for 0016
- Allow for checklists in tables (wow amazing)
- Added a "column-break-before|after" templatetag for landscape

### Changed

- Remove HHS logo from CDC medium image cover page
  - Stretch image across the page, so it is left aligned.
- HTML in imported tables now leaves p tags if the cell has ul/ol elements
- Return nofos by most recently created
- Change "page-break-after|before" paragraphs into hrs like Google does
- Add nofo.number to icon picking logic

### Fixed

- Use right colours for the CDC portrait medium image cover
- Links in table cells with icons
- Links in callout boxes are preserved
- Reimporting a NOFO re-calculates heading IDs
- Strip messy spans and NBSPs in tables on import
- Center cover images
- Allow saving content for callout boxes in the UI editor

## [1.3.1] - 2023-02-01

### Added

- Added images for next 3 NOFO covers

### Changed

- Refactor the templatetag for returning icons
  - Moved the logic out of the template and into the templatetag function

### Fixed

- Small fixes to wording of "Before you begin" page
  - Push down icon on "Before you begin" page to match other icons
- Strip weird whitespace from NOFO headers on import
- Creating HTML ids for sections and subsections is now atomic
  - This should stop empty HTML ids making it through

## [1.3.0] - 2023-01-31

### Added

- Add CMS theme (portrait + white + icons)

### Changed

- Standardize Opdiv + Agency + Subagency rules for cover page and basic info

### Fixed

- Say "SAM.gov" on Before you Begin page (not "Sam.gov")
- Remove col-span rules (CDC landscape) that no one asked for

## [1.2.0] - 2023-01-30

### Added

- Added "add_section_page" attribute to sections
  - Sections without section pages are not in the ToC and don't have custom section title pages
  - Add "no section page" sections to ToC
- Add Endnotes to the imported HTML
  - Decided to manually fix the weird endnotes
- Add success alert that links back to the edited subsection

### Changed

- Add new HRSA blue colour and swap it in as main theme colour
- Add new HRSA red colour for accent colour
- Top breaking pages on h3s
  - Allow H3s to be manually page broken

### Fixed

- Use Helvetica Condensed for the header and footer of HRSA theme
- Use the right icon colour for HRSA theme Before you Begin page
- Remove tagline when not needed
- Adjust tables with new HRSA colour
- Callout box alternative colours for HRSA

## [1.1.0] - 2023-01-24

### Added

- CDC portrait theme
  - Add blue and white variants
- Right column for callout boxes in portrait
- Split text for apply-by date on cover page
- Add "status" key to NOFOs
  - Status is now shown on NOFO index rather than coach
- Paragraph elements containing "page-break-before" function as manual page breaks
  - also: paragraph elements containing "page-break-after" function as manual page breaks
- Add page break checkbox to subsection headings
- Handle inline images
  - Add HRSA 017 images to the repo
- Add a way to change settings from the Django admin
  - Add a link to toggle this

### Changed

- Bumped heading levels to be closer to the USWDS
  - changed heading colours
- Added page breaks for h3s
- Add colspan: all to headings after the 'purpose' heading
- Remove "coach" from import flow, since we aren't using it
- Add 10px margin for p tags that follow p tags
- A bunch of last minute changes to heading sizes for the 0139
- Turned off "test" mode for printing
- Move callout boxes in right margin until after "Basic information"
  - Change h5 callout box titles to h4
- Remove grey top bar from tables in portrait

### Fixed

- Don't accept markdown files in the import anymore
- Fix: Don't add empty 'class' attribute to headings
- Fix: remove Google tracking information from URLs

## [1.0.0] - 2023-01-22

- First NOFO published! (not true in the end)

### Fixed

- Strip empty HTML tags so that NOFOs don't blow up on import

## [0.0.16] - 2023-01-19

### Added

- New combined CDC and HHS logo
  - Dropped the footer logo
- Callout box for the in-PDF nav instructions
  - Add PDF svg icon
- Alternate callout-box style
- Icons are revamped
  - Now all svgs are in the colour they will end up being displayed as

### Changed

- Fixed the border above tables, reduced spacing underneath
- Use NOFO title for PDF title
- Change body heading sizes to match typescale
  - Larger for h3, h4, h5
- CDC white theme uses vibrant blue everywhere in place of dark blue
- Even in the white theme, the "hero" cover page uses blue background and white text
- Use 50% width for section 4 (other than tables)
  - Same with "Before you begin" page
- Tables with 3 cols are "large", and have grey top bar
  - Before it was only for tables with captions
- Clean up header nav colours
- Standardize heading colours
- Underline page numbers in table of contents
- Increase space after lists
- Reduce footer padding: move it on top to separate footer from page content
- Prefer filling in column over balancing them

### Fixed

- Show arrow svgs on bolded li elements in table cells
- Contacts and support section is not a step
- Fix: Headings have less top spacing if they follow another heading

## [0.0.15] - 2023-01-17

### Added

- Added hero image cover style
  - Added new field to nofo: 'cover'
  - Built white and blue themes for CDC
  - HRSA theme needs review

### Changed

- Choose cover image based on directory path matching nofo number

### Fixed

- Reduce list left padding
- Callout box headings are h5s

## [0.0.14] - 2023-01-16

### Added

- Solve for nested lists during HTML import

### Changed

- Section 4 is now 1 column since it was too challenging
- Tables are now only large based on columns, not rows
- Table captions only if preceding text starts with "Table: "
  - Also add a horizontal bar above tables with captions
- Reduce spacing under headings
- Increase spacing under tables

### Fixed

- Fix: Application table styling for CDC 'light' theme
  - Also general table headings in 'light' theme

## [0.0.13] - 2023-01-15

### Added

- Solve for nested lists during HTML import

### Changed

- Shrink vertical margins of list items
- Larger left-padding for lists
  - Shrink vertical margins of lists themselves to match list items
- Slightly lessen table cell padding

## [0.0.12] - 2023-01-13

### Added

- Add new coach: Julie

### Fixed

- Fix: duplicate ids for headers being generated
- Fix: Run NOFO output through HTML validation
- Fix: Internal links broke (eg, Questions callout box)
- Fix: Subsection editing borken

## [0.0.11] - 2023-01-12

### Changed

- Use `pt` sizing for all font-sizes, which means a bunch of things shifted around

## [0.0.10] - 2023-01-11

### Added

- Added icon to Before you begin page
  - Before you begin page is in the table of contents

### Changed

- Smallen the font-size partout
  - Tables are even smaller
- New image for the cover page

### Fixed

- CSS for the application table makes it look like a sublist

## [0.0.9] - 2023-01-10

### Added

- Guess the opdiv, agency, subagency
- Add tagline and subagency to NOFO
  - No body text under the "Basic information" subsection is displayed
- Single cell tables become callout boxes
  - Add questions callout box with icon

### Changed

- Move callout boxes after the summary

### Fixed

- Fixed extra spaces that were showing up in links

## [0.0.8] - 2023-01-09

### Changed

- Watermark the image we're using so we don't publish it accidentally
- Add classes to tables based on row count as well as column count

### Fixed

- Swap unicode square for empty checkbox svg in "Application Checklist" table
- Swap unicode arrows for svg up/down arrows in table lists
- Remove empty list items from the DOM

## [0.0.7] - 2023-01-08

### Fixed

- Handle h6s, make them into h7s (ps once rendered)
- Find NOFO name and number if nested in spans
- Handle lists in table cells

## [0.0.6] - 2023-01-05

### Added

- Added a new theme: Administration for Children and Families (ACF)
- Guess the application deadline from the content

### Fixed

- New ACF logo svg file

## [0.0.5] - 2023-01-04

### Added

- Added a button to print the current NOFO to PDF
  - Only works in prod, not locally
  - Increased the number of gunicorn workers, otherwise I was blocking myself

## [0.0.4] - 2023-01-03

### Added

- Added icons to the table of contents page

### Fixed

- Fix styling for CDC NOFO (eg, table styles)

## [0.0.3] - 2023-01-02

### Added

- Added icons to the section title pages
- Add favicon

### Fixed

- View page looks more like rendered NOFO

## [0.0.2] - 2023-12-30

### Added

- Before you start page

### Fixed

- Subsections showing up out of order in prod

## [0.0.1] - 2023-12-29

### Added

- Added a changelog and a version number 👍
