shader_type spatial;
render_mode cull_disabled, specular_schlick_ggx;
// Faceted tropical sea. Opaque (cheap on phones, nothing to sort against boats):
// depth comes from the baked terrain map, so shallows glow turquoise over sand,
// foam breathes in and out along every shore, and facets catch the sun.

uniform vec3 shallow : source_color = vec3(0.36, 0.86, 0.84);
uniform vec3 mid : source_color = vec3(0.13, 0.62, 0.80);
uniform vec3 deep : source_color = vec3(0.06, 0.30, 0.62);
uniform vec3 sand : source_color = vec3(0.93, 0.86, 0.66);
uniform vec3 foam : source_color = vec3(0.96, 0.98, 1.0);
uniform float wave_height = 0.11;
uniform float wave_scale = 0.22;
uniform float wave_speed = 0.55;
uniform float sim_time = 0.0;      // wave clock shared with scripts/sim/ocean.gd
uniform float tide = 0.0;
uniform float storm = 0.0;
uniform float light_level = 1.0;
uniform sampler2D height_tex : filter_linear, repeat_disable;
uniform vec4 height_rect = vec4(-53.0, -41.0, 51.0, 37.0);
uniform vec2 height_range = vec2(-3.0, 1.0);

varying vec3 wpos;
varying float crest;

float h(vec2 p, float t) {
	return sin(p.x * wave_scale + t) * 0.5 + sin(p.y * wave_scale * 1.3 - t * 0.8) * 0.35
		+ sin((p.x + p.y) * wave_scale * 2.1 + t * 1.7) * 0.15;
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec2 j = vec2(sin(wpos.z * 1.7 + wpos.x * 0.3), cos(wpos.x * 1.3 - wpos.z * 0.2)) * 0.8;
	crest = h(wpos.xz, sim_time * wave_speed);
	VERTEX.y += crest * wave_height + tide;      // identical to Ocean.wave() in GDScript
	VERTEX.xz += j;
	wpos.xz += j;
}

void fragment() {
	vec3 n = normalize(cross(dFdy(VERTEX), dFdx(VERTEX)));
	NORMAL = n;
	vec2 huv = (wpos.xz - height_rect.xy) / (height_rect.zw - height_rect.xy);
	float ground = mix(height_range.x, height_range.y, texture(height_tex, huv).r);
	if (huv.x < 0.0 || huv.x > 1.0 || huv.y < 0.0 || huv.y > 1.0) { ground = height_range.x; }
	float depth = max(0.0, tide - ground);
	float k = smoothstep(0.0, 2.7, depth);
	// sand shows through the first hand of water, then turquoise, then deep blue
	vec3 col = mix(mix(sand, shallow, smoothstep(0.0, 0.45, depth)), mid, smoothstep(0.1, 0.6, k));
	col = mix(col, deep, smoothstep(0.55, 1.0, k));
	// each facet takes its own tone from its tilt: the paper-cut look
	vec3 nw = (INV_VIEW_MATRIX * vec4(n, 0.0)).xyz;
	col *= 0.90 + 0.22 * dot(nw, normalize(vec3(0.35, 1.0, 0.25)));
	// slow light patches drifting over open water
	float patch_ = sin(wpos.x * 0.07 + TIME * 0.05) * sin(wpos.z * 0.09 - TIME * 0.04);
	col *= 1.0 + 0.06 * patch_ * k;
	// foam: a line that hugs the shore plus two bands that roll in behind it
	float t = TIME * 0.9;
	float edge = 1.0 - smoothstep(0.0, 0.42, depth + 0.12 * sin(t * 1.4 + wpos.x * 0.9 + wpos.z * 0.7));
	float band = smoothstep(0.86, 1.0, sin(depth * 5.2 - t * 1.5 + 0.6 * sin(wpos.x * 0.5 + wpos.z * 0.4))) * (1.0 - smoothstep(0.25, 1.5, depth));
	float cap = smoothstep(0.80, 1.0, crest) * smoothstep(0.2, 0.5, wave_height) * 0.7;      // whitecaps when the wind is up
	col = mix(col, foam, clamp(edge * 0.95 + band * 0.55 + cap, 0.0, 1.0));
	col = mix(col, vec3(dot(col, vec3(0.33))) * vec3(0.78, 0.86, 0.95), storm * 0.6);
	col *= mix(0.22, 1.0, light_level);
	col = mix(col, col * vec3(0.55, 0.65, 1.0), (1.0 - light_level) * 0.6);
	ALBEDO = col;
	ROUGHNESS = 0.12;
	SPECULAR = 0.55 * light_level + 0.2;
}
