#ifdef _WIN32
#include "RenderContextGLFW.h"

void RenderContextGLFW::error_callback(int error, const char* description)
{
	printf("Error: %s\n", description);
}

bool RenderContextGLFW::activate()
{
	// Initialise GLFW
	if (!glfwInit())
	{
		return false;
	}
	glfwWindowHint(GLFW_DEPTH_BITS, 8);
	glfwWindowHint(GLFW_SAMPLES, 4);
	glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
	glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
	glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, true); // To make MacOS happy; should not be needed
	glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
	glfwWindowHint(GLFW_VISIBLE, GL_FALSE);
	glfwWindowHint(GLFW_DOUBLEBUFFER, GL_FALSE);

	// Open a window and create its OpenGL context

	window = glfwCreateWindow(width, height, "Cpp gcodeRender", NULL, NULL);
	if (window == NULL) {
		glfwTerminate();
		return false;
	}
	glfwMakeContextCurrent(window);

	return true;
}

RenderContextGLFW::~RenderContextGLFW()
{
	glfwTerminate();
}
#endif
