/* 

RenderContextGLFW.h

Class defintion for GLFW render context. A little bit bulky 
for our needs, but works on Windows.

*/


#ifndef RENDERCONTEXTGLFW_H
#define RENDERCONTEXTGLFW_H 1

//TODO: Maybe use GLFW for mac too?
#ifdef _WIN32

#include <stdio.h>
#include <GLFW/glfw3.h>

#include "RenderContextBase.h"

class RenderContextGLFW : public RenderContextBase
{
	GLFWwindow* window;
public:
	RenderContextGLFW(int width, int height) : RenderContextBase(width, height) {};
	bool activate();
	~RenderContextGLFW();
};

#endif


#endif // !RENDERCONTEXTGLFW_H
