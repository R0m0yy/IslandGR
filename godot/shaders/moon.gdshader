shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, fog_disabled;
// Moon disc with its phase: `phase` 0 new .. 0.5 full .. 1 new.
uniform float phase = 0.5;
uniform float brightness = 1.0;

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float r = length(p);
	if (r > 1.0) { discard; }
	float z = sqrt(1.0 - r * r);
	float a = phase * 6.2831853;
	vec3 sun_dir = vec3(sin(a), 0.0, -cos(a));          // light swings round the disc over the month
	float lit = step(0.0, dot(vec3(p.x, p.y, z), sun_dir));
	float crater = 0.88 + 0.12 * sin(p.x * 9.0 + 1.3) * sin(p.y * 7.0 - 0.4);
	vec3 col = mix(vec3(0.05, 0.06, 0.09), vec3(0.95, 0.95, 0.88) * crater, lit);
	ALBEDO = col * brightness;
	ALPHA = mix(0.15, 1.0, lit) * smoothstep(1.0, 0.94, r);
}
