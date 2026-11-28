"""Edge-case pattern gallery for NOFO web pages, in both prototype themes.

Usage: python build_edge_cases.py uswds <out_dir>
       python build_edge_cases.py sgg <out_dir> <uswds_dist> <sgg_logo.svg>

Writes edge-cases.html. Sample content is illustrative unless a pattern says
otherwise; the 15 assistance listings come from the live PAR-24-295 listing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_nofo_web as base  # noqa: E402

esc = base.esc

PAR_24_295_ALNS = [
    ("93.173", "Research Related to Deafness and Communication Disorders"),
    ("93.233", "National Center on Sleep Disorders Research"),
    (
        "93.853",
        "Extramural Research Programs in the Neurosciences and Neurological Disorders",
    ),
    ("93.837", "Cardiovascular Diseases Research"),
    (
        "93.840",
        "Translation and Implementation Science Research for Heart, Lung, Blood Diseases, and Sleep Disorders",
    ),
    ("93.113", "Environmental Health"),
    ("93.866", "Aging Research"),
    ("93.172", "Human Genome Research"),
    ("93.838", "Lung Diseases Research"),
    ("93.398", "Cancer Research Manpower"),
    ("93.313", "NIH Office of Research on Women's Health"),
    ("93.242", "Mental Health Research Grants"),
    ("93.989", "International Research and Research Training"),
    ("93.839", "Blood Diseases and Resources Research"),
    ("93.279", "Drug Abuse and Addiction Research Programs"),
]

CSS = """
.ec-intro{max-width:46rem}
.ec-toc{columns:2 16rem;column-gap:2rem;padding-left:1.25rem;margin:1rem 0 0}
.ec-toc li{break-inside:avoid;margin-bottom:.35rem}
.ec-pattern{margin-top:3.5rem;padding-top:2rem;border-top:2px solid var(--nofo-border)}
.ec-pattern>h2{margin:0 0 .5rem;font-size:1.75rem}
.ec-pattern [id]{scroll-margin-top:calc(var(--nofo-sticky-top) + .5rem)}
.ec-when{max-width:46rem;margin:0 0 1rem}
.ec-frame{border:1px dashed #a9aeb1;border-radius:.5rem;padding:1.25rem;margin:1rem 0;background:#fff}
.ec-frame-label{display:block;font-size:.8125rem;font-weight:700;color:var(--nofo-muted);margin:0 0 .75rem}
.ec-notes{max-width:46rem;font-size:.9375rem}
.ec-notes li{margin-bottom:.35rem}
.ec-frame h3{font-size:1.25rem;margin:0 0 .5rem}
.ec-frame h4{font-size:1.0625rem;margin:1rem 0 .25rem}
.ec-frame .usa-alert{margin-top:0}
.ec-frame .usa-alert+.usa-alert{margin-top:1rem}
.nofo-tag-row{display:flex;flex-wrap:wrap;gap:.5rem;margin:.25rem 0 1rem;padding:0;list-style:none}
.nofo-tag-row li{margin:0;max-width:none}
.nofo-tag{display:inline-block;font-size:.875rem;font-weight:600;line-height:1.3;padding:.15rem .5rem;border-radius:2px;border:1px solid currentColor}
.nofo-tag--component{color:#1a4480;background:#e1f3f8;border-color:#73b3e7}
.nofo-tag--updated{color:#1b1b1b;background:#fff5c2;border-color:#8e6a00}
.nofo-fons{list-style:none;padding:0;margin:.25rem 0 0}
.nofo-fons li{margin:0 0 .25rem;max-width:none}
.nofo-fons .v{font-weight:700;white-space:nowrap}
.ec-dates{list-style:none;margin:0;padding:0;border-left:3px solid var(--nofo-border)}
.ec-dates li{position:relative;margin:0 0 1rem;padding-left:1.25rem;max-width:none}
.ec-dates li::before{content:"";position:absolute;left:-.55rem;top:.35rem;width:.8rem;height:.8rem;border-radius:50%;background:#fff;border:3px solid var(--nofo-border)}
.ec-dates .is-next::before{background:var(--nofo-accent);border-color:var(--nofo-accent)}
.ec-dates .is-past{color:var(--nofo-muted)}
.ec-dates .d{display:block;font-weight:700;font-size:1.0625rem}
.ec-dates .is-past .d{font-weight:600}
.ec-state{display:inline-block;font-size:.8125rem;font-weight:700;margin-left:.5rem;padding:0 .4rem;border-radius:2px}
.ec-state--next{background:var(--nofo-accent);color:#fff}
.ec-state--past{background:#e6e6e2;color:#1b1b1b}
details.ec-more summary{cursor:pointer;color:var(--nofo-accent);font-weight:600;min-height:24px}
details.ec-more summary:focus{outline:.25rem solid #2491ff;outline-offset:2px}
details.ec-more ul{margin-top:.5rem}
.ec-compare{width:100%}
.ec-lang{display:flex;flex-wrap:wrap;gap:.25rem 1rem;align-items:center;margin:0;padding:0;list-style:none}
.ec-lang li{margin:0}
@media(max-width:39.99em){.ec-frame{padding:1rem}}
"""


def patterns():
    """(id, title, when, example_html, notes) for each edge case."""
    alns_first, alns_rest = PAR_24_295_ALNS[:2], PAR_24_295_ALNS[2:]
    aln_li = lambda rows: "".join(
        f"<li>{esc(n)}: {esc(t)}</li>" for n, t in rows
    )  # noqa: E731
    return [
        (
            "multiple-numbers",
            "One NOFO, several opportunity numbers",
            "One NOFO document is posted as several opportunities, for example a separate number per track, applicant type or clinical-trial option. The Builder stores one number per NOFO today.",
            f"""
<span class="ec-frame-label">NOFO title block</span>
<p class="nofo-title__agency">Health Resources and Services Administration</p>
<h3>Rural Health Workforce Pathways</h3>
<p class="margin-0"><strong>This NOFO covers 3 funding opportunities.</strong> Apply under the number for your track.</p>
<ul class="nofo-fons">
  <li><span class="v">HRSA-27-101</span>: Track 1, new applicants (<a class="usa-link" href="#ec-listing">opportunity listing</a>)</li>
  <li><span class="v">HRSA-27-102</span>: Track 2, current recipients (<a class="usa-link" href="#ec-listing">opportunity listing</a>)</li>
  <li><span class="v">HRSA-27-103</span>: Track 3, Tribal organizations (<a class="usa-link" href="#ec-listing">opportunity listing</a>)</li>
</ul>""",
            [
                "Each listing links to the same NOFO page; the NOFO links back to every listing, not just one.",
                "Data: the Builder's single <code>number</code> field needs to become a list. In CommonGrants each opportunity stays separate and points to the same NOFO document.",
                "Applying under the wrong number is a common, costly error, so say which number fits which applicant.",
                "Real examples (Simpler.Grants.gov, 2026-11-28): NIH parent K awards come in companion pairs, for example PA-24-190 and PA-24-191 (Clinical Trial Required / Not Allowed). PA-24-191's description says to apply to 'the companion FOA ()' with the link missing. NASA's ROSES 2025 posts each program element as its own listing (NNH25ZDA001N-SBR and others) with a generic description. Companion and reissue links exist only as free text, so the Builder should store them as data.",
            ],
        ),
        (
            "components",
            "Multi-component or multi-track NOFOs",
            "Components differ in who can apply, funding, deadlines or review criteria, while sharing most of the text.",
            """
<span class="ec-frame-label">At-a-glance comparison, near the top of Step 1</span>
<div class="usa-table-container--scrollable" tabindex="0" role="region" aria-label="Table: Compare the components">
<table class="usa-table usa-table--borderless usa-table--stacked">
  <caption>Compare the components</caption>
  <thead><tr><th scope="col">Component</th><th scope="col">Who can apply</th><th scope="col">Funding per award</th><th scope="col">Awards</th><th scope="col">Deadline</th></tr></thead>
  <tbody>
    <tr><th scope="row" data-label="Component">A: Planning</th><td data-label="Who can apply">States and territories</td><td data-label="Funding per award">Up to $250,000</td><td data-label="Awards">20</td><td data-label="Deadline">Jan 15, 2027</td></tr>
    <tr><th scope="row" data-label="Component">B: Implementation</th><td data-label="Who can apply">Prior Component A recipients</td><td data-label="Funding per award">Up to $1,000,000</td><td data-label="Awards">8</td><td data-label="Deadline">Mar 1, 2027</td></tr>
  </tbody>
</table>
</div>
<span class="ec-frame-label">A section that applies to one component</span>
<div class="nofo-heading nofo-heading--h3"><h3 id="ec-comp-b-budget" tabindex="-1">Budget narrative</h3></div>
<ul class="nofo-tag-row" aria-label="Applies to"><li><span class="nofo-tag nofo-tag--component">Component B only</span></li></ul>
<p>Include a 4-year budget with a separate line for implementation partners.</p>""",
            [
                'Label content, don\'t hide it: a filter that removes text makes the page differ from the PDF and from what a colleague sees. An optional "show only my component" view can come later, with a clear on/off state.',
                "Tags are text, not color alone, and sit next to the heading so they're read right after it.",
                'Repeated headings ("Eligibility" for each component) need unique anchors and navigation labels, such as "Eligibility: Component B".',
                "Real examples: RFA-OH-27-049 (NIOSH Total Worker Health Centers) calls itself a multi-component NOFO, with an overall component, cores and project types; RFA-CA-26-010 merges a former U01 and U24 into one NOFO with two tracks; RESTORE Act GR-RDC-25-001 and -002 are construction and non-construction components posted as separate listings.",
            ],
        ),
        (
            "status",
            "Forecasted, closed, archived and cancelled NOFOs",
            "The same page has to work before posting, while open, after the deadline and years later, when awardees still rely on it.",
            """
<span class="ec-frame-label">Status banners, one per state</span>
<div class="usa-alert usa-alert--info"><div class="usa-alert__body"><h3 class="usa-alert__heading">Forecasted: details may change</h3><p class="usa-alert__text">This NOFO isn't open yet. Dates and amounts are estimates. The agency expects to post it in March 2027.</p></div></div>
<div class="usa-alert usa-alert--warning"><div class="usa-alert__body"><h3 class="usa-alert__heading">Closed to new applications</h3><p class="usa-alert__text">The deadline was January 15, 2025. This page stays available for applicants and recipients.</p></div></div>
<div class="usa-alert usa-alert--info"><div class="usa-alert__body"><h3 class="usa-alert__heading">A newer version of this NOFO is available</h3><p class="usa-alert__text">This is the FY 2025 NOFO. <a class="usa-link" href="#reissue">Read the FY 2027 NOFO</a>.</p></div></div>
<div class="usa-alert usa-alert--error"><div class="usa-alert__body"><h3 class="usa-alert__heading">Cancelled</h3><p class="usa-alert__text">The agency cancelled this NOFO on May 2, 2026 and won't make awards under it.</p></div></div>""",
            [
                "One banner at a time, above the title block, using USWDS alerts with a real heading.",
                "Never delete a closed NOFO page: recipients cite it for years. A newer version gets a link, not a redirect.",
                "Live data shows why: a 2020 State Department listing is still marked Forecasted with no close date, AFPRA-20-04 (posted 2020) is still Open with no close date, and HHS-2027-ACL-AOA-CGNS-0039 was archived the day it was created. A NOFO page should state its own status and dates rather than trusting the listing's.",
            ],
        ),
        (
            "dates",
            "Several deadlines, rounds or two-phase applications",
            "Letters of intent, pre-applications with invited full applications, multiple funding rounds, standard recurring due dates, or rolling review.",
            """
<span class="ec-frame-label">Key dates as a timeline</span>
<h3>Key dates</h3>
<p class="margin-top-0">All times are 11:59 p.m. Eastern Time.</p>
<ol class="ec-dates">
  <li class="is-past"><span class="d">Oct 1, 2026<span class="ec-state ec-state--past">Passed</span></span>Letter of intent (required)</li>
  <li class="is-next"><span class="d">Dec 1, 2026<span class="ec-state ec-state--next">Next deadline</span></span>Pre-application, all applicants</li>
  <li><span class="d">Mar 15, 2027</span>Full application, by invitation only</li>
  <li><span class="d">Sep 30, 2027</span>Expected award date</li>
</ol>""",
            [
                "State the time zone once, prominently. CommonGrants event times carry no time zone, so the publishing side has to supply it.",
                '"Passed" and "Next deadline" are words, not only color, and they depend on today\'s date: generate them when the page is published or rebuilt, and say when that was.',
                "For rolling or recurring due dates, link to the schedule instead of listing years of dates.",
                "Real examples: the listing's single close date is often only one of several deadlines. AFOSR FA955026S0003 stores the December proposal deadline but not the October white-paper deadline, which goes through a different system; ROSES NNH25ZDA001N-SBR stores the Step-2 date while Step-1 appears only in the description.",
            ],
        ),
        (
            "modified",
            "Modified or amended NOFOs",
            "A NOFO changes after posting. The Builder already has a <code>modifications</code> date that adds a cover-page notice and a Modifications section to the PDF.",
            """
<span class="ec-frame-label">Banner under the title block</span>
<div class="usa-alert usa-alert--info usa-alert--slim"><div class="usa-alert__body"><p class="usa-alert__text"><strong>Modified March 3, 2027.</strong> The application deadline moved and the eligibility section changed. <a class="usa-link" href="#ec-mods">See all modifications</a>.</p></div></div>
<span class="ec-frame-label">Marker on a changed section</span>
<div class="nofo-heading nofo-heading--h3"><h3 id="ec-elig" tabindex="-1">Eligibility</h3></div>
<ul class="nofo-tag-row" aria-label="Section status"><li><span class="nofo-tag nofo-tag--updated">Updated March 3, 2027</span></li></ul>
<span class="ec-frame-label">Modifications section (end of the NOFO)</span>
<div class="nofo-heading nofo-heading--h3"><h3 id="ec-mods" tabindex="-1">Modifications</h3></div>
<div class="usa-table-container--scrollable" tabindex="0" role="region" aria-label="Table: Modifications">
<table class="usa-table usa-table--borderless usa-table--stacked"><thead><tr><th scope="col">Date</th><th scope="col">Change</th></tr></thead>
<tbody><tr><td data-label="Date">Mar 3, 2027</td><td data-label="Change">Application deadline moved from March 1 to March 15, 2027. <a class="usa-link" href="#ec-elig">Eligibility</a>: added territories.</td></tr></tbody></table></div>""",
            [
                "Keep section anchors stable across versions so links shared before the change still work. Builder <code>html_id</code>s are stable today; a re-import must keep them.",
                "The web page and the PDF show the same version and the same modification date.",
                "The Builder's Compare tool could generate the change list instead of someone writing it by hand.",
                "Real examples: AFOSR FA955026S0003 attaches the original announcement plus Amendment_0001 and Amendment_0002 as separate PDFs, leaving applicants to merge them; ROSES records an amendment only in its description, and the record's modified date didn't change. Listing timestamps aren't a reliable amendment signal, so the NOFO should carry its own modification record.",
            ],
        ),
        (
            "reissue",
            "Reissues, continuations and year-over-year NOFOs",
            'The same program returns each year, or a NOFO is reissued ("This is a reissue of PAR-21-xxx"). The Builder links versions through its <code>successor</code> field.',
            """
<span class="ec-frame-label">What's new callout, Step 1</span>
<div class="usa-summary-box" role="region" aria-labelledby="ec-new"><div class="usa-summary-box__body">
<h3 class="usa-summary-box__heading" id="ec-new">What's new for FY 2027</h3>
<div class="usa-summary-box__text"><ul>
<li>Territories are now eligible. <a class="usa-link" href="#ec-elig">Eligibility</a></li>
<li>The project narrative limit is 15 pages, down from 20.</li>
<li>A new review criterion covers sustainability (10 points).</li>
</ul><p class="margin-bottom-0">Previous version: <a class="usa-link" href="#reissue">FY 2025 NOFO (CMS-2U2-25-001)</a></p></div>
</div></div>""",
            [
                "Returning applicants mostly want the differences. The Compare tool already diffs documents and could draft this list.",
                "Link both directions: new version to old, and old to new (see the status banners).",
                "Real examples: RFA-FD-25-020 puts 'Reissue of RFA-FD-23-001' in its title; PAR-25-352 is a reissue of PAR-20-118 according to its description; Fish and Wildlife's F25AS00283 and F26AS00104 are near-identical year-over-year listings.",
                "Non-competing continuations usually aren't public NOFOs; when one is, say clearly who it is for (next pattern).",
            ],
        ),
        (
            "limited",
            "Limited competition or restricted eligibility",
            "Only named organizations, current recipients or one applicant type may apply.",
            """
<span class="ec-frame-label">Eligibility notice at the top of Step 1</span>
<div class="usa-alert usa-alert--warning"><div class="usa-alert__body"><h3 class="usa-alert__heading">Limited competition</h3><p class="usa-alert__text">Only current recipients of the State Offices of Rural Health program may apply. <a class="usa-link" href="#ec-elig">Check eligibility</a>.</p></div></div>""",
            [
                "Put it before everything else so ineligible readers stop early.",
                "Mirror it on the opportunity listing's Eligibility section.",
                "Real examples: PAR-27-009's title begins 'Single Source:'; USDA's Harvest to Hallways grant is awarded non-competitively to state agencies, with each state's amount in an appendix.",
            ],
        ),
        (
            "listings",
            "Many assistance listings or co-funding institutes",
            "NIH NOFOs often list many institutes; the live PAR-24-295 listing has 15 assistance listings.",
            f"""
<span class="ec-frame-label">Title block metadata (real PAR-24-295 data)</span>
<p class="margin-0"><strong>Assistance listings</strong></p>
<ul class="margin-y-1">{aln_li(alns_first)}</ul>
<details class="ec-more"><summary>Show 13 more assistance listings</summary><ul>{aln_li(alns_rest)}</ul></details>""",
            [
                "Show the first few and put the rest behind a native disclosure, which works with keyboard and screen readers without script. The full list stays in the HTML for search and print.",
                "Data: the Builder stores one assistance listing number as text; CommonGrants and Simpler.Grants.gov already use a list. NIH parent K listings carry 23 to 28 each (PA-24-191 has 23), and some codes are alphanumeric, such as 93.HL6, so don't validate them as numbers.",
                'Joint NOFOs from several agencies or OpDivs need the same treatment for "Issued by" and for contacts. The Builder has two subagency fields today.',
            ],
        ),
        (
            "systems",
            "Applications outside Grants.gov",
            "Some NOFOs use eRA ASSIST, GrantSolutions, an agency portal or email.",
            """
<span class="ec-frame-label">Where to apply</span>
<div class="usa-summary-box" role="region" aria-labelledby="ec-where"><div class="usa-summary-box__body">
<h3 class="usa-summary-box__heading" id="ec-where">Where to apply</h3>
<div class="usa-summary-box__text"><p>Submit your application in <strong>GrantSolutions</strong>, not Grants.gov. You need a GrantSolutions account before you start.</p>
<a class="usa-button" href="#ec-where">Apply in GrantSolutions</a></div></div></div>""",
            [
                "The apply button names the real system, on both the NOFO page and the opportunity listing.",
                "Registration steps change with the system, so Step 2 content should follow the same field.",
                "Real examples: Fish and Wildlife's F24AS00022 says applications submitted through Grants.gov won't be evaluated (GrantSolutions only); State Department listings such as OFOP0002825 point to the MyGrants portal; ROSES accepts Grants.gov only on request.",
            ],
        ),
        (
            "placeholders",
            "Placeholder dates and amounts",
            "Listing data sometimes holds stand-in values: a close date far in the future for rolling programs, $0 or $1 minimum awards, or $0 totals.",
            """
<span class="ec-frame-label">Show what the value means, not the stored placeholder</span>
<div class="usa-table-container--scrollable" tabindex="0" role="region" aria-label="Table: Placeholder values and what to show">
<table class="usa-table usa-table--borderless usa-table--stacked">
  <thead><tr><th scope="col">Stored value</th><th scope="col">Real example</th><th scope="col">Show instead</th></tr></thead>
  <tbody>
    <tr><td data-label="Stored value">Close date 2099-01-01</td><td data-label="Real example">OFOP0002825, rolling State Department program</td><td data-label="Show instead">Rolling: applications reviewed as received</td></tr>
    <tr><td data-label="Stored value">Same distant close date on every listing</td><td data-label="Real example">NIH parent K awards all close 2027-11-13</td><td data-label="Show instead">Standard due dates, with a link to the schedule</td></tr>
    <tr><td data-label="Stored value">Minimum award $0 or $1</td><td data-label="Real example">HRSA-27-072 ($0), USGS CESU listings ($1)</td><td data-label="Show instead">Leave out the minimum, or use the NOFO's range</td></tr>
    <tr><td data-label="Stored value">Total available $0</td><td data-label="Real example">OVC-2018-14081 ($400,000 maximum)</td><td data-label="Show instead">Not specified</td></tr>
  </tbody>
</table>
</div>""",
            [
                "Never display a sentinel date or a $0/$1 amount as if it were real. The NOFO page should take dates and funding from the NOFO itself, and the listing should defer to it.",
                "Other real oddities to plan for: award minimums that are a per-year cap while maximums are a multi-year total (AFOSR), RFIs posted as funding opportunities, the NOFO attached as both .docx and .pdf, and a contact email with invisible characters (HRSA-27-072).",
            ],
        ),
        (
            "content",
            "Very long NOFOs, complex tables, images and attachments",
            "190-page NOFOs, budget tables with merged cells, maps or logic models, appendices, and templates to download.",
            """
<span class="ec-frame-label">Attachments the NOFO refers to</span>
<ul class="usa-list">
  <li><a class="usa-link" href="#content">Budget template</a> (Excel, 48 KB)</li>
  <li><a class="usa-link" href="#content">Logic model example</a> (PDF, 210 KB)</li>
</ul>
<span class="ec-frame-label">Language versions</span>
<ul class="ec-lang" aria-label="Language versions"><li><strong>English</strong></li><li><a class="usa-link" href="#content" lang="es" hreflang="es">Español</a></li></ul>""",
            [
                "Navigation lists only h2 and h3; deeper headings stay in the text. Tables keep header cells and scroll in their own container; images need alt text from import, which the Builder already asks for on cover images.",
                "List file type and size for every attachment.",
                "Translations get their own page with <code>lang</code> set, linked both ways.",
            ],
        ),
        (
            "listing",
            "Opportunity listing for an edge-case NOFO",
            "How the listing's NOFO section adapts to several numbers and to a modification.",
            """
<span class="ec-frame-label">NOFO section on a Simpler.Grants.gov listing</span>
<section class="sgg-nofo-card" aria-labelledby="ec-listing">
  <h3 id="ec-listing">Notice of funding opportunity (NOFO)</h3>
  <p class="margin-top-1">This opportunity (HRSA-27-102, Track 2) shares one NOFO with 2 other opportunities: <a class="usa-link" href="#multiple-numbers">HRSA-27-101</a> and <a class="usa-link" href="#multiple-numbers">HRSA-27-103</a>.</p>
  <div class="usa-alert usa-alert--info usa-alert--slim"><div class="usa-alert__body"><p class="usa-alert__text"><strong>Modified March 3, 2027.</strong> <a class="usa-link" href="#ec-mods">See what changed</a>.</p></div></div>
  <p><a class="usa-button" href="#ec-listing">Read the NOFO online</a> <a class="usa-button usa-button--outline" href="#ec-listing">Download PDF</a></p>
</section>""",
            [
                "The listing names this opportunity's track so applicants know they're in the right place.",
                "The modification notice appears on the listing as well as on the NOFO.",
            ],
        ),
    ]


def body(theme):
    pats = patterns()
    toc = "".join(
        f'<li><a class="usa-link" href="#{pid}">{esc(t)}</a></li>'
        for pid, t, *_ in pats
    )
    sections = []
    for pid, title, when, example, notes in pats:
        notes_html = "".join(f"<li>{n}</li>" for n in notes)
        sections.append(
            f'<section class="ec-pattern" aria-labelledby="{pid}">'
            f'<h2 id="{pid}" tabindex="-1">{esc(title)}</h2>'
            f'<p class="ec-when"><strong>When:</strong> {when}</p>'
            f'<div class="ec-frame">{example}</div>'
            f'<h3 class="font-sans-sm margin-bottom-0">Design and data notes</h3>'
            f'<ul class="ec-notes">{notes_html}</ul></section>'
        )
    container = "grid-container padding-y-4" if theme == "sgg" else "nofo-page"
    return f"""
<main id="main-content" class="{container}" tabindex="-1">
  <div class="ec-intro usa-prose">
    <p class="nofo-title__agency margin-top-4">NOFO web pages, issue #851</p>
    <h1>Edge-case patterns</h1>
    <p>How the NOFO page and the opportunity listing handle NOFOs that don't fit the simple case. Sample content is illustrative unless a pattern says it's real data.</p>
    <ul class="ec-toc">{toc}</ul>
  </div>
  <div class="usa-prose">{''.join(sections)}</div>
</main>"""


def main():
    theme, out = sys.argv[1], Path(sys.argv[2])
    if theme == "uswds":
        shell = base.page_shell(
            "Edge-case patterns | NOFO web pages",
            body(theme),
            "Edge-case patterns for NOFO web pages",
        )
        shell = shell.replace(
            "</head>",
            f"<style>{CSS}.sgg-nofo-card{{border:1px solid var(--nofo-border);border-left:.5rem solid var(--nofo-accent);border-radius:.5rem;padding:1.25rem 1.5rem}}</style>\n</head>",
        )
        (out / "edge-cases.html").write_text(shell)
    else:
        import build_sgg as sgg

        dist, logo = Path(sys.argv[3]), Path(sys.argv[4])
        sgg.set_fonts(dist)
        top, bottom = sgg.chrome(dist, logo)
        page = sgg.shell(
            "Edge-case patterns | NOFO pages in Simpler.Grants.gov",
            top + body(theme) + bottom,
            sgg.CHROME_JS,
        )
        page = page.replace("/*CSS*/", "/*CSS*/" + CSS)
        page = sgg.inline_sprite(page, (dist / "img/sprite.svg").read_text())
        (out / "edge-cases.html").write_text(
            page.replace(
                "/*CSS*/", "/*SGG-CSS*/" + base.LOCAL_CSS.strip() + sgg.SGG_VARS
            )
        )


if __name__ == "__main__":
    main()
