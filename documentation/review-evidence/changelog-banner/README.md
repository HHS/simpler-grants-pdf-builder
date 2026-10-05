# "Latest release" banner

Local Chromium screenshots from October 5, 2026, taken with the Django dev
server (SQLite) on this branch. The repository's real `CHANGELOG.md` was used
with no changes and no time freezing. Its newest release is 3.48.0 from
Saturday, October 3, 2026, so the 5-business-day window runs from Monday,
October 5 through Friday, October 9. October 5 is day 1.

- [Signed-out Login page](login-signed-out.png) (1280px): the banner sits
  directly below the site header.
- [Signed-in NOFO index](nofo-index-signed-in.png) (1280px).
- [NOFO Compare index](compare-index.png) (1280px): the banner shows across
  Builder, Compare and Composer because they all extend `base.html`.
- [Keyboard focus on the link](link-keyboard-focus.png): the standard USWDS
  focus outline.
- [Login page on a phone](login-mobile.png) (390px, 2x): the text wraps and the
  external-link icon stays next to the link text.
- [Metrics page in print preview](print-preview-metrics.png): Chromium print
  media. The banner is hidden, along with the header and footer that page
  already hides when printing.

- [Constance settings in Django admin](admin-constance-settings.png), signed in
  as a superuser: both banner settings with their help text. The business-days
  input has `min="0" max="30"`. Typing 31 shows the browser message "Value must
  be less than or equal to 30", and the server rejects it too (unit test).

Clicking the link opened a new browser tab (Playwright `popup` event). This
sandbox can't reach GitHub, so that tab's content isn't shown.
