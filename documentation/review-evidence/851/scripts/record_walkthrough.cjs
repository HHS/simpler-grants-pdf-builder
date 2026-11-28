const {chromium}=require('playwright');
// Records the listing-to-NOFO walkthrough used for #851.
// Usage: serve ../prototypes (for example: python3 -m http.server 8771 --directory ../prototypes),
// then: node record_walkthrough.cjs http://localhost:8771/simpler-grants/ <out_dir>
// Produces a .webm in out_dir; see the README for the GIF and MP4 conversion commands.
const [,,base,outDir]=process.argv;
if(!base||!outDir){console.error('Usage: node record_walkthrough.cjs <base_url> <out_dir>');process.exit(1);}
// Visible cursor and click ring (video doesn't record the real pointer), plus a caption band.
const overlay=`(()=>{
 const add=()=>{if(document.getElementById('wt-cursor'))return;
  const c=document.createElement('div');c.id='wt-cursor';
  c.innerHTML='<svg width="28" height="28" viewBox="0 0 24 24"><path d="M4 2l14 9-6.5 1.5L15 20l-3 1.5-2.6-7.5L4 19z" fill="#111" stroke="#fff" stroke-width="1.5"/></svg>';
  c.style.cssText='position:fixed;left:-50px;top:-50px;z-index:99999;pointer-events:none;transition:none';
  document.body.appendChild(c);
  const cap=document.createElement('div');cap.id='wt-cap';
  cap.style.cssText='position:fixed;left:0;right:0;bottom:0;z-index:99998;background:rgba(17,24,39,.92);color:#fff;font:600 20px/1.35 system-ui,sans-serif;padding:14px 28px;pointer-events:none;display:none';
  document.body.appendChild(cap);
  document.addEventListener('mousemove',e=>{c.style.left=(e.clientX-4)+'px';c.style.top=(e.clientY-2)+'px';},true);
  document.addEventListener('mousedown',e=>{const r=document.createElement('div');r.style.cssText='position:fixed;z-index:99997;pointer-events:none;width:36px;height:36px;border-radius:50%;border:3px solid #ffbe2e;left:'+(e.clientX-18)+'px;top:'+(e.clientY-18)+'px;transition:transform .5s,opacity .5s';document.body.appendChild(r);requestAnimationFrame(()=>{r.style.transform='scale(1.8)';r.style.opacity='0'});setTimeout(()=>r.remove(),600);},true);
 };
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',add);else add();
})();`;
(async()=>{
 const b=await chromium.launch();
 const ctx=await b.newContext({viewport:{width:1280,height:800},recordVideo:{dir:outDir,size:{width:1280,height:800}},permissions:['clipboard-read','clipboard-write']});
 await ctx.addInitScript(overlay);
 const p=await ctx.newPage();
 const wait=ms=>p.waitForTimeout(ms);
 const cap=async t=>{await p.evaluate(t=>{const c=document.getElementById('wt-cap');if(c){c.textContent=t;c.style.display=t?'block':'none';}},t);};
 let mx=640,my=400;
 const moveTo=async(loc)=>{const bb=await loc.boundingBox();const x=bb.x+Math.min(bb.width/2,60),y=bb.y+bb.height/2;await p.mouse.move(x,y,{steps:25});mx=x;my=y;await wait(250);};
 const scrollBy=async(px,steps=20,delay=45)=>{for(let i=0;i<steps;i++){await p.mouse.wheel(0,px/steps);await wait(delay);}};
 await p.goto(base+'opportunity.html');await wait(400);await p.mouse.move(mx,my);
 await cap('1. The opportunity listing on Simpler.Grants.gov');await wait(2200);
 await scrollBy(900,24);await cap('2. A new NOFO section: read it online, download the PDF, or jump straight to a section');await wait(2600);
 const read=p.locator('.sgg-nofo-card a',{hasText:'Read the NOFO online'});await moveTo(read);await read.click();await p.waitForLoadState('load');await wait(300);
 await p.mouse.move(640,420);await cap('3. The NOFO opens as a page of the site, with a link back to the listing');await wait(2600);
 await cap('4. Scrolling: "On this page" marks where you are and opens only the current step');
 await scrollBy(2600,60,55);await wait(500);await scrollBy(3200,60,55);await wait(1200);
 const nav=p.locator('.usa-in-page-nav__link',{hasText:'Step 4: Learn About Review'});await moveTo(nav);
 await cap('5. Jump from the list: the section is highlighted and receives focus');await nav.click();await wait(2600);
 const anchor=p.locator('#step-4-learn-about-review-and-award').locator('xpath=..').locator('a[data-anchor]');await moveTo(anchor);
 await cap('6. Every heading has a link you can copy and share');await anchor.click();await wait(2400);
 await p.evaluate(()=>window.scrollTo(0,0));await wait(300);
 const crumb=p.locator('.usa-breadcrumb a',{hasText:'Opportunity listing'});await moveTo(crumb);await cap('7. Back to the listing');await crumb.click();await p.waitForLoadState('load');await wait(300);
 await p.evaluate(()=>{document.getElementById('nofo-card-heading').scrollIntoView();window.scrollBy(0,-140)});await p.mouse.move(640,420);
 await cap('8. Links in the listing open the exact NOFO section');await wait(1500);
 const deep=p.locator('.sgg-jump a',{hasText:'Merit review criteria'});await moveTo(deep);await deep.click();await p.waitForLoadState('load');await wait(400);
 await p.mouse.move(700,500,{steps:10});await cap('8. Links in the listing open the exact NOFO section');await wait(3200);
 await ctx.close();await b.close();
})();
