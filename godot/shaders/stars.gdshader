shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, fog_disabled, blend_add;
uniform float visibility = 0.0;
void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float d = 1.0 - length(p);
	ALBEDO = vec3(0.9, 0.93, 1.0) * visibility * smoothstep(0.0, 1.0, d) * COLOR.r;
}
