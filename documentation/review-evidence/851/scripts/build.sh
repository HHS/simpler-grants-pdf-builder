#!/usr/bin/env bash
# Rebuild the #851 prototypes in ../prototypes from the NOFO Builder test fixture.
#
# Requirements: Python with `markdown` and `beautifulsoup4` (both already in the
# Builder's Poetry environment), Node 18+, and a checkout of HHS/simpler-grants-gov
# (only frontend/src/styles/ and frontend/public/img/grants-logo.svg are read).
#
#   SGG_REPO=/path/to/simpler-grants-gov ./build.sh
#
# One-off spike tooling: it is not used by the Builder application.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../../.." && pwd)"
OUT="$HERE/../prototypes"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
: "${SGG_REPO:?Set SGG_REPO to a checkout of HHS/simpler-grants-gov}"
PYTHON="${PYTHON:-python3}"
NOFO_JSON="$REPO_ROOT/nofos/nofos/fixtures/json/cms-u2u-25-001.json"

cd "$HERE"
npm install --no-audit --no-fund --no-package-lock --silent
USWDS="$HERE/node_modules/@uswds/uswds"

# 1. Plain USWDS prototypes: one page per step, and the whole NOFO on one page.
"$PYTHON" build_nofo_web.py "$NOFO_JSON" "$USWDS/dist" "$WORK/uswds"
"$PYTHON" build_edge_cases.py uswds "$WORK/uswds"
"$PYTHON" build_components.py uswds "$WORK/uswds"
node inline_assets.mjs "$WORK/uswds" "$USWDS/dist/img"
rm -rf "$WORK/uswds/css" "$WORK/uswds/img"

# 2. Simpler.Grants.gov theme compiled from that site's own USWDS settings.
mkdir -p "$WORK/sgg-scss"
cp "$SGG_REPO"/frontend/src/styles/*.scss "$WORK/sgg-scss/"
sed -i.bak 's#"/uswds/fonts"#"../fonts"#; s#"/uswds/img"#"../img"#' "$WORK/sgg-scss/_uswds-theme.scss"
npx sass --no-source-map --style=compressed --quiet-deps \
  --load-path="$USWDS/packages" "$WORK/sgg-scss/styles.scss" "$WORK/sgg.css"

"$PYTHON" build_sgg.py "$NOFO_JSON" data/opportunity-ffeeff3a.json "$USWDS/dist" \
  "$SGG_REPO/frontend/public/img/grants-logo.svg" "$WORK/sgg.css" "$WORK/simpler-grants"
"$PYTHON" build_edge_cases.py sgg "$WORK/simpler-grants" "$USWDS/dist" \
  "$SGG_REPO/frontend/public/img/grants-logo.svg"
"$PYTHON" build_components.py sgg "$WORK/simpler-grants" "$USWDS/dist" \
  "$SGG_REPO/frontend/public/img/grants-logo.svg"
node purge_sgg.mjs "$WORK/simpler-grants" "$USWDS/dist/img"

# 3. Replace the committed output; strip trailing whitespace for pre-commit.
rm -rf "$OUT/uswds" "$OUT/simpler-grants"
mkdir -p "$OUT"
cp -r "$WORK/uswds" "$WORK/simpler-grants" "$OUT/"
find "$OUT" -name '*.html' -exec sed -i.bak -e 's/[[:space:]]*$//' {} \; -exec rm -f {}.bak \;
echo "Prototypes written to $OUT"
