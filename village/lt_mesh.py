"""Shared mesh helpers for Living Tides scripted geometry (massing / pipeline tests). Pure Python + numpy, writes glTF binary."""
import json, math, random, struct
import numpy as np

def hexc(h):
    h = h.lstrip('#'); return np.array([int(h[i:i+2], 16) / 255 for i in (0, 2, 4)])
def lin(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def rotm(rx=0, ry=0, rz=0):
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    return (np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]) @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]) @ np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]))

BOXF = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
T = (1 + 5 ** 0.5) / 2
ICOV = np.array([[-1, T, 0], [1, T, 0], [-1, -T, 0], [1, -T, 0], [0, -1, T], [0, 1, T], [0, -1, -T], [0, 1, -T], [T, 0, -1], [T, 0, 1], [-T, 0, -1], [-T, 0, 1]], float)
ICOV /= np.linalg.norm(ICOV[0])
ICOF = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]

class Mesh:
    def __init__(self, seed=1):
        self.R = random.Random(seed); self.obj = {}; self.extras = {}; self._R = np.eye(3); self._T = np.zeros(3); self._stack = []
    def vary(self, c, a=0.06): return np.clip(np.asarray(c) * (1 + self.R.uniform(-a, a)), 0, 1)
    def push(self, t=(0, 0, 0), ry=0):
        self._stack.append((self._R, self._T)); self._T = self._R @ np.array(t, float) + self._T; self._R = self._R @ rotm(0, ry, 0)
    def pop(self): self._R, self._T = self._stack.pop()
    def tri(self, name, a, b, c, col):
        P = [self._R @ np.array(p, float) + self._T for p in (a, b, c)]
        self.obj.setdefault(name, []).append((P[0], P[1], P[2], np.array(col, float)))
    def tri_out(self, name, a, b, c, col, center):
        a, b, c = (np.array(p, float) for p in (a, b, c))
        if np.dot(np.cross(b - a, c - a), (a + b + c) / 3 - np.array(center, float)) < 0: b, c = c, b
        self.tri(name, a, b, c, col)
    def tri_up(self, name, a, b, c, col):
        a, b, c = (np.array(p, float) for p in (a, b, c))
        if np.cross(b - a, c - a)[1] < 0: b, c = c, b
        self.tri(name, a, b, c, col)
    def quad_up(self, name, a, b, c, d, col): self.tri_up(name, a, b, c, col); self.tri_up(name, a, c, d, col)
    def convex(self, name, pts, faces, col, v=0.03):
        pts = np.array(pts, float); cen = pts.mean(0)
        for f in faces:
            fc = self.vary(col, v)
            for i in range(1, len(f) - 1): self.tri_out(name, pts[f[0]], pts[f[i]], pts[f[i + 1]], fc, cen)
    def box(self, name, c, s, col, rx=0, ry=0, rz=0, v=0.03):
        h = np.array(s, float) / 2
        cs = np.array([[(1 if i & 4 else -1) * h[0], (1 if i & 2 else -1) * h[1], (1 if i & 1 else -1) * h[2]] for i in range(8)])
        self.convex(name, cs @ rotm(rx, ry, rz).T + np.array(c, float), BOXF, col, v)
    def prism(self, name, p0, p1, r0, r1, n, col, v=0.03):
        p0, p1 = np.array(p0, float), np.array(p1, float); ax = p1 - p0; ax /= np.linalg.norm(ax)
        u = np.cross(ax, [0, 1, 0] if abs(ax[1]) < 0.9 else [1, 0, 0]); u /= np.linalg.norm(u); w = np.cross(ax, u)
        ring = lambda p, r: [p + r * (math.cos(2 * math.pi * k / n + math.pi / n) * u + math.sin(2 * math.pi * k / n + math.pi / n) * w) for k in range(n)]
        self.convex(name, ring(p0, r0) + ring(p1, r1), [[k, (k + 1) % n, n + (k + 1) % n, n + k] for k in range(n)] + [list(range(n)), list(range(n, 2 * n))], col, v)
    def beam(self, name, a, b, th, col, v=0.04): self.prism(name, a, b, th * 0.707, th * 0.707, 4, col, v)
    def ico(self, name, c, r, col, jit=0.12, squash=(1, 1, 1), v=0.07):
        pts = ICOV * (1 + np.array([[self.R.uniform(-jit, jit)] for _ in range(12)])) * r * np.array(squash) + np.array(c, float)
        self.convex(name, pts, ICOF, col, v)
    def export(self, path, scene_name, generator):
        bin_, views, accs, meshes, nodes = bytearray(), [], [], [], []
        def add(arr, minmax=False):
            data = arr.astype('<f4').tobytes(); off = len(bin_); bin_.extend(data)
            views.append({'buffer': 0, 'byteOffset': off, 'byteLength': len(data), 'target': 34962})
            a = {'bufferView': len(views) - 1, 'componentType': 5126, 'count': len(arr), 'type': 'VEC3'}
            if minmax: a['min'] = [float(x) for x in arr.min(0)]; a['max'] = [float(x) for x in arr.max(0)]
            accs.append(a); return len(accs) - 1
        total = 0
        for name in sorted(self.obj):
            pos, nor, col = [], [], []
            for (a, b, c, k) in self.obj[name]:
                n = np.cross(b - a, c - a); ln = np.linalg.norm(n)
                if ln < 1e-10: continue
                kl = lin(k)
                for p in (a, b, c): pos.append(p); nor.append(n / ln); col.append(kl)
            if not pos: continue
            total += len(pos) // 3
            meshes.append({'name': name, 'primitives': [{'attributes': {'POSITION': add(np.array(pos), True), 'NORMAL': add(np.array(nor)), 'COLOR_0': add(np.array(col))}, 'material': 0, 'mode': 4}]})
            node = {'name': name, 'mesh': len(meshes) - 1}
            if name in self.extras: node['extras'] = self.extras[name]
            nodes.append(node)
        g = {'asset': {'version': '2.0', 'generator': generator}, 'scene': 0, 'scenes': [{'name': scene_name, 'nodes': list(range(len(nodes)))}], 'nodes': nodes, 'meshes': meshes,
             'materials': [{'name': 'LT_VertexColor', 'pbrMetallicRoughness': {'baseColorFactor': [1, 1, 1, 1], 'metallicFactor': 0.0, 'roughnessFactor': 0.9}, 'doubleSided': True}],
             'accessors': accs, 'bufferViews': views, 'buffers': [{'byteLength': len(bin_)}]}
        js = json.dumps(g, separators=(',', ':')).encode(); js += b' ' * (-len(js) % 4); bin_ += b'\0' * (-len(bin_) % 4)
        with open(path, 'wb') as f:
            f.write(struct.pack('<III', 0x46546C67, 2, 28 + len(js) + len(bin_))); f.write(struct.pack('<II', len(js), 0x4E4F534A)); f.write(js)
            f.write(struct.pack('<II', len(bin_), 0x004E4942)); f.write(bin_)
        return len(nodes), total

# ---- 2D polygon helpers
def poly_area(p): return 0.5 * sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))
def pt_in_poly(x, z, p):
    c = False
    for i in range(len(p)):
        (x1, z1), (x2, z2) = p[i], p[(i + 1) % len(p)]
        if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1: c = not c
    return c
def seg_dist(px, pz, a, b):
    ax, az = a; bx, bz = b; dx, dz = bx - ax, bz - az; L = dx * dx + dz * dz
    t = max(0, min(1, ((px - ax) * dx + (pz - az) * dz) / L)) if L else 0
    return math.hypot(px - ax - t * dx, pz - az - t * dz)
def poly_edge_dist(x, z, p): return min(seg_dist(x, z, p[i], p[(i + 1) % len(p)]) for i in range(len(p)))
def earclip(p):
    p = list(p); idx = list(range(len(p)))
    if poly_area(p) < 0: idx.reverse()
    tris = []; guard = 0
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    while len(idx) > 3 and guard < 20000:
        guard += 1; n = len(idx); done = False
        for i in range(n):
            a, b, c = idx[i - 1], idx[i], idx[(i + 1) % n]
            if cross(p[a], p[b], p[c]) <= 1e-9: continue
            if any(k not in (a, b, c) and cross(p[a], p[b], p[k]) >= 0 and cross(p[b], p[c], p[k]) >= 0 and cross(p[c], p[a], p[k]) >= 0 for k in idx): continue
            tris.append((a, b, c)); idx.pop(i); done = True; break
        if not done: idx.pop(0)
    if len(idx) == 3: tris.append(tuple(idx))
    return tris
