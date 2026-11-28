"""Simpler.Grants.gov-themed NOFO mockups (local files only; not for publishing).

Usage: python build_sgg.py <nofo.json> <opportunity.json> <uswds_dist> <sgg_logo.svg> <sgg_css> <out_dir>

Writes self-contained pages (CSS, icons and images inlined):
  opportunity.html     Opportunity listing in the site's header/footer, linking into the NOFO
  nofo.html            The NOFO as a page of the site, linking back to the listing
  nofo-standalone.html The same NOFO without site chrome: what would be attached to the opportunity
  index.html           Small guide to the three
"""

import base64
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_nofo_web as base
from bs4 import BeautifulSoup

base.SPRITE = ""  # icons reference an inline <symbol> sheet
esc, icon = base.esc, base.icon

MOCK_NOTE = (
    '<div class="usa-alert usa-alert--warning usa-alert--slim margin-0" role="region" aria-label="About this mockup">'
    '<div class="usa-alert__body"><p class="usa-alert__text"><strong>Design mockup, not the live site.</strong> '
    "Opportunity data from the Simpler.Grants.gov API via CommonGrants; NOFO text from the NOFO Builder test fixture. "
    '<a class="usa-link" href="index.html">About these mockups</a></p></div></div>'
)

SGG_VARS = (
    "body.theme-sgg{--nofo-accent:#286846;--nofo-accent-bg:#dbf6ed;--nofo-muted:#5d5d52;"
    '--nofo-muted-dark:#454540;--nofo-border:#e6e6e2;--nofo-display:"Public Sans",sans-serif}'
    ".theme-sgg .nofo-glance li{border-top-color:#34a37e}"
    ".theme-sgg .nofo-content h2{font-size:2rem}"
    ".theme-sgg .nofo-onepage .nofo-content>section+section{border-top-color:#171716}"
    ".nofo-crumbs .usa-breadcrumb{padding-top:0;padding-bottom:1rem}"
    ".sgg-nofo-card{border:1px solid #e6e6e2;border-left:.5rem solid #34a37e;border-radius:.5rem;padding:1.25rem 1.5rem;margin-top:1.5rem}"
    ".sgg-nofo-card h3{margin-top:0}"
    ".sgg-jump{columns:2 14rem;column-gap:2rem;padding-left:0;list-style:none;margin:1rem 0 0}"
    ".sgg-jump li{break-inside:avoid;margin:0 0 .5rem;max-width:none}"
    ".sgg-jump a{display:inline-flex;align-items:flex-start;gap:.25rem;min-height:24px}"
    ".sgg-jump .usa-icon{flex:none;margin-top:.15rem}"
    ".sgg-new{background:#fff5c2;color:#171716;font-size:.8125rem;font-weight:700;padding:.1rem .4rem;border-radius:2px;margin-left:.5rem;vertical-align:middle}"
    "#opportunity-detail-content [id]{scroll-margin-top:calc(var(--nofo-sticky-top) + .5rem)}"
    ".usa-nav__submenu[hidden]{display:none}"
    # The site's footer row uses grid-gap-lg (3rem) inside 1rem container padding: 8px of sideways scroll at 320px.
    "@media(max-width:39.99em){.usa-footer__primary-section .grid-gap-lg{margin-left:-.5rem;margin-right:-.5rem}"
    ".usa-footer__primary-section .grid-gap-lg>*{padding-left:.5rem;padding-right:.5rem}}"
)

# Mobile menu, nav dropdowns and the gov banner: the few behaviours the site's React code provides.
CHROME_JS = """{
const header=document.querySelector('.usa-header');
const setTop=()=>{const sticky=header&&getComputedStyle(header).position==='sticky';
  document.documentElement.style.setProperty('--nofo-sticky-top',sticky?(header.offsetHeight+16)+'px':'1rem');};
setTop();window.addEventListener('resize',setTop);
document.addEventListener('click',e=>{
  const b=e.target.closest('.usa-accordion__button[aria-controls]');
  if(b){const t=document.getElementById(b.getAttribute('aria-controls'));const open=b.getAttribute('aria-expanded')==='true';
    document.querySelectorAll('.usa-nav .usa-accordion__button[aria-expanded="true"]').forEach(o=>{if(o!==b){o.setAttribute('aria-expanded','false');document.getElementById(o.getAttribute('aria-controls')).hidden=true;}});
    b.setAttribute('aria-expanded',String(!open));t.hidden=open;return;}
  const nav=document.querySelector('.usa-nav'),ov=document.querySelector('.usa-overlay');
  if(e.target.closest('.usa-menu-btn')){nav.classList.add('is-visible');ov.classList.add('is-visible');document.body.classList.add('usa-js-mobile-nav--active');nav.querySelector('.usa-nav__close').focus();return;}
  if(e.target.closest('.usa-nav__close')||e.target===ov){nav.classList.remove('is-visible');ov.classList.remove('is-visible');document.body.classList.remove('usa-js-mobile-nav--active');document.querySelector('.usa-menu-btn').focus();}
});
document.addEventListener('keydown',e=>{if(e.key!=='Escape')return;
  const open=document.querySelector('.usa-nav .usa-accordion__button[aria-expanded="true"]');
  if(open){open.setAttribute('aria-expanded','false');document.getElementById(open.getAttribute('aria-controls')).hidden=true;open.focus();}
  const nav=document.querySelector('.usa-nav.is-visible');if(nav)document.querySelector('.usa-nav__close').click();});
}"""


def data_uri(path, mime):
    return f"data:{mime};base64,{base64.b64encode(Path(path).read_bytes()).decode()}"


def svg_uri(path):
    return data_uri(path, "image/svg+xml")


def fmt_date(iso):
    d = date.fromisoformat(iso)
    return d.strftime("%b %-d, %Y")


def chrome(dist, logo):
    img = dist / "img"
    sgg = "https://simpler.grants.gov"

    def ext(label, href):
        return (
            f'<a href="{href}" target="_blank" rel="noreferrer"><span class="icon-btn">{esc(label)}'
            f'{icon("launch", "usa-icon--size-2")}<span class="usa-sr-only"> (opens in a new tab)</span></span></a>'
        )

    def drop(key, label, items):
        lis = "".join(f'<li class="usa-nav__submenu-item">{i}</li>' for i in items)
        return (
            f'<li class="usa-nav__primary-item"><button type="button" class="usa-accordion__button usa-nav__link text-bold" '
            f'aria-expanded="false" aria-controls="nav-{key}"><span>{label}</span></button>'
            f'<ul id="nav-{key}" class="usa-nav__submenu" hidden>{lis}</ul></li>'
        )

    def a(label, href):
        return f'<a href="{href}"><span>{esc(label)}</span></a>'

    top = f"""
<a class="usa-skipnav" href="#main-content">Skip to main content</a>
<section class="usa-banner" aria-label="Official website of the United States government">
  <div class="usa-accordion">
    <header class="usa-banner__header"><div class="usa-banner__inner">
      <div class="grid-col-auto"><img aria-hidden="true" class="usa-banner__header-flag" src="{data_uri(img / 'us_flag_small.png', 'image/png')}" alt=""></div>
      <div class="grid-col-fill tablet:grid-col-auto" aria-hidden="true"><p class="usa-banner__header-text">An official website of the United States government</p><p class="usa-banner__header-action">Here’s how you know</p></div>
      <button type="button" class="usa-accordion__button usa-banner__button" aria-expanded="false" aria-controls="gov-banner"><span class="usa-banner__button-text">Here’s how you know</span></button>
    </div></header>
    <div class="usa-banner__content usa-accordion__content" id="gov-banner" hidden><div class="grid-row grid-gap-lg">
      <div class="usa-banner__guidance tablet:grid-col-6"><img class="usa-banner__icon usa-media-block__img" src="{svg_uri(img / 'icon-dot-gov.svg')}" alt="" aria-hidden="true"><div class="usa-media-block__body"><p><strong>Official websites use .gov</strong><br>A <strong>.gov</strong> website belongs to an official government organization in the United States.</p></div></div>
      <div class="usa-banner__guidance tablet:grid-col-6"><img class="usa-banner__icon usa-media-block__img" src="{svg_uri(img / 'icon-https.svg')}" alt="" aria-hidden="true"><div class="usa-media-block__body"><p><strong>Secure .gov websites use HTTPS</strong><br>A <strong>lock</strong> or <strong>https://</strong> means you’ve safely connected to the .gov website. Share sensitive information only on official, secure websites.</p></div></div>
    </div></div>
  </div>
</section>
{MOCK_NOTE}
<div class="usa-overlay"></div>
<header class="usa-header usa-header--basic desktop:position-sticky top-0 desktop:z-500 bg-white border-bottom-2px border-primary-vivid">
  <div class="usa-nav-container display-flex flex-justify">
    <div class="usa-navbar border-bottom-0">
      <div class="usa-logo margin-y-2"><div class="display-flex flex-align-center">
        <a href="{sgg}/" class="position-relative"><img alt="Simpler.Grants.gov" src="{svg_uri(logo)}" class="height-4 display-block position-relative desktop:height-auto" style="max-width:16rem"></a>
      </div></div>
    </div>
    <div class="usa-navbar order-last desktop:display-none"><button type="button" class="usa-menu-btn">Menu</button></div>
    <nav aria-label="Primary navigation" class="usa-nav padding-bottom-05">
      <button type="button" class="usa-nav__close"><img src="{svg_uri(img / 'usa-icons/close.svg')}" role="img" alt="Close"></button>
      <ul class="usa-nav__primary usa-accordion">
        <li class="usa-nav__primary-item"><a class="usa-nav__link text-bold" href="{sgg}/"><span>Home</span></a></li>
        <li class="usa-nav__primary-item"><a class="usa-nav__link text-bold usa-current" href="{sgg}/search"><span>Search</span></a></li>
        {drop('about', 'About', [a('Our vision', sgg + '/vision'), a('Product roadmap', sgg + '/roadmap')])}
        {drop('community', 'Community', [a('Newsletter', sgg + '/newsletter'), a('Events', sgg + '/events'), a('Developers', sgg + '/developers'), ext('Public wiki', 'https://wiki.simpler.grants.gov/'), ext('Discussion forum', 'https://simplergrants.discourse.group/')])}
        <li class="usa-nav__primary-item"><a class="usa-nav__link text-normal" href="{sgg}/"><span>Sign in</span></a></li>
      </ul>
    </nav>
  </div>
</header>"""

    bottom = f"""
<footer class="usa-footer usa-footer--medium">
  <div class="grid-container usa-footer__return-to-top margin-top-5"><a href="#main-content">Return to top</a></div>
  <div class="usa-footer__primary-section"><div class="grid-container"><div class="grid-row grid-gap-lg">
    <div class="desktop:grid-col-4"><div class="footer-logo-container"><img src="{svg_uri(logo)}" alt="Grants.gov logo"></div></div>
    <nav class="usa-footer__nav border-0 tablet:grid-col-auto tablet-lg:grid-col-2 desktop:grid-col-2" aria-labelledby="footer-explore">
      <h2 id="footer-explore" class="font-sans-md desktop:padding-top-4">Explore</h2>
      <ul class="margin-top-3 usa-list usa-list--unstyled">
        {''.join(f'<li class="usa-footer__secondary-link margin-left-0">{a(l, sgg + h)}</li>' for l, h in [('Home', '/'), ('Search', '/search'), ('Vision', '/vision'), ('Roadmap', '/roadmap'), ('Events', '/events'), ('Subscribe', '/subscribe')])}
      </ul>
    </nav>
    <div class="margin-top-3 tablet:margin-top-0 tablet:grid-col-fill tablet-lg:grid-col-5 desktop:grid-col-3">
      <h2 class="font-sans-md">Simpler.Grants.gov</h2><p>To give feedback, contact: <a href="mailto:simpler@grants.gov">simpler@grants.gov</a></p>
      <h2 class="font-sans-md desktop:padding-top-2">Grants.gov Support Center</h2><p>For technical support, contact: <a href="mailto:support@grants.gov">support@grants.gov</a></p>
      <div class="margin-top-2">1-800-518-4726</div>
    </div>
    <div class="margin-top-3 tablet:margin-top-0 tablet:grid-col-fill tablet-lg:grid-col-5 desktop:grid-col-3">
      <h2 class="font-sans-md">Grants.gov Program Management Office</h2><p>Grantors, contact the PMO through your Agency Point of Contact.</p>
    </div>
  </div></div></div>
</footer>
<div class="usa-identifier">
  <section class="usa-identifier__section usa-identifier__section--masthead" aria-label="Agency identifier"><div class="usa-identifier__container">
    <section class="usa-identifier__identity" aria-label="Agency description"><p class="usa-identifier__identity-domain">Simpler.Grants.gov</p>
      <p class="usa-identifier__identity-disclaimer">An official website of the <a href="https://www.hhs.gov">U.S. Department of Health and Human Services</a></p></section>
  </div></section>
  <nav class="usa-identifier__section usa-identifier__section--required-links" aria-label="Important links"><div class="usa-identifier__container"><ul class="usa-identifier__required-links-list">
    {''.join(f'<li class="usa-identifier__required-links-item"><a href="#" class="usa-identifier__required-link usa-link">{l}</a></li>' for l in ['About HHS', 'Accessibility support', 'FOIA requests', 'EEO/No Fear Act', 'Office of the Inspector General', 'Performance reports', 'Privacy Policy'])}
  </ul></div></nav>
  <section class="usa-identifier__section usa-identifier__section--usagov" aria-label="U.S. government information and services"><div class="usa-identifier__container">
    <div class="usa-identifier__usagov-description">Looking for U.S. government information and services?</div> <a href="https://www.usa.gov/" class="usa-link">Visit USA.gov</a>
  </div></section>
</div>"""
    return top, bottom


def nofo_page(nofo, opp, chrome_parts, standalone, listing_href="opportunity.html"):
    """The NOFO as one long page, in Simpler.Grants.gov styling."""
    sections = base.nofo_sections(nofo)
    basic = base.find_basic(sections)
    meta = dict(base.label_lines(basic["body"]) or []) if basic else {}

    secs, nav_items = [], []
    for s in sections:
        parts = []
        step, label = base.step_label(s["name"])
        step_html = (
            f'<span class="nofo-step">{esc(step)}<span class="usa-sr-only">: </span></span>'
            if step
            else ""
        )
        parts.append(
            base.heading(2, s["html_id"], f"{step_html}{esc(label)}", s["name"])
        )
        prev = 2
        for ss in sorted(s["subsections"], key=lambda x: x["order"]):
            if ss is basic:
                continue
            level = None
            if ss.get("tag") and ss.get("name"):
                level = min(int(ss["tag"][1]), prev + 1)
                prev = level
            parts.append(base.subsection_html(ss, level))
        content = base.enhance("\n".join(parts))
        for m in re.finditer(
            r'<h([23]) id="([^"]+)" tabindex="-1"(?: class="([^"]*)")?>(.*?)</h\1>',
            content,
        ):
            lvl, hid, cls, inner = m.groups()
            if cls and "summary-box" in cls:
                continue
            text = BeautifulSoup(inner, "html.parser").get_text()
            primary = " usa-in-page-nav__item--primary" if lvl == "2" else ""
            nav_items.append(
                f'<li class="usa-in-page-nav__item{primary}" data-group="{s["html_id"]}">'
                f'<a class="usa-in-page-nav__link" href="#{hid}">{esc(text)}</a></li>'
            )
        secs.append(
            f'<section aria-labelledby="{s["html_id"]}">{content}'
            f'<a class="usa-link nofo-backtop" href="#main-content">{icon("arrow_upward")}Back to top</a></section>'
        )
    body_html = "".join(secs)
    body_html = re.sub(r'href="(?:[a-z0-9-]+\.html)#', 'href="#', body_html)

    status = opp["status"]
    status_label = (status.get("customValue") or status["value"]).capitalize()
    aln = meta.get("Assistance Listing", "").strip()
    listing = listing_href
    # Status tag colors as on Simpler.Grants.gov opportunity pages
    tag_cls = {
        "open": "bg-accent-warm-light text-ink",
        "forecasted": "bg-accent-cool-dark text-white",
        "closed": "bg-base-dark text-white",
    }.get(status["value"], "bg-base-lighter text-ink")
    crumbs = (
        ""
        if standalone or not listing
        else f"""
  <nav class="usa-breadcrumb nofo-crumbs" aria-label="Breadcrumbs"><ol class="usa-breadcrumb__list">
    <li class="usa-breadcrumb__list-item"><a href="https://simpler.grants.gov/search" class="usa-breadcrumb__link"><span>Search</span></a></li>
    <li class="usa-breadcrumb__list-item"><a href="{listing}" class="usa-breadcrumb__link"><span>Opportunity listing</span></a></li>
    <li class="usa-breadcrumb__list-item usa-current" aria-current="page"><span>Notice of funding opportunity</span></li>
  </ol></nav>"""
    )
    if standalone:
        listing_btn = f'<a class="usa-button margin-right-0" href="https://simpler.grants.gov/opportunity/{opp["id"]}">View the opportunity listing on Simpler.Grants.gov</a>'
    elif listing:
        listing_btn = f'<a class="usa-button margin-right-0" href="{listing}">View the opportunity listing</a>'
    else:
        listing_btn = ""
    agency_names = [nofo.get(k, "") for k in ("agency", "subagency", "subagency2")]
    agency_html = "".join(
        f'<p class="margin-top-0 margin-bottom-1 text-base-dark">{esc(n)}</p>'
        for n in agency_names
        if n
    )
    n_deadlines = len(base.deadlines(nofo))
    header = f"""
<div class="bg-white border-bottom border-base-lighter"><div class="grid-container padding-y-3 tablet-lg:padding-y-4">
  {crumbs}
  <p class="font-sans-sm text-base-dark margin-top-0 margin-bottom-1">Notice of funding opportunity (NOFO)</p>
  <h1 class="margin-top-0 margin-bottom-3 font-sans-lg tablet-lg:font-sans-xl">{esc(nofo['title'])}</h1>
  <div class="display-flex flex-column tablet-lg:flex-row">
    <div class="flex-1"><div class="font-sans-sm">
      <p class="margin-top-0 margin-bottom-1">{esc(nofo['opdiv'])}</p>
      {agency_html}
      <ul class="nofo-title__meta margin-top-2">
        <li><span class="k">Funding opportunity number</span><span class="v">{esc(nofo['number'])}</span></li>
        <li><span class="k">Assistance listing</span><span class="v">{esc(aln)}</span></li>
        <li><span class="k">Application deadline{'s' if n_deadlines > 1 else ''}</span><span class="v">{base.deadline_html(nofo)}</span></li>
      </ul>
      <p class="margin-top-0 margin-bottom-0 font-sans-2xs"><span class="usa-tag text-no-uppercase font-sans-2xs radius-sm margin-right-2 {tag_cls}">{esc(status_label)}</span>NOFO last updated: {fmt_date(opp['lastModifiedAt'][:10])}</p>
      <div class="margin-top-2">{base.modified_banner(nofo, sections)}</div>
    </div></div>
    <div class="margin-top-3 tablet-lg:margin-top-0 tablet-lg:margin-left-4">
      <div class="opportunity-header__buttons">
        <a class="usa-button usa-button--outline" href="#pdf">{icon('file_download')} Download PDF</a>
        {listing_btn}
      </div>
    </div>
  </div>
</div></div>"""

    main = f"""
<main id="main-content" tabindex="-1">
{'' if not standalone else MOCK_NOTE}
{header}
<div class="grid-container padding-y-4 desktop-lg:padding-y-6 nofo-onepage">
<div class="usa-in-page-nav-container">
  <aside class="usa-in-page-nav"><nav class="usa-in-page-nav__nav" aria-labelledby="on-this-page"><p class="usa-in-page-nav__heading" id="on-this-page">On this page</p><ul class="usa-in-page-nav__list">{''.join(nav_items)}</ul></nav></aside>
  <div class="nofo-content usa-prose" id="nofo-content" tabindex="-1">{body_html}</div>
</div>
</div>
</main>"""
    if standalone:
        return f'<a class="usa-skipnav" href="#nofo-content">Skip to the NOFO text</a>{main}'
    top, bottom = chrome_parts
    return top + main + bottom


def opportunity_page(nofo, opp, chrome_parts):
    """The site's opportunity listing for the same NOFO, with a NOFO section linking in."""
    cf = opp["customFields"]
    agency = cf["agency"]["value"]
    alns = cf["assistanceListings"]["value"]
    s1 = {
        ss.get("name"): ss
        for ss in sorted(nofo["sections"], key=lambda s: s["order"])[0]["subsections"]
    }
    summary = base.enhance(base.md(s1["Summary"]["body"]))
    nofo_url = "nofo.html"
    ids = {
        ss["name"]: ss["html_id"]
        for s in nofo["sections"]
        for ss in s["subsections"]
        if ss.get("name")
    }
    jumps = [
        ("Eligibility", "Eligibility"),
        (
            "Program requirements and expectations",
            "Program requirements and expectations",
        ),
        ("Application contents and format", "Application contents and format"),
        ("Criteria", "Merit review criteria"),
        ("Deadlines", "Deadlines and how to submit"),
        ("Application checklist", "Application checklist"),
    ]
    jump_html = "".join(
        f'<li><a class="usa-link" href="{nofo_url}#{ids[k]}">{icon("arrow_forward")}<span>{esc(label)}</span></a></li>'
        for k, label in jumps
        if k in ids
    )
    status = opp["status"]
    status_label = (status.get("customValue") or status["value"]).capitalize()
    close = opp["keyDates"]["closeDate"]["date"]
    posted = opp["keyDates"]["postDate"]["date"]
    fmax = opp["funding"]["maxAwardAmount"]["amount"]
    fmin = opp["funding"]["minAwardAmount"]["amount"]
    money = lambda v: "${:,.0f}".format(float(v))
    email = cf["contactInfo"]["value"]["email"]
    top, bottom = chrome_parts

    def box_li(label, value):
        return f'<li class="margin-y-105"><span class="display-block text-bold">{label}:</span>{value}</li>'

    return top + f"""
<main id="main-content" tabindex="-1">
<div class="bg-white border-bottom border-base-lighter"><div class="grid-container padding-y-3 tablet-lg:padding-y-4">
  <h1 class="margin-top-0 margin-bottom-3 font-sans-lg tablet-lg:font-sans-xl">{esc(opp['title'])}</h1>
  <div class="display-flex flex-column tablet-lg:flex-row">
    <div class="flex-1"><div class="font-sans-sm">
      <p class="margin-top-0 margin-bottom-2">Agency: {esc(agency['name'])}</p>
      <div><a class="text-bold" href="https://sam.gov/" target="_blank" rel="noreferrer">Assistance Listings{icon('launch', 'margin-left-1 text-middle')}<span class="usa-sr-only"> (opens in a new tab)</span></a>
        <ul class="usa-list margin-top-1 margin-bottom-0">{''.join(f'<li class="margin-bottom-0">{esc(a["identifier"])} -- {esc(a["programTitle"])}</li>' for a in alns)}</ul></div>
      <p class="margin-top-2 margin-bottom-0 font-sans-2xs"><span class="usa-tag text-no-uppercase font-sans-2xs radius-sm margin-right-2 bg-base-lighter text-ink">{esc(status_label)}</span>Last Updated: {fmt_date(opp['lastModifiedAt'][:10])}</p>
    </div></div>
    <div class="margin-top-3 tablet-lg:margin-top-0 tablet-lg:margin-left-4">
      <div class="opportunity-header__buttons">
        <button type="button" class="usa-button usa-button--outline">{icon('star_outline', 'button-icon-large')} Save</button>
        <a class="usa-button margin-right-0" href="{nofo_url}">{icon('file_present')} Read the NOFO</a>
      </div>
    </div>
  </div>
</div></div>

<div class="grid-container padding-y-1 tablet:padding-y-3 desktop-lg:padding-y-6">
<div class="grid-row grid-gap" id="opportunity-detail-content">
  <div class="desktop:grid-col-4 grid-col-12 desktop:order-last margin-bottom-4 desktop:margin-bottom-0">
    <h2>Important dates</h2>
    <div class="border radius-md border-base-lighter padding-x-2"><div class="padding-05"><ul class="usa-list usa-list--unstyled">
      <li class="margin-y-1"><span class="text-bold text-no-wrap">Closed:</span> <span>{fmt_date(close)}</span></li>
      <li class="margin-y-1"><span class="text-bold text-no-wrap">Letter of intent (optional):</span> <span>Dec 15, 2024</span><p class="margin-bottom-0 margin-top-05 font-sans-2xs">From the NOFO's key dates</p></li>
    </ul></div></div>
    <div class="margin-top-4"><h2>Award details</h2>
      <div class="border radius-md border-base-lighter padding-x-2 padding-y-1 margin-top-2 margin-bottom-2"><ul class="usa-list usa-list--unstyled">
        <li class="margin-y-1"><strong>Expected project funding:</strong> $10,500,000</li>
        <li class="margin-y-1"><strong>Expected awards:</strong> Up to 28</li>
      </ul></div>
      <div class="grid-row grid-gap-2">
        <div class="tablet-lg:grid-col-6 margin-bottom-2"><div class="border radius-md border-base-lighter padding-x-2"><p class="desktop-lg:font-sans-sm margin-bottom-0 text-bold">Award min.</p><p class="font-sans-sm">{money(fmin)}</p></div></div>
        <div class="tablet-lg:grid-col-6 margin-bottom-2"><div class="border radius-md border-base-lighter padding-x-2"><p class="desktop-lg:font-sans-sm margin-bottom-0 text-bold">Award max.</p><p class="font-sans-sm">{money(fmax)}</p></div></div>
      </div>
      <div class="border radius-md border-base-lighter padding-x-2 padding-y-1"><ul class="usa-list usa-list--unstyled">
        {box_li('Funding opportunity number', esc(cf['federalOpportunityNumber']['value']))}
        {box_li('Cost sharing or matching requirement', 'No')}
        {box_li('Funding instrument type', 'Grant')}
        {box_li('Opportunity Category', esc(cf['federalFundingSource']['value'].capitalize()))}
      </ul></div>
    </div>
    <div class="margin-top-4"><h2>History</h2>
      <div class="border radius-md border-base-lighter padding-x-2"><ul class="usa-list usa-list--unstyled">
        <li class="margin-y-1"><span class="text-bold text-no-wrap">Posted date:</span> <span>{fmt_date(posted)}</span></li>
      </ul></div>
    </div>
  </div>

  <div class="desktop:grid-col-8 grid-col-12">
    <div class="display-block tablet:display-flex flex-align-end margin-bottom-2">
      <h2 class="flex-1 margin-bottom-0">Summary</h2>
      <a class="usa-button usa-button--unstyled text-no-underline" href="#opportunity-documents">{icon('arrow_downward')} Jump to documents</a>
    </div>
    {summary}

    <section class="sgg-nofo-card" aria-labelledby="nofo-card-heading">
      <h3 id="nofo-card-heading" class="font-sans-lg">Notice of funding opportunity (NOFO)<span class="sgg-new">New</span></h3>
      <p class="margin-top-1">The NOFO has everything you need to decide whether to apply and how to prepare your application. Read it online, or download the PDF to print.</p>
      <div class="opportunity-header__buttons tablet-lg:flex-justify-start">
        <a class="usa-button margin-right-0" href="{nofo_url}">Read the NOFO online</a>
        <a class="usa-button usa-button--outline" href="#pdf">{icon('file_download')} Download PDF</a>
      </div>
      <h4 class="font-sans-sm margin-top-3 margin-bottom-0">Go straight to</h4>
      <ul class="sgg-jump">{jump_html}</ul>
    </section>

    <h2 class="margin-top-6">Eligibility</h2>
    <div class="padding-left-6">
      <h3 class="font-sans-md">Government</h3>
      <ul><li class="margin-bottom-2">State governments</li></ul>
      <h3 class="font-sans-md">Additional information on eligibility</h3>
      <p>States with a Federally-facilitated Exchange (FFE) as of January 1, 2026. See <a class="usa-link" href="{nofo_url}#{ids.get('Eligibility', '')}">eligibility in the NOFO</a> for all criteria.</p>
    </div>

    <div class="grid-row margin-top-6 simpler-page-anchor-offset flex-justify flex-align-center" id="opportunity-documents">
      <div class="grid-col-auto margin-right-3 margin-bottom-1"><h2>Documents</h2></div>
      <div class="grid-col-auto margin-bottom-2"><button type="button" class="usa-button usa-button--outline">Download all {icon('file_download', 'usa-icon--size-4')}</button></div>
      <table class="usa-table usa-table--stacked width-full overflow-wrap">
        <thead><tr><th scope="col">File name</th><th scope="col">Description</th><th scope="col">Last updated</th></tr></thead>
        <tbody>
          <tr><td data-label="File name"><a class="usa-link" href="{nofo_url}">{esc(nofo['number'])} NOFO (web page)</a></td><td data-label="Description">Full NOFO as an accessible web page, with links to each section</td><td data-label="Last updated">Nov 13, 2024</td></tr>
          <tr><td data-label="File name"><a class="usa-link" href="#pdf">{esc(nofo['number'])}.pdf</a></td><td data-label="Description">Full NOFO, PDF for printing</td><td data-label="Last updated">Nov 13, 2024</td></tr>
        </tbody>
      </table>
    </div>

    <div class="margin-top-6"><h2>Agency contact information</h2>
      <p><strong>Email:</strong> <a class="usa-link" href="mailto:{esc(email)}">{esc(email)}</a></p>
      <p>See <a class="usa-link" href="{nofo_url}#{ids.get('Agency contacts', '')}">agency contacts in the NOFO</a> for program and budget contacts.</p>
    </div>
    <div class="margin-top-6"><h2>Link to additional information</h2><p>No additional information is available</p></div>
  </div>
</div>
</div>
</main>""" + bottom


def guide_page(chrome_parts):
    return f"""
<main id="main-content" class="grid-container padding-y-5" tabindex="-1">

  <h1 class="font-sans-xl margin-top-4">NOFO pages in Simpler.Grants.gov</h1>
  <p class="usa-intro">Mockups for CMS-2U2-25-001, built with the site's own USWDS theme (compiled from its source) and real data from the Simpler.Grants.gov API.</p>
  <ul class="usa-card-group">
    {''.join(f'''<li class="usa-card tablet:grid-col-6"><div class="usa-card__container"><div class="usa-card__header"><h2 class="usa-card__heading font-sans-md">{t}</h2></div><div class="usa-card__body"><p>{d}</p></div><div class="usa-card__footer"><a class="usa-button" href="{h}">Open</a></div></div></li>''' for t, d, h in [
        ('Opportunity listing', 'The existing listing page with a new NOFO section: read online, download the PDF, or jump straight to a section.', 'opportunity.html'),
        ('NOFO inside the site', 'The NOFO as a page of the site, with header, footer, breadcrumbs and a link back to the listing.', 'nofo.html'),
        ('NOFO on its own', 'The same NOFO without site chrome: the self-contained file that could be attached to an opportunity (issue #851).', 'nofo-standalone.html'),
        ('Content components', 'A sample NOFO showing the introduction, several deadlines, subagencies, note callouts, table captions and merged cells, list types, points labels, appendix and modifications.', 'components.html'),
        ('Edge-case patterns', 'Several opportunity numbers, components, status changes, modifications, reissues and other cases.', 'edge-cases.html'),
    ])}
  </ul>
</main>"""


def shell(title, body, extra_js=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,300..800;1,400..700&display=swap" rel="stylesheet">
<style>/*CSS*/</style>
</head>
<body class="theme-sgg">
<!--SPRITE-->
{body}
<div class="usa-sr-only" aria-live="polite" id="nofo-live"></div>
<script>{base.PAGE_JS}</script>
<script>{extra_js}</script>
</body>
</html>
"""


def inline_sprite(html_text, sprite):
    """Replace <!--SPRITE--> with only the USWDS icon symbols the page uses."""
    used = sorted(set(re.findall(r'href="#([a-z_0-9]+)"></use>', html_text)))
    pattern = r'<symbol id="(?:%s)".*?</symbol>' % "|".join(used)
    syms = "".join(re.findall(pattern, sprite, flags=re.S)) if used else ""
    sheet = f'<svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true">{syms}</svg>'
    return html_text.replace("<!--SPRITE-->", sheet)


def main():
    nofo = json.loads(Path(sys.argv[1]).read_text())
    opp = json.loads(Path(sys.argv[2]).read_text())
    dist, logo, sgg_css, out = (
        Path(sys.argv[3]),
        Path(sys.argv[4]),
        Path(sys.argv[5]),
        Path(sys.argv[6]),
    )
    out.mkdir(parents=True, exist_ok=True)
    parts = chrome(dist, logo)
    pages = {
        "opportunity.html": shell(
            f"Opportunity Listing - {opp['title']}",
            opportunity_page(nofo, opp, parts),
            CHROME_JS,
        ),
        "nofo.html": shell(
            f"NOFO: {nofo['title']} | {nofo['number']}",
            nofo_page(nofo, opp, parts, False),
            CHROME_JS,
        ),
        "nofo-standalone.html": shell(
            f"NOFO: {nofo['title']} | {nofo['number']}",
            nofo_page(nofo, opp, parts, True),
        ),
        "index.html": shell(
            "NOFO pages in Simpler.Grants.gov (mockups)",
            parts[0] + guide_page(parts) + parts[1],
            CHROME_JS,
        ),
    }
    # CSS: the site's compiled theme with bundled font files dropped (Public Sans comes from Google Fonts)
    css = Path(sgg_css).read_text()
    css = re.sub(r"@font-face\{[^}]*\}", "", css)
    css = css.replace('"Public Sans Web"', '"Public Sans"').replace(
        "Public Sans Web", '"Public Sans"'
    )
    css = re.sub(r"@import url\([^)]*\);?", "", css)
    local = base.LOCAL_CSS.strip() + SGG_VARS
    sprite = Path(dist / "img/sprite.svg").read_text()
    for name, html_text in pages.items():
        html_text = inline_sprite(html_text, sprite)
        (out / name).write_text(html_text.replace("/*CSS*/", "/*SGG-CSS*/" + local))
    (out / "_sgg_full.css").write_text(css)
    print("\n".join(pages))


if __name__ == "__main__":
    main()
