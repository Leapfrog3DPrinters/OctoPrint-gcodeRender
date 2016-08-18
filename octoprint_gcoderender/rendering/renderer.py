import sys

from math import *

if sys.platform == "win32" or sys.platform == "darwin":
    from OpenGL.GL import *
    from OpenGL.GLU import *
    import pygame
    from pygame.locals import *
else:
    from pyopengles import *
    # TODO: Define these inside pyopendles
    GL_VERTEX_ARRAY = 0x8074

from gcodeparser import *

from matrix44 import *
from vector3 import *

from PIL import Image
from datetime import datetime

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

#TODO: implement shared logic of win/linux
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

class RendererOpenGLES(Renderer):
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
        self.ctx = None
        self.position_handle = None
        self.color_handle = None
        self.camera_handle = None
                
    def initialize(self, bedWidth, bedDepth, width = DEFAULT_WIDTH, height = DEFAULT_HEIGHT, showWindow = False,  backgroundColor = None, partColor = None, bedColor = None, cameraPosition = None, cameraRotation = None):
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
        self._setViewportAndPerspective()
        self._setLighting()

        self.is_initialized = True

    def close(self):
        if not self.is_initialized or not self.is_window_open:
            return
        
        self.ctx.close()

    def renderModel(self, gcodeFile, bringCameraInPosition = False):
        if not self.is_initialized or not self.is_window_open:
            return

        # Parse the file
        parser = GcodeParser(verbose = self.verbose)
        self.gcode_model = parser.parseFile(gcodeFile)

        if self.gcode_model.syncOffset > 0:
            self.sync_offset = self.gcode_model.syncOffset
        
        self.base_vertices = self._getVertices()

        self._clearAll()
        self._setLight()

        if bringCameraInPosition:
            self._bringCameraInPosition()
        else:
            self._updateCamera()
        self._prepareDisplayList()        
        self._renderDisplayList()

        if self.is_window_open:
            time.sleep(3)


    def clear(self):
        if not self.is_initialized or not  self.is_window_open:
            return

        self._clearAll()
        self._renderBed()
    
    def save(self, imageFile):
        if not self.is_initialized or not self.is_window_open:
            return

        # Create Buffer
        N = self.width*self.height*4
        data = (ctypes.c_uint8*N)()

        # Read all pixel colors
        opengles.glReadPixels(0,0,self.width,self.height,GL_RGBA,GL_UNSIGNED_BYTE, ctypes.byref(data))
        
        # Write raw data to image file
        imgSize = (self.width, self.height)
        img = Image.frombytes('RGBA', imgSize, data)
        img.transpose(Image.FLIP_TOP_BOTTOM).save(imageFile)

    def _initFrameBuffer(self):
        self.fbo = ctypes.c_uint()
        self.color_buf = ctypes.c_uint()
        self.depth_buf = ctypes.c_uint()

        # Framebuffer
        opengles.glGenFramebuffers(1,self.fbo)
        opengles.glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        
        #Colorbuffer
        opengles.glGenRenderbuffers(1,self.color_buf)
        opengles.glBindRenderbuffer(GL_RENDERBUFFER, self.color_buf)
        opengles.glRenderbufferStorage(GL_RENDERBUFFER, GL_RGBA8, self.width, self.height)
        opengles.glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_RENDERBUFFER, self.color_buf)

        #Depthbuffer
        opengles.glGenRenderbuffers(1, self.depth_buf)
        opengles.glBindRenderbuffer(GL_RENDERBUFFER, self.depth_buf)
        opengles.glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, self.width, self.height)
        opengles.glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, self.depth_buf)

    def _deinitFrameBuffer(self):
       opengles.glDeleteRenderbuffersEXT(1, self.color_buffer)
       opengles.glDeleteRenderbuffersEXT(1, self.depth_buffer)
       opengles.glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)
       opengles.glDeleteFramebuffersEXT(1, self.fbo)

    def _bringCameraInPosition(self):

        if self.gcode_model.bbox:
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
        
        cam_dist = Vector3(self.camera_distance) * scale
        self.camera_position = (object_center + cam_dist).as_tuple()
        up = (0, 0, 1)

        lookat = Matrix44.lookat(object_center, up, self.camera_position)
        projection = Matrix44.perspective_projection_fov(radians(45), float(self.width)/float(self.height), 0.1, 10000.0)

        self.camera_matrix = projection * lookat

        ccam = eglfloats(self.camera_matrix.to_opengl())

        opengles.glUniformMatrix4fv(self.camera_handle, 1, GL_FALSE, ccam)

        # Light must be transformed as well
        self._setLight()

    def _openWindow(self):
        if self.is_window_open:
            return
        
        self._openWindowPi()

        self.is_window_open = True

    def _openWindowPi(self):

        self.ctx = EGL(depth_size = 8)

        vertex_shader = """
            uniform mat4 uCamera; 
            attribute vec4 aPosition;
            void main()
            {
                gl_Position = uCamera * aPosition;
            }
        """

        fragment_shader = """
            precision mediump float;
            uniform vec4 uColor;

            void main()
            {
                gl_FragColor = uColor;
            }
        """

        binding = ((5, 'aPosition'),)
        
        self.program = self.ctx.get_program(vertex_shader, fragment_shader, binding, False)
        self.logInfo("Program: %s" % self.program)
        self.position_handle = opengles.glGetAttribLocation(self.program, "aPosition")
        self.logInfo("Position handle: %s" % self.position_handle)
        self.color_handle = opengles.glGetUniformLocation(self.program, "uColor")
        self.logInfo("Color handle: %s" % self.color_handle)
        self.camera_handle = opengles.glGetUniformLocation(self.program, "uCamera")
        self.logInfo("Camera handle: %s" % self.camera_handle)

        opengles.glUseProgram(self.program)
        self.logInfo("Use program: %s" % hex(opengles.glGetError()))

    def _clearAll(self):
        opengles.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    def _renderDisplayList(self):
        
        # Update the window
        opengles.glFlush()
        opengles.glFinish()

        if self.show_window:
            openegl.eglSwapBuffers(self.ctx.display, self.ctx.surface)
        

    def _prepareDisplayList(self):
        self.logInfo("Load vertices")
        bedvertices = (   0, 0, 0,
                            0, self.bed_depth, 0,
                            self.bed_width, self.bed_depth, 0,
                            self.bed_width, self.bed_depth, 0,
                            self.bed_width, 0, 0,
                            0, 0, 0)
        cbedvertices = eglfloats(bedvertices)
        
        N = len(self.base_vertices)
        cvertices = self.base_vertices
        self.logInfo("Vertices loaded")
        # Draw part
        opengles.glUniform4f(self.color_handle, eglfloat(self.part_color[0]), eglfloat(self.part_color[1]), eglfloat(self.part_color[2]), eglfloat(1.0))
        self.logInfo("Coloring: %s" % hex(opengles.glGetError()))
        self.logInfo("Color: {0} {1} {2}".format(*self.part_color))
        opengles.glEnableClientState(GL_VERTEX_ARRAY)
        self.logInfo("Client state")
        vbo = eglint()
        opengles.glGenBuffers(1,ctypes.byref(vbo))
        self.logInfo("VBO: %s" % vbo.value)
        opengles.glBindBuffer(GL_ARRAY_BUFFER, vbo)
        self.logInfo("Bind buffer: %s" % hex(opengles.glGetError()))
        self.logInfo("N vertices: %s" % N)
        self.logInfo("Buffer size: %s" % ctypes.sizeof(cvertices))
        opengles.glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(cvertices), ctypes.byref(cvertices), GL_STATIC_DRAW)
        self.logInfo("Buffer filled %s" % hex(opengles.glGetError()))
        #opengles.glEnableVertexAttribArray(self.position_handle)
        self.logInfo("Enable part vertex: %s" % hex(opengles.glGetError()))
        opengles.glBindBuffer(GL_ARRAY_BUFFER, vbo)
        self.logInfo("Bind buffer: %s" % hex(opengles.glGetError()))
        opengles.glEnableVertexAttribArray(self.position_handle)
        opengles.glVertexAttribPointer(self.position_handle, 3, GL_FLOAT, GL_FALSE, 0, 0)
        #opengles.glEnableVertexAttribArray(self.position_handle)
        self.logInfo("Set part vertex: %s" % hex(opengles.glGetError()))
        opengles.glBindBuffer(GL_ARRAY_BUFFER, vbo)
        opengles.glDrawArrays( GL_LINES , 0, N/3 )
        self.logInfo("Draw part tri %s" % hex(opengles.glGetError()))
        opengles.glDisableVertexAttribArray(self.position_handle)
        self.logInfo("Disable vertex array %s" % hex(opengles.glGetError()))
        opengles.glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.logInfo("Disable buffer %s" % hex(opengles.glGetError()))
        
        # Draw bed
        opengles.glUniform4f(self.color_handle, eglfloat(self.bed_color[0]), eglfloat(self.bed_color[1]), eglfloat(self.bed_color[2]), eglfloat(1.0))
        self.logInfo("Bed color %s" % hex(opengles.glGetError()))
        opengles.glVertexAttribPointer(self.position_handle, 3, GL_FLOAT, GL_FALSE, 0, cbedvertices)
        self.logInfo("Bed vertex array %s" % hex(opengles.glGetError()))
        opengles.glEnableVertexAttribArray(self.position_handle)
        self.logInfo("Enable array %s" % hex(opengles.glGetError()))
        opengles.glDrawArrays ( GL_TRIANGLES, 0, 6 )
        self.logInfo("Draw bed array %s" % hex(opengles.glGetError()))
        opengles.glDisableVertexAttribArray(self.position_handle)
        self.logInfo("Disable array %s" % hex(opengles.glGetError()))
        opengles.glDeleteBuffers(1, ctypes.byref(vbo))
        self.logInfo("Delete buffer %s" % hex(opengles.glGetError()))

    def _updateCamera(self):
        
        self.camera_matrix = Matrix44()

        lookat = Matrix44.lookat((float(self.bed_width)/2, float(self.bed_depth)/2, 0), (0, 0, 1), (float(self.bed_width)/2, -100, 200))
        projection = Matrix44.perspective_projection_fov(radians(90), float(self.width)/float(self.height), 0.1, 10000.0)

        self.camera_matrix = projection * lookat

        ccam = eglfloats(self.camera_matrix.to_opengl())

        opengles.glUniformMatrix4fv(self.camera_handle, 1, GL_FALSE, ccam)

        # Light must be transformed as well
        self._setLight()

    
    def _setLight(self):
        light_ambient =  0.0, 0.0, 0.0, 1.0 
        light_diffuse =  1.0, 1.0, 1.0, 1.0 
        light_specular =  1.0, 1.0, 1.0, 1.0 
        light_position = 1.0, 1.0, 1.0, 0.0 

        mat_specular = 1.0, 1.0, 1.0, 1.0 
        mat_shininess =  50.0 

    def _setViewportAndPerspective(self):
        # Set viewport
        opengles.glViewport(0, 0, self.width, self.height)
        self.logInfo("Set viewport %s" % hex(opengles.glGetError()))

    def _setLighting(self):
        opengles.glEnable(GL_DEPTH_TEST)
        self.logInfo("Enable depth test %s" % hex(opengles.glGetError()))
        opengles.glClearColor(eglfloat(1.), eglfloat(1.), eglfloat(1.), eglfloat(1.))
        self.logInfo("Set color %s" % hex(opengles.glGetError()))

    def _getVertices(self):
        return self.gcode_model.segments

class RendererOpenGL(Renderer):
    def __init__(self, verbose = False):
        Renderer.__init__(self, verbose)
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
        self.clock = pygame.time.Clock()
        self.ctx = None
        self.program = None
                
    def initialize(self, bedWidth, bedDepth, width = DEFAULT_WIDTH, height = DEFAULT_HEIGHT, showWindow = False,  backgroundColor = None, partColor = None, bedColor = None, cameraPosition = None, cameraRotation = None):
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
        self._setViewportAndPerspective()
        self._setLighting()
        self._clearAll()
        self._updateCamera()

        self.is_initialized = True

    def close(self):
        if not self.is_initialized or not self.is_window_open:
            return
        
        pygame.display.quit()

    def renderModel(self, gcodeFile, bringCameraInPosition = False):
        if not self.is_initialized or not self.is_window_open:
            return

        # Parse the file
        self.logInfo("Parsing started")
        parser = GcodeParser(self.verbose)
        self.gcode_model = parser.parseFile(gcodeFile)
        self.logInfo("Parsing completed")
        if self.gcode_model.syncOffset > 0:
            self.sync_offset = self.gcode_model.syncOffset

        self.base_vertices = self._getVertices()
        self.logInfo("Rendering started")
        self._clearAll()
        self._setLight()
        self._prepareDisplayList()        

        if bringCameraInPosition:
            self._bringCameraInPosition()

        if self.show_window:
            while True:
                self._handleEvents()
                self._clearAll()
                self._setLight()
                self._renderDisplayList()
        else:
            self._initFrameBuffer()
            self._clearAll()
            self._setLight()
            self._renderDisplayList()
        self.logInfo("Rendering complete")


    def clear(self):
        if not self.is_initialized or not  self.is_window_open:
            return

        self._clearAll()
        self._renderBed()
    
    def save(self, imageFile):
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

    def _initFrameBuffer(self):
        self.fbo = ctypes.c_uint()
        self.color_buf = ctypes.c_uint()
        self.depth_buf = ctypes.c_uint()

        # Framebuffer
        glGenFramebuffers(1,self.fbo)
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        
        #Colorbuffer
        glGenRenderbuffers(1,self.color_buf)
        glBindRenderbuffer(GL_RENDERBUFFER, self.color_buf)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_RGBA8, self.width, self.height)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_RENDERBUFFER, self.color_buf)

        #Depthbuffer
        glGenRenderbuffers(1, self.depth_buf)
        glBindRenderbuffer(GL_RENDERBUFFER, self.depth_buf)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, self.width, self.height)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, self.depth_buf)

    def _deinitFrameBuffer(self):
       glDeleteRenderbuffersEXT(1, self.color_buffer)
       glDeleteRenderbuffersEXT(1, self.depth_buffer)
       glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)
       glDeleteFramebuffersEXT(1, self.fbo)

    def _bringCameraInPosition(self):

        if self.gcode_model.bbox:
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

        cam_dist = Vector3(self.camera_distance) * scale
        self.camera_position = (object_center + cam_dist).as_tuple()

        up = (0, 0, 1)

        glLoadIdentity()
        gluLookAt(self.camera_position[0], self.camera_position[1], self.camera_position[2],
                    object_center[0], object_center[1], object_center[2], 
                    up[0], up[1], up[2])

    def _handleEvents(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                return
            if event.type == KEYUP and event.key == K_ESCAPE:
                return

        pressed = pygame.key.get_pressed()

        # Reset rotation and movement directions
        self.rotation_direction.set(0.0, 0.0, 0.0)
        self.movement_direction.set(0.0, 0.0, 0.0)

        # Modify direction vectors for key presses
        if pressed[K_LEFT]:
            self.rotation_direction.y = +1.0
        elif pressed[K_RIGHT]:
            self.rotation_direction.y = -1.0
        if pressed[K_UP]:
            self.rotation_direction.x = +1.0
        elif pressed[K_DOWN]:
            self.rotation_direction.x = -1.0
        if pressed[K_z]:
            self.rotation_direction.z = +1.0
        elif pressed[K_x]:
            self.rotation_direction.z = -1.0
        if pressed[K_q]:
            self.movement_direction.z = -1.0
        elif pressed[K_a]:
            self.movement_direction.z = +1.0
        
        self._updateCameraForEvents()

    def _openWindow(self):
        if self.is_window_open:
            return
                
        pygame.init()

        if not self.show_window:
            pygame.display.iconify()

        pygame.display.set_mode((self.width, self.height), HWSURFACE|OPENGL|DOUBLEBUF)

        self.is_window_open = True

    def _clearAll(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    def _renderDisplayList(self):
        glCallList(self.display_list)
        
        # Update the window
        pygame.display.flip()
        

    def _prepareDisplayList(self):
        
        # Prepare batch
        self.display_list = glGenLists(1)    
        glNewList(self.display_list, GL_COMPILE)
    
        # Render all vertices
        glLineWidth(1)
        glColor( self.part_color )      
        glBegin(GL_LINES)
        for i in xrange(0, len(self.base_vertices), 3):
            glVertex((self.base_vertices[i], self.base_vertices[i+1], self.base_vertices[i+2]))     

        glEnd()
        
        #Render bed
        glColor( self.bed_color )       

        glBegin(GL_QUADS)
            
        glVertex(0, 0, 0)
        glVertex(0, self.bed_depth, 0)
        glVertex(self.bed_width, self.bed_depth, 0)
        glVertex(self.bed_width, 0, 0)

        glEnd()

        # Send batch
        glEndList()

    def _updateCamera(self):
        
        # Calculate camera matrix
        self.camera_matrix = Matrix44()
        self.camera_matrix.translate = self.camera_position
        self.rotation_matrix = Matrix44.xyz_rotation(*self.camera_rotation)
        self.camera_matrix *= self.rotation_matrix
        
        # Upload camera matrix
        glLoadMatrixd(self.camera_matrix.get_inverse().to_opengl())
        
        # Light must be transformed as well
        self._setLight()

    def _updateCameraForEvents(self):
        time_passed = self.clock.tick()
        time_passed_seconds = time_passed / 1000.

        if self.rotation_direction.x <> 0 or self.rotation_direction.y <> 0 or self.rotation_direction.z <> 0:
            # Calculate rotation matrix and multiply by camera matrix
            rotation = self.rotation_direction * self.rotation_speed * time_passed_seconds
            self.camera_rotation += rotation
        
            self.rotation_matrix = Matrix44.xyz_rotation(*rotation)
            self.camera_matrix *= self.rotation_matrix

            # Calcluate movment and add it to camera matrix translate
            heading = Vector3(self.camera_matrix.forward)
            movement = heading * self.movement_direction.z * self.movement_speed * time_passed_seconds
            self.camera_position += movement
            self.camera_matrix.translate += movement 

            # Upload camera matrix
            glLoadMatrixd(self.camera_matrix.get_inverse().to_opengl())

    def _setLight(self):
        light_ambient =  0.0, 0.0, 0.0, 1.0 
        light_diffuse =  1.0, 1.0, 1.0, 1.0 
        light_specular =  1.0, 1.0, 1.0, 1.0 
        light_position = 1.0, 1.0, 1.0, 0.0 

        mat_specular = 1.0, 1.0, 1.0, 1.0 
        mat_shininess =  50.0 


        glLight(GL_LIGHT0, GL_AMBIENT, light_ambient);
        glLight(GL_LIGHT0, GL_DIFFUSE, light_diffuse);
        glLight(GL_LIGHT0, GL_SPECULAR, light_specular);
        glLight(GL_LIGHT0, GL_POSITION, light_position);

        glMaterial(GL_FRONT, GL_SPECULAR, mat_specular);
        glMaterial(GL_FRONT, GL_SHININESS, mat_shininess);

        glLight(GL_LIGHT0, GL_POSITION,  (0, 0, 1, 0))

    def _setViewportAndPerspective(self):
        # Set viewport
        glViewport(0, 0, self.width, self.height)

        # Set projection
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, float(self.width)/self.height, 0.1, 1000.)

        # Reset mode, so camera may be adjusted
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def _setLighting(self):
        glEnable(GL_DEPTH_TEST)
        glShadeModel(GL_SMOOTH)

        glClearColor(1.0, 1.0, 1.0, 0.0)

        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LINE_SMOOTH)

        glLight(GL_LIGHT0, GL_POSITION,  (0, 1, 1, 0))

    def _getVertices(self):
        return self.gcode_model.segments

