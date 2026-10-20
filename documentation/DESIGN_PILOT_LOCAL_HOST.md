# Connected local design host

This is a synthetic, human-operated integration slice under [#1147](https://github.com/HHS/simpler-grants-pdf-builder/issues/1147), built on the
[presentation-operation rules](DESIGN_CANDIDATE_OPERATIONS.md). It reuses Builder's
Word import, metadata suggestions, section graph, theme choices and HTML templates.
It does not run a model or expose an agent tool endpoint.

## What it provides

- A manual Word upload, limited to 1 MB, with an invented-information confirmation.
- Original source bytes and SHA-256, a frozen imported-content snapshot, current
  presentation state and per-change reasons in an isolated SQLite database.
- Same-owner and current-group checks, duplicate-source retry protection, and
  transactional compare-and-swap for theme and section table-width changes.
- Optional HTML review links bound to the current candidate, rendered HTML,
  application/template/static bytes, lockfile and boolean feature flags. Old links
  and stale forms fail closed. Changes outside this workflow invalidate the run.
- Disabled PDF controls. **DocRaptor stays disabled in all lower environments.**
  There is no substitute PDF renderer, browser-print workflow or tunnel.

The host reuses the bounded Word-container guard with readability recognition
disabled, then uses Builder's own structural and OpDiv validation. The standalone
readability uploader retains its existing recognition policy. Source documents do
not choose the owning user/group or grant additional operations.

## Run locally with invented documents only

Use a clean checkout without dotenv files and the project's installed development
Python. Create a private scratch directory, then pass that exact absolute path as
`DESIGN_PILOT_ROOT` to every command. For example:

```sh
mktemp -d /tmp/builder-design-pilot-XXXXXX
```

Run each command with a clean environment. Replace the two bracketed paths below:

```sh
env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin \
  DESIGN_PILOT_ROOT=/absolute/private/scratch-directory \
  DJANGO_SETTINGS_MODULE=bloom_nofos.design_pilot_settings \
  /absolute/development/python nofos/manage.py migrate --noinput
```

Create an ordinary test account in that scratch database with Builder's existing
user manager. Do not use production accounts, passwords or browser cookies.
Start the same profile with `nofos/manage.py runserver 127.0.0.1:8917 --noreload
--insecure`, then visit `http://127.0.0.1:8917/design-pilot/` and sign in.
`--insecure` serves repository static assets with DEBUG off; it does not disable
CSRF or authentication. `--noreload` is required because the profile intentionally
rejects inherited database/provider configuration.

The profile requires a user-owned mode-0700 root, rejects a linked database or key
file, generates a private session key, rejects ambient provider/AWS/database
configuration and clears export credentials. The request middleware accepts only
loopback requests to pilot, sign-in/out and static paths. Other Builder routes are
unreachable in this profile. Without this profile, pilot views return 404.
Python socket connection/send calls are denied as defense in depth. **These
checks are not an OS sandbox or proof of containment for arbitrary agent code.**

## Review limitations and remaining work

The preview removes scripts, forms, embedded frames, inline style sheets and
external navigation/resource URLs. Only local static resources, internal anchors
and PNG/JPEG data images are retained; a restrictive CSP also applies. Stored
source/content is not rewritten by this preview filter. This slice uses text
covers only and rejects cover mutations/custom CSS. Do not infer asset or
external-link fidelity from the filtered preview. HTML review does not verify PDF
pagination, and opening it is not an acceptance prerequisite.

No acceptance, promotion, discard, production transfer, model credentials or
candidate-only agent transport is implemented. An ordinary human login is **not**
a candidate-scoped agent credential. Those boundaries must be implemented and
independently reviewed before claiming #1147 complete or running agent/real-data
work. Processing is synchronous, not a cancellable worker. Discard/retention and
full resource/time budgets are follow-up work; stopping the server does not erase
the scratch database, source bytes or local audit records.

The revision fingerprint is a freshness check, not an archived immutable HTML
artifact. Historical renderer reconstruction, readiness/fidelity findings and the
trusted human acceptance interface remain follow-ups under #1148/#1149/#1150.
This PR must not close those issues or be represented as operating approval.
