"""Run one solver the way the Main-track sandbox runs it.

    python harness/run_one.py --slug barnhart2000 --instance <path> [--time-limit 60]

Copies the solver folder to a scratch directory (the sandbox copies it into a
fresh read-only `/work/algorithm`), then starts

    python solve.py --problem <slug> --instance <in> --output <out> --time-limit N

The wall clock is measured here, not by the solver: an algorithm still running at
its limit scores 0, so this runner kills it and reports `timeout`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(
    slug: str,
    instance: str,
    time_limit: int = 60,
    solver_root: str = None,
    keep: bool = False,
) -> dict:
    solver_root = solver_root or os.path.join(ROOT, "solvers")
    src = os.path.join(solver_root, slug)
    if not os.path.isdir(src):
        return {"status": "no_algorithm", "message": f"no solver folder for {slug}"}

    work = tempfile.mkdtemp(prefix=f"fo-{slug}-")
    algorithm = os.path.join(work, "algorithm")
    out_dir = os.path.join(work, "out")
    os.makedirs(out_dir, exist_ok=True)
    shutil.copytree(src, algorithm)

    out_path = os.path.join(out_dir, "solution.json")
    cmd = [
        sys.executable,
        "solve.py",
        "--problem",
        slug,
        "--instance",
        os.path.abspath(instance),
        "--output",
        out_path,
        "--time-limit",
        str(time_limit),
    ]
    started = time.monotonic()
    timed_out = False
    try:
        proc = subprocess.run(
            cmd,
            cwd=algorithm,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=time_limit,
        )
        code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        code = None
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
    wall = time.monotonic() - started

    result = {
        "status": "ok",
        "wall_s": round(wall, 3),
        "limit_s": time_limit,
        "exit_code": code,
        "stdout_tail": stdout[-800:],
        "stderr_tail": stderr[-800:],
        "solution_path": out_path if os.path.exists(out_path) else None,
    }
    if timed_out:
        result["status"] = "timeout"
    elif code != 0:
        result["status"] = "crashed"
    elif not os.path.exists(out_path):
        result["status"] = "no_solution"

    if not keep:
        result["workdir"] = None
    else:
        result["workdir"] = work
    if result["solution_path"] is None and not keep:
        shutil.rmtree(work, ignore_errors=True)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--instance", required=True)
    ap.add_argument("--time-limit", type=int, default=60)
    ap.add_argument("--solver-root", default=None)
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    out = run(args.slug, args.instance, args.time_limit, args.solver_root, args.keep)
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0 if out["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
