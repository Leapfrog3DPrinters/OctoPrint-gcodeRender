/*
Helpers.h

Defines constants that are used across the rendering program
and provides helper structs and enums. Additionally provides
a helper method to log messages to Python

*/

#ifndef HELPERS_H
#define HELPERS_H 1

#define DRAW_TUBES 0 // Draw 3D tubes with n faces for every 3D printed path
#define DRAW_LINES 1 // Draw OpenGL lines without faces (far less memory required)

// A bounding box structure that defines a given volume in 3D space
struct BBox {
	float xmin, xmax, ymin, ymax, zmin, zmax;
};

// Log message types
enum LogTypes { info, warning, error, debug };

// May be used across the program to log a status message
void log_msg(int type, char *msg);
#endif
