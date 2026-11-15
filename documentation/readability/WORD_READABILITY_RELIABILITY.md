# Word report scope and reliability

The standalone Word checker reports aggregate counts for recognized covers,
contents, writer instructions, and Builder metadata. Covers are recognized
from Word’s Cover Pages gallery or, since `hhs-nofo-metrics` 0.8.1, from a
plain-paragraph first section that ends in a section break and is followed by a
table of contents (the GrantSolutions Announcement Module layout). That first
section must have no headings, no line ending in sentence punctuation, at most
25 words per line and at most 100 words. Builder metadata lines are recognized
under a "Basic information" or "Before You Begin" heading. Opening text before a
section break remains countable. The counts describe recognized exclusions from recovered text.

Investigation for #1169, against Builder's pinned `hhs-nofo-metrics` 0.6.0.
This changes report presentation, not formulas, source recognition, permissions
or upload handling.

## Why no rating is returned

`analyze_word` converts the Word body with Mammoth, then calls the package's
`hhs-nofo-fy27-html@0.5.0` source-native HTML profile. That pipeline uses
`estimate_kind="none"`. Its numeric results are `calculated` and deliberately
have no PDF-estimate reliability object. Builder still calls the displayed
results estimates because they describe recovered text, not guaranteed complete
Word coverage. `_safe_result` preserves the absence instead of inventing a rating.

The current PDF method compares scores with unknown-role content included and
excluded, along with classification coverage and failed-page evidence. It does
not establish how completely Word source structures survived conversion. A Word
reliability method would need a defined source-to-conversion coverage assessment
and validation corpus; successful arithmetic or no converter warning cannot
substitute for that work.

This is the current profile contract, not a failed check or a dependency on
Builder #1120. No identified pending PR or release provides Word conversion
reliability. This presentation fix does not promise such a feature. Sentence
fragment exclusions determine formula scope independently; they are not why a
Word rating is absent.

Pinned package references:

- [HTML versus PDF pipeline configuration](https://github.com/agilesix/hhs-nofo-metrics/blob/v0.6.0/src/hhs_nofo_metrics/analysis_pipelines.py)
- [Conditional metric reliability attachment](https://github.com/agilesix/hhs-nofo-metrics/blob/v0.6.0/src/hhs_nofo_metrics/semantic_html_engine.py)
- [PDF reliability evidence and sensitivity](https://github.com/agilesix/hhs-nofo-metrics/blob/v0.6.0/src/hhs_nofo_metrics/estimate_reliability.py)

## Presentation decision

Ordinary Word uploads do not need a second blue alert for a general limitation.
Put Word preparation/conversion guidance under **Measurement scope**, beginning
with bold **Why “Estimated”?** to connect the metric label to recovered text and
the effect of missing or changed text. Keep this explanation out of the metric
section to avoid repetition. The guidance is followed
by one plain explanation that conversion completeness is not checked and no
rating is assigned. Explicitly distinguish that limitation from a detected
problem. Keep metric cards marked **Estimated**, without repeating an absent
rating on every card. Unavailable values remain **Unavailable**.

Actual converter warnings remain separate in **Calculation notes**, alongside
other specific calculation notes. No warning is inferred from the general help
text. A warning-free conversion is not a complete-coverage guarantee.

PDF reliability notices and per-metric ratings are unchanged. If an upstream
Word result does supply a recognized rating, preserve its notice and per-metric
ratings; this change does not manufacture, suppress or downgrade supplied ratings.

**Copy metrics** reads the same scope guidance, absent-rating explanation,
metrics and calculation notes shown on screen. Browser printing uses that same
report markup; no separate Word PDF or report renderer is introduced.
