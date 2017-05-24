/*

shader.h

Header file for shader.cpp, defines helper methods to create an
OpenGL(ES) program object with compiled vertex and fragment shaders.

*/

#ifndef SHADER_H
#define SHADER_H 1

#include <stdio.h>
#include <string>
#include <vector>
#include <iostream>
#include <fstream>
#include <algorithm>

#include <stdlib.h>
#include <string.h>

#include "helpers.h"
#include "glinit.h"

bool loadShaders(const char * vertex_shader, const char * fragment_shader, GLuint * program_id, GLuint * vertex_shader_id, GLuint * fragment_shader_id);
void unloadShaders(GLuint program_id, GLuint vertex_shader_id, GLuint fragment_shader_id);

#endif // !SHADER_H


