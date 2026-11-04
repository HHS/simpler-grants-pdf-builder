# HHS footer identifier validation

Above the existing utility links, the shared application footer includes the existing HHS seal in white on
Builder's dark blue (`#00345e`), with a 48px crest and 4px vertical margins, “HHS.gov,” and the official-website statement
linking to HHS. This follows the identifier masthead at
https://simpler.grants.gov/ without copying its green palette.

- [Desktop, 1280px](after-1280.png)
- [Mobile, 320px](after-320.png)

These are local renders of the real shared Django application shell with sample
account data and empty page content. The agency link is focused to show its
keyboard outline. No live or production account data is used.

`tests/js/footer.browser.cjs` checks authenticated and anonymous layouts at
320, 375, 480, 768, and 1280 pixels: no horizontal overflow, preserved footer
navigation, one agency identifier, the HHS destination, logo and background
colors, and keyboard access with a visible focus outline. Django government
banner tests cover the identifier on login, signed-in index/account, and public
readability pages, and its absence from the NOFO document view.

Editor Tasks were reviewed; this adds agency identification only and does not
change import, editing, review, preview, or export instructions.

Validation results:

- All 15 browser layout scenarios passed.
- All 23 government-banner and public-readability tests passed.
- All 61 JavaScript unit tests passed.
- Black/isort checks passed for the modified Python test.
- The broader `bloom_nofos` suite has three local failures (Constance admin
  breadcrumbs and two authenticated readability upload tests). Running the
  same tests from an unmodified archive of upstream `8cac8f60` reproduces all
  three failures.
- Full Django suite: 2,913 tests, 5 failures, 22 errors, 3 skips. All 27
  failing/erroring tests reproduced against unchanged upstream `8cac8f60`.
  Besides the admin breadcrumb failure, these concern the local readability
  dependency versions (installed tagged adapter 0.1.6 versus expected 0.1.7
  and missing requested metrics profiles). Footer-specific tests pass.

The revised identifier sits above the utility links. Browser checks also verify
its position, 48px crest size, 4px top/bottom crest margins, and the revised
keyboard order. Cropped previews: [desktop](footer-1280.png), [mobile](footer-320.png).
