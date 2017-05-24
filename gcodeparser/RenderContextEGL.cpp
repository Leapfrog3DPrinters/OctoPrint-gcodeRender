#ifdef __linux__
#include "RenderContextEGL.h"

bool RenderContextEGL::activate()
{
	//TODO: Logging and error checking

	// Get and initialize the current display from EGL
	display = eglGetDisplay(EGL_DEFAULT_DISPLAY);

	EGLint major, minor;

	EGLBoolean r = eglInitialize(display, &major, &minor);

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

	// Set config
	EGLint numconfigs;
	EGLConfig config;

	r = eglChooseConfig(display, attribs, &config, 1, &numconfigs);

	// Bind API
	r = eglBindAPI(EGL_OPENGL_ES_API);

	// Create context
	const EGLint context_attribs[] = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };

	EGLContext context = eglCreateContext(display, config, EGL_NO_CONTEXT, context_attribs);

	EGLint surface_attribute_list[] = { EGL_WIDTH, width, EGL_HEIGHT, height, EGL_NONE };

	EGLSurface surface = eglCreatePbufferSurface(display, config, surface_attribute_list);

	r = eglMakeCurrent(display, surface, surface, context);

	// TODO: Return actual success status
	return true;
}


RenderContextEGL::~RenderContextEGL()
{
	eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
	eglTerminate(display);
}
#endif
