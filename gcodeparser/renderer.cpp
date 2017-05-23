#include "Renderer.h"

Renderer::Renderer(int width, int height)
{
	this->width = width;
	this->height = height;

	this->renderContext = new T_RENDERCONTEXT(width, height);

	std::vector<buffer_info> buffers;
}

Renderer::~Renderer()
{
#ifdef NEED_VERTEX_ARRAY_OBJECT
	glBindVertexArray(0);
	assert_error("Unbind vertex array");

	glDeleteVertexArrays(1, &vertex_array);
	assert_error("Delete vertex array");
#endif

	UnloadShaders(this->program, this->vertex_shader, this->fragment_shader);

	delete[] vertices;
	delete[] indices;
	delete parser;
	delete renderContext;
}

void Renderer::assert_error(const char* part)
{
	GLenum error = glGetError();

	if (error != 0)
	{
		//const char* description = (char*)glewGetErrorString(error);
		char desc[1024];
		sprintf(desc, "Error: %s %04x\n", part, error);
		log_msg(error, desc);
	}
}

void Renderer::initialize()
{
	log_msg(debug, "Initializing renderer\n");
	renderContext->activate();

#ifdef USE_GLEW
	if (glewInit() != GLEW_OK) {
		log_msg(error, "Failed to initialize GLEW\n");
		return;
	}
#endif

	log_msg(debug, "Creating program\n");
	this->createProgram();

	glClearColor(background_color[0], background_color[1], background_color[2], background_color[3]);
	assert_error("Set clear color");

	if (draw_type == DRAW_TUBES)
	{
		glUniform3f(light_handle, bed_width / 2, -50.0, 300.0);
		assert_error("Set light");
	}

#ifdef NEED_VERTEX_ARRAY_OBJECT

	glGenVertexArrays(1, &vertex_array);
	assert_error("gen vertex array");

	glBindVertexArray(vertex_array);
	assert_error("bind vertex array");
#endif

	this->bufferBed();
	log_msg(debug, "Bed buffered\n");
}

void Renderer::draw(const float color[4], GLuint ivbo, GLuint vbo, int n, GLenum element_type)
{
	glUniform4fv(color_handle, 1, color);
	assert_error("Set color");

	glEnableVertexAttribArray(position_handle);
	assert_error("Enable vertex array position");

	if (draw_type == DRAW_TUBES)
	{
		glEnableVertexAttribArray(normal_handle);
		assert_error("Enable vertex array normals");
	}

	glBindBuffer(GL_ARRAY_BUFFER, vbo);
	assert_error("Bind buffer");

	if (draw_type == DRAW_TUBES)
	{
		glVertexAttribPointer(position_handle, 3, GL_FLOAT, GL_FALSE, sizeof(float) * 6, (void*)0);
		assert_error("Position pointer");

		glVertexAttribPointer(normal_handle, 3, GL_FLOAT, GL_FALSE, sizeof(float) * 6, (void*)(3 * sizeof(float)));
		assert_error("Normal pointer");
	}
	else
	{
		glVertexAttribPointer(position_handle, 3, GL_FLOAT, GL_FALSE, sizeof(float) * 3, (void*)0);
		assert_error("Position pointer");
	}

	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ivbo);
	assert_error("Bind elements");

	glDrawElements(element_type, n, GL_UNSIGNED_SHORT, (void*)0);
	assert_error("Draw");

	glDisableVertexAttribArray(position_handle);
	assert_error("Disable position array");

	if (draw_type == DRAW_TUBES)
	{
		glDisableVertexAttribArray(normal_handle);
		assert_error("Disable normal array");
	}
}

void Renderer::buffer(const int nvertices, const float * vertices, const int nindices, const short * indices, GLuint * vbo, GLuint * ivbo)
{
	int vertex_buffer_size = nvertices * sizeof(float);
	int index_buffer_size = nindices * sizeof(short);
	glGenBuffers(1, vbo);
	assert_error("generate vertex buffer");
	glBindBuffer(GL_ARRAY_BUFFER, *vbo);
	assert_error("bind vertex buffer");

	glBufferData(GL_ARRAY_BUFFER, vertex_buffer_size, vertices, GL_STATIC_DRAW);
	assert_error("Vertex buffer data");

	glGenBuffers(1, ivbo);
	assert_error("generate index buffer");
	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, *ivbo);
	assert_error("bind index buffer");
	glBufferData(GL_ELEMENT_ARRAY_BUFFER, index_buffer_size, indices, GL_STATIC_DRAW);
	assert_error("index buffer data");

	memory_used += vertex_buffer_size + index_buffer_size;
}

void Renderer::deleteBuffer(GLuint ivbo, GLuint vbo)
{
	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0);
	assert_error("Unbind element array buffer");

	glBindBuffer(GL_ARRAY_BUFFER, 0);
	assert_error("Unbind vertex array buffer");

	GLuint toDelete[] = { vbo, ivbo };
	glDeleteBuffers(2, toDelete);
	assert_error("Delete buffers");
}

void Renderer::createProgram()
{
	GLuint program;

	if (draw_type == DRAW_LINES)
		program = LoadShadersFromSource(line_vertexshader, line_fragmentshader, &(this->program), &(this->vertex_shader), &(this->fragment_shader));
	else
		program = LoadShadersFromSource(tube_vertexshader, tube_fragmentshader, &(this->program), &(this->vertex_shader), &(this->fragment_shader));

	// Shader magic
	position_handle = glGetAttribLocation(program, "vertexPosition_modelspace");
	assert_error("Get position handle");

	color_handle = glGetUniformLocation(program, "ds_Color");
	assert_error("Get color handle");

	camera_handle = glGetUniformLocation(program, "MVP");
	assert_error("Get camera handle");

	if (draw_type == DRAW_TUBES)
	{
		light_handle = glGetUniformLocation(program, "LightPosition_worldspace");
		assert_error("Get light handle");
		normal_handle = glGetAttribLocation(program, "vertexNormal_modelspace");
		assert_error("Get normal handle");

		m_handle = glGetUniformLocation(program, "M");
		assert_error("Get model-matrix handle");
		v_handle = glGetUniformLocation(program, "V");
		assert_error("Get view-matrix handle");
	}

	glUseProgram(program);
	assert_error("Use program");

	glEnable(GL_DEPTH_TEST);
	assert_error("Enable depth test");
}

void Renderer::renderGcode(const char * gcodeFile, const char* imageFile)
{
	BBox bed_bbox = { -bed_origin_offset[0], bed_width + bed_origin_offset[0], -bed_origin_offset[1], bed_depth + bed_origin_offset[1], 0, bed_height };
	this->parser = new GcodeParser(gcodeFile, this->draw_type, bed_bbox);

	unsigned int vertices_size, indices_size;

	this->parser->get_buffer_size(&vertices_size, &indices_size);

	vertices = new float[this->lines_per_run * vertices_size];
	indices = new short[this->lines_per_run * indices_size];

	// Start with a clean slate
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

	this->renderPart();
	log_msg(debug, "Part rendered");

	this->renderBed();
	log_msg(debug, "Bed rendered");

	this->saveRender(imageFile);
	log_msg(debug, "File saved");

	delete[] vertices;
	delete[] indices;
	delete this->parser;
	this->buffers.clear();
}

void Renderer::setCamera()
{
	BBox bbox;
	glm::vec3 camera_position, camera_target, object_center;
	float fov_deg = 45.0f;
	if (parser->get_bbox(&bbox))
	{
		// Minimal smallest offset to bed edges
		float x_offset_min = min(bed_origin_offset[0] + bbox.xmin, bed_width - bed_origin_offset[0] - bbox.xmax);
		float y_offset_min = min(bed_origin_offset[1] + bbox.ymin, bed_depth - bed_origin_offset[1] - bbox.ymax);

		// Range offset from 0.0 (center of bed, smallest possible angle), to 1.0 (full bed used, widest angle needed)
		float x_factor = 1.0f - x_offset_min / (bed_width / 2);
		float y_factor = 1.0f - y_offset_min / (bed_depth / 2);

		// Use the biggest factor and scale to max 60 degrees (which is ~ the whole bed)
		float factor_max = max(x_factor, y_factor);
		fov_deg = max(fov_deg, factor_max * 60.0f);
	}

	// Point to the middle of the bed
	camera_target = glm::vec3((bed_width - bed_origin_offset[0]) / 2, (bed_depth - bed_origin_offset[1]) / 2, 0);

	camera_position = camera_target + camera_distance;
	glm::mat4 mvp, projection, view, model;
	glm::vec3 up = glm::vec3(0, 0, 1);

	model = glm::mat4(1.0f);
	view = glm::lookAt(camera_position, camera_target, up);
	projection = glm::perspective<float>(glm::radians(fov_deg), width / (float)height, 0.1f, 1000.0f);

	mvp = projection * view * model;

	// Upload the camera matrix to OpenGL(ES)

	glUniformMatrix4fv(camera_handle, 1, GL_FALSE, &mvp[0][0]);
	assert_error("Set camera matrix");

	if (draw_type == DRAW_TUBES)
	{
		glUniformMatrix4fv(m_handle, 1, GL_FALSE, &model[0][0]);
		assert_error("Set model matrix");
		glUniformMatrix4fv(v_handle, 1, GL_FALSE, &view[0][0]);
		assert_error("Set view matrix");
	}
}

void Renderer::bufferBed()
{
	int bedvertices_n;
	float * bedvertices;

	float x_min = -bed_origin_offset[0];
	float x_max = bed_width-bed_origin_offset[0];
	float y_min = -bed_origin_offset[1];
	float y_max = bed_depth - bed_origin_offset[1];


	// X, y, z, nx, ny, nz
	if (draw_type == DRAW_TUBES)
	{
		bedvertices_n = 24;
		bedvertices = new float[bedvertices_n] {
			x_min, y_min, 0, 0, 0, 1.0f,
			x_min, y_max, 0, 0, 0, 1.0f,
			x_max, y_max, 0, 0, 0, 1.0f,
			x_max, y_min, 0, 0, 0, 1.0f
		};
	}
	else
	{
		bedvertices_n = 12;
		bedvertices = new float[bedvertices_n] {
			x_min, y_min, 0,
			x_min, y_max, 0,
			x_max, y_max, 0,
			x_max, y_min, 0,
		};
	}

	const int bedindices_n = 6;
	short bedindices[bedindices_n] = { 0, 1, 2, 2, 3, 0 };

	bed_buffer.nindices = bedindices_n;
	bed_buffer.nvertices = bedvertices_n;

	buffer(bedvertices_n, bedvertices, bedindices_n, bedindices, &bed_buffer.vertex_buffer, &bed_buffer.index_buffer);

	delete[] bedvertices;
}

void Renderer::renderBed()
{
	draw(bed_color, bed_buffer.index_buffer, bed_buffer.vertex_buffer, bed_buffer.nindices, GL_TRIANGLES);
}

void Renderer::renderPart()
{
	log_msg(debug, "Begin rendering part");
	memory_used = 0;
	int nvertices, nindices;
	buffer_info buff = buffer_info();

	parser->get_vertices(lines_per_run, &nvertices, vertices, &nindices, indices);
	
	buff.nindices = nindices;
	buff.nvertices = nvertices;
	
	buffer(nvertices, vertices, nindices, indices, &buff.vertex_buffer, &buff.index_buffer);

	this->setCamera();

	if (draw_type == DRAW_LINES)
		draw(part_color, buff.index_buffer, buff.vertex_buffer, buff.nindices, GL_LINES);
	else
		draw(part_color, buff.index_buffer, buff.vertex_buffer, buff.nindices, GL_TRIANGLES);
	
	deleteBuffer(buff.index_buffer, buff.vertex_buffer);

	while (parser->get_vertices(lines_per_run, &nvertices, vertices, &nindices, indices))
	{
		buff.nindices = nindices;
		buff.nvertices = nvertices;

		buffer(nvertices, vertices, nindices, indices, &buff.vertex_buffer, &buff.index_buffer);

		if (draw_type == DRAW_LINES)
			draw(part_color, buff.index_buffer, buff.vertex_buffer, buff.nindices, GL_LINES);
		else
			draw(part_color, buff.index_buffer, buff.vertex_buffer, buff.nindices, GL_TRIANGLES);

		deleteBuffer(buff.index_buffer, buff.vertex_buffer);
	}

	char resp[512];
	sprintf(resp, "Total data processed: %d kb", memory_used / 1000);
	log_msg(debug, resp);
}

void Renderer::saveRender(const char* imageFile)
{
	// Wait for all commands to complete before we read the buffer
	glFlush();
	glFinish();

	// Create a buffer for the pixel data
	const int n = 4 * width*height;
	uint8_t *imgData = new uint8_t[n];

	glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, imgData);
	assert_error("glReadPixels");

	FILE *fp = NULL;
	png_structp png_ptr = NULL;
	png_infop info_ptr = NULL;

	// Open file for writing (binary mode)
	fp = fopen(imageFile, "wb");
	if (fp == NULL) {
		log_msg(error, "Could not open image file for writing");
		//goto finalise;
	}

	// Initialize write structure
	png_ptr = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
	if (png_ptr == NULL) {
		log_msg(error, "Could not allocate PNG write struct");
		//goto finalise;
	}

	// Initialize info structure
	info_ptr = png_create_info_struct(png_ptr);
	if (info_ptr == NULL) {
		log_msg(error, "Could not allocate PNG info struct");
		//goto finalise;
	}

	//TODO: Error handling without setjmp (not thread-safe)

	png_init_io(png_ptr, fp);

	// Write header (8 bit colour depth)
	png_set_IHDR(png_ptr, info_ptr, width, height,
		8, PNG_COLOR_TYPE_RGBA, PNG_INTERLACE_NONE,
		PNG_COMPRESSION_TYPE_BASE, PNG_FILTER_TYPE_BASE);

	// Write image data
	png_bytepp rows = (png_bytepp)png_malloc(png_ptr, height * sizeof(png_bytep));

	for (int i = 0; i < height; ++i) {
		rows[i] = &imgData[(height - i - 1) * width * 4];
	}

	png_set_rows(png_ptr, info_ptr, rows);
	png_write_png(png_ptr, info_ptr, PNG_TRANSFORM_IDENTITY, NULL);
	png_write_end(png_ptr, info_ptr);

	png_free(png_ptr, rows);

	if (fp != NULL) fclose(fp);
	if (info_ptr != NULL) png_free_data(png_ptr, info_ptr, PNG_FREE_ALL, -1);
	if (png_ptr != NULL) png_destroy_write_struct(&png_ptr, (png_infopp)NULL);

	delete[] imgData;

	return;
}

// Python API

static PyMethodDef GcodeParserMethods[] = {
	{ "initialize", (PyCFunction) initialize_renderer, METH_VARARGS | METH_KEYWORDS, "Initialize the renderer" },
	{"render_gcode",  (PyCFunction) render_gcode, METH_VARARGS | METH_KEYWORDS, "Render a gcode file to a PNG image file."},
	{NULL, NULL, 0, NULL}        /* Sentinel */
};

extern "C" void initgcodeparser(void)
{
	(void)Py_InitModule("gcodeparser", GcodeParserMethods);
}

PyObject * render_gcode(PyObject *self, PyObject *args, PyObject *kwargs, char *keywords[])
{
	log_msg(debug, "Begin rendering file");

	char *kwlist[] = { "gcode_file", "image_file", NULL };

	const char *gcode_file;
	const char *image_file;

	if(!PyArg_ParseTupleAndKeywords(args, kwargs, "ss", kwlist,
		&gcode_file, &image_file))
		return NULL;

	//TODO: Input validation	
	renderer->renderGcode(gcode_file, image_file);

	return Py_BuildValue("i", 0);
}

PyObject * initialize_renderer(PyObject *self, PyObject *args, PyObject *kwargs, char *keywords[])
{	
	char *kwlist[] = { "logger", NULL };

	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O", kwlist,
		&pyLogger))
		return NULL;
	
	renderer = new Renderer(250, 250);
	renderer->initialize();

	return Py_BuildValue("i", 0);
}

static void log_msg(int type, char *msg)
{
	static PyObject *string = NULL;

	// build msg-string
	string = Py_BuildValue("s", msg);

	// call function depending on loglevel
	switch (type)
	{
		case info:
			PyObject_CallMethod(pyLogger, "info", "O", string);
			break;
		case warning:
			PyObject_CallMethod(pyLogger, "warn", "O", string);
			break;
		case error:
			PyObject_CallMethod(pyLogger, "error", "O", string);
			break;
		case debug:
			PyObject_CallMethod(pyLogger, "debug", "O", string);
			break;
	}

	Py_DECREF(string);
}

int main(int argc, char** argv)
{

#ifdef _DEBUG
	if (argc > 1)
	{
		renderer = new Renderer(1024, 1024);
		renderer->initialize();
		renderer->renderGcode(argv[1], argv[2]);
		getchar();
		return 0;
	}
#endif

	/* Pass argv[0] to the Python interpreter */
	Py_SetProgramName(argv[0]);

	/* Initialize the Python interpreter.  Required. */
	Py_Initialize();

	/* Add a static module */
	initgcodeparser();

	return 0;
}
