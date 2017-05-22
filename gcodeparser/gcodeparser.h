#pragma once
#define _USE_MATH_DEFINES

#include <stdlib.h>
#include <iostream>
#include <fstream>
#include <stdlib.h>
#include <fstream>
#include <algorithm>
#include <math.h>
#include <string.h>

#include "constants.h"

using namespace std;

//#ifdef __GNUC__
//#define EXPORT extern "C"
//#else
//#define EXPORT extern "C"  __declspec(dllexport)
//#endif

#define eps 0.0001f
#define X 0
#define Y 1
#define Z 2
#define E 3
#define NUMCOORDS 4

#define FLY 0
#define EXTRUDE 1

#define MAX_CHARS_PER_LINE 512
#define R 1
#define NUM_VERTICES 16
#define STEP_SIZE ((float)M_PI * 2 / NUM_VERTICES)


struct BBox {
	float xmin, xmax, ymin, ymax, zmin, zmax;
};

class GcodeParser
{
	const char * file;
	ifstream fin;

	const char coords[NUMCOORDS] = { 'X', 'Y', 'Z', 'E' }; // We don't care about F

	float relative[NUMCOORDS] = {};
	float absolute[NUMCOORDS] = {};
	float offset[NUMCOORDS] = {};
	bool after_fly = true;

	const float dirA[3] = { 1, 0, 0 };
	const float dirB[3] = { 0, 1, 0 };

	bool is_relative = false;
	const char* strchr_pointer;
	int style;

	int vertex_i = 0;
	int index_i = 0;
	float * vertices;
	short * indices;

	uint8_t draw = DRAW_LINES;

	struct BBox bbox;

	bool skip = true;
	const int nincludes = 4;
	const char * includes[4] = { "CONTOUR", "LAYER_NO", "BRIM", "SKIRT" };

public:
	int number_of_lines = 0;
	GcodeParser(const char *file, uint8_t draw_type);
	~GcodeParser();
	BBox * get_bbox();
	unsigned int get_vertices(const unsigned int n_lines, int * nvertices, float * vertices, int * nindices, short * indices);
	void get_buffer_size(unsigned int * vertices_size, unsigned int * indices_size);
	
private:
	float code_value(const char * line);
	bool code_seen(char code, const char * line);
	void build_vertices_lines();
	void cross(const float v1[3], const float v2[3], float * result);
	void normalize(const float * v, float * result);
	void build_vertices_tubes();
	void parse_g1(const char * line);
	void parse_g92(const char * line);
	unsigned int file_read(istream & is, char * buff, int buff_size);
	int get_number_of_lines();
	unsigned int count_lines(const char * buff, int buff_size);
	void parse_line(const char *line);
};

