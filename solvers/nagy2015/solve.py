"""VRP with divisible deliveries and pickups (Nagy et al. 2015).

Every customer has a delivery and a pickup. They may be served on separate visits
by different vehicles, but each request must be fulfilled in one go. The load at
any point is (deliveries still on board + pickups already collected) and may not
exceed the capacity.

The observation that makes the problem tractable: a route can always be arranged
as *all its deliveries first, then all its pickups*. Then the load peaks at
`max(sum of the route's deliveries, sum of its pickups)`, the order inside each
block is free, and 2-opt inside a block cannot break feasibility. That also shows
the right decomposition: the deliveries and the pickups of the same customer are
**separate tasks** that may go on different routes — which is exactly the freedom
the problem grants, and what a "keep each customer together" model throws away.
On the set-3 instances (one demand close to the capacity) that difference is 20%
of the distance.

So: tasks are the unit, Clarke-Wright savings group them under the two capacity
budgets, each group is ordered by nearest neighbour and improved with 2-opt, then
whole tasks are relocated between routes while both budgets still fit.
"""

from __future__ import annotations

import orlib


def route_distance(route, dist):
    return sum(dist[a][b] for a, b in zip(route, route[1:]))


def order_block(nodes, start, dist):
    remaining = list(nodes)
    ordered = []
    cur = start
    while remaining:
        nxt = min(remaining, key=lambda x: dist[cur][x])
        ordered.append(nxt)
        remaining.remove(nxt)
        cur = nxt
    return ordered


def two_opt_block(block, dist, budget):
    """2-opt on an open path whose ends are the depot."""
    improved = True
    while improved and not budget.expired():
        improved = False
        for i in range(len(block) - 1):
            for k in range(i + 1, len(block)):
                a = block[i - 1] if i else 0
                b = block[i]
                c = block[k]
                d = block[k + 1] if k + 1 < len(block) else 0
                if a == c or b == d:
                    continue
                delta = dist[a][c] + dist[b][d] - dist[a][b] - dist[c][d]
                if delta < -1e-9:
                    block[i : k + 1] = reversed(block[i : k + 1])
                    improved = True
    return block


def feasible_sequence(route, dem, pick, n, cap):
    """Prefix load check plus the no backhaul->own-linehaul arc rule (constraint 15)."""
    for a, b in zip(route, route[1:]):
        if a > n and b == a - n:
            return False
    load = sum(dem[node] for node in route if node and node <= n)
    for node in route:
        if node == 0:
            continue
        if node <= n:
            load -= dem[node]
        else:
            load += pick[node - n]
        if load < -1e-9 or load > cap + 1e-9:
            return False
    return abs(load) <= 1e-9 or load <= cap + 1e-9


def two_opt_full(route, dem, pick, n, cap, dist, budget):
    """2-opt over the whole sequence, keeping it load-feasible.

    "Deliveries then pickups" is a sufficient order, not the only one: when a
    customer's two requests end up on the same route, visiting them back to back
    costs nothing extra in distance but can save a long detour, so the finished
    sequence is re-optimised with the real prefix-load check instead.
    """
    improved = True
    while improved and not budget.expired():
        improved = False
        for i in range(1, len(route) - 2):
            for k in range(i + 1, len(route) - 1):
                a, b = route[i - 1], route[i]
                c, d = route[k], route[k + 1]
                if a == c or b == d:
                    continue
                delta = dist[a][c] + dist[b][d] - dist[a][b] - dist[c][d]
                if delta >= -1e-9:
                    continue
                candidate = route[:i] + list(reversed(route[i : k + 1])) + route[k + 1 :]
                if feasible_sequence(candidate, dem, pick, n, cap):
                    route = candidate
                    improved = True
    return route


def solve(instance: dict, time_limit: float = 60.0) -> tuple[dict, float]:
    budget = orlib.Budget(time_limit, reserve=4.0)
    n = int(instance["num_customers"])
    cap = float(instance["vehicle_capacity"])
    base = instance["distance_matrix"]
    # Backhaul node n+c sits on customer c: extend the matrix to 2n+1 so every
    # lookup stays in range and both kinds share one table.
    size = 2 * n + 1
    dist = [[0.0] * size for _ in range(size)]
    for a in range(size):
        for b in range(size):
            dist[a][b] = base[a if a <= n else a - n][b if b <= n else b - n]

    customers = instance["customers"]
    dem = {c["id"]: float(c["delivery_demand"]) for c in customers}
    pick = {c["id"]: float(c["pickup_demand"]) for c in customers}

    # task t < n  = delivery of customer t+1 (node t+1)
    # task t >= n = pickup  of customer t-n+1 (node t+1, i.e. n + customer)
    def task_node(t):
        return t + 1

    def task_customer(t):
        return t + 1 if t < n else t - n + 1

    def task_qty(t):
        c = task_customer(t)
        return dem[c] if t < n else pick[c]

    num_tasks = 2 * n
    parent = list(range(num_tasks))
    load_d = {t: (dem[task_customer(t)] if t < n else 0.0) for t in range(num_tasks)}
    load_p = {t: (pick[task_customer(t)] if t >= n else 0.0) for t in range(num_tasks)}
    members = {t: {t} for t in range(num_tasks)}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    pairs = []
    for i in range(num_tasks):
        ni = task_node(i)
        for j in range(i + 1, num_tasks):
            nj = task_node(j)
            if task_customer(i) == task_customer(j):
                continue
            saving = dist[0][ni] + dist[0][nj] - dist[ni][nj]
            if saving > 0:
                pairs.append((saving, i, j))
    pairs.sort(reverse=True)

    for saving, i, j in pairs:
        if budget.expired():
            break
        ri, rj = find(i), find(j)
        if ri == rj:
            continue
        if load_d[ri] + load_d[rj] > cap + 1e-9 or load_p[ri] + load_p[rj] > cap + 1e-9:
            continue
        parent[rj] = ri
        load_d[ri] += load_d[rj]
        load_p[ri] += load_p[rj]
        members[ri] |= members.pop(rj)

    groups = [set(g) for g in members.values()]
    cache = {}

    def build(idx):
        group = groups[idx]
        if idx in cache:
            return cache[idx]
        deliveries = sorted(task_node(t) for t in group if t < n)
        pickups = sorted(task_node(t) for t in group if t >= n)
        seq_d = two_opt_block(order_block(deliveries, 0, dist), dist, budget)
        anchor = seq_d[-1] if seq_d else 0
        seq_p = two_opt_block(order_block(pickups, anchor, dist), dist, budget)
        route = [0] + seq_d + seq_p + [0]
        route = two_opt_full(route, dem, pick, n, cap, dist, budget)
        cache[idx] = (route, route_distance(route, dist))
        return cache[idx]

    totals = [build(i)[1] for i in range(len(groups))]
    owner = {}
    for i, g in enumerate(groups):
        for t in g:
            owner[t] = i
    ldd = [sum(task_qty(t) for t in g if t < n) for g in groups]
    lpp = [sum(task_qty(t) for t in g if t >= n) for g in groups]

    improved = True
    passes = 0
    while improved and not budget.expired() and passes < 4:
        improved = False
        passes += 1
        for t in range(num_tasks):
            if budget.expired():
                break
            a = owner[t]
            if len(groups[a]) <= 1:
                continue
            qd = task_qty(t) if t < n else 0.0
            qp = task_qty(t) if t >= n else 0.0
            groups[a].discard(t)
            cache.pop(a, None)
            cost_a = build(a)[1]
            best_move, best_delta = None, -1e-9
            for b in range(len(groups)):
                if b == a:
                    continue
                if ldd[b] + qd > cap + 1e-9 or lpp[b] + qp > cap + 1e-9:
                    continue
                groups[b].add(t)
                cache.pop(b, None)
                cost_b = build(b)[1]
                groups[b].discard(t)
                cache.pop(b, None)
                delta = cost_a + cost_b - totals[a] - totals[b]
                if delta < best_delta:
                    best_delta, best_move = delta, b
            if best_move is not None:
                b = best_move
                groups[b].add(t)
                cache.pop(b, None)
                totals[b] = build(b)[1]
                totals[a] = cost_a
                ldd[a] -= qd
                lpp[a] -= qp
                ldd[b] += qd
                lpp[b] += qp
                owner[t] = b
                improved = True
            else:
                groups[a].add(t)
                cache.pop(a, None)
                totals[a] = build(a)[1]

    routes = []
    detailed = []
    total = 0.0
    for idx in range(len(groups)):
        if not groups[idx]:
            continue
        route, cost = build(idx)
        routes.append(route)
        total += cost
        detail = [{"role": "depot", "customer": 0, "quantity": 0.0}]
        for node in route[1:-1]:
            c = node if node <= n else node - n
            role = "linehaul" if node <= n else "backhaul"
            detail.append({"role": role, "customer": c, "quantity": dem[c] if node <= n else pick[c]})
        detail.append({"role": "depot", "customer": 0, "quantity": 0.0})
        detailed.append(detail)

    orlib.log(f"nagy: {len(routes)} routes, distance {total:.0f}")
    return {"routes": routes, "routes_detailed": detailed}, total


def main() -> None:
    args = orlib.parse_cli("nagy2015")
    instance = orlib.load_instance(args.instance)
    payload, objective = solve(instance, args.time_limit)
    orlib.write_solution(args.output, payload, objective)


if __name__ == "__main__":
    main()
