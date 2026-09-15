# Decision Log

This file records significant architectural, product, and implementation decisions made on the NOFO Builder project. Entries are ordered newest-first.

---

## 2026-09-14 — Display Tier 2 clearance metrics in the readability accordion

**Update, 2026-09-15:** Include sentences per paragraph (target: 3 or lower)
as a fifth metric. It remains a Tier 1 drafting measure; no tier subtitle is
shown on the card. Retain the four
clearance metrics and keep Flesch Reading Ease excluded. Use five columns
when the results area is at least 52rem wide, two columns from 32rem, and
one column below that. Labels and target comparisons remain at least 1rem;
cards wrap text and grow vertically instead of shrinking text to fit.
This supersedes the four-card-only presentation decision below.

**Context:** The current NOFO clearance guidance requires four readability
metrics at Tier 2 submission: word count, words per sentence, Flesch-Kincaid
grade level, and passive sentences. Sentences per paragraph applies only to
Tier 1 drafting, and Flesch Reading Ease is not included in the current
guidance. The underlying NOFO readability metrics package can continue to
calculate and return its full metric set independently of what the Builder
interface presents.

**Decision:** Show only the four Tier 2 clearance metrics in the Readability
metrics accordion. Keep the other calculated values in the package response and
stored snapshots so the measurement contract does not change. Present the four
cards as a two-column grid on tablet and desktop screens, with the existing
single-column mobile layout. This keeps the interface focused on clearance
submission requirements and avoids an unbalanced five-card layout. Sentences
per paragraph can be reconsidered later if the accordion expands to include
Tier 1 drafting guidance.

---

## 2026-06-11 — Renamed "Download PDF (live)" button to "Download PDF"

**Context:** Users expressed confusion about what "live" meant in the "Download PDF (live)" button label. The term was originally used to distinguish the final, unwatermarked PDF from the watermarked "Preview PDF".

**Decision:** Simplified the label to "Download PDF". The distinction from Preview PDF is already clear from context. File changed: `nofos/bloom_nofos/templates/includes/print_button.html`

---

## 2026-05-21 — Backlog OpDiv Admin multi-group assignment

**Context:** A question was raised about whether OpDiv Admin users could be assigned to more than one OpDiv group (e.g., CDC DGHT and CDC DGHP). The two implementation paths identified were: (1) allowing users to belong to more than one group, or (2) introducing a parent-child group hierarchy — both considered complex. The Bloom group already provides all-or-nothing visibility across all users and NOFOs but offers no granular control.

**Decision:** Backlogged. The feature is not a hard requirement, the implementation complexity is high, and NOFO Builder is being sunset in favor of similar functionality on SGM. Not worth investing in at this time.
