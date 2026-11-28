"""Render the synthetic component-sampler NOFO as components.html in both themes.

Usage: python build_components.py uswds <out_dir>
       python build_components.py sgg <out_dir> <uswds_dist> <sgg_logo.svg>

The sampler (data/component-sampler.json) exercises the content components a web
NOFO needs: the generated introduction, several deadlines, subagencies, note
callouts, table captions and merged cells, lettered and roman lists, points
labels, the appendix and modifications.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_nofo_web as base  # noqa: E402

SAMPLER = HERE / "data" / "component-sampler.json"
SGG_NOTE = (
    "Opportunity data from the Simpler.Grants.gov API via CommonGrants; "
    "NOFO text from the NOFO Builder test fixture."
)


def main():
    theme, out = sys.argv[1], Path(sys.argv[2])
    nofo = json.loads(SAMPLER.read_text())
    if theme == "uswds":
        # Reuse the full build, then keep only the single-page view.
        with tempfile.TemporaryDirectory() as tmp:
            base.build(nofo, Path(tmp))
            shutil.copy(Path(tmp) / "one-page.html", out / "components.html")
        return
    import build_sgg as sgg

    dist, logo = Path(sys.argv[3]), Path(sys.argv[4])
    parts = sgg.chrome(dist, logo)
    body = sgg.nofo_page(nofo, nofo["opportunity"], parts, False, listing_href=None)
    page = sgg.shell(
        f"NOFO components (sample) | {nofo['number']}", body, sgg.CHROME_JS
    )
    page = page.replace(SGG_NOTE, nofo["mock_note"])
    page = sgg.inline_sprite(page, (dist / "img/sprite.svg").read_text())
    page = page.replace(
        "/*CSS*/", "/*SGG-CSS*/" + base.LOCAL_CSS.strip() + sgg.SGG_VARS
    )
    (out / "components.html").write_text(page)


if __name__ == "__main__":
    main()
