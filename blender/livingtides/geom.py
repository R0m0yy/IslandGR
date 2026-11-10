"""Geometry core: a small polygon-mesh builder with a transform stack.

No bpy / bmesh here.  Everything is plain Python + numpy so the same code is
used by Blender (via bl_io.to_object) and by the headless unit tests.

Conventions: Blender axes (X right, Y back, Z up), metres.
"""
from __future__ import annotations
import math
import random
from contextlib import contextmanager
import numpy as np


# ---------------------------------------------------------------- matrices
def T(x=0.0, y=0.0, z=0.0):
    m = np.eye(4); m[:3, 3] = (x, y, z); return m

def S(x=1.0, y=None, z=None):
    y = x if y is None else y; z = x if z is None else z
    m = np.eye(4); m[0, 0], m[1, 1], m[2, 2] = x, y, z; return m

def Rx(a):
    c, s = math.cos(a), math.sin(a); m = np.eye(4)
    m[1, 1], m[1, 2], m[2, 1], m[2, 2] = c, -s, s, c; return m

def Ry(a):
    c, s = math.cos(a), math.sin(a); m = np.eye(4)
    m[0, 0], m[0, 2], m[2, 0], m[2, 2] = c, s, -s, c; return m

def Rz(a):
    c, s = math.cos(a), math.sin(a); m = np.eye(4)
    m[0, 0], m[0, 1], m[1, 0], m[1, 1] = c, -s, s, c; return m

def frame(origin, u, v):
    """Matrix whose local X,Y map to u,v and Z to u x v (all normalised)."""
    u = np.asarray(u, float); v = np.asarray(v, float)
    u = u / np.linalg.norm(u); v = v / np.linalg.norm(v)
    n = np.cross(u, v); n /= np.linalg.norm(n)
    m = np.eye(4); m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = u, v, n, origin
    return m

def xform(M, p):
    p = np.asarray(p, float)
    return (M[:3, :3] @ p) + M[:3, 3]


# ---------------------------------------------------------------- mesh
class Mesh:
    """Accumulates vertices / n-gon faces / per-face material names."""

    def __init__(self, name="mesh"):
        self.name = name
        self.v: list = []
        self.f: list = []
        self.fm: list = []
        self.ft: list = []          # per-face colour tint multiplier
        self._stack = [np.eye(4)]

    # -- transform stack
    @property
    def M(self):
        return self._stack[-1]

    @contextmanager
    def push(self, *mats):
        m = self.M
        for a in mats:
            m = m @ a
        self._stack.append(m)
        try:
            yield self
        finally:
            self._stack.pop()

    # -- raw
    def add(self, pts, faces, mat, tint=1.0):
        base = len(self.v)
        P = np.asarray(pts, float)
        M = self.M
        W = P @ M[:3, :3].T + M[:3, 3]
        self.v.extend(map(tuple, W))
        if isinstance(mat, str):
            for fc in faces:
                self.f.append(tuple(base + i for i in fc)); self.fm.append(mat); self.ft.append(tint)
        else:
            for fc, mm in zip(faces, mat):
                self.f.append(tuple(base + i for i in fc)); self.fm.append(mm); self.ft.append(tint)
        return base

    def merge(self, other: "Mesh", M=None):
        base = len(self.v)
        P = np.asarray(other.v, float).reshape(-1, 3)
        Mx = self.M if M is None else self.M @ M
        W = P @ Mx[:3, :3].T + Mx[:3, 3]
        self.v.extend(map(tuple, W))
        self.f.extend(tuple(base + i for i in fc) for fc in other.f)
        self.fm.extend(other.fm)
        self.ft.extend(other.ft)

    def deform(self, start, fn):
        """Apply fn(xyz ndarray Nx3)->Nx3 to world-space verts from index start."""
        if start >= len(self.v):
            return
        P = np.asarray(self.v[start:], float)
        self.v[start:] = list(map(tuple, fn(P)))

    def bounds(self):
        P = np.asarray(self.v, float)
        return P.min(0), P.max(0)

    @property
    def tri_count(self):
        return sum(len(f) - 2 for f in self.f)

    # -- primitives
    _BOX_F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]

    def box(self, x0, y0, z0, x1, y1, z1, mat, wob=0.0, rng=None, taper=0.0, vary=0.0):
        """Axis-aligned (in local frame) box.  wob = random corner offset,
        taper = inward shrink of the top face (fraction of half-size)."""
        if x1 < x0: x0, x1 = x1, x0
        if y1 < y0: y0, y1 = y1, y0
        if z1 < z0: z0, z1 = z1, z0
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        tx0, tx1 = x0 + (cx - x0) * taper, x1 - (x1 - cx) * taper
        ty0, ty1 = y0 + (cy - y0) * taper, y1 - (y1 - cy) * taper
        pts = [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
               [tx0, ty0, z1], [tx1, ty0, z1], [tx1, ty1, z1], [tx0, ty1, z1]]
        if wob and rng is not None:
            for p in pts:
                p[0] += rng.uniform(-wob, wob); p[1] += rng.uniform(-wob, wob); p[2] += rng.uniform(-wob, wob)
        tint = 1.0 + rng.uniform(-vary, vary) if (vary and rng is not None) else 1.0
        return self.add(pts, self._BOX_F, mat, tint)

    def cbox(self, cx, cy, cz, sx, sy, sz, mat, rz=0.0, **kw):
        """Box by centre + full size, optional rotation about local Z."""
        with self.push(T(cx, cy, cz), Rz(rz)):
            return self.box(-sx / 2, -sy / 2, -sz / 2, sx / 2, sy / 2, sz / 2, mat, **kw)

    def beam(self, p0, p1, w, h, mat, up=(0, 0, 1), **kw):
        """Box of section w x h running from p0 to p1 (centred on the line)."""
        p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
        d = p1 - p0; L = float(np.linalg.norm(d))
        if L < 1e-9:
            return
        x = d / L; up = np.asarray(up, float)
        y = np.cross(up, x)
        if np.linalg.norm(y) < 1e-6:
            y = np.cross((0, 1, 0), x)
        y /= np.linalg.norm(y)
        with self.push(frame(p0, x, y)):
            return self.box(0, -w / 2, -h / 2, L, w / 2, h / 2, mat, **kw)

    def prism(self, poly, y0, y1, mat, dz1=0.0, cap_mat=None, tint=1.0):
        """Extrude polygon given in local XZ along local Y from y0 to y1.
        dz1 lifts the far end (used for overlapping roof tiles)."""
        n = len(poly)
        pts = [(x, y0, z) for x, z in poly] + [(x, y1, z + dz1) for x, z in poly]
        faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        mats = [cap_mat or mat, cap_mat or mat]
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, i + n, j + n, j)); mats.append(mat)
        return self.add(pts, faces, mats, tint)

    def cyl(self, r, h, n, mat, r_top=None, z0=0.0):
        """Vertical cylinder / cone frustum, base at z0."""
        rt = r if r_top is None else r_top
        pts, faces = [], []
        for i in range(n):
            a = 2 * math.pi * i / n
            pts.append((r * math.cos(a), r * math.sin(a), z0))
        for i in range(n):
            a = 2 * math.pi * i / n
            pts.append((rt * math.cos(a), rt * math.sin(a), z0 + h))
        faces.append(tuple(range(n - 1, -1, -1)))
        faces.append(tuple(range(n, 2 * n)))
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, j, j + n, i + n))
        return self.add(pts, faces, mat)

    def lathe(self, profile, n, mat):
        """Revolve [(r, z), ...] about Z.  Ends are capped."""
        pts, faces = [], []
        k = len(profile)
        for r, z in profile:
            for i in range(n):
                a = 2 * math.pi * i / n
                pts.append((r * math.cos(a), r * math.sin(a), z))
        for s in range(k - 1):
            for i in range(n):
                j = (i + 1) % n
                faces.append((s * n + i, s * n + j, (s + 1) * n + j, (s + 1) * n + i))
        faces.append(tuple(range(n - 1, -1, -1)))
        faces.append(tuple(range((k - 1) * n, k * n)))
        return self.add(pts, faces, mat)

    def half_tube(self, r, L, mat, seg=5, th=0.03):
        """Half pipe along local X (open side down): ridge / barrel tiles."""
        pts, faces = [], []
        for xi in (0.0, L):
            for rr in (r, r - th):
                for i in range(seg + 1):
                    a = math.pi * i / seg
                    pts.append((xi, rr * math.cos(a), rr * math.sin(a)))
        k = seg + 1
        o0, i0, o1, i1 = 0, k, 2 * k, 3 * k
        for i in range(seg):
            faces.append((o0 + i, o1 + i, o1 + i + 1, o0 + i + 1))      # outer
            faces.append((i0 + i, i0 + i + 1, i1 + i + 1, i1 + i))      # inner
            faces.append((o0 + i, o0 + i + 1, i0 + i + 1, i0 + i))      # end 0
            faces.append((o1 + i, i1 + i, i1 + i + 1, o1 + i + 1))      # end 1
        faces.append((o0, i0, i1, o1)); faces.append((o0 + seg, o1 + seg, i1 + seg, i0 + seg))
        return self.add(pts, faces, mat)

    def blob(self, rx, ry, rz, mat, rng, sub=1, rough=0.18, strata=0.0, flat_base=False):
        """Displaced icosphere: foliage, boulders, cliff masses.
        strata>0 quantises heights into ledges (layered rock)."""
        V, F = icosphere(sub)
        P = np.asarray(V, float)
        ph = [rng.uniform(0, 6.28) for _ in range(6)]
        fq = [rng.uniform(1.2, 2.6) for _ in range(3)]
        d = (np.sin(P[:, 0] * fq[0] * 2 + ph[0]) * np.sin(P[:, 1] * fq[1] * 2 + ph[1])
             + 0.6 * np.sin(P[:, 2] * fq[2] * 3 + ph[2]) * np.sin(P[:, 0] * 3.7 + ph[3])
             + 0.35 * np.sin(P[:, 1] * 6.1 + ph[4]) * np.sin(P[:, 2] * 5.3 + ph[5]))
        P = P * (1.0 + rough * d)[:, None]
        P = P * np.array([rx, ry, rz])
        if strata > 0:
            q = np.round(P[:, 2] / strata) * strata
            P[:, 2] = P[:, 2] * 0.25 + q * 0.75
            # push ledge edges outward a little, alternating by layer
            lay = np.round(P[:, 2] / strata)
            k = 1.0 + 0.07 * np.sin(lay * 2.4 + ph[0])
            P[:, 0] *= k; P[:, 1] *= k
        if flat_base:
            P[:, 2] = np.maximum(P[:, 2], -rz * 0.35)
        return self.add(P, F, mat, 1.0 + rng.uniform(-0.06, 0.06))


# ---------------------------------------------------------------- icosphere
_ICO_CACHE = {}

def icosphere(sub=1):
    if sub in _ICO_CACHE:
        return _ICO_CACHE[sub]
    t = (1 + 5 ** 0.5) / 2
    V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t),
         (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    V = [tuple(np.asarray(p, float) / np.linalg.norm(p)) for p in V]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4),
         (11, 10, 2), (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8),
         (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    for _ in range(sub):
        cache = {}
        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                p = (np.asarray(V[a]) + np.asarray(V[b])) / 2
                V.append(tuple(p / np.linalg.norm(p))); cache[k] = len(V) - 1
            return cache[k]
        F2 = []
        for a, b, c in F:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            F2 += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        F = F2
    _ICO_CACHE[sub] = (V, F)
    return V, F


def rng_for(*keys):
    """Deterministic RNG from arbitrary keys (stable across Python runs)."""
    h = 2166136261
    for ch in "|".join(str(k) for k in keys).encode():
        h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
    return random.Random(h)
