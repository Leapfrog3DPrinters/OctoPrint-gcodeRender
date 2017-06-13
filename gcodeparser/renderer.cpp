#include "Renderer.h"
#include "shader.h"
#include "shaders.h"

// Renderer constructor
// Width: width of the images to render
// Height: height of the images to render
Renderer::Renderer(unsigned int width, unsigned int height, unsigned int throttlingInterval, unsigned int throttlingDuration)
{
	this->width = width;
	this->height = height;

	this->throttlingDuration = throttlingDuration;
	this->throttlingInterval = throttlingInterval;

	this->renderContext = new T_RENDERCONTEXT(width, height);

	char log[512];

	if(throttlingInterval > 0 && throttlingDuration > 0)
		sprintf(log, "Renderer created. Image resolution: %dx%d. Throttling %d ms every %d lines.", width, height, throttlingDuration, throttlingInterval);
	else
		sprintf(log, "Renderer created. Image resolution: %dx%d. Throttling disabled.", width, height);

	log_msg(debug, log);
}


Renderer::~Renderer()
{
	unloadShaders(this->program, this->vertex_shader, this->fragment_shader);

	delete[] vertices;
	delete[] indices;
	delete parser;
	delete renderContext;
}

/* Public methods */

// Initialize the render context and, if used, GLEW
bool Renderer::initialize()
{
	// Reset the last error
	lastGlError = 0;

	log_msg(debug, "Initializing renderer");

	if (!renderContext->activate())
		return false;

#ifdef USE_GLEW
	if (glewInit() != GLEW_OK) {
		log_msg(error, "Failed to initialize GLEW");
		return false;
	}
#endif

	// Load and compile shaders and get handles to the shader variables
	log_msg(debug, "Creating program");
	this->createProgram();

	// Before every rendering, clear the buffer with this background color
	glClearColor(backgroundColor[0], backgroundColor[1], backgroundColor[2], backgroundColor[3]);
	checkGlError("Set clear color");

	// For the tubes rendering mode, we need an ambient light position
	if (drawType == DRAW_TUBES)
	{
		glUniform3f(light_handle, (printArea.xmax + printArea.xmin) / 2, -50.0, 300.0);
		checkGlError("Set light");
	}

	return lastGlError == 0;
}

// Set the print area and re-buffer the bed vertices
void Renderer::configurePrintArea(BBox * printArea)
{
	this->printArea = (*printArea);

	// Recreate bed buffer
	this->deleteBuffer(&bedBuffer);
	this->bufferBed();

	char log[128];
	sprintf(log, "Print area configured. Bounds: %.2f:%.2f %.2f:%.2f %.2f:%.2f", this->printArea.xmin, this->printArea.xmax, this->printArea.ymin, this->printArea.ymax, this->printArea.zmin, this->printArea.zmax);
	log_msg(debug, log);
}

// Configure where to position the camera and where to point it at
void Renderer::configureCamera(bool pointAtPart, float cameraDistance[3])
{
	this->pointCameraAtPart = pointAtPart;
	this->cameraDistance = glm::vec3(cameraDistance[0], cameraDistance[1], cameraDistance[2]);

	char log[128];
	sprintf(log, "Camera configured. Target: %s, distance: %.2f, %.2f, %.2f", pointCameraAtPart ? "part" : "bed", this->cameraDistance[0], this->cameraDistance[1], this->cameraDistance[2]);
	log_msg(debug, log);
}

// Configure the background color of the rendered image
void Renderer::configureBackgroundColor(float color[4])
{
	memcpy(this->backgroundColor, color, 4 * sizeof(float));
	
	glClearColor(backgroundColor[0], backgroundColor[1], backgroundColor[2], backgroundColor[3]);
	checkGlError("Set clear color");

	char log[64], colorStr[10];
	getColorHash(colorStr, color);
	sprintf(log, "Background color configured: %s", colorStr);
	log_msg(debug, log);
}

// Configure the color of the rendererd bed
void Renderer::configureBedColor(float color[4])
{
	memcpy(this->bedColor, color, 4 * sizeof(float));

	char log[64], colorStr[10];
	getColorHash(colorStr, color);
	sprintf(log, "Bed color configured: %s", colorStr);
	log_msg(debug, log);
}

// Configure the base color of the rendered part
void Renderer::configurePartColor(float color[4])
{
	memcpy(this->partColor, color, 4 * sizeof(float));

	char log[64], colorStr[10];
	getColorHash(colorStr, color);
	sprintf(log, "Part color configured: %s", colorStr);
	log_msg(debug, log);
}

// Render a gcode from a given gcodeFile in to a PNG imageFile
bool Renderer::renderGcode(const char * gcodeFile, const char* imageFile)
{
	// Reset the last error
	lastGlError = 0;
	
	// We can re-use the bed vertices, so lazy-load them once
	if (!bedBuffered)
	{	
		this->bufferBed();
		log_msg(debug, "Bed buffered");
	}


	// The origin offset is not included, as it is not considered a valid printing area
	// and thus should not be rendered.
	BBox bedBbox = { 0, printArea.xmax + printArea.xmin, 0, printArea.ymax + printArea.ymin, 0, printArea.zmax + printArea.zmin };
	this->parser = new GcodeParser(gcodeFile, this->drawType, bedBbox, this->throttlingInterval, this->throttlingDuration);

	// Create buffers for the vertex and index arrays
	unsigned int verticesSize, indicesSize;

	this->parser->get_buffer_size(&verticesSize, &indicesSize);

	vertices = new float[this->linesPerRun * verticesSize];
	indices = new short[this->linesPerRun * indicesSize];

	// Start with a clean slate and fill the image with the background color
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

	// Render the part to the pixel buffer (and set the camera after the first run)
	this->renderPart();
	log_msg(debug, "Part rendered");

	// Render the bed to the pixel buffer
	this->renderBed();
	log_msg(debug, "Bed rendered");

	// Save the contents of the pixel buffer to a file
	if(this->saveRender(imageFile))
		log_msg(debug, "File saved");

	// Clean up
	delete[] vertices;
	delete[] indices;
	delete this->parser;

	return lastGlError == 0;
}

/* Private methods */

// Create a GPU shader program and create handles to the shader's variables
void Renderer::createProgram()
{
	// Compile the shaders
	if (drawType == DRAW_LINES)
		loadShaders(line_vertexshader, line_fragmentshader, &(this->program), &(this->vertex_shader), &(this->fragment_shader));
	else
		loadShaders(tube_vertexshader, tube_fragmentshader, &(this->program), &(this->vertex_shader), &(this->fragment_shader));

	// Get handles to the shader's variables
	position_handle = glGetAttribLocation(program, "vertexPosition_modelspace");
	checkGlError("Get position handle");

	color_handle = glGetUniformLocation(program, "ds_Color");
	checkGlError("Get color handle");

	camera_handle = glGetUniformLocation(program, "MVP");
	checkGlError("Get camera handle");

	// For the fragment shader that uses normals to create better lighting 
	// provide additional handles
	if (drawType == DRAW_TUBES)
	{
		light_handle = glGetUniformLocation(program, "LightPosition_worldspace");
		checkGlError("Get light handle");

		normal_handle = glGetAttribLocation(program, "vertexNormal_modelspace");
		checkGlError("Get normal handle");

		m_handle = glGetUniformLocation(program, "M");
		checkGlError("Get model-matrix handle");

		v_handle = glGetUniformLocation(program, "V");
		checkGlError("Get view-matrix handle");
	}

	// Enable the shader program
	glUseProgram(program);
	checkGlError("Use program");

	// Enable depth tests (this requires the context to have depth buffer)
	// prevents the bed from colliding with the part
	glEnable(GL_DEPTH_TEST);
	checkGlError("Enable depth test");
}

// Create a vertex buffer object using the given vertices 
// and indices of the vertices that make up the fragments (lines, triangles etc.)
void Renderer::buffer(const int nVertices, const float * vertices, const int nIndices, const short * indices, BufferInfo * bufferInfo)
{
	int vertexBuffer_size = nVertices * sizeof(float);
	int indexBuffer_size = nIndices * sizeof(short);

	GLuint vbo, ivbo, vertexArray;

#ifdef NEED_VERTEX_ARRAY_OBJECT

	glGenVertexArrays(1, &vertexArray);
	checkGlError("gen vertex array");

	glBindVertexArray(vertexArray);
	checkGlError("bind vertex array");
#endif

	// Create a buffer
	glGenBuffers(1, &vbo);
	checkGlError("generate vertex buffer");
	glBindBuffer(GL_ARRAY_BUFFER, vbo);
	checkGlError("bind vertex buffer");

	// Load the vertices
	glBufferData(GL_ARRAY_BUFFER, vertexBuffer_size, vertices, GL_STATIC_DRAW);
	checkGlError("Vertex buffer data");

	// Create another buffer
	glGenBuffers(1, &ivbo);
	checkGlError("generate index buffer");
	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ivbo);
	checkGlError("bind index buffer");

	// Load the indices
	glBufferData(GL_ELEMENT_ARRAY_BUFFER, indexBuffer_size, indices, GL_STATIC_DRAW);
	checkGlError("index buffer data");

	// Save links to the buffers in a bufferInfo struct
	(*bufferInfo).nVertices = nVertices;
	(*bufferInfo).nIndices = nIndices;
	(*bufferInfo).vertexBuffer = vbo;
	(*bufferInfo).indexBuffer = ivbo;
	(*bufferInfo).vertexArray = vertexArray;

	// Count how much data we're buffering
	memoryUsed += vertexBuffer_size + indexBuffer_size;
}

// Clear a buffer from the GPU memory
void Renderer::deleteBuffer(BufferInfo * bufferInfo)
{
	// Unwire
	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0);
	checkGlError("Unbind element array buffer");

	glBindBuffer(GL_ARRAY_BUFFER, 0);
	checkGlError("Unbind vertex array buffer");

	// Delete buffers
	GLuint toDelete[] = { (*bufferInfo).vertexBuffer, (*bufferInfo).indexBuffer };
	glDeleteBuffers(2, toDelete);
	checkGlError("Delete buffers");

#ifdef NEED_VERTEX_ARRAY_OBJECT
	glBindVertexArray(0);
	checkGlError("Unbind vertex array");

	glDeleteVertexArrays(1, &(*bufferInfo).vertexArray);
	checkGlError("Delete vertex array");
#endif
}

// Draws a vertex buffer object to the render buffer
void Renderer::draw(const float color[4], BufferInfo * bufferInfo, GLenum element_type)
{
	// Set the base color of the fragments to be drawn
	glUniform4fv(color_handle, 1, color);
	checkGlError("Set color");

#ifdef NEED_VERTEX_ARRAY_OBJECT
	glBindVertexArray((*bufferInfo).vertexArray);
	checkGlError("bind vertex array");
#endif

	// Allow the shader's position variable to accept vertex buffers
	glEnableVertexAttribArray(position_handle);
	checkGlError("Enable vertex array position");

	if (drawType == DRAW_TUBES)
	{
		// Allow the shader's normals variable to accept vertex buffers
		glEnableVertexAttribArray(normal_handle);
		checkGlError("Enable vertex array normals");
	}

	// Bind to the vertex buffer
	glBindBuffer(GL_ARRAY_BUFFER, (*bufferInfo).vertexBuffer);
	checkGlError("Bind buffer");

	// Wire the vertex buffer to the position variable, and if needed, to the normals variable
	if (drawType == DRAW_TUBES)
	{	
		glVertexAttribPointer(position_handle, 3, GL_FLOAT, GL_FALSE, sizeof(float) * 6, (void*)0);
		checkGlError("Position pointer");

		glVertexAttribPointer(normal_handle, 3, GL_FLOAT, GL_FALSE, sizeof(float) * 6, (void*)(3 * sizeof(float)));
		checkGlError("Normal pointer");
	}
	else
	{
		glVertexAttribPointer(position_handle, 3, GL_FLOAT, GL_FALSE, sizeof(float) * 3, (void*)0);
		checkGlError("Position pointer");
	}

	// Bind to the vertex elements buffer (containing the indices of the vertices to draw) 
	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, (*bufferInfo).indexBuffer);
	checkGlError("Bind elements");

	// Draw the vertices from the given indices
	// Note: OpenGL ES is limited to using shorts
	glDrawElements(element_type, (*bufferInfo).nIndices, GL_UNSIGNED_SHORT, (void*)0);
	checkGlError("Draw");

	// Unwire buffers
	glDisableVertexAttribArray(position_handle);
	checkGlError("Disable position array");

	if (drawType == DRAW_TUBES)
	{
		glDisableVertexAttribArray(normal_handle);
		checkGlError("Disable normal array");
	}
}

// Sets the camera 
void Renderer::setCamera()
{
	BBox bbox = BBox();

	glm::vec3 cameraPosition, cameraTarget;

	// Start with a field-of-view for the camera of 20 deg
	float fov_deg = 20.0f;
	
	if (parser->get_bbox(&bbox))
	{
		// Never go below this fov
		float fov_deg_min = 5.0f;

		if (this->pointCameraAtPart)
		{
			// Point to the middle of the part
			cameraTarget = glm::vec3((bbox.xmax + bbox.xmin) / 2, (bbox.ymax + bbox.ymin) / 2, (bbox.zmax + bbox.zmin) / 2);

			// TODO: Determine the FOV based on the bounding box and camera angle
			float part_width = bbox.xmax - bbox.xmin;
			float part_depth = bbox.ymax - bbox.ymin;

			// Range offset from 0.0 (empty part), to 1.0 (full bed used, widest angle needed)
			float x_factor = part_width / printArea.width();
			float y_factor = part_depth / printArea.depth();

			// Use the biggest factor and scale to max 60 degrees (which is ~ the whole bed)
			float factor_max = max(x_factor, y_factor);
			fov_deg = max(fov_deg_min, factor_max * 60.0f);

		}
		else
		{
			// Point to the middle of the bed
			cameraTarget = glm::vec3(printArea.center_x(), printArea.center_y(), 0);

			// Narrow or widen FOV

			// Minimal smallest offset to bed edges
			float x_offset_min = min(printArea.xmin - bbox.xmin, printArea.xmax - bbox.xmax);
			float y_offset_min = min(printArea.ymin - bbox.ymin, printArea.ymax - bbox.ymax);

			// Range offset from 0.0 (center of bed, smallest possible angle), to 1.0 (full bed used, widest angle needed)
			float x_factor = 1.0f - x_offset_min / (printArea.width() / 2);
			float y_factor = 1.0f - y_offset_min / (printArea.depth() / 2);

			// Use the biggest factor and scale to max 60 degrees (which is ~ the whole bed)
			float factor_max = max(x_factor, y_factor);

			fov_deg = max(fov_deg_min, factor_max * 60.0f);
		}
	}
	else
	{
		// We don't have a valid bounding box of the part
		// Point to the middle of the bed
		cameraTarget = glm::vec3(printArea.center_x(), printArea.center_y(), 0);
	}

	// Move the camera away from the target
	cameraPosition = cameraTarget + cameraDistance;

	// Define the matrices that transform vertices to pixels
	glm::mat4 mvp, projection, view, model;
	glm::vec3 up = glm::vec3(0, 0, 1); // +Z is pointing upwards
	model = glm::mat4(1.0f); // We don't need to transform the model
	view = glm::lookAt(cameraPosition, cameraTarget, up);
	projection = glm::perspective<float>(glm::radians(fov_deg), width / (float)height, 0.1f, 1000.0f);

	mvp = projection * view * model;

	// Upload the camera matrix to OpenGL(ES)
	glUniformMatrix4fv(camera_handle, 1, GL_FALSE, &mvp[0][0]);
	checkGlError("Set camera matrix");

	// Provide additional matrices for the fragment shader that uses lighting
	if (drawType == DRAW_TUBES)
	{
		glUniformMatrix4fv(m_handle, 1, GL_FALSE, &model[0][0]);
		checkGlError("Set model matrix");
		glUniformMatrix4fv(v_handle, 1, GL_FALSE, &view[0][0]);
		checkGlError("Set view matrix");
	}
}

// Create vertex buffer for the bed
void Renderer::bufferBed()
{
	int bedvertices_n;
	float * bedvertices;

	// X, y, z, nx, ny, nz
	if (drawType == DRAW_TUBES)
	{
		bedvertices_n = 24;
		bedvertices = new float[bedvertices_n] {
			printArea.xmin, printArea.ymin, 0, 0, 0, 1.0f,
			printArea.xmin, printArea.ymax, 0, 0, 0, 1.0f,
			printArea.xmax, printArea.ymax, 0, 0, 0, 1.0f,
			printArea.xmax, printArea.ymin, 0, 0, 0, 1.0f
		};
	}
	else
	{
		bedvertices_n = 12;
		bedvertices = new float[bedvertices_n] {
			printArea.xmin, printArea.ymin, 0,
			printArea.xmin, printArea.ymax, 0,
			printArea.xmax, printArea.ymax, 0,
			printArea.xmax, printArea.ymin, 0,
		};
	}

	const int bedindices_n = 6;
	short bedindices[bedindices_n] = { 0, 1, 2, 2, 3, 0 };

	buffer(bedvertices_n, bedvertices, bedindices_n, bedindices, &bedBuffer);
	bedBuffered = true;

	delete[] bedvertices;
}

// (Buffer and) render the bed to the pixel buffer
void Renderer::renderBed()
{
	draw(bedColor, &bedBuffer, GL_TRIANGLES);
}

// Read the part vertices from the gcode and render it to the pixel buffer
void Renderer::renderPart()
{
	log_msg(debug, "Begin rendering part");

	// Reset the amount of memory we have used
	memoryUsed = 0;

	// Keep pointers to what we need to render
	int nVertices, nIndices;
	BufferInfo buff;

	// Extract vertices from the first n lines of gcode
	int nParsed = parser->get_vertices(linesPerRun, &nVertices, vertices, &nIndices, indices);

	if (nParsed == -1)
	{
		log_msg(error, "Could not parse gcode file. Does the file exist?");
		return;
	}

	if (nParsed == 0)
	{
		log_msg(debug, "Nothing to parse");
		return;
	}
		
	// Store them in the GPU
	buffer(nVertices, vertices, nIndices, indices, &buff);

	// The bounding box of the first layer is sufficient for our needs (set the camera FOV)
	// so at this point (before we rendered anything) we can point the camera
	// in the right direction
	this->setCamera();

	// With the camera in place we can start drawing
	if (drawType == DRAW_LINES)
		draw(partColor, &buff, GL_LINES);
	else
		draw(partColor, &buff, GL_TRIANGLES);
	
	// Free some space
	deleteBuffer(&buff);

	// Continue to read, buffer and draw the rest of the gcode file
	while (parser->get_vertices(linesPerRun, &nVertices, vertices, &nIndices, indices) > 0)
	{
		buffer(nVertices, vertices, nIndices, indices, &buff);

		if (drawType == DRAW_LINES)
			draw(partColor, &buff, GL_LINES);
		else
			draw(partColor, &buff, GL_TRIANGLES);

		deleteBuffer(&buff);
	}

	// Log how much GPU memory we used to draw this part
	char resp[512];
	sprintf(resp, "Total data processed: %ld kb", memoryUsed / 1000);
	log_msg(debug, resp);
}

// Reads the pixel buffer and encodes the data into a PNG file
bool Renderer::saveRender(const char* imageFile)
{
	// Wait for all commands to complete before we read the buffer
	glFlush();
	glFinish();

	// Create a buffer for the pixel data
	const int n = 4 * width*height;
	uint8_t *imgData = new uint8_t[n];

	// Read the pixels from the buffer
	glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, imgData);
	if (checkGlError("glReadPixels"))
	{
		log_msg(error, "Couldn't read pixels from Open GL pixel buffer");
		delete[] imgData;
		return false;
	}

	if (!writePng(imageFile, imgData, width, height))
	{
		log_msg(error, "Couldn't save image data to PNG file");
		delete[] imgData;
		return false;
	}

	delete[] imgData;
	return true;
}

// Check for any errors from the OpenGL API and log them.
// Returns true if an error occured
bool Renderer::checkGlError(const char* part)
{
	GLenum error = glGetError();

	if (error != 0)
	{
		lastGlError = error;

		char desc[1024];
		sprintf(desc, "Error: %s %04x", part, error);
		log_msg(error, desc);
		return true;
	}
	else
	{
		return false;
	}
}
