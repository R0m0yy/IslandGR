extends Node3D
## The four hero villagers on the Harbour Stair (owner's brief: "place each
## character on the Harbour Stair in the village"). Presentation only: they are
## not simulation residents and do not change the economy, schedules or saves.
##
##   A  fisher captain   walks up and down the stair, stops at the foot to haul rope
##   B  market vendor    near the foot, offers fruit to passers-by
##   C  elder            on a landing halfway up, mending his net
##   D  harbour child    runs and plays at the top, waves now and then

const STAIR := ["s1_bot", "s1_top"]

var village = null
var heroes: Dictionary = {}          # key -> HeroVillager
var _t: float = 0.0
var _a_state: String = "up"
var _a_u: float = 0.0
var _a_wait: float = 0.0

func setup(v) -> bool:
	village = v
	name = "HeroShowcase"
	var g = village.graph
	if not (g.pos.has(STAIR[0]) and g.pos.has(STAIR[1])):
		return false
	for k in ["A", "B", "C", "D"]:
		if not HeroVillager.available(k):
			continue
		var h := HeroVillager.new()
		if h.setup(k):
			add_child(h)
			heroes[k] = h
	_place()
	return not heroes.is_empty()

func stair_point(u: float) -> Vector3:
	var a: Vector3 = village.graph.pos[STAIR[0]]
	var b: Vector3 = village.graph.pos[STAIR[1]]
	return a.lerp(b, clampf(u, 0.0, 1.0))

func _side() -> Vector3:
	var a: Vector3 = village.graph.pos[STAIR[0]]
	var b: Vector3 = village.graph.pos[STAIR[1]]
	var d := (b - a); d.y = 0
	return d.normalized().cross(Vector3.UP)

func _face(h: Node3D, dir: Vector3) -> void:
	dir.y = 0
	if dir.length() > 0.01:
		h.rotation.y = atan2(-dir.x, -dir.z)

func _place() -> void:
	var a: Vector3 = village.graph.pos[STAIR[0]]
	var b: Vector3 = village.graph.pos[STAIR[1]]
	var down := (a - b); down.y = 0; down = down.normalized()
	var side := _side()
	if heroes.has("B"):
		heroes["B"].position = stair_point(0.0) + down * 1.2 + side * 0.9
		_face(heroes["B"], -side + down * 0.4)
		heroes["B"].play("hand_fruit")
	if heroes.has("C"):
		heroes["C"].position = stair_point(0.5) + side * 0.8
		_face(heroes["C"], down)
		heroes["C"].play("mend_net")
	if heroes.has("D"):
		heroes["D"].position = stair_point(1.0) + (-down) * 0.8
		_face(heroes["D"], down)
		heroes["D"].play("run_play")
	if heroes.has("A"):
		heroes["A"].position = stair_point(0.0) - side * 0.5
		_face(heroes["A"], -down)

func _process(dt: float) -> void:
	_t += dt
	if heroes.has("D"):
		# play, then wave down the stair every 8 s
		heroes["D"].play("wave" if fmod(_t, 8.0) > 6.5 else "run_play")
	if heroes.has("A"):
		_drive_captain(heroes["A"], dt)

func _drive_captain(h: HeroVillager, dt: float) -> void:
	var a: Vector3 = village.graph.pos[STAIR[0]]
	var b: Vector3 = village.graph.pos[STAIR[1]]
	var length := a.distance_to(b)
	var speed := 0.55        # m/s on the stair
	var side := -_side() * 0.5
	match _a_state:
		"up", "down":
			var dirv := 1.0 if _a_state == "up" else -1.0
			_a_u = clampf(_a_u + dirv * speed * dt / length, 0.0, 1.0)
			h.position = stair_point(_a_u) + side
			_face(h, (b - a) * dirv)
			h.play("climb_stairs" if _a_state == "up" else "walk")
			if (_a_state == "up" and _a_u >= 1.0) or (_a_state == "down" and _a_u <= 0.0):
				_a_wait = 5.0
				_a_state = "rest_top" if _a_state == "up" else "haul"
		"rest_top":
			h.play("idle")
			_a_wait -= dt
			if _a_wait <= 0.0:
				_a_state = "down"
		"haul":
			_face(h, -_side())
			h.play("haul_rope")
			_a_wait -= dt
			if _a_wait <= -3.0:
				_a_state = "up"
