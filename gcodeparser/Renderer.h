#pragma once
#define _CRT_SECURE_NO_WARNINGS
#define _USE_MATH_DEFINES
#define PNG_SKIP_SETJMP_CHECK

// Python
#include <Python.h>

// Include standard headers
#include <stdio.h>
#include <stdlib.h>
#include <algorithm>
#include <math.h>

// Include libpng
#include <png.h>

#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>

#include "constants.h"
#include "glinit.h"
#include "shader.h"
#include "shaders.h"
#include "gcodeparser.h"

struct buffer_info {
	GLuint index_buffer, vertex_buffer;
	int nindices, nvertices;
};

class Renderer
{
	int width = 250; 
	int height = 250;

	RenderContextBase* renderContext;
	GcodeParser* parser;

	uint8_t draw_type = DRAW_LINES;
	uint16_t lines_per_run = 10000; // Number of lines to parse before rendering
	std::vector<buffer_info> buffers;
	buffer_info bed_buffer;
	int buffer_i = 0;
	long memory_used = 0;

	float * vertices;
	short * indices;

	float bed_width = 365.0f;
	float bed_depth = 350.0f;
	float bed_height = 200.0f;

	glm::vec2 bed_origin_offset = { 37.0f, 33.0f };
	float sync_offset = (bed_width - 35) / 2.f;
	float part_color[4] = { 67.f / 255.f, 74.f / 255.f, 84.f / 255.f, 1.0f };
	float bed_color[4] = { 0.75f, 0.75f, 0.75f, 1.0f };
	float background_color[4] = { 1, 1, 1, 1 };
	glm::vec3 camera_distance = { -300.f, -300.f, 75.f };
	glm::vec3 camera_position = { 0, -80.0, 100.0 };

	GLuint program, vertex_shader, fragment_shader, vertex_array;
	GLint position_handle, normal_handle, color_handle, m_handle, v_handle, light_handle, camera_handle;

	public:
		Renderer(int width, int height);
		~Renderer();
		void initialize();
		void renderGcode(const char* gcodeFile, const char* imageFile);

	private:
		void assert_error(const char* part);
		void draw(const float color[4], GLuint ivbo, GLuint vbo, int n, GLenum element_type);
		void buffer(const int nvertices, const float * vertices, const int nindices, const short * indices, GLuint * vbo, GLuint * ivbo);
		void deleteBuffer(GLuint ivbo, GLuint vbo);
		void createProgram();
		void setCamera();
		void bufferBed();
		void renderBed();
		void renderPart();
		void saveRender(const char* imageFile);
};

static Renderer * renderer;

static PyObject *pyLogger;

static PyObject * initialize_renderer(PyObject *self, PyObject *args, PyObject *kwargs, char *keywords[]);
static PyObject * render_gcode(PyObject *self, PyObject *args, PyObject *kwargs, char *keywords[]);
extern "C" void initgcodeparser(void);
static void log_msg(int type, char *msg);
