#!/usr/bin/env python3
"""Bulk-delete research noise from OpenViking.

The "daily-explore" cron created 50+ topic dirs (whale communication, dark
matter, lichen, etc) — none of them are needed by sam-os, the gym, or nutrition
tracking. This script wipes them all.

Idempotent — skips anything that's already gone.

Usage:
  /home/server/sam-os/.venv/bin/python /home/server/sam-os/scripts/purge_viking_noise.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Root credentials (read-only use here, just for the user list)
ROOT_KEY = "91ac3c26678993cdd9f0f6bfc8873d30c7e2949b83ba3b3501639ff5fec4c687"
USER_KEY = "aGVybWVz.bWU.YjMyNzVlYTU2MzFmNjM3YmZlMGM1YjViYTUzNWNhMTI3OWUxN2RiZjQ3YTYyNzczYjM2YWQyYWI0OWE1MGU0OA"
BASE = "http://localhost:1933"
ACCOUNT = "hermes"
USER = "me"

# Topics to KEEP (none of these are research noise)
PROTECTED = {"sam-os"}

# Users to KEEP their resources
PROTECTED_USERS = {"me"}


def list_users() -> list[str]:
    r = subprocess.run(
        ["curl", "-s", f"{BASE}/api/v1/admin/accounts/{ACCOUNT}/users?limit=200",
         "-H", f"X-API-Key: {ROOT_KEY}"],
        capture_output=True, text=True, timeout=15,
    )
    return [u["user_id"] for u in json.loads(r.stdout)["result"]]


def list_resources(scope: str) -> list[str]:
    """List top-level dirs under viking://<scope>/ for user `me`."""
    r = subprocess.run(
        ["curl", "-s", f"{BASE}/api/v1/fs/ls?uri=viking://{scope}/",
         "-H", f"X-API-Key: {USER_KEY}",
         "-H", f"X-OpenViking-Account: {ACCOUNT}",
         "-H", f"X-OpenViking-User: {USER}"],
        capture_output=True, text=True, timeout=30,
    )
    try:
        data = json.loads(r.stdout)
    except Exception:
        return []
    items = data.get("result") or []
    if not isinstance(items, list):
        return []
    return [i["uri"] for i in items if i.get("isDir")]


def delete_resource(uri: str) -> tuple[str, bool, str]:
    r = subprocess.run(
        ["curl", "-s", "-X", "DELETE",
         f"{BASE}/api/v1/fs?uri={uri}&recursive=true",
         "-H", f"X-API-Key: {USER_KEY}",
         "-H", f"X-OpenViking-Account: {ACCOUNT}",
         "-H", f"X-OpenViking-User: {USER}"],
        capture_output=True, text=True, timeout=60,
    )
    try:
        data = json.loads(r.stdout)
        ok = data.get("status") == "ok"
        return uri, ok, data.get("error", {}).get("message", "") if not ok else f"deleted {data['result'].get('estimated_deleted_count', '?')} files"
    except Exception as e:
        return uri, False, f"parse error: {e}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    all_uris: list[str] = []
    for scope in ("resources", "user"):
        uris = list_resources(scope)
        print(f"=== {scope}: {len(uris)} entries ===")
        all_uris.extend(uris)

    to_kill = [u for u in all_uris if not any(u.endswith(p) for p in PROTECTED)]
    print(f"  total: {len(all_uris)}, keep: {len(all_uris) - len(to_kill)}, kill: {len(to_kill)}")

    if args.dry_run:
        for u in to_kill:
            print(f"  [dry-run] would delete {u}")
        return 0

    deleted = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(delete_resource, u): u for u in to_kill}
        for fut in as_completed(futures):
            uri, ok, msg = fut.result()
            if ok:
                deleted += 1
                print(f"  ✓ {uri} — {msg}")
            else:
                failed += 1
                print(f"  ✗ {uri} — {msg}")

    print(f"\n=== done: {deleted} deleted, {failed} failed ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())