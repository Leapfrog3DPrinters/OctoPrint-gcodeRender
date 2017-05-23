#pragma once
#define DRAW_TUBES 0
#define DRAW_LINES 1

struct BBox {
	float xmin, xmax, ymin, ymax, zmin, zmax;
};

enum logtypes { info, warning, error, debug };
