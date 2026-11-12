shader_type spatial;
render_mode cull_disabled;
// Wildlife: vertex colours (with the same tone lift as the villagers) and motion done
// in the vertex shader, so one static model per species animates for free.
// Models face +X, up +Y, wings / fins span +-Z (blender/livingtides/animals.py).
//   mode 0 still, 1 wing beat, 2 fish swim, 3 dolphin swim, 4 turtle stroke, 5 crab legs
uniform int mode = 0;
uniform float rate = 1.0;          // cycles per second
uniform float amp = 0.3;
uniform float body = 0.05;         // half-width of the body (wings start outside it)
uniform float lift : hint_range(0.5, 1.0) = 0.7;

void vertex() {
	float ph = dot(NODE_POSITION_WORLD, vec3(1.7, 0.0, 2.3));       // each animal out of step with the others
	float t = TIME * rate * 6.2831853 + ph;
	vec3 v = VERTEX;
	if (mode == 1) {
		float span = max(0.0, abs(v.z) - body);
		v.y += sin(t) * amp * span * (1.0 + span * 1.5);
		v.z *= 1.0 - 0.06 * max(0.0, sin(t)) * span;
	} else if (mode == 2) {
		float tail = clamp(-v.x * 4.0 + 0.3, 0.0, 2.0);
		v.z += sin(t - v.x * 9.0) * amp * tail * 0.08;
	} else if (mode == 3) {
		float tail = clamp(-v.x * 0.9 + 0.2, 0.0, 1.6);
		v.y += sin(t - v.x * 2.5) * amp * tail * 0.12;
	} else if (mode == 4) {
		float fl = smoothstep(0.35, 0.6, abs(v.z));
		v.y += sin(t + sign(v.x) * 1.2) * amp * fl * 0.2;
	} else if (mode == 5) {
		float leg = smoothstep(0.03, 0.06, abs(v.z)) * step(v.y, 0.03);
		v.x += sin(t * 3.0 + v.x * 60.0) * amp * leg * 0.01;
	}
	VERTEX = v;
}

void fragment() {
	vec3 c = pow(max(COLOR.rgb, vec3(0.0)), vec3(lift));
	ALBEDO = c;
	ROUGHNESS = 0.6;
}
