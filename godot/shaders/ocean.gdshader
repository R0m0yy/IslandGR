shader_type spatial;
render_mode cull_disabled, specular_schlick_ggx;
// Tropical sea, opaque (cheap on phones). The wave sum is identical to
// scripts/sim/ocean.gd (boats sit on what is drawn); on top of it:
//  - a long swell, and surf that rises and rolls toward every shore over the shallows
//  - breaking foam lines that follow the surf, a shore line that moves with the tide
//  - caustics dancing over the sand in the shallows, sun glints on the facets
// Depth comes from the baked terrain height map.

uniform vec3 shallow : source_color = vec3(0.36, 0.86, 0.84);
uniform vec3 mid : source_color = vec3(0.13, 0.62, 0.80);
uniform vec3 deep : source_color = vec3(0.05, 0.27, 0.58);
uniform vec3 sand : source_color = vec3(0.93, 0.86, 0.66);
uniform vec3 foam : source_color = vec3(0.96, 0.98, 1.0);
uniform float wave_height = 0.13;
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
varying float vdepth;
varying float surf;

float h(vec2 p, float t) {
	return sin(p.x * wave_scale + t) * 0.5 + sin(p.y * wave_scale * 1.3 - t * 0.8) * 0.35
		+ sin((p.x + p.y) * wave_scale * 2.1 + t * 1.7) * 0.15
		+ sin((p.x * 0.6 - p.y * 0.8) * wave_scale * 0.35 + t * 0.45) * 0.55;
}

float ground_at(vec2 xz) {
	vec2 huv = (xz - height_rect.xy) / (height_rect.zw - height_rect.xy);
	if (huv.x < 0.0 || huv.x > 1.0 || huv.y < 0.0 || huv.y > 1.0) { return height_range.x; }
	return mix(height_range.x, height_range.y, textureLod(height_tex, huv, 0.0).r);
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec2 j = vec2(sin(wpos.z * 1.7 + wpos.x * 0.3), cos(wpos.x * 1.3 - wpos.z * 0.2)) * 0.8;
	crest = h(wpos.xz, sim_time * wave_speed);
	vdepth = max(0.0, tide - ground_at(wpos.xz + j));
	// surf: over the shallows a wave rises and travels toward the shore (depth falling)
	float sh = smoothstep(2.2, 0.35, vdepth) * smoothstep(0.0, 0.25, vdepth);
	surf = pow(max(0.0, sin(vdepth * 3.2 + sim_time * 1.25)), 4.0) * sh;
	VERTEX.y += crest * wave_height + tide + surf * (0.09 + 0.6 * wave_height);
	VERTEX.xz += j;
	wpos.xz += j;
}

void fragment() {
	vec3 n = normalize(cross(dFdy(VERTEX), dFdx(VERTEX)));
	NORMAL = n;
	float depth = vdepth;
	float k = smoothstep(0.0, 2.7, depth);
	vec3 col = mix(mix(sand, shallow, smoothstep(0.0, 0.45, depth)), mid, smoothstep(0.1, 0.6, k));
	col = mix(col, deep, smoothstep(0.55, 1.0, k));
	// caustics: two drifting interference patterns, strongest over sand in clear shallow water
	vec2 cp = wpos.xz * 1.6;
	float ca = sin(cp.x + TIME * 0.9 + sin(cp.y * 1.3 + TIME * 0.7)) * sin(cp.y * 1.1 - TIME * 0.8 + sin(cp.x * 0.9 - TIME * 0.5));
	float caustic = pow(max(0.0, ca), 3.0) * (1.0 - smoothstep(0.2, 1.6, depth)) * smoothstep(0.02, 0.15, depth);
	col += vec3(0.25, 0.3, 0.25) * caustic * light_level * (1.0 - storm);
	// each facet takes its own tone from its tilt: the paper-cut look
	vec3 nw = (INV_VIEW_MATRIX * vec4(n, 0.0)).xyz;
	col *= 0.88 + 0.24 * dot(nw, normalize(vec3(0.35, 1.0, 0.25)));
	// crests in deep water catch light through the water (lighter turquoise)
	col = mix(col, shallow * 0.9, smoothstep(0.55, 1.0, crest) * k * 0.35);
	float patch_ = sin(wpos.x * 0.07 + TIME * 0.05) * sin(wpos.z * 0.09 - TIME * 0.04);
	col *= 1.0 + 0.06 * patch_ * k;
	// foam: the swash at the water's edge, breaking surf lines, whitecaps in wind
	float t = TIME * 0.9;
	float edge = 1.0 - smoothstep(0.0, 0.38, depth + 0.1 * sin(t * 1.4 + wpos.x * 0.9 + wpos.z * 0.7));
	float lace = 0.5 + 0.5 * sin(wpos.x * 3.1 + wpos.z * 2.3 + t * 2.0) * sin(wpos.z * 2.7 - wpos.x * 1.9 - t * 1.6);
	float breaking = smoothstep(0.35, 0.9, surf) * (0.6 + 0.4 * lace);
	float cap = smoothstep(0.80, 1.0, crest) * smoothstep(0.2, 0.5, wave_height) * (0.5 + 0.5 * lace);
	col = mix(col, foam, clamp(edge * 0.95 + breaking * 0.8 + cap * 0.7, 0.0, 1.0));
	col = mix(col, vec3(dot(col, vec3(0.33))) * vec3(0.78, 0.86, 0.95), storm * 0.6);
	col *= mix(0.22, 1.0, light_level);
	col = mix(col, col * vec3(0.55, 0.65, 1.0), (1.0 - light_level) * 0.6);
	ALBEDO = col;
	// sun glints: a few facets flash as they tilt toward the sun
	float glint = pow(max(0.0, sin(dot(wpos.xz, vec2(4.1, 3.3)) + TIME * 3.0) * sin(dot(wpos.xz, vec2(-2.7, 5.2)) - TIME * 2.3)), 12.0);
	EMISSION = vec3(1.0, 0.97, 0.9) * glint * 0.6 * light_level * k * (1.0 - storm);
	ROUGHNESS = 0.1;
	SPECULAR = 0.6 * light_level + 0.2;
}
