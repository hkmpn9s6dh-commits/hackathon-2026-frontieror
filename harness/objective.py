"""Recompute a solution's objective from its own decisions, independently.

The published checkers already reject a solution whose reported
`objective_value` disagrees with its decisions (each checker has an
"objective consistency" constraint). This module recomputes the same number a
second time, in a different piece of code, so the report never quotes a number
that only the solver ever produced: the score printed by `verify.py` comes from
here, and `AC-09` asserts it equals what the solution claims.
"""

from __future__ import annotations

import math


def barnhart2000(instance: dict, solution: dict) -> float:
    comm = {c["commodity_id"]: c for c in instance["commodities"]["commodity_list"]}
    arcs = {a["arc_id"]: a for a in instance["network"]["arcs"]}
    total = 0.0
    for entry in solution["commodities"]:
        c = comm[entry["commodity_id"]]
        if entry.get("rejected"):
            total += float(c["artificial_arc_cost"]) * float(c["demand"])
        else:
            for arc in entry["path_arcs"]:
                total += float(arcs[arc["arc_id"]]["cost"]) * float(c["demand"])
    return total


def fischetti1998(instance: dict, solution: dict) -> float:
    prizes = {int(k): v for k, v in instance["prizes"].items()}
    visited = solution.get("visited_nodes") or []
    return float(sum(prizes[int(v)] for v in visited))


def cordeau2006(instance: dict, solution: dict) -> float:
    nodes = {n["node_id"]: n for n in instance["nodes"]}
    total = 0.0
    for route in solution["routes"].values():
        for a, b in zip(route, route[1:]):
            na, nb = nodes[a], nodes[b]
            total += math.hypot(na["x"] - nb["x"], na["y"] - nb["y"])
    return total


def hoffman1993(instance: dict, solution: dict) -> float:
    costs = instance["cost_vector"]
    return float(sum(costs[j] for j in solution.get("selected_rotations") or []))


def bodur2017(instance: dict, solution: dict) -> float:
    facilities = instance["facilities"]
    costs = instance["transportation_costs"]
    opened = set(solution.get("open_facilities") or [])
    total = sum(float(facilities[f]["opening_cost"]) for f in opened)
    for scenario in instance["scenarios"]:
        sid = str(scenario["id"])
        flows = solution["y"][sid]
        prob = float(scenario["probability"])
        transport = 0.0
        for f_key, row in flows.items():
            f = int(f_key)
            for c_key, qty in row.items():
                transport += float(costs[f][int(c_key)]) * float(qty)
        total += prob * transport
    return total


def nagy2015(instance: dict, solution: dict) -> float:
    dm = instance["distance_matrix"]
    n = int(instance["num_customers"])
    # backhaul id n+c shares customer c's location
    total = 0.0
    for route in solution["routes"]:
        for a, b in zip(route, route[1:]):
            total += float(dm[a if a <= n else a - n][b if b <= n else b - n])
    return total


RECOMPUTE = {
    "barnhart2000": barnhart2000,
    "fischetti1998": fischetti1998,
    "cordeau2006": cordeau2006,
    "hoffman1993": hoffman1993,
    "bodur2017": bodur2017,
    "nagy2015": nagy2015,
}
