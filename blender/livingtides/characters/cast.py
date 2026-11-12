"""The four hero villagers (owner's concept sketches): A fisher captain, B market
vendor, C elder net-mender, D harbour child.  `build(key)` returns a Character
with every part as its own object, all bound to one armature built from the
shared game_engine rig definition (the child's armature is the same rig at the
child's joint positions)."""
from __future__ import annotations
import math
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix
from . import hero, mh
from . import garments as G
from .hero import BONES, BI, rgb, jitter, mix

SPECS = {
    "A": dict(name="A_captain", title="Fisher captain", gender=1.0, age_years=45, muscle=0.66, weight=0.56, height=0.55,
              proportions=0.6, race={"african": 1.0}, head_scale=1.42, height_m=1.76, skin="#5E3A28", iris="#3A2416",
              detail={"head/head-age-incr": 0.35, "mouth/mouth-laugh-lines-in": 0.4, "eyes/l-eye-bag-incr": 0.35,
                      "eyes/r-eye-bag-incr": 0.35, "chin/chin-width-incr": 0.3, "head/head-square": 0.35,
                      "nose/nose-flaring-incr": 0.3, "eyebrows/eyebrows-trans-down": 0.3}),
    "B": dict(name="B_vendor", title="Market vendor", gender=0.0, age_years=33, muscle=0.5, weight=0.58, height=0.5,
              proportions=0.65, race={"african": 1.0}, head_scale=1.42, height_m=1.66, skin="#4A2C1F", iris="#2E1C12",
              detail={"mouth/mouth-lowerlip-volume-incr": 0.3, "cheek/l-cheek-bones-incr": 0.4, "cheek/r-cheek-bones-incr": 0.4,
                      "mouth/mouth-dimples-in": 0.4, "eyes/l-eye-scale-incr": 0.2, "eyes/r-eye-scale-incr": 0.2}),
    "C": dict(name="C_elder", title="Elder net-mender", gender=1.0, age_years=74, muscle=0.35, weight=0.45, height=0.42,
              proportions=0.5, race={"african": 0.75, "caucasian": 0.25}, head_scale=1.42, height_m=1.66, skin="#7A4E36",
              iris="#3B2A1C",
              detail={"head/head-age-incr": 1.0, "mouth/mouth-laugh-lines-in": 1.0, "eyes/l-eye-bag-incr": 0.8,
                      "eyes/r-eye-bag-incr": 0.8, "cheek/l-cheek-volume-decr": 0.5, "cheek/r-cheek-volume-decr": 0.5,
                      "nose/nose-scale-vert-incr": 0.3, "ears/l-ear-scale-incr": 0.3, "ears/r-ear-scale-incr": 0.3,
                      "neck/neck-double-incr": 0.3}),
    "D": dict(name="D_child", title="Harbour child", gender=0.85, age_years=8, muscle=0.5, weight=0.45, height=0.5,
              proportions=0.5, race={"african": 1.0}, head_scale=1.3, height_m=1.27, skin="#6A4430", iris="#3A2416",
              hand_scale=1.08, body_density=0.34,
              detail={"eyes/l-eye-scale-incr": 0.7, "eyes/r-eye-scale-incr": 0.7, "eyebrows/eyebrows-trans-up": 0.3,
                      "cheek/l-cheek-volume-incr": 0.3, "cheek/r-cheek-volume-incr": 0.3}),
}
BUDGET = {"A": (2300, 2500), "B": (2300, 2700), "C": (2300, 2400), "D": (2200, 2400)}   # (head, body) tris before hiding


class Char:
    def __init__(self, key):
        self.key = key
        self.spec = SPECS[key]
        self.rng = np.random.default_rng({"A": 11, "B": 22, "C": 33, "D": 44}[key])
        self.coll = bpy.data.collections.new(self.spec["name"])
        bpy.context.scene.collection.children.link(self.coll)
        self.parts = {}            # name -> (object, category)
        self.rig = None

    # -- geometry helpers ------------------------------------------------
    def along(self, bone, p):
        h, t = self.info["bones"][bone][:2]
        d = t - h
        return float(np.dot(p - h, d) / np.dot(d, d))

    def add(self, name, ob, cat):
        ob.name = f"{self.key}_{name}"
        self.parts[name] = (ob, cat)
        return ob

    def new_bm_object(self, name, bm, cat, colour, weights=None, gloss=False, metal=False, wmask=None):
        ob = G.bm_to_object(bm, name, self.coll)
        G.colour_faces(ob, colour, self.rng)
        hero.assign(ob, hero.char_material_metal() if metal else (hero.char_material_gloss() if gloss else None))
        if weights == "nearest" or weights is None:
            m = self.torso_mask() if wmask is None else wmask
            G.copy_weights_from(ob, self.P[m], self.W[m])
        elif isinstance(weights, dict):
            G.rigid_weights(ob, weights)
        return self.add(name, ob, cat)

    def solidify(self, ob, t):
        m = ob.modifiers.new("sol", "SOLIDIFY"); m.thickness = t; m.offset = -1; m.use_rim = True
        dg = bpy.context.evaluated_depsgraph_get()
        nm = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        ob.modifiers.remove(m); old = ob.data; ob.data = nm; bpy.data.meshes.remove(old)

    @property
    def hk(self):           # head size factor relative to the captain
        return self.info["head_r"] / 0.137

    # -- body ------------------------------------------------------------
    def build_body(self):
        s = self.spec
        self.body, self.info = hero.build_body(s, self.coll)
        self.lod_counts = hero.lod_body(self.body, *BUDGET[self.key])
        self.P, self.W = hero.body_arrays(self.body)
        self.bvh = G.bvh_of(self.body)
        self.add("body", self.body, "body")
        self.mouth = np.array(self.info["mouth"])
        J = self.info["joints"]
        self.waist_z = float(self.info["bones"]["spine_02"][0][2]) - 0.02 * self.hk
        self.hip_z = float(J["joint-pelvis"][2])

    def lip(self, p, n):
        r = p - self.mouth; k = self.hk
        return abs(r[0]) < 0.027 * k * (1 - (r[2] / (0.014 * k)) ** 2 * 0.3) and -0.013 * k < r[2] < 0.012 * k and n[1] < 0.25 and r[1] < 0.02

    def beard_zone(self, p, n, moustache=True):
        r = p - self.mouth; k = self.hk
        d = p - self.info["head_c"]
        if self.lip(p, n):
            return False
        if moustache and 0.006 * k < r[2] < 0.024 * k and abs(r[0]) < 0.034 * k and r[1] < 0.03:
            return True
        return -0.085 * k < r[2] < 0.004 * k and abs(r[0]) < 0.072 * k and (d[1] < 0.03 * k) and not (r[2] > -0.02 * k and abs(r[0]) > 0.055 * k)

    def paint_skin(self, stubble=0.0, lips="#3E2019"):
        base = rgb(self.spec["skin"])
        me = self.body.data
        part = np.zeros(len(me.polygons), dtype=np.int64)
        if "part" in me.attributes:
            me.attributes["part"].data.foreach_get("value", part)
        W = self.W
        polys = me.polygons
        lipc = rgb(lips)
        stub = mix(base, (0.07, 0.05, 0.04), 0.55)

        def col(p, n, i, rng):
            if part[i] == 1:
                return jitter((0.92, 0.89, 0.8), rng, 0.02)
            if part[i] == 2:
                return (0.55, 0.22, 0.22)
            if self.lip(p, n):
                return jitter(mix(base, lipc, 0.6), rng, 0.03)
            if stubble > 0 and self.beard_zone(p, n):
                return jitter(mix(base, stub, stubble), rng, 0.05)
            w = W[list(polys[i].vertices)].mean(axis=0)
            b = BONES[int(np.argmax(w))]
            if b.endswith(("_03_l", "_03_r")) and n[2] > 0.3:
                return jitter(mix(base, (0.78, 0.6, 0.52), 0.35), rng, 0.02)          # fingernail facets
            # weathered: forehead and cheekbones a touch darker / warmer
            c = jitter(base, rng, 0.03)
            if w[BI["head"]] > 0.5 and n[1] < -0.5 and p[2] > self.info["eyes"]["l"][0][2] + 0.03 * self.hk:
                c = mix(c, (c[0] * 0.9, c[1] * 0.85, c[2] * 0.85), 0.5)
            return c
        G.colour_faces(self.body, col, self.rng)
        hero.assign(self.body)

    # -- hair ------------------------------------------------------------
    def eyebrows(self, colour, length=0.013, n=6, thick=0.0042):
        bm = bmesh.new()
        for side, sx in (("l", 1), ("r", -1)):
            e, r = self.info["eyes"][side]
            roots, nrm = [], []
            for k in range(n):
                t = k / (n - 1)
                x = e[0] + sx * (-0.9 * r + 2.1 * r * t)
                z = e[2] + 1.45 * r + 0.35 * r * math.sin(math.pi * min(1, t * 1.2)) - 0.2 * r * t
                hit, nn = G.surface_hit(self.bvh, (x, e[1] - 0.3, z), (0, 1, 0))
                if hit is not None:
                    roots.append(hit); nrm.append(nn)
            G.clumps(bm, roots, nrm, length * self.hk, thick * self.hk, self.rng, droop=(sx, 0, 0.15), droop_amt=0.85, taper=0.3)
        return self.new_bm_object("eyebrows", bm, "hair", G.solid(colour, amt=0.06), weights={"head": 1.0})

    def scalp(self, test, density=1.0):
        return G.scalp_points(self.body, self.info, test, density, self.rng)

    # -- shells ----------------------------------------------------------
    def dom(self, w):
        return BONES[int(np.argmax(w))]

    def limb_cut(self, bone, t, keep="head"):
        """Plane across a limb at fraction t along `bone`; removes the part toward
        the tail (keep='head') or toward the head (keep='tail')."""
        h, tl = self.info["bones"][bone][:2]
        d = (tl - h) / np.linalg.norm(tl - h)
        co = h + (tl - h) * t
        L = np.linalg.norm(tl - h)

        def region(p, h=h, d=d, L=L, co=co):
            a = np.dot(p - h, d)
            perp = np.linalg.norm((p - h) - a * d)
            return -0.35 * L < a < 1.35 * L and perp < 0.11 * self.hk and abs(np.dot(p - co, d)) < 0.35 * L
        return (co, d if keep == "head" else -d, region)

    def shell(self, name, sel, cat="clothing", **kw):
        ob = G.shell(self.body, name, sel, self.coll, rng=self.rng, **kw)
        return self.add(name, ob, cat)

    def torso_mask(self):
        keep = [BI[b] for b in ("pelvis", "spine_01", "spine_02", "spine_03", "clavicle_l", "clavicle_r", "thigh_l", "thigh_r", "neck_01")]
        return self.W[:, keep].sum(axis=1) > 0.6

    def torso_pts(self, extra=()):
        m = self.torso_mask()
        pts = [self.P[m]] + [hero.get_co(self.parts[n][0].data) for n in extra if n in self.parts]
        return np.vstack(pts)

    def band_obj(self, name, centre, axis, width, thick, colour, target=None, cat="clothing", weights="nearest", metal=False, wmask=None, **kw):
        bm = bmesh.new()
        G.band(bm, self.torso_pts() if target is None else target, centre, axis, width, thick, **kw)
        return self.new_bm_object(name, bm, cat, colour, weights, metal=metal, wmask=wmask)

    def limb_ring(self, name, bone, t, width, thick, colour, target=None, clearance=0.003, **kw):
        h, tl = self.info["bones"][bone][:2]
        c = h + (tl - h) * t
        tgt = self.P if target is None else target
        # only points belonging to that limb segment (avoid catching the torso or the other arm)
        bones = self.info["bones"]
        chain = [bone] + [b for b, v in bones.items() if v[3] == bone]
        if bones[bone][3]:
            chain.append(bones[bone][3])
        cols = [BI[b] for b in chain if b in BI]
        W = self.W[hero.nearest_idx(self.P, tgt)] if target is not None else self.W
        m = (W[:, cols].sum(axis=1) > 0.5) & (np.linalg.norm(tgt - c, axis=1) < 0.16 * max(1.0, self.hk))
        wm = self.W[:, cols].sum(axis=1) > 0.5
        return self.band_obj(name, c, tl - h, width, thick, colour, target=tgt[m], clearance=clearance, wmask=wm, **kw)

    # -- hats --------------------------------------------------------------
    def hat(self, name, colour_fn, base_lift=0.045, tilt=0.3, crown_h=0.12, bulge=1.0, brim=(0.06, 0.06, 0.09),
            droop=0.35, forward=0.0, segs=20, rings=5, thick=0.007, clearance=0.012, flat=0.0):
        k = self.hk
        e = self.info["eyes"]["l"][0]
        hc = self.info["head_c"]
        axis = np.array([0, tilt, 1.0]); axis /= np.linalg.norm(axis)
        c = np.array([0, hc[1], e[2] + base_lift * k])
        R = G.orient(axis); ex, ey = np.array(R.col[0]), np.array(R.col[1])
        head = self.P[self.W[:, BI["head"]] > 0.5]
        # radius per direction from the head points above the band (hat must clear them all)
        d = head - c
        h = d @ axis
        q = d - np.outer(h, axis)
        ang = np.arctan2(q @ ey, q @ ex)
        rad = np.linalg.norm(q, axis=1)
        top = float(h.max())
        rs = []
        for s in range(segs):
            a0 = -math.pi + 2 * math.pi * s / segs
            dd = np.abs(((ang - a0 + math.pi) % (2 * math.pi)) - math.pi)
            m = (dd < 2.2 * math.pi / segs) & (h > -0.01)
            rs.append(rad[m].max() if m.any() else rad.max())
        rs = np.array(rs)
        rs = (np.roll(rs, 1) + 2 * rs + np.roll(rs, -1)) / 4 + clearance
        verts, faces = [], []
        dirs = [math.cos(-math.pi + 2 * math.pi * s / segs) * ex + math.sin(-math.pi + 2 * math.pi * s / segs) * ey for s in range(segs)]
        H = max(crown_h * k, top + clearance)
        # brim (outer ring -> base ring), then crown rings, then apex
        for s, dv in enumerate(dirs):
            front = -dv[1]
            bl = brim[1] + (brim[0] - brim[1]) * max(0, front) + (brim[2] - brim[1]) * max(0, -front)
            bl *= k
            verts.append(tuple(c + dv * (rs[s] + bl) - axis * bl * droop))
        for j in range(rings):
            u = j / rings
            rr = np.sqrt(max(0.0, 1 - u ** 2)) if flat == 0 else (1 - flat * u ** 3)
            for s, dv in enumerate(dirs):
                shift = np.array([0, -forward * k * u, 0])
                verts.append(tuple(c + dv * rs[s] * (rr if j else 1.0) * (1 + (bulge - 1) * math.sin(math.pi * u)) + axis * H * u + shift))
        verts.append(tuple(c + axis * H + np.array([0, -forward * k, 0])))
        apex = len(verts) - 1
        for j in range(rings):
            for s in range(segs):
                s2 = (s + 1) % segs
                faces.append((j * segs + s, j * segs + s2, (j + 1) * segs + s2, (j + 1) * segs + s))
        last = rings * segs
        for s in range(segs):
            faces.append((last + s, last + (s + 1) % segs, apex))
        bm = bmesh.new()
        G.add_geom(bm, verts, faces)
        ob = G.bm_to_object(bm, name, self.coll)
        self.solidify(ob, thick)
        G.colour_faces(ob, colour_fn, self.rng)
        hero.assign(ob)
        G.rigid_weights(ob, {"head": 1.0})
        return self.add(name, ob, "hat")

    # -- rig -------------------------------------------------------------
    def finish(self):
        removed = G.delete_hidden(self.body)
        hero.add_shape_keys(self.body)
        self.rig = hero.build_armature(self.spec["name"], self.info["V_full"], self.coll)
        for n, (ob, cat) in self.parts.items():
            if cat == "held":
                continue
            if ob.parent is None:
                hero.bind(ob, self.rig)
        # facial hair follows the face shape keys from the nearest skin vertex
        src_P = hero.get_co(self.body.data)
        D = {}
        for kb in self.body.data.shape_keys.key_blocks[1:]:
            a = np.zeros(len(src_P) * 3); kb.data.foreach_get("co", a)
            D[kb.name] = a.reshape(-1, 3) - src_P
        for n in ("beard", "moustache", "stubble_hair", "eyebrows"):
            if n in self.parts:
                ob = self.parts[n][0]
                hero.add_shape_keys(ob, keys=list(D.keys()), source=(src_P, D))
        self.removed_faces = removed
        return self

    # -- posing ----------------------------------------------------------
    def rotate(self, bone, axis, deg):
        pb = self.rig.pose.bones[bone]
        M = pb.matrix.copy()
        head = M.to_translation()
        R = Matrix.Translation(head) @ Matrix.Rotation(math.radians(deg), 4, Vector(axis)) @ Matrix.Translation(-head)
        pb.matrix = R @ M
        bpy.context.view_layer.update()

    def rest(self):
        for pb in self.rig.pose.bones:
            pb.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()

    def aim(self, bone, direction):
        """Rotate a pose bone about its head so it points along `direction` (world)."""
        pb = self.rig.pose.bones[bone]
        M = pb.matrix.copy()
        cur = (pb.tail - pb.head).normalized()
        q = cur.rotation_difference(Vector(direction).normalized())
        head = M.to_translation()
        pb.matrix = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head) @ M
        bpy.context.view_layer.update()

    def relaxed(self, up_l=(0.22, 0.04, -1), up_r=(-0.22, 0.04, -1), lo_l=(0.1, -0.3, -1), lo_r=(-0.1, -0.3, -1)):
        self.rest()
        self.aim("upperarm_l", up_l); self.aim("lowerarm_l", lo_l)
        self.aim("upperarm_r", up_r); self.aim("lowerarm_r", lo_r)

    def bone_world(self, bone):
        pb = self.rig.pose.bones[bone]
        M = self.rig.matrix_world @ pb.matrix
        return np.array(M.to_translation()), np.array(self.rig.matrix_world @ pb.tail), M

    def held(self, name, bm, bone, colour, gloss=False, metal=False):
        ob = G.bm_to_object(bm, name, self.coll)
        G.colour_faces(ob, colour, self.rng)
        hero.assign(ob, hero.char_material_metal() if metal else (hero.char_material_gloss() if gloss else None))
        hero.attach_to_bone(ob, self.rig, bone)
        return self.add(name, ob, "held")

    def tris(self):
        return {n: hero.tri_count(ob) for n, (ob, c) in self.parts.items()}


# ====================================================================== A
def build_A():
    c = Char("A"); c.build_body(); rng = c.rng; k = c.hk
    c.paint_skin(stubble=0.75)
    eyes = G.eyes(c.info, c.coll, iris=c.spec["iris"], rng=rng)
    c.add("eye_l", eyes[0], "face"); c.add("eye_r", eyes[1], "face")
    c.eyebrows("#1E1410")
    # cropped hair showing under the hat brim at back and sides
    pts, nrm = c.scalp(lambda d, p: d[2] > -0.25 and d[2] < 0.3 and d[1] > -0.05 and abs(d[0]) < 0.95, 0.22)
    bm = bmesh.new(); G.curls(bm, pts, nrm, 0.007 * k, rng)
    c.new_bm_object("hair", bm, "hair", G.solid("#17110D", amt=0.08), weights={"head": 1.0})

    W, P = c.W, c.P
    wz = c.waist_z
    navy, teal, white = rgb("#26355A"), rgb("#2F8E86"), rgb("#EFEBE1")

    def shirt_sel(p, n, w):
        b = c.dom(w)
        if b in ("spine_01", "spine_02", "spine_03", "clavicle_l", "clavicle_r", "upperarm_l", "upperarm_r", "pelvis"):
            return p[2] > wz - 0.05 and w[BI["neck_01"]] < 0.35
        if b in ("lowerarm_l", "lowerarm_r"):
            return c.along(b, p) < 0.55
        return False
    c.shell("shirt", shirt_sel, rim_only=True, offset=0.007, thick=0.004, folds=0.0035, flare=0.004,
            cuts=[c.limb_cut("lowerarm_l", 0.4), c.limb_cut("lowerarm_r", 0.4)],
            colour=lambda p, n, i, r: jitter(mix(white, (0.86, 0.83, 0.74), r.random() * 0.4), r, 0.02))
    # rolled sleeves: thick turned-up cuffs
    for s in ("l", "r"):
        c.limb_ring(f"sleeve_roll_{s}", f"lowerarm_{s}", 0.36, 0.05 * k, 0.012, G.solid("#E6E0D2", amt=0.03))
    # open collar
    nb = c.info["bones"]["neck_01"]
    c.band_obj("collar", nb[0] + (nb[1] - nb[0]) * 0.15, nb[1] - nb[0], 0.028 * k, 0.006, G.solid("#F2EEE4", amt=0.02), clearance=0.006)

    def vest_sel(p, n, w):
        b = c.dom(w)
        if b not in ("spine_01", "spine_02", "spine_03", "pelvis", "clavicle_l", "clavicle_r"):
            return False
        if w[BI["upperarm_l"]] + w[BI["upperarm_r"]] > 0.18 or w[BI["neck_01"]] > 0.08:
            return False
        return p[2] > wz - 0.16
    vest = c.shell("vest", vest_sel, offset=0.02, thick=0.008, folds=0.003, flare=0.005, hide_body=False,
                   cuts=[((0, 0, wz - 0.08), (0, 0, -1), lambda p: True),                                   # straight hem
                         ((0.045 * k, 0, 0), (-1, 0, 0), lambda p: p[1] < -0.02 and p[0] > -0.005),       # open front, left panel
                         ((-0.045 * k, 0, 0), (1, 0, 0), lambda p: p[1] < -0.02 and p[0] < 0.005)],
                   colour=lambda p, n, i, r: jitter(mix(teal, (0.22, 0.42, 0.4), 0.25 if p[2] < wz + 0.1 else 0), r, 0.04))
    # vest pockets with flaps and a button each
    vb = G.bvh_of(vest[0] if isinstance(vest, tuple) else vest)
    bm = bmesh.new(); bmb = bmesh.new()
    for sx in (1, -1):
        for zz in (wz + 0.06 * k, wz + 0.24 * k):
            hit, nn = G.surface_hit(vb, (sx * 0.095 * k, -0.6, zz), (0, 1, 0))
            if hit is None:
                continue
            R = G.orient(nn, (0, 0, 1))
            G.box(bm, hit + nn * 0.004, (0.075 * k, 0.07 * k, 0.008), R)
            G.box(bm, hit + nn * 0.009 + np.array([0, 0, 0.03 * k]), (0.08 * k, 0.025 * k, 0.006), R)  # flap
            G.cylinder(bmb, hit + nn * 0.011 + np.array([0, 0, 0.026 * k]), hit + nn * 0.016 + np.array([0, 0, 0.026 * k]), 0.006, segs=6)
    c.new_bm_object("vest_pockets", bm, "clothing", G.solid(mix(teal, (0, 0, 0), 0.12), amt=0.04))
    c.new_bm_object("vest_buttons", bmb, "clothing", G.solid("#C9A14A", amt=0.05), metal=True)

    def trouser_sel(p, n, w):
        b = c.dom(w)
        if b in ("pelvis", "thigh_l", "thigh_r", "spine_01"):
            return p[2] < wz + 0.02
        if b in ("calf_l", "calf_r"):
            return c.along(b, p) < 0.72
        return False
    c.shell("trousers", trouser_sel, rim_only=True, cuts=[c.limb_cut("calf_l", 0.62), c.limb_cut("calf_r", 0.62)], offset=0.009, thick=0.005, folds=0.004, flare=0.003,
            colour=lambda p, n, i, r: jitter(mix(navy, (0.32, 0.38, 0.5), 0.3 if n[2] > 0.3 else 0), r, 0.04))
    for s in ("l", "r"):
        c.limb_ring(f"trouser_cuff_{s}", f"calf_{s}", 0.4, 0.05 * k, 0.018, G.solid("#2D3D66", amt=0.04))
    # belt and brass buckle
    belt_c = np.array([0, float(P[np.abs(P[:, 2] - wz) < 0.02][:, 1].mean()), wz])
    c.band_obj("belt", belt_c, (0, 0, 1), 0.045 * k, 0.008, G.solid("#4A2E1E", amt=0.06), clearance=0.004,
               target=c.torso_pts(("trousers",)))
    front = P[(np.abs(P[:, 2] - wz) < 0.02) & (np.abs(P[:, 0]) < 0.03)][:, 1].min()
    bm = bmesh.new()
    G.box(bm, (0, front - 0.028, wz), (0.06 * k, 0.012, 0.048 * k))
    c.new_bm_object("buckle", bm, "accessory", G.solid("#C9A14A", amt=0.04), metal=True)

    def boot_sel(p, n, w):
        b = c.dom(w)
        if b.startswith(("foot_", "ball_")):
            return True
        if b in ("calf_l", "calf_r"):
            return c.along(b, p) > 0.32
        return False
    boots = c.shell("boots", boot_sel, cuts=[c.limb_cut("calf_l", 0.44, keep="tail"), c.limb_cut("calf_r", 0.44, keep="tail")], offset=0.021, thick=0.006, smooth=8, flare=0.007, folds=0.002,
                    colour=lambda p, n, i, r: jitter((0.06, 0.06, 0.065) if p[2] > 0.03 else (0.13, 0.11, 0.09), r, 0.08))
    bo = boots
    V = hero.get_co(bo.data); V[:, 2] = np.maximum(V[:, 2], 0.0); hero.set_co(bo.data, V)

    # sou'wester: yellow, sun-faded crown, long back brim
    yel = rgb("#E7B52C")
    c.hat("souwester", lambda p, n, i, r: jitter(mix(yel, (0.95, 0.88, 0.6), 0.35 if n[2] > 0.6 else 0.0), r, 0.04),
          base_lift=0.05, tilt=0.3, crown_h=0.13, bulge=1.05, brim=(0.05, 0.065, 0.1), droop=0.5, thick=0.007)
    # rope coil over the left shoulder: three turns hugging the torso diagonally
    sh = c.info["joints"]["joint-l-shoulder"]; hip = c.info["joints"]["joint-r-upper-leg"]
    diag = sh - hip; diag /= np.linalg.norm(diag)
    axis = np.cross(diag, (0, 1, 0)); axis /= np.linalg.norm(axis)
    ctr = (sh + hip) / 2 + np.array([0, 0.0, 0.02])
    tgt = c.torso_pts(("vest", "belt"))
    tgt = tgt[tgt[:, 2] < c.info["joints"]["joint-neck"][2] - 0.03 * k]          # ride on the shoulder, not the neck
    bm = bmesh.new()
    for turn in range(3):
        rs = None
        segs = 28
        R = G.orient(axis); ex, ey = np.array(R.col[0]), np.array(R.col[1])
        d = tgt - ctr; h = d @ axis
        q = d[np.abs(h) < 0.04] - np.outer(h[np.abs(h) < 0.04], axis)
        ang = np.arctan2(q @ ey, q @ ex); rad = np.linalg.norm(q, axis=1)
        pts = []
        for s in range(segs + 1):
            a0 = -math.pi + 2 * math.pi * s / segs
            dd = np.abs(((ang - a0 + math.pi) % (2 * math.pi)) - math.pi)
            r0 = rad[dd < 0.25].max() if (dd < 0.25).any() else 0.2
            pts.append(ctr + (math.cos(a0) * ex + math.sin(a0) * ey) * (r0 + 0.02 + 0.012 * turn) + axis * (turn - 1) * 0.022)
        G.tube_path(bm, pts, 0.011, sides=5, cap=False)
    c.new_bm_object("rope_coil", bm, "accessory",
                    lambda p, n, i, r: jitter(mix(rgb("rope"), (0.55, 0.45, 0.3), 0.3 if (i // 5) % 3 == 0 else 0), r, 0.05))
    c.finish()
    c.relaxed(lo_r=(-0.15, -0.55, -1))
    # fish held by the tail in the right hand
    h, t, M = c.bone_world("hand_r")
    dn = np.array([0, -0.15, -1.0]); dn /= np.linalg.norm(dn)
    grip = t + dn * 0.02
    bm = bmesh.new()
    Rf = G.orient(dn, (0, -1, 0))
    G.ellipsoid(bm, grip + dn * 0.17, (0.038, 0.016, 0.15), Rf, segs=8, rings=6)          # body
    tail = grip + dn * 0.03
    G.add_geom(bm, [tuple(tail + dn * 0.0), tuple(grip + dn * 0.025 + np.array(Rf @ Vector((0.05, 0, -0.03)))),
                    tuple(grip + dn * 0.025 + np.array(Rf @ Vector((-0.05, 0, -0.03))))], [(0, 1, 2)])
    G.add_geom(bm, [tuple(grip + dn * 0.12 + np.array(Rf @ Vector((0, 0.012, 0)))), tuple(grip + dn * 0.2 + np.array(Rf @ Vector((0, 0.04, 0)))),
                    tuple(grip + dn * 0.24 + np.array(Rf @ Vector((0, 0.012, 0))))], [(0, 1, 2)])      # dorsal fin
    c.held("fish", bm, "hand_r", lambda p, n, i, r: jitter((0.3, 0.42, 0.36) if n[0] * dn[0] + n[2] < 0.2 and r.random() < 0.7 else (0.78, 0.78, 0.72), r, 0.06))
    return c


# ====================================================================== B
def build_B():
    c = Char("B"); c.build_body(); rng = c.rng; k = c.hk
    c.paint_skin(stubble=0.0, lips="#5A2A26")
    eyes = G.eyes(c.info, c.coll, iris=c.spec["iris"], rng=rng)
    c.add("eye_l", eyes[0], "face"); c.add("eye_r", eyes[1], "face")
    c.eyebrows("#120B08", length=0.011, thick=0.0034)
    W, P = c.W, c.P; wz = c.waist_z
    coral, gold, cream = rgb("#D8725F"), rgb("#D7A546"), rgb("#EBDCB4")

    def top_sel(p, n, w):
        b = c.dom(w)
        if b in ("spine_01", "spine_02", "spine_03", "clavicle_l", "clavicle_r", "pelvis"):
            if p[2] < wz - 0.04 or w[BI["neck_01"]] > 0.15:
                return False
            if n[1] < -0.3 and abs(p[0]) < 0.075 * k and p[2] > c.info["joints"]["joint-l-clavicle"][2] - 0.07 * k:
                return False                                           # scoop neckline
            return True
        if b in ("upperarm_l", "upperarm_r"):
            return c.along(b, p) < 0.5
        return False
    c.shell("top", top_sel, cuts=[c.limb_cut("upperarm_l", 0.36), c.limb_cut("upperarm_r", 0.36),
                                  ((0, 0, wz - 0.03), (0, 0, -1), lambda p: True)], rim_only=True, offset=0.005, thick=0.004, folds=0.0015, flare=0.002,
            colour=lambda p, n, i, r: jitter(coral, r, 0.035))
    for s in ("l", "r"):
        c.limb_ring(f"sleeve_hem_{s}", f"upperarm_{s}", 0.34, 0.02 * k, 0.006, G.solid(mix(coral, (0.4, 0.15, 0.1), 0.2)))
    # flared skirt: waist to mid-calf, flute folds, gold hem band
    hem_z = float(c.info["bones"]["calf_l"][0][2]) - 0.1 * k
    rings, segs = 8, 32
    centre = P[(np.abs(P[:, 2] - wz) < 0.03) & (W[:, [BI["spine_01"], BI["pelvis"], BI["spine_02"]]].sum(axis=1) > 0.5)].mean(axis=0)
    prof = []
    bm = bmesh.new()
    verts, faces = [], []
    legs = W[:, [BI[b] for b in ("pelvis", "spine_01", "thigh_l", "thigh_r", "calf_l", "calf_r")]].sum(axis=1) > 0.6
    lower = P[legs & (P[:, 2] < wz + 0.02) & (P[:, 2] > hem_z)]
    for j in range(rings + 1):
        u = j / rings
        z = wz - (wz - hem_z) * u
        sl = lower[np.abs(lower[:, 2] - z) < 0.04]
        for s in range(segs):
            a = 2 * math.pi * s / segs
            dv = np.array([math.cos(a), math.sin(a), 0])
            q = sl - centre; q[:, 2] = 0
            proj = q @ dv
            m = (q @ np.array([-dv[1], dv[0], 0])) ** 2 < 0.03 ** 2
            r0 = proj[m].max() if m.any() else 0.15
            if j == 0:
                prof.append(r0)
            rr = max(r0 + 0.012, prof[s] + 0.012) + 0.2 * u ** 1.4 + 0.022 * u * math.sin(a * 9 + 0.6)
            verts.append(tuple(np.array([centre[0], centre[1], z]) + dv * rr * np.array([1, 0.9, 1])))
    for j in range(rings):
        for s in range(segs):
            s2 = (s + 1) % segs
            faces.append((j * segs + s, (j + 1) * segs + s, (j + 1) * segs + s2, j * segs + s2))
    G.add_geom(bm, verts, faces)
    sk = G.bm_to_object(bm, "skirt", c.coll); c.solidify(sk, 0.006)
    G.colour_faces(sk, lambda p, n, i, r: jitter(mix(coral, gold, 1.0) if p[2] < hem_z + 0.05 * k else coral, r, 0.035), rng)
    hero.assign(sk)
    Ps = hero.get_co(sk.data)
    Ws = np.zeros((len(Ps), len(BONES)))
    t = np.clip((wz - Ps[:, 2]) / (wz - hem_z), 0, 1)
    Ws[:, BI["pelvis"]] = 1 - 0.6 * t
    Ws[:, BI["thigh_l"]] = 0.6 * t * np.clip(0.5 + Ps[:, 0] * 8, 0, 1)
    Ws[:, BI["thigh_r"]] = 0.6 * t * np.clip(0.5 - Ps[:, 0] * 8, 0, 1)
    hero.set_groups(sk, Ws)
    c.add("skirt", sk, "clothing")
    # gold hem band (separate piece, thicker)
    bm = bmesh.new()
    ring = np.array(verts[rings * segs:])
    rr = []
    for s in range(segs + 1):
        rr.append(ring[s % segs] + np.array([0, 0, 0.012]))
    for z_off in (0.0,):
        G.tube_path(bm, rr, 0.012, sides=4, cap=False)
    c.new_bm_object("skirt_hem", bm, "clothing", G.solid("#C99A3A", amt=0.05))
    # waistband
    c.band_obj("waistband", (0, centre[1], wz), (0, 0, 1), 0.035 * k, 0.006, G.solid(mix(coral, gold, 0.5)), clearance=0.012)
    # apron: cream front panel over the skirt + ties and a bow at the back
    bm = bmesh.new()
    av, af = [], []
    cols = 9
    arow = 7
    for j in range(arow + 1):
        u = j / arow
        idx = j * segs if j <= rings else rings * segs
        for q in range(cols):
            a = -math.pi / 2 + (q / (cols - 1) - 0.5) * 1.55       # front = -Y
            s = int(round((a % (2 * math.pi)) / (2 * math.pi) * segs)) % segs
            jj = min(rings, int(round(u * rings * 0.75)))
            p = np.array(verts[jj * segs + s])
            dv = np.array([math.cos(a), math.sin(a), 0])
            av.append(tuple(p + dv * 0.016 + np.array([0, 0, 0.004 * math.sin(q * 2.1)])))
    for j in range(arow):
        for q in range(cols - 1):
            af.append((j * cols + q, (j + 1) * cols + q, (j + 1) * cols + q + 1, j * cols + q + 1))
    G.add_geom(bm, av, af)
    ap = G.bm_to_object(bm, "apron", c.coll); c.solidify(ap, 0.005)
    G.colour_faces(ap, lambda p, n, i, r: jitter(mix(cream, (0.75, 0.7, 0.58), 0.35 if r.random() < 0.15 else 0), r, 0.03), rng)
    hero.assign(ap)
    G.copy_weights_from(ap, Ps, Ws)
    c.add("apron", ap, "clothing")
    c.band_obj("apron_ties", (0, centre[1], wz + 0.005), (0, 0, 1), 0.02 * k, 0.004, G.solid(cream), clearance=0.02)
    back = P[(np.abs(P[:, 2] - wz) < 0.03)][:, 1].max() + 0.03
    bm = bmesh.new()
    for sx in (1, -1):
        G.torus(bm, (sx * 0.035, back, wz + 0.005), (0, 1, 0.2), 0.026, 0.007, segs=8, sides=4)
        G.tube_path(bm, [(sx * 0.008, back, wz), (sx * 0.03, back + 0.006, wz - 0.07), (sx * 0.035, back + 0.004, wz - 0.13)], 0.007, sides=4)
    G.ellipsoid(bm, (0, back + 0.004, wz + 0.005), (0.012, 0.01, 0.014), segs=6, rings=3)
    c.new_bm_object("apron_bow", bm, "clothing", G.solid(cream))

    # headwrap: wrapped turns around the head + a knot on top, madras checks
    def madras(p, n, i, r):
        a = int(math.floor((p[0] + 1) * 60)) % 6; b = int(math.floor((p[2] + p[1] * 0.4) * 60)) % 6
        if a == 0 or b == 0:
            return jitter(gold, r, 0.04)
        if a == 3 or b == 3:
            return jitter((0.15, 0.35, 0.2), r, 0.05)
        return jitter((0.7, 0.13, 0.12) if (a + b) % 2 else (0.82, 0.22, 0.16), r, 0.03)
    c.hat("headwrap", madras, base_lift=0.025, tilt=-0.15, crown_h=0.15, bulge=1.12, brim=(0, 0, 0), droop=0, thick=0.008,
          clearance=0.02, rings=6)
    hc = c.info["head_c"]; hr = c.info["head_r"]
    e = c.info["eyes"]["l"][0]
    for j in range(3):
        z = e[2] + (0.045 + 0.03 * j) * k
        axis = (0, -0.25 + 0.2 * j, 1)
        c.band_obj(f"wrap_turn_{j}", (0, hc[1] + 0.005, z), axis, 0.028 * k, 0.012, madras,
                   target=hero.get_co(c.parts["headwrap"][0].data), clearance=0.002, weights={"head": 1.0}, cat="hat")
    topz = hero.get_co(c.parts["headwrap"][0].data)[:, 2].max()
    bm = bmesh.new()
    for sx in (1, -1):
        G.ellipsoid(bm, (sx * 0.03, hc[1] + 0.01, topz + 0.01), (0.045, 0.028, 0.03), G.orient((sx * 0.6, 0, 1)), segs=7, rings=4)
    G.ellipsoid(bm, (0, hc[1] + 0.01, topz + 0.015), (0.022, 0.024, 0.022), segs=6, rings=4)
    c.new_bm_object("headwrap_knot", bm, "hat", madras, weights={"head": 1.0})
    # gold hoop earrings at the ear lobes
    bm = bmesh.new()
    for side, sx in (("l", 1), ("r", -1)):
        t = mh.target(f"ears/{side}-ear-lobe-incr")
        lobe = c.info["V_full"][t[0]]
        lobe = lobe[np.argsort(lobe[:, 2])[:6]].mean(axis=0)
        G.torus(bm, lobe + np.array([sx * 0.006, 0, -0.022]), (1, 0, 0), 0.02, 0.0028, segs=14, sides=4)
    c.new_bm_object("earrings", bm, "accessory", G.solid("#E0B23E", amt=0.03), weights={"head": 1.0}, metal=True)
    # sandals: soles + straps over toes and ankle
    sandals(c, "#7A4A2A")
    c.finish()
    c.relaxed(up_l=(0.45, 0.05, -1), lo_l=(0.55, -0.55, -0.35))
    # basket of fruit on her left hip (rides on the pelvis; left hand rests on the rim)
    hipj = c.info["joints"]["joint-l-upper-leg"]
    bc = np.array([hipj[0] + 0.2, hipj[1] - 0.03, c.hip_z + 0.02])
    bm = bmesh.new()
    segs = 12
    for j in range(5):
        z0 = bc[2] - 0.09 + 0.04 * j
        G.torus(bm, (bc[0], bc[1], z0), (0, 0, 1), 0.13 + 0.012 * j, 0.012, segs=segs, sides=4)
    G.cylinder(bm, (bc[0], bc[1], bc[2] - 0.105), (bc[0], bc[1], bc[2] - 0.09), 0.12, segs=segs)
    G.torus(bm, (bc[0], bc[1], bc[2] + 0.085), (0, 0, 1), 0.185, 0.014, segs=segs, sides=4)
    basket = G.bm_to_object(bm, "basket", c.coll)
    G.colour_faces(basket, lambda p, n, i, r: jitter((0.74, 0.56, 0.32) if (i // 4) % 2 else (0.6, 0.43, 0.24), r, 0.05), rng)
    hero.assign(basket); hero.attach_to_bone(basket, c.rig, "pelvis"); c.add("basket", basket, "held")
    bm = bmesh.new()
    fr = []
    for q in range(5):
        a = q * 1.3
        p = bc + np.array([math.cos(a) * 0.08, math.sin(a) * 0.07, 0.075])
        G.ellipsoid(bm, p, (0.05, 0.038, 0.035), G.orient((math.cos(a), math.sin(a), 0.4)), segs=7, rings=4)        # mangoes
    for q in range(3):
        pts = [bc + np.array([-0.07 + 0.02 * q, -0.05 + 0.03 * u - 0.02 * q, 0.1 + 0.07 * math.sin(math.pi * u * 0.8) + 0.04 * u]) for u in np.linspace(0, 1, 6)]
        G.tube_path(bm, pts, 0.016, sides=5, radii=[0.006, 0.014, 0.017, 0.017, 0.014, 0.005])                       # bananas
    for q in range(3):
        a = 2.4 + q * 0.6
        G.ellipsoid(bm, bc + np.array([math.cos(a) * 0.11, math.sin(a) * 0.09, 0.105]), (0.026, 0.024, 0.024), segs=6, rings=4)  # limes

    def fruitcol(p, n, i, r):
        f = i
        if f < 5 * 42:
            return jitter(mix((0.95, 0.62, 0.12), (0.85, 0.3, 0.12), r.random() * 0.5), r, 0.04)
        if f < 5 * 42 + 3 * 32:
            return jitter((0.97, 0.84, 0.28), r, 0.04)
        return jitter((0.45, 0.72, 0.22), r, 0.04)
    c.held("fruit", bm, "pelvis", fruitcol, gloss=True)
    return c


def sandals(c, leather):
    P = c.P; k = c.hk
    bm = bmesh.new()
    for s in ("l", "r"):
        foot = P[[c.dom(w).startswith((f"foot_{s}", f"ball_{s}")) for w in c.W]]
        foot = foot[foot[:, 2] < 0.05]
        ctr = foot.mean(axis=0)
        lo, hi = foot.min(axis=0), foot.max(axis=0)
        G.box(bm, ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, 0.006), (hi[0] - lo[0] + 0.02, hi[1] - lo[1] + 0.025, 0.012))
    c.new_bm_object("sandal_soles", bm, "footwear", G.solid(mix(rgb(leather), (0, 0, 0), 0.2), amt=0.06))
    for s in ("l", "r"):
        c.limb_ring(f"sandal_strap_toe_{s}", f"foot_{s}", 0.78, 0.018 * k, 0.005, G.solid(leather, amt=0.05), clearance=0.002)
        c.limb_ring(f"sandal_strap_ankle_{s}", f"foot_{s}", 0.12, 0.016 * k, 0.005, G.solid(leather, amt=0.05), clearance=0.002)


# ====================================================================== C
def build_C():
    c = Char("C"); c.build_body(); rng = c.rng; k = c.hk
    c.paint_skin(stubble=0.0, lips="#4A2A22")
    eyes = G.eyes(c.info, c.coll, iris=c.spec["iris"], rng=rng)
    c.add("eye_l", eyes[0], "face"); c.add("eye_r", eyes[1], "face")
    c.eyebrows("#E8E4DA", length=0.016, n=7, thick=0.0048)
    white = lambda p, n, i, r: jitter(mix((0.94, 0.93, 0.89), (0.8, 0.78, 0.72), r.random() * 0.4), r, 0.02)
    Cc = hero.face_centres(c.body); Nn = hero.face_normals(c.body)
    # full white beard (dense droopy clumps) and moustache
    bm = bmesh.new(); pts, nrm = [], []
    for p, n in zip(Cc, Nn):
        if c.beard_zone(p, n, moustache=False) and rng.random() < 0.36:
            pts.append(p); nrm.append(n)
    G.clumps(bm, pts, nrm, 0.034 * k, 0.019 * k, rng, droop=(0, -0.2, -1), droop_amt=0.7, sides=3, taper=0.45, curl=0.002)
    c.new_bm_object("beard", bm, "hair", white, weights={"head": 1.0})
    bm = bmesh.new(); pts, nrm = [], []
    for p, n in zip(Cc, Nn):
        r = p - c.mouth
        if 0.006 * k < r[2] < 0.024 * k and abs(r[0]) < 0.034 * k and n[1] < 0 and not c.lip(p, n):
            pts.append(p); nrm.append(n)
    G.clumps(bm, pts, nrm, 0.022 * k, 0.007 * k, rng, droop=(0, -0.3, -1), droop_amt=0.75, sides=4, taper=0.25)
    c.new_bm_object("moustache", bm, "hair", white, weights={"head": 1.0})
    # white hair around the back and sides under the cap
    pts, nrm = c.scalp(lambda d, p: -0.35 < d[2] < 0.3 and d[1] > -0.15 and abs(d[0]) < 0.97, 0.16)
    bm = bmesh.new(); G.clumps(bm, pts, nrm, 0.018 * k, 0.007 * k, rng, droop=(0, 0.3, -1), droop_amt=0.7, taper=0.3)
    c.new_bm_object("hair", bm, "hair", white, weights={"head": 1.0})
    W, P = c.W, c.P; wz = c.waist_z
    cream, cardi, khaki = rgb("#E9DFC6"), rgb("#6F8193"), rgb("#B59E73")

    def shirt_sel(p, n, w):
        b = c.dom(w)
        if b in ("spine_01", "spine_02", "spine_03", "clavicle_l", "clavicle_r", "upperarm_l", "upperarm_r", "pelvis", "lowerarm_l", "lowerarm_r"):
            return p[2] > wz - 0.05 and w[BI["neck_01"]] < 0.45 and (b[:8] != "lowerarm" or c.along(b, p) < 0.93)
        return False
    c.shell("shirt", shirt_sel, rim_only=True, offset=0.006, thick=0.003, colour=lambda p, n, i, r: jitter(cream, r, 0.02))
    nb = c.info["bones"]["neck_01"]
    c.band_obj("shirt_collar", nb[0] + (nb[1] - nb[0]) * 0.25, nb[1] - nb[0], 0.032 * k, 0.005, G.solid(cream, amt=0.02), clearance=0.01)
    # collar points
    bm = bmesh.new()
    nf = P[(np.abs(P[:, 0]) < 0.02) & (np.abs(P[:, 2] - (nb[0][2] + 0.01)) < 0.02)]
    fy = nf[:, 1].min() if len(nf) else -0.08
    for sx in (1, -1):
        G.add_geom(bm, [(sx * 0.012, fy - 0.012, nb[0][2] + 0.03 * k), (sx * 0.06 * k, fy + 0.012, nb[0][2] + 0.03 * k),
                        (sx * 0.03 * k, fy - 0.016, nb[0][2] - 0.035 * k)], [(0, 1, 2)])
    cp = G.bm_to_object(bm, "collar_points", c.coll); c.solidify(cp, 0.004)
    G.colour_faces(cp, G.solid(cream, amt=0.02), rng); hero.assign(cp); G.copy_weights_from(cp, P, W); c.add("collar_points", cp, "clothing")

    def cardi_sel(p, n, w):
        b = c.dom(w)
        if b in ("spine_01", "spine_02", "spine_03", "clavicle_l", "clavicle_r", "upperarm_l", "upperarm_r", "pelvis", "lowerarm_l", "lowerarm_r"):
            if w[BI["neck_01"]] > 0.12 or p[2] < c.hip_z - 0.07:
                return False
            if b.startswith("lowerarm") and c.along(b, p) > 0.95:
                return False
            vz = c.info["joints"]["joint-l-clavicle"][2] - 0.17 * k        # V-neck depth
            if n[1] < -0.2 and abs(p[0]) < 0.02 * k + max(0, p[2] - vz) * 0.55:
                return False
            return True
        return False
    cd = c.shell("cardigan", cardi_sel, cuts=[c.limb_cut("lowerarm_l", 0.84), c.limb_cut("lowerarm_r", 0.84),
                                              ((0, 0, c.hip_z), (0, 0, -1), lambda p: True)], offset=0.017, thick=0.008, folds=0.004, flare=0.006, hide_body=False,
                 colour=lambda p, n, i, r: jitter(mix(cardi, (0.5, 0.58, 0.66), 0.25 if (int(p[2] * 140) % 2) else 0), r, 0.03))
    for s in ("l", "r"):
        c.limb_ring(f"cardigan_cuff_{s}", f"lowerarm_{s}", 0.82, 0.04 * k, 0.008, G.solid(mix(cardi, (0, 0, 0), 0.1)),
                    target=hero.get_co(cd.data))
    cb = G.bvh_of(cd)
    bm = bmesh.new(); bmp = bmesh.new()
    vz = c.info["joints"]["joint-l-clavicle"][2] - 0.17 * k
    for j in range(5):
        z = vz - 0.012 - j * (vz - c.hip_z) / 5.2
        hit, nn = G.surface_hit(cb, (0.032 * k, -0.6, z), (0, 1, 0))
        if hit is not None:
            G.cylinder(bm, hit, hit + nn * 0.006, 0.0085, segs=7)
    for sx in (1, -1):
        hit, nn = G.surface_hit(cb, (sx * 0.1 * k, -0.6, c.hip_z + 0.07 * k), (0, 1, 0))
        if hit is not None:
            G.box(bmp, hit + nn * 0.004, (0.08 * k, 0.075 * k, 0.007), G.orient(nn, (0, 0, 1)))
    c.new_bm_object("cardigan_buttons", bm, "clothing", G.solid("#4A3A2C", amt=0.06), gloss=True)
    c.new_bm_object("cardigan_pockets", bmp, "clothing", G.solid(mix(cardi, (0, 0, 0), 0.08)))

    def trouser_sel(p, n, w):
        b = c.dom(w)
        if b in ("pelvis", "thigh_l", "thigh_r", "spine_01"):
            return p[2] < wz + 0.02
        if b in ("calf_l", "calf_r"):
            return c.along(b, p) < 0.93
        return False
    c.shell("trousers", trouser_sel, rim_only=True, offset=0.011, thick=0.005, folds=0.005, flare=0.004,
            colour=lambda p, n, i, r: jitter(mix(khaki, (0.6, 0.55, 0.42), 0.4 if p[2] < 0.25 else 0), r, 0.035))
    sandals(c, "#5A3A24")
    # flat cap
    grey = rgb("#7E7E80")
    c.hat("flatcap", lambda p, n, i, r: jitter(mix(grey, (0.38, 0.38, 0.4), 0.3 if (i % 7 == 0) else 0), r, 0.04),
          base_lift=0.06, tilt=0.15, crown_h=0.085, bulge=1.12, brim=(0.075, 0.0, 0.0), droop=0.25, forward=0.035, flat=0.85,
          thick=0.008, rings=4)
    c.finish()
    # stoop and the relaxed arm pose; cane in the right hand, net over the left forearm
    c.rest()
    c.rotate("spine_02", (1, 0, 0), -7); c.rotate("spine_03", (1, 0, 0), -9); c.rotate("neck_01", (1, 0, 0), 10)
    c.rotate("head", (1, 0, 0), 6)
    c.aim("upperarm_l", (0.25, 0.1, -1)); c.aim("lowerarm_l", (0.15, -1, -0.12))
    c.aim("upperarm_r", (-0.35, -0.05, -1)); c.aim("lowerarm_r", (-0.2, -0.65, -0.75))
    h, t, M = c.bone_world("hand_r")
    grip = t
    bm = bmesh.new()
    base = np.array([grip[0] - 0.03, grip[1] - 0.12, 0.0])
    G.tube_path(bm, [base, grip * 0.5 + base * 0.5, grip + np.array([0, 0, 0.03])], 0.013, sides=6)
    crook = [grip + np.array([0, 0, 0.03]) + np.array([0.0, -math.sin(a) * 0.05, (1 - math.cos(a)) * 0.0 + math.sin(a * 0.5) * 0.05]) for a in np.linspace(0, math.pi, 6)]
    G.tube_path(bm, crook, 0.013, sides=6)
    c.held("cane", bm, "hand_r", lambda p, n, i, r: jitter((0.42, 0.27, 0.15) if p[2] > 0.03 else (0.2, 0.15, 0.1), r, 0.07))
    # net draped over the left forearm: threads, knots, a red float
    h, t, M = c.bone_world("lowerarm_l")
    axis = t - h
    bm = bmesh.new(); bmk = bmesh.new(); bmf = bmesh.new()
    nu, nv = 7, 9
    grid = np.zeros((nu, nv, 3))
    for i in range(nu):
        base_p = h + axis * (0.2 + 0.6 * i / (nu - 1))
        for j in range(nv):
            v = j / (nv - 1)
            side = -1 if v < 0.5 else 1
            dd = abs(v - 0.5) * 2
            over = base_p + np.array([0, side * 0.045 * (1 - math.cos(min(1, dd * 4) * math.pi / 2)), 0.035 * (1 - dd * 3) if dd < 0.33 else 0])
            drop = max(0, dd - 0.15) * 0.42
            grid[i, j] = over + np.array([0.01 * math.sin(i * 1.7 + j), side * (0.05 + 0.02 * math.sin(i)), -drop - 0.03 * dd])
    for i in range(nu):
        G.tube_path(bm, list(grid[i]), 0.0022, sides=3, cap=False)
    for j in range(nv):
        G.tube_path(bm, list(grid[:, j]), 0.0022, sides=3, cap=False)
    for i in range(nu):
        for j in range(nv):
            if (i + j) % 2 == 0:
                G.ellipsoid(bmk, grid[i, j], (0.005, 0.005, 0.005), segs=4, rings=2)
    G.ellipsoid(bmf, grid[nu - 1, nv - 1] + np.array([0, 0, -0.03]), (0.03, 0.03, 0.038), segs=8, rings=5)
    c.held("net", bm, "lowerarm_l", G.solid("#B9A77E", amt=0.06))
    c.held("net_knots", bmk, "lowerarm_l", G.solid("#9C8A62", amt=0.06))
    c.held("net_float", bmf, "lowerarm_l", lambda p, n, i, r: jitter((0.8, 0.2, 0.15) if n[2] < 0.5 else (0.93, 0.9, 0.85), r, 0.04), gloss=True)
    return c


# ====================================================================== D
def build_D():
    c = Char("D"); c.build_body(); rng = c.rng; k = c.hk
    c.paint_skin(stubble=0.0, lips="#4E2A22")
    eyes = G.eyes(c.info, c.coll, iris=c.spec["iris"], rng=rng)
    c.add("eye_l", eyes[0], "face"); c.add("eye_r", eyes[1], "face")
    c.eyebrows("#150E0A", length=0.01, thick=0.0034)
    pts, nrm = c.scalp(lambda d, p: (d[2] > 0.3 or (d[1] > 0.0 and d[2] > -0.3)) and not (d[1] < -0.25 and d[2] < 0.62) and abs(d[0]) < 0.9, 1.0)
    keep = rng.random(len(pts)) < 0.36
    bm = bmesh.new(); G.curls(bm, pts[keep], nrm[keep], 0.0185 * k, rng)
    c.new_bm_object("hair", bm, "hair", lambda p, n, i, r: jitter((0.08, 0.055, 0.04), r, 0.12), weights={"head": 1.0})
    W, P = c.W, c.P; wz = c.waist_z
    blue, white, yellow = rgb("#3F7DC0"), rgb("#F3EFE4"), rgb("#E9B92F")

    def shirt_sel(p, n, w):
        b = c.dom(w)
        if b in ("spine_01", "spine_02", "spine_03", "clavicle_l", "clavicle_r", "pelvis"):
            return p[2] > wz - 0.06 and w[BI["neck_01"]] < 0.25
        if b in ("upperarm_l", "upperarm_r"):
            return c.along(b, p) < 0.62
        return False
    c.shell("shirt", shirt_sel, cuts=[c.limb_cut("upperarm_l", 0.48), c.limb_cut("upperarm_r", 0.48)], rim_only=True, offset=0.006, thick=0.004, folds=0.002, flare=0.003,
            colour=lambda p, n, i, r: jitter(blue if int(math.floor(p[2] * 32)) % 2 else white, r, 0.03))
    nb = c.info["bones"]["neck_01"]
    c.band_obj("shirt_collar", nb[0] + (nb[1] - nb[0]) * 0.1, nb[1] - nb[0], 0.02 * k, 0.005, G.solid(white), clearance=0.006)
    for s in ("l", "r"):
        c.limb_ring(f"sleeve_hem_{s}", f"upperarm_{s}", 0.49, 0.025 * k, 0.006, G.solid(blue))

    def shorts_sel(p, n, w):
        b = c.dom(w)
        if b in ("pelvis", "spine_01"):
            return p[2] < wz + 0.01
        if b in ("thigh_l", "thigh_r"):
            return c.along(b, p) < 0.68
        return False
    c.shell("shorts", shorts_sel, cuts=[c.limb_cut("thigh_l", 0.55), c.limb_cut("thigh_r", 0.55)], offset=0.012, thick=0.005, folds=0.004, flare=0.008,
            colour=lambda p, n, i, r: jitter(mix(yellow, (0.75, 0.6, 0.2), 0.3 if r.random() < 0.12 else 0), r, 0.035))
    c.band_obj("shorts_waist", (0, float(P[np.abs(P[:, 2] - wz) < 0.02][:, 1].mean()), wz), (0, 0, 1), 0.03 * k, 0.006,
               G.solid(mix(yellow, (0.6, 0.45, 0.1), 0.2)), clearance=0.014)
    c.finish()
    c.relaxed(up_r=(-0.25, 0.0, -1), lo_r=(-0.12, -0.15, -1))
    # small orange bucket with a wire handle, right hand
    h, t, M = c.bone_world("hand_r")
    top = t + np.array([0, -0.005, -0.06])
    bm = bmesh.new()
    segs = 10
    vb, fb = [], []
    for j, (z, r) in enumerate(((top[2] - 0.15, 0.06), (top[2] - 0.15, 0.06), (top[2] - 0.01, 0.075), (top[2] - 0.01, 0.068), (top[2] - 0.14, 0.054))):
        for s in range(segs):
            a = 2 * math.pi * s / segs
            rr = 0.0 if j == 0 else r
            vb.append((top[0] + math.cos(a) * rr, top[1] + math.sin(a) * rr, z))
    for j in range(4):
        for s in range(segs):
            s2 = (s + 1) % segs
            fb.append((j * segs + s, j * segs + s2, (j + 1) * segs + s2, (j + 1) * segs + s))
    G.add_geom(bm, vb, fb)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    G.torus(bm, (top[0], top[1], top[2] - 0.012), (0, 0, 1), 0.074, 0.006, segs=segs, sides=4)
    c.held("bucket", bm, "hand_r", lambda p, n, i, r: jitter((0.95, 0.47, 0.12) if n[2] < 0.9 else (0.75, 0.34, 0.08), r, 0.04), gloss=True)
    bm = bmesh.new()
    arc = [np.array([top[0] + math.cos(a) * 0.072, top[1], top[2] - 0.02 + math.sin(a) * 0.06]) for a in np.linspace(0, math.pi, 9)]
    G.tube_path(bm, arc, 0.0025, sides=4)
    c.held("bucket_handle", bm, "hand_r", G.solid("#8A8D92", amt=0.05), metal=True)
    return c


BUILDERS = {"A": build_A, "B": build_B, "C": build_C, "D": build_D}


def build(key):
    return BUILDERS[key]()
