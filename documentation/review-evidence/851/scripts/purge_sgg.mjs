import {PurgeCSS} from 'purgecss';
import fs from 'fs'; import path from 'path';
const [out,img]=process.argv.slice(2);
const pages=fs.readdirSync(out).filter(f=>f.endsWith('.html'));
const res=await new PurgeCSS().purge({content:pages.map(p=>path.join(out,p)),css:[path.join(out,'_sgg_full.css')],
  extractors:[{extractor:c=>c.match(/[A-Za-z0-9_:-]+/g)||[],extensions:['html']}],safelist:{standard:['is-visible','usa-js-mobile-nav--active','usa-current','is-copied','html','body'],greedy:[/aria-expanded/]}, variables:false, keyframes:true, fontFace:false});
let css=res[0].css;
css=css.replace(/url\((["']?)\.\.\/img\/([^"')]+)\1\)/g,(m,q,f)=>{const p=path.join(img,f);if(!fs.existsSync(p))return 'none';const mime=f.endsWith('.svg')?'image/svg+xml':'image/png';return `url("data:${mime};base64,${fs.readFileSync(p).toString('base64')}")`});
for(const p of pages){const f=path.join(out,p);fs.writeFileSync(f,fs.readFileSync(f,'utf8').replace('/*SGG-CSS*/',()=>css));}
fs.unlinkSync(path.join(out,'_sgg_full.css'));
console.log('purged css bytes',css.length);
