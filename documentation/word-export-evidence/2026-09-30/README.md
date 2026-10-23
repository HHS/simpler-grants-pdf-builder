# Local Word-export verification, September 30

Synthetic data only. Current Builder main was merged into PR #882 and the Linux
image rebuilt with the locked dependencies and Pandoc 3.11. No dev/production
deployment or shared feature-flag change was made.

Chrome used the actual download buttons for normal NOFO, clearance, Composer,
and Writer. Each produced a saved DOCX. The clearance-specific action was
checked, not just the normal button on a clearance preview. Its document contains
the pre-decisional review notice. Long-document markers remained present in all
four downloads. Images remained in normal, clearance and Writer; Composer
retained its variable placeholder and writer instructions.

- [Clearance ready state](clearance-sep30.png)
- [Composer ready state](composer-sep30.png)
- [Writer preview after its successful download](writer-sep30.png)

The Writer download is a direct download, unlike the modal used by Composer and
NOFO exports. Its screenshot records the preview after downloading, not a modal.
DOCX files, session cookies and fixture databases remain local and are not
committed. These screenshots show browser behavior, not desktop Word pagination.

Checks: 32 focused real-Pandoc tests, the full 2,223-test suite (two skips),
30 JavaScript tests, and the network-disabled resource/admission probe passed.
Independent implementation and added-test
reviews found no default-off merge blocker. See `documentation/WORD_EXPORT.md`
for the separate rollout limitations and older desktop Word evidence.
