"""Clothing, hair, eyes and prop geometry for hero villagers.

All pieces are separate meshes with real thickness, faceted (flat shaded) and
coloured with per-face vertex colours. Clothing shells are cut from the
decimated body so they fit and inherit its bone weights."""
from __future__ import annotations
import math
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from . import hero
from .hero import BONES, BI, rgb, jitter, mix


# ------------------------------------------------------------------ low-level
def bm_to_object(bm, name, coll, faces_col=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def colour_faces(ob, fn, rng):
    C = hero.face_centres(ob)
    N = hero.face_normals(ob)
    cols = [fn(C[i], N[i], i, rng) for i in range(len(C))]
    hero.paint(ob, cols)
    return ob


def solid(c, rng=None, amt=0.035):
    c = rgb(c)
    return lambda p, n, i, r: jitter(c, r, amt)


def rigid_weights(ob, bone_weights: dict):
    hero.set_groups(ob, _dense(len(ob.data.vertices), bone_weights))


def _dense(n, bw):
    W = np.zeros((n, len(BONES)))
    for b, w in bw.items():
        W[:, BI[b]] = w
    return W


def copy_weights_from(ob, src_P, src_W):
    """Nearest-body-vertex weights for loose pieces (hair, beard, hems, pockets)."""
    P = hero.get_co(ob.data)
    idx = hero.nearest_idx(src_P, P)
    hero.set_groups(ob, src_W[idx])


def bvh_of(ob):
    me = ob.data
    P = hero.get_co(me)
    return BVHTree.FromPolygons([tuple(p) for p in P], [tuple(p.vertices) for p in me.polygons])


def surface_hit(bvh, origin, direction):
    loc, nor, idx, dist = bvh.ray_cast(Vector(origin), Vector(direction).normalized())
    return (np.array(loc), np.array(nor)) if loc is not None else (None, None)


def orient(z, y_hint=(0, 0, 1)):
    """Rotation matrix whose local Z is `z`."""
    z = Vector(z).normalized()
    y = Vector(y_hint)
    if abs(z.dot(y.normalized())) > 0.95:
        y = Vector((0, 1, 0)) if abs(z.y) < 0.9 else Vector((1, 0, 0))
    x = y.cross(z).normalized()
    y = z.cross(x).normalized()
    return Matrix((x, y, z)).transposed()


def add_geom(bm, verts, faces):
    vv = [bm.verts.new(Vector(v)) for v in verts]
    for f in faces:
        try:
            bm.faces.new([vv[i] for i in f])
        except ValueError:
            pass
    return vv


def cylinder(bm, p0, p1, r0, r1=None, segs=6, cap0=True, cap1=True, phase=0.0):
    r1 = r0 if r1 is None else r1
    p0, p1 = np.array(p0, float), np.array(p1, float)
    R = orient(p1 - p0)
    ring = []
    for k, (p, r) in enumerate(((p0, r0), (p1, r1))):
        for s in range(segs):
            a = phase + 2 * math.pi * s / segs
            ring.append(tuple(p + np.array(R @ Vector((math.cos(a) * r, math.sin(a) * r, 0)))))
    faces = [(s, (s + 1) % segs, segs + (s + 1) % segs, segs + s) for s in range(segs)]
    if cap0:
        faces.append(tuple(reversed(range(segs))))
    if cap1:
        faces.append(tuple(segs + s for s in range(segs)))
    return add_geom(bm, ring, faces)


def box(bm, centre, size, R=None):
    R = R or Matrix.Identity(3)
    sx, sy, sz = [s / 2 for s in size]
    corners = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
               (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    vs = [tuple(np.array(centre) + np.array(R @ Vector(c))) for c in corners]
    return add_geom(bm, vs, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])


def ellipsoid(bm, centre, radii, R=None, segs=8, rings=5):
    R = R or Matrix.Identity(3)
    verts, faces = [], []
    verts.append((0, 0, -1))
    for i in range(1, rings):
        th = math.pi * i / rings - math.pi / 2
        for s in range(segs):
            a = 2 * math.pi * s / segs
            verts.append((math.cos(th) * math.cos(a), math.cos(th) * math.sin(a), math.sin(th)))
    verts.append((0, 0, 1))
    top = len(verts) - 1
    for s in range(segs):
        faces.append((0, 1 + (s + 1) % segs, 1 + s))
    for i in range(rings - 2):
        b = 1 + i * segs
        for s in range(segs):
            faces.append((b + s, b + (s + 1) % segs, b + segs + (s + 1) % segs, b + segs + s))
    b = 1 + (rings - 2) * segs
    for s in range(segs):
        faces.append((b + s, b + (s + 1) % segs, top))
    vs = [tuple(np.array(centre) + np.array(R @ Vector((v[0] * radii[0], v[1] * radii[1], v[2] * radii[2])))) for v in verts]
    return add_geom(bm, vs, faces)


def torus(bm, centre, axis, R0, r, segs=16, sides=5, arc=2 * math.pi, start=0.0, closed=True):
    M = orient(axis)
    verts, faces = [], []
    n = segs if closed else segs + 1
    for i in range(n):
        a = start + arc * i / segs
        cdir = Vector((math.cos(a), math.sin(a), 0))
        for j in range(sides):
            b = 2 * math.pi * j / sides
            p = cdir * (R0 + r * math.cos(b)) + Vector((0, 0, r * math.sin(b)))
            verts.append(tuple(np.array(centre) + np.array(M @ p)))
    for i in range(segs if closed else segs):
        i2 = (i + 1) % n
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((i * sides + j, i2 * sides + j, i2 * sides + j2, i * sides + j2))
    return add_geom(bm, verts, faces)


def tube_path(bm, pts, r, sides=5, cap=True, radii=None):
    """Tube along a polyline (ropes, wire handles, ties, cane)."""
    pts = [np.array(p, float) for p in pts]
    verts, faces = [], []
    prev = None
    for k, p in enumerate(pts):
        t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)])
        R = orient(t, prev if prev is not None else (0, 0, 1))
        prev = tuple(R.col[1])
        rr = r if radii is None else radii[k]
        for j in range(sides):
            b = 2 * math.pi * j / sides
            verts.append(tuple(p + np.array(R @ Vector((math.cos(b) * rr, math.sin(b) * rr, 0)))))
    for k in range(len(pts) - 1):
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((k * sides + j, k * sides + j2, (k + 1) * sides + j2, (k + 1) * sides + j))
    if cap:
        faces.append(tuple(reversed(range(sides))))
        faces.append(tuple((len(pts) - 1) * sides + j for j in range(sides)))
    return add_geom(bm, verts, faces)


# ------------------------------------------------------------------ eyes
def eyes(info, coll, iris="#4A2E1E", rng=None):
    out = []
    for side in ("l", "r"):
        c, r = info["eyes"][side]
        bm = bmesh.new()
        segs, rings = 14, 8
        verts, faces = [], []
        # sphere whose pole points forward (-Y)
        for i in range(rings + 1):
            th = math.pi * i / rings
            for s in range(segs):
                a = 2 * math.pi * s / segs
                verts.append((math.sin(th) * math.cos(a) * r, -math.cos(th) * r, math.sin(th) * math.sin(a) * r))
        for i in range(rings):
            for s in range(segs):
                s2 = (s + 1) % segs
                faces.append((i * segs + s, i * segs + s2, (i + 1) * segs + s2, (i + 1) * segs + s))
        add_geom(bm, [tuple(np.array(v) + c) for v in verts], faces)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        ob = bm_to_object(bm, f"eye_{side}", coll)
        ic = rgb(iris)

        def col(p, n, i, rr, c=c, r=r, ic=ic):
            d = (p - c) / r
            ang = math.degrees(math.acos(max(-1, min(1, -d[1] / max(1e-6, np.linalg.norm(d))))))
            if ang < 15:
                return (0.03, 0.025, 0.02)
            if ang < 24:
                return ic
            if ang < 34:
                return mix(ic, (0.05, 0.04, 0.03), 0.55)     # limbal ring
            return (0.93, 0.91, 0.86)
        colour_faces(ob, col, rng)
        hero.assign(ob, hero.char_material_gloss())
        rigid_weights(ob, {"head": 1.0})
        out.append(ob)
    return out


# ------------------------------------------------------------------ clothing shells
def vertex_normals(ob):
    me = ob.data
    n = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("normal", n)
    return n.reshape(-1, 3)


def shell(body, name, face_sel, coll, offset=0.012, thick=0.006, colour=None, rng=None,
          smooth=0, flare=0.0, folds=0.0, fold_freq=38.0, extra=None, hide_body=True, keep_mask=None, rim_only=False, cuts=()):
    """Cut faces `face_sel(centre, normal, mean_weights) -> bool` from the body,
    inflate them by `offset` (+ extra(p) per vertex), add folds, flare the open
    edges (hems and rolled cuffs) and give the result real thickness."""
    me = body.data
    P = hero.get_co(me)
    N = vertex_normals(body)
    W = hero.read_groups(body)
    C = hero.face_centres(body)
    FN = hero.face_normals(body)
    polys = [tuple(p.vertices) for p in me.polygons]
    sel = [i for i, f in enumerate(polys) if face_sel(C[i], FN[i], W[list(f)].mean(axis=0))]
    if not sel:
        raise ValueError("empty shell " + name)
    used = sorted({v for i in sel for v in polys[i]})
    remap = {v: k for k, v in enumerate(used)}
    Pv = P[used].copy(); Nv = N[used].copy(); Wv = W[used].copy()
    F = [tuple(remap[v] for v in polys[i]) for i in sel]
    bm = bmesh.new()
    vs = [bm.verts.new(Vector(p)) for p in Pv]
    for f in F:
        try:
            bm.faces.new([vs[i] for i in f])
        except ValueError:
            pass
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    boundary = np.array([v.is_boundary for v in bm.verts])
    # smooth (fills between toes / fingers, softens a boot or mitten)
    for _ in range(smooth):
        newp = Pv.copy()
        for v in bm.verts:
            if v.link_edges:
                newp[v.index] = np.mean([Pv[e.other_vert(v).index] for e in v.link_edges], axis=0) * 0.6 + Pv[v.index] * 0.4
        Pv = newp
    off = np.full(len(Pv), offset)
    if extra is not None:
        off += np.array([extra(p) for p in Pv])
    if folds > 0:
        ph = rng.uniform(0, 6.28, 3)
        f = (np.sin(Pv[:, 2] * fold_freq + ph[0] + 3 * np.sin(Pv[:, 0] * 9 + ph[1])) *
             np.sin(Pv[:, 0] * fold_freq * 0.7 + Pv[:, 1] * 11 + ph[2]))
        off += folds * f
    off[boundary] += flare
    Pv = Pv + Nv * off[:, None]
    for v in bm.verts:
        v.co = Vector(Pv[v.index])
    ob = bm_to_object(bm, name, coll)
    hero.set_groups(ob, Wv)
    if cuts:
        apply_cuts(ob, cuts)
    if thick > 0:
        m = ob.modifiers.new("sol", "SOLIDIFY")
        m.thickness = thick; m.offset = -1.0; m.use_rim = True; m.use_even_offset = False
        m.use_rim_only = rim_only     # body-hugging layers: the inner face is never visible, keep only the thick hem edge
        dg = bpy.context.evaluated_depsgraph_get()
        nm = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        ob.modifiers.remove(m)
        old = ob.data; ob.data = nm; bpy.data.meshes.remove(old)
    if colour is not None:
        colour_faces(ob, colour, rng)
    hero.assign(ob)
    if hide_body:
        _hide_under(body, set(sel), polys, keep_mask)
    return ob


def apply_cuts(ob, cuts):
    """Clean straight hems: each cut is (point, normal, region(p) -> bool). Faces
    in the region are split by the plane and the part on the +normal side is
    removed. Vertex weights on the new edge are interpolated by bmesh."""
    for co, no, region in cuts:
        bm = bmesh.new(); bm.from_mesh(ob.data)
        faces = [f for f in bm.faces if region(np.array(f.calc_center_median()))]
        if not faces:
            bm.free(); continue
        geom = list({v for f in faces for v in f.verts}) + list({e for f in faces for e in f.edges}) + faces
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector(co), plane_no=Vector(no), clear_outer=True, dist=1e-5)
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(ob.data); bm.free()
    ob.data.update()


def _hide_under(body, sel, polys, keep_mask=None):
    """Mark body faces fully inside the clothed region for deletion (all
    neighbours of all their verts are covered)."""
    hid = body.get("_hide", set())
    hid = set(hid) if hid else set()
    vert_faces = {}
    for i, f in enumerate(polys):
        for v in f:
            vert_faces.setdefault(v, []).append(i)
    for i in sel:
        if all(all(j in sel for j in vert_faces[v]) for v in polys[i]):
            hid.add(i)
    body["_hide"] = list(hid)


def delete_hidden(body):
    hid = set(body.get("_hide", []))
    if not hid:
        return 0
    bm = bmesh.new(); bm.from_mesh(body.data)
    bm.faces.ensure_lookup_table()
    kill = [bm.faces[i] for i in hid]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(body.data); bm.free()
    body.data.update()
    return len(hid)


# ------------------------------------------------------------------ bands (belts, cuffs, hems, hat bands, wraps)
def band(bm, target_P, centre, axis, width, thick, clearance=0.003, segs=14, tilt=None, rmin=0.0, profile=None):
    """A closed ring with rectangular section hugging the points of target_P
    that lie in a slab of `width` around `centre` along `axis`."""
    c = np.array(centre, float); a = np.array(axis, float); a /= np.linalg.norm(a)
    R = orient(a)
    ex, ey = np.array(R.col[0]), np.array(R.col[1])
    d = target_P - c
    h = d @ a
    m = np.abs(h) < max(width, 0.01)
    if m.sum() > 6:                      # re-centre on the slab so the ring hugs what it wraps
        q0 = d[m] - np.outer(h[m], a)
        c = c + (q0.max(axis=0) + q0.min(axis=0)) / 2
        d = target_P - c
        h = d @ a
    q = d[m] - np.outer(h[m], a)
    ang = np.arctan2(q @ ey, q @ ex)
    rad = np.linalg.norm(q, axis=1)
    rs = []
    for s in range(segs):
        a0 = -math.pi + 2 * math.pi * s / segs
        dd = np.abs(((ang - a0 + math.pi) % (2 * math.pi)) - math.pi)
        k = dd < (math.pi / segs) * 1.6
        rs.append(max(rmin, rad[k].max() if k.any() else (rad.max() if len(rad) else rmin)))
    rs = np.array(rs)
    rs = (np.roll(rs, 1) + 2 * rs + np.roll(rs, -1)) / 4 + clearance
    if profile is not None:
        rs = rs * np.array([profile(-math.pi + 2 * math.pi * s / segs) for s in range(segs)])
    verts = []
    for s in range(segs):
        th = -math.pi + 2 * math.pi * s / segs
        dirv = math.cos(th) * ex + math.sin(th) * ey
        for (rr, hh) in ((rs[s], -width / 2), (rs[s] + thick, -width / 2), (rs[s] + thick, width / 2), (rs[s], width / 2)):
            verts.append(tuple(c + dirv * rr + a * hh))
    faces = []
    for s in range(segs):
        s2 = (s + 1) % segs
        for j in range(4):
            j2 = (j + 1) % 4
            faces.append((s * 4 + j, s2 * 4 + j, s2 * 4 + j2, s * 4 + j2))
    add_geom(bm, verts, faces)
    return rs


# ------------------------------------------------------------------ hair
def clumps(bm, roots, normals, length, radius, rng, droop=(0, 0, -1), droop_amt=0.3, sides=4, taper=0.15, curl=0.0):
    """Faceted hair clumps: one tapered prism per root, tips bent by `droop`."""
    dv = np.array(droop, float)
    for p, n in zip(roots, normals):
        n = np.array(n) / (np.linalg.norm(n) + 1e-9)
        L = length * rng.uniform(0.75, 1.25)
        rr = radius * rng.uniform(0.75, 1.2)
        d1 = n * (1 - droop_amt) + dv * droop_amt
        d1 /= np.linalg.norm(d1) + 1e-9
        mid = p + n * L * 0.45 + d1 * L * 0.15 + rng.normal(0, curl, 3)
        tip = p + d1 * L + rng.normal(0, curl + L * 0.06, 3)
        tube_path(bm, [p - n * rr * 0.5, mid, tip], rr, sides=sides, cap=False, radii=[rr, rr * 0.7, rr * taper])


def curls(bm, roots, normals, size, rng):
    """Tight curls: small faceted octahedra sitting on the scalp."""
    for p, n in zip(roots, normals):
        s = size * rng.uniform(0.75, 1.25)
        c = p + n * s * 0.55
        R = orient(n, tuple(rng.normal(0, 1, 3)))
        ellipsoid(bm, c, (s, s * 0.85, s * 0.7), R, segs=4, rings=2)


def scalp_points(body, info, test, density=1.0, rng=None):
    """Sample points (face centres + normals) of body faces satisfying test(d, p)
    where d is the unit direction from the head centre."""
    C = hero.face_centres(body); N = hero.face_normals(body)
    W = hero.read_groups(body)
    hc = info["head_c"]
    pts, nrm = [], []
    polys = body.data.polygons
    for i, p in enumerate(polys):
        w = W[list(p.vertices)].mean(axis=0)
        if w[BI["head"]] + w[BI["neck_01"]] < 0.6:
            continue
        d = C[i] - hc; d = d / (np.linalg.norm(d) + 1e-9)
        if test(d, C[i]) and rng.random() < density:
            pts.append(C[i]); nrm.append(N[i])
    return np.array(pts), np.array(nrm)
