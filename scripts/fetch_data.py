"""Fetch the large instances the repository does not carry.

    python scripts/fetch_data.py            # all six problems
    python scripts/fetch_data.py --slug hoffman1993

The small fixtures (tiny instance, schema, checker, reference objective) are
committed, so `harness/verify.py --tier tiny` works offline. The large instances
are 39 MB in total, get their own folder and are verified against the sha256 in
`benchmark/large_instances.json`.

Source: `frontieror/FrontierOR` on Hugging Face, CC BY 4.0. `huggingface.co` is
not reachable from every network here, so the mirror `hf-mirror.com` is tried
first and the canonical host second.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "benchmark", "large_instances.json")
DEST = os.path.join(ROOT, "data", "large")
HOSTS = [
    "https://hf-mirror.com/datasets/frontieror/FrontierOR/resolve/main/",
    "https://huggingface.co/datasets/frontieror/FrontierOR/resolve/main/",
]


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(rel_path: str, target: str, expected: int) -> bool:
    for host in HOSTS:
        url = host + urllib.parse.quote(rel_path)
        try:
            with urllib.request.urlopen(url, timeout=120) as resp, open(target, "wb") as fh:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    fh.write(chunk)
        except Exception as exc:  # try the next host
            print(f"  {host.split('/')[2]}: {exc}", file=sys.stderr)
            continue
        if os.path.getsize(target) == expected:
            return True
        print(f"  size mismatch from {host.split('/')[2]}", file=sys.stderr)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", action="append", help="limit to one problem (repeatable)")
    args = ap.parse_args()

    items = json.load(open(MANIFEST, encoding="utf-8"))
    if args.slug:
        items = [i for i in items if i["slug"] in set(args.slug)]

    kept, failed = 0, 0
    for item in items:
        target = os.path.join(DEST, item["slug"], item["name"] + ".json")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if os.path.exists(target) and sha256_of(target) == item["sha256"]:
            kept += 1
            continue
        print(f"fetching {item['slug']}/{item['name']} ({item['size']/1024:.0f} KiB)", flush=True)
        if not fetch(item["path"], target, item["size"]):
            failed += 1
            continue
        digest = sha256_of(target)
        if digest != item["sha256"]:
            print(f"  sha256 mismatch: {digest[:12]} != {item['sha256'][:12]}", file=sys.stderr)
            os.unlink(target)
            failed += 1
            continue
        kept += 1
    print(f"{kept}/{len(items)} instances present and verified, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
