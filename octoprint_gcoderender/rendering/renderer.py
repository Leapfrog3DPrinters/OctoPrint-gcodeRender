__author__ = "Erik Heidstra <ErikHeidstra@live.nl>"

import sys, os

from math import *
from OpenGL.GLU import *

if sys.platform == "win32" or sys.platform == "darwin":
    os.environ["PYSDL2_DLL_PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sdl')
    import sdl2
    from OpenGL.GL import *
    CONTEXT_LIB="SDL"
else:
    from pyopengles import EGLContext
    from OpenGL.GLES3 import *
    CONTEXT_LIB="EGL"
    
from gcodeparser import *

from matrix44 import *
from vector3 import *

from PIL import Image
from datetime import datetime

# C-type helpers
eglint = ctypes.c_int
eglshort = ctypes.c_short

def eglints(L):
    """Converts a tuple to an array of eglints (would a pointer return be better?)"""
    return (eglint*len(L))(*L)

eglfloat = ctypes.c_float

def eglfloats(L):
    return (eglfloat*len(L))(*L)

# Default settings for the renderer
DEFAULT_WIDTH = 600
DEFAULT_HEIGHT = 1024
DEFAULT_BED_WIDTH = 365
DEFAULT_BED_DEPTH = 350
DEFAULT_SYNC_OFFSET = float(DEFAULT_BED_WIDTH - 35) / 2
DEFAULT_PART_COLOR = (77./255., 120./255., 190./255.)
DEFAULT_BED_COLOR=  (70./255., 70./255., 70./255.)
DEFAULT_BACKGROUND_COLOR=  (1,1,1)
DEFAULT_CAMERA_POSITION=  (0, -80.0, 100.0)
DEFAULT_CAMERA_MOVEMENT_SPEED = 100.0
DEFAULT_CAMERA_ROTATION=  (radians(45), radians(0), radians(0))
DEFAULT_CAMERA_ROTATION_SPEED = radians(90.0)
DEFAULT_CAMERA_DISTANCE = (-100., -100., 75.)

# Abstract of the renderer class, allow interoperability between linux and win32
#TODO: implement shared logic of win/linux
#TODO: Make a blueprint that makes more sense, functionality should better match to function names for both OpenGL and OpenGLES
class Renderer:
    def __init__(self, verbose = False):
        self.verbose = verbose
        pass
    def initialize(self):
        pass
    def close(self):
        pass
    def renderModel(self, gcodeFile, bringCameraInPosition = False):
        pass
    def clear(self):
        pass
    def save(self, imageFile):
        pass
    def logInfo(self, message):
        #TODO: Actual logging to file
        if self.verbose:
            print "{time} {msg}".format(time=datetime.now(), msg=message)

class RendererOpenGL(Renderer):
    def __init__(self, verbose = False):
        Renderer.__init__(self, verbose)
        #TODO:Parent class to share all these properties with the OpenGL-renderer
        self.show_window = False
        self.is_initialized = False
        self.is_window_open = False
        self.width = DEFAULT_WIDTH
        self.height = DEFAULT_HEIGHT
        self.bed_width = DEFAULT_BED_WIDTH
        self.bed_depth = DEFAULT_BED_DEPTH
        self.sync_offset = DEFAULT_SYNC_OFFSET
        self.background_color = DEFAULT_BACKGROUND_COLOR
        self.bed_color = DEFAULT_BED_COLOR
        self.part_color = DEFAULT_PART_COLOR
        self.camera_position = DEFAULT_CAMERA_POSITION
        self.camera_rotation = DEFAULT_CAMERA_ROTATION
        self.gcode_model = None
        self.base_vertices = None
        self.display_list = None
        self.rotation_direction = Vector3()
        self.rotation_speed = DEFAULT_CAMERA_ROTATION_SPEED
        self.movement_direction = Vector3()
        self.movement_speed = DEFAULT_CAMERA_MOVEMENT_SPEED
        self.camera_distance = DEFAULT_CAMERA_DISTANCE # Distance from object
        self.program = None
        self.context = None
        self.position_handle = None
        self.color_handle = None
        self.camera_handle = None
                
    def initialize(self, bedWidth, bedDepth, width = DEFAULT_WIDTH, height = DEFAULT_HEIGHT, showWindow = False,  backgroundColor = None, partColor = None, bedColor = None, cameraPosition = None, cameraRotation = None):
        """
        Initializes and configures the renderer
        """

        if self.is_initialized:
            return

        self.bed_width = bedWidth
        self.bed_depth = bedDepth
        self.width = width
        self.height = height
        self.show_window = showWindow

        if backgroundColor:
            self.background_color = backgroundColor
          
        if bedColor:
            self.bed_color = bedColor

        if partColor:
            self.part_color = partColor
            
        if cameraPosition:
            self.camera_position = cameraPosition
        else:
            self.camera_position = (self.bed_width / 2, DEFAULT_CAMERA_POSITION[1], DEFAULT_CAMERA_POSITION[2]) # Move to x-center

        if cameraRotation:
            self.camera_rotation = cameraRotation

        self._openWindow()
        
        self.is_initialized = True

    def close(self):
        """
        Closes the rendering context. Only call when you are done rendering all images
        """
        if not self.is_initialized or not self.is_window_open:
            return
       
        if CONTEXT_LIB == "SDL":
            sdl2.SDL_GL_DeleteContext(self.context)
            sdl2.SDL_DestroyWindow(self.window)
            sdl2.SDL_Quit()
        else:
            self.context.close()

    def renderModel(self, gcodeFile, bringCameraInPosition = False):
        """
        Renders a gcode file into a preview image.

        bringCameraInPosition: Automatically calculate camera position for a nice angle
        """ 
        if not self.is_initialized or not self.is_window_open:
            return

        # Read the gcode file and get all coordinates
        parser = GcodeParser(verbose = self.verbose)
        self.gcode_model = parser.parseFile(gcodeFile)

        # Deprecated: Sync mode. Distance between parts left and right
        if self.gcode_model.syncOffset > 0:
            self.sync_offset = self.gcode_model.syncOffset
        
        # Get all vertices that define the lines to be drawn from the parser
        self.base_vertices = self._getVertices()

        # Configure viewport
        self._setViewportAndPerspective()

        # Configure lights and colors
        self._setLight()

        # Start with a clean slate
        self._clearAll()

        if bringCameraInPosition:
            # Calculate a nice position for the camera and move it there
            self._bringCameraInPosition()
        else:
            # Just move the camera to the predefined (fixed) position
            self._updateCamera()

        # Prepare the lines that should be drawn from the vertices
        self._render()        
        
        # Draw the lines to the framebuffer
        self._display()

    def clear(self):
        """
        Clears the frame and draws the bed
        """
        if not self.is_initialized or not  self.is_window_open:
            return

        self._clearAll()
        self._renderBed()
    
    def save(self, imageFile):
        """
        Save the framebuffer to a file
        """

        if not self.is_initialized or not self.is_window_open:
            return

        # Create Buffer
        N = self.width*self.height*4
        data = (ctypes.c_uint8*N)()

        # Read all pixel colors
        glReadPixels(0,0,self.width,self.height,GL_RGBA,GL_UNSIGNED_BYTE, ctypes.byref(data))
        
        # Write raw data to image file
        imgSize = (self.width, self.height)
        img = Image.frombytes('RGBA', imgSize, data)
        img.transpose(Image.FLIP_TOP_BOTTOM).save(imageFile)

    def _load_shader ( self, shader_src, shader_type = GL_VERTEX_SHADER):
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
            self.logInfo('Shader: shader message: %s' % message)

        return shader

    def _openWindow(self):
        """
        Open a window for the renderer.
        """
        if self.is_window_open:
            return
        
        # Define the shaders that draw the vertices. Camera and color are kept contant.
        vertex_shader_src = """
            #version 150
            uniform mat4 ds_ModelViewProjection; 
            attribute vec4 ds_Position;
            void main()
            {
                gl_Position = ds_ModelViewProjection * ds_Position;
            }
        """

        fragment_shader_src = """
            #version 150
            uniform vec4 ds_Color;

            void main()
            {
                gl_FragColor = ds_Color;
            }
        """

        # Get a OpenGL context from EGL. The OpenGL framebuffers are bound to this context
        if CONTEXT_LIB == 'SDL':
            sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)

            sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_RED_SIZE, 8)
            sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_GREEN_SIZE, 8)
            sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_BLUE_SIZE, 8)
            sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_ALPHA_SIZE, 8)
            sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_DEPTH_SIZE, 24)
            sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_DOUBLEBUFFER, 1)
            sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_MULTISAMPLEBUFFERS, 1)
            sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_MULTISAMPLESAMPLES, 4)

            self.window = sdl2.SDL_CreateWindow(b"GcodeRender",
                                       sdl2.SDL_WINDOWPOS_UNDEFINED,
                                       sdl2.SDL_WINDOWPOS_UNDEFINED, self.width, self.height,
                                       sdl2.SDL_WINDOW_OPENGL|sdl2.SDL_WINDOW_HIDDEN)
            self.context = sdl2.SDL_GL_CreateContext(self.window)

        else:
            self.context = EGLContext(depth_size = 8)
            
        vertexShader = self._load_shader(vertex_shader_src, GL_VERTEX_SHADER)
        fragmentShader = self._load_shader(fragment_shader_src, GL_FRAGMENT_SHADER)

        self.program = glCreateProgram()

        self.logInfo("Create program %s" % hex(glGetError()))

        glAttachShader(self.program, vertexShader)
        glAttachShader(self.program, fragmentShader)

        self.logInfo("Attach shaders %s" % hex(glGetError()))

        # Bind positions to attributes:
        for pos, attrib in bindings:
            glBindAttribLocation (self.program, pos, attrib)

        self.logInfo("Set bindings %s" % hex(glGetError()))
        
        glLinkProgram (self.program)
        self.logInfo("Link program %s" % hex(glGetError()))

        self.logInfo("Program: %s" % self.program)

        # Get pointers to the shader parameters
        self.position_handle = glGetAttribLocation(self.program, "ds_Position")
        self.logInfo("Position handle: %s" % self.position_handle)

        self.color_handle = glGetUniformLocation(self.program, "ds_Color")
        self.logInfo("Color handle: %s" % self.color_handle)

        self.camera_handle = glGetUniformLocation(self.program, "ds_ModelViewProjection")
        self.logInfo("Camera handle: %s" % self.camera_handle)
        
        # Activate the program
        glUseProgram(self.program)
        self.logInfo("Use program: %s" % hex(glGetError()))

        self.is_window_open = True

    def _clearAll(self):
        """
        Render a blank screen
        """
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.logInfo("Clear all: %s" % hex(glGetError()))

    def _display(self):
        """
        Empty the buffers and if a window is open, swap the buffers
        """
        # Update the window
        glFlush()
        glFinish()

        if CONTEXT_LIB == 'SDL':
            pass
        else:
            openegl.eglSwapBuffers(self.context.display, self.context.surface)
        

    def _bringCameraInPosition(self):
        """
        Calculates the best position for the camera to bring the entire part into the viewport
        """

        # Check if the gcode model knows the boundaries of the part
        if self.gcode_model.bbox:
            # Find the center of the object and make an estimation of the size of it (the / 75 was found by trial and error to give a nice zoom factor)
            # Take more distance for sync/mirror parts 
            if self.gcode_model.printMode == 'sync':
                object_center = Vector3(self.gcode_model.bbox.cx() + self.sync_offset / 2, self.gcode_model.bbox.cy(), self.gcode_model.bbox.cz())
                scale = max(self.gcode_model.bbox.xmax+self.sync_offset - self.gcode_model.bbox.xmin, self.gcode_model.bbox.dy(), self.gcode_model.bbox.dz())  / 75
            elif self.gcode_model.printMode == 'mirror':
                object_center = Vector3(self.bed_width / 2, self.gcode_model.bbox.cy(), self.gcode_model.bbox.cz())
                scale = max(self.bed_width - self.gcode_model.bbox.xmin*2, self.gcode_model.bbox.dy(), self.gcode_model.bbox.dz())  / 75
            else:
                object_center = Vector3(self.gcode_model.bbox.cx(), self.gcode_model.bbox.cy(), self.gcode_model.bbox.cz())
                scale = max(self.gcode_model.bbox.dx(), self.gcode_model.bbox.dy(), self.gcode_model.bbox.dz())  / 75
        else:
            object_center = Vector3(self.bed_width/2, self.bed_depth/2, 0)
            scale = 1
        
        # Calculate the camera distance
        cam_dist = Vector3(self.camera_distance) * scale
        self.camera_position = (object_center + cam_dist).as_tuple()
        up = (0, 0, 1)

        # Calculate the lookat and projection matrices
        lookat = Matrix44.lookat(object_center, up, self.camera_position)
        projection = Matrix44.perspective_projection_fov(radians(45), float(self.width)/float(self.height), 0.1, 10000.0)

        # Calculate the camera matrix. This matrix translates and rotates all vertices, as such that it looks like the camera is brought in position
        self.camera_matrix = projection * lookat

        ccam = eglfloats(self.camera_matrix.to_opengl())

        # Upload the camera matrix to OpenGLES
        glUniformMatrix4fv(self.camera_handle, 1, GL_FALSE, ccam)

    def _render(self):
        """
        Does the main rendering of the bed and the part
        """

        # Define the vertices that make up the print bed. The vertices define two triangles that make up a square 
        # (squares are not directly supported in OpenGLES)
        self.logInfo("Load vertices")
        bedvertices = (   0, 0, 0,
                            0, self.bed_depth, 0,
                            self.bed_width, self.bed_depth, 0,
                            self.bed_width, self.bed_depth, 0,
                            self.bed_width, 0, 0,
                            0, 0, 0)
        cbedvertices = eglfloats(bedvertices)

        # Draw the bed in a similar way as the part, but without a VBO
        glUniform4f(self.color_handle, self.bed_color[0], self.bed_color[1], self.bed_color[2], 1.0)
        self.logInfo("Bed color %s" % hex(glGetError()))

        glVertexAttribPointer(self.position_handle, 3, GL_FLOAT, GL_FALSE, 0, cbedvertices) # 3 floats per vertex (x, y, z)
        self.logInfo("Bed vertex array %s" % hex(glGetError()))

        glEnableVertexAttribArray(self.position_handle)
        self.logInfo("Enable array %s" % hex(glGetError()))

        glDrawArrays ( GL_TRIANGLES, 0, 6 ) # 6 vertices make up two triangles, which make up 1 square
        self.logInfo("Draw bed array %s" % hex(glGetError()))

        glDisableVertexAttribArray(self.position_handle)
        self.logInfo("Disable array %s" % hex(glGetError()))
        
        # Get the part vertices 
        # cvertices is a one-dimensional array: [x1a y1a z1a x1b y1b z1b x2a y2a ... ], where the number refers to the line number and a/b to start/end of the line.
        # Thus each line consists out of 6 floats
        N = len(self.base_vertices)
        cvertices = self.base_vertices
        self.logInfo("Vertices loaded")

        # Set the shader's color parameter to the part color 
        glUniform4f(self.color_handle, self.part_color[0], self.part_color[1], self.part_color[2], 1.0)
        self.logInfo("Coloring: %s" % hex(glGetError()))
        self.logInfo("Color: {0} {1} {2}".format(*self.part_color))

        # Create a Vertex Buffer Object
        vbo = glGenBuffers(1)
        self.logInfo("VBO: %s" % vbo)

        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        self.logInfo("Bind buffer: %s" % hex(glGetError()))
        #self.logInfo("N vertices: %s" % N)
        #self.logInfo("Buffer size: %s" % ctypes.sizeof(cvertices))

        ## Fill the buffer with the vertices
        ## TODO: This loads the entire vertice buffer at once to the GPU mem. (May be 100s of mbs), may be try and load this sequentially in chuncks of x mb
        glBufferData(GL_ARRAY_BUFFER, cvertices, GL_STATIC_DRAW)
        self.logInfo("Buffer filled %s" % hex(glGetError()))
        
        # Now, load the VBO into the shader's position parameter
        glEnableVertexAttribArray(self.position_handle)
        glVertexAttribPointer(self.position_handle, 3, GL_FLOAT, GL_FALSE, 0, None) # The array consists of 3 items per vertex (x, y, z)
        self.logInfo("Set part vertex: %s" % hex(glGetError()))

        # The position parameter is set, now start drawing. Because of GL_LINES, 2 vertices are expected per line = cvertices->a and b
        glDrawArrays( GL_LINES , 0, N )
        self.logInfo("Draw part %s" % hex(glGetError()))

        #Remove the binding to the VBO
        glDisableVertexAttribArray(self.position_handle)
        self.logInfo("Disable vertex array %s" % hex(glGetError()))
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.logInfo("Disable buffer %s" % hex(glGetError()))

        glDeleteBuffers(1, vbo)
        self.logInfo("Delete buffer %s" % hex(glGetError()))

    def _updateCamera(self):
        """
        Sets the camera matrix to the given position
        """

        self.camera_matrix = Matrix44()

        # Lookat the center of the bed
        lookat = Matrix44.lookat((float(self.bed_width)/2, float(self.bed_depth)/2, 0), (0, 0, 1), (float(self.bed_width)/2, -100, 200))

        # Define the perspective of the camera
        projection = Matrix44.perspective_projection_fov(radians(90), float(self.width)/float(self.height), 0.1, 10000.0)

        # Calculate the camera matrix
        self.camera_matrix = projection * lookat

        # Upload the camera matrix to the shader
        ccam = eglfloats(self.camera_matrix.to_opengl())
        glUniformMatrix4fv(self.camera_handle, 1, GL_FALSE, ccam)
    
    def _setLight(self):
        """
        Sets the clear color and enables depth testing
        """
        #glLineWidth(3)
        glEnable(GL_DEPTH_TEST)
        self.logInfo("Enable depth test %s" % hex(glGetError()))
        glClearColor(1, 1, 1, 1)
        self.logInfo("Set clear color %s" % hex(glGetError()))

    def _setViewportAndPerspective(self):
        """
        Sets the width and height of the viewport
        """
        glViewport(0, 0, self.width, self.height)
        self.logInfo("Set viewport %s" % hex(glGetError()))

    def _getVertices(self):
        """
        Gets the vertices that make up the gcode model
        """
        return self.gcode_model.segments
