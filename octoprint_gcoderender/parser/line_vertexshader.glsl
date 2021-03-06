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
