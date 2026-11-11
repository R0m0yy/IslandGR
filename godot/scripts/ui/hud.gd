extends CanvasLayer
## Minimal debug HUD: clock, speed control, and what every villager is doing.

var village = null
var label: Label
var help: Label
var _t := 0.0

func _ready() -> void:
	label = Label.new()
	label.position = Vector2(14, 10)
	label.add_theme_font_size_override("font_size", 14)
	label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
	label.add_theme_constant_override("outline_size", 4)
	add_child(label)
	help = Label.new()
	help.text = "RMB orbit · wheel zoom · WASD pan · Tab follow villager · C cutaway · 1/2/3/4 speed x1 x4 x16 x60 · Space pause"
	help.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	help.position += Vector2(14, -30)
	help.add_theme_font_size_override("font_size", 13)
	help.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
	help.add_theme_constant_override("outline_size", 4)
	add_child(help)

func _unhandled_input(ev: InputEvent) -> void:
	if ev is InputEventKey and ev.pressed and not ev.echo and village:
		match ev.keycode:
			KEY_1: village.sim.time_scale = 1.0
			KEY_2: village.sim.time_scale = 4.0
			KEY_3: village.sim.time_scale = 16.0
			KEY_4: village.sim.time_scale = 60.0
			KEY_SPACE: village.sim.auto = not village.sim.auto

func _process(dt: float) -> void:
	_t -= dt
	if _t > 0.0 or village == null:
		return
	_t = 0.25
	var lines := ["%s   speed x%d%s   villagers %d" % [GameClock.text(), int(village.sim.time_scale), "" if village.sim.auto else " (paused)", village.villagers.size()]]
	var counts := {}
	for v in village.villagers:
		counts[v.fsm.current_name] = counts.get(v.fsm.current_name, 0) + 1
	var parts := []
	for k in counts:
		parts.append("%s %d" % [k, counts[k]])
	lines.append("  ".join(parts))
	var f = village.camera_rig.follow if village.camera_rig else null
	if f and is_instance_valid(f):
		lines.append("")
		lines.append("FOLLOWING  " + f.status())
		for l in f.log.slice(-6):
			lines.append("   " + l)
	label.text = "\n".join(lines)
