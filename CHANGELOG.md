# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic
Versioning since version 1.0.0.

## Unversioned

### Added

- Add "README" overview to the composer app

### Changed

- Use pencil icon for "Build your application" step
- Automatically assign "optional" to ContentGuideInstance subsections based on instructions
- Allow title casing for "Key Facts" and "Key Dates" subsections

### Fixed

- Fixed how instructions are associated with subsections when creating a ContentGuideInstance
- Explicitly mark "Style Bold" text as bold on import
- Don't duplicate sections and subsections by repeatedly confirming a draft NOFO

## [3.23.0] - 2025-12-10

### Added

- Add preview page for NOFO writers
  - Make sure preview page hides hidden sections and shows values for variables

### Changed

- Upgrade Python from 3.12.12 to 3.14.2
- Show a title derived from subsection.body for subsections with no name on Composer pages
- Prefill "key facts" variables with values from the NOFO Writer "details" page
- Add new style for variables with filled-in values
- Add "optional" and "hidden" labels to the "Guide to tags"
  - Auto-open "Guide to tags" when looking at a newly-created ContentGuideInstance
- Published content guides on "start" page now sorted by latest updated
- [Temporary] Prefill OpDiv field of "staging" ContentGuideInstances with "CDC" name
- Remove the lock icon from instructions for NOFO writers

### Fixed

- Add a fix for importing ContentGuides
- "Admin" link for superusers now works as expected for ContentGuideInstances
- Don't show the "hidden" field on subsection edit page for "variables" subsections
- NOFO Composer header links to admin/writer index depending on current url
- Hide edit buttons for locked, non-optional subsections
- Add html ID attribute to callout boxes with no headings
- Standardize table widths for composer index pages
- Standardize vertical spacing for the top of the section_overview page

## [3.22.0] - 2025-12-08

### Added

- Add Composer screen for NOFO Writer variable editing
- Add "Show/Hide" radios to subsection editing screen for optional subsections
  - Hide the rest of the inputs (except done) if user selects "hide" option
- Add subsection labels to writer section overview
- Add "new draft NOFO" alert to writer section overview for new drafts
- Add "Not started" alert to writer section overview for no-longer-new drafts

### Changed

### Fixed

### Migrations

- Add fields to ContentGuideSubsection:
  - variables
  - hidden

## [3.21.0] - 2025-12-06

### Added

- Added "Writer" flow
  - Writer dashboard
  - Writer "start" page: pick from published content guides
  - Writer "details" page: add your NOFO info
  - Writer "Yes/No" conditional questions
  - Writer section overview page
  - Writer subsection edit page for subsection.body
- Add "status" to ContentGuideSubsections
- Remove "enabled" from ContentGuideSubsections
- Add "expand all" button to section overview page

### Changed

- System Admin content guide creation routes are just for "staff" users
- Move "configure section" link to top of section overview page

### Migrations

- Add new fields to ContentGuideInstance:
  - activity_code
  - federal_assistance_listing
  - statutory_authority
  - tagline
  - author
  - subject
  - keywords
- Add new field to ContentGuideSubsection:
  - status
- Remove field from ContentGuideSubsection:
  - enabled

## [3.20.0] - 2025-10-31

### Added

- Add "Published" status to ContentGuides
- Add a publishing and unpublishing flow for ContentGuides
- Create a duplicate ContentGuide when unpublishing a ContentGuide
  - This is so that we can track version history of published ContentGuides

### Changed

- Show an "Archived" warning banner when viewing an archived ContentGuide

### Migrations

- Add new "published" status for ContentGuide objects
- Remove "active" and "retired" statuses for ContentGuide objects

## [3.19.0] - 2025-10-31

### Added

- Add right-aligned "Preview" button to Section overview pages in Composer
- Add "Optional/Required" field to Subsection edit field
- Add labels to the subsection edit radio button labels
- Add a "search NOFOs" page for superusers
- Add an "OpDiv" column to the admin view for a NOFO
- Add functionality for adding/deleting a Content Guide subsection
- Add "preview" page for Composer
- Added syntax highlighting to Ace editor for {variables}
- Add django-markdown-editor markdown extension for wrapping {variables} with spans

## Removed

- Remove "Yes/No" as an edit_mode option (replaced by "Required/Optional" field)

### Changed

- Add updated_display and created_display utils for consistent date presentation in index tables
- Detect presence of variables ("{var}") on composer import
- Change Composer tags to new format
- Scroll-to-top button now on multiple composer pages
- Allow "instructions" to be edited like a subsection body

### Migrations

- Add a new ContentGuideInstance model for NOFO writers
- Change up ContentGuideSection to point back to either a ContentGuide _or_ a ContentGuideInstance (but not both)
- Remove "yes_no" edit mode for ContentGuideSubsection
- Add new "optional" field to ContentGuideSubsection

## [3.18.0] - 2025-10-31

### Added

- Add "instructions" to matching subsections

### Changed

- Change labels on ConentGuideSubsection accordions to match prototype
- Use "locked" by default for new ContentGuideSubsections
- Hide the first ConentGuideSubsection of a group if:
  - it has no body
  - it has no instructions
  - it has the same name as the group

### Fixed

- Show "destructive" alert message when deleting a Content Guide

### Migrations

- Default new ContentGuideSubsection edit_type values to "locked"

## [3.17.0] - 2025-10-28

### Changed

- Updated list of coaches and designers
  - Retired coaches:
    - Aarti
    - Alex
    - Emily
    - Hannah
    - July
  - Retired designers:
    - Abbey
    - Emily B
    - Emily I
    - Jackie
    - Kevin
  - New coaches:
    - Laura
    - Sara D
    - Sara T
  - New designer:
    - Ben B

### Migrations

- Updated list of coaches and designers 👆

## [3.16.0] - 2025-10-24

### Added

- Add new app: "composer"
  - Add index view
  - Add import view
  - Add archive view
  - Add edit title view
  - Add "section" overview (with accordions)
  - Add subsection edit view

### Changed

- Cleaned up the martor text editor to look more like Annie's designs
  - Larger text
  - Active button is blue
  - Black border, squared edges

### Fixed

- Docraptor live mode should be a boolean, otherwise it is always true
- Removed trailing slash from the couple of URLs that (unintentionally) had them

### Migrations

- Add new "composer" data models: ContentGuide, ContentGuideSection, ContentGuideSubsection

## [3.15.0] - 2025-10-15

### Added

- Added a new app: "compare"
  - Compare will be "guides" renamed, because "guides" is no longer relevant

### Changed

- Invalidate all links to NOFO Compare for now

## Removed

- Removed all "guides" data and references
- Removed (unused) view for editing a CompareDoc subsection
- Remove all files related to "guides" app
- Remove (almost) all code related to DOCRAPTOR_LIVE_MODE
- Remove the view for NOFO import compare: we don't need it now that there is a "compare" app

### Migrations

- Remove all 'guides' models and data

## [3.14.0] - 2025-10-13

### Added

- Add new field to Document objects: "updated_by"
  - It stores the logged in user who made the most recent edit

### Fixed

- Remove "get all audit events" function that runs when editing a NOFO

### Migrations

- Add 'updated_by' val to NOFO and ContentGuide

## [3.13.0] - 2025-10-10

### Changed

- Downgrade Python from 3.13.x to 3.12.12

## [3.12.0] - 2025-10-03

### Added

- Add "NOFO Compare" to header
- Add "Step" title to side nav for NOFO Compare

### Changed

- Submit a support ticket footer link is visible for all users
- "Compare" is a new option in "NOFO Actions" drop down
- Change all references to "Content guides" to just say "Documents" on Compare side of things
- Many improvements to side nav for NOFO Compare
  - Highlight background colour of "ADD", "DELETE", "CHANGED" in side nav
  - "ADD" has blue outline now
  - Add sticky "Step" headers between the nav items in the side nav
  - Auto scroll side nav items as we scroll down the document
  - Keep the index number of nav items as we scroll past sections

### Migrations

- Add migration for new "from_nofo" field to ContentGuide objects

## [3.11.0] - 2025-09-30

### Removed

- Remove 'h7s' check from NOFO warnings
  - Since we upgraded DocRaptor, we have stopped manually tagging them, so there is no action to take anymore.
- Remove the "LIVE/TEST" toggle in the header
  - Now, the buttons themselves will download different kinds of PDFs

### Changed

- Show "check broken links" and "check heading errors" in a tabbed interface
- Remove "external links" option from NOFO actions menu. Add it to the "Things to check" section.
- Added new HRSA designer: Kerry

### Migrations

- Add migration for new HRSA designer

## [3.10.0] - 2025-09-16

### Added

- Add "Before You Begin" page setting for superusers and 1 other user
- Add "Nofo actions" dropdown menu, align with NOFO title
  - Move print buttons down below
  - Remove NOFO action buttons in blue box
- Add name of user who last updated a NOFO for more transparency

### Migrations

- Change 'sole_source_justification' boolean val into 'before_you_begin' ENUM

### Changed

- Remove "status" table on nofo_edit page, in favour of status picker in blue box.
- Move "↑ Top" button on NOFO Edit page to bottom right
- Rearrange print buttons, so that "Download PDF" always prints a 'live' NOFO

### Fixed

- Remove 1px outline from table headings in PDFs

## [3.9.0] - 2025-09-05

### Changed

- Use "pipeline: 11" which uses the newest Prince release, Prince 16
  - More details here: https://www.princexml.com/releases/16/
- Use USWDS sortable table for NOFO index instead of 3rd party library

### Fixed

- Show deletions in compare page in order
- Fix martor bug in admin console where subsection content could not be edited
- Fix next query param redirect on login
- Retrieving NOFO audit history is more efficient
- Remove JS code from "Page break" input on subsection edit page
  - Same functionality, but simpler implementation
- Fix bug on /compare page if no subsections are selected

## [3.8.0] - 2025-08-21

### Added

- Content Guides have "groups" now
  - Most users can only see content guides from their group
  - Bloom users can see content guides from all groups
- Add edit table to Content Guide edit page
  - Allows everyone to edit name
  - Allows bloom users to edit group
- Add site header admin link for Content Guides
- Add "created" and "updated" fields to admin view for a NOFO

### Changed

- Admin management panel for Content Guides is cleaned up
  - Looks a lot like the admin management panel for NOFOs does
- Demote heading sizes inside of sections with no title pages
- Application Checklist subsection only gets a page-break when in Step 5

### Fixed

- Fix site header admin link for Section pages
- Fix CSS for Application Checklist tables in Step 3
  - Some very specific CSS would only apply if the tables were in Step 5
  - Other too general CSS should only apply to tables in Step 5
- Show "Have questions?" callout box inline when it is _not_ in step 1
- Shave .5 px off small toc items now that we have seen some GS-exported templates

### Migrations

- Change help text for the "group" attribute of a BaseNOFO
  - It is now shorter and more general so that it works for both kinds of objects

## [3.7.2] - 2025-08-18

### Fixed

- Fix Word import bug by downgrading python-mammoth

## [3.7.1] - 2025-08-18

### Changed

- Use trash can icons for the "delete" column on Content Guides index
- NOFO status picker in blue box on nofo_edit page is now a select box (previously a link)
- Set full-width tables for this section is now a checkbox (previously a button)
- Change "active" nav link on compare page to blue
- Don't show "Have questions?" subsection in Content Guide

### Fixed

- Center trash can icons for the "delete" column on Content Guides index
- Add failure notification messages on Content Guide compare page if AJAX update fails (or partially fails)
- Fixed height for the "filenames" sticky header on diff page
- Disable "compare" buttons when no subsections are selected on Content Guide edit page
- Require 3 contiguous characters in heading before merging subsections in diff (previously, it was 1 character)
- Remove empty elements in diff side-by-side comparisons

## [3.7.0] - 2025-08-06

### Added

- Export a CSV list of changes from the Content Guide compare page

### Changed

- Change Content Guide index page to add more onboarding help
- Use filename without suffix as default Content Guide name
- Change site header to say "NOFO Boilerplate Compare" for "/guides" urls
- Completely redo Content Guide edit page
  - Add checkboxes to select/deselect which subsections to compare

### Migrations

- Add migration to change label of content_guide.title to refer to "name", not "title"

## [3.6.0] - 2025-08-05

### Changed

- Huge rewrite of HTML diffing engine
- Content Guide Compare page now supports a side-by-side diff or consolidated diff
- Content Guide import now defaults all "comparison_type" fields to "body"

### Migrations

- Add migration for setting all "comparison_type" fields to "body" on import

## [3.5.0] - 2025-08-05

### Added

- Implement image uploads for NOFO cover images
  - Users can now add, edit, or remove cover images their NOFOs
  - Superusers can see a listing of all images uploaded and which NOFO they belong to
- Add left-hand floating menu for in-page navigation of a NOFO's major (H2) headings
- Add button for users to apply full-width tables per section
  - Add emoji icon near the "Configure section" link if full-width tables are active
- Add cover image for CDC-RFA-DP-25-0014
- Add a page for superusers to see manually uploaded images
- Add an ADR (Architecture Decision Record) for which diff library we are planning to use

### Changed

- Find and replace functions can replace hrefs if formatted as links
- Replace multiple icons in a table cell, should it come to that

### Fixed

## [3.4.1] - 2025-07-14

### Added

- Add new nav breadcrumb for "Build your application"

### Changed

- Show "Find & Replace" and "Page breaks" button in review states
- Don't allow "Find & Replace" or "Page breaks" after publishing
  - Once published, NOFOs should generally not be edited
- Create "Edit" links for tables where all values are on 1 page
  - This means we remove the "Edit" links from table rows (for individual values)
- Change all app logs to JSON strings
  - Fixes very long multi-line console output in our app logs in prod
- Remove "import" and "export" buttons to NOFO models and audit events
- Set app timeout time in gunicorn to 90 seconds (was previously 900 seconds)

### Migrations

- Change "DOGE" status to "Dep Sec" (Deputy Secretary) status

## [3.4.0] - 2025-06-25

### Added

- Add cover image for DGHP FY25 NOFOs
- Add a new status: "DOGE"

### Migrations

- Add migration for new "DOGE" status

## [3.3.0] - 2025-06-25

### Added

- Add new theme: CDC Portrait (DGHP)
- Add new image(s) for HHS-2026-IHS-​IPP​-​0001​

### Changed

- DO find and replace subsection.name values on Find + Replace page
- DO NOT replace URLs on Find + Replace page
- More comprehensive error messages for section.name and subsection.name validation errors
  - Delete NOFOs with heading errors now, don't keep them
- Use "extract content" function in all find+replace types of interfaces
- NOFO title and short name are separated now
  - It made sense to group them before, but the "matched values" logic for the title field makes the double inputs really messy.

### Fixed

- Fix contextual button text for "Save" title, "Remove" page breaks, and "Replace" values

### Migrations

- Add migration for new DGHP theme

## [3.2.2] - 2025-06-16

### Added

- Add a warning message to ".rodeo" domain and ".dev" domain
  - Now that we have multiple versions of the NOFO Builder up, we want to prevent people from using the wrong one

## [3.2.1] - 2025-06-10

### Changed

- Removed django-version-number
  - This library was preventing us from upgrading Django beyond 5.1
- Updated most of the libraries:
  - Can't update markdown past 3.5 because of martor

## [3.2.0] - 2025-06-09

### Added

- Add "Find and replace" functionality
  - Allows you to find a term within the body of the NOFO and change it everywhere
- Add "Remove page breaks" functionality
  - Allows you to bulk remove page breaks you may have added
  - Note that the original 3 page breaks can't be removed this way
- Allow `<br>` tags in heading strings
- Add cover images for HHS-2025-ACF-OCS-EF-0177, ACF-OCS-EE-0118
- Add healthcheck endpoint at /health
- Add `db-migrate` command that can be run from built container
- Add "import" and "export" buttons to NOFO models and audit events

### Changed

- Consolidate Theme options (Theme, Cover, Icon style) on one page
  - This means we removed the 3 individual edit pages (and views, forms, etc)
- Temporarily stop logging audit events for model updates
- Temporarily set the app timeout time for 15 minutes
- Add the "Important: public information" subsection after _last_ matching subsection
- Show agency name (instead of subagency) on front cover for HHS-2025-ACF-OCS-EF-0177 and HHS-2025-ACF-OCS-EE-0118

### Fixed

- Show audit events for deleted subsections on the "All updates for NOFO" page
- Add AWS Load Balancer domain to ALLOWED_HOSTS
- Add current hostname to ALLOWED_HOSTS if using a private IP range starting with "10."
- Refresh AWS DB connection password periodically

## [3.1.0] - 2025-05-12

### Added

- Add configuration in settings.py for AWS database connection

### Changed

- Changed top-level app directory from `./bloom_nofos/` to `./nofos`
- IHS not-selected top nav link borders on section pages are white
- Tag docker images built with Makefile with latest git sha (or "latest")
- Show sticky flash message for edits on nofo_edit page

### Fixed

- match_view_url needed to be updated to look for uuid vals in urls

## [3.0.0] - 2025-05-07

### Changed

- Use uuids for NOFO.id, section.id, subsection.id
- [BREAKING] All NOFO urls are broken because of the database migration
- Use uuids for ContentGuide.id, section.id, subsection.id
- [BREAKING] All Content Guide urls are broken because of the database migration

### Added

- Add script to download all NOFOs and ContentGuides to a .csv

### Changed

- Makefile commands can be run from a Docker image

### Migrations

- Change id fields from integers to UUIDs for our main models
  - Includes: NOFO, Section, Subsection, ContentGuide, ContentGuideSection, and Subsection
- Remove the separate `uuid` field that is no longer needed

## [2.17.0] - 2025-05-05

### Added

- Added a Makefile so that we can lint and run tests and stuff

### Changed

- Dockerfile now uses python -slim image, not python -alpine image
- Dockerfile runs as non-root user, which is a security best-practice

### Migrations

- Add `uuid` field to NOFOs, Sections, and Subsections (and ContentGuide equivalents)
  - Note that the `uuid` field is not being used for anything yet, it just exists

## [2.16.0] - 2025-05-04

### Added

- Compare content guides
- Delete a content guide
- Use width classes for HTML tables on nofo_edit page
- Add cover image for HHS-2025-IHS-ALZ-0002
- Early concept of "change this everywhere" feature for application deadline
- 4 new cover images for ACF nofos:
  - hhs-2025-acf-ofa-fn-0015.jpg
  - hhs-2025-acf-ofa-zd-0013.jpg
  - hhs-2025-acf-ofa-zj-0014.jpg
  - hhs-2025-acf-ofa-zb-0109.jpg

### Changed

- Update Python version to 3.13.2
- Editing a content guide name from the nofo_edit page works better
- Show HTML table classnames on nofo_edit page and martor preview
- Don't show ADDs on Content Guide compare screen
- Don't show red lines on Content Guide compare screen
- "nofo_compare" function accepts a list of statuses to exclude
  - for example, we don't want to show the matches on the diff page

## [2.15.0] - 2025-04-18

### Added

- Add License: CC0 1.0 Universal (Public Domain Dedication)

### Changed

- Allow any number of "required strings" for content guide subsections
  - More correctly, up to 100

## [2.14.0] - 2025-04-14

### Added

- Added a real "edit" page for Content Guides
- Add in an "edit" page for Content Guide Subsections

### Migrations

- Update options for comparison_type of a Content Guide Subsection

## [2.13.0] - 2025-04-10

### Added

- Add completely new app: guides
  - Add basic functionality: we can import a content guide and edit its title
- Added a separate page for the NOFO exports
  - It is now possible to export for all users in your group
- Added a real "edit" page for Content Guides
- Add in an "edit" page for Content Guide Subsections

### Changed

- Change cover page "modifications" message for HRSA NOFOs
  - "Modified [date]. Review updates." → "Last modifed [date]. Review updates."

### Fixed

- Fix to allow unbolded "Other required forms:" string in appliction checklist
- Fix link to edit modification date in the subsection edit page for the mods table
- Fix for nested lists no longer importing correctly

### Migrations

- Add migrations for subclassing all of our Nofo models
  - a ContentGuide is related but not the same as a Nofo

## [2.12.0] - 2025-03-31

### Added

- Show audit events since modifying a NOFO on its own page
  - Also provide a markdown table that people can copy and paste
- Show the modification date in the subsection edit page for the mods table
- Add links in nofo_edit page "actions" box to new audit page and mods date
- Added initial version of RandyReport on account pages
  - The name will have to change for sure
- Add default column classes to HTML tables on import
  - Previously, it was just markdown tables
- Show previous heading level on "create subsection" page

### Changed

- Added new HRSA designers
  - Dvora
  - Jennifer
  - Marco
- Removed former HRSA designers
  - Doretha
  - Gwen
  - Shonda
- Removed former Bloom coaches
  - Idit
  - Mick
  - Morgan
  - Sara
  - Shane
- Also match "Annoucement type/version: Initial" when we slam that Modifications button

### Migrations

- Add migration for added/removed designers & coaches

## [2.11.0] - 2025-03-21

### Added

- Add 2 new statuses: Paused and Cancelled

### Changed

- When you save a subsection, the nofo_edit page loads at the top of that subsection
  - Same when you add a new subsection
  - Same with the "back" link
- Change index page to show 4 groupings: in progress, published, paused, cancelled
  - Remove "all", since probably nobody uses this
- "Add modifications" now finds all instances of "Announcement type: New" and changes them to say "Announcement type: Modified"

### Migrations

- Add migration for new statues

## [2.10.0] - 2025-03-19

### Added

- Added "Past versions" to the nofo audit history page
- Added a tooltip to the box emoji that explains the subsection is a callout box

### Changed

- Update Python version to 3.12.2
- "Live mode" timeout is 5 minutes
- Archived NOFOs can't be edited in any way
  - This includes hiding all the edit UI links

### Fixed

- Published NOFOs can't have subsections added or removed

## [2.9.0] - 2025-03-18

### Added

- Reimporting a NOFO saves a past revision of that NOFO from now on
  - We don't expose this in the UI yet, but it is now IMPOSSIBLE to wipe out your past NOFO by reimporting another NOFO over it

### Changed

- Temporarily set the "Live mode" timeout to 90 minutes
- Add rounded corners by default to all inline images
- Breadcrumb links now have a 5px top border
- Allow page break styles within tables
- Allow empty sections
  - No longer creating a default empty subsection when a section is created
- Error message tooltips match colour blocks at the top on nofo_edit page

### Fixed

- Remove "Jump to a step": we don't have links here anymore so they should go
- Normalize whitespace for MS Word AI-generated alt text

### Removed

- Super duper custom callout box from the front cover of HRSA-24-014
  - Replaced with the "modifications" setting

### Migrations

- Add "successor" field to NOFO model

## [2.8.0] - 2025-03-12

### Added

- Add new theme: "CDC Portrait (DHP)"
- Added "Login.gov" user attributes to admin page
- Add explanation for `429` links on the external links status table

### Changed

- Green button colour 🟢
- Lower word count for smaller "Key dates"/"Key facts" callout boxes (>= 80 chars, up from >86)
- Change top nav breadcrumb colours for section pages in DHP theme
- Rotate certs for login.gov staging
- Remove "local" cert: only 2 envs exist now
- Update style map for "w:" and "heading 8" styles
- Use MS form for feedback form (no longer using Airtable)

### Fixed

- Solve "page break" floating at the top in Safari
- Login page once again displays errors correctly

### Migrations

- Add migration for the new DHP theme

## [2.7.0] - 2025-03-05

### Added

- Add hint text to "Add page break?" radio buttons
- Adds login.gov as an authentication option

### Changed

- "Top" link is more visible on nofo_edit page
- "Preview" tab is more visible (blue background)
- Markdown Guide button is more visible (orange background)

### Fixed

- Don't apply default list-style-type styling to lists with "type" attribute

### Migrations

- Adds login.gov ID to users model

## [2.6.0] - 2025-02-27

### Added

- Added the status to the edit_nofo actions box, with a link to the "edit status" page

### Fixed

- Make sure the "Last changed" time on the NOFO edit page is in EST
- Fix the "compare" page for when there are NO changes

### Migrations

- Added a new theme: 'portrait-cdc-dhp'

## [2.5.0] - 2025-02-26

### Added

- Add new "{id}/compare" route for comparing a new NOFO document to an existing one
- Add a "modifications" status to published NOFOs:
  - Only "published" NOFOs can be modified
  - There is a 'modified' message on the cover page
  - There is a new setting in the NOFO edit page allowing you to set a modifications date
  - A "Modifications" section is added to the end of your NOFO:
    - This section shows up in the table of contents, but it does not have a section page
    - It comes with 1 subsection: a table for you to list changes and the date
      of those changes

### Changed

- Use a MS 365 form for feedback instead of a Google Form
- Breadcrumb links are no longer clickable (instead, they are just visual indicators)
- When you open a NOFO Builder PDF in Acrobat, the Bookmarks tab will be open by default
- "Important: public information" callout box will appear after specific subsection names in section 3 of new NOFOs
  - If no matching subsection names are found, it will appear at the end of section 3 like normal

### Fixed

- Fixed a bunch of things in the diff interface:
  - Use full-word diffs, so `<del>January</del><ins>March</ins>` instead of `<del>Janu</del><ins>M</ins>ar<del>y</del><ins>ch</ins>`
  - Show linebreaks that exist in body content (easier for lists, for example)
  - Reclassify whitespace-only changes as "MATCH" not "UPDATE" (in markdown, they generally don't matter)
  - Hide the "Basic information" subsection because it duplicates information
- Fix for more list styles that were not importing correctly ("List Bullet1, Bullet 2", etc)

### Migrations

- Added a new attribute to NOFO model: "modifications", a datetime object (default null)

## [2.4.0] - 2025-02-13

### Added

- Add classes to Table of Contents based on number of items
  - The idea is to shrink the table of contents a bit if lots of items show up
- Add a new icon for "award" (only for 2 CDC NOFOs for now)
- Add 2 new images for CDC-RFA-CE-25-0114-b
- Add cover image for CDC-RFA-CK-25-0125 and CDC-RFA-JG-25-0178
- Add inline images for CDC-RFA-CE-25-0114
- Can use 'page-break' to add a page-break in markdown body
- Add confirmation page for re-importing a NOFO if the IDs don't match up
- Add "Important: public information" callout box to section 3 of new NOFOs
- Adds Login.gov as an authentication option

### Changed

- All page break visuals say "page-break" now, dropped the "-before", "-after"
- In the nofo section editor, page breaks added to a section now say "page-break"
  - Previously, it was just a dashed line, but nobody knew what that meant
- Loop through sections to create breadcrumbs
  - Support "Understand Review, Selection, and Award" as a new section name
- Preserve existing page breaks when a NOFO is reimported
  - Note that this is a best-guess effort: if subsections are renamed, page breaks can't be preserved
- DocRaptor IPs can now be updated by superadmin users
- Requires Login.gov certs and ENV vars to be set for devs.

### Fixed

- Retry failed external link requests so that more of them will show up green
- H7 warning notice at the top of a NOFO now handles h7s in markdown body as well
- Preserve heading links for h7 headings (other heading levels worked before, but not h7s)
- Remove unneeded nested lists "li > ul > li" for BYB page and appendices
- Page breaks were not possible to add to subsections without a heading
- page-break-after was briefly not working
- Small ToC links are all the same colour

### Migrations

- Add "Important: public information" subsection to non-archived, non-published NOFOs
- Adds login.gov ID to users model

## [2.3.0] - 2025-01-17

### Fixed

- NCIPC Teal theme link colour is now darker to meet AAA contrast

### Migrations

- New theme: NCIPC Blue
- Rename previous theme: DOP → NCIPC Teal

## [2.2.0] - 2025-01-14

### Added

- Add script for exporting reimport audit events
- Add cover images for:
  - CDC-RFA-CE-25-0114
  - HHS-2025-ACF-IOAS-OTIP-ZV-0002
  - HRSA-25-020
  - HRSA-25-021
  - HRSA-25-029
  - HRSA-25-033
  - HRSA-25-082
- Add "highlight-strong" class to shared CSS
- Add more style map rules for bullets
- Added "Link text" to the external links page
- Added default subsection and order behavior to Section model

### Changed

- Styling changes to external links page for acommodate more cols
- Style maps are better at handling lists when importing .docx files
- Before You Begin page uses 'sole_source_justification' to show alternate version, not a specific NOFO ID

### Fixed

- Fixes issue where archiving a NOFO would fail due to validation checks requiring at least one section
- Links starting with "file:///" should be flagged as broken links
- Hotfix to make viewing content tables easier in edit view
- Return sections by "order" for nofo.get_first_subsection()
- Return sections and subsections by "order" in the API response

### Migrations

- Add 'sole_source_justification' boolean field to Nofo objects

## [2.1.0] - 2025-01-10

### Added

- Add cover image for HRSA-25-044, HRSA-25-066

### Migrations

- Add "Jana", our new NOFO Designer
- Add "Shonda" and "Lynda" as HRSA Designers

## [2.0.0] - 2025-01-10

### Added

- Add heading styles for H7s in edit and preview modes
- Add cover image for HRSA-25-007, HRSA-25-042
- Add 2 inline images for HRSA-25-066
- Add list style for quint nested lis
- Add new error messaging for NOFO validation
- Added validation rules for NOFO models

### Changed

- Improve validation and error handling for section titles and subsections
  - [BREAKING] Make Section model's name and html_id fields required
  - [BREAKING] OpDiv: required in NOFO document, or else they won't import
  - [BREAKING] Nofos must have a section
  - [BREAKING] Sections must have a subsection
  - Add custom HeadingValidationError class for clearer error messages
  - Add data migration to populate empty fields with valid values
  - Update tests to handle new validation requirements
- Change heading sizes in edit mode
- Remove "Fix in Word and reimport." note in warning message
- Change ACF heading styles
  - h1s: 36 pt, 700
  - h4s: 600
  - h7s: 11.5pt, 600, #264a64
- Change how sublist headings are identified in application checklist
  - headings with links must also not have a checkbox
  - cells with "Narratives" are headings now
- All tables in appendices are full-width
- Speed up "create_nofo" function
  - Batch create sections and subsections in "\_build_nofo"
- All links are blue now, not black
- White background in svg circle in HRSA light

### Fixed

- Fix for links after colons in callout boxes
  - Visually, they would look like "Key:Link", now they look like "Key: Link"

### Migrations

- Require "name" and "html_id" for section
- "nofo.title" 250 chars or less
- "section.title" 250 chars or less
- "subsection.title" 400 chars or less

## [1.42.0] - 2023-12-24

### Added

- Add cover image for CDC-RFA-IP-25-0007
- Add cover image for CMS-2V2-25-001
  - Also add inline images
- Add utility classes for different list counters

### Changed

- Updates to CMS theme:
  - Fix background and text colour for cover page
  - "Standard" icons are blue
  - Tighter line-height for h5s
  - Smaller, bolder h7s
- Speed up "add_headings_to_nofo" function
  - Precompile regex patterns for heading ID substitution
  - Batch update sections and subsections

### Fixed

- Don't demote h7s, since there is no lower heading level

## [1.41.0] - 2023-12-18

### Added

- Add cover images for HSRA-25-032, HSRA-25-075, CMS-3Y3-25-001
- Add a new custom CDC theme: CDC (IOD)
- Add new "staging" group for users to test NOFO Builder safely
- Add new API endpoints for importing and exporting NOFOs

### Changed

- Find ranges for numbered sublists: include "8 to 15." and "8 — 15." (emdash)
- H7 styling in ACF now bold and slightly smaller (12.5pt)
- Add links are CMS blue (no more links in the theme colour)

### Migrations

- Add new user group: "staging"
- Add new theme: "portrait-cdc-iod"
- Make some fields nullable: "filename", "inline_css", "subagency2"

## [1.40.0] - 2023-12-16

### Added

- Add new command for downloading NOFOs with published times
- Add new command to count all section name lengths and subsection name lengths
- Add inline image for CDC-RFA-25-0061
- Add cover image for HRSA-25-019
- Add cover image for HHS-2025-ACF-ECD-TH-0106
- Add cover image for HSRA-25-071

### Changed

- Decompose instructions boxes that start with "Instructions for new nofo team"
- Made the import button more dynamic

### Fixed

- Loading gif also used on re-import page
- bug: since adding replace_links, replace_chars was not being applied

### Migrations

- Add one new coach ("Sara") and 1 new HRSA designer ("KieuMy")

## [1.39.0] - 2023-12-04

### Added

- Add loading state to 'import' pages with little galloping horse gif
  - Import doc files and import JSON files
- Add new command for downloading all 'print' audit events

### Changed

- Setting "Live" mode is only good for 5 minutes
  - After 5 minutes have gone by, it will revert to "Test" mode again

### Fixed

- Creating superusers from the terminal doesn't set the 'force_password_reset'
  flag
- Reduce horizontal hit area for radio buttons (was previously full-width)
- Link to NOFO in success message for JSON import
- Remove borders and left padding from `<fieldset>` elements by default

### Migrations

- Migrate some audit events with string values for "changed_fields" to valid
  JSON

## [1.38.0] - 2023-11-29

### Added

- Added ability to export and import NOFOs as JSON
  - Only superusers can do this!
- Add script to pull links from all non-archived NOFOs
- Add inline image for CDC-RFA-JG-25-0055
- New cover images for HRSA-25-036, HRSA-25-080
- Add dash (⁃) as bullet for all quadruple nested bullets

### Changed

- Cloned NOFO statuses automatically set to "draft", regardless of original
  status
- Condense Before You Begin page for NOFO: CDC-RFA-PS-25-0008
  - This will be a sole-source thing, but for now it's just for this one
- Tighter line-lengths for `<a>` tags in the application checklist table
  - Helps to visually distinguish several multi-line anchor tags in the same
    cell

### Removed

- Remove admin-only view to export all NOFO links
  - We used this once ever

### Fixed

- Replace "www.grants.gov/web/grants/search-grants.html" with
  "grants.gov/search-grants"
- Replace "www.grants.gov/web/grants/forms/sf-424-family.html" with
  "grants.gov/forms/forms-repository/sf-424-family"
- Replace "www.cdc.gov/grants/dictionary/index.html" with
  "www.cdc.gov/grants/dictionary/index.html"

## [1.37.0] - 2023-11-21

### Added

- 2 new HRSA designers, and 1 new Bloom Coach
- 2 new images, for HRSA-25-70, HRSA-25-76
- Support src="data:..." images in the NOFO Builder 🖼️
- Add "Heading level" `<select>` to subsection edit page
  - Remove Heading level hint text from Subsection name label
  - Remove "h2" from the options from heading level
    - H2s are for Sections, not Subsections

### Changed

- Make text in right hand callout box smaller if too many words
- Titles with 166 chars or more now get the smaller classname
- White table borders are now 3px instead of 2px
  - More emphasis on the line, basically

### Fixed

- Mention the name of the preceding subsection on the 'New subsection' page
- Do not bold paragraph in th that follows a strong
- Add 33% and 66% width classes
- Tables with no rows no longer crash the app

### Migrations

- "Stephanie V" instead of "Stephanie" for HRSA

## [1.36.0] - 2023-11-19

### Added

- 2 new HRSA designers, and 1 new Bloom Coach

### Migrations

- (Same) 2 new HRSA designers, and 1 new Bloom Coach

## [1.35.0] - 2023-11-18

### Added

- Added a new "migrate" step to migrate the database before deploying the app
  - migrate waits for the tests to pass
  - deploy waits for migrate to pass

### Changed

- Smallen the font size (even more) for NOFOs with very, very long titles (> 230
  chars)
- Add bold font-weight to the first paragraph in a table heading

### Fixed

- Only deploy the app if the "test" job finishes successfully
  - Previously, it would always deploy

### Migrations

- Update some of the field descriptions on the NOFO object

## [1.34.0] - 2023-11-18

### Added

- Added (small) cover image for HRSA-25-026

### Changed

- Always show user permissions in the same order on the admin screens
- Force emails to lowercase when new users are created
- Automatically lowercase email addresses during login attempts

### Migrations

- Default "force reset password" field to True for new users

## [1.33.0] - 2023-11-18

### Added

- New alert box for NOFOs that have H7 headings
  - H7 headings need to be manually fixed in the PDF
- New column for the heading level in the nofo_edit view
  - Slight change to subsection_edit page to match new heading tag styling
- Add image for CDC 0047
  - Add alt image for CDC 0047
- Automatically assign all new PEPFAR NOFOs to cdc-pepfar.jpg

### Changed

- Smallen the font size (again) for NOFOs with very long titles (> 170 chars)

### Fixed

- Preserve bookmark targets that have been getting stripped out
- Convert literal asterisks to `&ast;` inside of HTML PARAGRAPHS in table cells
  - We did this for lists already but paragraphs need the same treatment
- Criteria tables with a page break or table in front of them should also be
  full-width

## [1.32.0] - 2023-11-09

### Changed

- Autodeploys from GH Actions

## [1.31.0] - 2023-11-08

### Added

- Add new view to verify individual external URL responses
- Add button to copy list of broken links on nofo_edit page
- Add new coaches and designers
  - Remove a couple of retired coaches
- Add audit events for printing, importing or reimporting a NOFO

### Changed

- Un-bold paragraphs in table headings
  - Means that multi-line table headings are unbolded by default
- Remove stroke on CDC logo svg
- Add CSS class to add bullets to lists
- "Adam 👀" is now "Ready for QA"
  - We are cleaning up our act, to my enormous disappointment
- Change the string values for the cover image names

### Fixed

- H7 elements are properly recognized as subsections
- Add migration to fix previous "PRINT..." audit events that were not JSON
  formatted
- Convert literal asterisks to `&ast;` inside of HTML lists in table cells
- More left padding on callout box lists that are NOT in the right hand column
- More specific CSS selector for application table divs
- Application list checkbox cells that are not sublists have bottom borders
- "Adam 👀" status needs yellow highlight background

## [1.30.0] - 2023-10-28

### Added

- Convert 'Heading 7' styles from Word
- Add cover image for CDC-RFA-DD-25-0157
- Add cover image for CDC-RFA-DP-25-0024
- Add cover image for HRSA-25-068
- Add cover image for HRSA-25-025
- Add cover image for HRSA-25-027

### Changed

- Allow users to remove subagency and subagency 2
- HRSA tagline is now HRSA blue!
- Show subagency under the logo on the small image page, not subagency 2
  - For HRSA, show the agency, not the subagency
- Reimporting a NOFO that already has a cover image won't replace the image
- Change heading links on NOFO view page
- "Other required forms" and "attachments" are sublist headings in application
  table

### Fixed

- Restructure HTML in the Application Checklists for better styling
  - Previously, I was using a CSS hack because I didn't have enough elements to
    style
- 'Criterion' tables are always small
- Find ranges for numbered sublists
  - Match for "8-15.", "8 - 15.", "8 through 15."
  - Remove the border under "Attachments"
- ids inserted using markdown attributes should not show up as 'broken links'
- Added more known styles for the mammoth style map

## [1.29.0] - 2023-10-19

### Added

- Ignore single-celled tables that include the phrase "-specific instructions"
  - These are new instructions boxes
- Add cover image for CDC-RFA-DP-25-0012

### Changed

- Add "TEST" to the audit event for a printed NOFO if we are in test mode

### Fixed

- Add broken bookmark links to alert box
  - Add styling for broken bookmark links
- Update DocRaptor env var
- Fix CDC logo text for all backgrounds in portrait mode
- Hide "alt text" row when cover style is text only
- Manually return a 500 response when an exception is raised by requests lib

## [1.28.0] - 2023-10-11

### Added

- Link in the footer to CHANGELOG so latest changes are visible
- Manually add audit event when printing a NOFO
- Add image for HRSA-25-67
- Add image for HRSA-25-63
- Add default column widths for application checklist
  - Col 1: 45%, col 2: 40%, col 3: 15%
- Add link to submit a support ticket for HRSA users
- Add cover_image and cover_image_alt_text fields
  - If there is a cover image, then the 'alt text' field shows up on nofo_edit
    page

### Changed

- Use Firefox user agent for the "check links" page
- Essential change to favicon
- Change CDC blue to `0057b7` instead of `005eaa`
- Tables with "Criterion" header are table--small

### Fixed

- Fixed: Wrap all text that says "de minimis" with `<em>` tags
- Show order number of subsection with no name in alert boxes for broken links
- Case-insensitive match when looking for hrefs to convert to new header ids
- Preserve line breaks in table heading cells
- Add missing svg images from USWDS

## [1.27.0] - 2023-10-03

### Added

- Highlight improperly nested headings on the "nofo_edit" page
  - Test for:
    - Consecutive headings at the same level, no text between
    - Consecutive headings where second is larger, no text between
    - Subsequent headings that skip levels, with text between
  - Color them red, add a light red background, add a tooltip with error message
- Highlight broken links on the "nofo_edit" page
  - Color them red, add a light red background, add a tooltip
- Add little "copy" icon button that copies ids to the clipboard
  - For section ids
  - For subsection ids
  - Add "#" to beginning of ids
- Add uswds JavaScript files to the base theme file (not the NOFO theme file)
  - The motivation for this is so that we can get tooltips to work
- Add a group filter ("Bloom/All") for Bloom users on NOFO index

### Changed

- Added "re-import to fix" instruction to alert boxes
- No bueno was not bueno
- Add default width classes to markdown tables with 3,4,5 cols
- Updated column headers on NOFO index table
- "Top" link on nofo_edit page is always visible
  - Appearing and disappearing was causing issues
- Rename "NOFO data" to "Basic information"
- Remove "Basic information" from "Step 1"
- More if/else logic to support 2 application dates 😖

### Fixed

- Fix outline for back link on nofo_edit page
- Reduce left-hand spacing for bullets in callout boxes
- Make sure large tables have full-width table styles applied

## [1.26.0] - 2023-09-13

### Added

- count_updates script can optionally show user ids for individual nofos
- Add "archived" field to NOFOs
  - Don't show archived NOFOs on NOFO list page
  - Add warning banner for archived NOFOs to "view" and "edit" pages
  - Deleting NOFOs now just archives them
  - Archived NOFOs can only be seen by Bloom users

### Changed

- Try to keep callout boxes all on one page
  - Increase right padding for callout boxes
  - Move them up
  - Reduce vertical padding
- Uniform link colours matching the USWDS
- Accept numbered sublists in application checklist

### Fixed

- "Logout" link was broken, so it's fixed
- "Preview" link in markdown editor has "USA Blue" link text
- Specify exact Python version in Dockerfile
- Fix 2 broken cover images
- preserve_heading_links function now accounts for multiple links preceding
  headings
- Fix for heading links where the HTML id includes an ampersand

## [1.25.0] - 2023-08-27

### Added

- Add 'section_detail' page to add and remove subsections
  - 'section_detail' page must be manually visited for now
- Added mailto link to the 400 page
- Add cover image for "cdc-eh-25-011"
- Add cover image for "rfa-ce-25-149"
- Add a command line function can return all edits per nofo or for all nofos
- Sections called "Modifications" should also not have a cover page

### Changed

- Updated most of the libraries:
  - Can't update markdown past 3.5 because of martor
  - Can't update django past 5.0.8 because of django-easy-audit
- Change the floating header on NOFO edit page
  - Print buttons float now
  - Added "add or remove subsections"
  - Better little icon for the "top" button
- Changed URL patterns for subsections (include the section id as well)
- Very small update on "Before you begin" page
- Smallen cover page title if longer and there is an image
- Use svg arrows for the back links, not unicode arrows

### Fixed

- Automatic Endnotes "h1" heading would mess up documents where h2s are the
  highest heading level
- Fix an if condition that was broken for callout boxes
- Make sure footnote/endnote in-text refs are <sup>-wrapped
  - This means that footnote will work for callout boxes and on the "edit" page
- Smaller list number sizes for endnotes

## [1.24.0] - 2023-08-09

### Added

### Changed

- Accept NOFOs with H2s as the highest-level heading
  - No longer demote headings in these NOFO documents
- Replace weird unicodes in the application table checklist on import
  - No longer have a list of acceptable substitutes in
    "replace_unicode_with_icon.py"
- Fix reading order for right col callout boxes
- Default cover page for HRSA NOFOs now the text theme
- Reimporting a nofo changes all the "Nofo data" as well
  - Set the nofo.title as well
  - Re-importing redirects to edit page, not index page
- Remove tables that start with the phrase: "Instructions for NOFO Writers:"
- Add "br" after 'Have questions?'
- Put subsection 'other actions' into a little accordion box
  - We don't want people to click them accidentally

### Fixed

- Make sure "preserve_links_in_headings" finds all links in headings
- Fix for erroneously replacing heading IDs which were subsets of other ids
- Preserve existing links to table headings when importing documents
- Fix for "preserve_table_headings": also include empty links preceding headings
- Remove empty "absolute--right-col" wrapper for sections that don't need it
- One more format fix for the "Have questions?" callout box
- Preserve 'endnotes' as well, not just 'footnotes'
  - Make sure that endnotes get `<sup>`-wrapped as well
- Make sure that inline CSS makes it in properly

## [1.23.0] - 2023-07-26

### Added

- Add a user-visible route to delete a subsection
- Filter the available THEMES by a user's group
- Filter the available NOFO DESIGNERS by a user's group
- Admins can now clone a NOFO
- Show last login time for user accounts on admin screen
- Add the error reporting form to the 500 page
- Add JS file to sort the nofo index table
  - Added a comment in the pyptoject.toml file about it

### Changed

- Redirect logged-in users from the homepage to the index page
- Import look for heading/broken links that look like `#_`
  - "preserve_heading_links" function more inclusive about what ids it preserves
  - "find_broken_links" function more inclusive about what ids it preserves
- Disabled input for subsections with no subsection name
- Broken internal links widget works properly now
- Footnote ids are preserved during initial HTML import for DOCX files
- Remove "Group" from Nofo index page for non-bloom users

### Fixed

- When replacing IDs in our "preserve_heading_ids" method on import, find and
  replace for old links
- Add more stylemaps to my mammoth import config
- Deleting a NOFO is chill now (no 404 error)
- Solve layout bug where buttons next to each other wouldn't be rounded
- Add empty value to nofo designers
- Fixed permissions issue with viewing subsections
- Migrate old nofo.designer value in previously published nofos
- Application checklist boxes become umlauts sometimes
- Remove Normal_0 style map

## [1.22.0] - 2023-07-12

### Added

- Add "group" to NOFOs (represents the OpDiv the NOFO is associated with)
- Add "group" to users (represents the OpDiv that the user comes from)

### Changed

- Update Python version to 3.11.9
- Allow 'bloom' users to change a NOFO's group
- Add read-only group to user table
- Add read-only group to nofo index table and nofo edit page
- Set NOFO group to user's group during import
- Non-bloom users can only see NOFOs from their group

### Fixed

- Revert mammoth style maps for bullets
  - Mammoth actually converts them properly, so I am ignoring ListParagraphs
    explicitly
- Always return the first subsection by order in the nofo template
- Remove GroupAccessObjectMixin from the Detail view to allow for printing (we
  have other restrictions on that one)
- Remove "start_server.sh" file to resolve Dockerfile warning

## [1.21.0] - 2023-06-26

### Added

- Major release: Uploading .docx files are (mostly) equivalent to the .html
  imports
- Add admin-only route to export all external links from a NOFO
- Add CSS class for light blue table backgrounds (previously this was an inline
  fix)
- Add new theme: CMS blue
  - Works in no-text mode or hero image mode
- Reconstruct footnotes for the .docx imports
- Added "filename" field to store filename along with the NOFO

### Changed

- Do not remove headers from tables with a rowspan other than one
- Clean up table output in markdown conversion
  - Pretty print the HTML and remove classnames when table HTML is used
- More style maps added based on an early version of HHS-2026-ACL-AOD-DDUC
- Ignore "FootnoteReference" warning messages when importing .docx files
  - There is currently no way to build style maps for these
- Insert a "next page" link before the running header nav
  - Hopefully this allows screenreader users to avoid that focus trap
  - Update: removed this

### Fixed

- Change on-screen text around file importing to refer to .docx files before
  .html
- Wrap soup in a body tag if there isn't one.
- Remove classes in HTML uls and ols
- Catch broken links that look like "about:blank"
- Add endnotes header to the .docx files as well
  - Do not add an Endnotes header if one already exists
- Fix asterisks causing unintentional italics
- Do not swap out icons if table cells contain multiple instances
- Fix for weird lists that look like this:
  `<ul><li><ul><li><ul><li><ul><li>Item</li></ul></li></ul></li></ul></li></ul>`
  - We were seeing them in docx imports
- Add tbody tags to tables imported from .docx files
  - Previously all the cells became `<th>` elements, in a huge `<thead>` (with
    no tbody)
- Unwrap empty `<sup>` tags, which are lying around in Word exports for some
  reason
  - Also unwrap empty `<em>` tags
- Broken heading/bookmark links from docx files show up on the edit page
- Bookmark links followed by a paragraph are preserved
  - Add classes for bookmark levels
- Heading links for docx documents are preserved
- Alt text for the CMS logo is fixed
- White logo for the CMS logo shows up in browser PDF readers
- If consecutive lists don't have classnames, do not join them.
- Add a fix for callout boxes imported from .docx files

## [1.20.0] - 2023-05-20

### Added

- Allow .docx imports
  - Using a library called mammoth to covert .docx files to HTML
  - Created a new constance-configurable variable called "strict mode" for .docx
    imports
  - Added a list of known styles for the mammoth style map
- Add a Prince role mapping to the CSS theme
  - Basically, we are mapping `div[role="heading"]` to a paragraph tag
- Add information on creating users to the README
- Try adding a bookmark heading level 7

### Changed

- Use PNG logos for ASPR on cover page
- Consolidate the coach and designer onto the same page
- Strikeout & disable print buttons on localhost
- Colour changes for the ASPR theme
- Updated README with improved setup instructions

### Fixed

- Better new CDC logo

## [1.19.0] - 2023-04-25

### Added

- Add "superuser status" to the users add + edit page
- Add thin icons now that somebody has asked for them
  - Only visible for NOFOs using the ACF theme
- Added new button group for "View PDF | View HTML | Download PDF"
- Allow images as background of section pages
  - Don't actually add the image in CSS, we will do that using inline CSS for
    now
- Wrap all text that says "de minimis" with `<em>` tags
- Cover image for CDC-RFA-DP-24-0025
- Add section page background images for 0025
  - Add black and white images to test
- Add new CDC logo

### Changed

- Harmonize the page-break-befores and make them searchable
  - page-break-after
  - column-break-before
  - column-break-after
- Change the header nav
  - Add a link to the admin backend for the NOFO for superusers
  - Remove the "Logout" link which nobody uses

### Fixed

- Menu doesn't disappear until ~680px now, not 1024px like before
- Application checklist borders weren't computing properly for ballot boxes,
  hmmm
- Unwrap "empty" spans instead of decomposing them
  - Spaces were getting missed sometimes, now they aren't
- "combine multiple links" function now joins 3 or more links in a row if needed
  - previously, it would only join 2 at a time

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
- Lengthen final list items that don't need the avoid-page-break class to 85
  chars

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
- Move the CMS logo down so that it aligns better with text baseline on cover
  page
- Clean up cover page for ACF medium image
- Show the right heading level for callout boxes with headings
- Never show "Contacts and support" sublinks in ToC, no matter the
  capitalization

## [1.16.0] - 2023-03-25

### Added

- Added cover image for HHS-2024-ACF-ACYF-EV-0039
- Added (back) the little callout box for HRSA 14

### Changed

- Use "Write" in the running nav for section 3 if the section name inclues
  "Write"
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

- For ACF Nofos, move the "Adobe Reader" annoucement to the Before you Begin
  page
  - For all Nofos except HRSA
- Two more href patterns for the "broken links" widget: "/" links and google
  docs domains
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
- Tables which are 4 columns or over will now always be large, even if they are
  empty
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
  - Sections without section pages are not in the ToC and don't have custom
    section title pages
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
- Paragraph elements containing "page-break-before" function as manual page
  breaks
  - also: paragraph elements containing "page-break-after" function as manual
    page breaks
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
- Even in the white theme, the "hero" cover page uses blue background and white
  text
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

- Use `pt` sizing for all font-sizes, which means a bunch of things shifted
  around

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
