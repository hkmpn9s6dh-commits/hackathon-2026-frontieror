"""Structural checks on the generated page.

    python scripts/check_site.py

The page must be openable offline and must not invent numbers: every table row
comes from `out/results.json`, nothing is fetched, and the failure rows are marked
in the row itself rather than only by text colour.
"""

from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "site", "index.html")
RESULTS = os.path.join(ROOT, "out", "results.json")


def main() -> int:
    html = open(PAGE, encoding="utf-8").read()
    data = json.load(open(RESULTS, encoding="utf-8"))
    rows = data["rows"]
    problems = data["problems"]
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    check("page exists", os.path.exists(PAGE))
    # No external requests: the page has to open from a file:// path.
    external = re.findall(r'(?:src|href)="(https?:)?//[^"]+', html)
    check("no external assets", not external, ", ".join(external[:3]))
    check("no fetch/xhr", not re.search(r"\bfetch\(|XMLHttpRequest", html))

    # One row per instance, in the same order as results.json.
    body = html.split("<tbody>")[1].split("</tbody>")[0]
    group_rows = len(re.findall(r'<tr class="group">', body))
    page_rows = body.count("<tr") - group_rows
    check("one table row per instance", page_rows == len(rows), f"{page_rows} vs {len(rows)}")

    # Failure rows are marked on the row, not by colour alone.
    bad_in_data = sum(1 for r in rows if not r["feasible"])
    bad_in_page = len(re.findall(r'<tr class="bad">', body))
    check("failed rows marked", bad_in_page == bad_in_data, f"{bad_in_page} vs {bad_in_data}")

    # Scores printed with three decimals, matching results.json.
    for r in rows[:8]:
        needle = f'{r["score"]:.3f}'
        if needle not in html:
            check(f"score printed {r['slug']}/{r['instance']}", False, needle)
            break

    # Every problem appears with its mean score.
    for slug, p in problems.items():
        if f'{p["mean_score"]:.3f}' not in html:
            check(f"mean score {slug}", False, f'{p["mean_score"]:.3f}')
            break

    # The 60 s ruler exists and its red line is not decorative.
    check("ruler present", "60 s" in html and "aria-label" in html)
    check("no scroll container", "overflow-y: auto" not in html)

    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        print(f"{'ok  ' if ok else 'FAIL'} {name}{(' — ' + detail) if detail and not ok else ''}")
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
