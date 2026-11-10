"""Furniture and interaction-object models for every anchor type named in
data/village_layout.json (BUILDING_CONTRACT.md).

Frame for every builder: back edge on y=0 (against a wall), the piece extends
+y into the room, centred on x=0, floor at z=0.  The villager stands at
(0, d + STAND) facing -y.
"""
from __future__ import annotations
import math
from .geom import Mesh, T, Rz, Rx

STAND = 0.42


def bed(m, rng, blanket="fabric_a"):
    L, W = 1.9, 0.9            # lies along x: head at -x
    for x in (-L / 2 + 0.05, L / 2 - 0.05):
        for y in (0.05, W - 0.05):
            m.box(x - 0.04, y - 0.04, 0, x + 0.04, y + 0.04, 0.34, "wood_dark")
    m.box(-L / 2, 0.02, 0.22, L / 2, W - 0.02, 0.30, "wood_mid", rng=rng, vary=0.05)
    m.box(-L / 2 - 0.02, 0.0, 0.1, -L / 2 + 0.03, W, 0.85, "wood_mid", wob=0.01, rng=rng, vary=0.05)      # headboard
    m.box(L / 2 - 0.03, 0.0, 0.1, L / 2 + 0.02, W, 0.55, "wood_mid", wob=0.01, rng=rng)
    m.box(-L / 2 + 0.04, 0.05, 0.30, L / 2 - 0.04, W - 0.05, 0.42, "fabric_white")
    m.box(-L / 2 + 0.55, 0.03, 0.40, L / 2 - 0.03, W - 0.03, 0.455, blanket, wob=0.012, rng=rng)
    m.box(-L / 2 + 0.08, 0.2, 0.42, -L / 2 + 0.45, W - 0.2, 0.50, "fabric_white", wob=0.015, rng=rng)


def stove(m, rng, flue_to=2.6):
    w, d = 0.78, 0.52
    for x in (-w / 2 + 0.05, w / 2 - 0.05):
        for y in (0.06, d - 0.05):
            m.box(x - 0.03, y - 0.03, 0, x + 0.03, y + 0.03, 0.16, "iron")
    m.box(-w / 2, 0.02, 0.16, w / 2, d, 0.74, "iron", wob=0.006, rng=rng)
    m.box(-w / 2 - 0.02, 0.0, 0.74, w / 2 + 0.02, d + 0.02, 0.78, "iron_lit")
    m.box(-0.2, d, 0.26, 0.2, d + 0.012, 0.52, "iron_lit")                     # fire door
    m.box(-0.13, d + 0.012, 0.31, 0.13, d + 0.02, 0.46, "emit_fire")           # glow slot
    with m.push(T(-0.14, 0.27, 0.78)):
        m.lathe([(0.13, 0), (0.16, 0.05), (0.16, 0.2), (0.14, 0.22)], 8, "iron_lit")       # pot
    with m.push(T(0.2, 0.26, 0.78)):
        m.lathe([(0.11, 0), (0.12, 0.03), (0.02, 0.035)], 8, "iron")                        # pan
    with m.push(T(0.22, 0.12, 0.78)):
        m.cyl(0.07, flue_to - 0.78, 8, "tin_bare")
    # firewood
    for i in range(4):
        m.cbox(w / 2 + 0.22 + (i % 2) * 0.1, 0.2, 0.05 + (i // 2) * 0.1, 0.09, 0.36, 0.09, "wood_light", rz=rng.uniform(-0.2, 0.2), rng=rng, vary=0.1)


def sink(m, rng):
    w, d = 0.7, 0.48
    for x in (-w / 2 + 0.04, w / 2 - 0.04):
        for y in (0.04, d - 0.04):
            m.box(x - 0.03, y - 0.03, 0, x + 0.03, y + 0.03, 0.78, "wood_mid")
    m.box(-w / 2, 0, 0.72, w / 2, d, 0.80, "wood_light", rng=rng, vary=0.05)
    m.box(-0.24, 0.08, 0.80, 0.24, d - 0.06, 0.92, "enamel")
    m.box(-0.2, 0.12, 0.90, 0.2, d - 0.10, 0.925, "water_still")
    m.box(-w / 2 + 0.03, 0.02, 0.3, w / 2 - 0.03, d - 0.02, 0.33, "wood_mid")
    with m.push(T(0.18, 0.2, 0.33)):
        m.lathe([(0.11, 0), (0.13, 0.18), (0.12, 0.2)], 8, "tin_bare")                      # bucket


def cabinet(m, rng):
    w, d, h = 0.8, 0.38, 1.7
    m.box(-w / 2, 0, 0.06, w / 2, d, h, "wood_mid", wob=0.008, rng=rng, vary=0.04)
    for i, x in enumerate((-w / 4, w / 4)):
        m.box(x - w / 4 + 0.02, d, 0.1, x + w / 4 - 0.02, d + 0.02, h - 0.04, "trim", rng=rng, vary=0.05)
        m.cbox(x + (0.12 if i == 0 else -0.12), d + 0.03, h * 0.5, 0.025, 0.02, 0.1, "brass")
    m.box(-w / 2 - 0.02, -0.0, h, w / 2 + 0.02, d + 0.03, h + 0.03, "wood_dark")


def storage(m, rng):
    w, d, h = 0.82, 0.44, 0.42
    m.box(-w / 2, 0.02, 0.03, w / 2, d, h, "wood_mid", wob=0.008, rng=rng, vary=0.05)
    m.box(-w / 2 - 0.015, 0.0, h, w / 2 + 0.015, d + 0.015, h + 0.06, "wood_dark", wob=0.006, rng=rng)
    for x in (-w / 2 + 0.1, w / 2 - 0.1):
        m.box(x - 0.025, d, 0.03, x + 0.025, d + 0.008, h + 0.06, "iron")


def washstand(m, rng):
    w, d = 0.55, 0.38
    for x in (-w / 2 + 0.03, w / 2 - 0.03):
        for y in (0.03, d - 0.03):
            m.box(x - 0.025, y - 0.025, 0, x + 0.025, y + 0.025, 0.74, "wood_mid")
    m.box(-w / 2, 0, 0.72, w / 2, d, 0.76, "wood_light")
    with m.push(T(0, d / 2, 0.76)):
        m.lathe([(0.08, 0), (0.17, 0.09), (0.16, 0.1), (0.07, 0.02)], 8, "enamel")
    m.box(-0.16, 0.0, 1.05, 0.16, 0.02, 1.5, "glass_mirror")
    m.box(w / 2 - 0.02, 0.05, 0.45, w / 2 + 0.0, d - 0.05, 0.7, "fabric_white")


def counter(m, rng, w=1.6):
    d = 0.55
    m.box(-w / 2, 0.04, 0, w / 2, d - 0.04, 0.9, "wall", rng=rng, vary=0.04)
    m.box(-w / 2 - 0.04, 0, 0.9, w / 2 + 0.04, d, 0.95, "wood_light", wob=0.006, rng=rng)
    for i in range(3):
        with m.push(T(-w / 2 + 0.3 + i * 0.45, d / 2, 0.95)):
            m.lathe([(0.07, 0), (0.09, 0.12), (0.05, 0.16), (0.055, 0.2)], 8, rng.choice(["clay", "glass_jar", "enamel"]))


def shelf(m, rng, w=1.2):
    d, h = 0.34, 1.8
    for x in (-w / 2, w / 2 - 0.04):
        m.box(x, 0, 0, x + 0.04, d, h, "wood_mid")
    for i in range(5):
        z = 0.12 + i * 0.4
        m.box(-w / 2, 0, z, w / 2, d, z + 0.035, "wood_light", rng=rng, vary=0.05)
        x = -w / 2 + 0.12
        while x < w / 2 - 0.15 and i < 4:
            k = rng.random()
            if k < 0.4:
                m.box(x, 0.05, z + 0.035, x + 0.2, d - 0.05, z + 0.035 + rng.uniform(0.12, 0.26), rng.choice(["crate", "fabric_a", "fabric_b"]), rng=rng, vary=0.08)
                x += 0.26
            elif k < 0.8:
                with m.push(T(x + 0.08, d / 2, z + 0.035)):
                    m.lathe([(0.06, 0), (0.08, 0.1), (0.045, 0.18), (0.05, 0.22)], 7, rng.choice(["clay", "glass_jar", "enamel"]))
                x += 0.2
            else:
                x += 0.18


def workbench(m, rng, w=1.6):
    d = 0.6
    for x in (-w / 2 + 0.06, w / 2 - 0.06):
        for y in (0.06, d - 0.06):
            m.box(x - 0.045, y - 0.045, 0, x + 0.045, y + 0.045, 0.82, "wood_dark")
    m.box(-w / 2, 0, 0.82, w / 2, d, 0.9, "wood_light", wob=0.008, rng=rng, vary=0.05)
    m.box(-w / 2 + 0.06, 0.06, 0.2, w / 2 - 0.06, d - 0.06, 0.23, "wood_mid")
    m.cbox(-0.3, 0.3, 0.93, 0.34, 0.07, 0.06, "wood_mid", rz=0.3)       # plane
    m.cbox(0.35, 0.25, 0.915, 0.5, 0.04, 0.03, "iron", rz=-0.4)          # saw blade
    m.cbox(w / 2 - 0.12, d - 0.1, 0.96, 0.14, 0.12, 0.12, "iron")        # vice


def tool_rack(m, rng):
    w = 1.0
    m.box(-w / 2, 0, 1.0, w / 2, 0.03, 1.7, "wood_mid", rng=rng, vary=0.05)
    for i in range(5):
        x = -w / 2 + 0.12 + i * 0.19
        m.box(x - 0.012, 0.03, 1.15, x + 0.012, 0.05, 1.15 + rng.uniform(0.25, 0.45), "wood_light")
        m.cbox(x, 0.05, 1.13, rng.uniform(0.06, 0.12), 0.03, rng.uniform(0.05, 0.1), "iron")


def timber_stack(m, rng):
    for k in range(4):
        n = 5 - (k % 2)
        for i in range(n):
            m.box(-0.8 + rng.uniform(-0.05, 0.05), 0.05 + i * 0.11, k * 0.09, 0.8 + rng.uniform(-0.1, 0.1), 0.05 + i * 0.11 + 0.1, k * 0.09 + 0.08,
                  "wood_light", rng=rng, vary=0.12)


def saw_horse(m, rng):
    m.box(-0.5, 0.18, 0.62, 0.5, 0.28, 0.72, "wood_mid")
    for x in (-0.4, 0.4):
        m.beam((x, 0.02, 0), (x, 0.2, 0.64), 0.06, 0.05, "wood_mid")
        m.beam((x, 0.44, 0), (x, 0.26, 0.64), 0.06, 0.05, "wood_mid")
    m.box(-0.7, 0.12, 0.72, 0.6, 0.34, 0.76, "wood_light", rng=rng, vary=0.1)


def net_frame(m, rng):
    w = 1.4
    for x in (-w / 2, w / 2):
        m.box(x - 0.03, 0.05, 0, x + 0.03, 0.11, 1.7, "wood_mid")
        m.box(x - 0.03, 0.0, 0, x + 0.03, 0.4, 0.05, "wood_mid")
    m.box(-w / 2, 0.05, 1.64, w / 2, 0.11, 1.7, "wood_mid")
    for i in range(9):
        x = -w / 2 + 0.08 + i * (w - 0.16) / 8
        m.box(x - 0.006, 0.075, 0.25, x + 0.006, 0.085, 1.64, "rope")
    for j in range(7):
        z = 0.3 + j * 0.2
        m.box(-w / 2 + 0.05, 0.075, z - 0.006, w / 2 - 0.05, 0.085, z + 0.006, "rope")
    for i in range(4):
        with m.push(T(-w / 2 + 0.2 + i * 0.33, 0.09, 0.27)):
            m.blob(0.05, 0.05, 0.05, "float_a" if i % 2 else "float_b", rng, sub=0, rough=0.05)


def ice_box(m, rng):
    m.box(-0.45, 0.02, 0.05, 0.45, 0.58, 0.72, "enamel", wob=0.006, rng=rng)
    m.box(-0.47, 0.0, 0.72, 0.47, 0.6, 0.78, "tin_bare")
    m.box(-0.1, 0.6, 0.45, 0.1, 0.62, 0.5, "iron")


def scales(m, rng):
    m.box(-0.25, 0.05, 0, 0.25, 0.35, 0.8, "wood_mid", rng=rng, vary=0.05)
    m.box(-0.28, 0.02, 0.8, 0.28, 0.38, 0.84, "wood_light")
    m.box(-0.02, 0.18, 0.84, 0.02, 0.22, 1.2, "brass")
    m.box(-0.22, 0.19, 1.18, 0.22, 0.21, 1.2, "brass")
    for x in (-0.2, 0.2):
        with m.push(T(x, 0.2, 1.0)):
            m.lathe([(0.02, 0), (0.09, 0.02), (0.1, 0.04)], 8, "brass")


def desk(m, rng, w=1.0):
    d = 0.55
    for x in (-w / 2 + 0.04, w / 2 - 0.04):
        for y in (0.04, d - 0.04):
            m.box(x - 0.03, y - 0.03, 0, x + 0.03, y + 0.03, 0.72, "wood_mid")
    m.box(-w / 2, 0, 0.72, w / 2, d, 0.76, "wood_light", rng=rng, vary=0.05)
    m.cbox(-0.15, 0.3, 0.775, 0.3, 0.22, 0.03, "paper", rz=rng.uniform(-0.2, 0.2))
    m.cbox(0.3, 0.2, 0.8, 0.06, 0.06, 0.08, "glass_jar")


def board(m, rng):
    m.box(-0.75, 0, 0.9, 0.75, 0.03, 1.8, "slate")
    for bx in ((-0.78, -0.75), (0.75, 0.78)):
        m.box(bx[0], 0, 0.87, bx[1], 0.045, 1.83, "wood_mid")
    m.box(-0.78, 0, 0.87, 0.78, 0.045, 0.9, "wood_mid"); m.box(-0.78, 0, 1.8, 0.78, 0.045, 1.83, "wood_mid")
    m.box(-0.6, 0.03, 0.9, 0.6, 0.09, 0.92, "wood_light")


def stage(m, rng, w=2.4):
    for i in range(int(w / 0.25)):
        m.box(-w / 2 + i * 0.25 + 0.005, 0, 0.26, -w / 2 + (i + 1) * 0.25 - 0.005, 1.1, 0.3, "wood_light", rng=rng, vary=0.07)
    m.box(-w / 2, 0.02, 0, w / 2, 1.08, 0.26, "wood_dark")


def bench(m, rng, w=1.4):
    m.box(-w / 2, 0.04, 0.4, w / 2, 0.36, 0.45, "wood_light", wob=0.006, rng=rng, vary=0.06)
    for x in (-w / 2 + 0.1, w / 2 - 0.1):
        m.box(x - 0.03, 0.06, 0, x + 0.03, 0.34, 0.4, "wood_mid")


def stall(m, rng, awning="fabric_a"):
    w, d = 1.6, 0.8
    for x in (-w / 2 + 0.05, w / 2 - 0.05):
        for y in (0.05, d - 0.05):
            m.box(x - 0.035, y - 0.035, 0, x + 0.035, y + 0.035, 0.8 if y > 0.1 else 2.0, "wood_mid")
    m.box(-w / 2, 0, 0.78, w / 2, d, 0.84, "wood_light", rng=rng, vary=0.05)
    # tilted display tray with fish on ice
    pts = [(-w / 2 + 0.05, 0.15, 0.84), (w / 2 - 0.05, 0.15, 0.98), (w / 2 - 0.05, d - 0.02, 0.84), (-w / 2 + 0.05, d - 0.02, 0.84)]
    m.box(-w / 2 + 0.05, 0.1, 0.84, w / 2 - 0.05, d - 0.03, 0.9, "ice")
    for i in range(7):
        with m.push(T(-w / 2 + 0.2 + i * 0.2, 0.3 + (i % 2) * 0.22, 0.92), Rz(rng.uniform(-0.5, 0.5))):
            m.blob(0.12, 0.04, 0.025, rng.choice(["fish_a", "fish_b"]), rng, sub=0, rough=0.05)
    for i in range(6):
        a, b = -w / 2 + i * w / 6, -w / 2 + (i + 1) * w / 6
        m.add([(a, 0.0, 2.0), (b, 0.0, 2.0), (b, d + 0.25, 1.78), (a, d + 0.25, 1.78),
               (a, 0.0, 2.02), (b, 0.0, 2.02), (b, d + 0.25, 1.8), (a, d + 0.25, 1.8)], Mesh._BOX_F, awning if i % 2 else "fabric_white")


def table(m, rng, w=1.1):
    d = 0.7
    for x in (-w / 2 + 0.06, w / 2 - 0.06):
        for y in (0.06, d - 0.06):
            m.box(x - 0.035, y - 0.035, 0, x + 0.035, y + 0.035, 0.72, "wood_mid")
    for i in range(4):
        m.box(-w / 2, i * d / 4 + 0.003, 0.72, w / 2, (i + 1) * d / 4 - 0.003, 0.765, "wood_light", wob=0.004, rng=rng, vary=0.07)
    for x in (-0.28, 0.28):
        with m.push(T(x, d / 2, 0.765)):
            m.lathe([(0.05, 0), (0.11, 0.025), (0.105, 0.03), (0.04, 0.008)], 8, "enamel")
    with m.push(T(0, d / 2 + 0.05, 0.765)):
        m.lathe([(0.05, 0), (0.07, 0.1), (0.035, 0.2), (0.04, 0.24)], 8, "clay")
    with m.push(T(0.05, d / 2 - 0.15, 0.80)):
        m.blob(0.11, 0.07, 0.05, "bread", rng, sub=0, rough=0.1)


def chair(m, rng):
    s = 0.38
    for x in (-s / 2 + 0.025, s / 2 - 0.025):
        m.box(x - 0.02, 0.0, 0, x + 0.02, 0.04, 0.88, "wood_mid")
        m.box(x - 0.02, s - 0.04, 0, x + 0.02, s, 0.44, "wood_mid")
    m.box(-s / 2, 0, 0.42, s / 2, s, 0.46, "trim", rng=rng, vary=0.06)
    for z in (0.62, 0.8):
        m.box(-s / 2, 0.005, z, s / 2, 0.03, z + 0.06, "trim")


def slip_cradle(m, rng):
    for x in (-0.9, 0.0, 0.9):
        m.box(x - 0.06, 0.1, 0, x + 0.06, 1.1, 0.12, "wood_dark")
        m.beam((x, 0.15, 0.1), (x, 0.4, 0.55), 0.08, 0.08, "wood_mid")
        m.beam((x, 1.05, 0.1), (x, 0.8, 0.55), 0.08, 0.08, "wood_mid")
    # half-built hull ribs
    for i in range(7):
        x = -1.1 + i * 0.37
        k = 1 - abs(i - 3) / 4.5
        m.beam((x, 0.6 - 0.42 * k, 0.75), (x, 0.6, 0.3), 0.04, 0.05, "wood_light")
        m.beam((x, 0.6 + 0.42 * k, 0.75), (x, 0.6, 0.3), 0.04, 0.05, "wood_light")
    m.box(-1.3, 0.56, 0.24, 1.3, 0.64, 0.32, "wood_light")


def loading_point(m, rng):
    for i in range(3):
        m.cbox(-0.3 + i * 0.32, 0.3 + (i % 2) * 0.1, 0.2, 0.3, 0.3, 0.4, "crate", rz=rng.uniform(-0.2, 0.2), rng=rng, vary=0.1)
    m.cbox(-0.1, 0.33, 0.55, 0.3, 0.3, 0.3, "crate", rz=0.3, rng=rng, vary=0.1)


def lamp_hanging(m, rng, drop=0.5):
    """Origin at the ceiling fixing point; hangs down."""
    m.box(-0.006, -0.006, -drop, 0.006, 0.006, 0, "iron")
    with m.push(T(0, 0, -drop - 0.22)):
        m.lathe([(0.05, 0.0), (0.075, 0.03), (0.075, 0.17), (0.03, 0.22)], 6, "emit_lamp")
        m.lathe([(0.03, 0.2), (0.13, 0.215), (0.02, 0.27)], 8, "tin_bare")


def net_rack(m, rng, w=1.6):
    """Outdoor drying rack with a draped net and floats."""
    for x in (-w / 2, w / 2):
        m.box(x - 0.035, 0.1, 0, x + 0.035, 0.17, 1.55, "wood_mid", wob=0.01, rng=rng)
    m.box(-w / 2 - 0.1, 0.1, 1.5, w / 2 + 0.1, 0.17, 1.56, "wood_mid")
    n = 12
    for i in range(n):
        a, b = -w / 2 + i * w / n, -w / 2 + (i + 1) * w / n
        sag = 0.25 * math.sin(math.pi * (i + 0.5) / n)
        m.add([(a, 0.06, 0.55 - sag), (b, 0.06, 0.55 - sag), (b, 0.135, 1.5), (a, 0.135, 1.5),
               (a, 0.075, 0.55 - sag), (b, 0.075, 0.55 - sag), (b, 0.15, 1.5), (a, 0.15, 1.5)], Mesh._BOX_F, "net", 1.0 + rng.uniform(-0.08, 0.08))
    for i in range(5):
        with m.push(T(-w / 2 + 0.2 + i * 0.3, 0.05, 0.5 - 0.2 * math.sin(math.pi * (i + 0.7) / 5.5))):
            m.blob(0.06, 0.06, 0.06, "float_a" if i % 2 else "float_b", rng, sub=0, rough=0.05)


# type -> (width along wall, depth, placement, builder, use-pose)
#   placement: wall | free | ceiling | special
#   pose: where the villager is while using it: stand | lie | sit
REG = {
    "bed":          (1.95, 0.92, "wall", bed, "lie"),
    "stove":        (1.25, 0.55, "wall", stove, "stand"),
    "sink":         (0.75, 0.50, "wall", sink, "stand"),
    "cabinet":      (0.85, 0.40, "wall", cabinet, "stand"),
    "storage":      (0.86, 0.46, "wall", storage, "stand"),
    "washstand":    (0.60, 0.40, "wall", washstand, "stand"),
    "counter":      (1.70, 0.56, "wall", counter, "stand"),
    "shelf":        (1.25, 0.36, "wall", shelf, "stand"),
    "workbench":    (1.70, 0.62, "wall", workbench, "stand"),
    "tool_rack":    (1.05, 0.10, "wall", tool_rack, "stand"),
    "timber_stack": (1.80, 0.62, "wall", timber_stack, "stand"),
    "net_frame":    (1.50, 0.42, "wall", net_frame, "stand"),
    "ice_box":      (1.00, 0.62, "wall", ice_box, "stand"),
    "scales":       (0.62, 0.40, "wall", scales, "stand"),
    "desk":         (1.05, 0.56, "free", desk, "sit"),
    "teacher_desk": (1.05, 0.56, "wall", desk, "sit"),
    "ledger_desk":  (1.05, 0.56, "wall", desk, "sit"),
    "board":        (1.60, 0.10, "wall", board, "stand"),
    "stage":        (2.40, 1.12, "wall", stage, "stand"),
    "loading_point": (1.10, 0.70, "wall", loading_point, "stand"),
    "saw_horse":    (1.30, 0.50, "free", saw_horse, "stand"),
    "slip_cradle":  (2.70, 1.20, "free", slip_cradle, "stand"),
    "bench":        (1.45, 0.40, "free", bench, "sit"),
    "stall":        (1.65, 0.85, "free", stall, "stand"),
    "table":        (1.15, 0.72, "free", table, "stand"),
    "chair":        (0.40, 0.40, "seat", chair, "sit"),
    "lamp":         (0, 0, "ceiling", lamp_hanging, None),
    "net_rack":     (1.7, 0.3, "porch", net_rack, "stand"),
    "door":         (0, 0, "special", None, None),
    "stairs_interior": (0, 0, "special", None, None),
}
