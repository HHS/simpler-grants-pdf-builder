# "What's new" changelog banner

After a new release is deployed, NOFO Builder shows a banner at the top of every page saying the site was updated. It links to [CHANGELOG.md](../CHANGELOG.md) on GitHub, which opens in a new tab. The banner turns itself on and off. Nobody has to remember to do it.

Screenshots: [review-evidence/changelog-banner](review-evidence/changelog-banner/README.md).

## What users see

> ⓘ **NOFO Builder was updated on October 3, 2026.** [See what's new in version 3.48.0](https://github.com/HHS/simpler-grants-pdf-builder/blob/main/CHANGELOG.md#changelog)

- **Component:** USWDS [Site alert](https://designsystem.digital.gov/components/site-alert/), info and slim variants (`usa-site-alert--info usa-site-alert--slim`). It uses the site's existing USWDS styles, with no custom CSS. It's the USWDS equivalent of the VA Design System banner on design.va.gov.
- **Placement:** directly below the site header, on every page that extends `base.html`. That includes signed-out pages like **Login**.
- **Not on NOFO view, PDF, or export pages:** those templates extend `base_barebones.html`, so the banner can't end up in a PDF.
- **Not dismissible:** this is on purpose. Everyone sees it until the window ends.
- **Not printed:** a `@media print` rule in `styles.css` hides it. That stylesheet loads on every `base.html` page, so the rule covers all printable pages, like the metrics and readability history pages.
- **Accessibility:** the link shows the USWDS external-link icon and includes screen reader text "(opens in a new tab)". The section has an `aria-label` so it's announced as a site alert.

## When it shows

1. The app reads the newest dated release heading from the `CHANGELOG.md` **bundled in the deployed image**. release-please writes these headings when the release PR is merged:

   ```markdown
   ## [3.48.0](https://github.com/HHS/simpler-grants-pdf-builder/compare/nofos-v3.47.1...nofos-v3.48.0) (2026-10-03)
   ```

   The older `## [3.33.0] - 2026-05-26` format also works. `## [Unreleased]` and undated headings are ignored. Future-dated headings don't show until that date.

2. The banner shows from that date through the end of the **5th business day**. The release date counts as day 1 if it's a business day. Business days are weekdays that aren't US federal holidays, using Eastern time.

3. A newer release **restarts** the window, because only the newest heading counts.

Because the app reads the bundled file, the banner only appears once a release is **deployed**. It never appears for something merged to `main` but not yet deployed. The app makes no calls to GitHub. The file is read once per process and cached.

The window is counted from the **release date in the heading**, not the deploy date. A release deployed several days after it was cut gets a shorter window. A release deployed more than 5 business days after it was cut never shows a banner.

## Turning it off

In Django admin, go to **Constance › Config**:

| Setting | Default | What it does |
| --- | --- | --- |
| `CHANGELOG_BANNER_ENABLED` | `True` (`False` while running tests) | Uncheck to hide the banner for everyone, even during a window. |
| `CHANGELOG_BANNER_BUSINESS_DAYS` | `5` | How many business days the banner shows. `0` also turns it off. |

Changes take effect on the next page load, without a deploy.

## Code

| File | Purpose |
| --- | --- |
| `nofos/bloom_nofos/changelog_banner.py` | Parses `CHANGELOG.md`; counts business days, including federal holidays |
| `nofos/bloom_nofos/context_processors.py` | Adds `CHANGELOG_BANNER` to every template |
| `nofos/bloom_nofos/templates/includes/changelog_banner.html` | Banner markup |
| `nofos/bloom_nofos/templates/base.html` | Includes the banner, right after the site header |
| `nofos/bloom_nofos/static/styles.css` | Hides the banner when printing |
| `nofos/bloom_nofos/settings.py` | `CHANGELOG_BANNER_*` Constance settings |
| `.dockerignore` | `CHANGELOG.md` must **not** be listed here, or deployed environments can't read it and the banner never shows |
| `nofos/bloom_nofos/tests_bloom_nofos/test_changelog_banner.py` | Tests, including one that fails if the real `CHANGELOG.md` heading format stops parsing |

## Tests

The banner is **off by default while running tests** (`CHANGELOG_BANNER_ENABLED_DEFAULT` in settings). Otherwise, any test that renders a `base.html` page would pass or fail depending on whether the newest `CHANGELOG.md` release is recent. To test banner behavior, turn it on with `@override_config(CHANGELOG_BANNER_ENABLED=True)` and patch `get_latest_release` and the date. `test_changelog_banner.py` shows how.

## Federal holidays

The holidays in 5 U.S.C. 6103 are calculated in code, including the rule that moves a holiday on Saturday to Friday and one on Sunday to Monday, so there's no extra dependency. One-off closures, like extra days off by executive order, aren't included. If the list of federal holidays changes, update `federal_holidays()`.

## Previewing locally

The banner only shows inside a window. To see it, run the dev server within 5 business days of the newest `CHANGELOG.md` date. Or temporarily add a heading dated today to your local `CHANGELOG.md`, for example `## [9.9.9] - 2026-10-05`, and restart the server. The file is cached per process.
