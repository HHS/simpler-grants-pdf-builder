# Endnote editor spike: local evidence

October 27, 2026. Synthetic prototype only; no Builder application route,
template, importer, dependency or stored document changed. See the
[investigation](../../ENDNOTES_EDITOR_SPIKE.md) for scope and limits.

## Automated checks

- `node --test documentation/spikes/endnotes-1186/core.test.mjs`: 11 tests passed.
- The [browser smoke script](../../spikes/endnotes-1186/browser-smoke.cjs) passed
  in local headless Chrome: empty-input recovery; paragraph insertion; repeated
  references and return links; number changes after reorder; citation editing;
  cancelled/confirmed deletion; stale-text rejection; explicit relocation;
  keyboard cursor insertion; narrow layout; and no JavaScript exceptions.
- At 390px, document width does not exceed viewport width. The screen stacks
  its columns and long buttons wrap. The script checks Chrome's actual rendered
  heading font: custom Merriweather Bold, requested at weight 700. Fonts and icons
  are the existing local Builder assets, with relative paths for this standalone
  HTTP-served prototype. Shared assets are unchanged.
- `git diff --check` and local guide/asset-link checks passed.

To repeat browser checks, start the loopback server described in the guide,
then run `node documentation/spikes/endnotes-1186/browser-smoke.cjs` with
Playwright resolvable in your Node environment. It uses installed Chrome on
macOS; `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` can select an installed executable.
It captures the synthetic screens in this directory. No AWS, PDF service, AI
provider, login or application database is used.

## Screens reviewed

- [Paragraph approach](paragraph-placement.png): paired reference/return links.
- [Cursor approach](cursor-placement.png): insertion inside a paragraph.
- [Changed reference location](stale-reference.png): warning and explicit review.
- [Narrow controls](mobile.png) and [narrow preview](mobile-preview.png).

All final screenshots were directly inspected. This is not an accessibility
certification or a representative-user usability test. Keyboard insertion was
tested in the plain-text stand-in, not Ace/Martor. No actual imported document,
rich citation round trip, generated PDF, Word export, browser-to-server save,
database locking or deployment was exercised. No independent subagent review is
claimed. Full Django tests were not run because production code is unchanged.
