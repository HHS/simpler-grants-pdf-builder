import ast,re,html,json
from pathlib import Path
from bs4 import BeautifulSoup,Tag,NavigableString,Comment
source=(Path(__file__).resolve().parents[4] / 'nofos/nofos/content_processing.py').read_text(); tree=ast.parse(source)
names={'ELIGIBLE_ORGANIZATION_CATEGORIES','ELIGIBLE_ORGANIZATION_INTROS','repair_eligibility_organization_lists'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets)]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'pr1193','exec'))
out=Path(__file__).resolve().parent;out.mkdir(exist_ok=True)
prefix='<h2>Eligibility</h2><h3>Types of eligible organizations</h3><p>These types of *domestic organizations may apply:</p>'
base='<p>State governments</p><p>County governments</p><p>Small businesses</p>'
tail='<p>“Domestic” means the 50 states and territories.</p><p><strong>Additional information on eligibility</strong></p><p>Individuals are not eligible applicants under this NOFO.</p>'
cases=[
('01-success','Recognized categories','Bullets restored','All category paragraphs are recognized. The definition and restriction stay outside the list.',base+tail,True),
('02-later-restriction-list','A later restriction list','Unchanged','A separate restriction list anywhere in this subsection disables the repair, even when the organization categories are recognized.',base+tail+'<ul><li>Applicants must satisfy the program requirements.</li></ul>',False),
('03-unknown-category','An unfamiliar organization category','Unchanged','“Others” is outside the reviewed vocabulary. The entire organization block stays unbulleted, including the recognized categories.',base+'<p>Others (see additional information on eligibility)</p>'+tail,False),
('04-straight-quotes','Straight quotes in the Unrestricted item','Unchanged','Straight quotation marks are not an accepted spelling of the full Unrestricted label. The entire organization block stays unbulleted.','<p>State governments</p><p>Unrestricted (i.e., open to any type of entity above), subject to any clarification in text field entitled &quot;Additional Information on Eligibility&quot;</p>'+tail,False),
('05-intro-variant','Supported introductory wording','Bullets restored','This explicitly supported introductory wording works without matching the original sentence word for word.',base+tail,True),
]
for slug,title,status,explanation,content,expected in cases:
 before=prefix+content
 if slug=='05-intro-variant': before=before.replace('These types of *domestic organizations may apply:','The following domestic organizations are eligible to apply.')
 soup=BeautifulSoup('<body>'+before+'</body>','html.parser');original=str(soup);repair_eligibility_organization_lists(soup);changed=str(soup)!=original
 assert changed==expected,(slug,changed)
 after=soup.body.decode_contents(); saved=str(soup);repair_eligibility_organization_lists(soup);assert str(soup)==saved
 page='''<!doctype html><html><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0;padding:38px;background:#edf1f5;color:#182c3b;font:17px/1.5 Arial,sans-serif}.eyebrow{font-size:13px;letter-spacing:1px;color:#516575;font-weight:bold}h1{font-size:29px;margin:8px 0}.description{max-width:1150px;margin:8px 0 24px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}.panel{background:white;border:1px solid #ccd5dd;border-radius:10px;overflow:hidden}.bar{background:#e1e8ef;padding:14px 22px;font-weight:bold}.after{background:STATUSCOLOR}.document{padding:20px 28px}h2{font-size:24px;margin:0 0 14px}h3{font-size:20px;margin:0 0 16px}p{margin:0 0 15px}ul{padding-left:26px;margin:0 0 15px}li{padding-left:3px;margin:0 0 7px}.foot{font-size:13px;color:#516575;margin-top:20px}
</style><div class="eyebrow">PR #1193 · SYNTHETIC REVIEW SCENARIO</div><h1>TITLE</h1><p class="description">EXPLANATION</p><div class="grid"><section class="panel"><div class="bar">Before · paragraphs received by the repair</div><div class="document">BEFORE</div></section><section class="panel"><div class="bar after">After · STATUS</div><div class="document">AFTER</div></section></div><p class="foot">Actual eligibility repair from commit a681fed · Browser-rendered HTML comparison, not a NOFO Builder editor screenshot or an original Announcement Module export. Both panels use identical styling.</p></html>'''
 for key,value in {'STATUSCOLOR':'#d6eee0' if expected else '#f9e8c8','TITLE':html.escape(title),'EXPLANATION':html.escape(explanation),'STATUS':status,'BEFORE':before,'AFTER':after}.items():page=page.replace(key,value)
 (out/(slug+'.html')).write_text(page)
 print(slug+': '+status+'; idempotence verified')
