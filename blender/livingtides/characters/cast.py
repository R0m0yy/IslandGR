"""Hero villagers, version 2 (hero quality).

The four characters from the owner's concept sketches: A fisher captain, B market
vendor, C elder net-mender, D harbour child.

What changed from v1 (owner feedback: faces not detailed enough, hair looked
wrong, clothes too low quality):
  * the body is the FULL-RESOLUTION MakeHuman mesh, smooth shaded, so the face
    keeps its real structure (lids, lips, nostrils, ears, jaw and cheek planes);
  * skin is painted per vertex from the MakeHuman detail targets (lips, lids,
    eye bags, nostrils, cheeks, ears), not random per-face noise;
  * hair, beards and brows are sculpted volumes grown from the scalp / face with
    clean iso-cut hairlines (coils, combed locks, beard grooves) instead of
    scattered spikes; they inherit the face shape keys exactly;
  * garments are cut from the full-resolution body with iso-cuts (clean curved
    necklines, cuffs and hems), have folds, rolled hems, collars, patch pockets,
    belts with keepers, crisp stripes / checks and footwear with real soles.

Every object is bound to one armature built from the shared game_engine rig
definition (53 bones); the child's armature is the same rig at child joints.
"""
from __future__ import annotations
import math
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix
from . import hero, mh
from . import garments as G
from .hero import BONES, BI, rgb

SPECS = {
    "A": dict(name="A_captain", title="Fisher captain", gender=1.0, age_years=45, muscle=0.66, weight=0.56, height=0.55,
              proportions=0.6, race={"african": 1.0}, head_scale=1.38, height_m=1.76, skin="#5C3826", iris="#4A2E1A",
              detail={"head/head-age-incr": 0.35, "mouth/mouth-laugh-lines-in": 0.45, "eyes/l-eye-bag-incr": 0.35,
                      "eyes/r-eye-bag-incr": 0.35, "chin/chin-width-incr": 0.35, "head/head-square": 0.4,
                      "nose/nose-flaring-incr": 0.3, "eyebrows/eyebrows-trans-down": 0.25, "chin/chin-prominent-incr": 0.2,
                      "neck/measure-neck-circ-incr": 0.3}),
    "B": dict(name="B_vendor", title="Market vendor", gender=0.0, age_years=33, muscle=0.5, weight=0.58, height=0.5,
              proportions=0.65, race={"african": 1.0}, head_scale=1.38, height_m=1.66, skin="#4A2C1F", iris="#4E301C", lash=(0.03, 0.02, 0.02),
              detail={"mouth/mouth-lowerlip-volume-incr": 0.35, "mouth/mouth-upperlip-volume-incr": 0.2,
                      "cheek/l-cheek-bones-incr": 0.45, "cheek/r-cheek-bones-incr": 0.45, "mouth/mouth-dimples-in": 0.4,
                      "eyes/l-eye-scale-incr": 0.25, "eyes/r-eye-scale-incr": 0.25, "chin/chin-prominent-decr": 0.2}),
    "C": dict(name="C_elder", title="Elder net-mender", gender=1.0, age_years=74, muscle=0.35, weight=0.45, height=0.42,
              proportions=0.5, race={"african": 0.75, "caucasian": 0.25}, head_scale=1.38, height_m=1.66, skin="#7A4E36",
              iris="#5B4330",
              detail={"head/head-age-incr": 1.0, "mouth/mouth-laugh-lines-in": 1.0, "eyes/l-eye-bag-incr": 0.8,
                      "eyes/r-eye-bag-incr": 0.8, "cheek/l-cheek-volume-decr": 0.5, "cheek/r-cheek-volume-decr": 0.5,
                      "nose/nose-scale-vert-incr": 0.3, "ears/l-ear-scale-incr": 0.3, "ears/r-ear-scale-incr": 0.3,
                      "neck/neck-double-incr": 0.3, "nose/nose-hump-incr": 0.3}),
    "D": dict(name="D_child", title="Harbour child", gender=0.85, age_years=8, muscle=0.5, weight=0.45, height=0.5,
              proportions=0.5, race={"african": 1.0}, head_scale=1.28, height_m=1.27, skin="#6A4430", iris="#4A2E1C",
              hand_scale=1.08,
              detail={"eyes/l-eye-scale-incr": 0.7, "eyes/r-eye-scale-incr": 0.7, "eyebrows/eyebrows-trans-up": 0.3,
                      "cheek/l-cheek-volume-incr": 0.35, "cheek/r-cheek-volume-incr": 0.35, "nose/nose-scale-horiz-incr": 0.2}),
}

TORSO = ("pelvis", "spine_01", "spine_02", "spine_03", "clavicle_l", "clavicle_r", "neck_01")
ARM_L = ("upperarm_l", "lowerarm_l"); ARM_R = ("upperarm_r", "lowerarm_r")
LEGS = ("thigh_l", "thigh_r", "calf_l", "calf_r")
HANDS = tuple(f"{f}_{j:02d}_{s}" for f in ("thumb", "index", "middle", "ring", "pinky") for j in (1, 2, 3) for s in ("l", "r")) + ("hand_l", "hand_r")
NOT_LOWER = ("upperarm_l", "upperarm_r", "lowerarm_l", "lowerarm_r", "head", "foot_l", "foot_r", "ball_l", "ball_r") + HANDS     # never part of trousers / shorts
NOT_VEST = ("lowerarm_l", "lowerarm_r", "head") + HANDS + LEGS


def armhole(c, side, inset=0.012):
    """Plane across the top of the arm at the shoulder: keeps the torso side."""
    h, t = c.B[f"upperarm_{side}"]
    return G.limb_plane((h, t), 0.0 - inset / np.linalg.norm(t - h), radius=0.15 * c.k, keep="head")
FEET = ("foot_l", "foot_r", "ball_l", "ball_r")


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def front_back(P, f_front, f_back, y0=0.0, w=0.035):
    """Blend a front field into a back field across the sides (no step in the cut)."""
    t = smoothstep(y0 - w, y0 + w, P[:, 1])
    return f_front * (1 - t) + f_back * t


def fabric(base, var=0.07, scale=0.09, seed=0, fade=0.0, shade=0.0):
    """Woven-cloth colour: smooth mottling, sun fade on up-facing areas and
    slight darkening in down-facing folds."""
    b = np.asarray(rgb(base), float)

    def fn(P, N, W):
        n = G.vnoise(P, scale, seed) * var + G.vnoise(P, scale * 0.3, seed + 5) * var * 0.4
        c = b[None, :] * (1 + n[:, None])
        if fade:
            c = G.mixc(c, np.minimum(1, b * 1.25 + 0.06), fade * np.clip(N[:, 2], 0, 1))
        if shade:
            c = c * (1 - shade * np.clip(-N[:, 2], 0, 1))[:, None]
        return c
    return fn


class Char:
    def __init__(self, key):
        self.key = key
        self.spec = SPECS[key]
        self.rng = np.random.default_rng({"A": 11, "B": 22, "C": 33, "D": 44}[key])
        self.coll = bpy.data.collections.new(self.spec["name"])
        bpy.context.scene.collection.children.link(self.coll)
        self.parts = {}            # name -> (object, category)
        self.rig = None
        self.fields = {}           # garment name -> field (for clipping checks)
        self.pre = {}              # garment name -> un-thickened copy (edges for collars / cuffs, surface for patches)

    # ------------------------------------------------------------ setup
    @property
    def k(self):
        return self.info["head_r"] / 0.137

    def add(self, name, ob, cat):
        ob.name = f"{self.key}_{name}"
        ob.data.name = ob.name
        self.parts[name] = (ob, cat)
        return ob

    def build_body(self):
        s = self.spec
        self.body, self.info = hero.build_body(s, self.coll)
        self.body.vertex_groups.remove(self.body.vertex_groups["_density"])
        self.P, self.W = hero.body_arrays(self.body)
        self.add("body", self.body, "body")
        I = self.info; J = I["joints"]
        self.B = {b: (np.asarray(v[0]), np.asarray(v[1])) for b, v in I["bones"].items()}
        self.m = np.asarray(I["mouth"])
        self.hc = np.asarray(I["head_c"]); self.hr = I["head_r"]
        self.eye = {s_: (np.asarray(I["eyes"][s_][0]), I["eyes"][s_][1]) for s_ in ("l", "r")}
        self.neck_z = float(J["joint-neck"][2])
        self.clav_z = float(J["joint-l-clavicle"][2])
        self.waist_z = float(self.B["spine_02"][0][2]) - 0.02 * self.k
        self.hip_z = float(J["joint-pelvis"][2])
        self.sh = {"l": np.asarray(J["joint-l-shoulder"]), "r": np.asarray(J["joint-r-shoulder"])}
        Vu = I["V_full"][I["used"]]
        ear = I["masks"]["ears"]
        self.ear = {}
        for side, sg in (("l", 1), ("r", -1)):
            w = ear * (sg * Vu[:, 0] > 0)
            self.ear[side] = (Vu * w[:, None]).sum(0) / max(w.sum(), 1e-6)
        self.bvh = G.bvh_of(self.body)

    def surface(self, origin, direction):
        return G.surface_hit(self.bvh, origin, direction)

    # ------------------------------------------------------------ skin + face
    def paint_skin(self, lips="#3B1E18", stubble=0.0, blush=0.12, age=0.0):
        M = self.info["masks"]; me = self.body.data
        base = np.asarray(rgb(self.spec["skin"]))
        P = self.P; n = len(P)

        def fn(P_, N, W):
            c = np.tile(base, (n, 1))
            c = c * (1 + 0.035 * G.vnoise(P_, 0.05, 3))[:, None]
            dark = base * 0.7
            warm = np.minimum(1, base * np.array([1.12, 0.93, 0.9]))
            c = G.mixc(c, warm, blush * 2 * M["cheeks"] + blush * M["nose"] + blush * 1.5 * M["ears"])
            c = G.mixc(c, dark, 0.45 * M["eyebags"] + 0.35 * M["lids"] + 0.45 * M["nostrils"] * (N[:, 2] < -0.2))
            lip = np.asarray(rgb(lips))
            c = G.mixc(c, lip * 0.75 + base * 0.25, np.clip(M["lips"] * 1.4, 0, 0.92))
            if age:
                c = G.mixc(c, dark, age * 0.35 * M["laugh"] + age * 0.15 * M["forehead"])
                spots = np.clip(G.vnoise(P_, 0.012, 9) - 0.55, 0, 1) * 2.2 * (W[:, BI["head"]] > 0.5)
                c = G.mixc(c, dark, age * spots)
            if stubble:
                bz = self.beard_field(P_, W, stubble=True)
                st = np.clip(bz / 0.01, 0, 1) * (0.75 + 0.25 * G.vnoise(P_, 0.004, 4))
                c = G.mixc(c, base * 0.42, stubble * st)
            # palms and soles a shade lighter, nails pale
            hands = G.bone_sum(W, [b for b in BONES if b.startswith(("thumb", "index", "middle", "ring", "pinky", "hand"))])
            c = G.mixc(c, np.minimum(1, base * 1.35 + 0.05), 0.35 * hands * (N[:, 2] < -0.35))
            tips = G.bone_sum(W, [b for b in BONES if b[-5:-2] == "_03"])
            c = G.mixc(c, np.minimum(1, base * 1.5 + 0.12), 0.55 * (tips > 0.7) * (N[:, 2] > 0.35))
            return c
        G.paint_vertices(self.body, fn, smooth=True, sharp_angle=1.2)
        # teeth, tongue and lashes keep flat colours
        part = np.zeros(len(me.polygons), dtype=np.int64); me.attributes["part"].data.foreach_get("value", part)
        ca = me.color_attributes["Col"]
        cols = np.zeros(len(me.loops) * 4); ca.data.foreach_get("color_srgb", cols); cols = cols.reshape(-1, 4)
        fix = {1: (0.93, 0.9, 0.82), 2: (0.6, 0.27, 0.27), 3: self.spec.get("lash", (0.13, 0.09, 0.07))}
        for p in me.polygons:
            if part[p.index] in fix:
                cols[p.loop_start:p.loop_start + p.loop_total, :3] = fix[part[p.index]]
        ca.data.foreach_set("color_srgb", cols.ravel())
        hero.assign(self.body)

    def eyes(self):
        out = []
        iris = np.asarray(rgb(self.spec["iris"]))
        for side in ("l", "r"):
            c, r = self.eye[side]
            bm = bmesh.new()
            segs, rings = 24, 14
            verts, faces = [], []
            for i in range(rings + 1):
                th = math.pi * i / rings
                # cornea bulge over the iris
                rr = r * (1.06 if th < math.radians(28) else 1.0)
                for s in range(segs):
                    a = 2 * math.pi * s / segs
                    verts.append((math.sin(th) * math.cos(a) * rr, -math.cos(th) * rr, math.sin(th) * math.sin(a) * rr))
            for i in range(rings):
                for s in range(segs):
                    s2 = (s + 1) % segs
                    faces.append((i * segs + s, i * segs + s2, (i + 1) * segs + s2, (i + 1) * segs + s))
            G.add_geom(bm, [tuple(np.array(v) + c) for v in verts], faces)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
            ob = G.bm_to_object(bm, f"eye_{side}", self.coll)

            def fn(P, N, W, c=c, r=r):
                d = (P - c) / r
                ang = np.degrees(np.arccos(np.clip(-d[:, 1] / np.maximum(1e-6, np.linalg.norm(d, axis=1)), -1, 1)))
                col = np.tile(np.array([0.9, 0.87, 0.82]), (len(P), 1))
                col = G.mixc(col, np.array([0.78, 0.66, 0.6]), smoothstep(60, 85, ang))     # sclera shadowed at the edges
                ir = G.mixc(iris * 1.1, iris * 0.5, smoothstep(10, 27, ang))
                col = np.where((ang < 28)[:, None], ir, col)
                col = np.where((ang < 27.5)[:, None] & (ang > 25.5)[:, None], iris * 0.35, col)   # limbal ring
                col = np.where((ang < 11)[:, None], np.array([0.02, 0.02, 0.02]), col)
                return col
            G.paint_vertices(ob, fn, smooth=True)
            hero.assign(ob, hero.char_material_gloss())
            G.rigid_weights(ob, {"head": 1.0})
            out.append(self.add(f"eye_{side}", ob, "face"))
        return out

    # ------------------------------------------------------------ fields (rest pose)
    def head_coords(self, P):
        d = (P - self.hc) / self.hr
        az = np.arctan2(d[:, 0], -d[:, 1])          # 0 = front, +-pi = back
        ez = self.eye["l"][0][2]
        hz = (P[:, 2] - ez) / self.hr                 # height above the eyes in head radii
        return d, az, hz

    def hair_field(self, front=0.9, side=0.3, back=-0.75, temple_dip=0.06, ear_clear=0.03, part=None):
        """Scalp region above a natural hairline. Positive inside the hair."""
        def f(P, W):
            d, az, hz = self.head_coords(P)
            b = np.abs(az) / math.pi                  # 0 front .. 1 back
            line = np.where(b < 0.5, front + (side - front) * smoothstep(0.0, 0.5, b) ** 0.8,
                            side + (back - side) * smoothstep(0.5, 1.0, b))
            line = line - temple_dip * np.exp(-((b - 0.3) / 0.08) ** 2)
            v = (hz - line) * self.hr
            for s_ in ("l", "r"):
                v = np.minimum(v, np.linalg.norm(P - self.ear[s_], axis=1) - ear_clear * self.k)
            v = np.where(W[:, BI["head"]] + W[:, BI["neck_01"]] > 0.4, v, -1)
            return v
        return f

    def beard_field(self, P, W, stubble=False, moustache=True, chin_drop=0.12):
        k = self.k; m = self.m
        rel = P - m
        ax = np.abs(rel[:, 0])
        top_c = 0.022 * k if moustache else 0.0
        cheek = self.eye["l"][0][2] - 0.032 * k
        upper = (m[2] + top_c) + (cheek - (m[2] + top_c)) * smoothstep(0.02 * k, 0.07 * k, ax)
        v = upper - P[:, 2]
        v = np.minimum(v, P[:, 2] - (m[2] - chin_drop * k))                   # under the chin, down the throat
        v = np.minimum(v, (self.ear["l"][1] - 0.012 * k) - P[:, 1])           # stop in front of the ears
        lipf = np.sqrt((rel[:, 0] / (0.029 * k)) ** 2 + ((rel[:, 2] - 0.0015 * k) / (0.0105 * k)) ** 2) - 1.0
        lip_front = rel[:, 1] < 0.02
        v = np.where(lip_front, np.minimum(v, lipf * 0.012 * k), v)
        v = np.where(W[:, BI["head"]] + W[:, BI["neck_01"]] > 0.3, v, -1)
        return v

    def brow_field(self, thick=0.3, span=1.45):
        def f(P, W):
            out = np.full(len(P), -1.0)
            for side, sg in (("l", 1), ("r", -1)):
                e, r = self.eye[side]
                u = (P[:, 0] - e[0]) * sg / r
                arc = e[2] + r * (1.5 + 0.28 * np.sin(np.pi * np.clip((u + 1.1) / 2.6, 0, 1))) - 0.2 * r * np.clip(u - 0.9, 0, None)
                w = r * (thick * (1.0 - 0.35 * np.clip(u / 1.6, 0, 1)) + 0.05)
                v = np.minimum(w - np.abs(P[:, 2] - arc), r * (span - np.abs(u - 0.2)))
                v = np.where(P[:, 1] < e[1] + 0.25 * r, v, -1)
                out = np.maximum(out, v)
            return out
        return f

    # ------------------------------------------------------------ builders
    def part_from_body(self, name, faces, field, cat):
        ob = G.copy_part(self.body, name, self.coll, faces)
        G.iso_cut(ob, field)
        return ob

    def garment(self, name, faces, field, offset, thick, colour, extra=None, subdiv=0, pattern=None, face_colour=None,
                hems=None, hide=True, hide_margin=0.012, rim_only=False, cat="clothing", sharp=0.85, mat=None, relax=0):
        """Cut a garment from the body, inflate it, thicken it, roll its hems.
        `relax` smooths the cloth surface so it drapes over anatomy instead of
        shrink-wrapping it."""
        ob = self.part_from_body(name, faces, field, cat)
        if subdiv:
            G.subdivide(ob, subdiv)
        if relax:
            G.displace(ob, lambda P, N, W: offset * 0.5)
            bm = bmesh.new(); bm.from_mesh(ob.data)
            for _ in range(relax):
                bmesh.ops.smooth_vert(bm, verts=[v for v in bm.verts if not v.is_boundary], factor=0.5,
                                      use_axis_x=True, use_axis_y=True, use_axis_z=True)
            bm.to_mesh(ob.data); bm.free(); ob.data.update()
            offset = offset * 0.5
        G.displace(ob, lambda P, N, W: offset + (extra(P, N, W) if extra else 0.0))
        if pattern:
            pattern(ob)
        Pg = hero.get_co(ob.data); Wg = hero.read_groups(ob)
        hem_objs = []
        if hems:
            for i, (r, col, sel) in enumerate(hems):
                bm = G.piping(ob, r, select=sel)
                if len(bm.verts) == 0:
                    bm.free(); continue
                ho = G.bm_to_object(bm, f"{name}_hem{i}", self.coll)
                G.copy_weights_from(ho, Pg, Wg)
                G.paint_vertices(ho, col if callable(col) else fabric(col), smooth=True)
                hero.assign(ho, mat)
                hem_objs.append(self.add(f"{name}_hem{i}", ho, cat))
        self.keep_pre(name, ob)
        if thick:
            G.thicken(ob, thick, rim_only=rim_only)
        if face_colour is not None:
            G.paint_faces_v2(ob, face_colour, smooth=True, sharp_angle=sharp)
        else:
            G.paint_vertices(ob, colour, smooth=True, sharp_angle=sharp)
        hero.assign(ob, mat)
        self.add(name, ob, cat)
        if hide:
            sel = (lambda P, W: faces(P, W)) if faces is not None else None
            G.hide_body_under(self.body, field, margin=hide_margin, sel=sel)
        self.fields[name] = field
        return ob, hem_objs

    def keep_pre(self, name, ob):
        me = ob.data.copy()
        o = bpy.data.objects.new(name + "_pre", me)
        for g in ob.vertex_groups:
            o.vertex_groups.new(name=g.name)
        self.pre[name] = o
        return o

    def loops(self, name):
        return G.boundary_loops(self.pre[name])

    def patch(self, src, name, field, lift, thick, colour, hems=None, cat="clothing", mat=None):
        """A patch (pocket, belt, strap, placket) cut from another garment's outer surface."""
        if isinstance(src, str):
            src = self.pre[src]
        ob = G.copy_part(src, name, self.coll, None)
        G.iso_cut(ob, field)
        # keep only the outward-facing layer of a thickened source
        G.displace(ob, lambda P, N, W: lift)
        Pg = hero.get_co(ob.data); Wg = hero.read_groups(ob)
        if hems:
            for i, (r, col) in enumerate(hems):
                bm = G.piping(ob, r)
                ho = G.bm_to_object(bm, f"{name}_edge{i}", self.coll)
                G.copy_weights_from(ho, Pg, Wg)
                G.paint_vertices(ho, col if callable(col) else fabric(col), smooth=True)
                hero.assign(ho, mat)
                self.add(f"{name}_edge{i}", ho, cat)
        if thick:
            G.thicken(ob, thick)
        G.paint_vertices(ob, colour if callable(colour) else fabric(colour), smooth=True)
        hero.assign(ob, mat)
        return self.add(name, ob, cat)

    def outer_layer(self, ob, name):
        """Copy of the outward-facing surface of a garment (before thickening it was a shell)."""
        return ob

    def solid(self, name, bm, colour, cat="accessory", weights=None, mat=None, smooth=True, sharp=0.6):
        ob = G.bm_to_object(bm, name, self.coll)
        G.paint_vertices(ob, colour if callable(colour) else (lambda P, N, W, c=np.asarray(rgb(colour)): np.tile(c, (len(P), 1)) * (1 + 0.04 * G.vnoise(P, 0.03, 2))[:, None]),
                         smooth=smooth, sharp_angle=sharp)
        hero.assign(ob, mat)
        if isinstance(weights, dict):
            G.rigid_weights(ob, weights)
        else:
            m = np.ones(len(self.P), bool) if weights is None else weights
            G.copy_weights_from(ob, self.P[m], self.W[m])
        return self.add(name, ob, cat)

    # ------------------------------------------------------------ hair
    def hair_volume(self, name, field, thickness, colour, subdiv=1, bumps=None, grooves=None, drop=None, cat="hair",
                    taper=0.012, sharp=1.2, cuts=None, face_colour=None, rim=None):
        """Hair grown from the scalp/face: a cut of the skin, inflated by
        `thickness(P)`, tapering to nothing at the hairline, with coils (bumps)
        or combed locks (grooves), closed underneath."""
        ob = self.part_from_body(name, None, field, cat)
        if subdiv:
            G.subdivide(ob, subdiv)
        P = hero.get_co(ob.data); W = hero.read_groups(ob)
        edge = np.clip(field(P, W) / (taper * self.k), 0, 1) ** 0.6
        self._hair_meta = {}

        def off(P, N, W):
            t = thickness(P) * edge
            b = np.zeros(len(P))
            if bumps:
                b = bumps(P, N) * edge
            g = np.zeros(len(P))
            if grooves:
                g = grooves(P, N) * edge
            self._hair_meta["b"] = b; self._hair_meta["g"] = g
            return t + b - g
        G.displace(ob, off)
        if drop is not None:
            P = hero.get_co(ob.data)
            hero.set_co(ob.data, P + np.asarray(drop(P)) * edge[:, None])
        b = self._hair_meta["b"]; g = self._hair_meta["g"]
        if rim:
            r, rc = rim
            Pg = hero.get_co(ob.data); Wg = hero.read_groups(ob)
            rb = G.piping(ob, r, step=0.006, sides=7)
            ro = G.bm_to_object(rb, name + "_rim", self.coll)
            G.copy_weights_from(ro, Pg, Wg)
            G.paint_faces_v2(ro, rc, smooth=True, sharp_angle=1.0) if face_colour else G.paint_vertices(ro, rc, smooth=True)
            hero.assign(ro)
            self.add(name + "_rim", ro, cat)
        if cuts:
            for ax, sp in cuts:
                G.plane_cuts(ob, ax, sp)
            n_cut = len(ob.data.vertices)
            b = np.resize(b, n_cut); g = np.resize(g, n_cut)
        G.thicken(ob, 0.002, offset=-1)
        n0 = len(b)
        nn = len(ob.data.vertices)
        bb = np.concatenate([b, b])[:nn] if nn >= n0 else b[:nn]
        gg = np.concatenate([g, g])[:nn] if nn >= n0 else g[:nn]
        if face_colour:
            G.paint_faces_v2(ob, face_colour, smooth=True, sharp_angle=sharp)
        else:
            G.paint_vertices(ob, lambda P, N, W: colour(P, N, bb, gg), smooth=True, sharp_angle=sharp)
        hero.assign(ob)
        hero.add_shape_keys(ob)
        return self.add(name, ob, cat)

    def coil_bumps(self, field, size, height, density, seed=1):
        """Gaussian coils scattered over the hair region (tight curls)."""
        rng = np.random.default_rng(seed)
        P, W = self.P, self.W
        f = field(P, W)
        cand = P[f > 0]
        n = int(len(cand) * density)
        C = cand[rng.choice(len(cand), size=min(n, len(cand)), replace=False)] if len(cand) else cand
        R = size * self.k * rng.uniform(0.75, 1.25, len(C))
        H = height * self.k * rng.uniform(0.7, 1.2, len(C))

        def bumps(Q, N):
            out = np.zeros(len(Q))
            for s in range(0, len(C), 200):
                d2 = ((Q[:, None, :] - C[None, s:s + 200, :]) ** 2).sum(-1)
                out = np.maximum(out, (H[None, s:s + 200] * np.exp(-d2 / (R[None, s:s + 200] ** 2))).max(axis=1))
            return out
        return bumps

    # ------------------------------------------------------------ rig
    def finish(self):
        removed = G.delete_hidden(self.body)
        hero.add_shape_keys(self.body)
        self.rig = hero.build_armature(self.spec["name"], self.info["V_full"], self.coll)
        for n, (ob, cat) in self.parts.items():
            if cat == "held" or ob.parent is not None:
                continue
            hero.bind(ob, self.rig)
        self.removed_faces = removed
        return self

    def rest(self):
        for pb in self.rig.pose.bones:
            pb.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()

    def aim(self, bone, direction):
        pb = self.rig.pose.bones[bone]
        M = pb.matrix.copy()
        cur = (pb.tail - pb.head).normalized()
        q = cur.rotation_difference(Vector(direction).normalized())
        head = M.to_translation()
        pb.matrix = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head) @ M
        bpy.context.view_layer.update()

    def rotate(self, bone, axis, deg):
        pb = self.rig.pose.bones[bone]
        M = pb.matrix.copy()
        head = M.to_translation()
        pb.matrix = Matrix.Translation(head) @ Matrix.Rotation(math.radians(deg), 4, Vector(axis)) @ Matrix.Translation(-head) @ M
        bpy.context.view_layer.update()

    def relaxed(self, up_l=(0.2, 0.04, -1), up_r=(-0.2, 0.04, -1), lo_l=(0.1, -0.3, -1), lo_r=(-0.1, -0.3, -1)):
        self.rest()
        self.aim("upperarm_l", up_l); self.aim("lowerarm_l", lo_l)
        self.aim("upperarm_r", up_r); self.aim("lowerarm_r", lo_r)
        self.curl_fingers(0.35)

    def curl_fingers(self, amt, sides=("l", "r")):
        for s in sides:
            for f in ("index", "middle", "ring", "pinky"):
                for j in (1, 2, 3):
                    pb = self.rig.pose.bones.get(f"{f}_{j:02d}_{s}")
                    if pb:
                        pb.rotation_mode = "XYZ"
                        pb.rotation_euler = (0, 0, 0)
                        pb.rotation_euler[2] = amt * (0.6 if j == 1 else 1.0) * (-1 if s == "l" else 1)
        bpy.context.view_layer.update()

    def bone_world(self, bone):
        pb = self.rig.pose.bones[bone]
        return np.array(self.rig.matrix_world @ pb.head), np.array(self.rig.matrix_world @ pb.tail), self.rig.matrix_world @ pb.matrix

    def held(self, name, bm, bone, colour, mat=None, smooth=True, sharp=0.6):
        """A prop built at the hand in the current (rest) pose and attached to a bone."""
        ob = G.bm_to_object(bm, name, self.coll)
        G.paint_vertices(ob, colour if callable(colour) else (lambda P, N, W, c=np.asarray(rgb(colour)): np.tile(c, (len(P), 1))),
                         smooth=smooth, sharp_angle=sharp)
        hero.assign(ob, mat)
        hero.attach_to_bone(ob, self.rig, bone)
        return self.add(name, ob, "held")

    def tris(self):
        return {n: hero.tri_count(ob) for n, (ob, c) in self.parts.items()}

    def hand_frame(self, side):
        """Grip point and axes of a hand in the rest pose: (grip, along, palm_normal)."""
        h, t = self.B[f"hand_{side}"]
        mid = self.B[f"middle_01_{side}"]
        along = (mid[1] - h); along /= np.linalg.norm(along)
        grip = mid[0] + along * 0.02 * self.k
        return grip, along


# ====================================================================== shared pieces
def footwear_sole(c, name, colour, thick=0.014, grow=0.006, heel=0.0):
    """Sole following each foot's outline (convex hull of the foot bottom)."""
    bm = bmesh.new()
    for s in ("l", "r"):
        m = G.bone_sum(c.W, (f"foot_{s}", f"ball_{s}")) + G.bone_sum(c.W, [b for b in BONES if b.endswith("_" + s) and b.startswith(("toe",))]) > 0.5
        pts = c.P[m & (c.P[:, 2] < 0.03)][:, :2]
        if len(pts) < 3:
            continue
        hull = convex_hull(pts)
        ctr = hull.mean(axis=0)
        hull = hull + (hull - ctr) / np.linalg.norm(hull - ctr, axis=1)[:, None] * grow
        hull = G.smooth_path(G.resample(np.c_[hull, np.zeros(len(hull))], 0.008), 2)[:, :2]
        n = len(hull)
        z0, z1 = -0.004, thick - 0.004
        verts = [(x, y, z0) for x, y in hull] + [(x, y, z1 + (heel if y > ctr[1] + 0.02 else 0)) for x, y in hull]
        faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
        faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        G.add_geom(bm, verts, faces)
    return c.solid(name, bm, colour, cat="footwear", sharp=0.5)


def convex_hull(pts):
    pts = sorted(set(map(tuple, np.round(pts, 6))))
    if len(pts) < 3:
        return np.array(pts)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return np.array(lower[:-1] + upper[:-1])


def sandals(c, leather):
    k = c.k
    footwear_sole(c, "sandal_soles", mix_hex(leather, "#2A1A10", 0.35), thick=0.016)
    foot_faces = lambda C, FW: G.bone_sum(FW, FEET) + G.bone_sum(FW, [b for b in BONES if b.startswith("toe")]) > 0.4
    for s in ("l", "r"):
        fb = c.B[f"foot_{s}"]
        # strap over the instep and a heel/ankle strap: strips cut from the foot skin
        for nm, t, w in (("instep", 0.55, 0.012), ("ankle", 0.0, 0.009)):
            f1 = G.limb_plane(fb, t + w / np.linalg.norm(fb[1] - fb[0]), radius=0.09, keep="head")
            f2 = G.limb_plane(fb, t - w / np.linalg.norm(fb[1] - fb[0]), radius=0.09, keep="tail")
            side_m = (lambda P, W, s=s: np.where((P[:, 0] > 0) == (s == "l"), 1.0, -1.0))
            field = G.fmin(f1, f2, side_m, lambda P, W: P[:, 2] - 0.012)
            c.garment(f"sandal_{nm}_{s}", foot_faces, field, 0.003, 0.003, fabric(leather, 0.05, 0.03), hide=False,
                      cat="footwear", sharp=0.5)


def mix_hex(a, b, t):
    ca, cb = np.asarray(rgb(a)), np.asarray(rgb(b))
    return tuple(ca * (1 - t) + cb * t)


def hat_shell(c, name, colour, base_lift=0.05, tilt=0.3, crown_h=0.12, bulge=1.0, brim=(0.06, 0.06, 0.09), droop=0.35,
              forward=0.0, segs=40, rings=9, thick=0.006, clearance=0.012, flat=0.0, brim_rings=4):
    """Hat: crown fitted over the head (clears every head vertex above the band),
    brim of any length per direction, smooth shaded."""
    k = c.k
    e = c.eye["l"][0]
    axis = np.array([0, tilt, 1.0]); axis /= np.linalg.norm(axis)
    ctr = np.array([0, c.hc[1], e[2] + base_lift * k])
    R = G.orient(axis); ex, ey = np.array(R.col[0]), np.array(R.col[1])
    head = c.P[c.W[:, BI["head"]] > 0.5]
    hair = [ob for n, (ob, cat) in c.parts.items() if cat == "hair" and n not in ("brows", "beard", "eyebrows")]
    if hair:
        head = np.vstack([head] + [hero.get_co(o.data) for o in hair])
    d = head - ctr; h = d @ axis
    q = d - np.outer(h, axis)
    ang = np.arctan2(q @ ey, q @ ex); rad = np.linalg.norm(q, axis=1)
    top = float(h.max())
    rs = []
    for s in range(segs):
        a0 = -math.pi + 2 * math.pi * s / segs
        dd = np.abs(((ang - a0 + math.pi) % (2 * math.pi)) - math.pi)
        m = (dd < 2.5 * math.pi / segs) & (h > -0.01)
        rs.append(rad[m].max() if m.any() else rad.max())
    rs = np.array(rs)
    for _ in range(3):
        rs = (np.roll(rs, 1) + 2 * rs + np.roll(rs, -1)) / 4
    rs = rs + clearance
    dirs = [math.cos(-math.pi + 2 * math.pi * s / segs) * ex + math.sin(-math.pi + 2 * math.pi * s / segs) * ey for s in range(segs)]
    H = max(crown_h * k, top + clearance)
    verts, faces = [], []
    # brim rings: outer edge -> band
    for j in range(brim_rings, 0, -1):
        u = j / brim_rings
        for s, dv in enumerate(dirs):
            front = -dv[1]
            bl = brim[1] + (brim[0] - brim[1]) * max(0, front) + (brim[2] - brim[1]) * max(0, -front)
            bl *= k
            verts.append(tuple(ctr + dv * (rs[s] + bl * u) - axis * bl * droop * u ** 1.6))
    for j in range(rings):
        u = j / rings
        rr = np.sqrt(max(0.0, 1 - u ** 2)) if flat == 0 else (1 - flat * u ** 3)
        for s, dv in enumerate(dirs):
            shift = np.array([0, -forward * k * u, 0])
            verts.append(tuple(ctr + dv * rs[s] * (rr if j else 1.0) * (1 + (bulge - 1) * math.sin(math.pi * u)) + axis * H * u + shift))
    verts.append(tuple(ctr + axis * H + np.array([0, -forward * k, 0])))
    apex = len(verts) - 1
    nr = brim_rings + rings
    for j in range(nr - 1):
        for s in range(segs):
            s2 = (s + 1) % segs
            faces.append((j * segs + s, j * segs + s2, (j + 1) * segs + s2, (j + 1) * segs + s))
    last = (nr - 1) * segs
    for s in range(segs):
        faces.append((last + s, last + (s + 1) % segs, apex))
    bm = bmesh.new()
    G.add_geom(bm, verts, faces)
    ob = G.bm_to_object(bm, name, c.coll)
    G.thicken(ob, thick, offset=-1)
    G.paint_vertices(ob, colour, smooth=True, sharp_angle=0.9)
    hero.assign(ob)
    G.rigid_weights(ob, {"head": 1.0})
    info = dict(ctr=ctr, axis=axis, rs=rs, dirs=dirs, H=H, ex=ex, ey=ey)
    return c.add(name, ob, "hat"), info


def fish_mesh(L, grip, dn, side_axis):
    """Bluefin-jack style fish hanging from the grip along `dn`."""
    from .. import animals
    bm = bmesh.new()
    animals.fish_body(bm, L, L * 0.26, L * 0.12, tail_fork=0.55, dorsal=[(0.5, 0.68, 0.4), (0.22, 0.4, 0.25)], segs=12)
    # local fish frame: +X head. Tail at -X hangs from the grip.
    R = Matrix((tuple(np.asarray(dn)), tuple(side_axis), tuple(np.cross(np.asarray(dn), side_axis)))).transposed()
    for v in bm.verts:
        p = np.array(v.co)
        p[0] += L * 0.56              # tail root at origin
        v.co = Vector(np.asarray(grip) + np.array(R @ Vector(p)))
    return bm


# ====================================================================== A
def build_A():
    c = Char("A"); c.build_body(); k = c.k; rng = c.rng
    c.paint_skin(lips="#3A1D17", stubble=0.55, blush=0.08, age=0.4)
    c.eyes()
    # short cropped hair (shows below the sou'wester), stubble is painted + a fine stubble shell
    hf = c.hair_field(front=0.85, side=0.22, back=-0.85, temple_dip=0.05)
    coils = c.coil_bumps(hf, 0.004, 0.0018, 0.6, seed=3)
    hair_col = lambda P, N, b, g: G.mixc(np.tile([0.07, 0.05, 0.04], (len(P), 1)), np.array([0.16, 0.12, 0.1]), np.clip(b / 0.002, 0, 1))
    c.hair_volume("hair", hf, lambda P: np.full(len(P), 0.0045 * k), hair_col, subdiv=0, bumps=coils)
    c.hair_volume("brows", c.brow_field(0.15), lambda P: np.full(len(P), 0.0014 * k),
                  lambda P, N, b, g: G.mixc(np.tile([0.06, 0.045, 0.035], (len(P), 1)), np.array([0.14, 0.1, 0.08]), np.clip(g / 0.0012, 0, 1)),
                  subdiv=2, grooves=lambda P, N: 0.0012 * k * np.abs(np.sin(P[:, 0] * 900 + P[:, 2] * 300)), taper=0.004)

    wz, P, W = c.waist_z, c.P, c.W
    white, teal, navy = "#EFEBE1", "#2F8E86", "#26355A"
    neck = c.neck_z

    # ---- shirt: long sleeves rolled to mid-forearm, open collar, tucked in
    shirt_faces = lambda C, FW: (G.bone_sum(FW, TORSO + ARM_L + ARM_R) > 0.5) & (C[:, 2] > wz - 0.12)
    v_depth = 0.075 * k
    neckline = lambda P, W: front_back(P, (neck - 0.006 - v_depth * np.clip(1 - np.abs(P[:, 0]) / (0.05 * k), 0, 1)) - P[:, 2], (neck - 0.006) - P[:, 2])
    shirt_f = G.fmin(neckline, lambda P, W: P[:, 2] - (wz - 0.08),
                     G.limb_plane(c.B["lowerarm_l"], 0.42), G.limb_plane(c.B["lowerarm_r"], 0.42))
    blouse = lambda P, N, W: (0.012 * np.exp(-((P[:, 2] - (wz + 0.035)) / 0.035) ** 2)
                              + 0.0035 * G.vnoise(P, 0.035, 1) + 0.004 * np.abs(np.sin(P[:, 2] * 60 + P[:, 0] * 20)) * G.bone_sum(W, ARM_L + ARM_R))
    shirt, _ = c.garment("shirt", shirt_faces, shirt_f, 0.006, 0.003, fabric(white, 0.05, 0.08, 1, fade=0.0, shade=0.12),
                         extra=blouse, hems=[(0.0035, white, lambda L: L[:, 2].mean() < neck - 0.02 and L[:, 2].mean() > wz)])
    for s in ("l", "r"):
        fa = c.B[f"lowerarm_{s}"]
        h, t = fa
        co = h + (t - h) * 0.42
        bm = bmesh.new()
        for loop in c.loops("shirt"):
            if np.linalg.norm(loop.mean(axis=0) - co) < 0.06:
                pts = G.smooth_path(G.resample(loop, 0.006), 1)
                d = (t - h) / np.linalg.norm(t - h)
                for j, (dz, rr) in enumerate(((-0.004, 0.011), (-0.026, 0.012), (-0.047, 0.009))):
                    cc = pts.mean(axis=0)
                    q = cc + (pts - cc) * (1 + 0.1 + 0.05 * j) + d * dz
                    G.ring_tube(bm, q, rr * k, sides=7)
        c.solid(f"sleeve_roll_{s}", bm, fabric(white, 0.05, 0.05, 2, shade=0.15), cat="clothing",
                weights=G.bone_sum(c.W, (f"lowerarm_{s}", f"upperarm_{s}")) > 0.5)
    G_coll = c.coll
    col = G.collar(c.pre["shirt"], lambda L: L[:, 2].mean() > neck - 0.05, 0.03 * k, 0.025 * k, 0.003, G_coll, "A_collar", points=0.035 * k)
    G.copy_weights_from(col, c.P, c.W); G.paint_vertices(col, fabric(white, 0.04, 0.05, 3), smooth=True); hero.assign(col)
    c.add("collar", col, "clothing")
    # placket buttons down the shirt front (below the open collar)
    bm = bmesh.new()
    for j in range(3):
        z = neck - v_depth - 0.03 - j * 0.07 * k
        hit, nn = c.surface((0.0, -0.6, z), (0, 1, 0))
        if hit is not None:
            G.cylinder(bm, hit + nn * 0.007, hit + nn * 0.010, 0.0055, segs=10)
    c.solid("shirt_buttons", bm, "#E8E2D2", cat="clothing", mat=hero.char_material_gloss())

    # ---- trousers: navy, rolled at the ankle, tucked into boots
    trouser_faces = lambda C, FW: (G.bone_sum(FW, NOT_LOWER) < 0.5) & (C[:, 2] < wz + 0.06)
    trouser_f = G.fmin(lambda P, W: (wz + 0.012) - P[:, 2],
                       G.limb_plane(c.B["calf_l"], 0.6), G.limb_plane(c.B["calf_r"], 0.6))
    folds = lambda P, N, W: (0.004 * G.vnoise(P, 0.04, 6) + 0.006 * np.exp(-((P[:, 2] - 0.2) / 0.06) ** 2) * np.abs(np.sin(P[:, 2] * 140))
                             + 0.003 * (np.abs(P[:, 0]) < 0.006) * (P[:, 1] < 0) * (P[:, 2] > c.hip_z - 0.12))   # fly seam
    trousers, _ = c.garment("trousers", trouser_faces, trouser_f, 0.009, 0.004, fabric(navy, 0.06, 0.09, 4, fade=0.15, shade=0.2),
                            extra=folds)
    for s in ("l", "r"):
        h, t = c.B[f"calf_{s}"]; co = h + (t - h) * 0.6
        bm = bmesh.new()
        for loop in c.loops("trousers"):
            if np.linalg.norm(loop.mean(axis=0) - co) < 0.08:
                pts = G.smooth_path(G.resample(loop, 0.006), 1)
                d = (t - h) / np.linalg.norm(t - h)
                cc = pts.mean(axis=0)
                for j, (dz, rr) in enumerate(((-0.004, 0.012), (-0.026, 0.013))):
                    G.ring_tube(bm, cc + (pts - cc) * 1.12 + d * dz, rr * k, sides=7)
        c.solid(f"trouser_cuff_{s}", bm, fabric("#2D3D66", 0.05, 0.05, 5), cat="clothing",
                weights=G.bone_sum(c.W, (f"calf_{s}",)) > 0.5)

    # ---- belt with brass buckle and keepers, cut from the trouser surface
    belt_f = lambda P, W: 0.021 * k - np.abs(P[:, 2] - (wz - 0.012 * k))
    belt = c.patch("trousers", "belt", belt_f, 0.005, 0.004, fabric("#4A2E1E", 0.08, 0.03, 7),
                   hems=[(0.0018, "#3A2216")])
    front_y = c.P[(np.abs(c.P[:, 2] - wz) < 0.02) & (np.abs(c.P[:, 0]) < 0.02)][:, 1].min() - 0.02
    bm = bmesh.new()
    z = wz - 0.012 * k
    for (sx, sz, w, h_) in ((0, 0.0, 0.07 * k, 0.012), (0, 0.0, 0.012, 0.05 * k)):
        pass
    # rectangular buckle frame (four bars) + prong
    bw, bh, bt = 0.034 * k, 0.026 * k, 0.005
    for (cx, cz, sx_, sz_) in ((0, bh, 2 * bw, bt), (0, -bh, 2 * bw, bt), (bw, 0, bt, 2 * bh), (-bw, 0, bt, 2 * bh)):
        G.box(bm, (cx, front_y - 0.004, z + cz), (sx_, 0.006, sz_))
    G.box(bm, (0.004, front_y - 0.008, z), (bw * 1.3, 0.003, 0.003))
    c.solid("buckle", bm, "#C9A14A", cat="accessory", mat=hero.char_material_metal(), sharp=0.4)
    bm = bmesh.new()
    for ax in (-0.11, 0.11, -0.16, 0.16):
        hit, nn = c.surface((ax * k, -0.6 if abs(ax) < 0.15 else 0.6, z), (0, 1, 0) if abs(ax) < 0.15 else (0, -1, 0))
        if hit is not None:
            G.box(bm, hit + nn * 0.014, (0.012, 0.004, 0.05 * k), G.orient(nn, (0, 0, 1)))
    c.solid("belt_keepers", bm, "#3A2216", cat="clothing")

    # ---- vest: teal canvas, open front, bound edges, two flap pockets
    vest_faces = lambda C, FW: (G.bone_sum(FW, NOT_VEST) < 0.5) & (C[:, 2] > wz - 0.16)
    arm_l = lambda P, W: np.linalg.norm((P - (c.sh["l"] + np.array([0.02, 0, -0.045]))) * np.array([1, 1, 0.8]), axis=1) - 0.072 * k
    arm_r = lambda P, W: np.linalg.norm((P - (c.sh["r"] + np.array([-0.02, 0, -0.045]))) * np.array([1, 1, 0.8]), axis=1) - 0.072 * k
    opening = lambda P, W: np.abs(P[:, 0]) - (0.03 * k + 0.25 * np.clip(P[:, 2] - (wz + 0.1), 0, None)) + 6.0 * np.clip(P[:, 1] + 0.03, 0, None)
    vest_f = G.fmin(arm_l, arm_r, armhole(c, "l", 0.02), armhole(c, "r", 0.02), opening, lambda P, W: P[:, 2] - (wz - 0.085), lambda P, W: (neck - 0.025) - P[:, 2])
    vest, _ = c.garment("vest", vest_faces, vest_f, 0.021, 0.006, fabric(teal, 0.07, 0.07, 8, fade=0.2, shade=0.15), relax=4,
                        extra=lambda P, N, W: 0.003 * G.vnoise(P, 0.05, 9), hems=[(0.004, "#22706A", None)], hide=False)
    for sx in (1, -1):
        for zz, hh in ((wz + 0.02 * k, 0.07), (wz + 0.2 * k, 0.055)):
            pf = lambda P, W, sx=sx, zz=zz, hh=hh: np.minimum(0.034 * k - np.abs(P[:, 0] - sx * 0.085 * k),
                                                              np.minimum(hh * k / 2 - np.abs(P[:, 2] - zz), np.where(P[:, 1] < 0, 1, -1)))
            c.patch("vest", f"pocket_{'l' if sx > 0 else 'r'}_{int(zz * 100)}", pf, 0.004, 0.003, fabric(teal, 0.06, 0.04, 10),
                    hems=[(0.0022, "#22706A")])
            ff = lambda P, W, sx=sx, zz=zz, hh=hh: np.minimum(0.037 * k - np.abs(P[:, 0] - sx * 0.085 * k),
                                                              np.minimum(0.013 * k - np.abs(P[:, 2] - (zz + hh * k / 2 - 0.006)), np.where(P[:, 1] < 0, 1, -1)))
            c.patch("vest", f"flap_{'l' if sx > 0 else 'r'}_{int(zz * 100)}", ff, 0.0085, 0.003, fabric("#2A807A", 0.05, 0.04, 11),
                    hems=[(0.002, "#22706A")])
            hit, nn = c.surface((sx * 0.085 * k, -0.6, zz + hh * k / 2 - 0.012), (0, 1, 0))
            if hit is not None:
                bm = bmesh.new()
                G.cylinder(bm, hit + nn * 0.026, hit + nn * 0.031, 0.0055, segs=10)
                c.solid(f"pocket_button_{'l' if sx > 0 else 'r'}_{int(zz * 100)}", bm, "#C9A14A", mat=hero.char_material_metal())

    # ---- rubber boots: smooth shell over foot and lower calf, real sole and heel
    boot_faces = lambda C, FW: (G.bone_sum(FW, FEET + ("calf_l", "calf_r")) + G.bone_sum(FW, [b for b in BONES if b.startswith("toe")])) > 0.5
    boot_f = G.fmin(G.limb_plane(c.B["calf_l"], 0.43, keep="tail"), G.limb_plane(c.B["calf_r"], 0.43, keep="tail"))
    boots = c.part_from_body("boots", boot_faces, boot_f, "footwear")
    bm = bmesh.new(); bm.from_mesh(boots.data)
    for _ in range(40):
        bmesh.ops.smooth_vert(bm, verts=[v for v in bm.verts if not v.is_boundary], factor=0.8, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(boots.data); bm.free()
    G.displace(boots, lambda P, N, W: 0.016 + 0.004 * (P[:, 2] > 0.06))
    V = hero.get_co(boots.data); V[:, 2] = np.maximum(V[:, 2], 0.012); hero.set_co(boots.data, V)
    Pg = hero.get_co(boots.data); Wg = hero.read_groups(boots)
    bm = G.piping(boots, 0.007)
    rim = G.bm_to_object(bm, "boot_rims", c.coll); G.copy_weights_from(rim, Pg, Wg)
    G.paint_vertices(rim, lambda P, N, W: np.tile([0.08, 0.08, 0.09], (len(P), 1)), smooth=True)
    hero.assign(rim, hero.char_material_gloss()); c.add("boot_rims", rim, "footwear")
    G.thicken(boots, 0.004)
    G.paint_vertices(boots, lambda P, N, W: np.tile([0.05, 0.05, 0.058], (len(P), 1)) * (1 + 0.15 * G.vnoise(P, 0.03, 12) + 0.6 * (P[:, 2] < 0.035))[:, None]
                     + (P[:, 2] < 0.035)[:, None] * np.array([0.12, 0.09, 0.06]), smooth=True, sharp_angle=0.9)
    hero.assign(boots, hero.char_material_gloss()); c.add("boots", boots, "footwear")
    G.hide_body_under(c.body, G.fmin(boot_f, lambda P, W: np.where(boot_faces(P, W), 1.0, -1.0)), margin=0.004)
    footwear_sole(c, "boot_soles", "#2A2420", thick=0.02, grow=0.012, heel=0.012)

    # ---- sou'wester: sun-faded yellow, long back brim, stitched rings
    yel = np.asarray(rgb("#E7B52C"))
    hat, hi = hat_shell(c, "souwester", lambda P, N, W: G.mixc(np.tile(yel, (len(P), 1)) * (1 + 0.05 * G.vnoise(P, 0.04, 13))[:, None],
                                                                np.minimum(1, yel * 1.15 + 0.1), 0.45 * np.clip(N[:, 2], 0, 1)),
                        base_lift=0.05, tilt=0.3, crown_h=0.13, bulge=1.05, brim=(0.05, 0.065, 0.1), droop=0.55, thick=0.006)
    bm = bmesh.new()
    for u in (0.35, 0.7):
        pts = []
        for s, dv in enumerate(hi["dirs"]):
            front = -dv[1]
            bl = (0.065 + (0.05 - 0.065) * max(0, front) + (0.1 - 0.065) * max(0, -front)) * k
            pts.append(hi["ctr"] + dv * (hi["rs"][s] + bl * u) - hi["axis"] * (bl * 0.55 * u ** 1.6 - 0.0035))
        G.ring_tube(bm, np.array(pts), 0.0016, sides=4)


    # ---- rope coil over the left shoulder: three twisted turns hugging the torso
    sh = c.sh["l"]; hip = c.info["joints"]["joint-r-upper-leg"]
    diag = sh - hip; diag /= np.linalg.norm(diag)
    axis = np.cross(diag, (0, 1, 0)); axis /= np.linalg.norm(axis)
    ctr = (sh + hip) / 2
    tgt = np.vstack([hero.get_co(vest.data), hero.get_co(shirt.data)])
    tgt = tgt[(tgt[:, 2] < neck - 0.03 * k) & (G.bone_sum(c.W[hero.nearest_idx(c.P, tgt)], ARM_L + ARM_R) < 0.3)]
    bm = bmesh.new()
    R = G.orient(axis); ex, ey = np.array(R.col[0]), np.array(R.col[1])
    d = tgt - ctr; hh = d @ axis
    q = d[np.abs(hh) < 0.05] - np.outer(hh[np.abs(hh) < 0.05], axis)
    ang = np.arctan2(q @ ey, q @ ex); rad = np.linalg.norm(q, axis=1)
    base_r = []
    for s in range(48):
        a0 = -math.pi + 2 * math.pi * s / 48
        dd = np.abs(((ang - a0 + math.pi) % (2 * math.pi)) - math.pi)
        base_r.append(rad[dd < 0.2].max() if (dd < 0.2).any() else 0.2)
    base_r = np.array(base_r)
    for _ in range(3):
        base_r = (np.roll(base_r, 1) + 2 * base_r + np.roll(base_r, -1)) / 4
    for turn in range(3):
        pts = np.array([ctr + (math.cos(a) * ex + math.sin(a) * ey) * (base_r[s] + 0.016 + 0.004 * turn)
                        + axis * (turn - 1) * 0.021 for s, a in enumerate(np.linspace(-math.pi, math.pi, 48, endpoint=False))])
        G.ring_tube(bm, pts, 0.0105, sides=9, twist=0.9, ridge=0.18)
    c.solid("rope_coil", bm, lambda P, N, W: np.tile(rgb("rope"), (len(P), 1)) * (0.85 + 0.2 * G.vnoise(P, 0.01, 14))[:, None],
            weights=G.bone_sum(c.W, TORSO) > 0.6, sharp=1.2)
    c.finish()
    # fish held by the tail in the right hand (bone-attached, follows every animation)
    grip, along = c.hand_frame("r")
    dn = along
    side_axis = np.cross(dn, (0, 1, 0)); side_axis /= np.linalg.norm(side_axis)
    bm = fish_mesh(0.42 * k / 1.0, grip, dn, side_axis)
    back = np.cross(dn, side_axis)
    c.held("fish", bm, "hand_r", lambda P, N, W: G.mixc(np.tile([0.22, 0.36, 0.44], (len(P), 1)), np.array([0.84, 0.86, 0.84]),
                                                          np.clip(0.5 - 1.6 * (N @ back), 0, 1)) * (1 + 0.06 * G.vnoise(P, 0.01, 3))[:, None],
           mat=hero.char_material_gloss(), sharp=0.8)
    c.relaxed(lo_r=(-0.15, -0.5, -1))
    return c


# ====================================================================== B
def build_B():
    c = Char("B"); c.build_body(); k = c.k; rng = c.rng
    c.paint_skin(lips="#5A2A26", blush=0.12)
    c.eyes()
    c.hair_volume("brows", c.brow_field(0.16, 1.3), lambda P: np.full(len(P), 0.0013 * k),
                  lambda P, N, b, g: np.tile([0.07, 0.05, 0.04], (len(P), 1)), subdiv=2, taper=0.006)
    wz, P, W = c.waist_z, c.P, c.W
    coral, gold, cream = "#D8725F", "#D7A546", "#EBDCB4"
    neck = c.neck_z

    # ---- fitted coral top, scoop neck, puffed short sleeves
    top_faces = lambda C, FW: (G.bone_sum(FW, TORSO + ("upperarm_l", "upperarm_r")) > 0.5) & (C[:, 2] > wz - 0.1)
    scoop = lambda P, W: front_back(P, (c.clav_z + 0.03 - 0.085 * k * np.sqrt(np.clip(1 - (P[:, 0] / (0.1 * k)) ** 2, 0, 1))) - P[:, 2],
                                    (c.clav_z + 0.03) - P[:, 2], y0=-0.01, w=0.05)
    top_f = G.fmin(scoop, lambda P, W: P[:, 2] - (wz - 0.05),
                   G.limb_plane(c.B["upperarm_l"], 0.42), G.limb_plane(c.B["upperarm_r"], 0.42))

    def puff(P, N, W):
        out = 0.002 * G.vnoise(P, 0.04, 2)
        for s in ("l", "r"):
            h, t = c.B[f"upperarm_{s}"]
            d = (t - h) / np.linalg.norm(t - h)
            a = ((P - h) @ d) / np.linalg.norm(t - h)
            out = out + 0.016 * np.sin(np.pi * np.clip(a / 0.42, 0, 1)) * (G.bone_sum(W, (f"upperarm_{s}",)) > 0.5) * (1 + 0.3 * np.sin(np.arctan2(P[:, 1], P[:, 0]) * 10))
        return out
    top, _ = c.garment("top", top_faces, top_f, 0.008, 0.003, fabric(coral, 0.05, 0.07, 1, fade=0.1, shade=0.15), relax=8, extra=puff,
                       hems=[(0.0035, "#B85846", lambda L: L[:, 2].mean() > c.clav_z - 0.12 * k or True)])

    # ---- flared skirt (procedural, higher resolution), gold hem band, waistband
    hem_z = float(c.B["calf_l"][0][2]) - 0.12 * k
    rings, segs = 16, 72
    legs = G.bone_sum(W, ("pelvis", "spine_01", "thigh_l", "thigh_r", "calf_l", "calf_r")) > 0.6
    centre = P[(np.abs(P[:, 2] - wz) < 0.03) & (G.bone_sum(W, ("spine_01", "pelvis", "spine_02")) > 0.5)].mean(axis=0)
    lower = P[legs & (P[:, 2] < wz + 0.03) & (P[:, 2] > hem_z)]
    verts, faces = [], []
    prof = None
    for j in range(rings + 1):
        u = j / rings
        z = wz - (wz - hem_z) * u
        sl = lower[np.abs(lower[:, 2] - z) < 0.035]
        q = sl - centre; q[:, 2] = 0
        row = []
        for s in range(segs):
            a = 2 * math.pi * s / segs
            dv = np.array([math.cos(a), math.sin(a), 0])
            proj = q @ dv
            mm = (q @ np.array([-dv[1], dv[0], 0])) ** 2 < 0.03 ** 2
            row.append(proj[mm].max() if mm.any() else 0.15)
        row = np.array(row)
        for _ in range(3):
            row = (np.roll(row, 1) + 2 * row + np.roll(row, -1)) / 4
        prof = row if prof is None else np.maximum(row, prof * 0.98)
        for s in range(segs):
            a = 2 * math.pi * s / segs
            dv = np.array([math.cos(a), math.sin(a), 0])
            flute = 0.02 * u ** 1.2 * math.sin(a * 11 + 0.6 + 0.6 * math.sin(a * 3))
            rr = prof[s] + 0.012 + 0.21 * u ** 1.5 + flute
            verts.append(tuple(np.array([centre[0], centre[1], z]) + dv * rr * np.array([1, 0.92, 1])))
    for j in range(rings):
        for s in range(segs):
            s2 = (s + 1) % segs
            faces.append((j * segs + s, (j + 1) * segs + s, (j + 1) * segs + s2, j * segs + s2))
    bm = bmesh.new(); G.add_geom(bm, verts, faces)
    sk = G.bm_to_object(bm, "skirt", c.coll)
    hem_ring = np.array(verts[rings * segs:])
    G.thicken(sk, 0.005)
    Ps = hero.get_co(sk.data)
    Ws = np.zeros((len(Ps), len(BONES)))
    t = np.clip((wz - Ps[:, 2]) / (wz - hem_z), 0, 1)
    Ws[:, BI["pelvis"]] = 1 - 0.65 * t
    Ws[:, BI["thigh_l"]] = 0.65 * t * np.clip(0.5 + Ps[:, 0] * 8, 0, 1)
    Ws[:, BI["thigh_r"]] = 0.65 * t * np.clip(0.5 - Ps[:, 0] * 8, 0, 1)
    hero.set_groups(sk, Ws)
    gold_c = np.asarray(rgb("#C99A3A"))
    G.paint_vertices(sk, lambda P, N, W: np.where((P[:, 2] < hem_z + 0.055 * k)[:, None], gold_c * (1 + 0.05 * G.vnoise(P, 0.03, 3))[:, None],
                                                    fabric(coral, 0.05, 0.08, 4, shade=0.18)(P, N, W)), smooth=True, sharp_angle=1.1)
    hero.assign(sk); c.add("skirt", sk, "clothing")
    bm = bmesh.new()
    G.ring_tube(bm, G.smooth_path(hem_ring + np.array([0, 0, 0.003]), 1), 0.006, sides=6)
    G.ring_tube(bm, G.smooth_path((hem_ring - np.array([centre[0], centre[1], 0])) * np.array([1.0, 1.0, 1]) * 0.995 + np.array([centre[0], centre[1], 0.055 * k]), 1), 0.0035, sides=5)
    hm = G.bm_to_object(bm, "skirt_hem", c.coll); G.copy_weights_from(hm, Ps, Ws)
    G.paint_vertices(hm, lambda P, N, W: np.tile(rgb("#B8862E"), (len(P), 1)), smooth=True); hero.assign(hm); c.add("skirt_hem", hm, "clothing")
    bm = bmesh.new()
    top_ring = np.array(verts[:segs])
    for dz, rr in ((0.012, 0.011),):
        G.ring_tube(bm, G.smooth_path((top_ring - centre * np.array([1, 1, 0])) * 1.0 + centre * np.array([1, 1, 0]) + np.array([0, 0, dz]), 1), rr, sides=7)
    c.solid("waistband", bm, fabric("#C4604E", 0.04, 0.04, 5), cat="clothing", weights={"pelvis": 0.6, "spine_01": 0.4})
    G.hide_body_under(c.body, lambda P, W: np.where(legs & (P[:, 2] < wz - 0.02) & (P[:, 2] > hem_z + 0.04), 1.0, -1.0) * 1.0, margin=0.0,
                      sel=lambda P_, W_: (P_[:, 2] < wz - 0.02) & (P_[:, 2] > hem_z + 0.05) & (G.bone_sum(W_, ("pelvis", "thigh_l", "thigh_r")) > 0.5))

    # ---- apron: cream, gathered at the waist, patch pocket, ties and a bow
    av, af = [], []
    cols_n, arow = 17, 12
    for j in range(arow + 1):
        u = j / arow
        jj = min(rings, int(round(u * rings * 0.72)))
        for q_ in range(cols_n):
            a = -math.pi / 2 + (q_ / (cols_n - 1) - 0.5) * 1.6
            s = int(round((a % (2 * math.pi)) / (2 * math.pi) * segs)) % segs
            p = np.array(verts[jj * segs + s])
            dv = np.array([math.cos(a), math.sin(a), 0])
            gather = 0.006 * (1 - u) * math.sin(q_ * 2.4)
            av.append(tuple(p + dv * (0.014 + gather + 0.003 * u)))
    for j in range(arow):
        for q_ in range(cols_n - 1):
            af.append((j * cols_n + q_, (j + 1) * cols_n + q_, (j + 1) * cols_n + q_ + 1, j * cols_n + q_ + 1))
    bm = bmesh.new(); G.add_geom(bm, av, af)
    ap = G.bm_to_object(bm, "apron", c.coll)
    Pa = hero.get_co(ap.data)
    bm = G.piping(ap, 0.0025)
    ae = G.bm_to_object(bm, "apron_hem", c.coll); G.copy_weights_from(ae, Ps, Ws)
    G.paint_vertices(ae, fabric("#D9C79C", 0.03, 0.04, 6), smooth=True); hero.assign(ae); c.add("apron_hem", ae, "clothing")
    G.copy_weights_from(ap, Ps, Ws)
    c.keep_pre("apron", ap)
    G.thicken(ap, 0.004)
    G.paint_vertices(ap, fabric(cream, 0.05, 0.06, 7, shade=0.12), smooth=True); hero.assign(ap); c.add("apron", ap, "clothing")
    pk_z = wz - (wz - hem_z) * 0.33
    pf = lambda P, W: np.minimum(0.06 * k - np.abs(P[:, 0] - 0.02), 0.045 * k - np.abs(P[:, 2] - pk_z))
    c.patch("apron", "apron_pocket", pf, 0.003, 0.003, fabric("#E3D2A8", 0.04, 0.04, 8), hems=[(0.002, "#C9B585")])
    back = P[(np.abs(P[:, 2] - wz) < 0.03) & legs][:, 1].max() + 0.02
    bm = bmesh.new()
    for sx in (1, -1):
        loop = np.array([(sx * (0.012 + 0.032 * (1 - math.cos(a))), back + 0.012 * math.sin(a), wz + 0.008 + 0.028 * math.sin(a))
                         for a in np.linspace(0, 2 * math.pi, 18, endpoint=False)])
        G.ring_tube(bm, loop, 0.0055, sides=6)
        tail = np.array([(sx * 0.01, back + 0.004, wz), (sx * 0.022, back + 0.01, wz - 0.06), (sx * 0.03, back + 0.006, wz - 0.13)])
        G.ring_tube(bm, G.resample(tail, 0.01, closed=False), 0.006, sides=6, closed=False)
    G.ellipsoid(bm, (0, back + 0.006, wz + 0.006), (0.012, 0.01, 0.014), segs=10, rings=6)
    c.solid("apron_bow", bm, fabric(cream, 0.04, 0.03, 9), cat="clothing", weights={"pelvis": 0.5, "spine_01": 0.5})

    # ---- headwrap: wrapped volume over the whole scalp, madras checks, knot on top
    wf = c.hair_field(front=0.62, side=0.15, back=-0.6, temple_dip=0.0, ear_clear=0.02)
    hc = c.hc

    def wrap_thick(P):
        d = (P - hc) / c.hr
        return (0.022 + 0.045 * np.clip(d[:, 2] + 0.1, 0, 1.2) ** 1.4 + 0.03 * np.clip(d[:, 1], 0, 1) * np.clip(d[:, 2] + 0.5, 0, 1)) * k

    folds = lambda P, N: 0.006 * k * np.abs(np.sin((P[:, 2] * 0.8 + P[:, 1] * 0.55 + np.abs(P[:, 0]) * 0.3) * 95))

    A1 = np.array([1.0, 0.0, 0.3]); A1 /= np.linalg.norm(A1)
    A2 = np.array([-0.3, 0.2, 1.0]); A2 /= np.linalg.norm(A2)
    cell = 1 / 70

    def madras(P, N, b, g):
        a = np.floor((P @ A1) / cell + 1000).astype(int) % 7
        bb = np.floor((P @ A2) / cell + 1000).astype(int) % 7
        base = np.where(((a + bb) % 2 == 0)[:, None], np.array([0.72, 0.12, 0.1]), np.array([0.84, 0.22, 0.14]))
        base = np.where(((a == 0) | (bb == 0))[:, None], np.array([0.86, 0.64, 0.2]), base)
        base = np.where(((a == 3) | (bb == 4))[:, None], np.array([0.15, 0.36, 0.2]), base)
        return base * (1 - 4 * np.clip(g, 0, 0.06))[:, None]
    madras_f = lambda C, N, I: madras(C, N, None, np.zeros(len(C)))
    c.hair_volume("headwrap", wf, wrap_thick, madras, subdiv=1, grooves=lambda P, N: folds(P, N) * np.clip((wf(P, np.ones((len(P), len(BONES)))) / (0.03 * k)), 0, 1),
                  cat="hat", taper=0.006, sharp=0.7, cuts=[(A1, cell), (A2, cell)], face_colour=madras_f,
                  rim=(0.011 * k, madras_f))
    top = hero.get_co(c.parts["headwrap"][0].data)
    tz = top[:, 2].max()
    ty = top[np.argmax(top[:, 2]), 1]
    bm = bmesh.new()
    for sx in (1, -1):
        loop = []
        for a in np.linspace(0, 2 * math.pi, 22, endpoint=False):
            loop.append((sx * (0.01 + 0.035 * (1 - math.cos(a))), ty + 0.01 + 0.018 * math.sin(a) * 0.6, tz - 0.012 + 0.03 * math.sin(a) + 0.01 * (1 - math.cos(a))))
        G.ring_tube(bm, np.array(loop), 0.012, sides=8)
    G.ellipsoid(bm, (0, ty + 0.01, tz), (0.018, 0.02, 0.016), segs=10, rings=6)
    c.solid("headwrap_knot", bm, lambda P, N, W: madras(P, N, None, np.zeros(len(P))), cat="hat", weights={"head": 1.0}, sharp=0.7)

    # ---- gold hoop earrings at the lobes
    bm = bmesh.new()
    for side, sx in (("l", 1), ("r", -1)):
        t = mh.target(f"ears/{side}-ear-lobe-incr")
        lobe = c.info["V_full"][t[0]]
        lobe = lobe[np.argsort(lobe[:, 2])[:6]].mean(axis=0)
        G.torus(bm, lobe + np.array([sx * 0.004, 0, -0.024]), (1, 0, 0), 0.022, 0.0024, segs=28, sides=8)
    c.solid("earrings", bm, "#E0B23E", weights={"head": 1.0}, mat=hero.char_material_metal(), sharp=1.2)
    sandals(c, "#7A4A2A")
    c.finish()

    # basket of fruit on her left hip: woven sides, rim, base (rides on the pelvis)
    hipj = c.info["joints"]["joint-l-upper-leg"]
    bc = np.array([hipj[0] + 0.21 * k, hipj[1] - 0.02, c.hip_z + 0.01])
    bm = bmesh.new()
    segs_b, rows_b = 40, 9
    vb, fb = [], []
    for j in range(rows_b + 1):
        u = j / rows_b
        for s in range(segs_b):
            a = 2 * math.pi * s / segs_b
            weave = 0.004 * math.sin(a * 20 + (j % 2) * math.pi) * math.sin(u * math.pi * rows_b)
            r = 0.12 + 0.06 * u + weave
            vb.append((bc[0] + math.cos(a) * r, bc[1] + math.sin(a) * r * 0.85, bc[2] - 0.09 + 0.17 * u))
    for j in range(rows_b):
        for s in range(segs_b):
            s2 = (s + 1) % segs_b
            fb.append((j * segs_b + s, j * segs_b + s2, (j + 1) * segs_b + s2, (j + 1) * segs_b + s))
    G.add_geom(bm, vb, fb)
    G.cylinder(bm, (bc[0], bc[1], bc[2] - 0.095), (bc[0], bc[1], bc[2] - 0.088), 0.12, segs=segs_b)
    G.torus(bm, (bc[0], bc[1], bc[2] + 0.082), (0, 0, 1), 0.18, 0.013, segs=segs_b, sides=8)
    basket = G.bm_to_object(bm, "basket", c.coll)
    G.thicken(basket, 0.006, offset=0)
    G.paint_vertices(basket, lambda P, N, W: np.where((np.floor((P[:, 2] - bc[2]) * 50) % 2 == 0)[:, None], np.array([0.74, 0.56, 0.32]),
                                                      np.array([0.6, 0.43, 0.24])) * (1 + 0.08 * G.vnoise(P, 0.01, 2))[:, None], smooth=True, sharp_angle=1.0)
    hero.assign(basket); hero.attach_to_bone(basket, c.rig, "pelvis"); c.add("basket", basket, "held")
    bm_m, bm_b, bm_l = bmesh.new(), bmesh.new(), bmesh.new()
    for q_ in range(5):
        a = q_ * 1.3
        p = bc + np.array([math.cos(a) * 0.075, math.sin(a) * 0.06, 0.07])
        G.ellipsoid(bm_m, p, (0.052, 0.04, 0.036), G.orient((math.cos(a), math.sin(a), 0.4)), segs=14, rings=9)
    for q_ in range(4):
        pts = np.array([bc + np.array([-0.07 + 0.016 * q_, -0.05 + 0.03 * u - 0.012 * q_, 0.1 + 0.07 * math.sin(math.pi * u * 0.8) + 0.04 * u]) for u in np.linspace(0, 1, 10)])
        G.tube_path(bm_b, list(pts), 0.016, sides=7, radii=[0.004, 0.01, 0.015, 0.017, 0.017, 0.017, 0.016, 0.013, 0.009, 0.003])
    for q_ in range(4):
        a = 2.2 + q_ * 0.55
        G.ellipsoid(bm_l, bc + np.array([math.cos(a) * 0.115, math.sin(a) * 0.09, 0.1]), (0.026, 0.024, 0.024), segs=12, rings=8)
    mango = lambda P, N, W: G.mixc(np.tile([0.95, 0.6, 0.12], (len(P), 1)), np.array([0.8, 0.22, 0.12]), np.clip(N[:, 2] + 0.3 * G.vnoise(P, 0.02, 3), 0, 1))
    c.held("mangoes", bm_m, "pelvis", mango, mat=hero.char_material_gloss(), sharp=1.3)
    c.held("bananas", bm_b, "pelvis", lambda P, N, W: np.tile([0.96, 0.82, 0.26], (len(P), 1)) * (1 + 0.06 * G.vnoise(P, 0.01, 5))[:, None], sharp=0.5)
    c.held("limes", bm_l, "pelvis", lambda P, N, W: np.tile([0.42, 0.7, 0.2], (len(P), 1)) * (1 + 0.08 * G.vnoise(P, 0.008, 6))[:, None], mat=hero.char_material_gloss(), sharp=1.3)
    # a mango in her right hand, the one she offers to customers (hand_fruit)
    grip, along = c.hand_frame("r")
    side = np.cross(along, (0, 0, 1)); side /= np.linalg.norm(side) + 1e-9
    palm = np.cross(along, side)
    bm = bmesh.new()
    G.ellipsoid(bm, grip + along * 0.03 * k - palm * 0.035 * k, (0.05, 0.04, 0.036), G.orient(along, (0, 0, 1)), segs=14, rings=9)
    c.held("mango_in_hand", bm, "hand_r", mango, mat=hero.char_material_gloss(), sharp=1.3)
    c.relaxed(up_l=(0.45, 0.05, -1), lo_l=(0.55, -0.55, -0.35))
    return c


# ====================================================================== C
def build_C():
    c = Char("C"); c.build_body(); k = c.k; rng = c.rng
    c.paint_skin(lips="#4A2A22", blush=0.1, age=1.0)
    c.eyes()
    white = lambda P, N, b, g: G.mixc(np.tile([0.95, 0.94, 0.9], (len(P), 1)), np.array([0.68, 0.66, 0.62]), np.clip(g / (0.0035 * k), 0, 1))
    # full white beard: thick at the chin, grooved locks, hanging below the jaw
    bf = lambda P, W: c.beard_field(P, W, moustache=True, chin_drop=0.1)
    m = c.m

    def beard_t(P):
        below = np.clip((m[2] - P[:, 2]) / (0.07 * k), 0, 1)
        return (0.008 + 0.018 * below) * k

    def drop(P):
        below = np.clip((m[2] + 0.01 - P[:, 2]) / (0.08 * k), 0, 1)
        front = np.clip(-(P[:, 1] - m[1]) / (0.06 * k) + 0.5, 0, 1)
        d = np.zeros_like(P)
        d[:, 2] = -0.035 * k * below ** 1.3 * (0.4 + 0.6 * front) * (1 + 0.12 * G.vnoise(P, 0.02, 4))
        d[:, 1] = -0.008 * k * below
        return d
    lock = lambda P, N: 0.0035 * k * np.abs(np.sin(P[:, 0] * 260 + 2.0 * np.sin(P[:, 2] * 90)))
    c.hair_volume("beard", bf, beard_t, white, subdiv=1, grooves=lock, drop=drop, taper=0.006)
    # moustache: two lobes drooping past the mouth corners
    mf = lambda P, W: np.minimum(np.minimum((m[2] + 0.022 * k) - P[:, 2], P[:, 2] - (m[2] + 0.004 * k)),
                                 np.minimum(0.04 * k - np.abs(P[:, 0] - m[0]), np.where(P[:, 1] < m[1] + 0.02, 1.0, -1.0)))

    def mdrop(P):
        d = np.zeros_like(P)
        ax = np.abs(P[:, 0] - m[0])
        d[:, 2] = -0.012 * k * smoothstep(0.012 * k, 0.04 * k, ax)
        d[:, 1] = -0.004 * k
        return d
    c.hair_volume("moustache", mf, lambda P: np.full(len(P), 0.007 * k), white, subdiv=2,
                  grooves=lambda P, N: 0.002 * k * np.abs(np.sin(P[:, 0] * 420)), drop=mdrop, taper=0.004)
    hf = c.hair_field(front=0.75, side=0.05, back=-0.85, temple_dip=0.05)
    c.hair_volume("hair", hf, lambda P: np.full(len(P), 0.008 * k), white, subdiv=0,
                  grooves=lambda P, N: 0.003 * k * np.abs(np.sin(P[:, 2] * 220 + P[:, 1] * 60)), taper=0.01)
    c.hair_volume("brows", c.brow_field(0.24, 1.45), lambda P: np.full(len(P), 0.0045 * k), white, subdiv=2,
                  grooves=lambda P, N: 0.002 * k * np.abs(np.sin(P[:, 0] * 500 - P[:, 2] * 300)), taper=0.004)

    wz, P, W = c.waist_z, c.P, c.W
    cream, cardi, khaki = "#E9DFC6", "#6F8193", "#B59E73"
    neck = c.neck_z

    # ---- cream shirt with a proper collar (shows at the neck and cuffs)
    shirt_faces = lambda C, FW: (G.bone_sum(FW, TORSO + ARM_L + ARM_R) > 0.5) & (C[:, 2] > wz - 0.12)
    shirt_f = G.fmin(lambda P, W: (neck - 0.004 - 0.02 * k * np.clip(1 - np.abs(P[:, 0]) / (0.03 * k), 0, 1) * (P[:, 1] < 0)) - P[:, 2],
                     lambda P, W: P[:, 2] - (wz - 0.08),
                     G.limb_plane(c.B["lowerarm_l"], 0.92), G.limb_plane(c.B["lowerarm_r"], 0.92))
    shirt, _ = c.garment("shirt", shirt_faces, shirt_f, 0.005, 0.0025, fabric(cream, 0.04, 0.07, 1), rim_only=True)
    col = G.collar(c.pre["shirt"], lambda L: L[:, 2].mean() > neck - 0.05, 0.026 * k, 0.03 * k, 0.003, c.coll, "C_collar", points=0.04 * k)
    G.copy_weights_from(col, c.P, c.W); G.paint_vertices(col, fabric(cream, 0.03, 0.04, 2), smooth=True); hero.assign(col)
    c.add("collar", col, "clothing")

    # ---- cardigan: V-neck, ribbed hem and cuffs, five buttons, two pockets
    cardi_faces = lambda C, FW: (G.bone_sum(FW, TORSO + ARM_L + ARM_R) > 0.5) & (C[:, 2] > c.hip_z - 0.12)
    vz = c.clav_z - 0.2 * k
    vneck = lambda P, W: front_back(P, np.abs(P[:, 0] - 0.004) - (0.008 * k + 0.45 * np.clip(P[:, 2] - vz, 0, None)), (neck - 0.02) - P[:, 2], y0=-0.02, w=0.03)
    cardi_f = G.fmin(vneck, lambda P, W: P[:, 2] - (c.hip_z - 0.03), lambda P, W: (neck - 0.015) - P[:, 2],
                     G.limb_plane(c.B["lowerarm_l"], 0.84), G.limb_plane(c.B["lowerarm_r"], 0.84))

    def knit(P, N, W):
        rib = np.zeros(len(P))
        near_hem = np.exp(-((P[:, 2] - (c.hip_z - 0.015)) / 0.02) ** 2)
        rib += 0.0025 * near_hem * np.abs(np.sin(np.arctan2(P[:, 1], P[:, 0]) * 70))
        for s in ("l", "r"):
            h, t = c.B[f"lowerarm_{s}"]; dd = (t - h) / np.linalg.norm(t - h)
            a = ((P - h) @ dd) / np.linalg.norm(t - h)
            cuff = np.exp(-((a - 0.79) / 0.05) ** 2) * (G.bone_sum(W, (f"lowerarm_{s}",)) > 0.5)
            rib += 0.003 * cuff * np.abs(np.sin(np.arctan2(P[:, 1], P[:, 0] - h[0]) * 40)) - 0.004 * cuff
        return rib + 0.004 * G.vnoise(P, 0.05, 3) + 0.006 * np.exp(-((P[:, 2] - wz) / 0.05) ** 2)
    cd, _ = c.garment("cardigan", cardi_faces, cardi_f, 0.016, 0.006, fabric(cardi, 0.06, 0.05, 4, fade=0.1, shade=0.2), extra=knit,
                      subdiv=0, hems=[(0.005, "#5E6F80", lambda L: L[:, 2].max() - L[:, 2].min() > 0.2)])
    bm = bmesh.new()
    for j in range(5):
        z = vz - 0.015 - j * (vz - c.hip_z + 0.01) / 5.0
        hit, nn = G.surface_hit(G.bvh_of(cd), (0.028 * k, -0.6, z), (0, 1, 0))
        if hit is not None:
            G.cylinder(bm, hit + nn * 0.001, hit + nn * 0.006, 0.0085, segs=12)
    c.solid("cardigan_buttons", bm, "#4A3A2C", mat=hero.char_material_gloss())
    for sx in (1, -1):
        pf = lambda P, W, sx=sx: np.minimum(np.minimum(0.04 * k - np.abs(P[:, 0] - sx * 0.1 * k), 0.035 * k - np.abs(P[:, 2] - (c.hip_z + 0.06 * k))),
                                            np.where(P[:, 1] < 0, 1.0, -1.0))
        c.patch("cardigan", f"pocket_{'l' if sx > 0 else 'r'}", pf, 0.004, 0.004, fabric("#66788A", 0.05, 0.04, 6), hems=[(0.003, "#5E6F80")])

    # ---- khaki trousers with turn-ups and a front crease
    trouser_faces = lambda C, FW: (G.bone_sum(FW, NOT_LOWER) < 0.5) & (C[:, 2] < wz + 0.06)
    trouser_f = G.fmin(lambda P, W: (wz + 0.01) - P[:, 2], G.limb_plane(c.B["calf_l"], 0.93), G.limb_plane(c.B["calf_r"], 0.93))

    def crease(P, N, W):
        out = 0.004 * G.vnoise(P, 0.05, 7)
        for s, sx in (("l", 1), ("r", -1)):
            h, t = c.B[f"thigh_{s}"]
            cx = h[0]
            out += 0.003 * np.exp(-((P[:, 0] - cx) / 0.006) ** 2) * (P[:, 1] < h[1]) * (G.bone_sum(W, (f"thigh_{s}", f"calf_{s}")) > 0.5)
        out += 0.006 * np.exp(-((P[:, 2] - 0.06) / 0.04) ** 2) * np.abs(np.sin(P[:, 2] * 160))
        return out
    trousers, _ = c.garment("trousers", trouser_faces, trouser_f, 0.012, 0.004, fabric(khaki, 0.06, 0.08, 8, fade=0.15, shade=0.2), extra=crease,
                            hems=[(0.009, "#A68F64", lambda L: L[:, 2].mean() < 0.2)])
    sandals(c, "#5A3A24")
    grey = np.asarray(rgb("#7E7E80"))
    hat, hi = hat_shell(c, "flatcap", lambda P, N, W: grey * (1 + 0.08 * G.vnoise(P, 0.012, 9) + 0.04 * np.sin(P[:, 0] * 300))[:, None],
                        base_lift=0.06, tilt=0.15, crown_h=0.085, bulge=1.12, brim=(0.075, 0.0, 0.0), droop=0.25, forward=0.035, flat=0.85,
                        thick=0.007, rings=7)
    bm = bmesh.new()
    top = hi["ctr"] + hi["axis"] * hi["H"] + np.array([0, -0.035 * k, 0])
    G.ellipsoid(bm, top, (0.009, 0.009, 0.005), segs=10, rings=5)
    pts = [hi["ctr"] + dv * hi["rs"][s] * 1.005 + hi["axis"] * 0.006 for s, dv in enumerate(hi["dirs"])]
    G.ring_tube(bm, np.array(pts), 0.004, sides=6)
    c.solid("cap_band", bm, "#5E5E62", cat="hat", weights={"head": 1.0})
    c.finish()
    # stoop + arms; cane in the right hand, net over the left forearm (built in pose, attached to bones)
    c.rest()
    c.rotate("spine_02", (1, 0, 0), -7); c.rotate("spine_03", (1, 0, 0), -9); c.rotate("neck_01", (1, 0, 0), 10)
    c.rotate("head", (1, 0, 0), 6)
    c.aim("upperarm_l", (0.25, 0.1, -1)); c.aim("lowerarm_l", (0.15, -1, -0.12))
    c.aim("upperarm_r", (-0.35, -0.05, -1)); c.aim("lowerarm_r", (-0.2, -0.65, -0.75))
    c.curl_fingers(0.9, ("r",)); c.curl_fingers(0.3, ("l",))
    h, t, Mw = c.bone_world("hand_r")
    grip = t + (t - h) * 0.4
    bm = bmesh.new()
    base = np.array([grip[0] - 0.03, grip[1] - 0.12, 0.0])
    shaft = np.array([base + (grip + np.array([0, 0, 0.03]) - base) * u for u in np.linspace(0, 1, 12)])
    G.ring_tube(bm, shaft, 0.012, sides=10, closed=False)
    crook = np.array([grip + np.array([0, -math.sin(a) * 0.05, 0.03 + math.sin(a * 0.5) * 0.045]) for a in np.linspace(0, math.pi, 12)])
    G.ring_tube(bm, crook, 0.012, sides=10, closed=False)
    G.cylinder(bm, base + np.array([0, 0, 0.0]), base + np.array([0, 0, 0.03]), 0.014, segs=10)
    c.held("cane", bm, "hand_r", lambda P, N, W: np.where((P[:, 2] < 0.03)[:, None], np.array([0.15, 0.12, 0.1]),
                                                           np.array([0.45, 0.29, 0.16]) * (1 + 0.15 * np.sin(P[:, 2] * 200 + G.vnoise(P, 0.02, 1) * 3))[:, None]), sharp=0.9)
    h, t, Mw = c.bone_world("lowerarm_l")
    axis = t - h
    nu, nv = 13, 17
    grid = np.zeros((nu, nv, 3))
    for i in range(nu):
        bp = h + axis * (0.2 + 0.65 * i / (nu - 1))
        for j in range(nv):
            v = j / (nv - 1); side = -1 if v < 0.5 else 1; dd = abs(v - 0.5) * 2
            over = bp + np.array([0, side * 0.05 * (1 - math.cos(min(1, dd * 4) * math.pi / 2)), 0.04 * (1 - dd * 3) if dd < 0.33 else 0])
            drop_ = max(0, dd - 0.15) * 0.45
            grid[i, j] = over + np.array([0.012 * math.sin(i * 1.7 + j), side * (0.055 + 0.02 * math.sin(i)), -drop_ - 0.03 * dd])
    bm = bmesh.new(); bmk = bmesh.new(); bmf = bmesh.new()
    for i in range(nu):
        G.ring_tube(bm, grid[i], 0.0016, sides=4, closed=False)
    for j in range(nv):
        G.ring_tube(bm, grid[:, j], 0.0016, sides=4, closed=False)
    for i in range(nu):
        for j in range(nv):
            G.ellipsoid(bmk, grid[i, j], (0.0034, 0.0034, 0.0034), segs=5, rings=3)
    G.ellipsoid(bmf, grid[nu - 1, nv - 1] + np.array([0, 0, -0.035]), (0.03, 0.03, 0.04), segs=14, rings=9)
    c.held("net", bm, "lowerarm_l", lambda P, N, W: np.tile([0.73, 0.65, 0.49], (len(P), 1)))
    c.held("net_knots", bmk, "lowerarm_l", lambda P, N, W: np.tile([0.6, 0.53, 0.38], (len(P), 1)))
    c.held("net_float", bmf, "lowerarm_l", lambda P, N, W: np.where((N[:, 2] > 0.3)[:, None], np.array([0.94, 0.92, 0.86]), np.array([0.82, 0.18, 0.13])),
           mat=hero.char_material_gloss(), sharp=1.3)
    return c


# ====================================================================== D
def build_D():
    c = Char("D"); c.build_body(); k = c.k; rng = c.rng
    c.paint_skin(lips="#4E2A22", blush=0.1)
    c.eyes()
    # short tight coils: a shaped hair volume with a crisp edged-up hairline
    hf = c.hair_field(front=0.92, side=0.32, back=-0.55, temple_dip=0.05, ear_clear=0.035)
    coils = c.coil_bumps(hf, 0.0075, 0.0045, 0.75, seed=7)

    def hair_t(P):
        d = (P - c.hc) / c.hr
        return (0.011 + 0.012 * np.clip(d[:, 2] + 0.2, 0, 1.2)) * k
    coil_col = lambda P, N, b, g: G.mixc(np.tile([0.035, 0.025, 0.02], (len(P), 1)), np.array([0.17, 0.12, 0.09]), np.clip(b / (0.004 * k), 0, 1) ** 1.5)
    c.hair_volume("hair", hf, hair_t, coil_col, subdiv=1, bumps=coils, taper=0.004, sharp=1.3)
    c.hair_volume("brows", c.brow_field(0.17, 1.3), lambda P: np.full(len(P), 0.0013 * k),
                  lambda P, N, b, g: np.tile([0.09, 0.065, 0.05], (len(P), 1)), subdiv=2, taper=0.006)
    wz, P, W = c.waist_z, c.P, c.W
    blue, white, yellow = np.asarray(rgb("#3F7DC0")), np.asarray(rgb("#F3EFE4")), "#E9B92F"
    neck = c.neck_z
    shirt_faces = lambda C, FW: (G.bone_sum(FW, TORSO + ("upperarm_l", "upperarm_r", "thigh_l", "thigh_r")) > 0.5) & (C[:, 2] > c.hip_z - 0.06)
    crew = lambda P, W: front_back(P, (neck - 0.012 - 0.02 * k * np.clip(1 - np.abs(P[:, 0]) / (0.06 * k), 0, 1)) - P[:, 2], (neck - 0.006) - P[:, 2])
    shirt_f = G.fmin(crew, lambda P, W: P[:, 2] - (c.hip_z - 0.01),
                     G.limb_plane(c.B["upperarm_l"], 0.5), G.limb_plane(c.B["upperarm_r"], 0.5))
    stripe_w = 0.024 * k

    def stripes(ob):
        G.plane_cuts(ob, (0, 0, 1), stripe_w)
    stripe_col = lambda C, N, I: np.where((np.floor(C[:, 2] / stripe_w) % 2 == 0)[:, None], blue, white) * (1 + 0.03 * G.vnoise(C, 0.05, 1))[:, None]
    shirt, _ = c.garment("shirt", shirt_faces, shirt_f, 0.007, 0.003, None, pattern=stripes, relax=3, face_colour=stripe_col,
                         extra=lambda P, N, W: 0.004 * G.vnoise(P, 0.04, 2) + 0.016 * smoothstep(wz + 0.03, wz - 0.02, P[:, 2]),
                         hems=[(0.004, "#F3EFE4", lambda L: L[:, 2].mean() < neck - 0.03)])
    # ribbed crew collar band
    col = G.collar(c.pre["shirt"], lambda L: L[:, 2].mean() > neck - 0.05, 0.014 * k, 0.003 * k, 0.003, c.coll, "D_collar")
    G.copy_weights_from(col, c.P, c.W)
    G.paint_vertices(col, lambda P, N, W: np.tile(rgb("#2F6CB0"), (len(P), 1)) * (1 - 0.12 * np.abs(np.sin(np.arctan2(P[:, 1] - c.hc[1], P[:, 0]) * 60)))[:, None], smooth=True)
    hero.assign(col); c.add("shirt_collar", col, "clothing")
    shorts_faces = lambda C, FW: (G.bone_sum(FW, NOT_LOWER + ("calf_l", "calf_r")) < 0.5) & (C[:, 2] < wz + 0.06)
    shorts_f = G.fmin(lambda P, W: (wz - 0.015) - P[:, 2], G.limb_plane(c.B["thigh_l"], 0.56), G.limb_plane(c.B["thigh_r"], 0.56))
    shorts, _ = c.garment("shorts", shorts_faces, shorts_f, 0.013, 0.004, fabric(yellow, 0.07, 0.07, 3, fade=0.2, shade=0.2),
                          extra=lambda P, N, W: 0.004 * G.vnoise(P, 0.03, 4) + 0.008 * np.clip((c.hip_z - P[:, 2]) / 0.15, 0, 1),
                          hems=[(0.006, "#D5A426", lambda L: L[:, 2].mean() < c.hip_z)])
    for sx in (1, -1):
        pf = lambda P, W, sx=sx: np.minimum(np.minimum(0.032 * k - np.abs(P[:, 0] - sx * 0.08 * k), 0.03 * k - np.abs(P[:, 2] - (c.hip_z - 0.02))),
                                            np.where(P[:, 1] > 0.0, 1.0, -1.0))
        c.patch("shorts", f"back_pocket_{'l' if sx > 0 else 'r'}", pf, 0.003, 0.003, fabric("#DDAE2A", 0.04, 0.03, 6), hems=[(0.0018, "#C2921C")])
    c.finish()
    c.relaxed(up_r=(-0.25, 0.0, -1), lo_r=(-0.12, -0.15, -1))
    c.curl_fingers(0.9, ("r",))
    hh, ht, _ = c.bone_world("middle_01_r")
    grip = hh + (ht - hh) * 0.6
    top = grip + np.array([0, 0, -0.035])
    bm = bmesh.new()
    segs = 28
    vb, fb = [], []
    prof = [(-0.15, 0.0), (-0.15, 0.058), (-0.01, 0.074), (-0.01, 0.068), (-0.14, 0.053)]
    for j, (zz, r) in enumerate(prof):
        for s in range(segs):
            a = 2 * math.pi * s / segs
            vb.append((top[0] + math.cos(a) * r, top[1] + math.sin(a) * r, top[2] + zz))
    for j in range(len(prof) - 1):
        for s in range(segs):
            s2 = (s + 1) % segs
            fb.append((j * segs + s, j * segs + s2, (j + 1) * segs + s2, (j + 1) * segs + s))
    G.add_geom(bm, vb, fb)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    G.torus(bm, (top[0], top[1], top[2] - 0.012), (0, 0, 1), 0.074, 0.006, segs=segs, sides=6)
    for sx in (1, -1):
        G.cylinder(bm, (top[0] + sx * 0.074, top[1], top[2] - 0.03), (top[0] + sx * 0.08, top[1], top[2] - 0.03), 0.008, segs=8)
    c.held("bucket", bm, "hand_r", lambda P, N, W: np.tile([0.95, 0.47, 0.12], (len(P), 1)) * (1 - 0.2 * (N[:, 2] > 0.9))[:, None],
           mat=hero.char_material_gloss(), sharp=0.6)
    bm = bmesh.new()
    arc = np.array([[top[0] + math.cos(a) * 0.078, top[1], top[2] - 0.03 + math.sin(a) * 0.065] for a in np.linspace(0, math.pi, 16)])
    G.ring_tube(bm, arc, 0.0022, sides=6, closed=False)
    c.held("bucket_handle", bm, "hand_r", lambda P, N, W: np.tile([0.55, 0.56, 0.58], (len(P), 1)), mat=hero.char_material_metal())
    return c


BUILDERS = {"A": build_A, "B": build_B, "C": build_C, "D": build_D}


def build(key):
    return BUILDERS[key]()
