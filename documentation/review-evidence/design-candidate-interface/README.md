# Candidate-only interface verification

October 20, 2026. Synthetic local data only; stacked on the connected-host slice.

## Verified

- Full local Django suite: 2,734 tests, three existing skips, OK. Run from `nofos/`.
- JavaScript suite: 57 passed.
- Independent review: no blocking findings; reviewer independently passed all 41
  transport, SQLite concurrency, connected-host and pure-kernel tests.
- Final focused rerun: all 41 tests passed. Coverage includes cookie-only and
  cross-candidate denial, current ownership, expiry, replacement, revocation,
  quotas, malformed JSON, stale revisions, forbidden operations and rollback.
- Actual concurrent requests use separate SQLite connections. Competing writes
  cannot both succeed against an old revision; requests cannot exceed quota.
  SQLite contention may fail closed and require a sequential retry.
- Fresh migration 0155 applied to the isolated scratch database.
- Chrome: reviewed credential-free access controls and revoked a synthetic grant.
  No plaintext key was displayed, captured or shared. Issuance and authenticated
  operations were tested through Django clients, not a live model or browser key page.
- At the default width and 390-pixel narrow viewport, access controls wrap and
  remain visible. At 390 pixels the document width is also 390 pixels. Computed
  new heading styles match the existing Theme and Cover headings: Merriweather Web,
  21.44 pixels, weight 700. Temporary viewport override was reset.

## Screenshots

These contain invented candidate data and no credentials.

Credential-free access controls before revocation:

![Access controls](access-controls.jpg)

After revocation:

![Access revoked](access-revoked.jpg)

Narrow-screen controls after revocation:

![Narrow access controls](access-narrow.jpg)

## Not established

This is an HTTP authorization boundary, not an OS sandbox or a wired agent
runtime. No real documents, provider calls, DocRaptor, PDF review, acceptance,
transfer, publication or discard were exercised. No shared or production use is
approved by this evidence. Other database engines and reverse proxies were not
tested. The one-time key page is covered by response/security tests, not screenshots.
