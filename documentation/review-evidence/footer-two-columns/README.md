# Small-screen footer columns

The four signed-in utility links use two equal columns below the 1024px
USWDS desktop breakpoint. Desktop retains its existing single row. Anonymous
Builder and public readability pages use the same columns with three links.
Link destinations and visibility are unchanged. Links follow reading and keyboard
order: support ticket (when signed in), latest updates, privacy policy, back to top.
The signed-in mobile grid places support and updates above privacy and back to top.

Uses existing USWDS `grid-col-6 desktop:grid-col-auto` utilities.

- [Before at 576px](before-footer-576.png) and [after at 576px](footer-576.png),
  rendered from upstream `963ff90c` and this branch with the same synthetic account.
- [Mobile preview](footer-320.png)
- [Desktop preview](footer-1280.png)

Validation: `tests/js/footer.browser.cjs` passes all 24 combinations of shared
shell, authentication state and viewport width (320, 375, 480, 576, 768,
1023, 1024 and 1280px). It checks row and column alignment, desktop's single
row, requested link order, no horizontal overflow, link counts and existing HHS identifier checks.
Previews use local Django templates and synthetic account data.

Reviewed UI Patterns, Editor Tasks, README and contribution documentation.
No editor instructions change: this only adjusts utility-link columns.
No new shared component or migration workflow is introduced.

Additional checks: 23 focused Django banner/public-readability tests and all
61 JavaScript unit tests pass. Repository-wide lint reports existing formatting
issues in unmodified `policy_language.py`, `test_policy_language.py` and
`tests_nofos/test_metrics.py`; this change does not edit Python files.

Full Django suite completed: 2,916 tests, 5 failures, 26 errors, 3 skipped.
These broader failures are outside the targeted checks; no claim of a green
full suite or baseline equivalence is made.
