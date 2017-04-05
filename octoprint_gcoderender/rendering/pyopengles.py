#
# Copyright (c) 2012 Peter de Rivaz
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.
#
# Raspberry Pi 3d demo using OpenGLES 2.0 via Python
#
# Version 0.1 (Draws a rectangle using vertex and fragment shaders)
# Version 0.2 (Draws a Julia set on top of a Mandelbrot controlled by the mouse.  Mandelbrot rendered to texture in advance.

import ctypes
import time
import math
import sys
import os

os.environ["PYOPENGL_PLATFORM"] = "egl"

from OpenGL.EGL import *
from OpenGL.GLES3 import *

# Define verbose=True to get debug messages
verbose = False

# Define some extra constants that the automatic extraction misses
EGL_DEFAULT_DISPLAY = 0
EGL_NO_CONTEXT = 0
EGL_NO_DISPLAY = 0
EGL_NO_SURFACE = 0
DISPMANX_PROTECTION_NONE = 0

# Open the libraries
bcm = ctypes.CDLL('libbcm_host.so')

eglint = ctypes.c_int

eglshort = ctypes.c_short

def eglints(L):
    """Converts a tuple to an array of eglints (would a pointer return be better?)"""
    return (eglint*len(L))(*L)

eglfloat = ctypes.c_float

def eglfloats(L):
    return (eglfloat*len(L))(*L)
                
class Alpha_struct(ctypes.Structure):
  """typedef enum {
  /* Bottom 2 bits sets the alpha mode */
  DISPMANX_FLAGS_ALPHA_FROM_SOURCE = 0,
  DISPMANX_FLAGS_ALPHA_FIXED_ALL_PIXELS = 1,
  DISPMANX_FLAGS_ALPHA_FIXED_NON_ZERO = 2,
  DISPMANX_FLAGS_ALPHA_FIXED_EXCEED_0X07 = 3,

  DISPMANX_FLAGS_ALPHA_PREMULT = 1 << 16,
  DISPMANX_FLAGS_ALPHA_MIX = 1 << 17
} DISPMANX_FLAGS_ALPHA_T;

typedef struct {
  DISPMANX_FLAGS_ALPHA_T flags;
  uint32_t opacity;
  VC_IMAGE_T *mask;
} DISPMANX_ALPHA_T;

typedef struct {
  DISPMANX_FLAGS_ALPHA_T flags;
  uint32_t opacity;
  DISPMANX_RESOURCE_HANDLE_T mask;
} VC_DISPMANX_ALPHA_T;  /* for use with vmcs_host */

"""

  _fields_ = [ ("flags", ctypes.c_long),
               ("opacity", ctypes.c_ulong),
               ("mask", ctypes.c_ulong)]


class Window_struct(ctypes.Structure):
	"""typedef struct {
   DISPMANX_ELEMENT_HANDLE_T element;
   int width;   /* This is necessary because dispmanx elements are not queriable. */
   int height;
 } EGL_DISPMANX_WINDOW_T;
"""

	_fields_ = [ ("element", ctypes.c_uint32), 
		("width", ctypes.c_int), 
		("height", ctypes.c_int) ]

class EGLContext(object):

    def __init__(self, pref_width=None, pref_height=None, 
               red_size=8, green_size=8,blue_size=8,
               alpha_size=None, depth_size=8, 
               layer=0, alpha_flags=0, alpha_opacity=0, other_attribs = []):
        """Opens up the OpenGL library and prepares a window for display"""
        b = bcm.bcm_host_init()
        assert b==0
        self.display = eglGetDisplay(EGL_DEFAULT_DISPLAY)
        assert self.display
	major, minor = ctypes.c_long(),ctypes.c_long()
        r = eglInitialize(self.display, major, minor)
        assert r
        
        
        attribute_list = [EGL_RED_SIZE, red_size,
                          EGL_GREEN_SIZE, green_size,
                          EGL_BLUE_SIZE, blue_size]
        if alpha_size:
            attribute_list.extend([EGL_ALPHA_SIZE, alpha_size])

        attribute_list.extend([EGL_SURFACE_TYPE, EGL_WINDOW_BIT])
        
        if depth_size:
            attribute_list.extend([EGL_DEPTH_SIZE, depth_size])
        if other_attribs and len(other_attribs) % 2 == 0:
            attribute_list.extend(other_attribs)
	#attribute_list.extend([EGL_COLOR_BUFFER_TYPE, EGL_RGB_BUFFER])
	#attribute_list.extend([EGL_CONFIG_CAVEAT, EGL_NONE])
        #attribute_list.extend([EGL_CONFORMANT, EGL_OPENGL_ES2_BIT])
        attribute_list.append(EGL_NONE)
	print('attribute_list', attribute_list)
        attribute_list = eglints(attribute_list)

        numconfig = ctypes.c_long()
        configs = (EGLConfig*2)()

        r = eglChooseConfig(self.display, attribute_list, configs, 2, numconfig)
        assert r

	print numconfig.value

        r = eglBindAPI(EGL_OPENGL_ES_API)
        assert r

        context_attribs = eglints((EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE))
        self.context = eglCreateContext(self.display, configs[0], EGL_NO_CONTEXT, context_attribs)

        width = eglint()

        height = eglint()

        s = bcm.graphics_get_display_size(0,ctypes.byref(width),ctypes.byref(height))

        if pref_width and pref_height:

            self.width = eglint(pref_width)

            self.height = eglint(pref_height)

            width = self.width

            height = self.height

        else:

            self.width = width

            self.height = height

        assert s>=0

        self.dispman_display = bcm.vc_dispmanx_display_open(0)

        dispman_update = bcm.vc_dispmanx_update_start( 0 )
        dst_rect = eglints( (0,0,width.value,height.value) )
        src_rect = eglints( (0,0,width.value<<16, height.value<<16) )

        assert dispman_update

        assert self.dispman_display

        alpha_s = Alpha_struct(alpha_flags, 0xFF, 0)



        self.dispman_element = bcm.vc_dispmanx_element_add ( dispman_update, self.dispman_display,
                                  layer, ctypes.byref(dst_rect), 0,
                                  ctypes.byref(src_rect),
                                  DISPMANX_PROTECTION_NONE,
                                  ctypes.byref(alpha_s), 0, 0)
	print self.dispman_element
        bcm.vc_dispmanx_update_submit_sync( dispman_update )

        nativewindow = EGLNativeWindowType(eglints((self.dispman_element,width.value,height.value)))

        self.surface = eglCreateWindowSurface( self.display, configs[0], nativewindow , None)

        assert self.surface != EGL_NO_SURFACE



        assert self.context != EGL_NO_CONTEXT

        r = eglMakeCurrent(self.display, self.surface, self.surface, self.context)
        assert r
       
    def close(self):
        print "Closing..."
        eglDestroySurface( self.display, self.surface )

        dispman_update = bcm.vc_dispmanx_update_start( 0 );
        print "Dispman_update %s" % dispman_update
        print "dispman_element %s" % self.dispman_element
        s = bcm.vc_dispmanx_element_remove(dispman_update, self.dispman_element);
        assert(s == 0);
        bcm.vc_dispmanx_update_submit_sync( dispman_update );
        s = bcm.vc_dispmanx_display_close(self.dispman_display);
        assert (s == 0);

        # Release OpenGL resources
        eglMakeCurrent( self.display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT )
        eglDestroyContext( self.display, self.context )
        eglTerminate( self.display )

        b = bcm.bcm_host_deinit()
