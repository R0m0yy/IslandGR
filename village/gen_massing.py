#!/usr/bin/env python3
"""TEMPORARY MASSING MODEL of the village - generated from layout.py. Not production art.
Writes assets/glb/village_massing_v02.glb, assets/glb/village_nav_overlay_v02.glb and data/village_layout.json."""
import json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as L
from lt_mesh import Mesh, hexc, earclip, poly_area, pt_in_poly, poly_edge_dist
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
C = {k: hexc(v) for k, v in dict(red='#B5463C', coral='#D8725F', ochre='#D7A546', cream='#EBDCB4', turq='#3FA79E', blue='#3F7DC0', deep='#2D5894', green='#6E9C58', leaf='#4FA05A',
     leaf2='#7DBB55', plum='#7B4F86', dwood='#553828', wood='#8B5D3F', lwood='#A9774F', stone='#9C9CAB', rock='#C4854A', rock2='#B27540', rockd='#8C5632', sand='#D9B27C', white='#EDE9DF',
     glass='#2F4B66', rope='#C9B48A', rust='#A85B3A', path='#EAD9B6', dwoodl='#7A5236', stonew='#B9B4A6', lwoodw='#B98A5E').items()}
m = Mesh(seed=21); R = m.R

# ------------------------------------------------------------ terrain: stratified cliff prisms
def resample(poly, step=2.4):
    out = []
    for i in range(len(poly)):
        a, b = np.array(poly[i], float), np.array(poly[(i + 1) % len(poly)], float); n = max(1, int(np.linalg.norm(b - a) / step))
        out += [a + (b - a) * k / n for k in range(n)]
    return out
def cliff(name, poly, h, y0=-1.3, flare=1.0, top_col=None, cap_bottom=False):
    pts = resample(poly); n = len(pts); sgn = 1 if poly_area(poly) > 0 else -1
    nrm = []
    for i in range(n):
        d = pts[(i + 1) % n] - pts[i - 1]; d /= np.linalg.norm(d); nrm.append(np.array([d[1], -d[0]]) * sgn)   # outward
    levels = [y0] + [y for y in np.arange(max(0.3, y0 + 1.3), h - 0.8, 1.55)] + [h]
    rings = []
    for li, y in enumerate(levels):
        f = (1 - (y - y0) / (h - y0)) ** 1.4; ledge = R.uniform(0.0, 0.35) if 0 < li < len(levels) - 1 else 0
        rings.append([np.array([p[0] + nr[0] * (0.12 + flare * 0.95 * f + ledge + R.uniform(0, 0.4 if li else 0.2)), y + (0 if li in (0, len(levels) - 1) else R.uniform(-0.25, 0.25)),
                                p[1] + nr[1] * (0.12 + flare * 0.95 * f + ledge + R.uniform(0, 0.4 if li else 0.2))]) for p, nr in zip(pts, nrm)])
    cx, cz = np.mean([p[0] for p in pts]), np.mean([p[1] for p in pts])
    for li in range(len(levels) - 1):
        base = (C['rockd'], C['rock2'], C['rock'])[min(2, li)] if li < 2 else (C['rock'] if li % 2 else C['rock2'])
        for k in range(n):
            a, b, c, d = rings[li][k], rings[li][(k + 1) % n], rings[li + 1][(k + 1) % n], rings[li + 1][k]
            # orient away from the polygon interior using the edge normal
            mid = (a + b + c + d) / 4; cen = mid - np.array([nrm[k][0], 0, nrm[k][1]])
            if (k + li) % 2: m.tri_out(name, a, b, c, m.vary(base, 0.08), cen); m.tri_out(name, a, c, d, m.vary(base, 0.08), cen)
            else: m.tri_out(name, a, b, d, m.vary(base, 0.08), cen); m.tri_out(name, b, c, d, m.vary(base, 0.08), cen)
    top = [(p[0], p[2]) for p in rings[-1]]
    for (a, b, c) in earclip(top):
        m.tri_up(name + '_top', rings[-1][a], rings[-1][b], rings[-1][c], m.vary(top_col if top_col is not None else C['sand'], 0.035))
    if cap_bottom:
        for (a, b, c) in earclip([(p[0], p[2]) for p in rings[0]]): m.tri(name, rings[0][a], rings[0][c], rings[0][b], C['rockd'])
for l in L.LAND:
    cliff('terrain_' + l['id'], l['poly'], l['h'], flare=0.5 if l['id'] in ('SP',) else 1.0)
A = L.ARCH
cliff('terrain_ARCH', [(A['x0'], A['z0']), (A['x1'], A['z0']), (A['x1'], A['z1']), (A['x0'], A['z1'])], A['y1'], y0=A['y0'], flare=0.0, cap_bottom=True)
for (x, z, r) in [(44, 22, 1.6), (41, 26, 1.0), (-30, 30, 1.8), (-34, 26, 1.1), (18, 31, 1.2), (44, -18, 1.5)]:
    m.ico('terrain_sea_rocks', (x, 0.2, z), r, C['rock2'], jit=0.25, squash=(1, 0.8, 1))

# ------------------------------------------------------------ water
WX0, WX1, WZ0, WZ1, cell = -50, 50, -40, 37, 2.2
nx, nz = int((WX1 - WX0) / cell), int((WZ1 - WZ0) / cell); cw, cd = (WX1 - WX0) / nx, (WZ1 - WZ0) / nz
grid = [[np.array([WX0 + i * cw + (0 if i in (0, nx) else R.uniform(-0.55, 0.55)), R.uniform(-0.1, 0.1), WZ0 + j * cd + (0 if j in (0, nz) else R.uniform(-0.55, 0.55))]) for j in range(nz + 1)] for i in range(nx + 1)]
blues = [hexc(h) for h in ('#3E84C4', '#4B93D0', '#3577B8', '#58A0D8', '#4489C8')]
def near_shore(p):
    if L.ground_h(p[0], p[2]) is not None: return False
    return any(poly_edge_dist(p[0], p[2], l['poly']) < 2.4 for l in L.LAND)
for i in range(nx):
    for j in range(nz):
        a, b, c, d = grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]
        for t in ((a, b, c), (a, c, d)) if (i + j) % 2 else ((a, b, d), (b, c, d)):
            cen = sum(t) / 3; m.tri_up('water_surface', *t, m.vary(hexc('#7CC0E4'), 0.04) if near_shore(cen) else m.vary(R.choice(blues), 0.03))
m.box('water_slab', ((WX0 + WX1) / 2, -1.6, (WZ0 + WZ1) / 2), (WX1 - WX0, 3.0, WZ1 - WZ0), hexc('#2F6DB4'), v=0.0)

# ------------------------------------------------------------ decks
for (did, y, x0, x1, z0, z1) in L.DECKS:
    alongx = (x1 - x0) > (z1 - z0); t = z0 if alongx is False else x0; end = z1 if alongx is False else x1
    if did == 'slipway':
        m.convex('deck_slipway', [(x0, 1.5, z0), (x0, 1.5, z1), (x1, -0.4, z0), (x1, -0.4, z1), (x0, 1.3, z0), (x0, 1.3, z1), (x1, -0.6, z0), (x1, -0.6, z1)], [[0, 1, 3, 2], [4, 5, 7, 6], [0, 2, 6, 4], [1, 3, 7, 5], [0, 1, 5, 4], [2, 3, 7, 6]], C['stone']); continue
    while t < end - 0.05:
        w = min(R.uniform(0.28, 0.4), end - t)
        if alongx: m.box('deck_' + did, (t + w / 2, y - 0.04, (z0 + z1) / 2), (w - 0.03, 0.08, z1 - z0 + R.uniform(-0.1, 0.1)), m.vary(C['wood'], 0.11))
        else: m.box('deck_' + did, ((x0 + x1) / 2, y - 0.04, t + w / 2), (x1 - x0 + R.uniform(-0.1, 0.1), 0.08, w - 0.03), m.vary(C['wood'], 0.11))
        t += w
    for px in np.arange(x0 + 0.15, x1 + 0.01, max(2.2, (x1 - x0 - 0.3) / max(1, round((x1 - x0) / 2.6)))):
        for pz in np.arange(z0 + 0.15, z1 + 0.01, max(2.2, (z1 - z0 - 0.3) / max(1, round((z1 - z0) / 2.6)))):
            edge_post = min(px - x0, x1 - px, pz - z0, z1 - pz) < 0.3
            m.beam('deck_piles', (px, -1.4, pz), (px, y + (0.55 if edge_post and did.startswith('pier') else -0.08), pz), 0.2, C['dwood'])

# ------------------------------------------------------------ buildings (massing volumes)
def building(b):
    fr, dp, st = b['front'], b['depth'], b['storeys']; wall, roof = C[b['wall']], C[b['roof']]; bid = 'bld_' + b['id']
    hf = 2.55 * st + 0.25; gable = b['kind'] in ('hall', 'school', 'clinic', 'warehouse'); hb = hf if gable else hf + 0.22 * dp
    m.push((b['cx'], b['y'], b['cz']), ry=(0 if b['facing'] == 'S' else math.pi / 2) + R.uniform(-0.035, 0.035))
    x, z = fr / 2, dp / 2
    if b['level'] == 'DECK':
        for (px, pz) in ((-x + .2, -z + .2), (x - .2, -z + .2), (-x + .2, z - .2), (x - .2, z - .2)): m.beam('bld_stilts', (px, -2.8, pz), (px, 0, pz), 0.2, C['dwood'])
    m.box('bld_plinths', (0, 0.08, 0), (fr + 0.25, 0.3, dp + 0.25), C['stone'])
    if b['kind'] == 'market':   # open-sided hall
        for px in (-x + 0.2, 0, x - 0.2):
            for pz in (-z + 0.2, z - 0.2): m.beam(bid + '_body', (px, 0, pz), (px, hf if pz > 0 else hb, pz), 0.24, C['dwood'])
        m.box(bid + '_body', (0, hf * 0.5, -z + 0.1), (fr, hf, 0.2), wall)
        for k in range(4): m.box('prop_market_stalls', (-x + 1.4 + k * 2.4, 0.5, 0.6), (1.7, 0.9, 1.0), m.vary(C['lwood'], 0.08)); m.box('prop_market_stalls', (-x + 1.4 + k * 2.4, 1.0, 0.6), (1.5, 0.12, 0.8), (C['blue'], C['white'], C['coral'], C['turq'])[k])
    else:
        pts = [(sx * x, hy, sz * z) for sx in (-1, 1) for hy in (0, 1) for sz in (-1, 1)]
        pts = [(px, 0.0 if hy == 0 else (hf if pz > 0 else hb), pz) for (px, hy, pz) in pts]
        m.convex(bid + '_body', pts, [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]], wall, v=0.05)
        for s in range(1, st): m.box('bld_trim', (0, 2.55 * s + 0.2, 0), (fr + 0.1, 0.14, dp + 0.1), C['dwood'])
    ox, of_, ob, th = 0.42, 0.55, 0.3, 0.16
    if gable:
        rh = hf + 0.3 * dp
        for (za, zb, ya, yb) in ((z + of_, 0, hf - 0.3 * of_ * 0.6, rh), (0, -z - ob, rh, hf - 0.1)):
            P = [(-x - ox, ya, za), (x + ox, ya, za), (x + ox, yb, zb), (-x - ox, yb, zb)]
            m.convex(bid + '_roof', [(p[0], p[1] + 0.05, p[2]) for p in P] + [(p[0], p[1] + 0.05 + th, p[2]) for p in P], [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]], roof, v=0.05)
        for sx in (-1, 1): m.convex(bid + '_body', [(sx * x, hf, z), (sx * x, hf, -z), (sx * x, rh, 0), (sx * (x - 0.2), hf, z), (sx * (x - 0.2), hf, -z), (sx * (x - 0.2), rh, 0)], [[0, 1, 2], [3, 4, 5], [0, 1, 4, 3], [1, 2, 5, 4], [2, 0, 3, 5]], wall)
    else:
        sl = (hb - hf) / dp; yf, yb = hf - sl * of_, hb + sl * ob
        P = [(-x - ox, yf, z + of_), (x + ox, yf, z + of_), (x + ox, yb, -z - ob), (-x - ox, yb, -z - ob)]
        m.convex(bid + '_roof', [(p[0], p[1] + 0.05, p[2]) for p in P] + [(p[0], p[1] + 0.05 + th, p[2]) for p in P], [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]], roof, v=0.05)
    # door (front centre) and windows on the two camera-facing sides
    if b['kind'] != 'market':
        big = b['kind'] in ('boatyard', 'warehouse', 'carpenter')
        m.box('bld_doors', (0, 1.0 if not big else 1.2, z + 0.04), (2.4 if big else 0.95, 2.0 if not big else 2.4, 0.1), C['dwood']); m.box('bld_door_steps', (0, 0.1, z + 0.45), (1.5, 0.2, 0.7), C['stone'])
        side = 1 if b['facing'] == 'S' else -1
        for s in range(st):
            wy = 2.55 * s + 1.55
            for wx in ([-x * 0.58, x * 0.58] if s == 0 else [-x * 0.55, 0, x * 0.55]):
                if abs(wx) > 0.95 or s > 0 or big: m.box('bld_windows', (wx, wy, z + 0.03), (0.8, 0.8, 0.08), C['glass'], v=0)
            for wz in (-z * 0.4, z * 0.4): m.box('bld_windows', (side * (x + 0.03), wy, wz), (0.08, 0.8, 0.8), C['glass'], v=0)
        if st == 2:
            m.box('bld_balconies', (0, 2.6, z + 0.65), (fr * 0.8, 0.1, 1.3), C['wood'])
            for px in (-fr * 0.38, fr * 0.38): m.beam('bld_balconies', (px, 0, z + 1.2), (px, 3.5, z + 1.2), 0.13, C['dwood'])
            m.beam('bld_balconies', (-fr * 0.38, 3.45, z + 1.2), (fr * 0.38, 3.45, z + 1.2), 0.08, C['dwood'])
    if b['kind'] in ('eatery', 'store'):
        m.box('bld_awnings', (0, 2.35, z + 0.9), (fr * 0.9, 0.08, 1.7), C['cream'] if b['kind'] == 'store' else C['white'], rx=0.22)
    m.pop()
for b in L.BUILDINGS: building(b)
m.extras['bld_windows'] = {'emissive': [1.0, 0.70, 0.34]}

# ------------------------------------------------------------ circulation geometry from the walk graph
Nn = L.N; P3 = lambda k: np.array([Nn[k]['x'], Nn[k]['y'], Nn[k]['z']])
for a, b, t in L.E:
    pa, pb = P3(a), P3(b); d = pb - pa; run = math.hypot(d[0], d[2]); dirh = np.array([d[0], 0, d[2]]) / max(run, 1e-6); side = np.array([-dirh[2], 0, dirh[0]])
    if t in ('walk', 'door') and Nn[a]['kind'] == 'ground' and Nn[b]['kind'] == 'ground':
        w = 0.55 if t == 'door' else 0.85
        m.quad_up('paths', pa + side * w + (0, .05, 0), pa - side * w + (0, .05, 0), pb - side * w + (0, .05, 0), pb + side * w + (0, .05, 0), m.vary(C['path'], 0.03))
    elif t == 'stair':
        st = L.STAIR_STYLE[a]; w = st['width'] / 2; n = max(2, round(d[1] / 0.19)); stone = st.get('stone')
        for k in range(n):
            c = pa + dirh * run * (k + 0.5) / n; y = pa[1] + d[1] * (k + 1) / n
            if stone: m.box('stairs_stone', (c[0], (pa[1] + y) / 2 - 0.3, c[2]), (run / n + 0.02, y - pa[1] + 0.6, 2 * w), m.vary(C['stone'], 0.05), ry=math.atan2(-dirh[2], dirh[0]), v=0.02)
            else: m.box('stairs_wood', (c[0], y - 0.04, c[2]), (run / n + 0.03, 0.08, 2 * w), m.vary(C['lwood'], 0.08), ry=math.atan2(-dirh[2], dirh[0]), v=0.02)
        for s in (-1, 1):
            if not stone: m.beam('stairs_wood', pa + side * s * w * 0.9 - (0, 0.2, 0), pb + side * s * w * 0.9 - (0, 0.2, 0), 0.16, C['dwood'])
            m.beam('stairs_rails', pa + side * s * w + (0, 0.95, 0), pb + side * s * w + (0, 0.95, 0), 0.08, C['dwood'])
            for k in range(0, n + 1, 5):
                q = pa + d * k / n + side * s * w
                m.beam('stairs_rails', q + (0, 0, 0), q + (0, 0.95, 0), 0.09, C['dwood'])
                if not stone and k % 10 == 5: m.beam('stairs_wood', (q[0], pa[1] - 0.2, q[2]), q, 0.14, C['dwood'])
    elif t == 'ladder':
        for s in (-0.25, 0.25): m.beam('ladders', pa + side * s, pb + side * s + (0, 0.6, 0), 0.08, C['lwood'])
        for k in range(1, 12): m.beam('ladders', pa + d * k / 12 + side * -0.28, pa + d * k / 12 + side * 0.28, 0.06, C['wood'])
    elif t == 'bridge':
        n = int(run / 0.38); sag = lambda s: 0.9 * math.sin(math.pi * s)
        for k in range(n):
            s = (k + 0.5) / n; c = pa + d * s - (0, sag(s), 0); m.box('bridge_planks', c, (0.33, 0.07, 1.5), m.vary(C['lwood'], 0.1), ry=math.atan2(-dirh[2], dirh[0]))
        for sd in (-0.78, 0.78):
            for k in range(24):
                s0, s1 = k / 24, (k + 1) / 24
                for up in (0.0, 1.0): m.beam('bridge_ropes', pa + d * s0 - (0, sag(s0) - up, 0) + side * sd, pa + d * s1 - (0, sag(s1) - up, 0) + side * sd, 0.06, C['rope'])
                if k % 2 == 0: m.beam('bridge_ropes', pa + d * s0 - (0, sag(s0), 0) + side * sd, pa + d * s0 - (0, sag(s0) - 1.0, 0) + side * sd, 0.04, C['rope'])
        for s in (0.0, 0.34, 0.67, 1.0):
            c = pa + d * s; g = L.ground_h(c[0], c[2]) or -1.3
            for sd in (-0.9, 0.9): m.beam('bridge_trestles', (c[0] + side[0] * sd * 1.6, g, c[2] + side[2] * sd * 1.6), c + side * sd + (0, 1.3 - sag(s), 0), 0.24, C['dwood'])
            if 0 < s < 1: m.beam('bridge_trestles', c + side * -0.9 - (0, sag(s) + 0.15, 0), c + side * 0.9 - (0, sag(s) + 0.15, 0), 0.2, C['dwood'])
    elif t == 'archwalk':
        for k in range(0, int(run / 1.6) + 1):
            for sd in (-1.3, 1.3):
                q = pa + d * min(1, k * 1.6 / run) + side * sd; m.beam('arch_rail_posts', q, q + (0, 1.0, 0), 0.1, C['dwood'])
        for sd in (-1.3, 1.3): m.beam('arch_rail_posts', pa + side * sd + (0, 0.9, 0), pb + side * sd + (0, 0.9, 0), 0.05, C['rope'])

# ------------------------------------------------------------ lamps (drive the night render; later driven by sim state)
for i, k in enumerate(L.LAMPS):
    p = P3(k) + np.array([0.9, 0, 0.9]); beacon = k == 'st_beacon'; h = 5.5 if beacon else 2.7
    m.beam('lamp_posts', p, p + (0, h, 0), 0.26 if beacon else 0.1, C['white'] if beacon else C['dwood'])
    nm = f'lamp_{i:02d}_{k}'; m.box(nm, p + (0, h + 0.15, 0), (0.7, 0.7, 0.7) if beacon else (0.26, 0.32, 0.26), C['ochre'], v=0)
    m.extras[nm] = {'emissive': [1.0, 0.62, 0.25], 'light': {'color': [1.0, 0.62, 0.3], 'intensity': 9.0 if beacon else 5.0, 'range': 16 if beacon else 8.5}}

# ------------------------------------------------------------ boats, props, vegetation (placeholder forms)
def boat(name, hull, L_=1.5, wmax=0.55):
    secs = []
    for s in (-1.0, -0.8, -0.35, 0.2, 0.7, 1.0):
        w = wmax * max(0.0, 1 - abs(s) ** 2.4) ** 0.55 if -0.99 < s < 0.999 else (wmax * 0.65 if s < 0 else 0.0); rise = 0.2 * max(0, s) ** 2
        secs.append([np.array([s * L_, 0.45 + rise, -w]), np.array([s * L_, 0.12 + rise * 0.6, -w * 0.62]), np.array([s * L_, rise * 0.8, 0.0]), np.array([s * L_, 0.12 + rise * 0.6, w * 0.62]), np.array([s * L_, 0.45 + rise, w])])
    for a, b in zip(secs[:-1], secs[1:]):
        for j in range(4):
            col = m.vary(hull if j in (0, 3) else C['white'], 0.05); m.tri_out(name, a[j], b[j], b[j + 1], col, (0, 0.8, 0)); m.tri_out(name, a[j], b[j + 1], a[j + 1], col, (0, 0.8, 0))
    for j in range(1, 4): m.tri_out(name, secs[0][0], secs[0][j], secs[0][j + 1], hull, (1, 0.2, 0))
    m.box(name, (-0.5 * L_ / 1.25, 0.34, 0), (0.24, 0.05, wmax * 1.6), C['lwood']); m.box(name, (0.3 * L_ / 1.25, 0.34, 0), (0.24, 0.05, wmax * 1.7), C['lwood'])
cols = [C['turq'], C['red'], C['blue'], C['ochre'], C['coral'], C['white']]
for i, bt in enumerate(L.BOATS):
    n_ = Nn[bt['mooring']]; big = bt['kind'] == 'fishing_boat'
    m.push((n_['x'], -0.12, n_['z']), ry=(0.2 if i % 2 else math.pi / 2 + 0.1)); boat('boat_' + bt['id'], cols[i], 2.6 if big else 1.6, 0.95 if big else 0.6)
    if big: m.box('boat_' + bt['id'], (-0.9, 0.95, 0), (1.3, 1.0, 1.1), C['white']); m.beam('boat_' + bt['id'], (0.6, 0.4, 0), (0.6, 3.4, 0), 0.09, C['lwood'])
    m.pop()
for (x, z, ry) in [(26, 24, 0.6), (8, 33, -0.3)]:
    m.push((x, -0.12, z), ry=ry); boat('boat_at_sea', C['coral'], 1.6, 0.6); m.pop()
m.push((-2.5, 0.75, 8.5), ry=0.0); boat('boat_on_slip', C['lwood'], 2.2, 0.8); m.pop()
def crate(c, s, ry=0): m.box('prop_crates', (c[0], c[1] + s / 2, c[2]), (s, s, s), m.vary(C['lwood'], 0.1), ry=ry)
for (x, z) in [(2.6, 4.2), (3.3, 4.0), (15.8, 3.2), (16.4, 4.0), (16, 3.6), (-7.6, 5.2), (-7.9, 21.6), (24.5, -3.5), (25.3, -3.0), (-15.2, 19.5)]:
    g = L.ground_h(x, z); crate((x, g, z), R.uniform(0.5, 0.8), R.uniform(0, 1.5))
for k in range(5):   # net racks on the spit
    x = 1 + k * 2.3; m.beam('prop_net_racks', (x, 0.8, 25.2), (x, 2.2, 25.2), 0.09, C['dwood']); m.beam('prop_net_racks', (x, 0.8, 26.8), (x, 2.2, 26.8), 0.09, C['dwood']); m.beam('prop_net_racks', (x, 2.15, 25.2), (x, 2.15, 26.8), 0.07, C['dwood'])
    if k < 4: m.quad_up('prop_net_racks', (x, 2.1, 25.3), (x + 2.3, 2.1, 25.3), (x + 2.3, 1.2, 26.4), (x, 1.2, 26.4), m.vary(C['turq'], 0.1))
m.prism('prop_well', (-18, 5.5, -9.3), (-18, 6.2, -9.3), 0.8, 0.8, 8, C['stone']); m.prism('prop_cistern', (-25, 19, -31), (-25, 21.4, -31), 2.0, 2.0, 10, C['stonew']); m.prism('prop_cistern', (-25, 21.4, -31), (-25, 21.9, -31), 2.15, 0.3, 10, C['rust'])
for k in range(3): m.box('prop_benches', (-39.3 + 0 * k, 19.25, -10.2), (1.6, 0.1, 0.45), C['lwood'])
def palm(base, lean, h=4.2, seed=3):
    import random
    rr = random.Random(seed); base = np.array(base, float); n = 6
    P = [base + np.array([lean[0] * (k / n) ** 2, h * k / n, lean[1] * (k / n) ** 2]) for k in range(n + 1)]
    for k in range(n): r0 = 0.2 - 0.09 * k / n; m.prism('veg_palm_trunks', P[k], P[k + 1], r0 * 1.1, r0 * 0.9, 5, m.vary(C['wood'] if k % 2 else C['lwood'], 0.06))
    top = P[-1]
    for f in range(8):
        a = 2 * math.pi * f / 8 + rr.uniform(-0.25, 0.25); ln = rr.uniform(2.0, 2.7); droop = rr.uniform(1.0, 1.7); lift = rr.uniform(0.5, 0.9)
        d = np.array([math.cos(a), 0, math.sin(a)]); sd = np.array([-math.sin(a), 0, math.cos(a)]); col = m.vary(C['leaf'] if f % 3 else C['leaf2'], 0.08); prev = None
        for k in range(5):
            s = k / 4; c = top + d * ln * s + np.array([0, lift * math.sin(math.pi * s * 0.8) - droop * s * s, 0]); w = 0.38 * math.sin(math.pi * (0.08 + 0.92 * s)) ** 0.7
            cur = (c + sd * w - np.array([0, 0.1, 0]), c + np.array([0, 0.06, 0]), c - sd * w - np.array([0, 0.1, 0]))
            if prev:
                for (i0, i1) in ((0, 1), (1, 2)): m.tri_up('veg_palm_fronds', prev[i0], prev[i1], cur[i1], col); m.tri_up('veg_palm_fronds', prev[i0], cur[i1], cur[i0], col)
            prev = cur
def tree(base, h, s=1.0):
    base = np.array(base, float); m.prism('veg_tree_trunks', base, base + (0.15, h, 0), 0.28 * s, 0.16 * s, 6, C['dwood'])
    for (o, r) in (((0.1, h + 0.6, 0.0), 1.5), ((-1.1, h + 0.2, 0.4), 1.1), ((1.2, h + 0.1, -0.4), 1.05), ((0.3, h + 1.7, -0.3), 1.0)):
        m.ico('veg_tree_canopies', base + np.array(o) * s, r * s, C['green'] if r > 1.08 else C['leaf'], jit=0.16, squash=(1, 0.85, 1))
gh = lambda x, z: L.ground_h(x, z)
for i, (x, z, lx, lz) in enumerate([(-20, 26, -0.8, 1.0), (27.5, -4, 1.0, 0.6), (-20.8, -10.8, -0.6, 0.8), (17, -11.5, 1.0, 0.4), (-27, -18.5, -0.8, 0.6), (11.5, -19.5, 0.9, -0.4), (5, -25.5, 0.8, 0.5),
                                        (-41, -30, -0.9, 0.5), (39, -9, 1.0, 0.3), (37, -2, 0.9, 0.8), (10, 26, 0.8, 0.9), (-27.5, 18.5, -0.7, 0.9), (-38, 7.5, -0.9, 0.7), (36.5, 19, 0.8, 0.8)]):
    palm((x, gh(x, z), z), (lx, lz), h=R.uniform(3.6, 5.0), seed=i)
for (x, z, h, s) in [(-39.5, -18.5, 3.4, 1.5), (-13, -31, 3.0, 1.1), (4.5, -15.5, 2.6, 0.9), (16.5, -8, 2.4, 0.8), (-34, -15, 2.8, 1.0), (34, -13, 2.6, 1.0), (-33, 12.5, 2.4, 0.9), (-28, -24, 2.6, 0.9)]:
    tree((x, gh(x, z), z), h, s)
for (x, z, r) in [(-21, 19.5, 0.8), (16, -6.2, 0.7), (17.5, -9.5, 0.9), (11, -14.5, 0.7), (5.3, -17.5, 0.8), (-21.5, -18.5, 0.8), (5, -22, 0.9), (-5, -27, 0.8), (-41, -12, 0.9), (-37.5, -32, 1.0), (40, -5, 0.9), (33, -14, 0.8),
                  (-34.5, 0.5, 0.7), (-29, 14, 0.8), (-24, -11.5, 0.6), (28, 4, 0.6), (36, 20, 0.7), (-12.5, 26.5, 0.7), (-39, 2, 0.8), (-15, -32.5, 0.9)]:
    g = gh(x, z)
    if g is not None: m.ico('veg_bushes', (x, g + r * 0.5, z), r, C['leaf2'] if r < 0.75 else C['green'], jit=0.2, squash=(1, 0.7, 1))
for (bx, by, bz, a) in ((16, 6, 14, 0.3), (18, 7, 12, 0.9), (20, 8, 16, -0.4), (14, 9, 18, 1.4), (22, 6.5, 19, 0.1), (36, 12, 9, 0.7), (33, 13, 10, 2.0), (0, 6, 12, 1.0)):
    m.push((bx, by, bz), ry=a); m.tri_up('seabirds', (0, 0, 0.1), (0.55, 0.14, -0.04), (0.04, 0, -0.14), C['white']); m.tri_up('seabirds', (0, 0, 0.1), (-0.55, 0.14, -0.04), (-0.04, 0, -0.14), C['white']); m.pop()

os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
json.dump(L.to_json(), open(os.path.join(ROOT, 'data', 'village_layout.json'), 'w'), indent=1)
n, t = m.export(os.path.join(ROOT, 'assets/glb/village_massing_v02.glb'), 'LT_Village_Massing_v02_TEMPORARY', 'Living Tides gen_massing.py (temporary massing, no Blender)')
print(f'village_massing_v02.glb: {n} objects, {t} triangles')

# ------------------------------------------------------------ navigation overlay (diagram layer)
o = Mesh(seed=3); TC = dict(walk='#FFE14D', door='#FFFFFF', ramp='#7CFF6B', stair='#FF5A36', ladder='#FF4FD8', bridge='#35E0FF', archwalk='#35E0FF', board='#3D7BFF')
for a, b, t in L.E:
    o.beam('nav_edges_' + t, P3(a) + (0, 0.5, 0), P3(b) + (0, 0.5, 0), 0.5 if t in ('stair', 'ladder', 'bridge') else 0.32, hexc(TC[t]), v=0)
for k, nd in Nn.items():
    o.ico('nav_doors' if k.startswith('door_') else 'nav_nodes', P3(k) + (0, 0.5, 0), 0.55 if k.startswith('door_') else 0.3, hexc('#2B6BFF') if k.startswith('door_') else hexc('#FFFFFF'), jit=0, v=0)
for k in list(o.obj): o.extras[k] = {'unlit': True}
n, t = o.export(os.path.join(ROOT, 'assets/glb/village_nav_overlay_v02.glb'), 'LT_Village_NavOverlay_v02', 'Living Tides gen_massing.py')
print(f'village_nav_overlay_v02.glb: {n} objects, {t} triangles')
