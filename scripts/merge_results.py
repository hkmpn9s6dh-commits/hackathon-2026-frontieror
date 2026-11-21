"""Merge per-problem verification runs into one `out/results.json`.

    python scripts/merge_results.py

`harness/verify.py --slugs <one> --out out/results-<slug>.json` writes one file per
problem, so a long run can be done in batches without losing the finished ones.
This merges them, re-derives the per-problem summary and the overall mean, and
refuses to merge two files that disagree about an assertion.
"""

from __future__ import annotations

import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
sys.path.insert(0, os.path.join(ROOT, "harness"))

import directions  # noqa: E402


def main() -> int:
    parts = []
    for path in sorted(glob.glob(os.path.join(OUT, "results-*.json"))):
        data = json.load(open(path, encoding="utf-8"))
        parts.append((path, data))
    if not parts:
        print("no out/results-*.json to merge", file=sys.stderr)
        return 1

    seen: dict[str, str] = {}
    rows, checks = [], []
    for path, data in parts:
        for slug in data["slugs"]:
            if slug in seen:
                print(f"duplicate slug {slug} in {path} and {seen[slug]}", file=sys.stderr)
                return 1
            seen[slug] = path
        rows.extend(data["rows"])
        checks.extend(data["checks"])

    # Recompute every score from the objective the checker accepted, using the
    # problem's own direction; never reuse a per-run number.
    for row in rows:
        row["direction"] = directions.DIRECTION[row["slug"]]
        row["score"] = (
            round(directions.score(row["reference_objective"], row["objective"], row["direction"]), 4)
            if row["feasible"]
            else 0.0
        )

    problems = {}
    for row in rows:
        p = problems.setdefault(row["slug"], {"instances": 0, "feasible": 0, "_sum": 0.0, "max_wall_s": 0.0})
        p["instances"] += 1
        p["feasible"] += 1 if row["feasible"] else 0
        p["_sum"] += row["score"]
        p["max_wall_s"] = max(p["max_wall_s"], row["wall_s"])
    for p in problems.values():
        p["mean_score"] = round(p.pop("_sum") / max(1, p["instances"]), 4)
        p["max_wall_s"] = round(p["max_wall_s"], 2)

    # AC-03 (the checker rejected the solution) is a *result*, not a defect: an
    # instance the solver cannot solve scores 0, and that is what the competition
    # measures. Keep it in `recorded` so the report can state it, and keep
    # `failed` for things that mean the harness or a solver is broken.
    failed = [c for c in checks if not c["ok"] and not c["id"].startswith("AC-03/")]
    recorded = [c for c in checks if not c["ok"] and c["id"].startswith("AC-03/")]

    payload = {
        "generated_by": "harness/verify.py (per problem) + scripts/merge_results.py",
        "time_limit_s": 60,
        "tier": "all",
        "slugs": sorted(problems),
        "problems": {k: problems[k] for k in sorted(problems)},
        "mean_score": round(sum(p["mean_score"] for p in problems.values()) / max(1, len(problems)), 4),
        "rows": rows,
        "checks": checks,
        "failed": failed,
        "recorded_infeasible": recorded,
    }
    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)

    print(f"merged {len(parts)} files, {len(rows)} instances, {len(problems)} problems")
    print(f"mean score {payload['mean_score']}, hard failures {len(failed)}, "
          f"infeasible instances recorded {len(recorded)}")
    for slug, p in payload["problems"].items():
        print(f"  {slug:14s} {p['feasible']}/{p['instances']}  mean {p['mean_score']:.4f}  max {p['max_wall_s']:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
