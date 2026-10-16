#!/usr/bin/env python3
"""Bounded, read-only basic latency/load smoke for a local owned Frappe instance.

This is *not* an optimization certificate. For realistic capacity testing use k6
or Locust and representative authenticated business tasks, plus host metrics.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib import error, request


def one(url: str, timeout: float) -> tuple[bool, float, int]:
    start = time.perf_counter()
    try:
        with request.urlopen(request.Request(url, headers={"Accept": "application/json"}),
                             timeout=timeout) as resp:
            body = json.load(resp)
            valid = resp.status == 200 and "message" in body
            status = resp.status
    except error.HTTPError as exc:
        valid, status = False, exc.code
    except (error.URLError, TimeoutError, ValueError, OSError):
        valid, status = False, 0
    return valid, (time.perf_counter() - start) * 1000, status


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    data = sorted(values)
    rank = (len(data) - 1) * (p / 100)
    lo, hi = math.floor(rank), math.ceil(rank)
    return data[lo] + (data[hi] - data[lo]) * (rank - lo)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("PP_BASE_URL", "http://demo.localhost:8000"))
    parser.add_argument("--requests", type=int, default=60)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--max-p95-ms", type=float, default=None, help="Optional environment-specific threshold")
    args = parser.parse_args()
    if not (1 <= args.requests <= 200 and 1 <= args.concurrency <= 20 and args.concurrency <= args.requests):
        parser.error("1<=requests<=200, 1<=concurrency<=20, concurrency<=requests")
    url = args.base_url.rstrip("/") + "/api/method/ping"
    for _ in range(3):
        if not one(url, args.timeout)[0]:
            print("ERROR: warm-up ping failed; test aborted", file=sys.stderr)
            return 1
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(as_completed(pool.submit(one, url, args.timeout) for _ in range(args.requests)))
        samples = [future.result() for future in results]
    elapsed = time.perf_counter() - start
    success = [s[1] for s in samples if s[0]]
    failures = len(samples) - len(success)
    summary = {
        "target": url, "requests": args.requests, "concurrency": args.concurrency,
        "success": len(success), "errors": failures, "error_rate": round(failures / len(samples), 4),
        "elapsed_seconds": round(elapsed, 2), "rps": round(len(samples) / elapsed, 2),
        "median_ms": round(statistics.median(success), 2) if success else None,
        "p95_ms": round(percentile(success, 95), 2) if success else None,
        "p99_ms": round(percentile(success, 99), 2) if success else None,
        "http_statuses": dict(sorted((str(s), sum(row[2] == s for row in samples)) for s in {x[2] for x in samples})),
    }
    print(json.dumps(summary, indent=2))
    ok = failures == 0 and (args.max_p95_ms is None or (success and percentile(success, 95) <= args.max_p95_ms))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
