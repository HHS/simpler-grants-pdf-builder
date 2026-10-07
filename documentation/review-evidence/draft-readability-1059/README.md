# Draft readability scope verification

Local authenticated Chrome verification on October 7, 2026, against the branch
for #1059 with an isolated SQLite database and a synthetic pilot participant.
The public pilot was disabled throughout. No private source was uploaded in the
browser or included in screenshots.

- [Upload guidance](upload.jpg): expanded PDF requirements explain draft use,
  writer-note effects, and blank-template recognition limits.
- [Report](report.jpg): real synthetic upload through the subprocess worker;
  reference denominators and all five displayed values; draft scope and readiness
  caveats remain visible alongside the existing reliability warning.

The test fixture contains 17 applicant prose words and six heading words, with
three sentences, two prose paragraphs, 21 syllables, and one passive sentence.
This verifies the small controlled reference, not private-document accuracy.

- [Print-style recognition](print-recognition.jpg): authenticated Chrome upload
  of an untagged, synthetic four-page PDF without descriptive agency metadata.
  The opportunity number is on page one and agency name on page three. The
  subprocess returns a report with the expected low-reliability warning.
  Inferred paragraph boundaries differ from the tagged reference, so this does
  not establish five-metric parity for untagged exports.

After the recognition fix, the six local private exports retain their expected
recognition results: five supported and the blank guide unsupported. The real
Word print export also completes analysis. No private content is committed.

No application flags outside the isolated local database changed. No deployment
or clearance determination was made. See the durable guide for matrix gaps.
