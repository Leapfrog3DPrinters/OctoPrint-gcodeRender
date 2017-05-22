#pragma once
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
