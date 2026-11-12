"""Procedural keyframed animation for the hero villagers.

Every clip is authored as a pose function pose(c, p) of the cycle phase p in
[0, 1), applied to the shared game_engine rig in world-space terms (swing a limb
forward, bend a knee, lean the spine), then baked to quaternion keys on every
bone at 24 fps and stored as one NLA track per clip, so the glTF export carries
one named animation per clip.

Clip names follow the game's animation contract (godot VillagerAnimator.CLIPS)
plus run and one job clip per character.

World convention: the character faces -Y, left is +X, up is +Z.
"""
from __future__ import annotations
import math
import numpy as np
import bpy
from mathutils import Vector, Matrix, Quaternion

FPS = 24
TAU = 2 * math.pi

CONTRACT = ["idle", "walk", "climb_stairs", "climb_ladder", "open_door", "cook", "eat", "sit", "sleep", "fish", "work", "wave"]
EXTRA = ["run", "give", "carry", "row", "steer", "swim", "cast", "haul_net", "sweep", "talk", "play"]
JOB = {"A": "haul_rope", "B": "hand_fruit", "C": "mend_net", "D": "run_play"}
LOOPING = {"idle", "walk", "climb_stairs", "climb_ladder", "cook", "eat", "sit", "sleep", "fish", "work", "wave", "run",
           "haul_rope", "hand_fruit", "mend_net", "run_play", "give", "carry", "row", "steer", "swim", "cast", "haul_net",
           "sweep", "talk", "play"}


# ------------------------------------------------------------------ pose primitives
class Poser:
    """Fast pose writer: world-space rotations about a bone's head."""

    def __init__(self, c):
        self.c = c
        self.rig = c.rig
        self.pb = self.rig.pose.bones
        for pb in self.pb:
            pb.rotation_mode = "QUATERNION"
        # leg / arm lengths for proportional motion (child vs adult)
        B = c.B
        self.thigh = float(np.linalg.norm(B["thigh_l"][1] - B["thigh_l"][0]))
        self.calf = float(np.linalg.norm(B["calf_l"][1] - B["calf_l"][0]))
        self.scale = self.thigh / 0.45
        self.hip_z = float(c.hip_z)

    def up(self):
        bpy.context.view_layer.update()

    def reset(self):
        for pb in self.pb:
            pb.matrix_basis = Matrix.Identity(4)
        self.up()

    def rot(self, bone, axis, deg):
        if abs(deg) < 1e-4:
            return
        pb = self.pb[bone]
        M = pb.matrix.copy()
        head = M.to_translation()
        pb.matrix = Matrix.Translation(head) @ Matrix.Rotation(math.radians(deg), 4, Vector(axis)) @ Matrix.Translation(-head) @ M
        self.up()

    def aim(self, bone, direction):
        pb = self.pb[bone]
        M = pb.matrix.copy()
        cur = (pb.tail - pb.head).normalized()
        q = cur.rotation_difference(Vector(direction).normalized())
        head = M.to_translation()
        pb.matrix = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head) @ M
        self.up()

    def move(self, bone, dx=0.0, dy=0.0, dz=0.0):
        pb = self.pb[bone]
        M = pb.matrix.copy()
        M.translation = M.translation + Vector((dx, dy, dz))
        pb.matrix = M
        self.up()

    # semantic helpers -----------------------------------------------
    def leg(self, s, hip, knee, ankle=0.0, splay=0.0):
        """hip > 0 swings the thigh forward; knee > 0 flexes; ankle > 0 lifts the toes."""
        self.rot(f"thigh_{s}", (1, 0, 0), -hip)
        if splay:
            self.rot(f"thigh_{s}", (0, 1, 0), splay if s == "l" else -splay)
        self.rot(f"calf_{s}", (1, 0, 0), knee)
        self.rot(f"foot_{s}", (1, 0, 0), -ankle)

    def arm(self, s, swing, elbow=10.0, out=0.0, twist=0.0):
        """swing > 0 brings the arm forward; elbow > 0 bends the forearm forward."""
        if out:
            self.rot(f"upperarm_{s}", (0, 1, 0), out if s == "l" else -out)
        self.rot(f"upperarm_{s}", (1, 0, 0), -swing)
        self.rot(f"lowerarm_{s}", (1, 0, 0), -elbow)
        if twist:
            self.rot(f"lowerarm_{s}", (0, 0, 1), twist if s == "l" else -twist)

    def spine(self, lean=0.0, yaw=0.0, roll=0.0, parts=("spine_01", "spine_02", "spine_03")):
        for b in parts:
            self.rot(b, (1, 0, 0), lean / len(parts))
            self.rot(b, (0, 0, 1), yaw / len(parts))
            self.rot(b, (0, 1, 0), roll / len(parts))

    def head(self, nod=0.0, yaw=0.0, tilt=0.0):
        self.rot("neck_01", (1, 0, 0), nod * 0.4); self.rot("head", (1, 0, 0), nod * 0.6)
        self.rot("head", (0, 0, 1), yaw); self.rot("head", (0, 1, 0), tilt)

    def pelvis(self, dz=0.0, yaw=0.0, roll=0.0, pitch=0.0, dy=0.0):
        if dz or dy:
            self.move("pelvis", 0.0, dy, dz)
        self.rot("pelvis", (0, 0, 1), yaw)
        self.rot("pelvis", (0, 1, 0), roll)
        self.rot("pelvis", (1, 0, 0), pitch)

    def arms_down(self, out=0.2, fwd=0.04):
        self.aim("upperarm_l", (out, fwd, -1)); self.aim("lowerarm_l", (out * 0.5, -0.2, -1))
        self.aim("upperarm_r", (-out, fwd, -1)); self.aim("lowerarm_r", (-out * 0.5, -0.2, -1))

    def fingers(self, s, curl):
        for f in ("index", "middle", "ring", "pinky"):
            for j in (1, 2, 3):
                n = f"{f}_{j:02d}_{s}"
                if n in self.pb:
                    pb = self.pb[n]
                    pb.matrix_basis = Matrix.Rotation(curl * (0.6 if j == 1 else 1.0) * (-1 if s == "l" else 1), 4, "Z")
        for j in (1, 2, 3):
            n = f"thumb_{j:02d}_{s}"
            if n in self.pb:
                self.pb[n].matrix_basis = Matrix.Rotation(curl * 0.35 * (-1 if s == "l" else 1), 4, "X")
        self.up()


# ------------------------------------------------------------------ character base postures
def base(P, key):
    """Posture held under every clip: arms relaxed, plus what each villager holds."""
    P.arms_down()
    P.fingers("l", 0.35); P.fingers("r", 0.35)
    if key == "C":                       # elder: stoop, cane hand closed
        P.spine(lean=14)
        P.head(nod=-8)
        P.fingers("r", 0.9)
    if key == "A":                       # fish held by the tail
        P.fingers("r", 0.9)
    if key == "D":                       # bucket handle
        P.fingers("r", 0.9)


def hold_basket(P):
    """B's left arm curls over the basket on her hip."""
    P.aim("upperarm_l", (0.45, 0.05, -1)); P.aim("lowerarm_l", (0.55, -0.55, -0.35))
    P.fingers("l", 0.5)


def hold_net(P):
    """C's left forearm carries the draped net."""
    P.aim("upperarm_l", (0.25, 0.1, -1)); P.aim("lowerarm_l", (0.15, -1, -0.12))


def hold_cane(P, plant=0.0):
    P.aim("upperarm_r", (-0.35, -0.05 - 0.15 * plant, -1)); P.aim("lowerarm_r", (-0.2, -0.65 - 0.2 * plant, -0.75))


# ------------------------------------------------------------------ clips
def gait(P, p, key, stride=24.0, knee=55.0, bob=0.016, arm=18.0, lean=3.0, lift=0.0, run=False):
    s = P.scale
    phL, phR = p, p + 0.5
    for side, ph in (("l", phL), ("r", phR)):
        hip = stride * math.sin(TAU * ph) + lift * max(0.0, math.cos(TAU * ph))
        kn = 6 + knee * max(0.0, math.cos(TAU * ph - 0.35)) ** 1.5 + (lift * 1.2 * max(0.0, math.cos(TAU * ph)))
        ank = -10 * math.sin(TAU * ph) + (0.25 * kn if math.cos(TAU * ph) > 0 else 0)
        P.leg(side, hip, kn, ank)
    P.pelvis(dz=-(bob * s) * (1 - math.cos(4 * math.pi * p)) * 0.5 - (0.03 * s if run else 0.0), yaw=6 * math.sin(TAU * p),
             roll=2.5 * math.sin(TAU * p + math.pi / 2))
    P.spine(lean=lean, yaw=-8 * math.sin(TAU * p))
    left_free = key != "B" and key != "C"
    right_free = key != "C"
    el = 35 if run else 14
    if left_free:
        P.arm("l", -arm * math.sin(TAU * p), elbow=el + 8 * max(0, -math.sin(TAU * p)))
    if right_free:
        P.arm("r", arm * math.sin(TAU * p), elbow=el + 8 * max(0, math.sin(TAU * p)))
    P.head(nod=-lean * 0.4, yaw=-3 * math.sin(TAU * p))


def clip_idle(P, p, key):
    br = math.sin(TAU * p)
    P.pelvis(roll=1.6 * math.sin(TAU * p * 0.5 + 0.3), dz=-0.003 * P.scale * (1 + br) * 0.5)
    P.leg("l", 1.5, 4 + 2 * br); P.leg("r", -1.0, 3)
    P.spine(lean=1.0 * br, roll=-1.2 * math.sin(TAU * p * 0.5 + 0.3))
    P.rot("spine_03", (1, 0, 0), -0.8 * br)
    P.head(nod=1.5 * br, yaw=10 * math.sin(TAU * p * 0.5), tilt=2 * math.sin(TAU * p))
    if key not in ("B", "C"):
        P.arm("l", 2 * br, elbow=8)
    P.arm("r", -2 * br, elbow=8) if key != "C" else None


def clip_walk(P, p, key):
    gait(P, p, key, stride=24 if key != "C" else 17, knee=52, bob=0.016, arm=18 if key != "C" else 8, lean=3 if key != "C" else 4)
    if key == "C":
        hold_cane(P, plant=0.5 + 0.5 * math.sin(TAU * p))


def clip_run(P, p, key):
    gait(P, p, key, stride=38, knee=95, bob=0.035, arm=38, lean=12, run=True)


def clip_climb_stairs(P, p, key):
    gait(P, p, key, stride=20, knee=70, bob=0.03, arm=14, lean=11, lift=26)
    if key == "C":
        hold_cane(P, plant=0.5 + 0.5 * math.sin(TAU * p))


def clip_climb_ladder(P, p, key):
    s = math.sin(TAU * p)
    P.spine(lean=6)
    for side, sg in (("l", 1), ("r", -1)):
        up = 0.5 + 0.5 * s * sg
        P.aim(f"upperarm_{side}", (0.18 * sg, -0.55, 0.35 + 0.6 * up))
        P.aim(f"lowerarm_{side}", (0.05 * sg, -0.35, 1.0))
        P.fingers(side, 0.9)
        P.leg(side, 15 + 45 * (1 - up), 25 + 70 * (1 - up), 10)
    P.pelvis(dz=0.02 * P.scale * s, dy=0.03)
    P.head(nod=8)


def clip_open_door(P, p, key):
    reach = min(1.0, p / 0.35)
    push = max(0.0, (p - 0.35) / 0.65)
    P.spine(lean=6 * reach + 4 * push, yaw=-8 * reach)
    P.aim("upperarm_r", (-0.15, -1.0, -0.35 + 0.25 * push))
    P.aim("lowerarm_r", (-0.05, -1.0, -0.1))
    P.fingers("r", 0.6)
    P.leg("l", 10 * push, 10); P.leg("r", -6 * push, 8)
    P.head(yaw=-6)


def clip_cook(P, p, key):
    a = TAU * p
    P.spine(lean=10)
    P.aim("upperarm_r", (-0.25 + 0.1 * math.cos(a), -0.7, -0.6))
    P.aim("lowerarm_r", (0.25 * math.cos(a), -1.0, -0.25 + 0.15 * math.sin(a)))
    P.fingers("r", 0.9)
    if key not in ("B",):
        P.aim("upperarm_l", (0.25, -0.6, -0.75)); P.aim("lowerarm_l", (-0.2, -1.0, -0.15))
    P.head(nod=12, yaw=4 * math.sin(a))
    P.leg("l", 3, 6); P.leg("r", -2, 5)


def seated(P, key, lean=6.0):
    drop = P.thigh * 0.92
    P.pelvis(dz=-drop, dy=0.04 * P.scale)
    P.leg("l", 88, 88, 0, splay=4); P.leg("r", 88, 88, 0, splay=4)
    P.spine(lean=lean)


def clip_sit(P, p, key):
    seated(P, key, lean=4 + 1.2 * math.sin(TAU * p))
    if key not in ("B", "C"):
        P.aim("upperarm_l", (0.15, -0.35, -1)); P.aim("lowerarm_l", (-0.15, -1, -0.1))
    if key != "C":
        P.aim("upperarm_r", (-0.15, -0.35, -1)); P.aim("lowerarm_r", (0.15, -1, -0.1))
    P.head(nod=3 * math.sin(TAU * p), yaw=12 * math.sin(TAU * p * 0.5))


def clip_eat(P, p, key):
    seated(P, key, lean=10)
    lift = 0.5 - 0.5 * math.cos(TAU * p)
    P.aim("upperarm_r", (-0.2, -0.6 - 0.2 * lift, -1 + 0.6 * lift))
    P.aim("lowerarm_r", (0.3 * lift, -0.6 + 0.3 * lift, -0.1 + 1.2 * lift))
    P.fingers("r", 0.8)
    if key not in ("B",):
        P.aim("upperarm_l", (0.15, -0.45, -1)); P.aim("lowerarm_l", (-0.2, -1, -0.15))
    P.head(nod=8 - 10 * lift)


def clip_sleep(P, p, key):
    br = math.sin(TAU * p)
    s = P.scale
    P.pelvis(dz=0.52 * s - P.hip_z, dy=0.0, pitch=-90)
    P.rot("spine_03", (1, 0, 0), 1.2 * br)
    P.leg("l", -4, 10, 20); P.leg("r", -2, 14, 20)
    P.aim("upperarm_l", (0.3, -1.0, 0.05)); P.aim("upperarm_r", (-0.3, -1.0, 0.05))
    P.aim("lowerarm_l", (0.05, -1.0, 0.25)); P.aim("lowerarm_r", (-0.05, -1.0, 0.25))
    P.head(nod=6, yaw=12)


def clip_fish(P, p, key):
    s = math.sin(TAU * p)
    P.spine(lean=4)
    P.aim("upperarm_r", (-0.12, -0.65, -0.65 + 0.06 * s)); P.aim("lowerarm_r", (0.05, -0.95, 0.25 + 0.08 * s))
    P.aim("upperarm_l", (0.12, -0.6, -0.75)); P.aim("lowerarm_l", (-0.2, -0.95, 0.1))
    P.fingers("r", 0.95); P.fingers("l", 0.95)
    P.leg("l", 8, 10); P.leg("r", -5, 6)
    P.head(nod=6 + 2 * s, yaw=3 * s)


def clip_work(P, p, key):
    # hammering: raise (0..0.55), strike (0.55..0.7), recover
    if p < 0.55:
        u = p / 0.55
        h = math.sin(u * math.pi / 2)
    elif p < 0.7:
        u = (p - 0.55) / 0.15
        h = 1 - u
    else:
        h = 0.0
    P.spine(lean=12 - 4 * h)
    P.aim("upperarm_r", (-0.2, -0.75 + 0.2 * h, -0.65 + 1.25 * h))
    P.aim("lowerarm_r", (-0.05, -1.0 + 1.3 * h, -0.2 + 0.9 * h))
    P.fingers("r", 0.95)
    if key not in ("B",):
        P.aim("upperarm_l", (0.2, -0.6, -0.8)); P.aim("lowerarm_l", (-0.15, -1, -0.25))
    P.head(nod=14)
    P.leg("l", 6, 10); P.leg("r", -4, 8)


def clip_wave(P, p, key):
    w = math.sin(TAU * p)
    P.aim("upperarm_r", (-0.85, -0.15, 0.55))
    P.aim("lowerarm_r", (-0.25 + 0.35 * w, -0.1, 1.0))
    P.fingers("r", 0.05)
    P.spine(roll=3)
    P.head(yaw=-6, tilt=4 * w)


def clip_haul_rope(P, p, key):
    # hand over hand: each hand reaches forward then pulls to the chest
    P.spine(lean=-8)
    P.leg("l", 18, 22, 5); P.leg("r", -10, 18)
    P.pelvis(dz=-0.04 * P.scale, dy=0.03 * P.scale)
    for side, ph, sg in (("l", p, 1), ("r", p + 0.5, -1)):
        u = 0.5 - 0.5 * math.cos(TAU * ph)
        P.aim(f"upperarm_{side}", (0.08 * sg, -0.9 + 0.75 * u, -0.45 - 0.1 * u))
        P.aim(f"lowerarm_{side}", (-0.1 * sg, -1.0 + 0.2 * u, 0.05 + 0.4 * u))
        P.fingers(side, 0.95)
    P.head(nod=6, yaw=4 * math.sin(TAU * p))


def clip_hand_fruit(P, p, key):
    # reach a mango out to a customer, hold, take it back
    u = math.sin(math.pi * min(1.0, p / 0.7)) if p < 0.7 else 0.0
    P.spine(lean=8 * u, yaw=-6 * u)
    P.aim("upperarm_r", (-0.2, -0.15 - 0.85 * u, -1 + 0.75 * u))
    P.aim("lowerarm_r", (-0.1, -0.3 - 0.7 * u, -1 + 1.0 * u))
    P.fingers("r", 0.6 - 0.25 * u)
    P.head(nod=-4 * u + 3, yaw=-10 * u, tilt=6 * u)
    P.leg("l", 6 * u, 6 + 6 * u); P.leg("r", -3 * u, 5)


def clip_mend_net(P, p, key):
    a = TAU * p
    P.spine(lean=8)
    for side, sg in (("l", 1), ("r", -1)):
        P.aim(f"upperarm_{side}", (0.2 * sg, -0.55, -0.85))
        P.aim(f"lowerarm_{side}", (-0.45 * sg + 0.1 * math.sin(a * 2 + sg), -1.0, 0.25 + 0.08 * math.sin(a + sg)))
        P.rot(f"hand_{side}", (0, 1, 0), 20 * math.sin(a * 2) * sg)
        P.fingers(side, 0.7 + 0.2 * math.sin(a * 2 + sg))
    P.head(nod=18 + 3 * math.sin(a), yaw=4 * math.sin(a * 0.5))


def clip_run_play(P, p, key):
    # skipping run with a little hop every cycle and a free swinging bucket arm
    gait(P, p, key, stride=34, knee=90, bob=0.03, arm=40, lean=9, run=True)
    hop = max(0.0, math.sin(TAU * p * 2)) ** 2
    P.move("pelvis", dz=0.035 * P.scale * hop)
    P.head(yaw=10 * math.sin(TAU * p), tilt=5 * math.sin(TAU * p * 2))


# ------------------------------------------------------------------ village-life clips (session 8)
def clip_give(P, p, key):
    """Take an item from the basket / counter at the hip, reach it out, hold, come back."""
    if p < 0.2:                       # dip to the basket / counter
        u = p / 0.2; reach = 0.0; dip = math.sin(math.pi * u)
    else:
        u = (p - 0.2) / 0.8; reach = math.sin(math.pi * min(1.0, u / 0.85)); dip = 0.0
    P.spine(lean=6 * reach + 10 * dip, yaw=-6 * reach + 8 * dip)
    P.aim("upperarm_r", (-0.25 + 0.05 * dip, -0.15 - 0.85 * reach + 0.2 * dip, -1 + 0.75 * reach))
    P.aim("lowerarm_r", (-0.1 - 0.2 * dip, -0.3 - 0.7 * reach, -1 + 1.0 * reach))
    P.fingers("r", 0.8 - 0.3 * reach)
    P.head(nod=6 * dip - 3 * reach + 2, yaw=-10 * reach + 10 * dip, tilt=5 * reach)
    P.leg("l", 6 * reach, 6 + 6 * reach); P.leg("r", -3 * reach, 5)


def clip_carry(P, p, key):
    """Walk carrying something in both hands in front (crate, basket, catch)."""
    gait(P, p, key, stride=20, knee=48, bob=0.014, arm=0, lean=4)
    for side, sg in (("l", 1), ("r", -1)):
        P.aim(f"upperarm_{side}", (0.12 * sg, -0.35, -1)); P.aim(f"lowerarm_{side}", (-0.25 * sg, -1, 0.15 + 0.03 * math.sin(TAU * p * 2)))
        P.fingers(side, 0.8)


def boat_seat(P, lean=0.0):
    drop = P.thigh * 0.95 + 0.12 * P.scale            # thwart is lower than a chair
    P.pelvis(dz=-drop, dy=0.02 * P.scale)
    P.leg("l", 70, 95, 0, splay=8); P.leg("r", 70, 95, 0, splay=8)
    P.spine(lean=lean)


def clip_row(P, p, key):
    """Rowing seated on a thwart, facing the stern: catch (lean forward, arms long),
    drive (lean back, hands to the chest), recovery. The game turns the oars with the
    same phase (HeroVillager.row_phase)."""
    u = 0.5 - 0.5 * math.cos(TAU * p)                 # 0 catch .. 1 finish
    boat_seat(P, lean=24 - 36 * u)
    for side, sg in (("l", 1), ("r", -1)):
        P.aim(f"upperarm_{side}", (0.35 * sg, -0.95 + 0.9 * u, -0.25 - 0.25 * u))
        P.aim(f"lowerarm_{side}", (-0.05 * sg, -1.0 + 0.4 * u, 0.1 + 0.15 * u))
        P.fingers(side, 0.95)
    P.head(nod=-6 + 10 * u)


def clip_steer(P, p, key):
    """Seated at the stern, right hand on the outboard tiller, eyes ahead."""
    boat_seat(P, lean=4 + 2 * math.sin(TAU * p))
    P.aim("upperarm_r", (-0.6, 0.55, -0.6)); P.aim("lowerarm_r", (-0.2, 1.0, -0.15 + 0.05 * math.sin(TAU * p)))
    P.fingers("r", 0.95)
    P.aim("upperarm_l", (0.25, -0.2, -1)); P.aim("lowerarm_l", (-0.1, -1, -0.2))
    P.head(yaw=-8 + 14 * math.sin(TAU * p * 0.5), nod=-4)


def clip_swim(P, p, key):
    """Front crawl near the surface; the game keeps the swimmer at the waterline."""
    s = P.scale
    P.pelvis(dz=-P.hip_z + 0.04 * s, pitch=80, roll=8 * math.sin(TAU * p))
    for side, ph in (("l", 0.0), ("r", 0.5)):
        P.rot(f"upperarm_{side}", (1, 0, 0), -(360.0 * ((p + ph) % 1.0)) - 90)
        P.rot(f"lowerarm_{side}", (1, 0, 0), -25 - 25 * max(0.0, math.sin(TAU * (p + ph))))
        P.fingers(side, 0.2)
        P.leg(side, 12 * math.sin(TAU * (p * 3 + ph)), 10 + 8 * max(0, math.sin(TAU * (p * 3 + ph))), -30)
    P.head(nod=-30, yaw=25 * max(0.0, math.sin(TAU * p)))


def clip_cast(P, p, key):
    """Cast a line: back swing over the shoulder, flick forward, then hold and wait."""
    if p < 0.25:
        u = p / 0.25; back = math.sin(u * math.pi / 2); fwd = 0.0
    elif p < 0.4:
        u = (p - 0.25) / 0.15; back = 1 - u; fwd = u
    else:
        back = 0.0; fwd = 1.0
    bob = 0.03 * math.sin(TAU * p * 3) * (p > 0.4)
    P.spine(lean=-6 * back + 8 * fwd, yaw=-12 * back + 4 * fwd)
    P.aim("upperarm_r", (-0.25, -0.6 * fwd + 0.25 * back, -0.6 * fwd + 0.9 * back + bob))
    P.aim("lowerarm_r", (-0.05, -0.9 * fwd + 0.3 * back, 0.3 * fwd + 1.0 * back))
    P.aim("upperarm_l", (0.15, -0.6, -0.7)); P.aim("lowerarm_l", (-0.25, -0.95, 0.05))
    P.fingers("r", 0.95); P.fingers("l", 0.9)
    P.leg("l", 10 * fwd, 10); P.leg("r", -6 * fwd, 6)
    P.head(nod=4, yaw=4 * fwd)


def clip_haul_net(P, p, key):
    """Bent over the gunwale pulling a net in, hand over hand."""
    P.spine(lean=32)
    P.leg("l", 12, 22, 4); P.leg("r", -6, 18)
    P.pelvis(dz=-0.05 * P.scale)
    for side, ph, sg in (("l", p, 1), ("r", p + 0.5, -1)):
        u = 0.5 - 0.5 * math.cos(TAU * ph)
        P.aim(f"upperarm_{side}", (0.2 * sg, -0.6 + 0.45 * u, -0.9 + 0.55 * u))
        P.aim(f"lowerarm_{side}", (-0.1 * sg, -0.8 + 0.4 * u, -0.5 + 0.8 * u))
        P.fingers(side, 0.95)
    P.head(nod=14)


def clip_sweep(P, p, key):
    a = math.sin(TAU * p)
    P.spine(lean=14, yaw=10 * a)
    P.aim("upperarm_r", (-0.25 + 0.15 * a, -0.5, -0.9)); P.aim("lowerarm_r", (0.1 + 0.4 * a, -0.6, -0.5))
    P.aim("upperarm_l", (0.2 + 0.15 * a, -0.6, -0.6)); P.aim("lowerarm_l", (-0.2 + 0.4 * a, -0.8, -0.1))
    P.fingers("r", 0.9); P.fingers("l", 0.9)
    P.leg("l", 6, 10); P.leg("r", -4, 8)
    P.head(nod=16, yaw=6 * a)


def clip_talk(P, p, key):
    g = math.sin(TAU * p); g2 = math.sin(TAU * p * 2 + 1.0)
    P.spine(lean=2 + g2, yaw=4 * g)
    P.aim("upperarm_r", (-0.3, -0.35 - 0.15 * max(0, g), -1)); P.aim("lowerarm_r", (0.15 * g, -1.0, 0.2 + 0.35 * max(0, g)))
    P.fingers("r", 0.2 + 0.2 * abs(g2))
    if key not in ("B", "C"):
        P.aim("upperarm_l", (0.25, -0.15, -1)); P.aim("lowerarm_l", (0.1, -0.7, -0.6 + 0.3 * max(0, -g)))
    P.head(nod=4 * g2, yaw=8 * g, tilt=4 * math.sin(TAU * p * 0.5))
    P.leg("l", 3, 5); P.leg("r", -2, 4)


def clip_play(P, p, key):
    """Hop and skip in place, arms swinging high (children at play)."""
    hop = max(0.0, math.sin(TAU * p)) ** 1.5
    crouch = max(0.0, -math.sin(TAU * p))
    P.pelvis(dz=(0.07 * hop - 0.05 * crouch) * P.scale)
    P.leg("l", 20 * crouch + 10 * hop, 50 * crouch + 15 * hop, 10); P.leg("r", 20 * crouch - 5 * hop, 50 * crouch + 10 * hop, 10)
    for side, sg in (("l", 1), ("r", -1)):
        P.aim(f"upperarm_{side}", (0.5 * sg, -0.2, -0.6 + 1.6 * hop)); P.aim(f"lowerarm_{side}", (0.3 * sg, -0.1, -0.3 + 1.3 * hop))
        P.fingers(side, 0.3)
    P.head(nod=-6 * hop, yaw=12 * math.sin(TAU * p * 0.5))


CLIP_DEFS = {
    "idle": (clip_idle, 3.0), "walk": (clip_walk, 1.0), "run": (clip_run, 0.66), "climb_stairs": (clip_climb_stairs, 1.1),
    "climb_ladder": (clip_climb_ladder, 1.2), "open_door": (clip_open_door, 1.2), "cook": (clip_cook, 1.4),
    "eat": (clip_eat, 1.8), "sit": (clip_sit, 4.0), "sleep": (clip_sleep, 4.0), "fish": (clip_fish, 3.0),
    "work": (clip_work, 0.9), "wave": (clip_wave, 0.8),
    "haul_rope": (clip_haul_rope, 1.6), "hand_fruit": (clip_hand_fruit, 2.6), "mend_net": (clip_mend_net, 2.0),
    "run_play": (clip_run_play, 0.7),
    "give": (clip_give, 2.4), "carry": (clip_carry, 1.0), "row": (clip_row, 1.8), "steer": (clip_steer, 3.0),
    "swim": (clip_swim, 1.4), "cast": (clip_cast, 4.0), "haul_net": (clip_haul_net, 1.5), "sweep": (clip_sweep, 1.2),
    "talk": (clip_talk, 2.4), "play": (clip_play, 0.8),
}

HOLD_B = {"idle", "walk", "climb_stairs", "run", "hand_fruit", "give", "talk", "sit", "eat"}
HOLD_C_NET = {"idle", "walk", "climb_stairs", "sit", "talk", "give", "run"}
HOLD_C_CANE = {"idle", "talk", "give"}


def clips_for(key):
    return CONTRACT + EXTRA + ([JOB[key]] if key in JOB else [])


def pose_at(c, clip, p):
    P = c._poser if getattr(c, "_poser", None) else Poser(c)
    c._poser = P
    P.reset()
    base(P, c.key)
    if c.key == "B" and clip in HOLD_B:
        hold_basket(P)
    if c.key == "C" and clip in HOLD_C_NET:
        hold_net(P)
        if clip in HOLD_C_CANE:
            hold_cane(P)
    fn, _ = CLIP_DEFS[clip]
    fn(P, p, c.key)
    return P


def bake(c, clips=None, mute_mods=True):
    """Bake every clip to its own action + NLA track (named after the clip)."""
    rig = c.rig
    clips = clips or clips_for(c.key)
    mods = []
    if mute_mods:
        for n, (ob, cat) in c.parts.items():
            for m in ob.modifiers:
                if m.type == "ARMATURE" and m.show_viewport:
                    m.show_viewport = False; mods.append(m)
    rig.animation_data_create()
    made = {}
    for clip in clips:
        fn, L = CLIP_DEFS[clip]
        n = max(2, int(round(L * FPS)))
        act = bpy.data.actions.new(f"{c.key}_{clip}")
        act.use_fake_user = True
        rig.animation_data.action = act
        loop = clip in LOOPING
        for f in range(n + 1):
            p = (f / n) if not loop else (f % n) / n
            if not loop:
                p = min(p, 1.0)
            pose_at(c, clip, p)
            for pb in rig.pose.bones:
                pb.keyframe_insert("rotation_quaternion", frame=f + 1, group=pb.name)
                if pb.name in ("pelvis", "Root"):
                    pb.keyframe_insert("location", frame=f + 1, group=pb.name)
        rig.animation_data.action = None
        tr = rig.animation_data.nla_tracks.new()
        tr.name = clip
        st = tr.strips.new(clip, 1, act)
        st.name = clip
        tr.mute = True
        made[clip] = dict(frames=n + 1, seconds=L, loop=loop)
    for m in mods:
        m.show_viewport = True
    c._poser.reset() if getattr(c, "_poser", None) else None
    return made


def show(c, clip, p):
    """Pose the character at phase p of a clip (for renders)."""
    pose_at(c, clip, p)
