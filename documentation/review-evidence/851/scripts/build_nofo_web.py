"""Build NOFO web page mockups (USWDS 3.8.1) from a NOFO Builder JSON export.

Usage: python build_nofo_web.py <nofo.json> <uswds_dist_dir> <out_dir>

Produces two variants from the same content:
  * Multi-page: one page per section (index.html = Step 1), left side navigation,
    previous/next pagination.
  * Single page: one-page.html, the whole NOFO with a sticky USWDS in-page nav.
No site header or footer: the output is the content region an agency site would wrap.
"""

import html
import json
import re
import shutil
import sys
from pathlib import Path

import markdown
from bs4 import BeautifulSoup

USWDS_VERSION = "3.8.1"
SPRITE = "img/sprite.svg"


def esc(s):
    return html.escape(s or "", quote=True)


def icon(name, cls=""):
    return (
        f'<svg class="usa-icon {cls}" aria-hidden="true" focusable="false" role="img">'
        f'<use href="{SPRITE}#{name}"></use></svg>'
    )


def md(body):
    return markdown.markdown(body or "", extensions=["extra"])


# ---------- content parsing ----------

LABEL_LINE = re.compile(r"^([^:\n]{2,80}):\s+(.+)$")
DATE_SPLIT = re.compile(r"^(.*?\b\d{4})(?:,\s*(.+))?$")


def label_lines(body):
    """Return [(label, value)] if every paragraph in body is 'Label: value'."""
    paras = [p.strip() for p in (body or "").split("\n\n") if p.strip()]
    pairs = []
    for p in paras:
        m = LABEL_LINE.match(p)
        if not m or "\n" in p:
            return None
        pairs.append((m.group(1).strip(), m.group(2).strip()))
    return pairs or None


def inline_md(text):
    out = md(text)
    return re.sub(r"^<p>(.*)</p>$", r"\1", out.strip(), flags=re.S)


def render_facts(pairs, dates=False):
    rows = []
    for label, value in pairs:
        note = ""
        if dates:
            m = DATE_SPLIT.match(value)
            if m and m.group(2):
                value, note = m.group(1), m.group(2)
        note_html = (
            f'<span class="nofo-facts__note">{inline_md(note)}</span>' if note else ""
        )
        rows.append(
            f'<div class="nofo-facts__row"><dt>{esc(label)}</dt>'
            f"<dd>{inline_md(value)}{note_html}</dd></div>"
        )
    return f'<dl class="nofo-facts">{"".join(rows)}</dl>'


# Checklist glyphs, as the Builder handles them: import maps Word's "¨" (Wingdings) and
# "☐" to "◻" (content_processing.py), and rendering swaps "◻" for a USWDS checkbox icon
# (replace_unicode_with_icon.py). The fixture JSON predates the import step, so do both.
CHECKBOX_GLYPHS = ("\u00a8", "\u2610", "\u25fb", "\u007f")


def replace_checkboxes(fragment):
    box = icon("check_box_outline_blank", "nofo-checkbox")
    for glyph in CHECKBOX_GLYPHS:
        fragment = re.sub(re.escape(glyph) + r"[ \u00a0]?", box, fragment)
    return fragment


def enhance(fragment):
    """USWDS-ify rendered markdown: tables, external links, endnote refs, checkboxes."""
    soup = BeautifulSoup(replace_checkboxes(fragment), "html.parser")
    seen = {}
    for table in soup.find_all("table"):
        table["class"] = ["usa-table", "usa-table--borderless", "nofo-table"]
        # A focusable scroll container needs a role and a name (WCAG 4.1.2, 2.1.1)
        prev = table.find_previous(re.compile(r"^h[2-6]$"))
        name = prev.get_text("", strip=False).strip() if prev else "Table"
        seen[name] = seen.get(name, 0) + 1
        if seen[name] > 1:
            name = f"{name} ({seen[name]})"
        wrap = soup.new_tag(
            "div",
            attrs={
                "class": "usa-table-container--scrollable nofo-table-wrap",
                "tabindex": "0",
                "role": "region",
                "aria-label": f"Table: {name}",
            },
        )
        table.wrap(wrap)
        # first row of bold-only cells in a header-less table becomes a header row
        if not table.find("th"):
            first = table.find("tr")
            if first and all(td.find(["strong", "b"]) for td in first.find_all("td")):
                for td in first.find_all("td"):
                    td.name = "th"
                    td["scope"] = "col"
    for a in soup.find_all("a", href=True):
        if a.has_attr("data-anchor"):
            continue
        href = a["href"]
        if href.startswith("http"):
            a["class"] = ["usa-link", "usa-link--external"]
            a["rel"] = "noreferrer"
        elif href.startswith("#"):
            a["class"] = ["usa-link"]
    return str(soup)


def heading(level, hid, inner_html, label_text, extra_class=""):
    """Heading with a visible, keyboard-reachable anchor link beside it.

    The link sits outside the <hN> so the heading's accessible name stays clean;
    its own name is "Link to this section: <heading>".
    """
    cls = f' class="{extra_class}"' if extra_class else ""
    return (
        f'<div class="nofo-heading nofo-heading--h{level}">'
        f'<h{level} id="{hid}" tabindex="-1"{cls}>{inner_html}</h{level}>'
        f'<a class="nofo-anchor" href="#{hid}" data-anchor>'
        f'{icon("link")}<span class="usa-sr-only">Link to this section: {esc(label_text)}</span>'
        f'<span class="nofo-anchor__status" aria-hidden="true"></span></a></div>'
    )


def subsection_html(ss, level=None):
    name, tag, body = ss.get("name", ""), ss.get("tag", ""), ss.get("body", "")
    hid = ss["html_id"]
    if ss.get("callout_box"):
        pairs = label_lines(body)
        is_dates = "date" in name.lower()
        if not name and body.strip().lower().startswith("have questions?"):
            rest = body.strip()[len("Have questions?") :]
            return (
                f'<div class="usa-alert usa-alert--info usa-alert--slim nofo-callout" id="{hid}">'
                f'<div class="usa-alert__body"><p class="usa-alert__text">'
                f"<strong>Have questions?</strong> {inline_md(rest)}</p></div></div>"
            )
        inner = render_facts(pairs, dates=is_dates) if pairs else md(body)
        head = (
            heading(level, hid, esc(name), name, "usa-summary-box__heading")
            if name
            else ""
        )
        return (
            f'<div class="usa-summary-box nofo-summary" role="region"'
            f'{f" aria-labelledby=\"{hid}\"" if name else ""}>'
            f'<div class="usa-summary-box__body">{head}'
            f'<div class="usa-summary-box__text">{inner}</div></div></div>'
        )
    out = []
    if name and level:
        out.append(heading(level, hid, esc(name), name))
    if body.strip():
        pairs = label_lines(body) if name.lower() == "funding details" else None
        out.append(render_facts(pairs) if pairs else md(body))
    return "\n".join(out)


def step_label(name):
    m = re.match(r"^(Step \d+):\s*(.+)$", name)
    return (m.group(1), m.group(2)) if m else (None, name)


# ---------- page assembly ----------

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Merriweather:ital,wght@0,400;0,700;1,400'
    "&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&family=Roboto+Mono"
    '&display=swap" rel="stylesheet">'
)

LOCAL_CSS = """
/* USWDS 3.8.1 is the design system: tokens, components and type come from it.
   These rules only cover NOFO-specific patterns (facts list, sticky nav, title block). */
:root{color-scheme:light;--nofo-accent:#005ea2;--nofo-accent-bg:#e1f3f8;--nofo-muted:#565c65;--nofo-muted-dark:#3d4551;--nofo-border:#dfe1e2;--nofo-display:Merriweather,Georgia,serif;--nofo-sticky-top:1rem}
body{background:#fff;color:#1b1b1b;margin:0}
.nofo-page{padding-left:max(2rem,16px,env(safe-area-inset-left,0px));padding-right:max(2rem,16px,env(safe-area-inset-right,0px));padding-bottom:4rem}
.nofo-mock{margin:0 calc(-1*max(2rem,16px,env(safe-area-inset-left,0px)))}
.nofo-title{padding-block:2rem 1.5rem;border-bottom:1px solid var(--nofo-border);margin-bottom:2rem}
.nofo-title__agency{font-size:1rem;color:var(--nofo-muted);margin:0 0 .5rem;line-height:1.4;max-width:none}
.nofo-title__agency span{display:block}
.nofo-title h1{font-size:clamp(1.75rem,3.2vw,2.5rem);line-height:1.15;margin:0 0 .75rem;max-width:30ch}
.nofo-title__tagline{font-size:1.25rem;line-height:1.5;margin:0 0 1.25rem;color:var(--nofo-muted-dark);max-width:60ch}
.nofo-title__meta{display:flex;flex-wrap:wrap;gap:.5rem 2rem;margin:0 0 1.5rem;padding:0;list-style:none}
.nofo-title__meta li{margin:0;max-width:none}
.nofo-title__meta .k{display:block;font-size:.875rem;color:var(--nofo-muted)}
.nofo-title__meta .v{font-weight:700;font-size:1.0625rem;white-space:nowrap}
.nofo-title .usa-button-group{margin:0}
.nofo-title .usa-button .usa-icon{margin-right:.35rem;vertical-align:-.2em}
.nofo-layout{display:grid;gap:2rem;grid-template-columns:minmax(0,1fr)}
@media(min-width:64em){.nofo-layout{grid-template-columns:16rem minmax(0,1fr);gap:3rem}.nofo-sidebar{position:sticky;top:var(--nofo-sticky-top);align-self:start;max-height:calc(100vh - var(--nofo-sticky-top) - 1rem);overflow-y:auto}}
.nofo-sidebar__label{font-size:.875rem;font-weight:700;color:var(--nofo-muted);margin:0 0 .5rem}
.nofo-sidebar .usa-sidenav__item a{padding-block:.6rem}
.nofo-sidebar .usa-sidenav__sublist a{font-size:.9375rem;padding-block:.4rem}
.nofo-step{display:block;font-size:.8125rem;font-weight:400;color:var(--nofo-muted)}
.usa-current .nofo-step{color:var(--nofo-accent)}
@media(max-width:63.99em){.nofo-sidebar .usa-sidenav__sublist{display:none}}
.nofo-content{max-width:46rem}
.nofo-content h2{font-size:2rem;line-height:1.2}
.nofo-content h2 .nofo-step{font-size:1.125rem;font-weight:700;color:var(--nofo-accent);margin-bottom:.25rem}
.nofo-content h3{font-size:1.5rem}
.nofo-content h4{font-size:1.25rem}
.nofo-content h5{font-size:1.0625rem}
.nofo-content [id]{scroll-margin-top:calc(var(--nofo-sticky-top) + .5rem)}
/* Headings with section links */
.nofo-heading{display:flex;align-items:flex-start;gap:.25rem;margin:2rem -.5rem .5rem;padding:.25rem .5rem;border-radius:.25rem}
.nofo-heading--h2{margin-top:0}
.nofo-heading--h3{margin-top:2.75rem}
.nofo-heading--h5{margin-top:1.5rem}
.nofo-heading>:is(h2,h3,h4,h5,h6){margin:0;flex:0 1 auto}
.nofo-heading>:is(h2,h3,h4,h5,h6):focus{outline:0}
.usa-summary-box .nofo-heading{margin-top:0}
.nofo-anchor{flex:none;display:inline-flex;align-items:center;justify-content:center;gap:.25rem;min-width:2rem;min-height:2rem;margin-top:.1em;padding:0 .25rem;border-radius:.25rem;color:var(--nofo-muted);text-decoration:none;font-size:.875rem;font-weight:600}
.nofo-anchor .usa-icon{width:1.25rem;height:1.25rem}
.nofo-anchor:hover{color:var(--nofo-accent);background:var(--nofo-accent-bg)}
.nofo-anchor:focus{outline:.25rem solid #2491ff;outline-offset:0}
.nofo-anchor.is-copied{color:#00a91c;color:#008817}
.nofo-anchor__status:empty{display:none}
/* Target highlight: the section a link just took you to. Gold, so it never reads as keyboard focus (blue). */
.nofo-heading:has(>:target),.nofo-heading>:target{background:#fef0c8;box-shadow:inset .3rem 0 0 #8e6a00;outline:2px solid #8e6a00;outline-offset:2px}
.nofo-heading:has(>:target)>:target{background:none;box-shadow:none;outline:0}
@media (prefers-reduced-motion:no-preference){.nofo-heading:has(>:target){animation:nofo-target 1.2s ease-out}}
@keyframes nofo-target{from{background:#ffe396}to{background:#fef0c8}}
#nofo-content:focus{outline:0}
/* Windows high contrast / forced colors keep both indicators */
@media (forced-colors:active){.nofo-heading:has(>:target){outline:3px solid Highlight;box-shadow:none}.nofo-anchor:focus,.nofo-pager a:focus{outline:3px solid Highlight}}
.nofo-sidebar__all{margin:1rem 0 0;font-size:.9375rem;line-height:1.4}
.nofo-sidebar__all span{display:block;color:var(--nofo-muted);font-size:.875rem}
@media print{.usa-skipnav,.nofo-mock,.nofo-sidebar,.nofo-pager,.nofo-anchor,.usa-in-page-nav,.nofo-backtop,.nofo-title .usa-button-group{display:none!important}.nofo-layout{display:block}.nofo-heading{background:none!important;box-shadow:none!important;outline:0!important}.nofo-content{max-width:none}a.usa-link--external::after{content:" (" attr(href) ")";background:none;display:inline;width:auto;height:auto;margin:0;font-size:.8em}}
.nofo-summary,.nofo-callout{margin-block:1.5rem}
.nofo-facts{margin:0}
.nofo-facts__row{display:grid;grid-template-columns:minmax(0,13rem) minmax(0,1fr);gap:.25rem 1rem;padding-block:.5rem;border-top:1px solid rgba(0,0,0,.1)}
.nofo-facts__row:first-child{border-top:0;padding-top:0}
.nofo-facts dt{font-weight:700}
.nofo-facts dd{margin:0}
.nofo-facts__note{display:block;font-size:.9375rem;color:var(--nofo-muted-dark);margin-top:.15rem}
@media(max-width:30em){.nofo-facts__row{grid-template-columns:minmax(0,1fr)}}
.usa-prose .nofo-glance,.nofo-glance{display:grid;grid-template-columns:repeat(auto-fit,minmax(10rem,1fr));gap:1rem;margin:1.5rem 0 2rem;padding:0;list-style:none;max-width:none}
.nofo-glance li{margin:0;max-width:none;border:1px solid var(--nofo-border);border-top:.35rem solid var(--nofo-accent);padding:1rem 1.25rem}
.nofo-glance .k{display:block;font-size:.9375rem;color:var(--nofo-muted)}
.nofo-glance .v{display:block;font-family:var(--nofo-display);font-size:1.5rem;font-weight:700;line-height:1.25;margin-block:.25rem}
.nofo-glance .n{display:block;font-size:.9375rem}
.nofo-table-wrap{margin-block:1rem}
.nofo-checkbox{width:1.25rem;height:1.25rem;vertical-align:-.25em;margin-right:.35rem;fill:currentColor}
.nofo-table{font-size:.9375rem;width:100%}
.nofo-table-wrap .nofo-table th,.nofo-table-wrap .nofo-table td{vertical-align:top;white-space:normal;min-width:10rem}
.nofo-pager{margin-top:3rem;padding-top:1.5rem;border-top:1px solid var(--nofo-border);display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:1rem}
.nofo-pager a{display:block;text-decoration:none;padding:1rem;border:1px solid var(--nofo-border);border-radius:.25rem;color:var(--nofo-accent)}
.nofo-pager a:hover{border-color:var(--nofo-accent);background:var(--nofo-accent-bg)}
.nofo-pager a:focus{outline:.25rem solid #2491ff;outline-offset:0}
.nofo-pager .dir{display:flex;align-items:center;gap:.25rem;font-size:.9375rem;color:var(--nofo-muted-dark)}
.nofo-pager .t{display:block;font-weight:700;font-size:1.0625rem;margin-top:.25rem}
.nofo-pager .next{text-align:right;grid-column:2}
.nofo-pager .next .dir{justify-content:flex-end}
@media(max-width:30em){.nofo-pager{grid-template-columns:minmax(0,1fr)}.nofo-pager .next{grid-column:1}}
.nofo-onepage .usa-in-page-nav-container{display:block}
.nofo-onepage .usa-in-page-nav{display:block;margin:0 0 2rem;padding:1rem 1.25rem;border:1px solid var(--nofo-border);border-radius:.25rem}
.nofo-onepage .usa-in-page-nav__nav{position:static;max-height:none;padding:0;margin:0}
.nofo-onepage .usa-in-page-nav__item:not(.usa-in-page-nav__item--primary){display:none}
@media(min-width:64em){
.nofo-onepage .usa-in-page-nav-container{display:flex;gap:3rem;align-items:flex-start}
.nofo-onepage .usa-in-page-nav{order:2;flex:0 0 16rem;position:sticky;top:var(--nofo-sticky-top);max-height:calc(100vh - var(--nofo-sticky-top) - 1rem);overflow-y:auto;margin:0;padding:0;border:0}
.nofo-onepage .usa-in-page-nav__item:not(.usa-in-page-nav__item--primary){display:list-item}
.nofo-onepage .nofo-content{flex:1 1 auto}}
.nofo-onepage .nofo-content>section+section{margin-top:3.5rem;padding-top:2rem;border-top:3px solid #1b1b1b}
.usa-in-page-nav__link:focus{outline:.25rem solid #2491ff;outline-offset:0}
.nofo-nav--collapsible .usa-in-page-nav__item:not(.usa-in-page-nav__item--primary):not(.is-open){display:none}
.nofo-backtop{display:inline-flex;align-items:center;gap:.25rem;margin-top:1rem;font-size:.9375rem}
"""


PAGE_JS = """{
/* Section links: the href works without script (it moves to the heading and updates the URL).
   With script, also copy the full URL and confirm it visually and to screen readers. */
const live=document.getElementById('nofo-live');
document.addEventListener('click',async e=>{
  const a=e.target.closest('a[data-anchor]');
  if(!a)return;
  const url=location.href.split('#')[0]+a.getAttribute('href');
  const status=a.querySelector('.nofo-anchor__status');
  let msg='Link is in the address bar';
  try{await navigator.clipboard.writeText(url);msg='Link copied';}catch(err){}
  status.textContent=msg;a.classList.add('is-copied');live.textContent='';
  setTimeout(()=>{live.textContent=msg+'.';},50);
  clearTimeout(a._t);a._t=setTimeout(()=>{a.classList.remove('is-copied');status.textContent='';},2500);
});
/* Move keyboard and screen reader focus to the section reached by any in-page link,
   so the next Tab continues from there (headings carry tabindex="-1"). */
function focusTarget(){
  const id=decodeURIComponent(location.hash.slice(1));
  if(!id)return;
  const el=document.getElementById(id);
  if(el&&el.hasAttribute('tabindex'))el.focus({preventScroll:true});
}
window.addEventListener('hashchange',focusTarget);
/* "On this page" is static USWDS markup linking to the builder's stable heading ids
   (USWDS's own script would invent new ids from heading text). With script, the list shows the
   steps and opens only the current step's subsections, so it stays short on long NOFOs; the
   current item comes from scroll position, so short final sections can still be marked.
   Without script every item stays visible. */
const navLinks=[...document.querySelectorAll('.usa-in-page-nav__link')];
if(navLinks.length){
  const nav=document.querySelector('.usa-in-page-nav');
  const heads=navLinks.map(a=>({a,li:a.parentElement,h:document.getElementById(a.hash.slice(1))})).filter(x=>x.h);
  nav.classList.add('nofo-nav--collapsible');
  let current=null;
  const setCurrent=x=>{
    if(!x||x===current)return;current=x;
    navLinks.forEach(l=>{l.classList.remove('usa-current');l.removeAttribute('aria-current');});
    x.a.classList.add('usa-current');x.a.setAttribute('aria-current','location');
    const g=x.li.dataset.group;heads.forEach(y=>y.li.classList.toggle('is-open',y.li.dataset.group===g));
    const r=x.a.getBoundingClientRect(),br=nav.getBoundingClientRect();
    if(nav.scrollHeight>nav.clientHeight&&(r.top<br.top||r.bottom>br.bottom))nav.scrollTop+=r.top-br.top-br.height/3;
  };
  const update=()=>{
    const v=getComputedStyle(document.documentElement).getPropertyValue('--nofo-sticky-top').trim();
    const line=(v.endsWith('px')?parseFloat(v):16)+48;
    const atEnd=innerHeight+scrollY>=document.documentElement.scrollHeight-4;
    let pick=heads[0];
    for(const x of heads){const t=x.h.getBoundingClientRect().top;if(t<=line||(atEnd&&t<innerHeight))pick=x;}
    setCurrent(pick);
  };
  let raf=0;
  addEventListener('scroll',()=>{if(!raf)raf=requestAnimationFrame(()=>{raf=0;update();});},{passive:true});
  addEventListener('resize',update);addEventListener('hashchange',update);update();
}
if(location.hash)window.addEventListener('load',focusTarget);
}"""


def page_shell(title, body, description, script=False):
    js = (
        f'<script src="https://cdn.jsdelivr.net/npm/@uswds/uswds@{USWDS_VERSION}/dist/js/uswds.min.js"></script>'
        if script
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="claude:viewport-fit-sides" content="cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
{FONTS}
<link rel="stylesheet" href="css/uswds.min.css">
<link rel="stylesheet" href="css/nofo-web.css">
</head>
<body>
{body}
<div class="usa-sr-only" aria-live="polite" id="nofo-live"></div>
{js}
<script>{PAGE_JS}</script>
</body>
</html>
"""


def build(nofo, out):
    sections = sorted(nofo["sections"], key=lambda s: s["order"])
    meta = {}
    basic = None
    for ss in sections[0]["subsections"]:
        if ss.get("name") == "Basic information":
            basic = ss
            meta = dict(label_lines(ss["body"]) or [])
    description = meta.get("Metadata subject", nofo.get("tagline", ""))

    # file name for each section
    pages = []
    for i, s in enumerate(sections):
        fname = s["html_id"][:48].strip("-") + ".html"
        pages.append({"section": s, "file": fname})

    # key dates / facts for the "at a glance" row on Step 1
    s1 = {ss.get("name"): ss for ss in sections[0]["subsections"]}
    dates = dict(label_lines(s1.get("Key dates", {}).get("body", "")) or [])
    deadline = DATE_SPLIT.match(
        dates.get("Application submission deadline", nofo["application_deadline"])
    )
    funding = s1.get("Funding details", {}).get("body", "")
    total = re.search(r"\$\d[\d,]*\d", funding.split("total funding", 1)[-1])
    awards = re.search(r"Expected total awards:\s*([^\n]+?)\.?\s*\n", funding)
    base = re.search(r"\$[\d,]+(?= base award)", funding)

    def title_block(current_label):
        return f"""
<div class="nofo-title">
  <p class="nofo-title__agency"><span>{esc(nofo['opdiv'])}</span><span>{esc(nofo['agency'])}</span></p>
  <h1>{esc(nofo['title'])}</h1>
  <p class="nofo-title__tagline">{esc(nofo.get('tagline', ''))}</p>
  <ul class="nofo-title__meta">
    <li><span class="k">Opportunity number</span><span class="v">{esc(nofo['number'])}</span></li>
    <li><span class="k">Assistance listing</span><span class="v">{esc(meta.get('Assistance Listing', '').strip())}</span></li>
    <li><span class="k">Application deadline</span><span class="v">{esc(nofo['application_deadline'])}</span></li>
  </ul>
  <ul class="usa-button-group">
    <li class="usa-button-group__item"><a class="usa-button" href="#pdf-download">{icon('file_download')}Download the full NOFO (PDF)</a></li>
    <li class="usa-button-group__item"><a class="usa-button usa-button--outline" href="https://simpler.grants.gov/search?query={esc(nofo['number'])}">Apply on Grants.gov</a></li>
  </ul>
</div>"""

    def mock_banner(other_href, other_label):
        return f"""
<div class="usa-alert usa-alert--info usa-alert--slim nofo-mock">
  <div class="usa-alert__body"><p class="usa-alert__text"><strong>Design mockup.</strong> Text from {esc(nofo['number'])} in the NOFO Builder test fixtures; not an official notice. <a class="usa-link" href="{other_href}">{other_label}</a></p></div>
</div>"""

    def glance():
        items = [
            (
                "Application deadline",
                deadline.group(1) if deadline else nofo["application_deadline"],
                (
                    f"Letter of intent by {DATE_SPLIT.match(dates['Optional letter of intent deadline']).group(1)} (optional)"
                    if "Optional letter of intent deadline" in dates
                    else ""
                ),
            ),
            (
                "Expected total funding",
                total.group(0) if total else "",
                "Subject to availability of funds",
            ),
            (
                "Expected awards",
                (awards.group(1) if awards else ""),
                f"{base.group(0)} base award each" if base else "",
            ),
            (
                "Expected award date",
                (
                    DATE_SPLIT.match(dates.get("Expected award date", "")).group(1)
                    if dates.get("Expected award date")
                    else ""
                ),
                "Three-year period of performance",
            ),
        ]
        lis = "".join(
            f'<li><span class="k">{esc(k)}</span><span class="v">{esc(v)}</span><span class="n">{esc(n)}</span></li>'
            for k, v, n in items
            if v
        )
        return f'<ul class="nofo-glance" aria-label="At a glance">{lis}</ul>'

    def section_body(s, include_glance=False):
        parts = []
        step, label = step_label(s["name"])
        step_html = (
            f'<span class="nofo-step">{esc(step)}<span class="usa-sr-only">: </span></span>'
            if step
            else ""
        )
        parts.append(heading(2, s["html_id"], f"{step_html}{esc(label)}", s["name"]))
        if include_glance:
            parts.append(glance())
        prev = 2
        for ss in sorted(s["subsections"], key=lambda x: x["order"]):
            if ss is basic:
                continue  # document metadata: used for the title block and <meta>, not shown
            level = None
            if ss.get("tag") and ss.get("name"):
                # never skip a level (WCAG 1.3.1): h2 -> h4 becomes h2 -> h3
                level = min(int(ss["tag"][1]), prev + 1)
                prev = level
            parts.append(subsection_html(ss, level))
        return enhance("\n".join(parts))

    def sidenav(current_idx):
        items = []
        for i, p in enumerate(pages):
            s = p["section"]
            step, label = step_label(s["name"])
            cur = i == current_idx
            step_html = (
                f'<span class="nofo-step">{esc(step)}<span class="usa-sr-only">: </span></span>'
                if step
                else ""
            )
            sub = ""
            if cur:
                subs = [
                    ss
                    for ss in s["subsections"]
                    if ss.get("tag") == "h3" and ss is not basic and ss.get("name")
                ]
                if subs:
                    sub = (
                        '<ul class="usa-sidenav__sublist">'
                        + "".join(
                            f'<li class="usa-sidenav__item"><a href="#{ss["html_id"]}">{esc(ss["name"])}</a></li>'
                            for ss in subs
                        )
                        + "</ul>"
                    )
            items.append(
                f'<li class="usa-sidenav__item"><a href="{p["file"]}"'
                f'{" class=\"usa-current\" aria-current=\"page\"" if cur else ""}>{step_html}{esc(label)}</a>{sub}</li>'
            )
        return (
            '<nav class="nofo-sidebar" aria-labelledby="nofo-nav-label">'
            '<p class="nofo-sidebar__label" id="nofo-nav-label">In this NOFO</p>'
            f'<ul class="usa-sidenav">{"".join(items)}</ul>'
            f'<p class="nofo-sidebar__all"><a class="usa-link" href="one-page.html">View all steps on one page</a>'
            f"<span>Best for printing and searching the whole NOFO</span></p></nav>"
        )

    def pager(i):
        out = []
        if i > 0:
            p = pages[i - 1]
            out.append(
                f'<a class="prev" href="{p["file"]}"><span class="dir">{icon("navigate_before")}Previous</span><span class="t">{esc(p["section"]["name"])}</span></a>'
            )
        if i < len(pages) - 1:
            p = pages[i + 1]
            out.append(
                f'<a class="next" href="{p["file"]}"><span class="dir">Next{icon("navigate_next")}</span><span class="t">{esc(p["section"]["name"])}</span></a>'
            )
        return f'<nav class="nofo-pager" aria-label="Previous and next sections">{"".join(out)}</nav>'

    # render all pages, then fix in-document anchors to point across pages
    rendered = {}
    id_page = {}
    for i, p in enumerate(pages):
        content = section_body(p["section"], include_glance=(i == 0))
        for m in re.finditer(r'\sid="([^"]+)"', content):
            id_page[m.group(1)] = p["file"]
        rendered[p["file"]] = (i, content)

    def fix_links(content, here):
        def rep(m):
            target = m.group(1)
            f = id_page.get(target)
            if f and f != here:
                return f'href="{f}#{target}"'
            return m.group(0)

        return re.sub(r'href="#([^"]+)"', rep, content)

    for f, (i, content) in rendered.items():
        s = pages[i]["section"]
        body = f"""
<a class="usa-skipnav" href="#nofo-content">Skip to {esc(s['name'])}</a>
<main class="nofo-page">
{mock_banner('one-page.html', 'Compare: the whole NOFO on one page')}
{title_block(s['name'])}
<div class="nofo-layout">
{sidenav(i)}
<article class="nofo-content usa-prose" id="nofo-content" tabindex="-1">
{fix_links(content, f)}
{pager(i)}
</article>
</div>
</main>"""
        title = f"{s['name']} | {nofo['number']}"
        (out / f).write_text(page_shell(title, body, description))

    # single-page variant
    secs = []
    nav_items = []
    for p in pages:
        content = section_body(p["section"])
        for m in re.finditer(
            r'<h([23]) id="([^"]+)" tabindex="-1"(?: class="([^"]*)")?>(.*?)</h\1>',
            content,
        ):
            lvl, hid, cls, inner = m.groups()
            if cls and "summary-box" in cls:
                continue
            text = BeautifulSoup(inner, "html.parser").get_text().replace(": ", ": ")
            primary = " usa-in-page-nav__item--primary" if lvl == "2" else ""
            nav_items.append(
                f'<li class="usa-in-page-nav__item{primary}" data-group="{p["section"]["html_id"]}">'
                f'<a class="usa-in-page-nav__link" href="#{hid}">{esc(text)}</a></li>'
            )
        secs.append(
            f'<section aria-labelledby="{p["section"]["html_id"]}">{content}'
            f'<a class="usa-link nofo-backtop" href="#top">{icon("arrow_upward")}Back to top</a></section>'
        )
    one = f"""
<a class="usa-skipnav" href="#nofo-content">Skip to the NOFO text</a>
<div id="top" tabindex="-1"></div>
<main class="nofo-page nofo-onepage">
{mock_banner(pages[0]['file'], 'Compare: one page per step')}
{title_block('')}
<div class="usa-in-page-nav-container">
  <aside class="usa-in-page-nav"><nav class="usa-in-page-nav__nav" aria-labelledby="on-this-page"><p class="usa-in-page-nav__heading" id="on-this-page">On this page</p><ul class="usa-in-page-nav__list">{''.join(nav_items)}</ul></nav></aside>
  <div class="nofo-content usa-prose" id="nofo-content" tabindex="-1">
  {''.join(secs)}
  </div>
</div>
</main>"""
    one = re.sub(r'href="(?:[a-z0-9-]+\.html)#', 'href="#', one)
    (out / "one-page.html").write_text(
        page_shell(f"{nofo['title']} | {nofo['number']}", one, description)
    )
    return [p["file"] for p in pages] + ["one-page.html"]


def copy_assets(dist, out):
    css = (dist / "css/uswds.min.css").read_text()
    css = re.sub(
        r"@font-face\{[^}]*\}", "", css
    )  # bundled font files are replaced by Google Fonts
    for old, new in [
        ("Merriweather Web", "Merriweather"),
        ("Source Sans Pro Web", "Source Sans 3"),
        ("Roboto Mono Web", "Roboto Mono"),
    ]:
        css = css.replace(f'"{old}"', f'"{new}"').replace(old, f'"{new}"')
    (out / "css").mkdir(parents=True, exist_ok=True)
    (out / "css/uswds.min.css").write_text(css)
    (out / "css/nofo-web.css").write_text(LOCAL_CSS.strip() + "\n")
    refs = sorted(set(re.findall(r"\.\./img/([^)\"']+)", css)))
    for r in refs + ["sprite.svg"]:
        src = dist / "img" / r
        if src.exists():
            dst = out / "img" / r
            dst.parent.mkdir(parents=True, exist_ok=True)
            if (
                src.suffix == ".svg"
            ):  # drop DTD declarations; some hosts reject them in SVG files
                dst.write_text(re.sub(r"<!DOCTYPE[^>]*>", "", src.read_text()))
            else:
                shutil.copy(src, dst)


if __name__ == "__main__":
    nofo = json.loads(Path(sys.argv[1]).read_text())
    dist, out = Path(sys.argv[2]), Path(sys.argv[3])
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    copy_assets(dist, out)
    print("\n".join(build(nofo, out)))
