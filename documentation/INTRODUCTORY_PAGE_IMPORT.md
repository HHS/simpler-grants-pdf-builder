# Introductory pages in Word imports

Builder supports two source headings: **Before You Begin** and **Before You Get
Started**. Retain this section in your upload. Builder uses its real heading and
bookmark destinations to choose a maintained introductory page and preserve
incoming links, then consumes the source heading and its bounded body. Edits to
that source body never replace or supplement Builder's generated wording.

## Link setup in Word

Use a real Heading 1–6 paragraph for the introductory heading. Select the linked
phrase in Step 2 and choose **Place in This Document** (Windows) or **This
Document** (Mac), then select that heading or a named bookmark at the heading.
Do not type Builder's anchor ID, a public URL or a page number. Word-generated
bookmarks and named bookmarks are both accepted. The source phrase retains its
authored casing; the new generated heading, contents entry and PDF running
footer use **Before you get started**.

Builder routes a unique source destination to the stable
`section--before-you-begin` anchor. Conflicting or repeated introductory
headings, or duplicate destination IDs, are not guessed: the legacy presentation
remains and links to consumed ambiguous destinations become plain authored
text. Missing targets and unrelated internal/external links are unchanged.
Selecting None also renders links to the generated introductory destination as
plain text, without rewriting the saved body.

Consumption stops at a peer/higher heading, a recognized metadata label, a
recognized Metadata block even at a lower heading level, or a note heading/native
note list. Subsequent program content, metadata, appendices and notes remain.
Phrases such as “To register:” are source body, not metadata boundaries.

## Family and registration variant

`introductory_page_family` is a saved discriminator, separate from the existing
registration variant. Existing records have an empty discriminator and keep
their legacy presentation and historical Word-export behavior. No content-based
backfill runs. A recognized legacy upload stores `legacy`; a recognized new
upload stores `get_started`. An absent or ambiguous heading stores the empty
legacy fallback. Authorized re-import selects the incoming family but preserves
the saved variant; confirmation serializes the captured family with processed
HTML, and failed imports roll back family and content together. Duplication and
archive snapshots copy both saved values. Composer/Compare do not opt into this
Builder family selection; guide Introduction behavior is unchanged.

| Saved variant | New family registration content | Legacy family |
| --- | --- | --- |
| full | SAM.gov + Grants.gov | Existing full wording |
| era | SAM.gov + Grants.gov + eRA Commons | Existing eRA wording |
| sole_source | SAM.gov only | Existing sole-source wording |
| hrsa | Same new full registration, no HRSA requirements | Existing HRSA wording and requirements |
| none | No introductory page | Existing None behavior |

First import defaults are unchanged except new-family HRSA uses full. HRSA theme
takes precedence over NIH importing group: legacy → hrsa; new → full. Otherwise
NIH importing group selects era, other groups select full. This is a group check,
not an invented NIH OpDiv default. Re-import never resets a saved choice; a saved
hrsa value remains hrsa even though new-family registration uses the full body.

## Wording provenance and outputs

The new isolated registration partial follows the supplied October 5, 2026 draft
HHS NOFO master, not a claim of an officially issued final template. Full includes
both SAM.gov and Grants.gov; eRA adds eRA Commons; sole source includes only SAM.gov.
Generated deadline and keyboard-navigation functions remain. Deadline comes from
the record's Application Deadline metadata, not the Application Due Date section.
The only copy correction is the missing period after the Grants.gov registration
link. Source URLs are retained: the HTTP Quick Start URL redirects to the HTTPS
Quick Start page; SAM.gov `/content/entity-registration` redirects to
`/entity-registration`. No canonical-link substitution was made.

Normal Word-export HTML includes the maintained introduction for explicitly
recognized legacy/new imports, giving remapped links a destination. Unclassified
existing records retain their previous normal Word export. PDF uses the generated
H2 as `sectiontitle` for running footers; Word is a separate export path and does
not inherit Prince margin CSS. Check actual generated Word bookmarks and footer
behavior separately using dedicated allowed-environment credentials. Template
tests and browser HTML are not provider-generated DOCX proof.

Re-importing while No BYB page is selected retains the canonical introductory link in stored content. Rendering hides the link while disabled; selecting Full or another enabled variant restores it without another import.
