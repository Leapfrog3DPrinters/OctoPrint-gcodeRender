from __future__ import absolute_import

import sys, os

from math import *
from OpenGL.GLU import *
from ctypes import cdll, sizeof, c_float, c_void_p, c_uint, string_at
os.environ["PYSDL2_DLL_PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../rendering/sdl')
import sdl2
from OpenGL.GL import *

from octoprint_gcoderender.experimental.gcodeparser import *

from octoprint_gcoderender.rendering.matrix44 import *
from octoprint_gcoderender.rendering.vector3 import *

from PIL import Image
from datetime import datetime

# C-type helpers
eglint = ctypes.c_int
egluint = ctypes.c_int
eglshort = ctypes.c_short

def eglints(L):
    """Converts a tuple to an array of eglints (would a pointer return be better?)"""
    return (eglint*len(L))(*L)


def egluints(L):
    """Converts a tuple to an array of eglints (would a pointer return be better?)"""
    return (egluint*len(L))(*L)

eglfloat = ctypes.c_float

def eglfloats(L):
    return (eglfloat*len(L))(*L)

width = 1000
height = 600
bed_width = 365
bed_depth = 350
sync_offset = float(bed_width - 35) / 2
part_color = (77./255., 120./255., 190./255.)
bed_color =  (70./255., 70./255., 70./255.)
background_color =  (1,1,1)
camera_position =  (0, -80.0, 100.0)
camera_rotation =  (radians(45), radians(0), radians(0))
camera_distance = (-100., -100., 75.)

def logInfo(message):
    print "{time} {msg}".format(time=datetime.now(), msg=message)

def _load_shader(shader_src, shader_type = GL_VERTEX_SHADER):
    # Convert the src to the correct ctype, if not already done
    if isinstance(shader_src, basestring):
        shader_src = [shader_src]

    shader = glCreateShader(shader_type)
    glShaderSource(shader, shader_src)
    glCompileShader(shader)
  
    compiled = ctypes.c_int()

    # Check compiled status
    compiled = glGetShaderiv(shader, GL_COMPILE_STATUS)

    message = glGetShaderInfoLog(shader)
    if message:
        logInfo('Shader: shader message: %s' % message)

    return shader

# Create window
sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)

sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_RED_SIZE, 8)
sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_GREEN_SIZE, 8)
sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_BLUE_SIZE, 8)
sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_ALPHA_SIZE, 8)
sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_DEPTH_SIZE, 24)
sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_DOUBLEBUFFER, 1)
sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_MULTISAMPLEBUFFERS, 1)
sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_MULTISAMPLESAMPLES, 8)

window = sdl2.SDL_CreateWindow(b"GcodeRender",
                            sdl2.SDL_WINDOWPOS_UNDEFINED,
                            sdl2.SDL_WINDOWPOS_UNDEFINED, width, height,
                            sdl2.SDL_WINDOW_OPENGL)
context = sdl2.SDL_GL_CreateContext(window)

# Create program
# Define the shaders that draw the vertices. Camera and color are kept contant.
vertex_shader_src = """
    #version 150
    uniform mat4 ds_ModelViewProjection; 
    uniform mat4 M; 
    uniform mat4 V; 
    attribute vec4 ds_Position;
    attribute vec3 ds_Normal;
    
    varying vec3 Normal_cameraspace;
    varying vec3 LightDirection_cameraspace;
    varying vec3 EyeDirection_cameraspace;

    void main()
    {
        vec3 LightPosition_worldspace = vec3(150, -50, 100);

        // Output position of the vertex, in clip space : MVP * position
        gl_Position =  ds_ModelViewProjection * ds_Position;

        // Position of the vertex, in worldspace : M * position
        vec3 Position_worldspace = (M * ds_Position).xyz;

        // Vector that goes from the vertex to the camera, in camera space.
        // In camera space, the camera is at the origin (0,0,0).
        vec3 vertexPosition_cameraspace = ( V * M * ds_Position).xyz;
        EyeDirection_cameraspace = vec3(0,0,0) - vertexPosition_cameraspace;

        // Vector that goes from the vertex to the light, in camera space. M is ommited because it's identity.
        vec3 LightPosition_cameraspace = ( V * vec4(LightPosition_worldspace,1)).xyz;
        LightDirection_cameraspace = LightPosition_cameraspace + EyeDirection_cameraspace;

        // Normal of the the vertex, in camera space
        Normal_cameraspace = ( V * M * vec4(ds_Normal,0)).xyz; // Only correct if ModelMatrix does not scale the 
    }
"""

fragment_shader_src = """
    #version 150
    uniform vec4 ds_Color;
    varying vec3 Normal_cameraspace;
    varying vec3 LightDirection_cameraspace;
    varying vec3 EyeDirection_cameraspace;
    void main()
    {

        
        vec4 MaterialAmbientColor = vec4(0.1,0.1,0.1,1) * ds_Color;
        // Normal of the computed fragment, in camera space
        vec3 n = normalize( Normal_cameraspace );
        // Direction of the light (from the fragment to the light)
        vec3 l = normalize( LightDirection_cameraspace );
        // Eye vector (towards the camera)
        vec3 E = normalize(EyeDirection_cameraspace);
        // Direction in which the triangle reflects the light
        vec3 R = reflect(-l,n);
        // Cosine of the angle between the Eye vector and the Reflect vector,
        // clamped to 0
        //  - Looking into the reflection -> 1
        //  - Looking elsewhere -> < 1
        float cosAlpha = clamp( dot( E,R ), 0,1 );
        float LightPower = 1.0; //TODO: Make uniform
        vec4 LightColor = vec4(2.0); //TODO: Make uniform
        float cosTheta = clamp( dot( n,l ), 0, 1 );
        gl_FragColor = MaterialAmbientColor + ds_Color * LightColor * LightPower * pow(cosAlpha,5) + (ds_Color * LightColor * LightPower) * (cosTheta); // TODO: Add divide by square of distance 
    }
"""

with open("C:\\tijdelijk\\shaders\\StandardShading.vertexshader") as f:
    vertex_shader_src = f.read()
with open("C:\\tijdelijk\\shaders\\StandardShading.fragmentshader") as f:
    fragment_shader_src = f.read()

vertexShader = _load_shader(vertex_shader_src, GL_VERTEX_SHADER)
fragmentShader = _load_shader(fragment_shader_src, GL_FRAGMENT_SHADER)

program = glCreateProgram()

logInfo("Create program %s" % hex(glGetError()))

glAttachShader(program, vertexShader)
glAttachShader(program, fragmentShader)

logInfo("Attach shaders %s" % hex(glGetError()))
        
glLinkProgram (program)
logInfo("Link program %s" % hex(glGetError()))

logInfo("Program: %s" % program)

# Get pointers to the shader parameters
position_handle = glGetAttribLocation(program, "vertexPosition_modelspace")
logInfo("Position handle: %s" % position_handle)

normal_handle = glGetAttribLocation(program, "vertexNormal_modelspace")
logInfo("Normal handle: %s" % normal_handle)

color_handle = glGetUniformLocation(program, "ds_Color")
logInfo("Color handle: %s" % color_handle)

light_handle = glGetUniformLocation(program, "LightPosition_worldspace")
logInfo("Light handle: %s" % light_handle)

camera_handle = glGetUniformLocation(program, "MVP")
logInfo("Camera handle: %s" % camera_handle)

m_handle = glGetUniformLocation(program, "M")
v_handle = glGetUniformLocation(program, "V")
        
# Activate the program
glUseProgram(program)
logInfo("Use program: %s" % hex(glGetError()))

# Enable depth test
glEnable(GL_DEPTH_TEST);
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
logInfo("Clear all: %s" % hex(glGetError()))

scriptPath = os.path.realpath(__file__)
scriptDir = os.path.dirname(scriptPath)
gCodePath = os.path.join(scriptDir, "../sample/leapfrog.gcode")
parser = GcodeParser(verbose = True)
gcode_model = parser.parseFile(gCodePath)

base_vertices = gcode_model.segments
base_indices = gcode_model.indices

# Check if the gcode model knows the boundaries of the part
if gcode_model.bbox:
    object_center = Vector3(gcode_model.bbox.cx()+20, gcode_model.bbox.cy()+20, gcode_model.bbox.cz())
    scale = max(gcode_model.bbox.dx(), gcode_model.bbox.dy(), gcode_model.bbox.dz())  / 75
else:
    object_center = Vector3(bed_width/2, bed_depth/2, 0)
    scale = 1

#object_center = Vector3(105, 105, 0)
#scale = 0.5

# Calculate the camera distance
cam_dist = Vector3(camera_distance) * scale
camera_position = (object_center + cam_dist).as_tuple()
up = (0, 0, 1)

# Calculate the lookat and projection matrices
lookat = Matrix44.lookat(object_center, up, camera_position)
projection = Matrix44.perspective_projection_fov(radians(45), float(width)/float(height), 0.1, 10000.0)

# Calculate the camera matrix. This matrix translates and rotates all vertices, as such that it looks like the camera is brought in position
camera_matrix = projection * lookat

ccam = eglfloats(camera_matrix.to_opengl())
ccam_m = eglfloats(Matrix44().to_opengl())
ccam_v = eglfloats(lookat.to_opengl())

# Upload the camera matrix to OpenGLES
glUniformMatrix4fv(camera_handle, 1, GL_FALSE, ccam)
glUniformMatrix4fv(m_handle, 1, GL_FALSE, ccam_m)
glUniformMatrix4fv(v_handle, 1, GL_FALSE, ccam_v)

# Set light position
glUniform3f(light_handle, -100, -50, 300)

# Define the vertices that make up the print bed. The vertices define two triangles that make up a square 
# (squares are not directly supported in OpenGLES)
logInfo("Load vertices")

# X, y, z, nx, ny, nz
bedvertices = (   0, 0, 0, 0, 0, 1,
                    0, bed_depth, 0, 0, 0, 1,
                    bed_width, bed_depth, 0, 0, 0, 1,
                    bed_width, 0, 0, 0, 0, 1)

bedindices = ( 0, 1, 2, 2, 3, 0 )

cbedvertices = eglfloats(bedvertices)
cbedindices = egluints(bedindices)
glEnableClientState(GL_VERTEX_ARRAY)
# Draw the bed in a similar way as the part, but without a VBO
glUniform4f(color_handle, bed_color[0], bed_color[1], bed_color[2], 1.0)
logInfo("Bed color %s" % hex(glGetError()))

ivbo = glGenBuffers(1)
glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ivbo)
glBufferData(GL_ELEMENT_ARRAY_BUFFER, cbedindices, GL_STATIC_DRAW)
vbo = glGenBuffers(1)
glBindBuffer(GL_ARRAY_BUFFER, vbo)
glBufferData(GL_ARRAY_BUFFER, cbedvertices, GL_STATIC_DRAW)
glEnableVertexAttribArray(position_handle)
glEnableVertexAttribArray(normal_handle)
logInfo("Enable array %s" % hex(glGetError()))
glVertexAttribPointer(position_handle, 3, GL_FLOAT, GL_FALSE, sizeof(eglfloat)*6, c_void_p(0 * sizeof(c_float))) # 3 floats per vertex (x, y, z)
glVertexAttribPointer(normal_handle, 3, GL_FLOAT, GL_FALSE, sizeof(eglfloat)*6, c_void_p(3 * sizeof(c_float))) # 3 floats per vertex (x, y, z)
logInfo("Bed vertex array %s" % hex(glGetError()))

glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ivbo)
glDrawElements(GL_TRIANGLES, len(cbedindices), GL_UNSIGNED_INT, None)
logInfo("Draw bed array %s" % hex(glGetError()))

glDisableVertexAttribArray(position_handle)
logInfo("Disable array %s" % hex(glGetError()))
glBindBuffer(GL_ARRAY_BUFFER, 0)
glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
glDeleteBuffers(1, vbo)
glDeleteBuffers(1, ivbo)
   
# Get the part vertices 
# cvertices is a one-dimensional array: [x1a y1a z1a x1b y1b z1b x2a y2a ... ], where the number refers to the line number and a/b to start/end of the line.
# Thus each line consists out of 6 floats
N = len(base_vertices)
cvertices = base_vertices
cindices = base_indices
logInfo("Vertices loaded")

# Set the shader's color parameter to the part color 
glUniform4f(color_handle, part_color[0], part_color[1], part_color[2], 1.0)
logInfo("Coloring: %s" % hex(glGetError()))
logInfo("Color: {0} {1} {2}".format(*part_color))


#cindices = egluints((0, 1, 11))
# Create a Vertex Buffer Object
ivbo = glGenBuffers(1)
glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ivbo)
glBufferData(GL_ELEMENT_ARRAY_BUFFER, cindices, GL_STATIC_DRAW)

vbo = glGenBuffers(1)
glBindBuffer(GL_ARRAY_BUFFER, vbo)
glBufferData(GL_ARRAY_BUFFER, cvertices, GL_STATIC_DRAW)

glEnableVertexAttribArray(position_handle)
glEnableVertexAttribArray(normal_handle)

glVertexAttribPointer(position_handle, 3, GL_FLOAT, GL_FALSE, sizeof(eglfloat)*6, c_void_p(0 * sizeof(c_float))) # The array consists of 3 items per vertex (x, y, z)
glVertexAttribPointer(normal_handle, 3, GL_FLOAT, GL_FALSE, sizeof(eglfloat)*6, c_void_p(3 * sizeof(c_float))) # The array consists of 3 items per vertex (x, y, z)

# The position parameter is set, now start drawing. Because of GL_LINES, 2 vertices are expected per line = cvertices->a and b

glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ivbo)
glDrawElements(GL_TRIANGLES, len(cvertices), GL_UNSIGNED_INT, None)
logInfo("Draw part %s" % hex(glGetError()))

#Remove the binding to the VBO
glDisableVertexAttribArray(position_handle)
logInfo("Disable vertex array %s" % hex(glGetError()))
glBindBuffer(GL_ARRAY_BUFFER, 0)
glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
logInfo("Disable buffer %s" % hex(glGetError()))

glDeleteBuffers(1, vbo)
glDeleteBuffers(1, ivbo)
logInfo("Delete buffer %s" % hex(glGetError()))

sdl2.SDL_GL_SwapWindow(window)

raw_input()
