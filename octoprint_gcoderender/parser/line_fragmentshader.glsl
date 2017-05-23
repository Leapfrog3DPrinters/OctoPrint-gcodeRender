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
