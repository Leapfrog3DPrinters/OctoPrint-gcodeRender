import ctypes
import os

os.environ["PYOPENGL_PLATFORM"] = "egl"

# Requires pyopengl>=3.1.1a1
from OpenGL.EGL import *
from OpenGL.GLES2 import *

import OpenGL.GLES2.VERSION.GLES2_2_0
import OpenGL.arrays

# First, fix a bug in Pyopengl
OpenGL.GLES2.VERSION.GLES2_2_0.ArrayDatatype = OpenGL.arrays.ArrayDatatype 
OpenGL.GLES2.VERSION.GLES2_2_0.contextdata = OpenGL.contextdata

# Define some extra constants that the automatic extraction misses
EGL_DEFAULT_DISPLAY = 0
EGL_NO_CONTEXT = 0
EGL_NO_DISPLAY = 0
EGL_NO_SURFACE = 0

eglint = ctypes.c_int
eglshort = ctypes.c_short

def eglints(L):
    """Converts a tuple to an array of eglints (would a pointer return be better?)"""
    return (eglint * len(L))(*L)

eglfloat = ctypes.c_float

def eglfloats(L):
    return (eglfloat * len(L))(*L)
                
class EGLContext(object):

    def __init__(self, pref_width, pref_height, 
               red_size=8, green_size=8,blue_size=8,
               alpha_size=0, depth_size=24, 
               layer=0, alpha_flags=0, alpha_opacity=0, other_attribs=[]):
        """Opens up the OpenGL library and prepares a window for display"""
       
        # Get and initialize the current display from EGL
        self.display = eglGetDisplay(EGL_DEFAULT_DISPLAY)
        assert self.display

        major, minor = ctypes.c_long(),ctypes.c_long()
        r = eglInitialize(self.display, major, minor)
        assert r
        
        # Define surface config
        attribute_list = [EGL_RED_SIZE, red_size,
                          EGL_GREEN_SIZE, green_size,
                          EGL_BLUE_SIZE, blue_size]
        if alpha_size:
            attribute_list.extend([EGL_ALPHA_SIZE, alpha_size])
        
        if depth_size:
            attribute_list.extend([EGL_DEPTH_SIZE, depth_size])

        if other_attribs and len(other_attribs) % 2 == 0:
            attribute_list.extend(other_attribs)

        attribute_list.extend([EGL_COLOR_BUFFER_TYPE, EGL_RGB_BUFFER])

        #attribute_list.extend([EGL_CONFIG_CAVEAT, EGL_NONE])
        #attribute_list.extend([EGL_SAMPLE_BUFFERS, 1])
        #attribute_list.extend([EGL_SAMPLES, 1])
        #attribute_list.extend([EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT])
        #attribute_list.extend([EGL_CONFORMANT, EGL_OPENGL_ES2_BIT])

        attribute_list.append(EGL_NONE)
        attribute_list = eglints(attribute_list)

        # Set config
        numconfig = ctypes.c_long()
        configs = (EGLConfig * 2)()

        r = eglChooseConfig(self.display, attribute_list, configs, 2, numconfig)
        assert r

        # Bind API
        r = eglBindAPI(EGL_OPENGL_ES_API)
        assert r

        # Create context
        context_attribs = eglints((EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE))
        self.context = eglCreateContext(self.display, configs[0], EGL_NO_CONTEXT, context_attribs)

        # Find the display size
        self.width = eglint(pref_width)
        self.height = eglint(pref_height)

        surface_attribute_list = [EGL_WIDTH, self.width.value,
                                    EGL_HEIGHT, self.height.value, EGL_NONE]

        self.surface = eglCreatePbufferSurface(self.display, configs[0], surface_attribute_list)

        assert self.surface != EGL_NO_SURFACE
        assert self.context != EGL_NO_CONTEXT

        r = eglMakeCurrent(self.display, self.surface, self.surface, self.context)
        assert r
       
    def swap(self):
        eglSwapBuffers(self.display, self.surface)

    def close(self):
        eglDestroySurface(self.display, self.surface)

        # Release OpenGL resources
        eglMakeCurrent(self.display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT)
        eglDestroyContext(self.display, self.context)
        eglTerminate(self.display)
