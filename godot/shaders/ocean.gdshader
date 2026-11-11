shader_type spatial;
render_mode cull_disabled, specular_schlick_ggx;
// Calm faceted "paper-cut" sea (ART_BIBLE): animated facets, depth tint,
// soft foam where the water meets rock, piles and hulls.

uniform vec3 shallow : source_color = vec3(0.475, 0.745, 0.925);
uniform vec3 mid : source_color = vec3(0.298, 0.592, 0.839);
uniform vec3 deep : source_color = vec3(0.227, 0.471, 0.761);
uniform vec3 foam : source_color = vec3(0.92, 0.96, 0.98);
uniform float wave_height = 0.11;
uniform float wave_scale = 0.22;
uniform float wave_speed = 0.55;
uniform float sim_time = 0.0;      // wave clock shared with scripts/sim/ocean.gd
uniform float tide = 0.0;
uniform float foam_width = 0.6;
uniform float storm = 0.0;        // 0 clear .. 1 overcast: greys the water
uniform sampler2D height_tex : filter_linear, repeat_disable;   // terrain height, baked by the Blender pipeline
uniform vec4 height_rect = vec4(-53.0, -41.0, 51.0, 37.0);      // x0, z0, x1, z1 covered by height_tex
uniform vec2 height_range = vec2(-3.0, 1.0);

varying vec3 wpos;

float h(vec2 p, float t) {
	return sin(p.x * wave_scale + t) * 0.5 + sin(p.y * wave_scale * 1.3 - t * 0.8) * 0.35
		+ sin((p.x + p.y) * wave_scale * 2.1 + t * 1.7) * 0.15;
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	// jitter the grid so facets are irregular triangles, not squares
	vec2 j = vec2(sin(wpos.z * 1.7 + wpos.x * 0.3), cos(wpos.x * 1.3 - wpos.z * 0.2)) * 0.8;
	// height from the un-jittered position: identical to Ocean.wave() in GDScript
	VERTEX.y += h(wpos.xz, sim_time * wave_speed) * wave_height + tide;
	VERTEX.xz += j;
	wpos.xz += j;
}

void fragment() {
	// flat facets from screen-space derivatives
	vec3 n = normalize(cross(dFdy(VERTEX), dFdx(VERTEX)));
	NORMAL = n;
	vec2 huv = (wpos.xz - height_rect.xy) / (height_rect.zw - height_rect.xy);
	float ground = mix(height_range.x, height_range.y, texture(height_tex, huv).r);
	if (huv.x < 0.0 || huv.x > 1.0 || huv.y < 0.0 || huv.y > 1.0) {
		ground = height_range.x;
	}
	float water_depth = max(0.0, tide - ground);
	float k = smoothstep(0.0, 2.6, water_depth);
	vec3 col = mix(shallow, mid, smoothstep(0.0, 0.5, k));
	col = mix(col, deep, smoothstep(0.4, 1.0, k));
	float facet = dot(n, normalize(vec3(0.3, 1.0, 0.2)));
	col *= 0.86 + 0.22 * facet;
	float f = 1.0 - smoothstep(0.0, foam_width, water_depth + sin(TIME * 1.3 + wpos.x * 0.9 + wpos.z * 0.7) * 0.15);
	col = mix(col, foam, f * 0.85);
	col = mix(col, vec3(dot(col, vec3(0.33))) * vec3(0.8, 0.9, 1.0), storm * 0.55);
	ALBEDO = col;
	ROUGHNESS = 0.18;
	SPECULAR = 0.45;
	ALPHA = mix(0.78, 0.97, k);
}
