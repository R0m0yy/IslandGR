#!/usr/bin/env python3
"""Layout + navigation tests for the village data (no rendering). Exit code 1 on any failure."""
import heapq, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as L
from lt_mesh import pt_in_poly
fails, notes = [], []
def check(ok, msg):
    if not ok: fails.append(msg)
P = {l['id']: l for l in L.LAND}; order = [l['id'] for l in L.LAND]
# 1 buildings sit fully on their level
for b in L.BUILDINGS:
    x0, x1, z0, z1 = b['footprint']
    for (x, z) in [(x0, z0), (x0, z1), (x1, z0), (x1, z1), (b['cx'], b['cz'])]:
        if b['level'] == 'DECK': check(L.ground_h(x, z) is None and any(d[0] == 'stilt_deck' for d in L.deck_at(x, z)), f"{b['id']} stilt corner ({x},{z}) not on stilt deck over water")
        else: check(L.ground_h(x, z) == b['y'], f"{b['id']} corner ({x:.1f},{z:.1f}) ground {L.ground_h(x, z)} != level {b['y']}")
# 2 no overlaps (0.3 m gap)
for i, a in enumerate(L.BUILDINGS):
    for b in L.BUILDINGS[i + 1:]:
        A, Bf = a['footprint'], b['footprint']
        check(A[1] + 0.3 <= Bf[0] or Bf[1] + 0.3 <= A[0] or A[3] + 0.3 <= Bf[2] or Bf[3] + 0.3 <= A[2], f"{a['id']} overlaps {b['id']}")
# 3 nodes on valid support
def support_ok(x, y, z, tol=0.3):
    g = L.ground_h(x, z)
    return (g is not None and abs(g - y) <= tol) or any(abs(d[1] - y) <= tol for d in L.deck_at(x, z))
for k, n in L.N.items():
    if n['kind'] in ('ground', 'deck'): check(support_ok(n['x'], n['y'], n['z'], 0.05 if n['kind'] == 'ground' else 0.3), f"node {k} not supported at ({n['x']},{n['y']},{n['z']})")
    if n['kind'] == 'water': check(L.ground_h(n['x'], n['z']) is None and not L.deck_at(n['x'], n['z']), f"mooring {k} not on open water")
# 4 edges: slope limits, stay on ground, do not cross buildings
LIM = {'walk': (0, 12), 'door': (0, 12), 'ramp': (0, 25), 'stair': (25, 45), 'ladder': (60, 90), 'bridge': (0, 15), 'archwalk': (0, 15), 'board': (0, 60)}
def seg_hits_rect(ax, az, bx, bz, r, m=0.05):
    x0, x1, z0, z1 = r[0] + m, r[1] - m, r[2] + m, r[3] - m
    for i in range(41):
        t = i / 40; x, z = ax + (bx - ax) * t, az + (bz - az) * t
        if x0 < x < x1 and z0 < z < z1: return True
    return False
lengths = {}
for a, b, t in L.E:
    na, nb = L.N[a], L.N[b]; run = math.hypot(nb['x'] - na['x'], nb['z'] - na['z']); rise = abs(nb['y'] - na['y'])
    slope = math.degrees(math.atan2(rise, run)); lo, hi = LIM[t]; lengths[(a, b)] = math.hypot(run, rise)
    check(lengths[(a, b)] > 0.05, f"edge {a}-{b} has zero length")
    check(lo <= slope <= hi, f"edge {a}-{b} [{t}] slope {slope:.1f} deg outside {lo}-{hi}")
    if t in ('walk', 'door', 'ramp', 'stair', 'ladder'):
        for bl in L.BUILDINGS: check(not seg_hits_rect(na['x'], na['z'], nb['x'], nb['z'], bl['footprint']), f"edge {a}-{b} [{t}] passes through building {bl['id']}")
    if t in ('walk', 'door'):
        for i in range(1, 20):
            s = i / 20; x, z, y = na['x'] + (nb['x'] - na['x']) * s, na['z'] + (nb['z'] - na['z']) * s, na['y'] + (nb['y'] - na['y']) * s
            if not support_ok(x, y, z): check(False, f"edge {a}-{b} [{t}] leaves its surface at ({x:.1f},{z:.1f})"); break
# 5 connectivity and door-to-door routes
adj = {k: [] for k in L.N}
for (a, b), d in lengths.items(): adj[a].append((b, d)); adj[b].append((a, d))
def dijkstra(src, banned=()):
    dist = {src: 0.0}; pq = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]: continue
        for v, w in adj[u]:
            if (u, v) in banned or (v, u) in banned: continue
            if d + w < dist.get(v, 1e18): dist[v] = d + w; heapq.heappush(pq, (d + w, v))
    return dist
doors = [k for k in L.N if k.startswith('door_')]
unreach = [k for k in L.N if k not in dijkstra(doors[0])]
check(not unreach, f"unreachable nodes: {unreach}")
pairs = 0; worst = (0, None, None); total = 0.0
for i, a in enumerate(doors):
    d = dijkstra(a)
    for b in doors[i + 1:]:
        if b in d:
            pairs += 1; total += d[b]
            if d[b] > worst[0]: worst = (d[b], a, b)
        else: check(False, f"no route {a} -> {b}")
# 6 redundancy: remove each vertical link in turn; which doors get cut off?
vert = [(a, b) for a, b, t in L.E if t in ('stair', 'ladder', 'bridge')]
single_points = {}
for v in vert:
    d = dijkstra('door_P01', banned=[v]); cut = [k[5:] for k in doors if k not in d]
    if cut: single_points[f'{v[0]}-{v[1]}'] = cut
# 7 capacity vs jobs
cap = sum(b['household']['capacity'] for b in L.BUILDINGS if b['household']); jobs = sum(len(b['business']['jobs']) for b in L.BUILDINGS if b['business']) + sum(bt['crew_slots'] for bt in L.BOATS)
homes = sum(1 for b in L.BUILDINGS if b['household']); anchors = sum(len(b['interior']['anchors']) for b in L.BUILDINGS)
res = dict(buildings=len(L.BUILDINGS), homes=homes, businesses=sum(1 for b in L.BUILDINGS if b['business']), levels=len(L.LAND), nav_nodes=len(L.N), nav_edges=len(L.E),
           stairs=sum(1 for e in L.E if e[2] == 'stair'), ladders=sum(1 for e in L.E if e[2] == 'ladder'), bridges=sum(1 for e in L.E if e[2] == 'bridge'),
           door_pairs_routed=pairs, door_pairs_expected=len(doors) * (len(doors) - 1) // 2, mean_route_m=round(total / max(pairs, 1), 1),
           longest_route=dict(m=round(worst[0], 1), a=worst[1], b=worst[2]), single_points_of_failure=single_points,
           household_capacity=cap, job_slots=jobs, interaction_anchor_stubs=anchors, failures=fails)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'evidence', 'logs', 'layout_test.json'); json.dump(res, open(out, 'w'), indent=1)
print(json.dumps(res, indent=1)); print('RESULT:', 'FAILED' if fails else 'PASSED', f'({len(fails)} failures)')
sys.exit(1 if fails else 0)
