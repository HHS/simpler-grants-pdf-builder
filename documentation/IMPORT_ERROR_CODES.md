# NOFO import error codes

Every blocking failure in NOFO Builder's Word/HTML import shows the user an
error code. This is what each one means, what the user sees, and what to tell
someone who reports it.

The copy itself lives in [`nofos/bloom_nofos/import_errors.py`](../nofos/bloom_nofos/import_errors.py),
which is the single source of truth - this page describes those entries, it
doesn't define them. `nofos/nofos/tests_nofos/test_import_error_catalog.py`
fails if a code exists in one place and not the other.

## Adding a new code

1. Add an entry to `IMPORT_ERROR_CATALOG` with a title, a summary, recovery
   steps, and the `when` / `support` notes.
2. Raise or map to it from the import views, so the code reaches
   `log_import_attempt()` and the metrics page.
3. Add a section to this page.

A code with no specific message is not finished. If the only honest answer is
"ask someone else," the recovery steps say who to ask.

## Scope

These are NOFO Builder's own import codes, the ones recorded on `ImportAttempt`
and counted by the "Blocking import errors" chart on `/nofos/metrics`. Composer
and Compare import different kinds of document and use their own `COMPOSER-*`
and `COMPARE-*` codes, which are not catalogued here.

## Not the same as import rules

[`IMPORT_RULES.md`](IMPORT_RULES.md) catalogs the content transformations the
import pipeline applies, using numbered IDs like `IMPORT-011`. Those are a
different namespace from the `IMPORT-NAME` codes on this page, which are what a
user is shown when an import is blocked. A rule there can be the reason a code
here fires - `IMPORT-011` is why `IMPORT-AMBIGUOUS-HEADINGS` exists - but the two
registries are maintained separately.

## The codes

### `IMPORT-NO-FILE`

**HTTP status:** 400

**When it fires:** The import form was submitted without a file attached, or the upload did not reach the server.

**What the user sees**

> **Select a document to import**
>
> No file arrived with the import. NOFO Builder needs a Word (.docx) or HTML file to read.

1. Choose a file using the file picker on the import page.
2. Check that the file finished uploading before you submitted the form.

**What support should say:** Usually a mis-click or a dropped upload. Ask the user to select the file again. If it keeps happening on a large document, check whether the upload is timing out.

### `IMPORT-FILE-TYPE`

**HTTP status:** 400

**When it fires:** The uploaded file's content type is neither .docx nor text/html - commonly a PDF, a .doc, or a Google Docs download in the wrong format.

**What the user sees**

> **We can’t import this kind of file**
>
> NOFO Builder imports Word documents (.docx) and HTML files. The selected file is a different format, so there was nothing to read.

1. If this is a PDF or a Google Doc, open it and export or download it as a Word (.docx) file first.
2. If this is an older .doc file, open it in Word and use ‘Save As’ to save it as .docx.
3. Select the new file, then import it again.

**What support should say:** Point the user at ‘Save As .docx’ in Word. The detected file type is shown on the error page, which usually explains what they actually picked.

### `IMPORT-DOCX-CONVERSION`

**HTTP status:** 422

**When it fires:** The .docx-to-HTML conversion raised. The file claims to be a Word document but could not be parsed as one.

**What the user sees**

> **We couldn’t read this Word document**
>
> NOFO Builder could not open the selected Word document. The file may be damaged, incomplete, or still uploading. The document was not imported.

1. Open the document in Word and confirm that it opens normally.
2. Use ‘Save As’ to save it as a new .docx file.
3. Select the new file, then import it again.

**What support should say:** Almost always a damaged or partially copied file. A fresh ‘Save As’ from Word fixes most cases. If it does not, ask for the file so an engineer can try the conversion directly.

### `IMPORT-STRICT-FORMATTING`

**HTTP status:** 422

**When it fires:** WORD_IMPORT_STRICT_MODE is enabled and the Word-to-HTML conversion reported at least one style that is not in the style map and not on the ignore list.

**What the user sees**

> **This document uses formatting we don’t recognize**
>
> Strict import checks are on, and this document uses Word styles that NOFO Builder doesn’t recognize. Importing it would silently drop or garble that content, so the import stopped instead. Nothing was saved.

1. Open the document in Word and show the Styles pane (Home, then the Styles launcher).
2. Look for content using custom or pasted-in styles rather than the NOFO template’s styles, and re-apply the template style - for body text, that is usually ‘Normal’.
3. Save the document, then import it again.
4. If you can’t find it, send this error code and the document to the NOFO Builder team. We can see exactly which styles were flagged.

**What support should say:** The flagged style names are logged server-side but deliberately kept off the error page, since they are converter internals - read them from the logs and tell the user which styles to fix. If a style is legitimate and recurring, that is a style-map gap worth filing rather than asking the user to reformat every time.

### `IMPORT-AMBIGUOUS-HEADINGS`

**HTTP status:** 422

**When it fires:** `resolve_section_heading_level()` found a Heading 2 ahead of the first Heading 1, which makes the section level ambiguous.

**What the user sees**

> **We couldn’t tell which headings are the main sections**
>
> This document uses Heading 2 before its first Heading 1, so NOFO Builder cannot tell which level marks a main section. Importing it would silently skip everything before the first Heading 1, so the import stopped instead. The two headings involved are shown above.

1. Open the document in Word and look at the two headings shown above.
2. Decide which one is a main section, and apply the same heading level to every main section in the document.
3. Save the document, then import it again.

**What support should say:** A single final Heading 1 after multiple Heading 2 headings gets a likely Word fix naming that heading and suggesting Heading 2 if they are all main sections. Other mixed structures keep neutral guidance. Builder does not change the document or guess its intent.

For example, seven Heading 2 headings followed by a single Heading 1 named
"Endnotes" also show this document-specific detail:

> **Likely Word fix**
>
> “Endnotes” uses Heading 1 after 7 headings that use Heading 2. If these are all main sections, in Word, select “Endnotes” and apply the Heading 2 style. Save the document, then import it again.

The suggestion is not specific to Endnotes. It requires at least two nonempty,
non-table Heading 2 headings followed by exactly one final Heading 1, with no
later Heading 2. Other ambiguous patterns retain only the neutral steps above.

### `IMPORT-HEADING-TOO-LONG`

**HTTP status:** 422

**When it fires:** A section or subsection name exceeded the database field's max_length, which in practice means paragraph text carrying a heading style.

**What the user sees**

> **We found text that may have the wrong heading style**
>
> The document contains heading text that is far longer than a heading should be. This usually means a paragraph was formatted as a heading by mistake. The affected text is shown above.

1. Open the document in Word and find the affected text shown above.
2. If it is paragraph text, change its style to ‘Normal’. If it is genuinely a heading, shorten it or apply the correct heading style.
3. Save the document, then import it again.

**What support should say:** The error page names the heading, the limit, and the offending text, so the user can find it in Word directly. This is the most self-serviceable import error we have.

### `IMPORT-NO-SECTIONS`

**HTTP status:** 422

**When it fires:** Parsing produced zero sections - no headings at the resolved section level carried any content.

**What the user sees**

> **We couldn’t find any NOFO content in this document**
>
> NOFO Builder read the file but found no sections in it. Sections come from Word heading styles, so a document whose headings are styled as bold body text instead looks empty to Builder.

1. Open the document in Word and click into each section title.
2. Check the Styles pane: each one should be a real ‘Heading 1’ (or ‘Heading 2’) style, not bold or enlarged Normal text.
3. Apply the correct heading styles, save, then import it again.

**What support should say:** The giveaway is a document that looks perfectly structured to a human but uses manual bold instead of heading styles. Ask the user to check Word's Styles pane, not the visual appearance.

### `IMPORT-OPDIV-BLANK`

**HTTP status:** 400

**When it fires:** The NOFO failed validation with a blank `opdiv` field after parsing the document's first page.

**What the user sees**

> **We couldn’t read the Opdiv from this document**
>
> NOFO Builder couldn’t reliably read a value from the ‘Opdiv:’ field on page 1 of the Word document. The value may be missing, or separated from its label in a way Builder can’t recognize.

1. Open the Word document and go to page 1.
2. Put the agency’s operating division on the same line as ‘Opdiv:’ - for example, ‘Opdiv: Administration for Children and Families’ or ‘Opdiv: CDC’.
3. Save the document, then import it again.

**What support should say:** Most often the value sits in a separate table cell, text box, or line from the ‘Opdiv:’ label. Same line, same paragraph is the fix.

### `IMPORT-CREATE-INVALID`

**HTTP status:** 400

**When it fires:** The parsed document failed model validation while creating a new NOFO, for a reason other than a blank Opdiv or an over-long heading.

**What the user sees**

> **We couldn’t create a NOFO from this document**
>
> NOFO Builder read the document, but the content it found doesn’t make a valid NOFO. What failed is listed above. Nothing was saved.

1. Review the details above and fix the flagged content in Word.
2. Check that the document still has its required fields on page 1 (for example, the opportunity name and the Opdiv line).
3. Save the document, then select it again.

**What support should say:** The ‘What we found’ details name the field and the rule that failed. If the details are not intelligible to the user, that is a bug in this error's copy - file it rather than translating by hand every time.

### `IMPORT-VALIDATION-OTHER`

**HTTP status:** 422

**When it fires:** A validation failure during parsing that none of the specific codes above matched. This is the safety net: a code landing here regularly means it deserves an entry of its own.

**What the user sees**

> **We couldn’t import this document**
>
> NOFO Builder stopped before importing this document. What it found is shown above. Nothing was saved.

1. Read the details above - they name the specific problem in the document.
2. Fix that in Word, save, then import it again.
3. If the details don’t make sense, send this error code and the document to the NOFO Builder team.

**What support should say:** Treat a recurring IMPORT-VALIDATION-OTHER as a bug report. The point of this code is to be rare - look at the metrics page and split out whatever keeps landing in it.

### `REIMPORT-STATUS-BLOCKED`

**HTTP status:** 400

**When it fires:** A re-import was attempted against a NOFO whose status is published, review, doge, or paused.

**What the user sees**

> **We couldn’t re-import this NOFO**
>
> This NOFO’s status is ‘<the NOFO's status>’, and only draft NOFOs can be re-imported. Re-importing replaces the NOFO’s entire contents, so Builder blocks it once a NOFO has moved past drafting. Nothing was changed.

1. If this NOFO is in use, check with your team before changing it - re-importing overwrites everything in it.
2. Return to the NOFO and open its ‘Status’ page.
3. Change the status back to ‘Draft’. Anyone who can edit this NOFO can do this; it does not need an administrator.
4. Re-import the document.

**What support should say:** Self-service: the user changes the status on the NOFO's own status page. Worth confirming they mean to overwrite the NOFO rather than edit it, since re-import is destructive.

### `REIMPORT-DOCUMENT-INVALID`

**HTTP status:** 400

**When it fires:** The replacement document failed model validation during a re-import. The original NOFO is rolled back and kept.

**What the user sees**

> **We couldn’t re-import this NOFO**
>
> NOFO Builder read the document, but the content it found doesn’t make a valid NOFO. What failed is listed above. The existing NOFO was left untouched.

1. Review the details above and fix the flagged content in Word.
2. Check that the document still has its required fields on page 1 (for example, the opportunity name and the Opdiv line).
3. Save the document, then select it again.

**What support should say:** Reassure the user first: a failed re-import does not damage the existing NOFO. Then work the ‘What we found’ details as with IMPORT-CREATE-INVALID.

### `IMPORT-UNEXPECTED`

**HTTP status:** 500

**When it fires:** An unhandled exception during import. The traceback is logged server-side; the user deliberately sees none of it.

**What the user sees**

> **We couldn’t finish importing this document**
>
> Something went wrong inside NOFO Builder - this one is on us, not on your document. Nothing was imported, and nothing was changed.

1. Try the import again - some failures are transient.
2. If it fails again, send this error code, the time it happened, and the document to the NOFO Builder team using the help options below.

**What support should say:** Always a bug on our side. Get the timestamp and the document, then find the logged exception - the user cannot diagnose this one and should not be asked to.
