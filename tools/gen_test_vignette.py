#!/usr/bin/env python3
"""Living Tides - pipeline test vignette (NOT final art, NOT made in Blender).
Generates real, editable, named, vertex-coloured geometry and writes a binary glTF (.glb)
using only Python + numpy. Blender can import the result (File > Import > glTF 2.0)."""
import json, math, random, struct, sys
from contextlib import contextmanager
import numpy as np

R = random.Random(11)
OBJ, EXTRAS = {}, {}
_GR, _GT = np.eye(3), np.zeros(3)

def hexc(h):
    h = h.lstrip('#'); return np.array([int(h[i:i+2], 16) / 255 for i in (0, 2, 4)])
def lin(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def vary(c, a=0.06): return np.clip(np.asarray(c) * (1 + R.uniform(-a, a)), 0, 1)
def rotm(rx=0, ry=0, rz=0):
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz

@contextmanager
def place(t=(0, 0, 0), ry=0):
    global _GR, _GT
    oR, oT = _GR, _GT
    M = rotm(0, ry, 0); _GT = oR @ np.array(t, float) + oT; _GR = oR @ M
    try: yield
    finally: _GR, _GT = oR, oT

def tri(name, a, b, c, col):
    P = [_GR @ np.array(p, float) + _GT for p in (a, b, c)]
    OBJ.setdefault(name, []).append((P[0], P[1], P[2], np.array(col, float)))

def tri_out(name, a, b, c, col, center):
    a, b, c = (np.array(p, float) for p in (a, b, c))
    if np.dot(np.cross(b - a, c - a), (a + b + c) / 3 - np.array(center, float)) < 0: b, c = c, b
    tri(name, a, b, c, col)

def tri_up(name, a, b, c, col):
    a, b, c = (np.array(p, float) for p in (a, b, c))
    if np.cross(b - a, c - a)[1] < 0: b, c = c, b
    tri(name, a, b, c, col)

def convex(name, pts, faces, col, v=0.03):
    pts = np.array(pts, float); cen = pts.mean(0)
    for f in faces:
        fc = vary(col, v)
        for i in range(1, len(f) - 1):
            tri_out(name, pts[f[0]], pts[f[i]], pts[f[i + 1]], fc, cen)

BOXF = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
def box(name, c, s, col, rx=0, ry=0, rz=0, v=0.03):
    h = np.array(s, float) / 2
    cs = np.array([[(1 if i & 4 else -1) * h[0], (1 if i & 2 else -1) * h[1], (1 if i & 1 else -1) * h[2]] for i in range(8)])
    convex(name, cs @ rotm(rx, ry, rz).T + np.array(c, float), BOXF, col, v)

def prism(name, p0, p1, r0, r1, n, col, v=0.03, twist=0.0):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    ax = p1 - p0; ax /= np.linalg.norm(ax)
    u = np.cross(ax, [0, 1, 0] if abs(ax[1]) < 0.9 else [1, 0, 0]); u /= np.linalg.norm(u); w = np.cross(ax, u)
    ring = lambda p, r, off: [p + r * (math.cos(2 * math.pi * k / n + off) * u + math.sin(2 * math.pi * k / n + off) * w) for k in range(n)]
    off = math.pi / n
    pts = ring(p0, r0, off) + ring(p1, r1, off + twist)
    faces = [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)] + [list(range(n)), list(range(n, 2 * n))]
    convex(name, pts, faces, col, v)

def beam(name, a, b, th, col, v=0.04): prism(name, a, b, th * 0.707, th * 0.707, 4, col, v)

T = (1 + 5 ** 0.5) / 2
ICOV = np.array([[-1, T, 0], [1, T, 0], [-1, -T, 0], [1, -T, 0], [0, -1, T], [0, 1, T], [0, -1, -T], [0, 1, -T], [T, 0, -1], [T, 0, 1], [-T, 0, -1], [-T, 0, 1]], float)
ICOV /= np.linalg.norm(ICOV[0])
ICOF = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
def ico(name, c, r, col, jit=0.12, squash=(1, 1, 1), v=0.07):
    pts = ICOV * (1 + np.array([[R.uniform(-jit, jit)] for _ in range(12)])) * r * np.array(squash) + np.array(c, float)
    convex(name, pts, ICOF, col, v)

# ---------------------------------------------------------------- palette (sRGB)
C = {k: hexc(v) for k, v in dict(
    red='#B5463C', coral='#D8725F', ochre='#D7A546', cream='#EBDcB4', turq='#3FA79E', blue='#3F7DC0',
    deep='#2D5894', green='#6E9C58', leaf='#4FA05A', leaf2='#7DBB55', plum='#7B4F86', dwood='#553828',
    wood='#8B5D3F', lwood='#A9774F', stone='#9C9CAB', rock='#C98B4C', rock2='#B97A40', rockd='#955B33',
    sand='#DDB57A', white='#F1EEE6', glass='#2F4B66', rope='#C9B48A', rust='#A85B3A').items()}

# ---------------------------------------------------------------- rock
def rock(name, cx, cz, rbase, levels, seed, cols, top, n=16, harm=lambda a: 0.0):
    rr = random.Random(seed)
    ang = [2 * math.pi * k / n + rr.uniform(-0.09, 0.09) for k in range(n)]
    base = [rbase * (1 + harm(a)) + rr.uniform(-0.18, 0.18) for a in ang]
    rings = []
    for li, (y, s) in enumerate(levels):
        last = li == len(levels) - 1
        rings.append([np.array([cx + math.cos(a) * r * s * (1 + rr.uniform(-0.06, 0.06)),
                                y + (0 if last else rr.uniform(-0.12, 0.12)),
                                cz + math.sin(a) * r * s * (1 + rr.uniform(-0.06, 0.06))]) for a, r in zip(ang, base)])
    for li in range(len(levels) - 1):
        for k in range(n):
            a, b = rings[li][k], rings[li][(k + 1) % n]; d, c = rings[li + 1][k], rings[li + 1][(k + 1) % n]
            cen = (cx, (a[1] + d[1]) / 2, cz)
            if (k + li) % 2: tri_out(name, a, b, c, vary(cols[li], 0.09), cen); tri_out(name, a, c, d, vary(cols[li], 0.09), cen)
            else: tri_out(name, a, b, d, vary(cols[li], 0.09), cen); tri_out(name, b, c, d, vary(cols[li], 0.09), cen)
    ty = levels[-1][0]; ctr = np.array([cx, ty, cz])
    inner = [ctr + (p - ctr) * 0.45 + np.array([0, rr.uniform(0, 0.05), 0]) for p in rings[-1]]
    for k in range(n):
        a, b = rings[-1][k], rings[-1][(k + 1) % n]; d, c = inner[k], inner[(k + 1) % n]
        tri_up(name + '_top', a, b, c, vary(top, 0.05)); tri_up(name + '_top', a, c, d, vary(top, 0.05))
        tri_up(name + '_top', d, c, ctr + np.array([0, 0.04, 0]), vary(top, 0.05))
    return ang, base

TOP = 3.2
mainh = lambda a: 0.12 * math.sin(2 * a + 0.6) + 0.08 * math.sin(3 * a + 1.0)
rock('cliff_main', 0, 0, 3.7, [(-0.95, 1.14), (0.3, 1.0), (1.3, 0.84), (2.35, 0.87), (TOP, 0.93)], 5,
     [C['rockd'], C['rock2'], C['rock'], C['rock']], C['sand'], harm=mainh)
rock('cliff_ledge', 4.3, 2.4, 1.75, [(-0.95, 1.18), (0.05, 1.0), (0.55, 0.9)], 9, [C['rockd'], C['rock2']], C['sand'], n=11)
for (x, z, r) in [(-4.6, 3.4, 0.7), (-3.4, 4.6, 0.45), (2.2, 5.0, 0.5)]:      # sea stacks
    ico('rocks_sea', (x, 0.05, z), r, C['rock2'], jit=0.25, squash=(1, 0.8, 1))

# ---------------------------------------------------------------- water tile
WX0, WX1, WZ0, WZ1, cell = -8.5, 10.5, -8.5, 10.5, 0.95
nx, nz = int((WX1 - WX0) / cell), int((WZ1 - WZ0) / cell)
def wv(i, j):
    edge = i in (0, nx) or j in (0, nz)
    return np.array([WX0 + i * cell + (0 if edge else R.uniform(-0.25, 0.25)), R.uniform(-0.06, 0.06), WZ0 + j * cell + (0 if edge else R.uniform(-0.25, 0.25))])
grid = [[wv(i, j) for j in range(nz + 1)] for i in range(nx + 1)]
blues = [hexc(h) for h in ('#4C97D6', '#62ACE4', '#3F86C8', '#79BEEC', '#5AA2DC')]
def shore(p):
    d1 = math.hypot(p[0], p[2]); a = math.atan2(p[2], p[0])
    return d1 < 3.7 * (1 + mainh(a)) + 0.75 or math.hypot(p[0] - 4.3, p[2] - 2.4) < 2.6
for i in range(nx):
    for j in range(nz):
        a, b, c, d = grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]
        for t in ((a, b, c), (a, c, d)) if (i + j) % 2 else ((a, b, d), (b, c, d)):
            cen = sum(t) / 3
            tri_up('water_surface', *t, vary(hexc('#A8D9F2'), 0.04) if shore(cen) else vary(R.choice(blues), 0.03))
box('water_slab', ((WX0 + WX1) / 2, -0.55, (WZ0 + WZ1) / 2), (WX1 - WX0, 0.9, WZ1 - WZ0), hexc('#3A78C2'), v=0.0)

# ---------------------------------------------------------------- cottage
X0, X1, Z0, Z1 = -2.3, 0.9, -1.9, 0.7
HF, HB = 2.25, 3.0
def plank_wall(name, p0, p1, hfun, col):
    p0, p1 = np.array(p0, float), np.array(p1, float); L = np.linalg.norm(p1 - p0); d = (p1 - p0) / L
    ry = math.atan2(-d[1], d[0]); t = 0
    while t < L - 1e-6:
        w = min(R.uniform(0.22, 0.34), L - t)
        if L - t - w < 0.12: w = L - t
        m = t + w / 2; h = hfun(m / L) + R.uniform(-0.03, 0.03); cxz = p0 + d * m
        box(name, (cxz[0], TOP + h / 2, cxz[1]), (w - 0.018, h, 0.07 + R.uniform(-0.01, 0.012)), vary(col, 0.09), ry=ry, rz=R.uniform(-0.006, 0.006), v=0.02)
        t += w
plank_wall('house_wall_front', (X0, Z1), (X1, Z1), lambda s: HF, C['ochre'])
plank_wall('house_wall_right', (X1, Z1), (X1, Z0), lambda s: HF + (HB - HF) * s, C['ochre'])
plank_wall('house_wall_back', (X1, Z0), (X0, Z0), lambda s: HB, C['ochre'])
plank_wall('house_wall_left', (X0, Z0), (X0, Z1), lambda s: HB + (HF - HB) * s, C['ochre'])
for (x, z) in [(X0, Z0), (X0, Z1), (X1, Z0), (X1, Z1)]:
    box('house_corner_posts', (x, TOP + 1.5, z), (0.13, 3.0 if z == Z0 else 2.3, 0.13), C['dwood'])
    box('house_footings', (x, TOP - 0.02, z), (0.42, 0.26, 0.42), C['stone'], ry=R.uniform(-0.3, 0.3))
box('house_floor', ((X0 + X1) / 2, TOP + 0.05, (Z0 + Z1) / 2), (X1 - X0 - 0.1, 0.08, Z1 - Z0 - 0.1), C['wood'])

# corrugated roof (back high, front low)
RX0, RX1, RZ0, RZ1 = X0 - 0.32, X1 + 0.32, Z0 - 0.28, Z1 + 0.5
ry_ = lambda z: TOP + HB + 0.1 + (z - Z0) / (Z1 - Z0) * (HF - HB)
ns = int((RX1 - RX0) / 0.17); sheetcol = None
for i in range(ns):
    if i % 6 == 0: sheetcol = vary(C['rust'] if i == 12 else C['red'], 0.12)
    xa, xb = RX0 + (RX1 - RX0) * i / ns, RX0 + (RX1 - RX0) * (i + 1) / ns
    oa, ob = (0.035, -0.035) if i % 2 == 0 else (-0.035, 0.035)
    zm = (RZ0 + RZ1) / 2 + (0.25 if (i // 6) % 2 else -0.2)
    for (za, zb, dy, cm) in ((RZ0 - R.uniform(0, 0.06), zm + 0.06, 0.03, 1.0), (zm, RZ1 + R.uniform(-0.03, 0.08), 0.0, 0.93)):
        col = vary(sheetcol * cm, 0.035)
        quad_pts = [(xa, ry_(za) + oa + dy, za), (xb, ry_(za) + ob + dy, za), (xb, ry_(zb) + ob + dy, zb), (xa, ry_(zb) + oa + dy, zb)]
        tri_up('house_roof_sheets', quad_pts[0], quad_pts[1], quad_pts[2], col); tri_up('house_roof_sheets', quad_pts[0], quad_pts[2], quad_pts[3], col)
for x in (X0 - 0.2, (X0 + X1) / 2, X1 + 0.2):
    beam('house_roof_rafters', (x, ry_(RZ0 + 0.05) - 0.12, RZ0 + 0.05), (x, ry_(RZ1 - 0.05) - 0.12, RZ1 - 0.05), 0.11, C['dwood'])
box('house_roof_patch', (-0.2, ry_(-0.9) + 0.07, -0.9), (0.8, 0.03, 0.6), C['turq'], rx=math.atan2(HB - HF, Z1 - Z0), ry=0.2)
for (x, z) in ((-1.6, -0.2), (0.3, 0.2)):
    box('house_roof_weights', (x, ry_(z) + 0.12, z), (0.26, 0.14, 0.18), C['stone'], ry=R.uniform(0, 1))

def window(prefix, w=0.86, h=0.78):
    """built facing +z at local origin (centre of opening)"""
    box(prefix + '_glass', (0, 0, 0.0), (w, h, 0.03), C['glass'], v=0)
    EXTRAS[prefix + '_glass'] = {'emissive': [1.0, 0.70, 0.34]}
    for (c, s) in (((0, h / 2 + 0.04, 0.03), (w + 0.2, 0.09, 0.08)), ((0, -h / 2 - 0.04, 0.04), (w + 0.26, 0.09, 0.12)),
                   ((-w / 2 - 0.04, 0, 0.03), (0.09, h, 0.08)), ((w / 2 + 0.04, 0, 0.03), (0.09, h, 0.08)),
                   ((0, 0, 0.03), (0.04, h, 0.04)), ((0, 0, 0.03), (w, 0.04, 0.04))):
        box(prefix + '_frame', c, s, C['cream'])
    for sgn in (-1, 1):
        ang = sgn * 0.5; cx = sgn * (w / 2 + 0.09 + 0.21 * math.cos(0.5)); cz = 0.05 + 0.21 * math.sin(0.5)
        box(prefix + '_shutters', (cx, 0, cz), (0.42, h + 0.06, 0.04), C['blue'], ry=-ang)
        for k in range(4):
            box(prefix + '_shutters', (cx, -h / 2 + 0.14 + k * 0.19, cz + 0.02), (0.34, 0.05, 0.05), vary(C['deep'], 0.05), ry=-ang)

with place((0.05, TOP + 1.3, Z1 + 0.05)): window('house_window_front')
with place((X1 + 0.05, TOP + 1.45, -0.7), ry=math.pi / 2): window('house_window_side', w=0.7)

with place((-1.45, TOP, Z1 + 0.05)):  # door (facing +z); hinge pivot documented in manifest
    box('house_door_frame', (0, 1.93, 0.02), (1.08, 0.1, 0.1), C['dwood']); box('house_door_frame', (-0.5, 0.95, 0.02), (0.09, 1.9, 0.1), C['dwood']); box('house_door_frame', (0.5, 0.95, 0.02), (0.09, 1.9, 0.1), C['dwood'])
    for k in range(4): box('house_door_leaf', (-0.33 + k * 0.22, 0.95, 0.03), (0.2, 1.84, 0.05), vary(C['plum'], 0.08))
    box('house_door_leaf', (0, 1.55, 0.065), (0.86, 0.09, 0.03), C['dwood']); box('house_door_leaf', (0, 0.4, 0.065), (0.86, 0.09, 0.03), C['dwood'])
    box('house_door_leaf', (0, 0.97, 0.065), (1.35, 0.08, 0.03), C['dwood'], rz=0.93)
    box('house_door_leaf', (0.3, 0.95, 0.1), (0.05, 0.12, 0.05), C['ochre'])
    box('house_door_step', (0, 0.06, 0.38), (1.2, 0.14, 0.5), C['stone'], ry=0.04)

# life ring on front wall
def torus(name, c, Rm, r, cols, n=10, m=5):
    c = np.array(c, float)
    P = [[c + np.array([(Rm + r * math.cos(2 * math.pi * j / m)) * math.cos(2 * math.pi * i / n), (Rm + r * math.cos(2 * math.pi * j / m)) * math.sin(2 * math.pi * i / n), r * math.sin(2 * math.pi * j / m)]) for j in range(m)] for i in range(n)]
    for i in range(n):
        for j in range(m):
            a, b, cc, d = P[i][j], P[(i + 1) % n][j], P[(i + 1) % n][(j + 1) % m], P[i][(j + 1) % m]
            ring_c = c + Rm * np.array([math.cos(2 * math.pi * (i + .5) / n), math.sin(2 * math.pi * (i + .5) / n), 0])
            col = cols[(i // 2 + (1 if i % 4 < 2 else 0)) % 2] if False else cols[1 if i % 5 == 0 else 0]
            tri_out(name, a, b, cc, col, ring_c); tri_out(name, a, cc, d, col, ring_c)
torus('prop_life_ring', (-0.55, TOP + 1.25, Z1 + 0.12), 0.2, 0.06, [C['white'], C['red']])

# ---------------------------------------------------------------- stilted deck
DY = TOP + 0.03
z = 2.55
while z < 4.75:
    w = R.uniform(0.19, 0.26)
    box('deck_planks', (-0.7 + R.uniform(-0.05, 0.05), DY, z + w / 2), (3.5 + R.uniform(-0.12, 0.12), 0.06, w - 0.02), vary(C['wood'], 0.1), ry=R.uniform(-0.01, 0.01))
    z += w
for x in (-2.25, -0.7, 0.85):
    beam('deck_structure', (x, DY - 0.1, 2.2), (x, DY - 0.1, 4.7), 0.13, C['dwood'])
    beam('deck_structure', (x, -0.7, 4.55), (x, DY - 0.1, 4.55), 0.15, C['dwood'])
    beam('deck_structure', (x, 1.5, 4.55), (x, 2.75, 3.25), 0.1, C['dwood'])
beam('deck_structure', (-2.25, 1.1, 4.55), (0.85, 1.75, 4.55), 0.08, C['dwood']); beam('deck_structure', (-2.25, 1.75, 4.55), (0.85, 1.1, 4.55), 0.08, C['dwood'])
rail = [(-2.4, 2.7), (-2.4, 3.65), (-2.4, 4.68), (-1.2, 4.68), (0.0, 4.68), (1.0, 4.68), (1.0, 3.65), (1.0, 2.7)]
for (x, zz) in rail: beam('deck_rail_posts', (x, DY, zz), (x, DY + 0.82 + R.uniform(-0.04, 0.04), zz), 0.09, C['lwood'])
for (a, b) in zip(rail[:-1], rail[1:]):
    pa, pb = np.array([a[0], DY + 0.72, a[1]]), np.array([b[0], DY + 0.72, b[1]])
    for k in range(4):
        s0, s1 = k / 4, (k + 1) / 4
        q0 = pa + (pb - pa) * s0 - np.array([0, 0.16 * math.sin(math.pi * s0), 0]); q1 = pa + (pb - pa) * s1 - np.array([0, 0.16 * math.sin(math.pi * s1), 0])
        beam('deck_rail_rope', q0, q1, 0.035, C['rope'])
# laundry
for x in (-2.1, 0.7): beam('prop_laundry_poles', (x, DY, 3.75), (x, DY + 2.05, 3.75), 0.07, C['lwood'])
beam('prop_laundry_line', (-2.1, DY + 1.98, 3.75), (0.7, DY + 1.98, 3.75), 0.02, C['rope'])
for (x, w, h, col) in ((-1.6, 0.5, 0.7, C['white']), (-0.95, 0.4, 0.5, C['coral']), (-0.3, 0.55, 0.62, C['turq']), (0.3, 0.3, 0.42, C['cream'])):
    box('prop_laundry_cloth', (x, DY + 1.98 - h / 2, 3.75), (w, h, 0.025), col, rz=R.uniform(-0.05, 0.05), ry=R.uniform(-0.12, 0.12))
# stool + fish rack on deck
box('prop_stool', (0.35, DY + 0.4, 4.2), (0.42, 0.06, 0.36), C['lwood'])
for (dx, dz) in ((-0.16, -0.13), (0.16, -0.13), (-0.16, 0.13), (0.16, 0.13)): beam('prop_stool', (0.35 + dx, DY, 4.2 + dz), (0.35 + dx * 0.8, DY + 0.38, 4.2 + dz * 0.8), 0.05, C['dwood'])

# ---------------------------------------------------------------- yard props
def crate(c, s, ry=0):
    with place(c, ry):
        box('prop_crates', (0, s / 2, 0), (s, s, s), vary(C['lwood'], 0.1))
        for y in (0.12 * s, 0.88 * s): box('prop_crates', (0, y, 0), (s + 0.04, 0.07 * s, s + 0.04), C['dwood'])
crate((0.55, TOP, 1.55), 0.55, 0.2); crate((0.95, TOP, 2.05), 0.42, -0.3); crate((0.6, TOP + 0.55, 1.6), 0.36, 0.7)
def barrel(c):
    c = np.array(c, float)
    prism('prop_barrels', c, c + (0, 0.36, 0), 0.24, 0.3, 8, C['wood'], v=0.08); prism('prop_barrels', c + (0, 0.36, 0), c + (0, 0.72, 0), 0.3, 0.24, 8, C['wood'], v=0.08)
    prism('prop_barrels', c + (0, 0.2, 0), c + (0, 0.26, 0), 0.285, 0.295, 8, C['dwood']); prism('prop_barrels', c + (0, 0.48, 0), c + (0, 0.54, 0), 0.295, 0.285, 8, C['dwood'])
barrel((-2.55, TOP, 1.5)); barrel((4.9, 0.55, 3.2))
for k, x in enumerate((-0.32, 0.05, 0.4)):
    prism('prop_pots', (x, TOP, 1.02), (x, TOP + 0.2, 1.02), 0.085, 0.12, 6, (C['coral'], C['blue'], C['cream'])[k])
    ico('prop_pot_plants', (x, TOP + 0.32, 1.02), 0.14, C['leaf2'] if k != 1 else C['leaf'], jit=0.3)

# ladder between ledge and top
la, lb = np.array([3.78, 0.55, 2.0]), np.array([2.86, TOP + 0.35, 1.5])
side = np.cross(lb - la, [0, 1, 0]); side /= np.linalg.norm(side)
for s in (-0.22, 0.22): beam('ladder_rails', la + side * s, lb + side * s, 0.065, C['lwood'])
for k in range(1, 10):
    p = la + (lb - la) * k / 10; beam('ladder_rungs', p - side * 0.25, p + side * 0.25, 0.05, C['wood'])

# ---------------------------------------------------------------- dock + boat
x = 5.3
while x < 9.0:
    w = R.uniform(0.18, 0.25)
    box('dock_planks', (x + w / 2, 0.52, 2.4 + R.uniform(-0.04, 0.04)), (w - 0.02, 0.06, 1.15 + R.uniform(-0.08, 0.08)), vary(C['wood'], 0.11), ry=R.uniform(-0.02, 0.02))
    x += w
for xx in (5.9, 7.4, 8.85):
    for zz in (1.88, 2.92): beam('dock_piles', (xx, -0.8, zz), (xx + R.uniform(-0.03, 0.03), 0.9 + R.uniform(-0.06, 0.1), zz), 0.14, C['dwood'])
for zz in (1.95, 2.85): beam('dock_structure', (5.3, 0.44, zz), (9.0, 0.44, zz), 0.1, C['dwood'])

def boat(hull, trim):
    L = 1.25; secs = []
    for s in (-1.0, -0.8, -0.35, 0.2, 0.7, 1.0):
        w = 0.46 * max(0.0, 1 - abs(s) ** 2.4) ** 0.55 if s > -0.99 else 0.3
        if s >= 0.999: w = 0.0
        rise = 0.16 * max(0, s) ** 2
        secs.append([np.array([s * L, 0.34 + rise, -w]), np.array([s * L, 0.1 + rise * 0.6, -w * 0.62]), np.array([s * L, 0.0 + rise * 0.8, 0.0]),
                     np.array([s * L, 0.1 + rise * 0.6, w * 0.62]), np.array([s * L, 0.34 + rise, w])])
    cen = (0, 0.6, 0)
    for a, b in zip(secs[:-1], secs[1:]):
        for j in range(4):
            col = vary(hull if j in (0, 3) else trim, 0.05)
            tri_out('boat_hull', a[j], b[j], b[j + 1], col, cen); tri_out('boat_hull', a[j], b[j + 1], a[j + 1], col, cen)
    t = secs[0]
    for j in range(1, 4): tri_out('boat_hull', t[0], t[j], t[j + 1], hull, (1, 0.2, 0))
    box('boat_seats', (-0.5, 0.27, 0), (0.2, 0.04, 0.72), C['lwood']); box('boat_seats', (0.3, 0.27, 0), (0.2, 0.04, 0.8), C['lwood'])
    beam('boat_oars', (-0.9, 0.38, 0.3), (0.7, 0.34, 0.22), 0.04, C['lwood']); box('boat_oars', (0.82, 0.34, 0.215), (0.3, 0.02, 0.13), C['lwood'], ry=0.05)
with place((7.35, -0.1, 3.75), ry=0.12): boat(C['turq'], C['white'])
beam('boat_mooring', (7.9, 0.75, 2.92), (8.45, 0.28, 3.62), 0.025, C['rope'])
# ledge props
crate((4.0, 0.55, 1.6), 0.5, 0.4); crate((3.6, 0.55, 3.2), 0.4, 1.0)
ico('prop_net_pile', (4.75, 0.66, 2.3), 0.3, C['turq'], jit=0.3, squash=(1.2, 0.45, 1.0))
for (bx, bz, col) in ((5.0, 1.5, C['coral']), (5.2, 1.75, C['ochre'])):
    ico('prop_buoys', (bx, 0.7, bz), 0.15, col, jit=0.05)

# ---------------------------------------------------------------- vegetation
def palm(base, lean, h=3.6, seed=3):
    rr = random.Random(seed); base = np.array(base, float); n = 8
    P = [base + np.array([lean[0] * (k / n) ** 2, h * k / n, lean[1] * (k / n) ** 2]) for k in range(n + 1)]
    for k in range(n):
        r0 = 0.17 - 0.08 * k / n
        prism('palm_trunk', P[k], P[k + 1], r0 * 1.12, r0 * 0.9, 6, vary(C['wood'] if k % 2 else C['lwood'], 0.06), twist=0.3)
    top = P[-1]; ico('palm_crown', top, 0.2, C['dwood'], jit=0.1)
    for f in range(9):
        a = 2 * math.pi * f / 9 + rr.uniform(-0.25, 0.25); ln = rr.uniform(1.7, 2.2); droop = rr.uniform(0.9, 1.5); lift = rr.uniform(0.45, 0.8)
        d = np.array([math.cos(a), 0, math.sin(a)]); sd = np.array([-math.sin(a), 0, math.cos(a)]); col = vary(C['leaf'] if f % 3 else C['leaf2'], 0.08)
        prev = None
        for k in range(7):
            s = k / 6; c = top + d * ln * s + np.array([0, lift * math.sin(math.pi * s * 0.8) - droop * s * s, 0])
            w = 0.3 * math.sin(math.pi * (0.08 + 0.92 * s)) ** 0.7
            cur = (c + sd * w - np.array([0, 0.09, 0]), c + np.array([0, 0.05, 0]), c - sd * w - np.array([0, 0.09, 0]))
            if prev:
                for (i0, i1) in ((0, 1), (1, 2)):
                    cc = vary(col, 0.06)
                    tri_up('palm_fronds', prev[i0], prev[i1], cur[i1], cc); tri_up('palm_fronds', prev[i0], cur[i1], cur[i0], cc)
            prev = cur
palm((1.9, TOP, -2.1), (0.9, 0.5))
palm((-2.7, TOP, 2.0), (-0.7, 0.6), h=2.7, seed=8)
def tree(base, h):
    base = np.array(base, float)
    prism('tree_trunk', base, base + (0.15, h, 0), 0.2, 0.12, 6, C['dwood'])
    for (o, r) in (((0.1, h + 0.5, 0.0), 1.05), ((-0.75, h + 0.15, 0.3), 0.8), ((0.85, h + 0.1, -0.3), 0.75), ((0.2, h + 1.25, -0.2), 0.7)):
        ico('tree_canopy', base + o, r, C['green'] if r > 0.78 else C['leaf'], jit=0.16, squash=(1, 0.85, 1))
tree((-0.9, TOP, -2.75), 3.1)
for (c, r) in (((2.5, TOP + 0.25, 0.2), 0.42), ((2.75, TOP + 0.2, 0.65), 0.3), ((-2.75, TOP + 0.22, 0.9), 0.36), ((3.3, 0.75, 3.75), 0.3), ((1.2, TOP + 0.2, -2.9), 0.34)):
    ico('bushes', c, r, C['leaf2'] if r < 0.35 else C['green'], jit=0.2, squash=(1, 0.75, 1))

# ---------------------------------------------------------------- lantern + birds
beam('lantern_post', (1.0, DY + 0.8, 4.68), (1.0, DY + 1.75, 4.68), 0.06, C['dwood']); beam('lantern_post', (1.0, DY + 1.72, 4.68), (0.72, DY + 1.72, 4.68), 0.05, C['dwood'])
box('lantern_glow', (0.72, DY + 1.55, 4.68), (0.14, 0.2, 0.14), C['ochre'], v=0)
EXTRAS['lantern_glow'] = {'emissive': [1.0, 0.62, 0.25], 'light': {'color': [1.0, 0.6, 0.28], 'intensity': 5.0, 'range': 5.5}}
EXTRAS['house_window_front_glass']['light'] = {'color': [1.0, 0.68, 0.36], 'intensity': 3.5, 'range': 4.5, 'offset': [0, 0, 0.5]}
EXTRAS['house_window_side_glass']['light'] = {'color': [1.0, 0.68, 0.36], 'intensity': 3.0, 'range': 4.0, 'offset': [0.5, 0, 0]}
for (bx, by, bz, a) in ((5.5, 2.6, 5.5, 0.3), (6.3, 3.0, 4.6, 0.9), (4.6, 3.3, 6.2, -0.4), (2.6, 4.6, 6.4, 1.4), (7.2, 2.2, 6.0, 0.1)):
    with place((bx, by, bz), ry=a):
        tri_up('seabirds', (0, 0, 0.05), (0.26, 0.07, -0.02), (0.02, 0, -0.07), C['white']); tri_up('seabirds', (0, 0, 0.05), (-0.26, 0.07, -0.02), (-0.02, 0, -0.07), C['white'])

# ---------------------------------------------------------------- GLB export
def export(path):
    bin_, views, accs, meshes, nodes = bytearray(), [], [], [], []
    def add(arr, typ, minmax=False):
        data = arr.astype('<f4').tobytes(); off = len(bin_); bin_.extend(data)
        views.append({'buffer': 0, 'byteOffset': off, 'byteLength': len(data), 'target': 34962})
        a = {'bufferView': len(views) - 1, 'componentType': 5126, 'count': len(arr), 'type': typ}
        if minmax: a['min'] = [float(v) for v in arr.min(0)]; a['max'] = [float(v) for v in arr.max(0)]
        accs.append(a); return len(accs) - 1
    total = 0
    for name in sorted(OBJ):
        tris = OBJ[name]; pos, nor, col = [], [], []
        for (a, b, c, k) in tris:
            n = np.cross(b - a, c - a); ln = np.linalg.norm(n); n = n / ln if ln > 1e-12 else np.array([0, 1, 0])
            kl = lin(k)
            for p in (a, b, c): pos.append(p); nor.append(n); col.append(kl)
        total += len(tris)
        prim = {'attributes': {'POSITION': add(np.array(pos), 'VEC3', True), 'NORMAL': add(np.array(nor), 'VEC3'), 'COLOR_0': add(np.array(col), 'VEC3')}, 'material': 0, 'mode': 4}
        meshes.append({'name': name, 'primitives': [prim]})
        node = {'name': name, 'mesh': len(meshes) - 1}
        if name in EXTRAS: node['extras'] = EXTRAS[name]
        nodes.append(node)
    gltf = {'asset': {'version': '2.0', 'generator': 'Living Tides gen_test_vignette.py (no Blender)'}, 'scene': 0,
            'scenes': [{'name': 'LT_PipelineTest_01', 'nodes': list(range(len(nodes)))}], 'nodes': nodes, 'meshes': meshes,
            'materials': [{'name': 'LT_VertexColor', 'pbrMetallicRoughness': {'baseColorFactor': [1, 1, 1, 1], 'metallicFactor': 0.0, 'roughnessFactor': 0.9}, 'doubleSided': True}],
            'accessors': accs, 'bufferViews': views, 'buffers': [{'byteLength': len(bin_)}]}
    js = json.dumps(gltf, separators=(',', ':')).encode(); js += b' ' * (-len(js) % 4); bin_ += b'\0' * (-len(bin_) % 4)
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_)))
        f.write(struct.pack('<II', len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack('<II', len(bin_), 0x004E4942)); f.write(bin_)
    print(f'wrote {path}: {len(nodes)} named objects, {total} triangles')

if __name__ == '__main__':
    export(sys.argv[1])
