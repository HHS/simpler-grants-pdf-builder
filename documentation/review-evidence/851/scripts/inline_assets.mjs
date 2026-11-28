// Make every HTML page in a folder self-contained: inline its linked stylesheets
// (purged to the selectors the page uses), turn ../img/ CSS references into data URIs,
// and replace img/sprite.svg#icon references with an inline <symbol> sheet.
// Usage: node inline_assets.mjs <folder> <uswds-dist-img-folder>
import { PurgeCSS } from "purgecss";
import fs from "fs";
import path from "path";

const [dir, imgDir] = process.argv.slice(2);
const sprite = fs.readFileSync(path.join(imgDir, "sprite.svg"), "utf8");
const toDataUri = (file) => {
  const p = path.join(imgDir, file);
  if (!fs.existsSync(p)) return "none";
  const mime = file.endsWith(".svg") ? "image/svg+xml" : "image/png";
  return `url("data:${mime};base64,${fs.readFileSync(p).toString("base64")}")`;
};

for (const name of fs.readdirSync(dir).filter((f) => f.endsWith(".html"))) {
  const file = path.join(dir, name);
  let html = fs.readFileSync(file, "utf8");
  const links = [...html.matchAll(/<link rel="stylesheet" href="(css\/[^"]+)">/g)];
  let css = "";
  for (const [, href] of links) css += fs.readFileSync(path.join(dir, href), "utf8") + "\n";
  if (css) {
    const [res] = await new PurgeCSS().purge({
      content: [{ raw: html, extension: "html" }],
      css: [{ raw: css }],
      extractors: [{ extractor: (c) => c.match(/[A-Za-z0-9_:-]+/g) || [], extensions: ["html"] }],
      safelist: { standard: ["is-copied", "usa-current", "html", "body"] },
      keyframes: true,
    });
    const inlined = res.css.replace(/url\((["']?)\.\.\/img\/([^"')]+)\1\)/g, (m, q, f) => toDataUri(f));
    html = html.replace(/<link rel="stylesheet" href="css\/[^"]+">\s*/g, "");
    html = html.replace("</head>", () => `<style>${inlined}</style>\n</head>`);
  }
  const used = [...new Set([...html.matchAll(/href="img\/sprite\.svg#([a-z_0-9]+)"/g)].map((m) => m[1]))];
  if (used.length) {
    const syms = used
      .map((id) => (sprite.match(new RegExp(`<symbol id="${id}"[\\s\\S]*?</symbol>`)) || [""])[0])
      .join("");
    html = html.replace(/href="img\/sprite\.svg#/g, 'href="#');
    html = html.replace(/<body([^>]*)>/, (m) => `${m}\n<svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true">${syms}</svg>`);
  }
  fs.writeFileSync(file, html);
  console.log(name, Math.round(html.length / 1024) + "KB");
}
