/*

RenderContextEGL.h

Class definition for EGL render context. On supported platforms
this context has preference over GLFW as it supports PBuffers 
and is lightweight (doesn't include unnecessary user-interaction methods)

*/

#ifndef RENDERCONTEXTEGL_H
#define RENDERCONTEXTEGL_H 1

#ifdef __linux__
#include <EGL/egl.h>
#include "RenderContextBase.h"

class RenderContextEGL : public RenderContextBase
{
	EGLDisplay display;

public:
	RenderContextEGL(int width, int height) : RenderContextBase(width, height) {};
	bool activate();
	~RenderContextEGL();
};

#endif

#endif // !RENDERCONTEXTEGL_H
