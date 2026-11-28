# NOFO content contract (proposal)

- **Status:** proposal for discussion. Not adopted, not implemented.
- **Related issue:** [#851](https://github.com/HHS/simpler-grants-pdf-builder/issues/851) (Goal 2: whether the web redesign targets FOAM's own template or something the Builder generates)
- **Source baseline:** `main` at `1f7c527`, reviewed 2026-11-28; CommonGrants protocol v0.5.0 (HHS/simpler-grants-protocol at `ad104f2`)
- **Evidence:** the #851 spike in [`review-evidence/851/`](../../review-evidence/851/README.md) (added by PR #1439) has the web prototypes this contract is drawn from

## Why a contract

NOFOs are written in more than one system. NIH authors them in eRA's FOAM, which is their source of truth and publishes a "Full Announcement" HTML file to Grants.gov. Other OpDivs use the Builder, which makes the PDF. The #851 spike prototyped an accessible web version of a NOFO, and the question is how FOAM could produce the same design from its own content.

Handing eRA a finished HTML file from the Builder would create a second copy of FOAM's content that goes out of date with the first edit. This proposal keeps content and publishing with whoever owns them, and shares three things instead:

1. A **component vocabulary**: what each block of a NOFO is, which drives its markup and design.
2. **Stable keys** for the standard parts of a NOFO, so any system can map its own fields to them and other sites can deep-link to them.
3. A **JSON shape** for exchanging a NOFO's content, plus a markup spec and conformance checks, so any renderer can produce matching HTML.

None of this depends on the Builder's Python code. FOAM, the Builder and Simpler.Grants.gov could each implement it in their own stack.

## Limitations

- **Stable keys don't exist today.** The Builder's only identifiers are per-record `html_id`s built from position and heading text (for example `8--step-1-review-the-opportunity--eligible-applicants`). They differ between NOFOs and change when a section moves or is renamed. Content guides and policy-language slot keys exist in the codebase but aren't in active use, so they aren't a foundation. Keys would be new work; see [Assigning keys](#assigning-keys).
- **The key list is a draft.** It comes from the Builder's standard step names (the ones its icon logic recognizes) and the headings of one real NOFO in the test fixtures (CMS-2U2-25-001). It needs checking against the current HHS NOFO templates and against FOAM's structure.
- **FOAM's data model is unknown.** The public Full Announcement has a Part and Section structure, which suggests structured fields, but that is an inference from output.

## Roles

| Role | Who | Responsibility |
| --- | --- | --- |
| Content owner | FOAM for NIH NOFOs; the Builder (from the approved Word file) for other OpDivs | Holds and edits the NOFO's content |
| Renderer | Whoever publishes the web page | Turns contract JSON (or its own data, mapped to the contract) into HTML that follows the markup spec |
| Design and contract maintainers | Proposed: the Builder team, with eRA and Simpler.Grants.gov | Version the vocabulary, keys, markup spec, CSS and conformance fixtures |

## Component vocabulary

Each block declares its component with `data-nofo-component`. Components carry design and accessibility behavior, not meaning; meaning comes from keys.

| Component | What it is | Markup notes (from the #851 prototypes) |
| --- | --- | --- |
| `introduction` | "Before you begin" or "Before you get started" content | A section before the steps |
| `step` | A numbered step | `<section>` with an h2; the "Step N" label is part of the heading text |
| `section` | Unnumbered top-level content: contacts, endnotes, appendix, modifications, or anything non-standard | `<section>` with an h2 |
| `subsection` | A heading and its body | h3–h6; deeper levels use `role="heading"` with `aria-level` |
| `facts` | "Label: value" content such as key facts, key dates and funding details | `<dl>`; dates use `<time datetime>` with a time zone |
| `callout` | A highlighted box with optional heading | USWDS summary box |
| `note` | A one-line caveat with a bold lead-in | Ordinary paragraph; the lead-in carries the meaning |
| `table` | A data table | `<caption>`, header `scope`; simple tables stack on phones, wide ones scroll in a labelled, focusable container |
| `checklist` | A table of application items with checkboxes | Decorative checkbox icons with empty alt text |
| `points` | "Maximum points" for a review criterion | A label under its heading, not a heading |
| `deadlines` | Several application deadlines or phases | USWDS process list, or a list when short |
| `endnotes` | Endnotes with return links | Ordered list; each note links back to its citation |
| `appendix` | Appendices | A labelled back-matter section |
| `modifications` | The modification record | A table, linked from a "Last modified" banner |

## Keys

A key names a standard part of a NOFO, independent of its heading text or position. Keys are lowercase, dot-separated, and stable across NOFOs and versions.

### Metadata keys

Metadata uses [CommonGrants](https://commongrants.org/) field names **and shapes**, so the same values work in FOAM, the Builder and Simpler.Grants.gov without translation. See [Relationship to CommonGrants](#relationship-to-commongrants).

| Key | Builder field | CommonGrants shape |
| --- | --- | --- |
| `title` | `title` | `title` (string) |
| `identifiers.opp:us:fon` | `number` | Identifier: `{registry: {code: "opp:us:fon"}, id}` |
| `identifiers.opp:us:aln` | `assistance_listing_number` | Identifier: `{registry: {code: "opp:us:aln"}, id}` |
| `funders.primary` | `opdiv` | Organization reference: `{name}` (`id` is assigned by the hosting system) |
| `funders.otherOrgs.agency`, `funders.otherOrgs.subagency`, `funders.otherOrgs.subagency2` | `agency`, `subagency`, `subagency2` | Organization references keyed by role |
| `keyDates.closeDate` | `application_deadline` (first date) | Single-date event: `{name, eventType: "singleDate", date, time?, description?}` |
| `keyDates.otherDates.*` | Other dates in the NOFO text | Events keyed by name |

Values CommonGrants has no field for go in the document's `extensions` block, not alongside the CommonGrants fields:

| Extension | Builder field | Why it's an extension |
| --- | --- | --- |
| `timeZone` | None (the NOFO text states it) | CommonGrants event times have no time zone |
| `tagline` | `tagline` | No CommonGrants field |
| `modifiedAt` | `modifications` | No amendment model in CommonGrants |
| `relatedOpportunities` | None (free text today) | No CommonGrants field for companion, component or reissue links |

### Section keys (draft)

Step keys are matched to the Builder's standard step names. Subsection keys come from the CMS fixture's headings and need validation.

| Key | Typical heading |
| --- | --- |
| `introduction` | Before you begin / Before you get started |
| `introduction.registration.sam` | SAM.gov registration |
| `introduction.registration.grants-gov` | Grants.gov registration |
| `introduction.registration.era` | eRA Commons registration |
| `introduction.apply-by` | Apply by the application due date |
| `review` | Step 1: Review the (Funding) Opportunity |
| `review.summary` | Summary |
| `review.key-facts` | Key facts |
| `review.key-dates` | Key dates |
| `review.funding-details` | Funding details |
| `eligibility` | Eligibility |
| `eligibility.eligible-applicants` | Eligible applicants |
| `eligibility.cost-sharing` | Cost sharing |
| `program` | Program description |
| `program.purpose` | Purpose |
| `program.background` | Background |
| `program.requirements` | Program requirements and expectations |
| `program.funding-policies` | Funding policies and limitations |
| `program.statutory-authority` | Statutory authority |
| `get-ready` | Step 2: Get Ready to Apply |
| `get-ready.registration` | Get registered |
| `get-ready.application-package` | Find the application package |
| `get-ready.application-contents` | Application contents and format |
| `get-ready.project-abstract` | Project abstract |
| `get-ready.project-narrative` | Project narrative |
| `get-ready.budget-narrative` | Budget narrative |
| `get-ready.attachments` | Attachments |
| `get-ready.other-forms` | Other required forms |
| `write` | Step 3: Write / Prepare / Build Your Application |
| `review-award` | Step 4: Learn About (or Understand) Review and Award |
| `review-award.initial-review` | Initial review |
| `review-award.merit-review` | Merit review |
| `review-award.criteria` | Criteria |
| `review-award.risk-review` | Risk review |
| `review-award.selection` | Selection process |
| `review-award.award-notices` | Award notices |
| `submit` | Step 5: Submit Your Application |
| `submit.deadlines` | Deadlines |
| `submit.methods` | Submission methods |
| `submit.other-submissions` | Other submissions |
| `submit.checklist` | Application checklist |
| `after-award` | Step 6: Learn What Happens After Award |
| `after-award.requirements` | Post-award requirements and administration |
| `after-award.reporting` | Reporting |
| `contacts` | Contacts and Support |
| `contacts.agency` | Agency contacts |
| `endnotes` | Endnotes |
| `appendix` | Appendix / Appendices |
| `modifications` | Modifications |

Content without a key is still valid: it renders as an unkeyed `section` or `subsection` with its own heading, so nothing is lost.

## Markup spec

- Keyed elements carry `data-nofo-key` with the full key and an `id` made by replacing dots with hyphens (`eligibility.eligible-applicants` becomes `id="eligibility-eligible-applicants"`). These IDs are what other sites deep-link to, so they must not change between versions of a NOFO.
- Unkeyed elements get a renderer-generated `id` that is unique on the page.
- Metadata values carry `data-nofo-field` with their metadata key.
- The page declares its contract version: `<meta name="nofo-contract-version" content="0.1.0">`.
- Accessibility requirements, all met by the #851 prototypes:
  - one h1 per page and no skipped heading levels; source siblings stay siblings;
  - a visible, keyboard-reachable link on every heading, named "Link to this section: …";
  - a target highlight on the heading a link opens, distinct from focus, with focus moved to it;
  - "On this page" navigation built from the headings, listing the current step's subsections;
  - captions and header scope on tables, and lists that keep their numbering types;
  - deadlines in `<time datetime>` with the time zone.

```html
<meta name="nofo-contract-version" content="0.1.0">

<h1 data-nofo-field="title">Rural Health Workforce Pathways</h1>

<section id="eligibility" data-nofo-component="subsection" data-nofo-key="eligibility">
  <h3>Eligibility</h3>
  <div id="eligibility-eligible-applicants" data-nofo-component="subsection"
       data-nofo-key="eligibility.eligible-applicants">
    <h4>Eligible applicants</h4>
    <p>…</p>
  </div>
</section>

<dl data-nofo-component="facts" data-nofo-key="review.key-dates">
  <div data-nofo-field="keyDates.closeDate">
    <dt>Application deadline</dt>
    <dd><time datetime="2027-01-15T23:59-05:00">January 15, 2027, 11:59 p.m. ET</time></dd>
  </div>
</dl>
```

## JSON shape

A content owner exports, or a renderer reads, one document per NOFO version. It has three parts:

- `opportunity`: metadata as a subset of the CommonGrants opportunity, in exactly its shapes;
- `extensions`: values CommonGrants has no field for;
- `sections`: the NOFO's content, keyed where it matches a standard part.

Bodies are Markdown, as the Builder stores them. A JSON Schema would follow once the shape is agreed, reusing the CommonGrants schemas for the `opportunity` part.

```json
{
  "contractVersion": "0.1.0",
  "opportunity": {
    "title": "Rural Health Workforce Pathways",
    "identifiers": {
      "opp:us:fon": { "registry": { "code": "opp:us:fon" }, "id": "HRSA-27-101" },
      "opp:us:aln": { "registry": { "code": "opp:us:aln" }, "id": "93.000" }
    },
    "funders": {
      "primary": { "name": "Health Resources and Services Administration (HRSA)" },
      "otherOrgs": { "agency": { "name": "Bureau of Health Workforce" } }
    },
    "keyDates": {
      "closeDate": {
        "name": "Application deadline",
        "eventType": "singleDate",
        "date": "2027-01-15",
        "time": "23:59:00",
        "description": "Applications are due by 11:59 p.m. Eastern Time."
      }
    }
  },
  "extensions": {
    "timeZone": "America/New_York",
    "tagline": "Helping rural communities grow their health workforce.",
    "modifiedAt": null,
    "relatedOpportunities": [{ "fon": "HRSA-27-102", "relationship": "companion" }]
  },
  "sections": [
    {
      "key": "review",
      "component": "step",
      "heading": "Step 1: Review the Opportunity",
      "children": [
        { "key": "review.summary", "component": "subsection", "heading": "Summary", "level": 3, "body": "This program funds…" },
        { "key": null, "component": "note", "body": "**Note for current recipients:** Apply under HRSA-27-102." }
      ]
    }
  ]
}
```

`relatedOpportunities` comes from the #851 edge-case findings: companion, component and reissue relationships currently exist only as free text in listings. The time zone is repeated in the event's `description` so a CommonGrants-only reader still sees it.

## Relationship to CommonGrants

CommonGrants is the protocol Simpler.Grants.gov already serves for opportunity listings. This contract fits around it in three layers:

1. **Listing metadata is CommonGrants.** The `opportunity` part uses CommonGrants shapes exactly, so a NOFO page and its listing describe the same opportunity in the same format.
2. **The listing links to the NOFO through CommonGrants custom fields.** CommonGrants allows extensions only in `customFields`, so the opportunity record would point to the NOFO with two custom fields, as proposed in the #851 evidence: `nofoDocument` (web page and PDF addresses, version, contract version) and `nofoSections` (each keyed section's key, title and address). The section keys there are the keys defined here, which lets Simpler.Grants.gov build "go straight to" links from data instead of heading text.
3. **NOFO content is a separate document.** CommonGrants has no model for NOFO content and doesn't allow extra top-level fields. Putting a whole NOFO into custom fields would also make every listing response very large. The contract document is its own type, linked from the listing.

The gaps this contract works around are listed in the next section.

## Gaps between CommonGrants and NOFO content

Patterns that Builder NOFOs and live Simpler.Grants.gov listings show, compared with CommonGrants v0.5.0. Evidence comes from the CMS-2U2-25-001 fixture and the listings recorded in the #851 evidence. Each gap has a suggested route:

- **Protocol:** a change to the CommonGrants core models;
- **Catalog:** a new field in the shared custom-field catalog;
- **Docs:** guidance on using existing fields.

| NOFO pattern | CommonGrants today | Gap | Evidence | Suggested route |
| --- | --- | --- | --- | --- |
| NOFO content: steps, sections, eligibility and review criteria, application requirements | No model; extensions only in `customFields` | No home for NOFO content or its structure | Every NOFO | Catalog: `nofoDocument` and `nofoSections` linking to a separate content document (this contract) |
| Deadlines at a stated time in a stated zone ("11:59 p.m. Eastern Time") | Events have `date` and `time`, no time zone | A deadline can't be stated precisely | Every NOFO | Protocol: a time zone on events; this contract carries `extensions.timeZone` meanwhile |
| Several deadlines with meaning: required or optional letter of intent, pre-application then invited application, rounds | `closeDate` plus untyped `otherDates` | No event types such as letter of intent or pre-application, and no required/optional flag | CMS fixture (optional LOI); AFOSR FA955026S0003 white papers; NASA NNH25ZDA001N two steps | Protocol or Catalog: typed key-date roles |
| Rolling or continuous applications | A single `closeDate` | No way to say "rolling", which leads to placeholder dates | State Department OFOP0002825 (close date 2099-01-01) | Protocol: an application-period type, or Docs: leave `closeDate` null and describe the period |
| Companion, component and reissue opportunities | Nothing | Relationships exist only as free text | NIH PA-24-190/191 ("companion FOA ()"); RFA-FD-25-020 reissue | Catalog: related opportunities with a relationship type |
| Funding structure: base plus optional add-on, per-year versus whole-period amounts, period of performance | Min, max, total, counts and free-text `details` | No per-year versus total distinction, no add-on amounts, no period of performance | CMS fixture ($250,000 base plus $125,000 add-on over 3 years); AFOSR minimum is a yearly cap, maximum a 3-year total | Protocol: amount basis and performance period |
| Components or tracks with their own eligibility, funding and deadlines | One funding block per opportunity; competitions (experimental) have dates and applicant types but no funding | No per-component funding | NIOSH RFA-OH-27-049; NCI RFA-CA-26-010; RESTORE Act GR-RDC-25-001/002 | Protocol: funding on competitions |
| Several contacts by role (program, budget, grants management) | `contactInfo` custom field holds one contact | No list of contacts with roles | CMS fixture "Agency contacts" | Catalog: contacts as a list with roles |
| Limited competition or single source | `acceptedApplicantTypes` and free-text eligibility details | No limited-competition flag | NIH PAR-27-009 ("Single Source"); USDA non-competitive formula grant | Catalog: competition type |
| Applications submitted outside Grants.gov | One `additionalInfo` link | No field naming the application system | Fish and Wildlife F24AS00022 (GrantSolutions only); State Department MyGrants listings | Catalog: application system and address |
| Statuses beyond forecasted, open and closed | `custom` with a free-text value | Archived and cancelled aren't standard values | Simpler.Grants.gov uses `custom` with "archived" | Protocol: add archived and cancelled |
| Amendments and versions | `lastModifiedAt` only | No amendment record, and timestamps aren't reliable | AFOSR amendment PDFs; NASA amendment only in the description, with created and modified dates equal | Protocol or Catalog: an amendment list with dates and summaries |
| What an attachment is | File with name, type and size | No role, such as NOFO, amendment, template or FAQ | AFOSR's six attachments; NIH stub "Full Announcement" files of 420–422 bytes | Catalog: a role on attachments |
| Rich text | `description`, `details` and `instructions` are untyped strings | HTML, Markdown or plain text isn't specified | Simpler.Grants.gov descriptions carry inline-styled HTML; the Builder stores Markdown | Protocol: a declared format, or Docs: one required format |
| Translations | Nothing | No language or alternate-language versions | USAID 72052024RFI00001 (separate English and Spanish forms) | Protocol: language and alternates |
| Agency hierarchy (OpDiv, agency, subagencies) | `funders.primary` plus `otherOrgs` keyed by role | Role names aren't defined | Builder `agency`, `subagency`, `subagency2` | Docs: a shared role vocabulary |

Documentation gaps, where the field exists but guidance doesn't:

- **Unknown values:** no rule that an unknown value should be null rather than a placeholder such as $0, $1 or 2099-01-01. Live listings use all three.
- **Time zones:** no statement of which zone an event's `time` is in.
- **Organization roles:** no shared names for `funders.otherOrgs` keys.
- **Applicant types:** `non_profit_with_501c3` and `nonprofit_without_501c3` are spelled differently.

## Assigning keys

| Approach | How | Trade-off |
| --- | --- | --- |
| Heading matching at import | A maintained table maps standard headings to keys during Builder import, recorded as an import rule in `IMPORT_RULES.md` | Automatic, but reworded or renamed headings won't match |
| From FOAM's structure | FOAM's own fields map to keys once, in a mapping table | Durable for NIH; depends on FOAM's data model |
| Set by editors | An editor confirms or picks a key for each standard section in the Builder | Reliable, but adds a step to editors' work |

A realistic path combines the first two: draft the vocabulary from the standard NOFO structure, check it against FOAM's fields with eRA, and assign keys at import for Builder-authored NOFOs, with editors able to correct a missed match.

## Conformance

A renderer conforms when, for the shared fixtures:

1. every keyed part appears with its `data-nofo-key` and `id`;
2. axe-core (WCAG 2.2 A and AA) reports no violations;
3. the page has no sideways scrolling at 320px;
4. headings, target highlight, focus movement and navigation behave as in the markup spec.

Fixtures would pair contract JSON with expected structure, starting from the CMS-2U2-25-001 fixture and the synthetic sample NOFO in the #851 evidence.

## Versioning

The contract uses semantic versions. Adding a component or key is a minor change; renaming or removing a key, or changing an `id` rule, is a major change, because it breaks deep links. Renderers declare the version they follow.

## Open questions

- Does eRA want FOAM to render this design, and what is FOAM's stack and data model?
- Who maintains the contract and CSS, and how do design changes get approved across HHS, NIH and Simpler.Grants.gov?
- Which of the [gaps](#gaps-between-commongrants-and-nofo-content) will the CommonGrants maintainers take as protocol changes, catalog fields or documentation, starting with `nofoDocument`, `nofoSections`, related opportunities and time zones?
- How are amendments represented, so the web page and PDF always show the same version?
- Who runs the accessibility conformance checks for pages FOAM publishes?
