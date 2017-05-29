/*

gcodeparser.h

Header file for the gcode interpreter that builds the vertex arrays

*/

#ifndef GCODEPARSER_H
#define GCODEPARSER_H 1

#define _USE_MATH_DEFINES

#include <stdlib.h>
#include <iostream>
#include <fstream>
#include <stdlib.h>
#include <fstream>
#include <algorithm>
#include <math.h>
#include <string.h>
#include <glm/glm.hpp>

#include "helpers.h"

using namespace std;

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
#define NUM_VERTICES 16 // When drawing tubes, number of vertices per circle
#define STEP_SIZE ((float)M_PI * 2 / NUM_VERTICES) // Distance between vertices for drawing tubes

/*

GcodeParser

Interprets the coordinates in a given Gcode file and generates 
OpenGL vertex arrays. Vertices may describe either cylinders (tubes)
or lines . 

*/
class GcodeParser
{
	const char * file;			// Filename of the gcode file to parse
	ifstream fin;				// Input file stream
	const char* strchr_pointer; // Pointer to current position in gcode line

	unsigned int throttlingInterval; // Every N gcode lines sleep for a while
	unsigned int throttlingDuration; // The while to sleep (in ms)

	const char coords[NUMCOORDS] = { 'X', 'Y', 'Z', 'E' }; // We don't care about F

	// Each gcode line, these coordinates are updated to calculate the distance travelled
	float relative[NUMCOORDS] = {};
	float absolute[NUMCOORDS] = {};
	float offset[NUMCOORDS] = {};

	// When drawing tubes, we need to know whether we need to connect them (after extrude)
	// or we are starting from a new position (after fly)
	bool after_fly = true;

	// Directions to expand lines to tubes
	const float dirA[3] = { 1, 0, 0 };
	const float dirB[3] = { 0, 1, 0 };

	// Current movements are relative or absolute
	bool is_relative = false;

	// Are we curently extruding or flying
	int style;

	int vertex_i = 0;	// Index of current vertex
	int index_i = 0;	// Index of current vertex index
	float * vertices;	// Pointer to the vertex buffer
	short * indices;	// Pointer to the index buffer

	uint8_t draw = DRAW_LINES; // DRAW_LINES or DRAW_TUBES

	BBox bedBbox;		// The bounding box considered valid for printing (input)
	BBox bbox;			// The bounding box of the part (output)

	// We only parse certain segments of the gcode file
	// base on annotations within the file. 

	bool skip = false;		 // Skip parsing until we reach the next segment
	const int nincludes = 9; // Number of segment types to parse

	// The segments which should be included in the parse
	// They are defined by Simplify3D and Materialise (Creatr) 
	const char * includes[9] = { "CONTOUR", "LAYER_NO", "BRIM", "SKIRT", "layer", "skirt", "solid", "outer", "inner" };

public:
	GcodeParser(const char *file, uint8_t drawType, BBox bedBbox, const unsigned int throttlingInterval, const unsigned int throttlingDuration);
	~GcodeParser();
	bool get_bbox(BBox * bbox);
	int get_vertices(const unsigned int n_lines, int * nVertices, float * vertices, int * nIndices, short * indices);
	void get_buffer_size(unsigned int * vertices_size, unsigned int * indices_size);

private:
	bool code_seen(char code, const char * line);
	float code_value(const char * line);
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




#endif // !GCODEPARSER_H

