/*
shaders.h

Contains all vertex and fragment shaders to be compiled in OpenGL(ES)
*/

#ifndef SHADERS_H
#define SHADERS_H 1

// A very simple vertex shader,
// transforms a given vertex vertexPosition_modelspace using 
// Model-View-Projection matrix MVP
// Compatible with both OpenGL and OpenGL ES
static const char * line_vertexshader = R"(
#ifndef GL_ES
#version 330

layout(location = 0) in vec4 vertexPosition_modelspace;
uniform mat4 MVP; 

void main()
{
    gl_Position = MVP * vertexPosition_modelspace;
}

#else
precision mediump float;

attribute vec4 vertexPosition_modelspace;
uniform mat4 MVP; 

void main()
{
    gl_Position = MVP * vertexPosition_modelspace;
}
#endif
 )";

// An even simpler fragment shader
// Colors anything in a solid ds_Color
// Compatible with both OpenGL and OpenGL ES
static const char * line_fragmentshader = R"(
#ifndef GL_ES
#version 330

out vec4 color;
uniform vec4 ds_Color;

void main()
{
	color = ds_Color;
}
#else
precision mediump float;

uniform vec4 ds_Color;

void main()
{
	gl_FragColor = ds_Color;
}
#endif
)";


// A vertex shader that transforms a given vertex vertexPosition_modelspace using 
// Model-View-Projection matrix MVP
// Provides helpers for the fragment shader to calculate the light amount and direction
static const char * tube_vertexshader = R"(
#ifndef GL_ES
#version 330
#endif

// Input vertex data, different for all executions of this shader.
layout(location = 0) in vec4 vertexPosition_modelspace;
//layout(location = 1) in vec2 vertexUV; // We don't need textures
layout(location = 2) in vec3 vertexNormal_modelspace;

// Output data ; will be interpolated for each fragment.
out vec2 UV;
out vec3 Position_worldspace;
out vec3 Normal_cameraspace;
out vec3 EyeDirection_cameraspace;
out vec3 LightDirection_cameraspace;

// Values that stay constant for the whole mesh.
uniform mat4 MVP;
uniform mat4 V;
uniform mat4 M;
uniform vec3 LightPosition_worldspace;

void main(){

	// Output position of the vertex, in clip space : MVP * position
	gl_Position =  MVP * vertexPosition_modelspace;
	
	// Position of the vertex, in worldspace : M * position
	Position_worldspace = (M * vertexPosition_modelspace).xyz;
	
	// Vector that goes from the vertex to the camera, in camera space.
	// In camera space, the camera is at the origin (0,0,0).
	vec3 vertexPosition_cameraspace = ( V * M * vertexPosition_modelspace).xyz;
	EyeDirection_cameraspace = vec3(0,0,0) - vertexPosition_cameraspace;

	// Vector that goes from the vertex to the light, in camera space. M is ommited because it's identity.
	vec3 LightPosition_cameraspace = ( V * vec4(LightPosition_worldspace,1)).xyz;
	LightDirection_cameraspace = LightPosition_cameraspace + EyeDirection_cameraspace;
	
	// Normal of the the vertex, in camera space
	Normal_cameraspace = ( V * M * vec4(vertexNormal_modelspace,0)).xyz; // Only correct if ModelMatrix does not scale the model ! Use its inverse transpose if not.
	
	// UV of the vertex. No special space for this one.
	//UV = vertexUV;
}
)";

// A fragment shader that uses ds_Color as material diffuse color
// and applies ambient lighting and a specular effect based on
// a vertex' normals and a light position, both provided by the vertex shader
static const char * tube_fragmentshader = R"(
#ifndef GL_ES
#version 330
#endif

// Interpolated values from the vertex shaders
//in vec2 UV;

in vec3 Position_worldspace;
in vec3 Normal_cameraspace;
in vec3 EyeDirection_cameraspace;
in vec3 LightDirection_cameraspace;

// Ouput data
out vec4 color;

// Values that stay constant for the whole mesh.
uniform vec4 ds_Color;
uniform vec3 LightPosition_worldspace;

void main(){

	// Light emission properties
	// You probably want to put them as uniforms
	vec3 LightColor = vec3(1,1,1);
	float LightPower = 200000.0f;
	
	// Material properties
	vec3 MaterialDiffuseColor = ds_Color.xyz;
	vec3 MaterialAmbientColor = vec3(0.1,0.1,0.1) * MaterialDiffuseColor;
	vec3 MaterialSpecularColor = vec3(0.3,0.3,0.3);

	// Distance to the light
	float distance = length( LightPosition_worldspace - Position_worldspace );

	// Normal of the computed fragment, in camera space
	vec3 n = normalize( Normal_cameraspace );
	// Direction of the light (from the fragment to the light)
	vec3 l = normalize( LightDirection_cameraspace );
	// Cosine of the angle between the normal and the light direction, 
	// clamped above 0
	//  - light is at the vertical of the triangle -> 1
	//  - light is perpendicular to the triangle -> 0
	//  - light is behind the triangle -> 0
	float cosTheta = clamp( dot( n,l ), 0,1 );
	
	// Eye vector (towards the camera)
	vec3 E = normalize(EyeDirection_cameraspace);
	// Direction in which the triangle reflects the light
	vec3 R = reflect(-l,n);
	// Cosine of the angle between the Eye vector and the Reflect vector,
	// clamped to 0
	//  - Looking into the reflection -> 1
	//  - Looking elsewhere -> < 1
	float cosAlpha = clamp( dot( E,R ), 0,1 );
	
	color = vec4(
		// Ambient : simulates indirect lighting
		MaterialAmbientColor +
		// Diffuse : "color" of the object
		MaterialDiffuseColor * LightColor * LightPower * cosTheta / (distance*distance) +
		// Specular : reflective highlight, like a mirror
		MaterialSpecularColor * LightColor * LightPower * pow(cosAlpha,5) / (distance*distance)
		, 1.0);
}
)";
#endif /* SHADERS_H */
