"""Colour roles.  Hex values are the ART_BIBLE §4 palette; meshes carry role
names per face and bl_io bakes them to the vertex colour attribute `Col`."""

BIBLE = {
    "rock_l": "#DDB57A", "rock_m": "#C98B4C", "rock_d": "#955B33",
    "sea_l": "#79BEEC", "sea_m": "#4C97D6", "sea_d": "#3A78C2",
    "red": "#B5463C", "coral": "#D8725F", "ochre": "#D7A546", "cream": "#EBDCB4",
    "turq": "#3FA79E", "blue": "#3F7DC0", "deep": "#2D5894", "plum": "#7B4F86",
    "fol_d": "#6E9C58", "fol_m": "#4FA05A", "fol_l": "#7DBB55",
    "wood_d": "#553828", "wood_m": "#8B5D3F", "wood_l": "#A9774F",
    "stone": "#9C9CAB", "white": "#F1EEE6", "rope": "#C9B48A",
    # layout wall/roof names that are not plain palette entries
    "rust": "#9A5638", "dwoodl": "#6B4A36", "lwoodw": "#B58A60", "stonew": "#A9A7AE",
}

ROLES = {
    # structure
    "wall": "cream", "wall_bare": "#B79872", "wall_in": "#E4D3B0", "trim": "blue", "frame": "white",
    "wood_dark": "wood_d", "wood_mid": "wood_m", "wood_light": "wood_l", "wood_grey": "#8E8478",
    "stone": "stone", "stone_b": "#8A8A99", "stone_light": "#BDBBC2", "plaster_in": "#E4D3B0",
    "plaster_main": "cream", "plaster_accent": "white",
    # roofs
    "tin": "red", "tin_rust": "rust", "tin_patch": "#B9BDC2", "tin_bare": "#A7ADB3", "tin_bare_rust": "#8C6B55",
    "tile_a": "#C8603F", "tile_b": "#B5503A", "tile_c": "#D9804F", "tile_ridge": "#A84F38",
    # metal / glass / light
    "iron": "#3B3A3F", "iron_lit": "#4A4743", "metal_dark": "#3B3A3F", "brass": "#C9A14A",
    "glass": "#9CC7DA", "glass_mirror": "#C9DDE4", "glass_jar": "#A9D0C4", "enamel": "#EDEAE0",
    "emit_fire": "#FF8A2B", "emit_lamp": "#FFD27A",
    # cloth, props
    "fabric_a": "coral", "fabric_b": "turq", "fabric_white": "#F3EFE4", "fabric_awning": "coral",
    "rope": "rope", "net": "#B9A77E", "float_a": "red", "float_b": "ochre", "crate": "#B08A5A",
    "clay": "#C0714A", "paper": "#F0E8D2", "slate": "#3E4A46", "ice": "#DCEEF5", "bread": "#D9A45B",
    "fish_a": "#8FA9B8", "fish_b": "#C98F7A", "soil": "#5B4030", "water_still": "#6FAED6",
    # nature
    "foliage_a": "fol_m", "foliage_b": "fol_d", "foliage_c": "fol_l", "trunk": "#7A5A40",
    "flower_a": "coral", "flower_b": "ochre", "flower_c": "plum",
    "rock_l": "#D9A96C", "rock_m": "#C07F45", "rock_d": "#8E5230", "rock_wet": "#7A4B2E", "rock_cave": "#5A3522",
    "ground": "#DCC79E", "path": "#EFE3C4", "grass": "#8FB56A", "sand": "#E6D3A0", "seabed": "#5E8FA8",
    "sea": "sea_m", "foam": "#EAF4F8",
    "boat_hull": "#EFE6D2", "boat_a": "red", "boat_b": "blue", "boat_c": "turq", "boat_d": "ochre", "sail": "#EFE6CF",
    "skin": "#D9A27C", "debug": "#FF00FF",
}

# which Blender / glTF material a role is drawn with
def material_of(role):
    if role.startswith("emit_"): return "LT_emit_" + role[5:]
    if role == "glass": return "LT_glass"
    if role.startswith("tin") or role in ("iron", "iron_lit", "metal_dark", "brass", "glass_mirror"): return "LT_metal"
    if role in ("sea",): return "LT_water"
    return "LT_matte"


def hex_to_srgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def srgb_to_linear(c):
    return tuple(((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in c)


def resolve(role, overrides=None):
    """role -> sRGB tuple."""
    v = (overrides or {}).get(role, ROLES.get(role))
    if v is None:
        base = role.split("_")[0]
        v = (overrides or {}).get(base, ROLES.get(base, "#FF00FF"))
    seen = 0
    while not v.startswith("#") and seen < 4:
        v = BIBLE.get(v) or ROLES.get(v) or "#FF00FF"; seen += 1
    return hex_to_srgb(v)


def building_overrides(b):
    """Per-building colour roles from the layout's wall / roof names."""
    wall, roof = b["wall"], b["roof"]
    trim = roof if roof not in ("cream",) else "deep"
    o = {"wall": wall, "tin": roof, "trim": trim, "fabric_awning": roof, "fabric_a": roof,
         "frame": "white" if wall not in ("white", "cream") else "wood_l"}
    if wall in ("dwoodl", "lwoodw"):
        o["frame"] = "wood_d"
    return o
