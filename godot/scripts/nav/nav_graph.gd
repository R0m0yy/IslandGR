class_name NavGraph
extends RefCounted
## Typed walk graph + A*. Nodes are string ids with world positions; every
## link carries a type that the villager turns into a locomotion state:
##   walk | door | ramp | archwalk | interior  -> walking
##   stair                                     -> climbing stairs
##   ladder                                    -> climbing a ladder
##   bridge                                    -> careful walk
##   doorway                                   -> open the door, then walk
## `board` links (onto boats) are loaded but not walkable yet.

const WALKABLE := ["walk", "door", "ramp", "archwalk", "interior", "stair", "ladder", "bridge", "doorway"]
const COST := {"stair": 1.9, "ladder": 3.0, "bridge": 1.4, "doorway": 1.5}

var pos: Dictionary = {}          # id -> Vector3
var adj: Dictionary = {}          # id -> Array[{to, type, len, ref}]
var meta: Dictionary = {}         # id -> Dictionary

func add_node(id: String, p: Vector3, m: Dictionary = {}) -> void:
	pos[id] = p
	if not adj.has(id):
		adj[id] = []
	meta[id] = m

func add_edge(a: String, b: String, type: String, ref = null) -> void:
	if not (pos.has(a) and pos.has(b)):
		push_error("NavGraph: edge with unknown node %s - %s" % [a, b])
		return
	var d: float = pos[a].distance_to(pos[b])
	adj[a].append({"to": b, "type": type, "len": d, "ref": ref})
	adj[b].append({"to": a, "type": type, "len": d, "ref": ref})

func edge(a: String, b: String) -> Dictionary:
	for e in adj.get(a, []):
		if e["to"] == b:
			return e
	return {}

func find_path(from: String, to: String) -> Array:
	## A*. Returns [ids...] including both ends, or [] when unreachable.
	if not (pos.has(from) and pos.has(to)):
		return []
	if from == to:
		return [from]
	var open := {from: true}
	var came := {}
	var g := {from: 0.0}
	var f := {from: pos[from].distance_to(pos[to])}
	while not open.is_empty():
		var cur := ""
		var best := INF
		for k in open:
			if f[k] < best:
				best = f[k]
				cur = k
		if cur == to:
			var out := [cur]
			while came.has(cur):
				cur = came[cur]
				out.push_front(cur)
			return out
		open.erase(cur)
		for e in adj[cur]:
			if not WALKABLE.has(e["type"]):
				continue
			var ng: float = g[cur] + e["len"] * COST.get(e["type"], 1.0)
			if ng < g.get(e["to"], INF):
				came[e["to"]] = cur
				g[e["to"]] = ng
				f[e["to"]] = ng + pos[e["to"]].distance_to(pos[to])
				open[e["to"]] = true
	return []

func path_length(path: Array) -> float:
	var d := 0.0
	for i in range(path.size() - 1):
		d += pos[path[i]].distance_to(pos[path[i + 1]])
	return d

func nearest(p: Vector3, filter: Callable = Callable()) -> String:
	var best := ""
	var bd := INF
	for id in pos:
		if filter.is_valid() and not filter.call(id):
			continue
		var d: float = pos[id].distance_squared_to(p)
		if d < bd:
			bd = d
			best = id
	return best
