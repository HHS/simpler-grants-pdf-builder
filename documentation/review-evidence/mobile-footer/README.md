# Mobile footer overflow

Verified locally in Chrome on September 8, 2026 using Django's rendered shared
base template and repository CSS. The empty content area intentionally isolates
the shared layout. The user is a synthetic template fixture, not a live login.

Before: document width was 328px at a 320px viewport and 383px at 375px.
After: document width equals viewport width at 320, 375, 480, 768, and 1280px,
for both signed-in and signed-out template states. Footer link counts remain
three and two respectively. Desktop styling is unchanged.

- [Before, mobile](before-320.png)
- [After, mobile](after-320.png)
- [Before, desktop](before-1280.png)
- [After, desktop](after-1280.png)

Reproduce with `node tests/js/footer.browser.cjs` with Playwright available to
Node and `PYTHON` set to the project's Python environment. The script renders
the current template, checks widths and links, and captures screenshots.
On the original main revision, use `--before` to assert the reproduction.
