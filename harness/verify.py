"""Verify every solver against the published checkers, and score it.

    python harness/verify.py [--slugs ...] [--tier tiny|large|all] [--time-limit 60]

For each (problem, instance) pair it

  1. runs the solver through `harness/run_one.py` (same CLI and wall clock as the
     sandbox: it is killed at the time limit),
  2. runs the problem's own `feasibility_check.py`, the file the evaluation runs,
  3. recomputes the score with the formula from the scoring page, against the
     benchmark's Gurobi objective as the reference,
  4. asserts the contract items (AC-01 ... AC-08) and writes `out/results.json`.

Exit code 0 only when every assertion passes.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import run_one  # noqa: E402
import objective as objlib  # noqa: E402

BENCH = os.path.join(ROOT, "benchmark")
OUT = os.path.join(ROOT, "out")


def instance_path(slug: str, name: str) -> str | None:
    tiny = os.path.join(BENCH, "tasks", slug, "instance", f"{name}.json")
    if os.path.exists(tiny):
        return tiny
    large = os.path.join(ROOT, "data", "large", slug, f"{name}.json")
    if os.path.exists(large):
        return large
    return None


def run_checker(slug: str, inst: str, sol: str) -> dict:
    task_dir = os.path.join(BENCH, "tasks", slug)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        res_path = fh.name
    cmd = [
        sys.executable,
        "feasibility_check.py",
        "--instance_path",
        os.path.abspath(inst),
        "--solution_path",
        os.path.abspath(sol),
        "--result_path",
        res_path,
    ]
    proc = subprocess.run(cmd, cwd=task_dir, capture_output=True, text=True, timeout=600)
    try:
        with open(res_path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        payload = {
            "feasible": False,
            "violations": [f"checker exited {proc.returncode}: {proc.stderr[-400:]}"],
            "reported_objective_value": None,
            "computed_objective_value": None,
        }
    finally:
        try:
            os.unlink(res_path)
        except OSError:
            pass
    payload["checker_exit"] = proc.returncode
    return payload


def score_one(reference: float, value: float) -> float:
    """The scoring page's instance score (minimise problems only here)."""
    if reference is None or value is None:
        return 0.0
    if reference == 0:
        return 2.0 if value < 0 else 0.0
    if (reference > 0) == (value > 0):
        ratio = reference / value if reference > 0 else value / reference
    else:
        ratio = 2.0 if value < reference else 0.0
    return max(0.0, min(2.0, ratio))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slugs", nargs="*", default=None)
    ap.add_argument("--tier", choices=["tiny", "large", "all"], default="all")
    ap.add_argument("--time-limit", type=int, default=60)
    ap.add_argument("--solver-root", default=None)
    ap.add_argument("--json-only", action="store_true")
    ap.add_argument("--out", default=None, help="write results here (default out/results.json)")
    args = ap.parse_args()

    import shutil
    import tempfile as _tf
    import build_submission

    # Run from a staged copy: exactly the folder layout the sandbox unpacks, with
    # the shared helpers copied into every problem folder.
    stage_dir = _tf.mkdtemp(prefix="fo-stage-")
    build_submission.stage(stage_dir)
    solver_root = args.solver_root or stage_dir

    manifest = json.load(open(os.path.join(BENCH, "instances.json"), encoding="utf-8"))
    slugs = args.slugs or sorted({m["slug"] for m in manifest})
    checks: list[dict] = []
    rows: list[dict] = []

    def check(cid: str, ok: bool, detail: str) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail})

    for slug in slugs:
        items = [m for m in manifest if m["slug"] == slug]
        if args.tier != "all":
            items = [m for m in items if m["tier"] == args.tier]
        for m in items:
            path = instance_path(slug, m["name"])
            if path is None:
                check(f"AC-00/{slug}/{m['name']}", False, "instance file missing (run scripts/fetch_data.py --large)")
                continue
            run = run_one.run(slug, path, args.time_limit, solver_root)
            row = {
                "slug": slug,
                "instance": m["name"],
                "tier": m["tier"],
                "run_status": run["status"],
                "wall_s": run["wall_s"],
                "reference_objective": m["reference_objective"],
                "objective": None,
                "score": 0.0,
                "feasible": False,
                "violations": [],
            }
            if run["status"] != "ok":
                row["violations"] = [run.get("stderr_tail", "")[-300:] or run["status"]]
                rows.append(row)
                check(f"AC-01/{slug}/{m['name']}", False, f"run {run['status']} after {run['wall_s']}s")
                continue
            check(f"AC-01/{slug}/{m['name']}", True, f"exit 0 in {run['wall_s']}s (limit {args.time_limit}s)")
            check(
                f"AC-02/{slug}/{m['name']}",
                run["wall_s"] < args.time_limit,
                f"finished inside the limit ({run['wall_s']}s < {args.time_limit}s)",
            )

            res = run_checker(slug, path, run["solution_path"])
            row["feasible"] = bool(res.get("feasible"))
            row["violations"] = list(res.get("violations") or [])[:6]
            # Independent recomputation: the score never quotes the solver's own number.
            solution_doc = json.load(open(run["solution_path"], encoding="utf-8"))
            inst_doc = json.load(open(path, encoding="utf-8"))
            try:
                recomputed = float(objlib.RECOMPUTE[slug](inst_doc, solution_doc))
            except Exception as exc:  # malformed solution: keep the checker's verdict
                recomputed = None
                row["violations"].append(f"recompute failed: {exc}")
            row["computed_objective"] = recomputed
            row["reported_objective"] = solution_doc.get("objective_value")
            row["objective"] = recomputed
            check(
                f"AC-03/{slug}/{m['name']}",
                row["feasible"],
                "checker: feasible" if row["feasible"] else "checker rejected: " + "; ".join(row["violations"][:3]),
            )
            if row["feasible"]:
                rep, comp = row["reported_objective"], row["computed_objective"]
                tol = 1e-6 * max(1.0, abs(comp or 0.0))
                same = rep is not None and comp is not None and abs(float(rep) - comp) <= tol
                check(
                    f"AC-04/{slug}/{m['name']}",
                    same,
                    f"reported {rep} vs independently recomputed {comp}",
                )
                row["score"] = round(score_one(m["reference_objective"], comp), 4)
            rows.append(row)
            print(
                f"  {slug:14s} {m['name']:22s} {run['status']:8s} {run['wall_s']:6.2f}s "
                f"feasible={row['feasible']!s:5s} obj={row['objective']} score={row['score']}",
                flush=True,
            )

    # AC-05: every problem has an algorithm folder with a solve.py that runs.
    for slug in slugs:
        ok = os.path.exists(os.path.join(solver_root, slug, "solve.py"))
        check(f"AC-05/{slug}", ok, "staged <slug>/solve.py present" if ok else "missing solve.py")

    # AC-06: no solver reaches the network (the sandbox has none).
    import re

    forbidden = re.compile(
        r"^\s*(?:import|from)\s+(requests|urllib\.request|urllib|http\.client|socket|httpx)",
        re.MULTILINE,
    )
    for slug in slugs:
        folder = os.path.join(ROOT, "solvers", slug)
        hits = []
        for name in os.listdir(folder) if os.path.isdir(folder) else []:
            if not name.endswith(".py"):
                continue
            text = open(os.path.join(folder, name), encoding="utf-8").read()
            for m in forbidden.finditer(text):
                hits.append(f"{name}:{m.group(1)}")
        check(f"AC-06/{slug}", not hits, "no network imports" if not hits else "found " + ", ".join(hits))

    # AC-07: archive fits the 4 MB submission limit.
    size = build_submission.archive_size()
    shutil.rmtree(stage_dir, ignore_errors=True)
    check("AC-07/archive", size <= 4 * 1024 * 1024, f"submission archive {size/1024:.0f} KiB <= 4096 KiB")

    # AC-08: results are reproducible from the files in the repo.
    check(
        "AC-08/manifest",
        os.path.exists(os.path.join(BENCH, "instances.json")),
        "benchmark/instances.json lists every instance with a sha256 and a reference objective",
    )

    os.makedirs(OUT, exist_ok=True)
    out_path = args.out or os.path.join(OUT, "results.json")
    summary = {}
    for row in rows:
        summary.setdefault(row["slug"], []).append(row)
    per_problem = {}
    for slug, items in summary.items():
        feasible = [r for r in items if r["feasible"]]
        per_problem[slug] = {
            "instances": len(items),
            "feasible": len(feasible),
            "mean_score": round(sum(r["score"] for r in items) / len(items), 4) if items else 0.0,
            "max_wall_s": max((r["wall_s"] for r in items), default=0.0),
        }
    payload = {
        "generated_by": "harness/verify.py",
        "slugs": slugs,
        "time_limit_s": args.time_limit,
        "tier": args.tier,
        "problems": per_problem,
        "mean_score": round(sum(v["mean_score"] for v in per_problem.values()) / max(1, len(per_problem)), 4),
        "rows": rows,
        "checks": checks,
        "failed": [c for c in checks if not c["ok"]],
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)

    failed = payload["failed"]
    if not args.json_only:
        print("\n== per problem ==")
        for slug, s in per_problem.items():
            print(f"  {slug:14s} feasible {s['feasible']}/{s['instances']}  mean score {s['mean_score']:.3f}  max {s['max_wall_s']:.1f}s")
        print(f"\n  overall mean score: {payload['mean_score']:.4f}")
        print(f"  assertions: {len(checks) - len(failed)}/{len(checks)} passed")
        for c in failed:
            print(f"  FAIL {c['id']}: {c['detail'][:300]}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
