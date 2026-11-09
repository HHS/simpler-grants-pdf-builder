# Readability Checker scratch cleanup: local verification

[Builder #1315](https://github.com/HHS/simpler-grants-pdf-builder/issues/1315) ·
[Current operating guidance](../../readability/PDF_READABILITY_PILOT.md#temporary-processing-limits)

**November 9, 2026.** Local macOS, Python 3.14, SQLite, and the pinned
metrics package 0.7.0. The comparison used Builder `74eed504` and the
implementation branch for #1315. Only a synthetic PDF and disposable processes,
database and temporary storage were used.

The baseline probe forced Django to use a disk-backed upload and paused the real
parser subprocess once the metrics package staged its analysis input. Killing only
the parser returned a safe 503 and left no files. Killing both the request process
and parser left all three copies, including the metrics package's copy. A fresh
application process handled a new upload without removing the older files.

With the fix, the probe repeated the interruption at the same point. Starting the
replacement with the Builder Gunicorn configuration removed all three abandoned
files without a new HTTP request. To exercise the periodic path, the probe then
seeded a synthetic abandoned workspace just after startup. The idle worker
removed it at the next check, observed at 30 seconds.

The checked-in regression tests cover disk upload placement and cleanup on
success and invalid input, active leases, unrelated files, cleanup failure and
retry, and cleanup after a process exits without running its finalizers:

```sh
cd nofos
poetry run python manage.py test \
  nofos.tests_nofos.test_readability_scratch \
  bloom_nofos.tests_bloom_nofos.test_pdf_readability
```

This does not verify the deployed filesystem, Linux/ECS task replacement,
infrastructure logging, or an approved retention limit. Track deployed
verification in [#971](https://github.com/HHS/simpler-grants-pdf-builder/issues/971).
