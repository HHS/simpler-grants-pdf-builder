# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning since version 1.0.0.

## Unreleased

### Added

- Callout box for the in-PDF nav instructions
  - Add PDF svg icon
- Alternate callout-box style

### Changed

- CDC white theme uses vibrant blue everywhere in place of dark blue
- Even in the white theme, the "hero" cover page uses blue background and white text
- Use 50% width for section 4 (other than tables)
  - Same with "Before you begin" page
- Tables with 3 cols are "large", and have grey top bar
  - Before it was only for tables with captions
- Clean up header nav colours
- Standardize heading colours

### Fixed

- Show arrows on bolded li elements in table cells

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
