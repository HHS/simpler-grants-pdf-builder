# Experimental local Word export

Pandoc is the proposed basic editable Word converter under #880. This draft implementation is disabled by default with `PANDOC_WORD_EXPORT_ENABLED` in Constance. Do not enable it for production until the remaining review gates below are complete. When disabled, existing GrabzIt behavior is unchanged. There is no automatic vendor fallback when local conversion fails.

The local path renders the existing authorized export GET view, extracts its document target, and converts locally using pinned Pandoc 3.11, a reference document, and a Lua page-break adapter. Clearance uses its existing feature flag and export-time evaluation. No authenticated URL, session cookie, or document is sent to a conversion vendor by this path.

Two conversions may run per container. Additional requests receive HTTP 503 and Retry-After. This is admission control, not a queue; multiple replicas each have their own limit. Conversion subprocesses have a 45-second deadline and are killed/reaped on timeout. Temporary directories are removed on success and handled failures. Documents have a 10 MiB HTML limit and 20 MiB DOCX limit. Errors never silently return empty files or fall back to GrabzIt.

The Docker build verifies pinned Linux amd64/arm64 archive hashes. Local developers can provide `PANDOC_BINARY` through Django settings. Basic semantic formatting is intentional; this is not designed-PDF fidelity. The reference file derives from Pandoc's default reference document with the evaluated typography adjustments.

## Draft review gates

- Support and verify stored/remote image sources safely. Currently only embedded PNG/JPEG/GIF images are accepted; other images fail clearly. This is a rollout blocker, not a silent fidelity compromise.
- Browser verification of busy/error messages, preview/export actions, and normal/Composer/Writer/clearance fixtures against this actual implementation.
- Expand regression tests for timeout process cleanup, DOCX style/break normalization, feature-flag routing, and access restrictions.
- Repeat full-length and Word edit/save tests against this implementation, including tables, lists, links, and image fidelity.
- Review packaged Pandoc licensing, deployment architecture, and resource controls; retain an operational rollback plan. Disabling the flag restores the prior provider configuration, with its pre-existing operational constraints.

No provider cutover, account retirement, or production readiness is implied by this draft.
