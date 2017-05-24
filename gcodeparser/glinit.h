/*

glinit.h

Initializes platform-specific GL libraries and defines the 
platform dependent rendering context type.

*/

#ifndef GLINIT_H
#define GLINIT_H 1

// Required to use the ES2 functions such as glGenBuffers
#define GL_GLEXT_PROTOTYPES 

#ifdef _WIN32

#include <windows.h>
#include <GL/glew.h>
#include "RenderContextGLFW.h"

typedef RenderContextGLFW T_RENDERCONTEXT;

#define USE_GLEW
#define NEED_VERTEX_ARRAY_OBJECT

#else

#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#include "RenderContextEGL.h"

typedef RenderContextEGL T_RENDERCONTEXT;

#endif // _WIN32


#endif // !GLINIT_H

