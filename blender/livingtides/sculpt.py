"""Sculpted island rock (needs bpy).

The height-field terrain of session 3 could not undercut, overhang or hold a
cave.  Here the island is built the way a modeller would block it out and
then carved with Blender's own tools:

  1. every surveyed land level becomes a lofted rock mass whose outline swells
     and overhangs with height (never into a walk link, plot, deck or stair),
  2. boulders, buttresses and The Gate are added as volumes,
  3. everything is fused with a voxel remesh into one skin,
  4. sea caves and recesses are cut with booleans,
  5. faces are pushed into strata ledges and weathered in numpy,
  6. walkable tops are snapped back to the exact surveyed height,
  7. the result is decimated to a faceted low-poly mesh and painted by
     height / slope / strata into the vertex colour attribute.
"""
from __future__ import annotations
import math
import bpy, bmesh
import numpy as np
from mathutils.bvhtree import BVHTree
from mathutils import Vector
from .geom import Mesh, T, Rz, rng_for
from . import bl_io, palette, environment as E
from .world import pt_in_poly, ground_h

VOXEL = 0.3


def _densify(poly, step=0.6):
    out = []
    n = len(poly)
    for i in range(n):
        ax, az = poly[i]; bx, bz = poly[(i + 1) % n]
        k = max(1, int(math.hypot(bx - ax, bz - az) / step))
        for j in range(k):
            out.append((ax + (bx - ax) * j / k, az + (bz - az) * j / k))
    return out


def _level_mass(l, li, ter, L):
    """Lofted rock mass for one land polygon (layout x,z; Blender out)."""
    pts = _densify(l["poly"])
    n = len(pts)
    h = l["h"]
    low = l["id"] in ("T1", "SP")
    # outward normals
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    sgn = 1.0 if area > 0 else -1.0
    nrm, lim, bul = [], [], []
    for i in range(n):
        ax, az = pts[i - 1]; bx, bz = pts[(i + 1) % n]
        tx, tz = bx - ax, bz - az
        d = math.hypot(tx, tz) or 1.0
        nx, nz = sgn * tz / d, -sgn * tx / d
        nrm.append((nx, nz))
        # how far may the rock swell here before it reaches something walkable
        free = 0.0
        while free < 4.5 and not ter.is_keep(pts[i][0] + nx * (free + 0.45), pts[i][1] + nz * (free + 0.45)):
            free += 0.25
        lim.append(max(0.0, free - 0.25))
        x, z = pts[i]
        b = (0.35 if low else 1.7) * (0.5 + 0.5 * float(E.n2(x * 1.3, z * 1.3, 3.0 + li))) \
            + (0.0 if low else 1.9) * max(0.0, float(E.n2(x * 0.45, z * 0.45, 9.0 + li * 2)))
        bul.append(b)
    # smooth, then clamp to clearance
    sm = [(bul[i - 2] + 2 * bul[i - 1] + 3 * bul[i] + 2 * bul[(i + 1) % n] + bul[(i + 2) % n]) / 9 for i in range(n)]
    off = [min(sm[i], lim[i]) for i in range(n)]
    m = Mesh("mass_" + l["id"])
    if l["id"] == "SP":
        prof = [(-4.0, 3.2), (-0.4, 2.2), (0.3, 1.0), (h - 0.05, 0.25), (h, 0.0)]          # shelving beach
        add = True
    elif low:
        prof = [(-4.0, 0.15), (h - 0.5, 0.15), (h - 0.2, 0.45), (h, 0.4)]
        add = True
    else:
        # z, bulge factor, extra metres: eroded notch low down, belly, overhanging lip
        prof = [(-4.0, 0.2, -0.3), (0.2, 0.2, -0.9), (1.4, 0.45, -0.5), (h * 0.45, 0.75, 0.0), (h - 2.6, 1.0, 0.15),
                (h - 0.9, 1.0, 0.55), (h - 0.3, 1.0, 0.7), (h, 0.95, 0.55)]
        add = False
    rings = []
    for p in prof:
        ring = []
        for i in range(n):
            if add:
                o = off[i] * 0.0 + min(p[1] + off[i] * (1.0 if p[0] > 0 else 0.3), lim[i] + (p[1] if p[0] < 0.3 else 0.0))
            else:
                o = off[i] * p[1] + (p[2] if lim[i] > 0.9 or p[2] < 0 else min(p[2], lim[i] * 0.5))
                o = min(o, lim[i] + 0.0) if p[0] > 1.4 else o
            ring.append((pts[i][0] + nrm[i][0] * o, -(pts[i][1] + nrm[i][1] * o), p[0]))
        rings.append(ring)
    base = 0
    for ring in rings:
        m.v.extend(ring)
    k = len(rings)
    for r in range(k - 1):
        for i in range(n):
            j = (i + 1) % n
            m.f.append((r * n + i, r * n + j, (r + 1) * n + j, (r + 1) * n + i)); m.fm.append("rock_m"); m.ft.append(1.0)
    m.f.append(tuple(range(n - 1, -1, -1))); m.fm.append("rock_m"); m.ft.append(1.0)
    m.f.append(tuple((k - 1) * n + i for i in range(n))); m.fm.append("rock_m"); m.ft.append(1.0)
    return m


CAVES = [  # layout x, y, z, radii (x, y, z), yaw - sea caves and recesses, all under high ground
    (-44.5, 0.6, -2.0, (5.5, 2.6, 3.4), 0.3), (-41.0, 0.4, 12.5, (4.8, 2.3, 3.0), -0.5), (-31.0, 0.5, 22.3, (3.6, 2.1, 2.6), 0.9),
    (41.5, 0.5, -7.5, (4.2, 2.6, 3.2), 0.2), (35.5, 0.4, -15.5, (3.6, 2.2, 3.4), 1.3), (39.5, 0.6, 17.5, (2.8, 2.2, 2.4), 0.6),
    (-20.0, 0.5, -34.5, (4.6, 2.4, 3.0), 1.5), (10.5, 0.5, -27.5, (4.0, 2.3, 3.2), 1.2),
    (-9.0, 7.3, -5.8, (2.1, 1.3, 1.5), 1.5), (24.0, 2.6, -7.0, (2.6, 1.6, 2.0), 1.4),
]


def build_island(L, ter, log=None):
    rng = rng_for("island")
    coll = bl_io.collection("CLIFFS")
    objs = []
    for li, l in enumerate(L["land"]):
        objs.append(bl_io.to_object(_level_mass(l, li, ter, L), coll))
    objs.append(bl_io.to_object(E.cliffs(L, ter), coll))
    objs.append(bl_io.to_object(E.gate(L, ter), coll))
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = "LT_ISLAND"; ob.data.name = "LT_ISLAND"
    md = ob.modifiers.new("fuse", "REMESH"); md.mode = "VOXEL"; md.voxel_size = VOXEL
    bpy.ops.object.modifier_apply(modifier=md.name)
    # ---- caves
    cm = Mesh("caves")
    for (x, y, z, r, yaw) in CAVES:
        with cm.push(T(x, -z, y), Rz(yaw)):
            cm.blob(r[0], r[2], r[1], "rock_d", rng, sub=2, rough=0.16)
    # clearance boxes: ramps down to the decks and the ladder need headroom through the lip
    nodes_ = L["nav"]["nodes"]
    for e in L["nav"]["edges"]:
        if e["type"] in ("ramp", "ladder"):
            a_, b_ = nodes_[e["a"]], nodes_[e["b"]]
            k_ = 0.6 if e["type"] == "ladder" else 1.0          # the ladder top lands on the terrace: do not cut that
            bx_, by_, bz_ = (a_[q] + (b_[q] - a_[q]) * k_ for q in ("x", "y", "z"))
            cm.beam((a_["x"], -a_["z"], a_["y"] + 1.12), (bx_, -bz_, by_ + 1.12), 1.5, 2.2, "rock_d")
    cave = bl_io.to_object(cm, coll)
    bm_ = ob.modifiers.new("caves", "BOOLEAN"); bm_.operation = "DIFFERENCE"; bm_.object = cave; bm_.solver = "EXACT"
    bpy.ops.object.modifier_apply(modifier=bm_.name)
    bpy.data.objects.remove(cave, do_unlink=True)
    me = ob.data
    # ---- weathering in numpy
    me.calc_loop_triangles()
    nv = len(me.vertices)
    co = np.empty(nv * 3); no = np.empty(nv * 3)
    me.vertices.foreach_get("co", co); me.vertices.foreach_get("normal", no)
    co = co.reshape(-1, 3); no = no.reshape(-1, 3)
    x, yb, z = co[:, 0], co[:, 1], co[:, 2]
    zl = -yb                                         # layout z
    levels = sorted({l["h"] for l in L["land"]} | {L["arch"]["y1"]})
    flat = np.zeros(nv, bool)
    for h in levels:
        flat |= (np.abs(z - h) < VOXEL * 0.75) & (no[:, 2] > 0.6)
    face = (~flat) & (no[:, 2] < 0.75)
    # strata: ledges step in and out with height, the bedding dips gently
    bed = z + 0.10 * x * 0.12 + 0.35 * E.n2(x * 0.35, zl * 0.35, 4.0)
    # beds of uneven thickness (about 1.6 - 3 m): a few strong ledges, not a comb
    bedw = bed / 2.3 + 0.35 * np.sin(bed * 0.55 + 1.3)
    ph = bedw % 1.0
    step = np.where(ph < 0.72, 0.07, -0.16) + 0.04 * np.sin(bed * 5.0)
    big = 0.45 * E.n2(x * 0.55 + z * 0.4, zl * 0.55 - z * 0.3, 12.0) + 0.22 * E.n2(x * 1.9, zl * 1.9 + z * 1.4, 17.0)
    # vertical chimneys / joints
    joint = -0.55 * np.clip(np.sin((x * 0.9 + zl * 0.7) + 2.0 * E.n2(x * 0.2, zl * 0.2, 21.0)) - 0.86, 0, 1) / 0.14
    d = (step + big + joint) * face
    hn = no.copy(); hn[:, 2] *= 0.25
    ln = np.linalg.norm(hn, axis=1, keepdims=True); hn = hn / np.maximum(ln, 1e-6)
    # never push rock into a walkable zone
    gi = np.clip(np.round(((x + hn[:, 0] * 0.9) - ter.xs[0]) / ter.cell).astype(int), 0, len(ter.xs) - 1)
    gj = np.clip(np.round(((zl - hn[:, 1] * 0.9) - ter.zs[0]) / ter.cell).astype(int), 0, len(ter.zs) - 1)
    near_keep = ter.keep[gj, gi]
    d = np.where(near_keep, np.minimum(d, 0.0), d)
    co += hn * d[:, None]
    # ---- snap walkable tops to the surveyed height
    for h in levels:
        sel = flat & (np.abs(co[:, 2] - h) < VOXEL * 0.75)
        co[sel, 2] = h
    me.vertices.foreach_set("co", co.ravel()); me.update()
    md = ob.modifiers.new("lowpoly", "DECIMATE"); md.ratio = 0.085; md.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=md.name)
    me = ob.data
    # second snap: decimation may have nudged walkable ground
    nv = len(me.vertices)
    co = np.empty(nv * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    gi = np.clip(np.round((co[:, 0] - ter.xs[0]) / ter.cell).astype(int), 0, len(ter.xs) - 1)
    gj = np.clip(np.round((-co[:, 1] - ter.zs[0]) / ter.cell).astype(int), 0, len(ter.zs) - 1)
    dat = ter.data[gj, gi]
    sel = ter.keep[gj, gi] & ~np.isnan(dat) & (np.abs(co[:, 2] - np.nan_to_num(dat, nan=-99)) < 0.3)
    co[sel, 2] = dat[sel]
    me.vertices.foreach_set("co", co.ravel()); me.update()
    for p in me.polygons:
        p.use_smooth = False
    # ---- paint
    me.materials.clear()
    me.materials.append(bl_io.material("LT_matte"))
    attr = me.color_attributes.get("Col") or me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
    cols = np.empty((len(me.loops), 4), np.float32)
    lin = {r: palette.srgb_to_linear(palette.resolve(r)) for r in
           ("rock_l", "rock_m", "rock_d", "rock_wet", "ground", "grass", "sand", "rock_cave")}
    li = 0
    counts = {}
    for p in me.polygons:
        c = p.center; n = p.normal
        lx, lz = c.x, -c.y
        g = ground_h(L, lx, lz)
        if n.z > 0.72:
            if c.z < 0.25: role = "rock_wet"
            elif c.z < 1.35 and g is None: role = "sand"
            elif g is not None and abs(c.z - g) < 0.3:
                gn = float(E.n2(lx * 0.9, lz * 0.9, 11.0)) + (0.3 if c.z > 9 else -0.1)
                role = "grass" if (gn > 0.25 and not ter.is_keep(lx, lz)) else "ground"
            else:
                role = "grass" if float(E.n2(lx * 0.8, lz * 0.8 + c.z * 0.6, 5.0)) > 0.42 else "rock_l"    # only the odd ledge is green
        else:
            bedc = c.z + 0.012 * lx + 0.35 * float(E.n2(lx * 0.35, lz * 0.35, 4.0))
            band = int(math.floor(bedc / 2.3 + 0.35 * math.sin(bedc * 0.55 + 1.3))) % 4
            role = ("rock_m", "rock_l", "rock_m", "rock_m")[band]
            if n.z > 0.35 and float(E.n2(lx * 1.7, lz * 1.7, 8.0)) > 0.3: role = "rock_l"      # sun-bleached shoulders
            if n.z < -0.3: role = "rock_d"
            if c.z < 0.35: role = "rock_wet"
        for (cx, cy, cz, r, yaw) in CAVES:
            if (lx - cx) ** 2 / (r[0] * 0.92) ** 2 + (c.z - cy) ** 2 / (r[1] * 0.92) ** 2 + (lz - cz) ** 2 / (r[2] * 0.92) ** 2 < 1.0:
                role = "rock_cave"
        counts[role] = counts.get(role, 0) + 1
        t = 1.0 + rng.uniform(-0.07, 0.07)
        r_, g_, b_ = lin[role]
        for _ in p.loop_indices:
            cols[li] = (r_ * t, g_ * t, b_ * t, 1.0); li += 1
    attr.data.foreach_set("color", cols.ravel())
    me.color_attributes.active_color = attr
    me.validate(); me.update()
    # ---- verify against the walk graph by ray casting
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(ob, dg)
    nodes = L["nav"]["nodes"]
    off, buried = [], []
    for k, nd in nodes.items():
        if nd["kind"] != "ground":
            continue
        hit = bvh.ray_cast(Vector((nd["x"], -nd["z"], nd["y"] + 3.0)), Vector((0, 0, -1)))
        if hit[0] is None or abs(hit[0].z - nd["y"]) > 0.06:
            off.append((k, nd["y"], None if hit[0] is None else round(hit[0].z, 2)))
    for e in L["nav"]["edges"]:
        a, b = nodes[e["a"]], nodes[e["b"]]
        if "water" in (a["kind"], b["kind"]) or e["type"] == "ladder":
            continue        # the surveyed ladder leans 0.5 m into the terrace edge by design
        for s in range(1, 10):
            u = s / 10
            px, pz, py = a["x"] + (b["x"] - a["x"]) * u, a["z"] + (b["z"] - a["z"]) * u, a["y"] + (b["y"] - a["y"]) * u
            hit = bvh.ray_cast(Vector((px, -pz, py + 1.9)), Vector((0, 0, -1)))
            if hit[0] is not None and hit[0].z > py + 0.15:
                buried.append((e["a"], e["b"], round(hit[0].z - py, 2))); break
    if log is not None:
        log["island"] = dict(tris=len(me.polygons), paint=counts, caves=len(CAVES),
                             ground_nodes_off_height=off, links_buried=buried)
    return ob


def seabed(L):
    m = Mesh("LT_SEABED")
    rng = rng_for("seabed")
    s = 3.0
    xs = np.arange(-75, 75 + 1e-6, s); zs = np.arange(-60, 57 + 1e-6, s)
    P = {}
    for j, z in enumerate(zs):
        for i, x in enumerate(xs):
            P[(i, j)] = (x + rng.uniform(-0.8, 0.8), -(z + rng.uniform(-0.8, 0.8)), E.SEABED - 0.4 + 0.5 * float(E.n2(x * 0.6, z * 0.6, 2.0)))
    for j in range(len(zs) - 1):
        for i in range(len(xs) - 1):
            a, b, c, d = P[(i, j)], P[(i + 1, j)], P[(i + 1, j + 1)], P[(i, j + 1)]
            base = len(m.v); m.v.extend([a, b, c, d])
            for tri in ((0, 3, 2), (0, 2, 1)):
                m.f.append(tuple(base + q for q in tri)); m.fm.append("seabed"); m.ft.append(1.0 + rng.uniform(-0.08, 0.08))
    return m
