# Word export downloads an empty document after an unusually long wait

Reported on September 8, 2026 in production for HRSA-27-072 WISH.

## Reproduction

1. Open the [NOFO edit page](https://nofos.simpler.grants.gov/nofos/fb7a783f-5de2-4e80-bd63-1e6fafe3cf4b/edit).
2. Open the NOFO actions menu and select **Export Word doc**.
3. Wait for the loading indicator and download to finish.
4. Open the downloaded Word document.

The corresponding [export page](https://nofos.simpler.grants.gov/nofos/fb7a783f-5de2-4e80-bd63-1e6fafe3cf4b/export) identifies the affected export route.

**Expected:** A Word document containing the NOFO content. If conversion fails, show an error instead of downloading an empty document.

**Actual (user reported):** The loading indicator lasts longer than usual, then an empty Word document downloads. The elapsed time was not measured. Scope beyond this NOFO is unknown.

## Confirmed evidence

Both supplied downloads, `HRSA-27-072 WISH.docx` and `HRSA-27-072 WISH (1).docx`, are readable DOCX ZIP packages. In both, `word/document.xml` contains a `w:body` with only `w:sectPr` (page/section settings): no paragraphs, tables, text, or drawings. Their document XML is identical. This establishes absent content in the downloaded files, rather than merely a Word display problem.

The original attachments are not committed. Live authenticated reproduction and production logs have not yet been inspected.

## Investigation status

Root cause is not confirmed. Start by tracing the authenticated export page, the `#download_target` element, and the GrabzIt conversion result. Check the conversion's page access and timing, and whether empty output is incorrectly returned as a successful download.

## Verification criteria

- Re-export the affected NOFO and confirm that its substantive content is present in Word.
- An empty or failed conversion produces a visible error and no successful download.
- Confirm the normal Word export still works for another populated NOFO.
- Record measured conversion duration and investigate any remaining delay.
