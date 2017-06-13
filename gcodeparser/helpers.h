/*
Helpers.h

Defines constants that are used across the rendering program
and provides helper structs and enums. Additionally provides
a helper method to log messages to Python

*/

#ifndef HELPERS_H
#define HELPERS_H 1

#include <stdio.h>

#define DRAW_TUBES 0 // Draw 3D tubes with n faces for every 3D printed path
#define DRAW_LINES 1 // Draw OpenGL lines without faces (far less memory required)

// A bounding box structure that defines a given volume in 3D space
struct BBox {
	float xmin, xmax, ymin, ymax, zmin, zmax;

	BBox() { }

	BBox(float xmin, float xmax, float ymin, float ymax, float zmin, float zmax)
	{
		this->xmin = xmin;
		this->xmax = xmax;
		this->ymin = ymin;
		this->ymax = ymax;
		this->zmin = zmin;
		this->zmax = zmax;
	}

	// Improve readibility of some common calculations
	float width() { return this->xmax - this->xmin; }
	float depth() { return this->ymax - this->ymin; }
	float height() { return this->zmax - this->zmin; }

	float center_x() { return (this->xmax + this->xmin) / 2; }
	float center_y() { return (this->ymax + this->zmin) / 2; }
	float center_z() { return (this->zmax + this->zmin) / 2; }
};

// Log message types
enum LogTypes { info, warning, error, debug };

// May be used across the program to log a status message
void log_msg(int type, const char *msg);

#ifdef __linux__ 
#include <unistd.h>
#else
#include <windows.h>
#endif 

// Returns a nice rgba #AABBCCDDEE color code for a float[4]
inline void getColorHash(char * out, float color[4])
{
	sprintf(out, "#%02x%02x%02x%02x", (unsigned int)color[0] * 255, (unsigned int)color[1] * 255, (unsigned int)color[2] * 255, (unsigned int)color[3] * 255);
}

#endif
