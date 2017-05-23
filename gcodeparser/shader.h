#pragma once

#include <stdio.h>
#include <string>
#include <vector>
#include <iostream>
#include <fstream>
#include <algorithm>

#include <stdlib.h>
#include <string.h>

#include "glinit.h"

//GLuint LoadShaders(const char * vertex_file_path, const char * fragment_file_path);
GLuint LoadShadersFromSource(const char * vertex_shader, const char * fragment_shader, GLuint * program_id, GLuint * vertex_shader_id, GLuint * fragment_shader_id);
void UnloadShaders(GLuint program_id, GLuint vertex_shader_id, GLuint fragment_shader_id);
