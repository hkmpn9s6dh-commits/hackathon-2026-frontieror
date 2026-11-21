"""Shared helpers for FrontierOR solvers.

Every solver folder in `solvers/` (and in the packed submission) carries a copy of
this file, because the Main-track sandbox copies each problem folder on its own.
Keep it dependency-free (stdlib only): the sandbox image also ships numpy and
ortools, but a solver that only needs the stdlib is faster to start and easier to
check.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time


# --------------------------------------------------------------------------- io


def parse_cli(problem: str) -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", default=problem)
    ap.add_argument("--instance", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--time-limit", type=int, default=60)
    return ap.parse_args()


def load_instance(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_solution(path: str, payload: dict, objective: float) -> None:
    """Write the solution file the way the evaluation expects it.

    `objective_value` is always taken from the same number the payload was built
    from, so a solution can never claim a value its own decisions do not produce.
    """
    payload = dict(payload)
    payload["objective_value"] = float(objective)
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    os.replace(tmp, path)


# ----------------------------------------------------------------------- budget


class Budget:
    """Wall-clock budget with a reserve for serialising the answer.

    The evaluation stops an algorithm still running at its limit, even if the
    answer is already written, so every loop asks `left()` and stops early.
    """

    def __init__(self, time_limit: float, reserve: float = 3.0) -> None:
        self.start = time.monotonic()
        self.limit = float(time_limit)
        self.reserve = float(reserve)

    def elapsed(self) -> float:
        return time.monotonic() - self.start

    def left(self) -> float:
        return self.limit - self.reserve - self.elapsed()

    def expired(self) -> bool:
        return self.left() <= 0.0


# ---------------------------------------------------------------------- geometry


def euclid(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


def dist_matrix(xs, ys):
    n = len(xs)
    return [[math.hypot(xs[i] - xs[j], ys[i] - ys[j]) for j in range(n)] for i in range(n)]


# ------------------------------------------------------------------------ output


def log(*parts) -> None:
    print(*parts, file=sys.stderr, flush=True)
