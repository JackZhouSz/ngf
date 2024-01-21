#version 460

#extension GL_GOOGLE_include_directive: require
#extension GL_EXT_mesh_shader: require
#extension GL_EXT_debug_printf : require

#include "payload.h"

layout (binding = 0) readonly buffer Points
{
	vec3 data[];
} points;

layout (binding = 2) readonly buffer Patches
{
	ivec4 data[];
} patches;

layout (push_constant) uniform NGFPushConstants
{
	mat4 model;
	mat4 view;
	mat4 proj;

	vec2 extent;
	float time;
};

taskPayloadSharedEXT Payload payload;

// TODO: counter for number of primitives sent

vec2 project(vec3 p)
{
	vec4 pp = proj * view * model * vec4(p, 1.0f);
	pp.y = -pp.y;
	pp.z = (pp.z + pp.w) / 2.0;
	return vec2(pp);
}

float cross(vec2 a, vec2 b)
{
	return abs(a.x * b.y - b.x * a.y);
}

void main()
{
	// TODO: compute distance and set resolution
	payload.pindex = gl_GlobalInvocationID.x;

	ivec4 complex = patches.data[payload.pindex];

	vec3 v0 = points.data[complex.x];
	vec3 v1 = points.data[complex.y];
	vec3 v2 = points.data[complex.z];
	vec3 v3 = points.data[complex.w];

	vec2 p0 = project(v0) * extent;
	vec2 p1 = project(v1) * extent;
	vec2 p2 = project(v2) * extent;
	vec2 p3 = project(v3) * extent;

	float a0 = cross(p0 - p1, p0 - p2);
	float a1 = cross(p1 - p2, p1 - p3);
	float area = sqrt(a0 + a1)/16;

	payload.resolution = max(2, min(15, uint(area)));
	// payload.resolution = 15;

	debugPrintfEXT("Area %.2f  --> resolution: %d\n", area, payload.resolution);

	// TODO: group offsets
	uint groups = (payload.resolution - 1 + 6)/7;
	EmitMeshTasksEXT(groups, groups, 1);
}
