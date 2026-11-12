"""Faceted low-poly wildlife for Saltcrown: the 12 species the Ecosystem
simulates (WILDLIFE_BEHAVIOR.md). Each model is built from lofted cross
sections (body), flat extruded outlines (wings, fins, flukes, flippers) and
tubes (legs, beaks). Real-world lengths are kept in metres.

Local frame: animal faces +X, up is +Z, origin at the animal's centre on the
ground / waterline. Colours are per-face vertex colours (attribute `Col`)."""
from __future__ import annotations
import math
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix
from .characters import garments as G
from .characters import hero


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


# ------------------------------------------------------------------ primitives
def loft(bm, sections, segs=10, cap=True):
    """sections: [(x, half_width_y, half_height_z, centre_z)] head->tail or tail->head.
    Returns (rings, verts)."""
    verts, faces = [], []
    n = len(sections)
    for (x, ry, rz, cz) in sections:
        for s in range(segs):
            a = 2 * math.pi * s / segs
            verts.append((x, math.cos(a) * ry, cz + math.sin(a) * rz))
    for i in range(n - 1):
        for s in range(segs):
            s2 = (s + 1) % segs
            faces.append((i * segs + s, i * segs + s2, (i + 1) * segs + s2, (i + 1) * segs + s))
    if cap:
        x0, _, _, c0 = sections[0]; x1, _, _, c1 = sections[-1]
        verts.append((x0 - 0.001, 0, c0)); a0 = len(verts) - 1
        verts.append((x1 + 0.001, 0, c1)); a1 = len(verts) - 1
        for s in range(segs):
            s2 = (s + 1) % segs
            faces.append((a0, s2, s))
            faces.append((a1, (n - 1) * segs + s, (n - 1) * segs + s2))
    G.add_geom(bm, verts, faces)


def plate(bm, outline, thick, z=0.0, plane="xy", bend=None):
    """Flat extruded polygon (wing, fin, fluke). outline: [(u, v)] in order.
    plane 'xy' = horizontal (wings, flukes), 'xz' = vertical (dorsal, tail fins).
    bend(u, v) -> extra z (or y) offset to curve the plate."""
    top, bot = [], []
    for (u, v) in outline:
        e = bend(u, v) if bend else 0.0
        if plane == "xy":
            top.append((u, v, z + e + thick / 2)); bot.append((u, v, z + e - thick / 2))
        else:
            top.append((u, e + thick / 2, v)); bot.append((u, e - thick / 2, v))
    n = len(outline)
    verts = top + bot
    faces = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
    for i in range(n):
        i2 = (i + 1) % n
        faces.append((i, n + i, n + i2, i2))
    vs = G.add_geom(bm, verts, [])
    # triangulate the caps as fans so concave outlines stay valid
    for cap in (list(range(n)), list(reversed(range(n, 2 * n)))):
        for k in range(1, n - 1):
            try:
                bm.faces.new([vs[cap[0]], vs[cap[k]], vs[cap[k + 1]]])
            except ValueError:
                pass
    for i in range(n):
        i2 = (i + 1) % n
        try:
            bm.faces.new([vs[i], vs[n + i], vs[n + i2], vs[i2]])
        except ValueError:
            pass


def mirror_y(bm, geom_verts):
    pass


def finish(bm, name, coll, colour, rng):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = G.bm_to_object(bm, name, coll)
    G.colour_faces(ob, colour, rng)
    hero.assign(ob)
    return ob


def jit(c, r, a=0.04):
    f = 1 + r.uniform(-a, a)
    return tuple(min(1, max(0, x * f)) for x in c)


def wing(bm, side, root_x, span, chord, z, tip_back=0.3, sweep=0.0, dihedral=0.08, thick=0.012, fingers=0, slender=1.0):
    """Bird wing outline from the shoulder out to the tip (side = +1 / -1)."""
    s = side
    pts = [(root_x + chord * 0.35, 0.0), (root_x + chord * 0.45 - sweep * 0.3, s * span * 0.45),
           (root_x + chord * 0.2 - sweep, s * span * 0.85), (root_x - tip_back * chord - sweep * 1.4, s * span)]
    if fingers:
        for k in range(fingers):
            t = k / max(1, fingers - 1)
            pts.append((root_x - tip_back * chord - sweep * 1.4 - 0.1 * chord - t * 0.25 * chord, s * span * (0.98 - 0.04 * k)))
            pts.append((root_x - tip_back * chord - sweep * 1.2 - 0.18 * chord - t * 0.25 * chord, s * span * (0.9 - 0.04 * k)))
    pts += [(root_x - chord * 0.7 * slender - sweep * 0.8, s * span * 0.6), (root_x - chord * 0.65, s * span * 0.25), (root_x - chord * 0.55, 0.0)]
    if s < 0:
        pts = list(reversed(pts))
    plate(bm, pts, thick, z, "xy", bend=lambda u, v: abs(v) * dihedral + 0.04 * span * math.sin(min(1, abs(v) / span) * math.pi) * 0.5)


# ------------------------------------------------------------------ species
def gull(coll, rng):
    bm = bmesh.new()
    loft(bm, [(-0.2, 0.015, 0.015, 0.0), (-0.12, 0.05, 0.045, 0.0), (0.0, 0.065, 0.06, 0.005), (0.1, 0.055, 0.055, 0.015),
              (0.16, 0.035, 0.04, 0.04), (0.2, 0.03, 0.035, 0.055), (0.24, 0.022, 0.025, 0.055)], segs=8)
    G.cylinder(bm, (0.24, 0, 0.052), (0.3, 0, 0.045), 0.01, 0.003, segs=5)                       # beak
    for s in (1, -1):
        wing(bm, s, 0.02, 0.62, 0.2, 0.03, tip_back=0.6, sweep=0.06, dihedral=0.05)
    plate(bm, [(-0.18, 0.0), (-0.26, 0.06), (-0.3, 0.0), (-0.26, -0.06)], 0.008, 0.0)              # tail
    gw, gr, bk = hexc("#F4F3EE"), hexc("#A7AEB8"), hexc("#1E1E22")

    def col(p, n, i, r):
        if p[0] > 0.24:
            return (0.95, 0.78, 0.2)
        if abs(p[1]) > 0.5:
            return jit(bk, r)
        if abs(p[1]) > 0.07 and n[2] > -0.3:
            return jit(gr, r)
        return jit(gw, r, 0.02)
    return finish(bm, "gull", coll, col, rng), "Laughing gull", 1.3, 0.42


def pelican(coll, rng):
    bm = bmesh.new()
    loft(bm, [(-0.45, 0.03, 0.03, 0.0), (-0.3, 0.12, 0.11, 0.0), (-0.05, 0.15, 0.13, 0.01), (0.15, 0.1, 0.1, 0.05),
              (0.25, 0.05, 0.05, 0.12), (0.32, 0.04, 0.04, 0.15), (0.38, 0.045, 0.05, 0.16), (0.45, 0.03, 0.035, 0.16)], segs=8)
    # long bill + pouch
    loft(bm, [(0.44, 0.022, 0.012, 0.165), (0.6, 0.02, 0.01, 0.15), (0.76, 0.015, 0.008, 0.13), (0.8, 0.006, 0.006, 0.12)], segs=6)
    loft(bm, [(0.46, 0.018, 0.02, 0.135), (0.58, 0.024, 0.04, 0.115), (0.72, 0.016, 0.025, 0.11), (0.77, 0.006, 0.006, 0.115)], segs=6)
    for s in (1, -1):
        wing(bm, s, 0.0, 1.05, 0.38, 0.06, tip_back=0.35, sweep=0.04, dihedral=0.03, fingers=4)
    plate(bm, [(-0.42, 0.0), (-0.55, 0.09), (-0.6, 0.0), (-0.55, -0.09)], 0.01, 0.0)
    br, gr, wh, dk = hexc("#6B5A4A"), hexc("#9A8F84"), hexc("#EFE6D2"), hexc("#3A322C")

    def col(p, n, i, r):
        if p[0] > 0.44:
            return jit((0.82, 0.62, 0.42) if p[2] > 0.13 else (0.62, 0.45, 0.33), r)
        if p[0] > 0.3 and p[2] > 0.12:
            return jit(wh if p[2] > 0.18 else (0.92, 0.85, 0.55), r)
        if abs(p[1]) > 0.65:
            return jit(dk, r)
        if abs(p[1]) > 0.14:
            return jit(gr if n[2] > 0 else br, r)
        return jit(br, r)
    return finish(bm, "pelican", coll, col, rng), "Brown pelican", 1.3, 2.1


def tern(coll, rng):
    bm = bmesh.new()
    loft(bm, [(-0.14, 0.012, 0.012, 0.0), (-0.08, 0.035, 0.03, 0.0), (0.02, 0.04, 0.038, 0.004), (0.1, 0.03, 0.032, 0.015),
              (0.14, 0.022, 0.024, 0.025), (0.17, 0.016, 0.017, 0.028)], segs=8)
    G.cylinder(bm, (0.17, 0, 0.027), (0.24, 0, 0.022), 0.008, 0.002, segs=5)
    for s in (1, -1):
        wing(bm, s, 0.01, 0.42, 0.13, 0.02, tip_back=0.9, sweep=0.08, dihedral=0.1, slender=0.8, thick=0.008)
    plate(bm, [(-0.12, 0.0), (-0.2, 0.03), (-0.3, 0.07), (-0.22, 0.0), (-0.3, -0.07), (-0.2, -0.03)], 0.006, 0.0)   # forked tail
    wh, gr, bk = hexc("#F7F6F2"), hexc("#C8CDD3"), hexc("#151517")

    def col(p, n, i, r):
        if p[0] > 0.17:
            return (0.95, 0.55, 0.12)
        if p[0] > 0.1 and p[2] > 0.025:
            return jit(bk, r)
        if abs(p[1]) > 0.05 and n[2] > -0.2:
            return jit(gr, r)
        return jit(wh, r, 0.02)
    return finish(bm, "tern", coll, col, rng), "Royal tern", 0.9, 0.48


def frigatebird(coll, rng):
    bm = bmesh.new()
    loft(bm, [(-0.25, 0.015, 0.015, 0.0), (-0.12, 0.05, 0.045, 0.0), (0.02, 0.06, 0.055, 0.004), (0.12, 0.045, 0.045, 0.02),
              (0.18, 0.03, 0.03, 0.04), (0.23, 0.025, 0.026, 0.045)], segs=8)
    loft(bm, [(0.06, 0.03, 0.04, -0.03), (0.12, 0.045, 0.07, -0.05), (0.17, 0.02, 0.03, -0.01)], segs=7)       # red throat pouch
    G.cylinder(bm, (0.23, 0, 0.045), (0.36, 0, 0.035), 0.01, 0.004, segs=5)
    for s in (1, -1):
        wing(bm, s, 0.02, 1.1, 0.22, 0.03, tip_back=1.3, sweep=0.12, dihedral=-0.02, slender=0.9, thick=0.01)
    plate(bm, [(-0.22, 0.0), (-0.4, 0.05), (-0.62, 0.11), (-0.42, 0.0), (-0.62, -0.11), (-0.4, -0.05)], 0.008, 0.0)
    bk = hexc("#17171C")

    def col(p, n, i, r):
        if p[2] < -0.015 and 0.04 < p[0] < 0.19:
            return jit((0.86, 0.12, 0.1), r)
        if p[0] > 0.23:
            return (0.55, 0.55, 0.58)
        return jit(bk if n[2] > -0.2 else (0.12, 0.11, 0.14), r, 0.08)
    return finish(bm, "frigatebird", coll, col, rng), "Magnificent frigatebird", 1.9, 2.3


def sandpiper(coll, rng):
    bm = bmesh.new()
    h = 0.075
    loft(bm, [(-0.09, 0.01, 0.01, h + 0.01), (-0.05, 0.03, 0.028, h + 0.01), (0.02, 0.035, 0.033, h + 0.012), (0.07, 0.025, 0.026, h + 0.03),
              (0.095, 0.019, 0.02, h + 0.045), (0.11, 0.012, 0.014, h + 0.046)], segs=8)
    G.cylinder(bm, (0.11, 0, h + 0.045), (0.16, 0, h + 0.034), 0.004, 0.0015, segs=4)
    for s in (1, -1):
        G.tube_path(bm, [(0.0, s * 0.012, h - 0.01), (-0.008, s * 0.013, h * 0.45), (0.004, s * 0.014, 0.0)], 0.0028, sides=4)
        G.add_geom(bm, [(0.004, s * 0.014, 0.001), (0.03, s * 0.022, 0.001), (0.028, s * 0.008, 0.001)], [(0, 1, 2)])
    br, wh = hexc("#8C7A62"), hexc("#F2EEE4")

    def col(p, n, i, r):
        if p[2] < h - 0.005 or p[0] > 0.11:
            return (0.15, 0.14, 0.13)
        if n[2] < -0.2:
            return jit(wh, r, 0.02)
        return jit(br if (int(p[0] * 300) + int(p[1] * 300)) % 3 else (0.4, 0.33, 0.25), r, 0.06)
    return finish(bm, "sandpiper", coll, col, rng), "Spotted sandpiper", 0.19, 0.2


def fish_body(bm, L, depth, width, tail_fork=0.35, dorsal=None, segs=8, jaw=0.0):
    x0 = -L / 2
    S = []
    prof = [(0.0, 0.05, 0.08), (0.08, 0.45, 0.55), (0.25, 0.85, 0.95), (0.45, 1.0, 1.0), (0.65, 0.8, 0.8), (0.82, 0.4, 0.38), (0.9, 0.16, 0.18)]
    for t, w, d in reversed(prof):
        S.append((x0 + L * (1 - t), width / 2 * w, depth / 2 * d, 0.0))
    loft(bm, S, segs=segs)
    tx = x0 + L * 0.1
    plate(bm, [(tx + 0.02 * L, 0.0), (x0 - L * 0.06, depth * 0.55), (x0 - L * 0.02 + L * tail_fork * 0.15, 0.0),
               (x0 - L * 0.06, -depth * 0.55)], width * 0.08, 0.0, "xz")
    if dorsal:
        for (a, b, hgt) in dorsal:
            plate(bm, [(x0 + L * a, depth * 0.42), (x0 + L * (a + b) * 0.5 + L * 0.03, depth * 0.42 + hgt * depth), (x0 + L * b, depth * 0.4)],
                  width * 0.06, 0.0, "xz")
    plate(bm, [(x0 + L * 0.3, -depth * 0.38), (x0 + L * 0.22, -depth * 0.6), (x0 + L * 0.36, -depth * 0.4)], width * 0.05, 0.0, "xz")  # anal
    for s in (1, -1):                                                                                                                   # pectorals
        plate(bm, [(x0 + L * 0.72, s * width * 0.45), (x0 + L * 0.6, s * width * 0.95), (x0 + L * 0.66, s * width * 0.5)], 0.002, -depth * 0.1)
    # eye
    for s in (1, -1):
        G.ellipsoid(bm, (x0 + L * 0.86, s * width * 0.3, depth * 0.12), (L * 0.025, width * 0.06, L * 0.025), segs=6, rings=3)


def scad(coll, rng):
    bm = bmesh.new(); L = 0.25
    fish_body(bm, L, 0.06, 0.032, dorsal=[(0.45, 0.62, 0.5), (0.18, 0.42, 0.25)])
    def col(p, n, i, r):
        if abs(p[1]) > 0.012 and p[0] > L * 0.35 and abs(p[2] - 0.007) < 0.006:
            return (0.05, 0.05, 0.06)
        if abs(p[2]) < 0.004:
            return jit((0.95, 0.82, 0.3), r)
        return jit((0.3, 0.45, 0.6) if p[2] > 0 else (0.85, 0.88, 0.9), r, 0.05)
    return finish(bm, "scad", coll, col, rng), "Bigeye scad (school)", 0.25, 0.25


def snapper(coll, rng):
    bm = bmesh.new(); L = 0.45
    fish_body(bm, L, 0.16, 0.06, dorsal=[(0.25, 0.7, 0.35)])
    def col(p, n, i, r):
        if abs(p[1]) > 0.02 and p[0] > L * 0.36:
            return (0.05, 0.05, 0.06)
        return jit((0.88, 0.32, 0.3) if p[2] > -0.02 else (0.96, 0.66, 0.62), r, 0.05)
    return finish(bm, "snapper", coll, col, rng), "Red snapper", 0.45, 0.45


def mackerel(coll, rng):
    bm = bmesh.new(); L = 0.5
    fish_body(bm, L, 0.09, 0.055, tail_fork=0.6, dorsal=[(0.55, 0.7, 0.45), (0.2, 0.4, 0.25)])
    def col(p, n, i, r):
        if abs(p[1]) > 0.01 and p[0] > L * 0.36:
            return (0.05, 0.05, 0.06)
        if p[2] > 0.0:
            return jit((0.18, 0.45, 0.48) if int(p[0] * 40 + p[2] * 60) % 2 else (0.08, 0.18, 0.25), r, 0.05)
        return jit((0.88, 0.9, 0.86), r, 0.04)
    return finish(bm, "mackerel", coll, col, rng), "King mackerel", 0.5, 0.5


def barracuda(coll, rng):
    bm = bmesh.new(); L = 1.4
    fish_body(bm, L, 0.16, 0.11, tail_fork=0.5, dorsal=[(0.55, 0.65, 0.5), (0.18, 0.27, 0.45)], segs=8)
    # underbite jaw
    G.cylinder(bm, (L * 0.43, 0, -0.03), (L * 0.53, 0, -0.025), 0.022, 0.006, segs=5)
    def col(p, n, i, r):
        if abs(p[1]) > 0.03 and p[0] > L * 0.36 and p[0] < L * 0.42:
            return (0.05, 0.05, 0.06)
        if p[2] > 0.025 and int((p[0] + 2) * 9) % 2 == 0 and p[0] < L * 0.3:
            return jit((0.2, 0.24, 0.27), r)
        return jit((0.48, 0.55, 0.6) if p[2] > 0 else (0.86, 0.88, 0.88), r, 0.05)
    return finish(bm, "barracuda", coll, col, rng), "Great barracuda", 1.4, 1.4


def dolphin(coll, rng):
    bm = bmesh.new()
    S = [(-1.25, 0.03, 0.03, 0.02), (-1.05, 0.08, 0.1, 0.02), (-0.6, 0.2, 0.22, 0.0), (-0.1, 0.27, 0.3, 0.0), (0.35, 0.25, 0.28, 0.0),
         (0.7, 0.18, 0.2, 0.03), (0.86, 0.1, 0.12, 0.0), (0.98, 0.06, 0.06, -0.04), (1.15, 0.04, 0.035, -0.06), (1.22, 0.02, 0.02, -0.065)]
    loft(bm, S, segs=10)
    plate(bm, [(-0.15, 0.24), (-0.45, 0.62), (-0.42, 0.25)], 0.05, 0.0, "xz")                                      # dorsal
    plate(bm, [(-1.15, 0.0), (-1.4, 0.32), (-1.5, 0.3), (-1.3, 0.0), (-1.5, -0.3), (-1.4, -0.32)], 0.035, 0.02)     # flukes
    for s in (1, -1):
        plate(bm, [(0.45, s * 0.2), (0.2, s * 0.5), (0.28, s * 0.22)], 0.03, -0.17)
        G.ellipsoid(bm, (0.78, s * 0.15, 0.04), (0.02, 0.012, 0.016), segs=6, rings=3)
    def col(p, n, i, r):
        if p[0] > 0.76 and abs(p[1]) > 0.13 and abs(p[2] - 0.04) < 0.02:
            return (0.05, 0.05, 0.06)
        if n[2] < -0.35:
            return jit((0.85, 0.86, 0.88), r, 0.03)
        if n[2] < 0.1:
            return jit((0.56, 0.6, 0.66), r, 0.04)
        return jit((0.42, 0.46, 0.53), r, 0.04)
    return finish(bm, "dolphin", coll, col, rng), "Bottlenose dolphin", 2.7, 2.9


def turtle(coll, rng):
    bm = bmesh.new()
    # carapace: lofted dome, flat plastron
    loft(bm, [(-0.5, 0.05, 0.03, 0.08), (-0.38, 0.3, 0.12, 0.1), (-0.1, 0.42, 0.18, 0.1), (0.2, 0.4, 0.17, 0.1), (0.42, 0.25, 0.1, 0.1), (0.5, 0.08, 0.04, 0.1)], segs=12)
    loft(bm, [(0.45, 0.06, 0.06, 0.1), (0.58, 0.08, 0.075, 0.12), (0.7, 0.07, 0.065, 0.12), (0.76, 0.03, 0.03, 0.11)], segs=8)  # head
    for s in (1, -1):
        plate(bm, [(0.25, s * 0.32), (0.15, s * 0.85), (0.05, s * 0.88), (0.1, s * 0.35)], 0.03, 0.06,
              bend=lambda u, v: -abs(v) * 0.12)                                                                       # front flippers
        plate(bm, [(-0.32, s * 0.25), (-0.5, s * 0.45), (-0.55, s * 0.35), (-0.42, s * 0.2)], 0.025, 0.07)          # rear
    def col(p, n, i, r):
        if p[0] > 0.48:
            return jit((0.45, 0.42, 0.28) if int(p[0] * 60 + p[1] * 50) % 3 else (0.85, 0.78, 0.5), r, 0.05)
        if n[2] < -0.5:
            return jit((0.86, 0.8, 0.55), r, 0.04)
        if abs(p[1]) > 0.42:
            return jit((0.42, 0.4, 0.27), r, 0.05)
        cell = (int((p[0] + 1) * 6) + int((p[1] + 1) * 5)) % 3
        return jit([(0.42, 0.33, 0.18), (0.55, 0.42, 0.22), (0.33, 0.27, 0.15)][cell], r, 0.05)
    return finish(bm, "turtle", coll, col, rng), "Green turtle", 1.1, 1.2


def crab(coll, rng):
    bm = bmesh.new()
    h = 0.03
    loft(bm, [(-0.03, 0.02, 0.008, h), (-0.02, 0.035, 0.013, h), (0.01, 0.038, 0.014, h), (0.025, 0.03, 0.011, h), (0.032, 0.015, 0.006, h)], segs=10)
    for s in (1, -1):
        G.tube_path(bm, [(0.028, s * 0.012, h + 0.008), (0.034, s * 0.015, h + 0.026)], 0.003, sides=4)        # eye stalks
        G.ellipsoid(bm, (0.035, s * 0.016, h + 0.03), (0.006, 0.005, 0.008), segs=5, rings=3)
        for k in range(4):                                                                                       # 4 walking legs a side
            x = 0.012 - k * 0.012
            G.tube_path(bm, [(x, s * 0.033, h), (x - 0.006, s * 0.06, h + 0.014), (x - 0.012 - 0.003 * k, s * 0.078, 0.0)], 0.0028, sides=4)
        big = 1.35 if s > 0 else 1.0
        G.tube_path(bm, [(0.025, s * 0.03, h), (0.045, s * 0.045, h + 0.008)], 0.004, sides=4)
        G.ellipsoid(bm, (0.058, s * 0.05, h + 0.008), (0.016 * big, 0.009 * big, 0.01 * big), segs=6, rings=3)   # claw
        G.cylinder(bm, (0.068 * (1 + (big - 1) * 0.3), s * 0.05, h + 0.004), (0.082 * (1 + (big - 1) * 0.3), s * 0.05, h + 0.002), 0.004, 0.001, segs=4)
    def col(p, n, i, r):
        if p[2] > h + 0.025:
            return (0.08, 0.07, 0.07)
        return jit((0.87, 0.8, 0.62) if n[2] > 0.2 else (0.76, 0.66, 0.48), r, 0.05)
    return finish(bm, "crab", coll, col, rng), "Ghost crab", 0.08, 0.17


SPECIES = [("gull", gull), ("pelican", pelican), ("tern", tern), ("frigatebird", frigatebird), ("sandpiper", sandpiper),
           ("dolphin", dolphin), ("turtle", turtle), ("barracuda", barracuda), ("scad", scad), ("snapper", snapper),
           ("mackerel", mackerel), ("crab", crab)]


def build_all(coll, rng=None):
    rng = rng or np.random.default_rng(7)
    out = {}
    for key, fn in SPECIES:
        ob, title, length_m, size = fn(coll, rng)
        ob.name = "ANIMAL_" + key
        out[key] = dict(object=ob, title=title, length_m=length_m, frame=size, tris=hero.tri_count(ob))
    return out
