"""Orienteering problem (Fischetti, Salazar-Gonzalez & Toth 1998).

Maximise the prize of a single depot-to-depot tour whose total travel time stays
inside the budget `t0`. Instances here are 25 to 500 cities.

The tour is built by cheapest-prize insertion: every unvisited city is scored by
`prize / extra travel time` at its best insertion position, the best one goes in
if the budget allows. When nothing fits, 2-opt and or-opt shorten the tour so more
cities fit, and the loop restarts. Perturbation (a random prize multiplier per
restart) is what stops every run from ending at the same local optimum; the best
tour over restarts is kept.
"""

from __future__ import annotations

import random

import orlib


def load_distances(instance):
    n = int(instance["n"])
    dep = int(instance["depot"])
    tt = instance["travel_times"]
    # node ids are 1-based; keep a 1-based matrix so the ids stay native.
    dist = [[0.0] * (n + 1) for _ in range(n + 1)]
    for key, value in tt.items():
        i, j = key.strip("()").split(",")
        a, b = int(i), int(j)
        dist[a][b] = float(value)
        dist[b][a] = float(value)
    return n, dep, dist


def tour_length(tour, dist):
    return sum(dist[a][b] for a, b in zip(tour, tour[1:]))


def best_insertion(tour, city, dist):
    best_pos, best_cost = None, float("inf")
    for pos in range(len(tour) - 1):
        a, b = tour[pos], tour[pos + 1]
        extra = dist[a][city] + dist[city][b] - dist[a][b]
        if extra < best_cost:
            best_cost, best_pos = extra, pos + 1
    return best_pos, best_cost


def two_opt(tour, dist, deadline, max_rounds=200):
    """Shorten a closed tour; returns the new tour."""
    improved = True
    rounds = 0
    while improved and rounds < max_rounds and not deadline():
        improved = False
        rounds += 1
        m = len(tour) - 1
        for i in range(0, m - 1):
            if deadline():
                return tour
            for k in range(i + 2, m):
                if i == 0 and k == m - 1:
                    continue
                a, b, c, d = tour[i], tour[i + 1], tour[k], tour[k + 1]
                delta = dist[a][c] + dist[b][d] - dist[a][b] - dist[c][d]
                if delta < -1e-9:
                    tour[i + 1 : k + 1] = reversed(tour[i + 1 : k + 1])
                    improved = True
                    break
            if improved:
                break
    return tour


def build(instance, dist, n, dep, prizes, budget_len, rng, deadline, noise=0.0):
    tour = [dep, dep]
    length = 0.0
    visited = {dep}
    score = {c: prizes[c] * (1.0 + noise * rng.random()) for c in prizes}
    while not deadline():
        best = None
        best_key = None
        for city in range(1, n + 1):
            if city in visited or prizes[city] <= 0:
                continue
            pos, extra = best_insertion(tour, city, dist)
            if extra <= 1e-9:
                key = (float("inf"), prizes[city])
            else:
                key = (score[city] / extra, prizes[city])
            if length + extra > budget_len:
                continue
            if best_key is None or key > best_key:
                best_key, best = key, (city, pos, extra)
        if best is None:
            break
        city, pos, extra = best
        tour.insert(pos, city)
        length += extra
        visited.add(city)

    # shorten, then keep inserting; repeat while it pays off
    for _ in range(30):
        if deadline():
            break
        before = len(visited)
        tour = two_opt(tour, dist, deadline)
        length = tour_length(tour, dist)
        while not deadline():
            best = None
            best_key = None
            for city in range(1, n + 1):
                if city in visited or prizes[city] <= 0:
                    continue
                pos, extra = best_insertion(tour, city, dist)
                if length + extra > budget_len:
                    continue
                key = (score[city] / max(1e-9, extra), prizes[city])
                if best_key is None or key > best_key:
                    best_key, best = key, (city, pos, extra)
            if best is None:
                break
            city, pos, extra = best
            tour.insert(pos, city)
            length += extra
            visited.add(city)
        if len(visited) == before:
            break
    return tour, sum(prizes[c] for c in visited)


def solve(instance: dict, time_limit: float = 60.0) -> tuple[dict, float]:
    budget = orlib.Budget(time_limit, reserve=5.0)
    n, dep, dist = load_distances(instance)
    prizes = {int(k): float(v) for k, v in instance["prizes"].items()}
    budget_len = float(instance["t0"])
    rng = random.Random(20270104)

    best_tour, best_obj = [dep, dep], 0.0
    rounds = 0
    while not budget.expired():
        noise = 0.0 if rounds == 0 else rng.choice((0.05, 0.15, 0.3, 0.6))
        tour, obj = build(instance, dist, n, dep, prizes, budget_len, rng, budget.expired, noise)
        if obj > best_obj + 1e-9 and len(tour) >= 4:
            best_tour, best_obj = tour, obj
        rounds += 1
        if rounds >= 60:
            break
    orlib.log(f"fischetti: {rounds} restarts, prize {best_obj}, tour {len(best_tour)-1} stops")

    # Guarantee the "at least three cities" rule even on a pathological instance.
    if len(best_tour) < 4:
        best_tour, best_obj = [dep, dep], 0.0
        for city in sorted(range(1, n + 1), key=lambda c: -prizes[c])[:20]:
            if 2 * dist[dep][city] <= budget_len:
                best_tour = [dep, city, dep]
                best_obj = prizes[city]
                break

    visited = sorted(set(best_tour))
    edges = [[a, b] for a, b in zip(best_tour, best_tour[1:])]
    payload = {
        "visited_nodes": visited,
        "edges": edges,
        "tour": best_tour,
        "total_travel_time": tour_length(best_tour, dist),
        "total_prize": best_obj,
    }
    return payload, best_obj


def main() -> None:
    args = orlib.parse_cli("fischetti1998")
    instance = orlib.load_instance(args.instance)
    payload, objective = solve(instance, args.time_limit)
    orlib.write_solution(args.output, payload, objective)


if __name__ == "__main__":
    main()
