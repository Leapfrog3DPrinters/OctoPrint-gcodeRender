import sys

from math import *

import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

from gcodeparser import *

from matrix44 import *
from vector3 import *

from PIL import Image

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

def check(e):
    """Checks that error is zero"""
    if e==0: return
    if verbose:
        print 'Error code',hex(e&0xffffffff)
    raise ValueError

class ShaderCompilationFailed(Exception):
    def __init__(self, reason=None):
        self.reason = reason

class GLError(Exception):
    def __init__(self, code=None):
        self.code = code

    def __str__(self):
        if self.code:
            if self.code == GL_NO_ERROR:
                return "No Error found (%s)" % self.code
            elif self.code == GL_INVALID_ENUM:
                return "A GLenum argument is out of range. The command that generated that error is ignored (%s)" % self.code
            elif self.code == GL_INVALID_VALUE:
                return "A numeric argument is out of range. The command that generated that error is ignored (%s)" % self.code
            elif self.code == GL_INVALID_OPERATION:
                return "The specific command cannot be performed in the current state. The command that generated this is ignored (%s)" % self.code
            elif self.code == GL_OUT_OF_MEMORY:
                return "There is insufficient memory to execute this command. The state of the OpenGL ES pipeline is considered to be undefined. All bets are off, basically. (%s)" % self.code
            return "Unknown error code (%s)" % self.code
        else:
            return "No error code given"
                

class wind(object):

    def __init__(self, pref_width=None, pref_height=None, 
               red_size=8, green_size=8,blue_size=8,
               alpha_size=8, depth_size=None, 
               layer=0, alpha_flags=0, alpha_opacity=0, other_attribs = []):
      pass

    def _check_Linked_status(self, programObject):
        # Check the link status
        linked = eglint()
        glGetProgramiv ( programObject, GL_LINK_STATUS, ctypes.byref(linked))
        try:
            self._check_glerror()
        except GLError, e:
            print e
            return False

        if (linked.value == 0):
            print "Linking failed!"
            loglength = eglint()
            charswritten = eglint()
            glGetProgramiv(programObject, GL_INFO_LOG_LENGTH, ctypes.byref(loglength))
            logmsg = ctypes.c_char_p(" "*loglength.value)
            glGetProgramInfoLog(programObject, loglength, ctypes.byref(charswritten), logmsg)
            print logmsg.value
            return False
        return True
    
    def _check_glerror(self):
        e=glGetError()
        if e:
            raise GLError(e)
        return

    def _show_shader_log(self, shader):
        """Prints the compile log for a shader"""
        N=1024
        log=(ctypes.c_char*N)()
        loglen=ctypes.c_int()
        log = glGetShaderInfoLog(shader)
        print log
        
    def _show_program_log(self, program):
        """Prints the compile log for a program"""
        N=1024
        log=(ctypes.c_char*N)()
        loglen=ctypes.c_int()
        log = glGetProgramInfoLog(program)
        print log

    def load_shader ( self, shader_src, shader_type = GL_VERTEX_SHADER, quiet = True ):
        # Convert the src to the correct ctype, if not already done
        c_shader_src = shader_src
        #if type(shader_src) == basestring or type(shader_src) == str:
            #c_shader_src = ctypes.c_char_p(shader_src)

        # Create a shader of the given type
        if not quiet:
            print "Creating shader object"
        shader = glCreateShader(shader_type)
        glShaderSource(shader, c_shader_src)
        glCompileShader(shader)
  
        compiled = eglint()

        # Check compiled status
        glGetShaderiv ( shader, GL_COMPILE_STATUS, ctypes.byref(compiled) )

        if (compiled.value == 0):
            print "Failed to compile shader '%s'" % shader_src 
            loglength = eglint()
            charswritten = eglint()
            glGetShaderiv(shader, GL_INFO_LOG_LENGTH, ctypes.byref(loglength))
            logmsg = ctypes.c_char_p(" "*loglength.value)
            logmsg = glGetShaderInfoLog(shader)
            #glGetShaderInfoLog(shader, loglength, ctypes.byref(charswritten), logmsg)
            print logmsg
            raise ShaderCompilationFailed(logmsg)
        elif not quiet:
            shdtyp = "{unknown}"
            if shader_type == GL_VERTEX_SHADER:
                shdtyp = "GL_VERTEX_SHADER"
            elif shader_type == GL_FRAGMENT_SHADER:
                shdtyp = "GL_FRAGMENT_SHADER"
            print "Compiled %s shader" % (shdtyp)
        if not quiet:
            self._show_shader_log(shader)
        return shader

    def get_program(self, vertex_shader_src, fragment_shader_src, bindings=[], quiet=True):
        # Load the vertex/fragment shaders (can throw a ShaderCompilationFailed exception)
        vertexShader = self.load_shader ( vertex_shader_src, GL_VERTEX_SHADER, quiet )
        fragmentShader = self.load_shader ( fragment_shader_src, GL_FRAGMENT_SHADER, quiet )
        self._check_glerror()

        # Create the program object
        programObject = glCreateProgram ( )
        self._check_glerror()

        glAttachShader ( programObject, vertexShader )
        glAttachShader ( programObject, fragmentShader )
        self._check_glerror()

        # Bind positions to attributes:
        for pos, attrib in bindings:
            glBindAttribLocation ( programObject, pos, attrib )
        self._check_glerror()

        # Link the program
        glLinkProgram ( programObject )
        self._check_glerror()

        # Check the link status
        if not (self._check_Linked_status(programObject)):
            print "Couldn't link the shaders to the program object. Check the bindings and shader sourcefiles."
            raise Exception
        if not quiet:
            self._show_program_log(programObject)
        return programObject

def _getVertices(model):
    
        vertices = []
        
        for layer in model.layers:
            
            layer_vertices = []
            
            x = layer.start["X"]
            y = layer.start["Y"]
            z = layer.start["Z"]
       
            for seg in layer.segments:
                if seg.style is "extrude":
                    layer_vertices.append((x, y, z))
                    x = seg.coords["X"]
                    y = seg.coords["Y"]
                    z = seg.coords["Z"]
                    layer_vertices.append((x, y, z))
            
            vertices.append(layer_vertices)

        return vertices  

DEFAULT_BED_COLOR=  (70./255., 70./255., 70./255.)
DEFAULT_PART_COLOR = (77./255., 120./255., 190./255.)
bed_color = DEFAULT_BED_COLOR
part_color = DEFAULT_PART_COLOR
bed_width = 365
bed_depth = 350

vertex_shader = """
            uniform mat4 uCamera; 
            attribute vec4 aPosition;
            void main()
            {
                gl_Position = uCamera * aPosition;
		//gl_Position = aPosition;
            }
        """

fragment_shader = """
    //precision mediump float;
    uniform vec4 uColor;

    void main()
    {
        gl_FragColor = uColor;
    }
"""

ctx = wind()
binding = ((5, 'aPosition'),)
width = 480
height = 800
pygame.init()
pygame.display.set_mode((width, height), HWSURFACE|OPENGL|DOUBLEBUF)

program = ctx.get_program(vertex_shader, fragment_shader, binding, False)

position_handle = glGetAttribLocation(program, "aPosition")
print "Position handle: %s" % position_handle
color_handle = glGetUniformLocation(program, "uColor")
print "Color handle: %s" % color_handle
camera_handle = glGetUniformLocation(program, "uCamera")
print "Camera handle: %s" % camera_handle

glUseProgram(program)
print "Use program: %s" % hex(glGetError())

glClearColor(eglfloat(1), eglfloat(1), eglfloat(1),eglfloat(1.0))

# Clear the color buffer
glClear ( GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT )
glEnable(GL_DEPTH_TEST)

# Set the Viewport: (NB openegl, not opengles)
glViewport(0,0,width, height)

camera_matrix = Matrix44()

translation = Matrix44.translation(0, 1, 3).get_inverse()
rotation = Matrix44.xyz_rotation(0, radians(10), radians(10)).get_inverse()
lookat = Matrix44()
#lookat = Matrix44.lookat((0, 0, 0), (0, 0, 1), (0, 1, 1)).get_transpose()
lookat = Matrix44.lookat((float(bed_width)/2, float(bed_depth)/2, 0), (0, 0, 1), (float(bed_width)/2, -100, 300))

#lookat_rotation = Matrix44().lookat_rotation((0.5, 0.5, 0), (0, 1, 0), (2, 2, 2))
#lookat_translation = Matrix44().lookat_translation((0.5, 0.5, 0), (0, 1, 0), (2, 2, 2))

projection = Matrix44.perspective_projection_fov(radians(120), float(width)/float(height), 0.1, 1000.0)

camera_matrix = projection * lookat
camera_matrix = camera_matrix

print "Rotation:"
print rotation

print "Translation:"
print translation

print "Lookat:"
print lookat

print "Projection:"
print projection

print "Final:"
print camera_matrix.get_transpose()

ccam = eglfloats(camera_matrix.to_opengl())

glUniformMatrix4fv(camera_handle, 1, GL_FALSE, ccam)


bedvertices = eglfloats((   0, 0, 0,
                            0, bed_depth, 0,
                            bed_width, bed_depth, 0,
                            bed_width, bed_depth, 0,
                            bed_width, 0, 0,
                            0, 0, 0))

partvertices = eglfloats((   0.25*bed_width, 0.25*bed_depth, 0.05,
                            0.25*bed_width, 0.75*bed_depth, 0.05,
                            0.75*bed_width, 0.75*bed_depth, 0.05,
                            0.75*bed_width, 0.75*bed_depth, 0.05,
                            0.75*bed_width, 0.25*bed_depth, 0.05,
                            0.25*bed_width, 0.25*bed_depth, 0.05))

#bedvertices = eglfloats((   0, 0, 0,
#                            0, 1, 0,
#                            1, 1, 0,
#                            1, 1, 0,
#                            1, 0, 0,
#                            0, 0, 0))

parser = GcodeParser()
gcodeFile = "C:\Users\erikh\OneDrive\Programmatuur\OctoPrint-gcodeRender\octoprint_gcoderender\sample\leapfrog_small.gcode"
gcode_model = parser.parseFile(gcodeFile)
base_vertices = _getVertices(gcode_model)

bedvertices = eglfloats((   0, 0, 0,
                            0, bed_depth, 0,
                            bed_width, bed_depth, 0,
                            bed_width, bed_depth, 0,
                            bed_width, 0, 0,
                            0, 0, 0))
        
vertices = []
for layer_idx in xrange(len(base_vertices)):
    for vertex in base_vertices[layer_idx]:
        vertices.append(vertex[0])
        vertices.append(vertex[1])
        vertices.append(vertex[2])

N = len(vertices)
cvertices = eglfloats(vertices)
        
glUniform4f(color_handle, eglfloat(part_color[0]), eglfloat(part_color[1]), eglfloat(part_color[2]), eglfloat(1.0))
print "Coloring: %s" % hex(glGetError())
print "Color: {0} {1} {2}".format(*part_color)
glEnableClientState(GL_VERTEX_ARRAY)
print "Client state"

vbo = glGenBuffers(1)
print "VBO: %s" % vbo
glBindBuffer(GL_ARRAY_BUFFER, vbo)
print "Bind buffer: %s" % hex(glGetError())
print "N vertices: %s" % N
print "Buffer size: %s" % ctypes.sizeof(cvertices)
glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(cvertices), cvertices, GL_STATIC_DRAW)
print "Buffer filled %s" % hex(glGetError())
glEnableVertexAttribArray(position_handle)
print "Enable part vertex: %s" % hex(glGetError())
glBindBuffer(GL_ARRAY_BUFFER, vbo)
print "Bind buffer: %s" % hex(glGetError())
glVertexAttribPointer(position_handle, 3, GL_FLOAT, GL_FALSE, 0, None)
#glEnableVertexAttribArray(position_handle)
print "Set part vertex: %s" % hex(glGetError())
#glBindBuffer(GL_ARRAY_BUFFER, vbo)
glDrawArrays( GL_LINES , 0, N/3 )
print "Draw part tri %s" % hex(glGetError())
glDisableVertexAttribArray(position_handle)
print "Disable vertex array %s" % hex(glGetError())
glBindBuffer(GL_ARRAY_BUFFER, 0)
print "Disable buffer %s" % hex(glGetError())

glUniform4f(color_handle, eglfloat(bed_color[0]), eglfloat(bed_color[1]), eglfloat(bed_color[2]), eglfloat(1.0))
print "Bed color %s" % hex(glGetError())
glVertexAttribPointer(position_handle, 3, GL_FLOAT, GL_FALSE, 0, bedvertices)
print "Bed vertex array %s" % hex(glGetError())
glEnableVertexAttribArray(position_handle)
print "Enable array %s" % hex(glGetError())
glDrawArrays ( GL_TRIANGLES, 0, 6 )
print "Draw bed array %s" % hex(glGetError())
glDisableVertexAttribArray(position_handle)
print "Disable array %s" % hex(glGetError())
glDeleteBuffers(1, vbo)
print "Delete buffer %s" % hex(glGetError())


pygame.display.flip()

