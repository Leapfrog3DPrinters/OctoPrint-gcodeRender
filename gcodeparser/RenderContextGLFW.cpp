#ifdef _WIN32
#include "RenderContextGLFW.h"

// Opens a hidden window and activates the drawing context
bool RenderContextGLFW::activate()
{
	//TODO: Logging and error checking

	// Initialise GLFW
	if (!glfwInit())
	{
		log_msg(error, "Could not initialize GLFW");
		return false;
	}

	// This allows us to draw the bed and part in any given order
	glfwWindowHint(GLFW_DEPTH_BITS, 8);

	// Multi-sampling gives us nice anti-aliased lines
	glfwWindowHint(GLFW_SAMPLES, 4);

	// OpenGL version
	glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
	glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
	glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, true); // To make MacOS happy; should not be needed

	// Use the core of OpenGL (don't rely on extensions)
	glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

	// Hide the window
	glfwWindowHint(GLFW_VISIBLE, GL_FALSE);
	
	// We only make a picture, not an animation, so no need for double buffering
	glfwWindowHint(GLFW_DOUBLEBUFFER, GL_FALSE);

	// Open the (hidden) window
	window = glfwCreateWindow(width, height, "Cpp gcodeRender", NULL, NULL);
	if (window == NULL) {
		log_msg(error, "Could not create a window using GLFW");
		glfwTerminate();
		return false;
	}

	// Make the context current, so we can draw to it
	glfwMakeContextCurrent(window);

	return true;
}

RenderContextGLFW::~RenderContextGLFW()
{
	glfwTerminate();
}
#endif
