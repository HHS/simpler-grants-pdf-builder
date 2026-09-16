"""
The catalog of NOFO import error codes (see #913).

Every blocking import failure a user can hit has exactly one entry here. An
entry owns the copy shown on the error page - the title, the summary, and the
recovery steps - plus the two notes the documentation and the support team
work from: `when` (what makes this fire) and `support` (what to tell someone
who reports it).

This is the single source of truth. `documentation/IMPORT_ERROR_CODES.md`
describes the same codes for people, and
`nofos/tests_nofos/test_import_error_catalog.py` fails if the two drift apart
or if a code is logged that never got an entry here.

Copy rules, so the pages stay consistent and usable:

- The summary says what happened, in the user's terms. Not "an error
  occurred": what about their document stopped the import.
- Recovery steps are things the user can actually do, in order. If the only
  real answer is "ask someone else," name who.
- Specifics that vary per failure (the offending heading, the styles Word
  reported, the NOFO's status) belong in `error_details` at the call site,
  not baked into these strings.
- Avoid curly braces in copy unless they are an intentional placeholder:
  entries are run through `str.format()` when a call site passes context.
"""

# Steps shared by the two "the document didn't produce a valid NOFO" codes.
# Kept here rather than in error_helpers so the catalog stays self-contained.
DOCUMENT_STRUCTURE_RECOVERY_STEPS = (
    "Review the details above and fix the flagged content in Word.",
    "Check that the document still has its required fields on page 1 "
    "(for example, the opportunity name and the Opdiv line).",
    "Save the document, then select it again.",
)


IMPORT_ERROR_CATALOG = {
    "IMPORT-NO-FILE": {
        "title": "Select a document to import",
        "summary": (
            "No file arrived with the import. NOFO Builder needs a Word "
            "(.docx) or HTML file to read."
        ),
        "status": 400,
        "recovery_steps": (
            "Choose a file using the file picker on the import page.",
            "Check that the file finished uploading before you submitted the form.",
        ),
        "when": (
            "The import form was submitted without a file attached, or the "
            "upload did not reach the server."
        ),
        "support": (
            "Usually a mis-click or a dropped upload. Ask the user to select "
            "the file again. If it keeps happening on a large document, check "
            "whether the upload is timing out."
        ),
    },
    "IMPORT-FILE-TYPE": {
        "title": "We can’t import this kind of file",
        "summary": (
            "NOFO Builder imports Word documents (.docx) and HTML files. The "
            "selected file is a different format, so there was nothing to read."
        ),
        "status": 400,
        "recovery_steps": (
            "If this is a PDF or a Google Doc, open it and export or download "
            "it as a Word (.docx) file first.",
            "If this is an older .doc file, open it in Word and use "
            "‘Save As’ to save it as .docx.",
            "Select the new file, then import it again.",
        ),
        "when": (
            "The uploaded file's content type is neither .docx nor text/html - "
            "commonly a PDF, a .doc, or a Google Docs download in the wrong "
            "format."
        ),
        "support": (
            "Point the user at ‘Save As .docx’ in Word. The detected file type "
            "is shown on the error page, which usually explains what they "
            "actually picked."
        ),
    },
    "IMPORT-DOCX-CONVERSION": {
        "title": "We couldn’t read this Word document",
        "summary": (
            "NOFO Builder could not open the selected Word document. The file "
            "may be damaged, incomplete, or still uploading. The document was "
            "not imported."
        ),
        "status": 422,
        "recovery_steps": (
            "Open the document in Word and confirm that it opens normally.",
            "Use ‘Save As’ to save it as a new .docx file.",
            "Select the new file, then import it again.",
        ),
        "when": (
            "The .docx-to-HTML conversion raised. The file claims to be a Word "
            "document but could not be parsed as one."
        ),
        "support": (
            "Almost always a damaged or partially copied file. A fresh ‘Save "
            "As’ from Word fixes most cases. If it does not, ask for the file "
            "so an engineer can try the conversion directly."
        ),
    },
    "IMPORT-STRICT-FORMATTING": {
        "title": "This document uses formatting we don’t recognize",
        "summary": (
            "Strict import checks are on, and this document uses Word styles "
            "that NOFO Builder doesn’t recognize. Importing it would silently "
            "drop or garble that content, so the import stopped instead. "
            "Nothing was saved."
        ),
        "status": 422,
        "recovery_steps": (
            "Open the document in Word and show the Styles pane "
            "(Home, then the Styles launcher).",
            "Look for content using custom or pasted-in styles rather than the "
            "NOFO template’s styles, and re-apply the template style - for body "
            "text, that is usually ‘Normal’.",
            "Save the document, then import it again.",
            "If you can’t find it, send this error code and the document to the "
            "NOFO Builder team. We can see exactly which styles were flagged.",
        ),
        "when": (
            "WORD_IMPORT_STRICT_MODE is enabled and the Word-to-HTML conversion "
            "reported at least one style that is not in the style map and not "
            "on the ignore list."
        ),
        "support": (
            "The flagged style names are logged server-side but deliberately "
            "kept off the error page, since they are converter internals - read "
            "them from the logs and tell the user which styles to fix. If a "
            "style is legitimate and recurring, that is a style-map gap worth "
            "filing rather than asking the user to reformat every time."
        ),
    },
    "IMPORT-AMBIGUOUS-HEADINGS": {
        "title": "We couldn’t tell which headings are the main sections",
        "summary": (
            "This document uses Heading 2 before its first Heading 1, so NOFO "
            "Builder cannot tell which level marks a main section. Importing it "
            "would silently skip everything before the first Heading 1, so the "
            "import stopped instead. The two headings involved are shown above."
        ),
        "status": 422,
        "recovery_steps": (
            "Open the document in Word and look at the two headings shown above.",
            "Decide which one is a main section, and apply the same heading "
            "level to every main section in the document.",
            "Save the document, then import it again.",
        ),
        "when": (
            "`resolve_section_heading_level()` found a Heading 2 ahead of the "
            "first Heading 1, which makes the section level ambiguous."
        ),
        "support": (
            "Usually a title or preamble styled as Heading 2. The fix is in the "
            "document, not in Builder: one consistent heading level for main "
            "sections."
        ),
    },
    "IMPORT-HEADING-TOO-LONG": {
        "title": "We found text that may have the wrong heading style",
        "summary": (
            "The document contains heading text that is far longer than a "
            "heading should be. This usually means a paragraph was formatted as "
            "a heading by mistake. The affected text is shown above."
        ),
        "status": 422,
        "recovery_steps": (
            "Open the document in Word and find the affected text shown above.",
            "If it is paragraph text, change its style to ‘Normal’. If it is "
            "genuinely a heading, shorten it or apply the correct heading style.",
            "Save the document, then import it again.",
        ),
        "when": (
            "A section or subsection name exceeded the database field's "
            "max_length, which in practice means paragraph text carrying a "
            "heading style."
        ),
        "support": (
            "The error page names the heading, the limit, and the offending "
            "text, so the user can find it in Word directly. This is the most "
            "self-serviceable import error we have."
        ),
    },
    "IMPORT-NO-SECTIONS": {
        "title": "We couldn’t find any NOFO content in this document",
        "summary": (
            "NOFO Builder read the file but found no sections in it. Sections "
            "come from Word heading styles, so a document whose headings are "
            "styled as bold body text instead looks empty to Builder."
        ),
        "status": 422,
        "recovery_steps": (
            "Open the document in Word and click into each section title.",
            "Check the Styles pane: each one should be a real ‘Heading 1’ (or "
            "‘Heading 2’) style, not bold or enlarged Normal text.",
            "Apply the correct heading styles, save, then import it again.",
        ),
        "when": (
            "Parsing produced zero sections - no headings at the resolved "
            "section level carried any content."
        ),
        "support": (
            "The giveaway is a document that looks perfectly structured to a "
            "human but uses manual bold instead of heading styles. Ask the user "
            "to check Word's Styles pane, not the visual appearance."
        ),
    },
    "IMPORT-OPDIV-BLANK": {
        "title": "We couldn’t read the Opdiv from this document",
        "summary": (
            "NOFO Builder couldn’t reliably read a value from the ‘Opdiv:’ "
            "field on page 1 of the Word document. The value may be missing, or "
            "separated from its label in a way Builder can’t recognize."
        ),
        "status": 400,
        "recovery_steps": (
            "Open the Word document and go to page 1.",
            "Put the agency’s operating division on the same line as ‘Opdiv:’ - "
            "for example, ‘Opdiv: Administration for Children and Families’ or "
            "‘Opdiv: CDC’.",
            "Save the document, then import it again.",
        ),
        "when": (
            "The NOFO failed validation with a blank `opdiv` field after "
            "parsing the document's first page."
        ),
        "support": (
            "Most often the value sits in a separate table cell, text box, or "
            "line from the ‘Opdiv:’ label. Same line, same paragraph is the fix."
        ),
    },
    "IMPORT-CREATE-INVALID": {
        "title": "We couldn’t create a NOFO from this document",
        "summary": (
            "NOFO Builder read the document, but the content it found doesn’t "
            "make a valid NOFO. What failed is listed above. Nothing was saved."
        ),
        "status": 400,
        "recovery_steps": DOCUMENT_STRUCTURE_RECOVERY_STEPS,
        "when": (
            "The parsed document failed model validation while creating a new "
            "NOFO, for a reason other than a blank Opdiv or an over-long "
            "heading."
        ),
        "support": (
            "The ‘What we found’ details name the field and the rule that "
            "failed. If the details are not intelligible to the user, that is a "
            "bug in this error's copy - file it rather than translating by hand "
            "every time."
        ),
    },
    "IMPORT-VALIDATION-OTHER": {
        "title": "We couldn’t import this document",
        "summary": (
            "NOFO Builder stopped before importing this document. What it found "
            "is shown above. Nothing was saved."
        ),
        "status": 422,
        "recovery_steps": (
            "Read the details above - they name the specific problem in the "
            "document.",
            "Fix that in Word, save, then import it again.",
            "If the details don’t make sense, send this error code and the "
            "document to the NOFO Builder team.",
        ),
        "when": (
            "A validation failure during parsing that none of the specific "
            "codes above matched. This is the safety net: a code landing here "
            "regularly means it deserves an entry of its own."
        ),
        "support": (
            "Treat a recurring IMPORT-VALIDATION-OTHER as a bug report. The "
            "point of this code is to be rare - look at the metrics page and "
            "split out whatever keeps landing in it."
        ),
    },
    "REIMPORT-STATUS-BLOCKED": {
        "title": "We couldn’t re-import this NOFO",
        "summary": (
            "This NOFO’s status is ‘{status}’, and only draft NOFOs can be "
            "re-imported. Re-importing replaces the NOFO’s entire contents, so "
            "Builder blocks it once a NOFO has moved past drafting. Nothing was "
            "changed."
        ),
        "status": 400,
        "recovery_steps": (
            "If this NOFO is in use, check with your team before changing it - "
            "re-importing overwrites everything in it.",
            "Return to the NOFO and open its ‘Status’ page.",
            "Change the status back to ‘Draft’. Anyone who can edit this NOFO "
            "can do this; it does not need an administrator.",
            "Re-import the document.",
        ),
        "when": (
            "A re-import was attempted against a NOFO whose status is "
            "published, review, doge, or paused."
        ),
        "support": (
            "Self-service: the user changes the status on the NOFO's own status "
            "page. Worth confirming they mean to overwrite the NOFO rather than "
            "edit it, since re-import is destructive."
        ),
    },
    "REIMPORT-DOCUMENT-INVALID": {
        "title": "We couldn’t re-import this NOFO",
        "summary": (
            "NOFO Builder read the document, but the content it found doesn’t "
            "make a valid NOFO. What failed is listed above. The existing NOFO "
            "was left untouched."
        ),
        "status": 400,
        "recovery_steps": DOCUMENT_STRUCTURE_RECOVERY_STEPS,
        "when": (
            "The replacement document failed model validation during a "
            "re-import. The original NOFO is rolled back and kept."
        ),
        "support": (
            "Reassure the user first: a failed re-import does not damage the "
            "existing NOFO. Then work the ‘What we found’ details as with "
            "IMPORT-CREATE-INVALID."
        ),
    },
    "IMPORT-UNEXPECTED": {
        "title": "We couldn’t finish importing this document",
        "summary": (
            "Something went wrong inside NOFO Builder - this one is on us, not "
            "on your document. Nothing was imported, and nothing was changed."
        ),
        "status": 500,
        "recovery_steps": (
            "Try the import again - some failures are transient.",
            "If it fails again, send this error code, the time it happened, and "
            "the document to the NOFO Builder team using the help options below.",
        ),
        "when": (
            "An unhandled exception during import. The traceback is logged "
            "server-side; the user deliberately sees none of it."
        ),
        "support": (
            "Always a bug on our side. Get the timestamp and the document, then "
            "find the logged exception - the user cannot diagnose this one and "
            "should not be asked to."
        ),
    },
}
