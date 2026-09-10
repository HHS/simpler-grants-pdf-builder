"""Local-only converter stress probe; run inside a network-disabled container.

Not an HTTP/load test. Exercises actual conversion, timeout and shared slots.
"""

import concurrent.futures
import json
import multiprocessing
import resource
import time

from django.conf import settings

settings.configure(PANDOC_BINARY="pandoc")
from bloom_nofos.word_export import ExportError, conversion_slot, convert_html


def convert(size):
    html = (
        "<html><body><h1>Load fixture</h1>"
        + (
            "<p>Representative editable content with <strong>emphasis</strong>.</p>"
            * (size // 68)
        )
        + "</body></html>"
    )
    started = time.monotonic()
    try:
        data = convert_html(html)
        outcome = {"output_bytes": len(data), "status": "success"}
    except ExportError as exc:
        outcome = {"status": str(exc)}
    return dict(
        outcome,
        input_bytes=len(html.encode()),
        seconds=round(time.monotonic() - started, 2),
        child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
    )


def slot(ready, release):
    with conversion_slot() as admitted:
        ready.put(admitted)
        release.wait(10)


if __name__ == "__main__":
    multiprocessing.set_start_method("fork")  # Linux-only, also supports stdin.
    for size in (100_000, 1_000_000, 9_000_000):
        with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:
            print(
                json.dumps(
                    {
                        "requested_size": size,
                        "parallel": list(pool.map(convert, [size] * 2)),
                    }
                ),
                flush=True,
            )
    ready, release = multiprocessing.Queue(), multiprocessing.Event()
    workers = [
        multiprocessing.Process(target=slot, args=(ready, release)) for _ in range(2)
    ]
    for worker in workers:
        worker.start()
    held = [ready.get(timeout=10) for _ in workers]
    with conversion_slot() as admitted:
        print(json.dumps({"held_slots": held, "third_admitted": admitted}), flush=True)
    release.set()
    for worker in workers:
        worker.join(10)
    with conversion_slot() as admitted:
        print(json.dumps({"slot_reusable": admitted}), flush=True)
