#pragma once

#ifdef __linux__
#include <EGL/egl.h>
#include "RenderContextBase.h"

class RenderContextEGL: public RenderContextBase
{
public:
	RenderContextEGL(int width, int height) : RenderContextBase(width, height) {};
	bool activate();
	~RenderContextEGL();
};

#endif
