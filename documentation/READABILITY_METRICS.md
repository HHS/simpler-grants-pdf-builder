# Source-native readability metrics

NOFO Builder has a contained integration boundary for the standalone
[`hhs-nofo-metrics`](https://github.com/agilesix/hhs-nofo-metrics) package.
The package is pinned to the Agile Six `v0.5.4` release. The feature remains
disabled by default so environments can opt into the provisional metrics UI
independently.

## Source contract

Builder renders `nofos/includes/nofo_export_document.html` for both:

- the `#download_target` region used to generate Word documents; and
- the UTF-8 HTML passed to `hhs-nofo-metrics`.

This keeps the metrics source aligned with the generated document without an
authenticated HTTP request back into Builder. It also excludes navigation,
forms, CSRF tokens, and other application shell content from the source hash.

The caller selects:

- profile `hhs-nofo-fy27-html@0.4.0`;
- adapter root `download_target`;
- production path `nofo_builder_export_html`;
- the NOFO UUID as `document_id`; and
- `Nofo.updated` as the Builder revision.

## Endpoint

An authorized user with access to the NOFO can request:

```text
POST /nofos/<uuid>/readability-metrics
```

When enabled and installed, the endpoint returns the package's complete
status-aware `AnalysisResult` JSON and sets `Cache-Control: no-store`. It does
not flatten unavailable metrics to zero or turn provisional measurements into
pass/fail determinations.

Expected failures are machine-readable:

- `503 readability_metrics_disabled` when the feature flag is off;
- `503 readability_metrics_unavailable` when the package is absent; and
- `422` with the package's stable error code when analysis rejects the source.

Normal Builder group permissions and CSRF protection apply. The browser sends
the page's CSRF token in the `X-CSRFToken` header. GET requests return `405`.

## Stored snapshots

Opening the panel (which starts a calculation) or using its calculate button
stores an append-only `NofoReadabilityScore`
snapshot containing the result, the NOFO revision, the profile and package
versions, the requesting user, and the configured goals. Repeating a calculation
for the same revision, profile, and package version returns the stored result
without running the package again or creating another row. `Cache-Control:
no-store` prevents HTTP caching; it does not disable this database-backed reuse.

Editing or reimporting the NOFO advances its revision. The next calculation
creates a new snapshot and retains earlier snapshots. If the revision changes
while analysis is running, that result is returned but is not stored. Failed
calculations do not create snapshots. Results with unavailable metrics are
retained, but are not treated as the latest complete measurement.

Snapshots are not created on document saves or in the background. The only
calculations that run without opening the panel are the ones at import,
re-import and **Download PDF**, which also save a checkpoint (see
[Automatic checkpoints on import, re-import and PDF download](#automatic-checkpoints-on-import-re-import-and-pdf-download)).
Archiving a NOFO retains its snapshots; deleting it deletes its snapshots.
Deleting a user retains their snapshots with a null requesting user.

## Edit-screen panel

When the feature flag is enabled, the normal NOFO edit screen shows a compact,
collapsed readability accordion after the primary NOFO status. A **Beta** tag
identifies the feature as experimental. Expanding the accordion starts an
on-demand calculation; the button allows retries or **Recalculate**. The result
displays the four Tier 2 clearance metrics: word count, words per sentence,
Flesch-Kincaid grade level, and passive sentences, plus sentences per paragraph
(target: 3 or lower), a Tier 1 drafting measure. It also displays any
metric-specific unavailable status, a scope explanation for metrics that use
different denominators, and collapsed package notes. The browser reads only the
endpoint response; metric calculation and source rendering remain server-side.
The package profile and version remain available in the API response and are
shown in saved history so editors can identify a measurement change.

The accordion's closed heading describes the latest saved checkpoint, not a
calculation: for example **Last saved Oct 3 automatically on import**, or
**Not calculated** when the NOFO has no saved checkpoints. This line is
rendered by the server and stays accurate whether or not anyone has opened the
panel. After the panel calculates, the heading reads **Calculated · Last
saved …**; after someone saves, **Calculated · Saved just now**.

The panel does not assign pass/fail bands. Calculation and an explicit saved
review checkpoint are separate actions. Editors can calculate again after
editing or reimporting and save selected results for their review package.
Retention is documented under [Stored snapshots](#stored-snapshots).
Opening or reopening the panel checks the current NOFO and retrieves the stored result if
the revision and measurement contract are unchanged, or calculates a new result
otherwise. Target comparisons use current configuration, not the goals saved
with a previous snapshot.

## Target comparisons

Builder adds presentation-only comparisons without changing the metrics package
or its result contract. The default targets are:

- word count: 13,500 or fewer;
- words per sentence: 15 or fewer;
- sentences per paragraph: 3 or fewer;
- Flesch Reading Ease: 39 or higher;
- Flesch-Kincaid grade level: a displayed range of 11.5–12.5, depending on
  NOFO type; and
- passive sentences: 8% or fewer.

Builder does not infer a NOFO category. Grade-level values at or below 11.5
are within either category's target, values above 12.5 need improvement, and
values between the two thresholds prompt the editor to check the applicable
NOFO type. The Reading Ease comparison is a Builder presentation target rather
than a package enforcement rule.

Set `HHS_NOFO_METRIC_GOALS` to a JSON object keyed by metric ID to override the
defaults for an environment. Set it to `{}` to hide all target and assessment
language.

This synthetic example demonstrates the override shape:

```bash
HHS_NOFO_METRIC_GOALS='{"word_count":{"label":"Example goal","operator":"at_most","value":100}}'
```

Each configured goal requires a display `label` and an `operator`. Use
`at_most` or `at_least` with a finite numeric `value`. Use
`at_most_by_category` with finite numeric `minimum` and `maximum` thresholds
when the applicable upper limit depends on a category Builder cannot infer. A
metric may instead use a non-empty array of goal objects when multiple
comparisons apply. Builder compares the unrounded metric value and uses
**Within target**, **Check NOFO type**, or **Needs improvement** language rather
than pass or fail.

The package response and stored snapshot retain all calculated metrics.
`flesch_reading_ease` does not have a card in the edit-screen panel.
Sentences per paragraph uses the component supplied with words per sentence;
when unavailable, its card displays an unavailable value instead of zero.
The five cards use five columns at a results width of 52rem, two columns from
32rem (2–2–1), and one column below 32rem. Labels and target comparisons use
at least 1rem text; browser zoom can reduce the column count.

The application must not infer a category from the NOFO title or prose.

## Feature flag

`HHS_NOFO_METRICS_ENABLED` is a constance setting, so a superuser can turn the
feature on or off from the admin at `/admin/constance/config/` without a
redeploy. The change takes effect on the next request.

The `HHS_NOFO_METRICS_ENABLED` environment variable still supplies the value the
constance setting starts at, which keeps existing environment configuration
working. Once the setting has been saved in the admin, the saved value wins and
the environment variable no longer changes the flag for that environment.

## Local validation

Enable the feature in a local environment and start Builder normally:

```bash
HHS_NOFO_METRICS_ENABLED=true poetry run python nofos/manage.py runserver
```

Or start Builder normally and toggle `HHS_NOFO_METRICS_ENABLED` in the constance
admin.

## Release activation

For the release that introduces the four Tier 2 clearance metric cards, enable
readability metrics in the target environment after merging and deploying the
change. Set `HHS_NOFO_METRICS_ENABLED` to true in the constance admin, then open
a NOFO's Readability metrics accordion and confirm that calculation succeeds
and all four clearance metric cards appear. Changing the environment variable
alone does not override a previously saved admin setting.

Before enabling the feature outside local development:

1. Run the real-package integration test and the Builder test suite.
2. Confirm that the pinned package tag and profile reference are still the
   intended versions.
3. Turn on `HHS_NOFO_METRICS_ENABLED` in the constance admin only in the
   intended environment.

Apply migration `0132_noforeadabilityscore` before serving the new endpoint. The
feature flag remains disabled by default; deploying the migration does not
enable the panel. Historical charts, backfills, document-save triggers, and
background jobs are out of scope.

Apply migration `0148_readability_checkpoint_trigger` before serving automatic
import checkpoints. It adds `NofoReadabilityCheckpoint.trigger` with a default of
`manual`, so every existing checkpoint keeps its meaning: saved by a person.
Migration `0149_readability_checkpoint_download_trigger` adds the `download`
choice; it changes no data.

## Saved review checkpoints

Calculating metrics remains exploratory. Select **Save these results** to keep
a review checkpoint. The panel says **Snapshot saved** after saving. The server reuses the calculation for the current NOFO
and measurement setup, or calculates it if the NOFO has changed. It never
takes metric values from the browser. A content change during that request
returns a retry message instead of keeping results for stale content.

`NofoReadabilityCheckpoint` references the unchanged `NofoReadabilityScore` row
and records the saver, save time, and status at save. Calculation time and save
time are separate. Repeating a save for the same calculation returns the first
checkpoint without changing its time, user, or status. Existing calculations
are not backfilled into saved history. Partial results may be saved;
unavailable metrics show **Unavailable**, never zero.

### Automatic checkpoints on import, re-import and PDF download

When `HHS_NOFO_METRICS_ENABLED` is on, Builder saves a checkpoint automatically
after a NOFO is first imported, after it is re-imported, and after someone
selects **Download PDF**. Imports give every NOFO a baseline and let each new
uploaded version be compared with the last; downloads record readability for
the version that was actually produced. These are the only automatic saves.
Builder never saves a checkpoint because the panel was opened, a calculation
ran, **Preview PDF** was used, or the NOFO was edited.

- **What is saved:** the same server-side calculation and checkpoint that
  **Save these results** creates, with `trigger` set to `import`, `reimport` or
  `download`. The user who imported or downloaded is recorded as the saver.
- **Only when the NOFO has changed:** a checkpoint belongs to one NOFO version,
  and each version has at most one. Downloading an unchanged NOFO again, or
  downloading a version someone already saved, keeps the existing checkpoint
  (including its saver, time and trigger) and adds nothing.
- **When:** after the import has been written, or after the PDF has been
  generated. A re-import's checkpoint is taken outside the re-import
  transaction, so a slow or failed calculation never holds the NOFO's rows or
  rolls back the re-import. A failed PDF generation saves nothing.
- **What counts as a download:** a finished, non-watermarked PDF returned as an
  attachment, which is what **Download PDF** requests. **Preview PDF** (inline)
  and test-mode attachments never save.
- **Failures:** best effort. If the metrics package is missing, rejects the
  document, or the NOFO changes during measurement, Builder logs a warning
  (`save_automatic_checkpoint:import`, `:reimport` or `:download`) and the
  import or download succeeds without a checkpoint. Users are only told a
  snapshot was saved when one was.
- **New imports:** the checkpoint describes the document as uploaded. Naming the
  NOFO afterward advances its revision, so this checkpoint is not marked
  **Current version**. It is the as-imported baseline. After the user names the
  NOFO, the success message reads "View NOFO: *name*. Readability snapshot
  saved."
- **Re-imports:** the success message adds "Readability metrics were saved
  automatically as a snapshot, so you can compare this version with earlier
  ones." The checkpoint is compared with the previous saved checkpoint like any
  other.
- **Not backfilled:** NOFOs imported before this change have no import
  checkpoint.

How users are told:

- A line under the HTML / Preview PDF / Download PDF buttons, on the edit page
  and the HTML view, reads "Downloading also saves a readability snapshot." It
  is linked to the **Download PDF** button with `aria-describedby` and shown
  only when metrics are enabled. On the Edit NOFO page, the download also
  updates the readability heading,
  automatic-save notice, and saved snapshot list without reloading the page or
  opening the panel. Normal downloads show no progress or success text. A
  message appears only for an unavailable save or download, or to ask the user
  to refresh if saved history could not be retrieved. Sticky section captions follow the toolbar height, including
  wrapped hints and download status messages. The HTML view retains the normal
  file download.
- The new-import success message ends with "Readability snapshot saved." and
  the re-import success message says a snapshot was saved automatically. Both
  appear only when a checkpoint was actually saved.
- The closed accordion heading names the latest save, including **automatically
  on import**, **automatically on re-import** or **automatically on PDF
  download**. It updates after a download on the Edit NOFO page, including
  while the panel is collapsed; elsewhere it updates the next time the page loads.
- While the latest checkpoint is automatic, an info notice at the top of the
  panel says when it was saved and that new snapshots are only saved when the
  user selects **Save these results**, downloads the PDF, or re-imports the
  NOFO, and only if the NOFO has changed. The notice is hidden once a person
  saves.
- Automatic checkpoints are labeled **Automatic · on import**, **Automatic ·
  on re-import** or **Automatic · on PDF download** in the panel's snapshot
  list, and **Automatic, on import**, **Automatic, on re-import** or
  **Automatic, on PDF download** on the per-NOFO history page and the saved
  readability overview.
- If someone selects **Save these results** when the latest automatic
  checkpoint already covers the current NOFO, the panel says the results were
  already saved automatically and nothing has changed since.

The panel lists recent saved checkpoints from all users. **See all snapshots**
opens `/nofos/<uuid>/readability-scores`. History is newest first and includes
the saver, five metric values, and calculation version with expandable audit details.
Deleting a user retains their records with **Deleted user**. Archiving retains
history; deleting the NOFO deletes its calculation and checkpoint records.

Each record is compared with the immediately previous saved record, not the
previous calculation. Comparisons use current `HHS_NOFO_METRIC_GOALS`, not the
historic goals stored with the calculation. Lower values are better for
`at_most` and `at_most_by_category`; higher values are better for `at_least`.
The category-dependent grade-level thresholds are alternative upper limits,
not a bounded range. Sentences per paragraph comes from the stored words-per-
sentence component. Metrics without targets, unavailable values, and conflicting
target directions are not counted. Changed values also have text indicating
**Higher than previous** or **Lower than previous**. Nothing depends on color.

A changed profile, package, input contract, result schema, or result basis is
labeled **Measurement updated: not compared**. When no metrics can be compared,
the record says **No comparable metrics**, not **No change**.

## NOFO lifecycle and readability history

Readability history belongs to a specific NOFO database record (UUID), not its
name, content, or relationship to another NOFO. Calculation snapshots and saved
checkpoints are separate records. Only saved checkpoints, made by a person or
automatically on import, re-import or PDF download, qualify a NOFO for
`/nofos/metrics/readability-scores`.

| Action | Calculation snapshots and saved checkpoints | Saved readability overview |
| --- | --- | --- |
| Import a new NOFO | Calculates and saves an automatic `import` checkpoint when metrics are enabled. A failed calculation saves nothing and does not fail the import. | The NOFO is listed once its import checkpoint exists. |
| Re-import a NOFO | Calculates and saves an automatic `reimport` checkpoint on the same NOFO, compared with its previous saved checkpoint. | The row shows the re-import checkpoint as the latest save. |
| Select **Download PDF** | Saves an automatic `download` checkpoint after the PDF is generated, unless this NOFO version already has a checkpoint. **Preview PDF** never saves. | The row shows the download checkpoint as the latest save when one was added. |
| Archive a NOFO | Retained on the same NOFO. Archiving is a soft delete. | The NOFO remains eligible for listing. |
| Delete a NOFO through the application/ORM | Deleted with the NOFO: deletion cascades from NOFO to calculation snapshots to saved checkpoints. | Its row disappears on the next page request; counts and pagination are recalculated. |
| Delete the user who calculated or saved results | Retained; the corresponding user reference becomes null. Saved history displays **Deleted user** for a deleted saver. | The NOFO remains eligible for listing. |
| Use **Duplicate NOFO** | The copy receives a new UUID and copied content, but no calculation snapshots or saved checkpoints. Duplicating is not an import, so no automatic checkpoint is saved. The original keeps its own history. | The copy is absent until it has its own saved checkpoint; it then qualifies as a separate NOFO row. |
| Calculate metrics on the copy | Creates or reuses a calculation scoped to the copy's UUID and revision. Identical content does not reuse the original NOFO's calculation. | Calculation alone does not add the copy to the overview. |
| Save metrics on the copy | Starts the copy's own saved history. Later saves compare only with earlier checkpoints on that copy. | The copy's row shows its own latest saved results and comparisons. |

For example, duplicating a NOFO with three saved checkpoints leaves all three on
the original and zero on the copy. Saving the copy's first checkpoint gives it
one checkpoint, with no previous saved record for comparison. There is no
inherited baseline or automatic comparison to the original. Deleting either
record does not delete the other's readability history.

Eligibility also depends on the page's access rules and filters. Since
[PR #1018](https://github.com/HHS/simpler-grants-pdf-builder/pull/1018), the
overview excludes Bloomworks (`bloom`) and staging (`staging`) NOFOs using the
NOFO's **current** group. Importing, re-importing or downloading Bloomworks and
staging NOFOs still saves automatic checkpoints, but those NOFOs are not listed. Moving a NOFO into an
excluded group hides its row without deleting history; moving it out makes its saved history eligible again. Archived
NOFOs and duplicates follow the same group filter. Checkpoints do not capture a
group at save time. This differs from the historical group attribution used by
the [usage & quality metrics](BUILDER_METRICS.md).

There is no automatic age-based cutoff for these saved records. This database
history is separate from application logs and database backups; it is not an
independent archive that survives NOFO deletion.

### Implementation references for maintainers

- [`NofoReadabilityScore` and `NofoReadabilityCheckpoint`](../nofos/nofos/models.py)
  define the cascading NOFO/score relationships and nullable user references.
- [`duplicate_nofo()`](../nofos/nofos/views.py) copies the NOFO, sections and
  subsections; it does not copy readability records.
- [`record_readability_snapshot()`](../nofos/nofos/readability.py) scopes stored
  calculations to the NOFO and measurement contract.
- [`save_automatic_checkpoint()`](../nofos/nofos/readability.py) saves the
  best-effort automatic checkpoint after an import, re-import or PDF download.
  It is called from `NofosImportNewView`, `NofosImportOverwriteView.reimport_nofo()`
  and, for finished attachments only, `PrintNofoAsPDFView` in
  [`views.py`](../nofos/nofos/views.py).
- [`AUTOMATIC_TRIGGER_TEXT`](../nofos/nofos/readability_history.py) holds the
  wording for each automatic trigger ("on PDF download", "the PDF was
  downloaded"). Add new triggers there rather than in templates.
- [`checkpoint_rows()`](../nofos/nofos/readability_history.py) filters history by
  `score__nofo`; comparisons do not traverse original/copy relationships.
- [`readability_overview_page()`](../nofos/nofos/readability_overview.py) queries
  existing NOFOs with saved checkpoints and loads their latest two checkpoints.

When changing duplication, deletion, retention, or overview filtering, review
these relationships together and update this lifecycle contract. Existing
retention coverage is in
[`test_readability_metrics.py`](../nofos/nofos/tests_nofos/test_readability_metrics.py),
[`test_readability_checkpoints.py`](../nofos/nofos/tests_nofos/test_readability_checkpoints.py),
and [`test_readability_overview.py`](../nofos/nofos/tests_nofos/test_readability_overview.py).
Automatic saves are covered in
[`test_readability_import_checkpoints.py`](../nofos/nofos/tests_nofos/test_readability_import_checkpoints.py)
and
[`test_readability_download_checkpoints.py`](../nofos/nofos/tests_nofos/test_readability_download_checkpoints.py).

## Saved readability overview

`/nofos/metrics/readability-scores` lists NOFOs with at least one saved checkpoint,
including archived NOFOs. Because imports and downloads save a checkpoint
automatically, this includes NOFOs imported or downloaded while metrics were
enabled even if no one has saved results by hand. The saved-record count includes automatic checkpoints, and the
last-save cell says when the latest one was automatic. It shows saved-record count, last
save time, the latest five saved metric values, and the change from the previous saved
record. Latest saved results may differ from the current NOFO. A partial latest
checkpoint is shown rather than silently falling back to an older complete one.
Links lead to the per-NOFO history page.

The overview uses the existing `nofos.view_builder_metrics` permission. Superusers
and Metrics viewers can see it; membership in a NOFO's OpDiv alone does not grant
access. Per-NOFO history permits normal NOFO access or Metrics-viewer access;
the latter grants read access only, not permission to save.

The overview paginates NOFOs in groups of 50 before loading only the two latest
checkpoints for each visible NOFO. It selects five metric values and provenance from
the result JSON in the database instead of loading every full report. **Print
this page** prints the displayed page only. Both history pages use private,
`no-store` responses.

All saved-checkpoint UI stays behind `HHS_NOFO_METRICS_ENABLED`. When off, the
save endpoint returns `503 readability_metrics_disabled`, the new pages return
404 for authorized users, and their navigation is hidden. Saved data is retained.
This feature is separate from the anonymous PDF-readability pilot and does not
enable that pilot or its outcome recording.

Saved checkpoints, per-NOFO history, and the saved-results overview belong only
to the authenticated Builder readability feature (#1009, implemented in #1014).
They are outside the anonymous PDF pilot release epic (#968) and must not be
exposed through `/readability/` or counted toward that epic's acceptance criteria.
The pilot's content-free usage monitoring is separate from saved metric results.
See [the pilot runbook](PDF_READABILITY_PILOT.md) for its scope and release gates.

### Review display and keyboard interaction

The panel, recent snapshots, full history and overview display the same five
metrics: word count, words per sentence, sentences per paragraph, Flesch-Kincaid
grade level and passive sentences. Flesch Reading Ease remains in the immutable
calculation data but is excluded from displayed metrics and improvement counts.
Status at save and completeness remain stored but are omitted from the history
UI; unavailable displayed values still say **Unavailable**. The overview omits
current status and the archived/partial labels in NOFO cells. Horizontal scrolling
is unchanged; there are no sticky columns or changed-since-save labels.

History identifies the **Calculation version** with **Metrics v<package version>**
and a keyboard-operable **View details** disclosure for the full measurement
contract. Comparisons still check the entire contract, not only the package.
The empty panel hides **See all snapshots** until a snapshot exists.

Each panel opening checks current content through the existing server cache.
Saving compares source revisions to announce recalculation even if metric values
stay identical. A status-only change still creates no new checkpoint. The save
button uses `aria-disabled` and a submission guard while saving, so it retains
keyboard focus without moving focus back if the user navigates elsewhere.
Confirmation is announced through the existing polite status region; it is not
an additional Tab stop. Actual screen-reader speech requires manual verification.
