#pragma once

#include <stdio.h>
#include <GLFW/glfw3.h>

#include "RenderContextBase.h"

class RenderContextGLFW: public RenderContextBase
{
	GLFWwindow* window;
	void error_callback(int error, const char* description);
public:
	RenderContextGLFW(int width, int height) : RenderContextBase(width, height) {};
	bool activate();
	~RenderContextGLFW();	
};

