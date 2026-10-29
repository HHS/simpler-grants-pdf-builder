# Word passive sentence comparisons

This internal tracker explicitly retains completed authenticated Word-upload
Checker results. It does not change formulas, Builder exclusions, ordinary usage
records, or portfolio scores. A saved upload can still produce an ordinary,
content-free usage event.

## Rollout and permissions

1. Apply migration 0160. The Constance flag
   HHS_NOFO_WORD_COMPARISONS_ENABLED defaults **off**; it takes effect without
   restarting workers. Existing authenticated Checker enablement remains required.
2. Select **Can save and edit Word comparisons** on selected users in Django admin
   to grant nofos.manage_word_comparisons directly. This grants saving/editing, not
   metrics visibility. Bloom membership neither grants nor blocks this permission.
3. Grant nofos.view_builder_metrics separately to people who should see the
   tracker, including its retained document names. Comparison managers can open
   their own saved records without metrics-view permission.
4. Confirm the audience is authorized to see document names; use non-sensitive
   filenames when possible. Enable the flag, then exercise
   [TASK-WORD-COMPARISON](../EDITOR_TASKS.md#task-word-comparison).

Usage remains the default tab at /nofos/metrics/readability-checker-usage.
The legacy /nofos/metrics/readability-pilot redirects permanently and preserves
the query string. The existing Django URL name is retained for compatibility.

## Retention, integrity and deletion

Saved comparisons and manual revisions have **no automatic expiration**.
They are intentionally separate from short-lived uploads and content-free attempt
cleanup. Saved metadata includes the display filename, SHA-256 fingerprint,
analysis/run identity, package/profile/input-processing identities, scope and
conversion warnings, available counts and scores, and manual reviewer history.
No DOCX or extracted sentence text is retained.

The completed report is carried in a signed, compressed, 30-minute handoff bound
to the analyzing user. Unsaved reports are not written to the database. A forged,
expired, or different user's handoff cannot be saved. Do not log request bodies:
they may contain signed report metadata or manual notes. Run UUID uniqueness
makes concurrent/repeated saves idempotent; each fresh analysis has a new UUID.

Checker fields have no editing interface. Manual saves append revisions, including
reviewer and timestamp. Deleting a user preserves historical measurements with a
missing reviewer identity. Avoid personal or document text in review notes.

Superusers can inspect and delete an entire comparison in Django admin
(**Word comparisons**); deletion cascades to all its manual revisions.
This is the supported intentional deletion procedure. These models are excluded
from EasyAudit copying so deleted names/results are not retained there.
Database backups follow the deployment's independent backup policy; deletion
does not immediately purge backups. Do not enable until that policy and the
metrics-viewer audience are acceptable to the operator.

## Rollback

Disable the Constance flag to hide save, list, detail and editing routes immediately.
This preserves retained comparisons for investigation or later re-enablement.
Revoke comparison-management permission if needed. Keep migration 0160 applied
during code rollback to avoid deleting review history. Never run ordinary attempt
cleanup against these tables.

## Interpretation

Differences are signed **Checker minus Word**, in percentage points. No passive
numerator is inferred from rounded Word percentages. Missing values stay missing.
The Word sentence count and Checker denominator remain separate. A fingerprint
identifies the Checker input but cannot independently establish which file the
reviewer opened in Word. Reviewed is a workflow state, not a quality threshold.

[Implementation screenshots and validation](../review-evidence/1248/README.md)
use invented names and measurements.
