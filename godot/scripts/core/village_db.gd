extends Node
## Autoload. Read-only access to the authored data:
##   res://data/village_layout.json   (copy of /data, the single source of truth)
##   res://data/buildings/<ID>.json   (anchors + interior walk graph from Blender)
##   res://data/environment.json      (lamps, boats, landmarks)
##   res://data/dev_population.json   (PLACEHOLDER villagers)
## Layout axes are Godot axes (+x east, +y up, +z south): no conversion needed.

var layout: Dictionary = {}
var environment: Dictionary = {}
var population: Dictionary = {}
var buildings: Dictionary = {}       # id -> layout record
var sidecars: Dictionary = {}        # id -> sidecar

func _ready() -> void:
	reload()

func reload() -> void:
	layout = _read("res://data/village_layout.json")
	environment = _read("res://data/environment.json")
	population = _read("res://data/dev_population.json")
	buildings.clear()
	sidecars.clear()
	for b in layout.get("buildings", []):
		buildings[b["id"]] = b
		var sc := _read("res://data/buildings/%s.json" % b["id"])
		if not sc.is_empty():
			sidecars[b["id"]] = sc

func _read(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		push_warning("VillageDB: missing %s" % path)
		return {}
	var txt := FileAccess.get_file_as_string(path)
	var data = JSON.parse_string(txt)
	if typeof(data) != TYPE_DICTIONARY:
		push_error("VillageDB: bad JSON in %s" % path)
		return {}
	return data

static func v3(a) -> Vector3:
	return Vector3(a[0], a[1], a[2])

func node_pos(id: String) -> Vector3:
	var n = layout["nav"]["nodes"][id]
	return Vector3(n["x"], n["y"], n["z"])

func building_transform(id: String) -> Transform3D:
	var sc: Dictionary = sidecars[id]
	var basis := Basis(Vector3.UP, deg_to_rad(sc["yaw_deg"]))
	return Transform3D(basis, v3(sc["origin"]))
