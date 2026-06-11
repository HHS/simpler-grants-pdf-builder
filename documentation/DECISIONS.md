# Decision Log

This file records significant architectural, product, and implementation decisions made on the NOFO Builder project. Entries are ordered newest-first.

---

## 2026-06-11 — Renamed "Download PDF (live)" button to "Download PDF"

**Context:** Users expressed confusion about what "live" meant in the "Download PDF (live)" button label. The term was originally used to distinguish the final, unwatermarked PDF from the watermarked "Preview PDF".

**Decision:** Simplified the label to "Download PDF". The distinction from Preview PDF is already clear from context. File changed: `nofos/bloom_nofos/templates/includes/print_button.html`

---

## 2026-05-21 — Backlog OpDiv Admin multi-group assignment

**Context:** A question was raised about whether OpDiv Admin users could be assigned to more than one OpDiv group (e.g., CDC DGHT and CDC DGHP). The two implementation paths identified were: (1) allowing users to belong to more than one group, or (2) introducing a parent-child group hierarchy — both considered complex. The Bloom group already provides all-or-nothing visibility across all users and NOFOs but offers no granular control.

**Decision:** Backlogged. The feature is not a hard requirement, the implementation complexity is high, and NOFO Builder is being sunset in favor of similar functionality on SGM. Not worth investing in at this time.
