# Points columns without import markers (#1138)

The Markdown in the issue is passed through Martor's Markdown conversion and
`add_classes_to_tables`. A standalone table fixture loads the repository's
`uswds/uswds.css` and `styles.css`, inside a 760px-wide `.usa-prose` container.
Before uses the unmarked output that upstream currently produces. After uses
render-time detection. These are local browser fixtures, not authenticated
production screenshots.

| Check | Before | After |
| --- | --- | --- |
| Table width | 701.05px | 701.05px |
| `10 points` line count (each of three rows) | 2 | 1 |
| `5 points` line count | 1 | 1 |
| Points body `white-space` | `normal` | `nowrap` |

![Before](editor-before.png)

![After](editor-after.png)

Chromium print-media fixture checks with `theme-base.css` and
`theme-orientation-portrait.css` also keep all four values on one line after the
change. That fixture did not reproduce the baseline PDF wrapping, which was
reported in the user's production screenshot. DocRaptor was not called; the
change uses the existing PDF no-wrap CSS, with the missing class now supplied
at render time.
