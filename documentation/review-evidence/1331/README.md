# Note pagination verification

An invented boundary fixture used the Builder print stylesheet and the same
pipeline 11 / PDF/UA-1 options as Builder. The provider's public test mode
identified Prince 15.1 and watermarked the pages. No real document, production
credentials, or production application was used.

- Before: the [table on page 1](before-page-1.png) and [note on page 2](before-page-2.png) split.
- After: the [table and note both appear on page 2](after-page-2.png).

The fixture deliberately leaves just enough room for the table but not its
note. This verifies the break rule in that case; forced page breaks, custom
CSS, and material too tall to fit on one page can still split content.

Chrome computed-color check: the shared stylesheet plus each of the 21
configured theme variants, in screen and print media, passed 4.5:1 for
ordinary notes, table header notes, and notes in shaded body cells. The
lowest observed ratio was 4.61:1. Custom document CSS was not included.
