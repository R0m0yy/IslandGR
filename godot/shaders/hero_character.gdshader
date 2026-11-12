shader_type spatial;
// Hero villagers: vertex-colour albedo with a gentle tone lift. The characters are
// authored and approved in Blender under the AgX view transform, which opens up
// dark tones (deep skin, navy cloth); Godot's tonemapper keeps them much darker.
// A power curve on the albedo (exponent < 1) lifts dark colours far more than light
// ones, so skin and fabric read as they do in the approved renders.
uniform float lift : hint_range(0.5, 1.0) = 0.66;
uniform float soften : hint_range(0.0, 0.5) = 0.14;   // AgX-like desaturation of strong colours
uniform float roughness_v : hint_range(0.0, 1.0) = 0.78;
uniform float metallic_v : hint_range(0.0, 1.0) = 0.0;
uniform float rim_v : hint_range(0.0, 1.0) = 0.3;

void fragment() {
	vec3 c = pow(max(COLOR.rgb, vec3(0.0)), vec3(lift));
	float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
	ALBEDO = mix(c, vec3(l), soften);
	ROUGHNESS = roughness_v;
	METALLIC = metallic_v;
	RIM = rim_v;
	RIM_TINT = 0.5;
}
