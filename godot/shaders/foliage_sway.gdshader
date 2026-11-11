shader_type spatial;
render_mode cull_disabled;
// Vertex-colour foliage that moves in the wind. Trunks (brown) stay still:
// only vertices whose colour is green-dominant sway.
uniform float wind = 0.3;
varying float leaf;

void vertex() {
	leaf = step(COLOR.r * 1.12, COLOR.g);
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float s = sin(TIME * 1.6 + w.x * 0.55 + w.z * 0.35) + 0.5 * sin(TIME * 3.1 + w.z * 1.3);
	VERTEX.x += s * 0.045 * wind * leaf;
	VERTEX.z += cos(TIME * 1.3 + w.x * 0.4) * 0.03 * wind * leaf;
}

void fragment() {
	ALBEDO = COLOR.rgb;
	ROUGHNESS = 0.9;
}
