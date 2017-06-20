#ifdef __linux__
#include "RenderContextEGL.h"

// Create a pixel buffer and activate it
bool RenderContextEGL::activate()
{
	//TODO: Logging and error checking

	// Get and initialize the current display from EGL
	display = eglGetDisplay(EGL_DEFAULT_DISPLAY);

	if (display == EGL_NO_DISPLAY)
	{
		log_msg(error, "Could not get the default display. Is $DISPLAY set?");
		return false;
	}

	EGLint major, minor;

	EGLBoolean r = eglInitialize(display, &major, &minor);

	if (r == EGL_FALSE)
	{
		log_msg(error, "Could not initialize EGL");
		return false;
	}

	// Define surface config
	const EGLint attribs[] = { EGL_RED_SIZE, 8,
		EGL_GREEN_SIZE, 8,
		EGL_BLUE_SIZE, 8,
		EGL_ALPHA_SIZE, 8,
		EGL_DEPTH_SIZE, 8,
		EGL_COLOR_BUFFER_TYPE, EGL_RGB_BUFFER,
		EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
		EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
		EGL_CONFORMANT, EGL_OPENGL_ES2_BIT,
		EGL_NONE
	};

	// Find config that matches these parameters
	EGLint numconfigs;
	EGLConfig config;

	r = eglChooseConfig(display, attribs, &config, 1, &numconfigs);

	if (r == EGL_FALSE)
	{
		log_msg(error, "Could not find a valid EGL configuration");
		return false;
	}

	// Bind API
	r = eglBindAPI(EGL_OPENGL_ES_API);

	if(r == EGL_FALSE)
	{
		log_msg(error, "Could not bind to the OpenGL ES API");
		return false;
	}

	// Create context
	const EGLint context_attribs[] = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };
	EGLContext context = eglCreateContext(display, config, EGL_NO_CONTEXT, context_attribs);

	if(context == EGL_NO_CONTEXT)
	{
		log_msg(error, "Could not create a EGL context");
		return false;
	}

	EGLint surface_attribute_list[] = { EGL_WIDTH, width, EGL_HEIGHT, height, EGL_NONE };
	EGLSurface surface = eglCreatePbufferSurface(display, config, surface_attribute_list);

	if (context == EGL_NO_SURFACE)
	{
		log_msg(error, "Could not create a EGL surface");
		return false;
	}

	r = eglMakeCurrent(display, surface, surface, context);

	if (r == EGL_FALSE)
	{
		log_msg(error, "Could not activate the current EGL context");
		return false;
	}

	return true;
}


RenderContextEGL::~RenderContextEGL()
{
	eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
	eglTerminate(display);
}
#endif
