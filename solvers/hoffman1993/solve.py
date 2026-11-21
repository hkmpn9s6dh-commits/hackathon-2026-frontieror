"""Set partitioning / crew scheduling (Hoffman & Padberg 1993).

Every flight leg must be covered exactly once, plus optional crew-base
constraints. The instance arrives in column form: 100 rows, 15,000 columns whose
costs (1..200) are unrelated to their length (1..51 legs). Two consequences drive
the design:

* **Short columns are cheap, so the optimum is many short rotations.** CP-SAT's
  branch and bound starts from a feasible partition with ~33 long rotations and
  spends its budget walking down; on the densest instance it never finds *any*
  partition inside 60 s, because five columns that exactly partition 100 legs is
  a needle in 15,000 columns.
* **Feasibility and cost need different searches.** `min_conflicts` treats the
  number of wrongly covered legs as an objective and is not thrown off by the
  cost landscape; once it has a partition, large-neighbourhood search re-solves
  the rows of a few selected rotations exactly, which is where the cost falls.

Order: min-conflicts for a cover -> LNS with CP-SAT on small row sets -> CP-SAT
on the whole model with the best cover as a hint. The reported objective is
recomputed from the rotations actually written out.
"""

from __future__ import annotations

import random

import orlib


def build_rows(columns, num_rows):
    by_row = [[] for _ in range(num_rows)]
    for j, rows in enumerate(columns):
        for i in rows:
            if 0 <= i < num_rows:
                by_row[i].append(j)
    for rows in by_row:
        rows.sort()
    return by_row


def covers_exactly_once(chosen, columns, num_rows):
    seen = [0] * num_rows
    for j in chosen:
        for r in columns[j]:
            if 0 <= r < num_rows:
                seen[r] += 1
    return all(c == 1 for c in seen)


def min_conflicts(columns, costs, by_row, num_rows, rng, deadline, max_moves=400000):
    """Cover every leg exactly once by hill-climbing on the violation count."""
    count = [0] * num_rows
    sel: set[int] = set()

    def delta_add(j):
        d = 0
        for r in columns[j]:
            d += -1 if count[r] == 0 else 1
        return d

    def apply(j, sign):
        for r in columns[j]:
            count[r] += sign

    uncovered = set(range(num_rows))
    while uncovered:
        r = min(uncovered, key=lambda x: len(by_row[x]))
        best, best_key = None, None
        for j in by_row[r]:
            key = (delta_add(j) / max(1, len(columns[j])), costs[j])
            if best_key is None or key < best_key:
                best, best_key = j, key
        if best is None:
            break
        apply(best, +1)
        sel.add(best)
        for r2 in columns[best]:
            uncovered.discard(r2)

    moves = 0
    while moves < max_moves and not deadline():
        moves += 1
        bad = [r for r in range(num_rows) if count[r] != 1]
        if not bad:
            return sorted(sel)
        r = rng.choice(bad)
        if count[r] == 0:
            cands = rng.sample(by_row[r], min(40, len(by_row[r])))
            cands.sort(key=lambda j: (delta_add(j), costs[j]))
            j = cands[0]
            if j in sel:
                continue
            apply(j, +1)
            sel.add(j)
        else:
            holders = [j for j in by_row[r] if j in sel]
            if not holders:
                continue
            j = min(holders, key=lambda x: (delta_add(x), -costs[x]))
            apply(j, -1)
            sel.discard(j)
    return None


def lns(columns, costs, by_row, num_rows, sel, rng, deadline, rounds=80):
    """Free the legs of a few selected rotations and re-solve them exactly."""
    from ortools.sat.python import cp_model

    sel = list(sel)
    stall = 0
    member = [set(rows) for rows in columns]
    for _ in range(rounds):
        if deadline() or stall > 15:
            break
        k = rng.choice((2, 2, 3, 4))
        pick = rng.sample(sel, min(k, len(sel)))
        rows = sorted({r for j in pick for r in member[j]})
        row_set = set(rows)
        anchor = min(rows, key=lambda r: len(by_row[r]))
        cand = [j for j in by_row[anchor] if member_ok(member[j], row_set)]
        if not cand:
            stall += 1
            continue
        model = cp_model.CpModel()
        x = {j: model.NewBoolVar(f"y{j}") for j in cand}
        feasible_model = True
        for r in rows:
            covering = [x[j] for j in cand if r in member[j]]
            if not covering:
                feasible_model = False
                break
            model.Add(sum(covering) == 1)
        if not feasible_model:
            stall += 1
            continue
        model.Minimize(sum(int(costs[j]) * x[j] for j in cand))
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 2.0
        solver.parameters.num_search_workers = 1
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            stall += 1
            continue
        new_local = [j for j in cand if solver.Value(x[j]) == 1]
        local_cost = sum(costs[j] for j in new_local)
        old_cost = sum(costs[j] for j in pick)
        if local_cost < old_cost - 1e-9:
            sel = [j for j in sel if j not in pick] + new_local
            stall = 0
        else:
            stall += 1
    return sel


def member_ok(rows_j, row_set):
    return all(r in row_set for r in rows_j)


def cp_sat_full(columns, costs, by_row, num_rows, num_cols, instance, hint, seconds, minimise=True):
    from ortools.sat.python import cp_model

    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"x{j}") for j in range(num_cols)]
    for i in range(num_rows):
        model.Add(sum(x[j] for j in by_row[i]) == 1)
    base = instance.get("base_constraints")
    if instance.get("has_base_constraints") and base:
        for b, weights in enumerate(base["D_matrix"]["rows"]):
            terms = [int(round(w * 1000)) * x[j] for j, w in enumerate(weights) if w]
            if not terms:
                continue
            model.Add(sum(terms) >= int(round(base["lower_bounds_d1"][b] * 1000)))
            model.Add(sum(terms) <= int(round(base["upper_bounds_d2"][b] * 1000)))
    if minimise:
        model.Minimize(sum(int(costs[j]) * x[j] for j in range(num_cols)))
    if hint:
        hint_set = set(hint)
        for j in range(num_cols):
            model.AddHint(x[j], 1 if j in hint_set else 0)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 2
    solver.parameters.max_time_in_seconds = max(1.0, seconds)
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, status
    return [j for j in range(num_cols) if solver.Value(x[j]) == 1], status


def solve(instance: dict, time_limit: float = 60.0) -> tuple[dict, float]:
    budget = orlib.Budget(time_limit, reserve=7.0)
    columns = instance["constraint_matrix_A"]["columns"]
    costs = [float(c) for c in instance["cost_vector"]]
    num_rows = int(instance["dimensions"]["num_rows"])
    num_cols = int(instance["dimensions"]["num_cols"])
    by_row = build_rows(columns, num_rows)
    rng = random.Random(1993)

    best: list[int] = []
    best_cost = float("inf")

    # Cheap first try, hard-capped: min-conflicts either finds a cover fast or
    # wanders (exact cover is tight, so every move breaks something).
    cover = min_conflicts(columns, costs, by_row, num_rows, rng,
                          lambda: budget.elapsed() > 6.0, max_moves=20000)
    if cover and covers_exactly_once(cover, columns, num_rows):
        best, best_cost = cover, sum(costs[j] for j in cover)
        orlib.log(f"hoffman: min-conflicts cover {len(best)} rotations, cost {best_cost:.0f}")

    if best and budget.left() > 4:
        improved = lns(columns, costs, by_row, num_rows, best, rng, budget.expired)
        if covers_exactly_once(improved, columns, num_rows):
            cost = sum(costs[j] for j in improved)
            if cost < best_cost:
                best, best_cost = improved, cost
                orlib.log(f"hoffman: LNS -> {len(best)} rotations, cost {best_cost:.0f}")

    if budget.left() > 3:
        try:
            chosen, status = cp_sat_full(
                columns, costs, by_row, num_rows, num_cols, instance, best, seconds=budget.left()
            )
            if chosen and covers_exactly_once(chosen, columns, num_rows):
                cost = sum(costs[j] for j in chosen)
                orlib.log(f"hoffman: cp-sat {status} cost {cost:.0f}")
                if cost < best_cost:
                    best, best_cost = chosen, cost
        except Exception as exc:  # pragma: no cover
            orlib.log(f"hoffman: cp-sat unavailable ({exc})")

    objective = float(sum(costs[j] for j in best))
    orlib.log(f"hoffman: final {len(best)} rotations, objective {objective:.0f}")
    return _payload(best), objective


def _payload(chosen):
    return {
        "selected_rotations": [int(j) for j in chosen],
        "variable_values": {str(int(j)): 1.0 for j in chosen},
    }


def main() -> None:
    args = orlib.parse_cli("hoffman1993")
    instance = orlib.load_instance(args.instance)
    payload, objective = solve(instance, args.time_limit)
    orlib.write_solution(args.output, payload, objective)


if __name__ == "__main__":
    main()
