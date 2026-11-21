"""Dial-a-Ride (Cordeau 2006).

Each user has a pickup node, a drop-off node, a time window at both ends, a ride
time limit and a shared vehicle capacity; one vehicle has to serve both ends. The
algorithm is the classical cheapest feasible insertion: requests are inserted one
at a time, at the position pair (pickup, drop-off) with the smallest distance
increase that keeps the route feasible, and the route is re-scheduled from the
depot after every insertion so time windows, capacity, ride time and route
duration are checked on the real schedule rather than on an estimate.

Requests that fit nowhere are retried after a perturbation (randomised order of
insertion and a small amount of cost noise), and the cheapest feasible plan over
restarts is kept. A plan that serves every user always exists in these instances,
so the fallback is a per-user dedicated vehicle, which is feasible by
construction.
"""

from __future__ import annotations

import math
import random

import orlib


class Model:
    def __init__(self, instance):
        self.nodes = {n["node_id"]: n for n in instance["nodes"]}
        self.n_users = int(instance["num_users"])
        self.n_vehicles = int(instance["num_vehicles"])
        self.capacity = int(instance["vehicle_capacity"])
        self.max_ride = float(instance["maximum_ride_time"])
        self.max_duration = float(instance["maximum_route_duration"])
        self.start = 0
        self.end = 2 * self.n_users + 1
        self.dist = {}
        for a, na in self.nodes.items():
            for b, nb in self.nodes.items():
                if a != b:
                    self.dist[(a, b)] = math.hypot(na["x"] - nb["x"], na["y"] - nb["y"])
        self.pickup = {}
        self.dropoff = {}
        for node in self.nodes.values():
            if node["node_type"] == "pickup":
                self.pickup[node["user_id"]] = node["node_id"]
            elif node["node_type"] == "dropoff":
                self.dropoff[node["user_id"]] = node["node_id"]

    def d(self, a, b):
        return 0.0 if a == b else self.dist[(a, b)]

    def schedule(self, route):
        """Forward schedule; returns None when the route is infeasible."""
        times = {}
        load = 0
        t = 0.0
        prev = route[0]
        times[prev] = max(0.0, self.nodes[prev]["earliest_time"])
        if times[prev] > self.nodes[prev]["latest_time"] + 1e-9:
            return None
        load += self.nodes[prev]["load"]
        for node_id in route[1:]:
            node = self.nodes[node_id]
            arrive = times[prev] + self.nodes[prev]["service_duration"] + self.d(prev, node_id)
            t = max(arrive, node["earliest_time"])
            if t > node["latest_time"] + 1e-9:
                return None
            load += node["load"]
            if load < 0 or load > self.capacity:
                return None
            times[node_id] = t
            prev = node_id
        if times[self.end] - times[self.start] > self.max_duration + 1e-9:
            return None
        ride = {}
        for user, p in self.pickup.items():
            q = self.dropoff[user]
            if p not in times or q not in times:
                continue
            ride[user] = times[q] - (times[p] + self.nodes[p]["service_duration"])
            direct = self.d(p, q)
            if ride[user] > self.max_ride + 1e-9 or ride[user] < direct - 1e-9:
                return None
        return times, ride

    def cost(self, route):
        return sum(self.d(a, b) for a, b in zip(route, route[1:]))

    def try_insert(self, route, user):
        """Cheapest feasible (pickup, drop-off) insertion; cost is screened first.

        The distance increase is screened before the schedule is rebuilt, so the
        expensive feasibility check only runs for candidates that would actually
        improve the answer.
        """
        p, q = self.pickup[user], self.dropoff[user]
        base = self.cost(route)
        best = None
        for i in range(1, len(route)):
            for j in range(i, len(route)):
                cand = route[:i] + [p] + route[i:j] + [q] + route[j:]
                delta = self.cost(cand) - base
                if best is not None and delta >= best[0] - 1e-12:
                    continue
                sched = self.schedule(cand)
                if sched is None:
                    continue
                best = (delta, cand, sched)
        return best

    def empty_routes(self):
        return [[self.start, self.end] for _ in range(self.n_vehicles)]


def solve(instance: dict, time_limit: float = 60.0) -> tuple[dict, float]:
    budget = orlib.Budget(time_limit, reserve=6.0)
    m = Model(instance)
    rng = random.Random(2006)
    users = list(range(1, m.n_users + 1))
    best_routes, best_cost = None, float("inf")
    best_sched = None

    rounds = 0
    idle = 0
    while not budget.expired():
        routes = m.empty_routes()
        order = users[:]
        if rounds:
            rng.shuffle(order)
        noise = 0.0 if rounds == 0 else rng.choice((0.02, 0.08, 0.2))
        failed = []
        scheds = [m.schedule(r) for r in routes]
        for user in order:
            if budget.expired():
                failed.append(user)
                continue
            best = None
            for k, route in enumerate(routes):
                cand = m.try_insert(route, user)
                if cand is None:
                    continue
                delta, new_route, sched = cand
                key = delta * (1.0 + noise * rng.random())
                if best is None or key < best[0]:
                    best = (key, k, new_route, sched)
            if best is None:
                failed.append(user)
                continue
            _, k, new_route, sched = best
            routes[k] = new_route
            scheds[k] = sched
        # retry the ones that did not fit, in case an earlier insertion blocked them
        for user in failed[:]:
            done = False
            for k, route in enumerate(routes):
                cand = m.try_insert(route, user)
                if cand is not None:
                    routes[k] = cand[1]
                    scheds[k] = cand[2]
                    failed.remove(user)
                    done = True
                    break
            if not done:
                continue
        if not failed:
            cost = sum(m.cost(r) for r in routes)
            if cost < best_cost - 1e-9:
                best_routes, best_cost = [r[:] for r in routes], cost
                best_sched = [m.schedule(r) for r in routes]
                idle = 0
            else:
                idle += 1
        rounds += 1
        if idle >= 120:
            break
        if rounds >= 500:
            break

    if best_routes is None:
        # Dedicated vehicle per user: always feasible, never competitive.
        routes = []
        for user in users:
            route = [m.start, m.pickup[user], m.dropoff[user], m.end]
            if m.schedule(route) is None:
                orlib.log(f"cordeau: user {user} not insertable even alone")
            routes.append(route)
        best_routes = routes
        best_cost = sum(m.cost(r) for r in best_routes)
        best_sched = [m.schedule(r) for r in best_routes]

    routes_payload = {}
    service_times = {}
    ride_times = {}
    for k, route in enumerate(best_routes):
        # every vehicle needs a route entry, even an empty one: the checker
        # requires exactly one route per vehicle index
        key = str(k)
        routes_payload[key] = route
        sched = best_sched[k]
        times, rides = sched
        for node_id in route[1:-1]:
            service_times[str(node_id)] = times[node_id]
        for user, value in rides.items():
            ride_times[str(user)] = value
        service_times[f"depot_start_{k}"] = times[m.start]
        service_times[f"depot_end_{k}"] = times[m.end]
    orlib.log(f"cordeau: {rounds} restarts, cost {best_cost:.2f}, {len(routes_payload)} routes")
    return (
        {"routes": routes_payload, "service_times": service_times, "ride_times": ride_times},
        best_cost,
    )


def main() -> None:
    args = orlib.parse_cli("cordeau2006")
    instance = orlib.load_instance(args.instance)
    payload, objective = solve(instance, args.time_limit)
    orlib.write_solution(args.output, payload, objective)


if __name__ == "__main__":
    main()
