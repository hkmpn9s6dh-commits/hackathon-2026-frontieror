"""Stochastic capacitated facility location (Bodur et al. 2017).

Open facilities before demand is known, then ship from them in each scenario.
Fixed opening costs compete with expected transport: opening everything is always
capacity-feasible but expensive, opening too little breaks the "total capacity
covers the worst scenario" rule that the checker enforces.

The recourse is a transportation problem per scenario with the unit costs given
per facility-customer pair. Here it is solved greedily: the pairs are sorted once
by unit cost, and each scenario walks that order taking what it can. With a
capacity factor of 1.2-2.0 the capacities are loose enough that this is close to
the LP optimum, and it keeps the run inside the limit: 1,500 scenarios x 2,500
pairs is 3.75M operations, where a general LP per scenario would not fit.

The opening set is chosen by removal: start from every facility open, then drop
facilities while the total capacity still covers the worst scenario and the
sampled expected cost falls. The final allocation is then computed on all
scenarios, and only non-zero shipments are written (the reference solution does
the same; a dense matrix would not fit the 16 MB solution limit).
"""

from __future__ import annotations

import orlib


def allocate(open_ids, demand, costs, capacities, order):
    """Greedy transportation: walk pairs cheapest-first, ship what still fits.

    `demand` is a list indexed by customer; it is consumed in place.
    """
    remaining = {f: capacities[f] for f in open_ids}
    shipped = {}
    total = 0.0
    for f, c in order:
        if f not in remaining:
            continue
        qty = demand[c]
        if qty <= 0:
            continue
        give = qty if qty < remaining[f] else remaining[f]
        if give <= 0:
            continue
        shipped.setdefault(f, {})[c] = give
        remaining[f] -= give
        demand[c] = qty - give
        total += give * costs[f][c]
    unmet = sum(demand)
    return shipped, total, unmet


def expected_cost(open_ids, sample, costs, capacities, order, fixed):
    total = fixed
    for prob, demands in sample:
        remaining = list(demands)
        _, transport, unmet = allocate(open_ids, remaining, costs, capacities, order)
        if unmet > 1e-6:
            return None
        total += prob * transport
    return total


def solve(instance: dict, time_limit: float = 60.0) -> tuple[dict, float]:
    budget = orlib.Budget(time_limit, reserve=6.0)
    facilities = instance["facilities"]
    customers = instance["customers"]
    scenarios = instance["scenarios"]
    costs = instance["transportation_costs"]
    n_f = len(facilities)
    n_c = len(customers)
    capacities = {f["id"]: float(f["capacity"]) for f in facilities}
    fixed_cost = {f["id"]: float(f["opening_cost"]) for f in facilities}
    total_capacity = sum(capacities.values())

    # Cheapest pairs first, computed once: unit costs do not change with scenario.
    order = sorted(
        ((f, c) for f in range(n_f) for c in range(n_c)),
        key=lambda fc: costs[fc[0]][fc[1]],
    )

    worst = max(sum(float(d) for d in s["demands"]) for s in scenarios)
    if total_capacity + 1e-6 < worst:
        orlib.log(f"bodur: instance cannot cover the worst scenario ({total_capacity} < {worst})")

    # A sample keeps the facility search cheap; the final allocation uses all scenarios.
    step = max(1, len(scenarios) // 40)
    picked = scenarios[::step]
    sample = [(float(s["probability"]) * step, [float(d) for d in s["demands"]]) for s in picked]
    sample_prob = sum(p for p, _ in sample) or 1.0

    open_ids = set(range(n_f))

    def cost_with(ids):
        fixed = sum(fixed_cost[f] for f in ids)
        cap = sum(capacities[f] for f in ids)
        if cap + 1e-6 < worst:
            return None
        value = expected_cost(ids, sample, costs, capacities, order, fixed * sample_prob)
        if value is None:
            return None
        return value / sample_prob if sample_prob else value

    current = cost_with(open_ids)
    improved = True
    while improved and not budget.expired():
        improved = False
        best_drop, best_value = None, current
        for f in sorted(open_ids, key=lambda f: -fixed_cost[f]):
            if budget.expired():
                break
            trial = open_ids - {f}
            if not trial:
                continue
            value = cost_with(trial)
            if value is not None and value < best_value - 1e-9:
                best_drop, best_value = f, value
        if best_drop is not None:
            open_ids = open_ids - {best_drop}
            current = best_value
            improved = True
    orlib.log(f"bodur: {len(open_ids)} facilities open, sampled expected cost {current:.1f}")

    # Final allocation on every scenario.
    y = {}
    objective = sum(fixed_cost[f] for f in open_ids)
    worst_unmet = 0.0
    for s in scenarios:
        remaining = [float(d) for d in s["demands"]]
        shipped, transport, unmet = allocate(open_ids, remaining, costs, capacities, order)
        worst_unmet = max(worst_unmet, unmet)
        y[str(s["id"])] = {str(f): {str(c): q for c, q in row.items()} for f, row in shipped.items()}
        objective += float(s["probability"]) * transport
    orlib.log(f"bodur: objective {objective:.1f}, worst unmet demand {worst_unmet:.3f}")

    payload = {
        "open_facilities": sorted(open_ids),
        "x": {str(f): (1 if f in open_ids else 0) for f in range(n_f)},
        "y": y,
    }
    return payload, objective


def main() -> None:
    args = orlib.parse_cli("bodur2017")
    instance = orlib.load_instance(args.instance)
    payload, objective = solve(instance, args.time_limit)
    orlib.write_solution(args.output, payload, objective)


if __name__ == "__main__":
    main()
