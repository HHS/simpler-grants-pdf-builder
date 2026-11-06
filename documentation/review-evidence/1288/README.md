# Isolated bold punctuation on import

These browser captures use the same synthetic text and preview layout. Both run
through the NOFO HTML importer and Markdown conversion. The before case bypasses
the punctuation cleanup. The after case runs the cleanup. The preview renders
the resulting Markdown outside the authenticated Builder editor.

- [Before](before.png)
- [After](after.png)

See [issue #1288](https://github.com/HHS/simpler-grants-pdf-builder/issues/1288)
and [Editor Tasks](../../EDITOR_TASKS.md#task-import-word--import-a-new-word-nofo).
