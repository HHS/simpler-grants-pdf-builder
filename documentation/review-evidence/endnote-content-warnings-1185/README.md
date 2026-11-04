# Endnote content warnings — issue #1185

Local synthetic evidence, October 22, 2026, on `origin/main` at `8d43eee1`
plus this branch. No production records or source documents were modified.

![Endnote format warnings for a subsection and its nested sources](endnote-warning.jpg)

The coordinating agent checked the running local page in Chrome: **Check
endnotes (2)** displayed one warning for **Endnotes** and one for its nested
**More sources** subsection, with subsection links and bounded first-block
excerpts. Ordinary prose after the next peer heading was not included.
The coordinating agent also selected **Save subsection** with the malformed
Endnotes content unchanged: the save succeeded and both warnings remained.
This reuses the existing warning panel; no heading typography or alert styles
were changed. PDF generation and production behavior were not verified here.

Automated coverage includes a top-level Endnotes/Footnotes section, a nested
Endnotes subsection and deeper headings, plain text, bullet lists, pasted divs,
malformed native lists, escaped/bounded excerpts, manual continuation content,
legacy Google Docs links, native Word imports, existing relationship warnings,
group access denial, and a real subsection save that remains nonblocking.

Review follow-up: a saved native citation with its matching reference and a
nested Markdown heading formatted with emphasis, bold or a link exposed a false
format warning quoting “Sources.” A regression reproduced all six cases before
the fix: three heading formats, each with valid content alone or a subsequent
malformed paragraph. The format check now skips heading descendants as well as
the heading itself; valid citations have no warning and a later malformed block
supplies the first excerpt. Saved content and import conversion are unchanged.
No new browser or PDF validation was performed for this narrow correction.

Full-suite and formatter results are recorded in the pull request. Repository-wide
formatter checks have unrelated baseline failures in `policy_language.py`,
`test_metrics.py`, and `test_policy_language.py`; changed Python files pass.
