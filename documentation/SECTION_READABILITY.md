# On-demand section readability

This first slice of #1066 adds inline Flesch-Kincaid grade-level estimates to
the NOFO editor. It helps writers locate prose to review without leaving the
document. It does not rewrite text, certify compliance, or decide what a writer
may change. Clipboard prompts (#1071/#1072) and pilot rollout (#1073) remain
separate work.

## Local plan and reusable boundary

1. Confirm a subsection body works with the existing HTML analysis profile.
2. Add a narrow HTML-in/result-out function, without Django models or requests.
3. Integrate current policy checks, permissions and revision guards in Builder.
4. Add one check-all action and inline rechecks using existing USWDS styles.
5. Test real-engine scope and failure states, verify in a local browser, then
   request review. Do not enable shared environments as part of this PR.

`section_readability.measure_section(html)` uses the installed hhs-nofo-metrics
package and `hhs-nofo-fy27-html@0.4.0`. The package owns HTML normalization,
sentence selection and grade arithmetic. No Scanner engine, new tokenizer,
UI package or framework adapter is introduced. Builder renders stored Markdown
with Martor, excludes policy and Basic information, and owns access and display.

The result is plain data: status (`current`, `insufficient`, `unavailable`),
numeric grade or null, sentence-scope word/sentence counts, and package/profile/
adapter/input-contract identity. HTML headings do not enter the grade scope;
terminally punctuated prose in paragraphs, lists and narrative table cells does.
Unpunctuated contacts and fragments are not given artificial sentence endings. Tests characterize these
existing rules rather than copying a second normalization implementation.

The provisional display floor is 50 sentence-scope words and three sentences.
It suppresses grades for sparse text, not a scientific guarantee of reliability.
Short prose remains content a writer can review. This slice neither promises
rewrite eligibility nor infers a NOFO category or target from a grade.
Existing grade targets from `HHS_NOFO_METRIC_GOALS` are shown as reference only,
using Builder's existing configuration validator. Category-dependent limits
remain alternative upper bounds, not a range to aim inside. An empty setting
omits target language. No section-level pass/fail assessment is introduced.

Scanner's `nofo_utils.py` and `markdown_utils.py` were reviewed as references.
Its `fkscore` Reading Ease bands and hardest-first sorting are not adopted.
Normalization stays with Builder's existing semantic HTML engine so fragments
are not given artificial punctuation and tables keep their semantic boundaries.

## UI and freshness

With `HHS_NOFO_SECTION_READABILITY_ENABLED` enabled, the editor offers one
**Check section readability** button above the sections, outside the sticky
toolbar. One POST checks all subsections in document order. Results appear
beside their content; each can be rechecked. No calculation runs on import,
page load or save. Results disappear on reload, editing and reimport. Restoring
a back-forward cached page clears results and requires reload.

POST `/nofos/<uuid>/section-readability` uses normal NOFO group access and CSRF.
An optional `subsection_id` restricts a recheck to this NOFO's subsection.
Clients send the page's revision, never source text or trusted scores. The
revision includes current content/order, NOFO revision/access state, canonical
policy data and measurement identity. Before and after analysis, a mismatch
returns 409; the client clears all displayed results. Endpoint JSON responses
are private/no-store. Nothing writes scores, history, content or import tags.
One calculation failure leaves neighbouring results available. Content and
exception details are not logged.

## Policy coverage and release boundary

The existing #821 detector is called on current content on every request,
independently of `HHS_NOFO_POLICY_EXPORT_ENABLED`. Current, prior, potentially
altered and other non-`none` matches are excluded. A detected policy span
excludes its entire mixed subsection. Missing required slots remain part of the
existing policy workflow, not a new section-readability warning system.

An empty canonical set, no current slots, or a current slot without usable text
blocks scoring with an explicit **canonical policy data is not configured**
state. The repository's production source is currently empty. #827 demo data
is only for local tests and screenshots, never a production substitute.

This guard detects missing configuration, not comprehensive policy coverage.
Even with data present, `none` only means no match against that configured set.
The UI explicitly says that a result is not approval to edit. Before enabling a
pilot, verify the intended canonical source and coverage and run #1073's review
loop. The new flag defaults off. This PR does not enable it, change the export
flag, or change whole-document readability history.
