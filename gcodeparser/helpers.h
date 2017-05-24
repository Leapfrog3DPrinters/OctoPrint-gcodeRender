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
void log_msg(int type, char *msg);
#endif

#ifdef LINUX 
int Sleep(int sleepMs) { return usleep(sleepMs * 1000); } 
#endif 
