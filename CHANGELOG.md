# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning since version 1.0.0.

## [0.0.8] - 2023-01-09

### Changed

- Watermark the image we're using so we don't publish it accidentally
- Add classes to tables based on row count as well as column count

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
