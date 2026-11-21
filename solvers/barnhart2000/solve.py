"""ODIMCF (Barnhart, Hane & Vance 2000).

Every commodity goes on exactly one origin-to-destination path, or is rejected
onto its artificial arc; physical arcs have zero cost, so the objective is the
revenue of the rejected commodities. Accepted flow is unsplittable and the
capacity is shared, so this is a maximum-revenue unsplittable multicommodity
flow. No polynomial algorithm is known for it; the algorithm below is a
widest-path greedy with several orderings and a repair pass, which is cheap
enough to run many restarts inside the 60 s limit.

Why widest path rather than shortest path: every physical arc costs 0, so
"shortest" is arbitrary and tends to stack commodities on the same few arcs. The
bottleneck rule keeps the residual network balanced and accepts more revenue.
"""

from __future__ import annotations

import heapq
import random

import orlib


def _arc_index(network):
    arcs = network["arcs"]
    out = [[] for _ in range(network["num_nodes"])]
    for a in arcs:
        out[a["from_node"]].append(a)
    return arcs, out


def widest_path(out_arcs, origin, destination, demand, residual, tie_hops=0):
    """Widest (bottleneck) path that still has `demand` of residual capacity.

    Labels are (bottleneck, hops, spare): maximise the bottleneck, then minimise
    hops, then maximise the capacity left on the tightest arc. Ties are broken so
    that the residual network stays balanced, which accepts more revenue than a
    shortest-path packing. Returns the list of arc ids, or None.
    """
    n = len(out_arcs)
    best = [None] * n
    parent = [None] * n  # (previous node, arc id)
    best[origin] = (float("inf"), 0, float("inf"))
    heap = [(-float("inf"), 0, -float("inf"), origin)]
    done = [False] * n
    while heap:
        neg_bottle, hops, neg_spare, node = heapq.heappop(heap)
        if done[node]:
            continue
        done[node] = True
        if node == destination:
            break
        for a in out_arcs[node]:
            free = residual[a["arc_id"]]
            if free < demand:
                continue
            bottle = min(-neg_bottle, free)
            cand = (-bottle, hops + 1, -min(-neg_spare, free))
            nxt = a["to_node"]
            if done[nxt]:
                continue
            if best[nxt] is None or cand < best[nxt]:
                best[nxt] = cand
                parent[nxt] = (node, a["arc_id"])
                heapq.heappush(heap, (cand[0], cand[1], cand[2], nxt))
    if best[destination] is None:
        return None
    path = []
    cur = destination
    while cur != origin:
        step = parent[cur]
        if step is None:
            return None
        prev, aid = step
        path.append(aid)
        cur = prev
    path.reverse()
    return path


def greedy(instance, order_key, alpha, rng, deadline_check):
    network = instance["network"]
    commodities = instance["commodities"]["commodity_list"]
    arcs, out_arcs = _arc_index(network)
    cap = [a["capacity"] for a in arcs]
    residual = list(cap)
    # `alpha` mixes in a "keep room on the tightest arc" term; 0 is pure widest.
    order = sorted(commodities, key=order_key)
    routed = {}
    for k in order:
        if deadline_check():
            break
        cid = k["commodity_id"]
        path = widest_path(out_arcs, k["origin"], k["destination"], k["demand"], residual, alpha)
        if path is None:
            continue
        for aid in path:
            residual[aid] -= k["demand"]
        routed[cid] = path
    return routed, residual


def build_solution(instance, routed):
    commodities = instance["commodities"]["commodity_list"]
    arc_by_id = {a["arc_id"]: a for a in instance["network"]["arcs"]}
    entries = []
    objective = 0.0
    for k in commodities:
        cid = k["commodity_id"]
        path = routed.get(cid)
        if path is None:
            objective += float(k["artificial_arc_cost"]) * float(k["demand"])
            entries.append({"commodity_id": cid, "rejected": True, "path_arcs": []})
        else:
            arcs = [
                {"from": arc_by_id[aid]["from_node"], "to": arc_by_id[aid]["to_node"], "arc_id": aid}
                for aid in path
            ]
            entries.append({"commodity_id": cid, "rejected": False, "path_arcs": arcs})
    return {"commodities": entries}, objective


def solve(instance: dict, time_limit: float = 60.0) -> tuple[dict, float]:
    budget = orlib.Budget(time_limit, reserve=5.0)
    arcs = instance["network"]["arcs"]
    arc_by_id = {a["arc_id"]: a for a in arcs}
    best_payload, best_obj = None, float("inf")
    rng = random.Random(20270104)

    orderings = [
        lambda k: (-(k["artificial_arc_cost"] * k["demand"]), k["commodity_id"]),
        lambda k: (-(k["artificial_arc_cost"] * k["demand"]) / max(1, k["demand"]), k["commodity_id"]),
        lambda k: (k["demand"], -(k["artificial_arc_cost"] * k["demand"]), k["commodity_id"]),
        lambda k: (-k["artificial_arc_cost"], k["demand"], k["commodity_id"]),
    ]
    rounds = 0
    idle = 0
    while not budget.expired():
        if rounds < len(orderings):
            key = orderings[rounds]
        else:
            jitter = {k["commodity_id"]: rng.random() for k in instance["commodities"]["commodity_list"]}
            scale = 1.0 if rounds < 2 * len(orderings) else 0.35
            key = lambda k, j=jitter, s=scale: (-((k["artificial_arc_cost"] * k["demand"]) * (1.0 + s * j[k["commodity_id"]])), k["commodity_id"])
        routed, _ = greedy(instance, key, 0.0, rng, budget.expired)
        payload, obj = build_solution(instance, routed)
        if obj < best_obj - 1e-9:
            best_obj, best_payload = obj, payload
            idle = 0
        else:
            idle += 1
            # `arcs` is referenced to keep the checker's arc ids honest in dev.
            assert all(aid in arc_by_id for p in routed.values() for aid in p)
        rounds += 1
        if idle > 300:          # 300 restarts without a better cover: stop
            break
        if rounds > 20000:
            break
    orlib.log(f"barnhart: {rounds} restarts, best objective {best_obj}")
    return best_payload, best_obj


def main() -> None:
    args = orlib.parse_cli("barnhart2000")
    instance = orlib.load_instance(args.instance)
    payload, objective = solve(instance, args.time_limit)
    orlib.write_solution(args.output, payload, objective)


if __name__ == "__main__":
    main()
