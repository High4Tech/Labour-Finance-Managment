#!/usr/bin/env python3
"""Frappe API smoke test. Safe by default; --crud writes/cleans one ToDo using test token."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from urllib import error, parse, request


def http(base: str, path: str, *, method: str = "GET", token: str | None = None,
         body: dict | None = None, timeout: int = 15) -> tuple[int, dict, float]:
    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"token {token}"
    payload = None
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(base.rstrip("/") + path, method=method, data=payload, headers=headers)
    start = time.perf_counter()
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = resp.status
    except error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    try:
        result = json.loads(raw.decode("utf-8")) if raw else {}
    except (ValueError, UnicodeDecodeError):
        result = {"raw_prefix": raw[:250].decode("utf-8", errors="replace")}
    return status, result, (time.perf_counter() - start) * 1000


def require(condition: bool, title: str, details: str = "") -> None:
    print(f"{'PASS' if condition else 'FAIL'} {title}" + (f" ({details})" if details else ""))
    if not condition:
        raise RuntimeError(f"Failed: {title}. {details}")


def run(base: str, key: str | None, secret: str | None, crud: bool) -> None:
    status, result, ms = http(base, "/api/method/ping")
    require(status == 200 and "message" in result, "Public framework ping", f"HTTP {status}, {ms:.1f} ms")

    # Confirm a forged token does not authenticate (401 or 403; never 200).
    status, _, ms = http(base, "/api/resource/ToDo?limit_page_length=1",
                         token="pluspoint-invalid-api-key:pluspoint-invalid-secret")
    require(status in {401, 403}, "Invalid token is rejected", f"HTTP {status}, {ms:.1f} ms")

    if not (key and secret):
        if crud:
            raise RuntimeError("--crud needs PP_API_KEY and PP_API_SECRET environment variables")
        print("SKIP authenticated API and CRUD (set PP_API_KEY and PP_API_SECRET)")
        return

    token = key + ":" + secret
    status, _, ms = http(base, "/api/resource/ToDo?limit_page_length=1", token=token)
    require(status == 200, "Authenticated ToDo listing", f"HTTP {status}, {ms:.1f} ms")
    status, _, ms = http(base, "/api/resource/Company?limit_page_length=1", token=token)
    require(status == 200, "ERPNext Company endpoint", f"HTTP {status}, {ms:.1f} ms")
    if not crud:
        print("SKIP CRUD (add --crud to run create/read/update/delete on one temporary ToDo)")
        return

    name = None
    description = "PLUS POINT API SMOKE " + uuid.uuid4().hex
    try:
        status, data, ms = http(base, "/api/resource/ToDo", method="POST", token=token,
                                body={"description": description, "status": "Open"})
        name = data.get("data", {}).get("name")
        require(status in {200, 201} and bool(name), "Create temporary ToDo", f"HTTP {status}, {ms:.1f} ms")
        path = "/api/resource/ToDo/" + parse.quote(str(name), safe="")
        status, data, ms = http(base, path, token=token)
        require(status == 200 and data.get("data", {}).get("description") == description,
                "Read persisted ToDo", f"HTTP {status}, {ms:.1f} ms")
        status, _, ms = http(base, path, method="PUT", token=token,
                             body={"description": description + " updated"})
        require(status == 200, "Update ToDo", f"HTTP {status}, {ms:.1f} ms")
        status, data, ms = http(base, path, token=token)
        require(status == 200 and data.get("data", {}).get("description") == description + " updated",
                "Verify updated persisted data", f"HTTP {status}, {ms:.1f} ms")
        status, _, ms = http(base, path, method="DELETE", token=token)
        require(status in {200, 202, 204}, "Delete temporary ToDo", f"HTTP {status}, {ms:.1f} ms")
        name = None
        print("ALL FRAMEWORK API SMOKES PASSED; temporary test data cleaned")
    finally:
        if name is not None:
            path = "/api/resource/ToDo/" + parse.quote(str(name), safe="")
            status, _, _ = http(base, path, method="DELETE", token=token)
            if status not in {200, 202, 204, 404}:
                print("WARNING: temporary ToDo cleanup failed; remove it manually", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("PP_BASE_URL", "http://demo.localhost:8000"))
    parser.add_argument("--crud", action="store_true", help="Create/update/delete a temporary ToDo using a test API token")
    args = parser.parse_args()
    try:
        run(args.base_url, os.environ.get("PP_API_KEY"), os.environ.get("PP_API_SECRET"), args.crud)
    except (RuntimeError, error.URLError, TimeoutError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
