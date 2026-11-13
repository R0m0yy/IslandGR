shader_type spatial;
// Villager characters: vertex-colour albedo with a gentle tone lift, plus per-resident
// variation chosen per mesh part by the game (VillagerAnimator.build_model):
//   tag_mode 2 clothing -> hue rotated by cloth_hue and scaled by cloth_val
//   tag_mode 1 skin     -> scaled by skin_tone
//   tag_mode 0 fixed    (hair, eyes, props, metal)
// The tone lift: the characters are authored under Blender's AgX view, which opens up
// dark tones; a power curve (exponent < 1) lifts dark colours far more than light ones.
uniform float lift : hint_range(0.5, 1.0) = 0.66;
uniform float soften : hint_range(0.0, 0.5) = 0.14;
uniform float roughness_v : hint_range(0.0, 1.0) = 0.78;
uniform float metallic_v : hint_range(0.0, 1.0) = 0.0;
uniform float rim_v : hint_range(0.0, 1.0) = 0.3;
uniform float cloth_hue = 0.0;
uniform float cloth_val = 1.0;
uniform float skin_tone = 1.0;
uniform int tag_mode = 0;

vec3 hue_rotate(vec3 c, float h) {
	// rotate around the grey axis (YIQ-style), h in turns
	float a = h * 6.2831853;
	const vec3 k = vec3(0.57735);
	float ca = cos(a);
	return c * ca + cross(k, c) * sin(a) + k * dot(k, c) * (1.0 - ca);
}

void fragment() {
	vec3 c = max(COLOR.rgb, vec3(0.0));
	if (tag_mode == 2) {
		c = clamp(hue_rotate(c, cloth_hue), 0.0, 1.0) * cloth_val;
	} else if (tag_mode == 1) {
		// darker/lighter skin; the pinkish lips and pale nails keep their relation
		c *= skin_tone;
	}
	c = pow(clamp(c, vec3(0.0), vec3(4.0)), vec3(lift));   // the hue rotation can push a channel below 0: pow(<0) is NaN on WebGL
	float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
	ALBEDO = mix(c, vec3(l), soften);
	ROUGHNESS = roughness_v;
	METALLIC = metallic_v;
	RIM = rim_v;
	RIM_TINT = 0.5;
}
