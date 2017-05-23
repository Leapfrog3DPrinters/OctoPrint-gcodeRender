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
		printf("Error: %s %04x\n", part, error);
	}
}

void Renderer::initialize()
{
	printf("Initializing renderer\n");
	renderContext->activate();

#ifdef USE_GLEW
	if (glewInit() != GLEW_OK) {
		printf("Failed to initialize GLEW\n");
		return;
	}
#endif

	printf("Creating program\n");
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
	printf("Bed buffered\n");
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

	glVertexAttribPointer(position_handle, 3, GL_FLOAT, GL_FALSE, sizeof(float) * 6, (void*)0);
	assert_error("Position pointer");

	if (draw_type == DRAW_TUBES)
	{
		glVertexAttribPointer(normal_handle, 3, GL_FLOAT, GL_FALSE, sizeof(float) * 6, (void*)(3 * sizeof(float)));
		assert_error("Normal pointer");
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
	glGenBuffers(1, vbo);
	assert_error("generate vertex buffer");
	glBindBuffer(GL_ARRAY_BUFFER, *vbo);
	assert_error("bind vertex buffer");
	glBufferData(GL_ARRAY_BUFFER, nvertices * sizeof(float), vertices, GL_STATIC_DRAW);
	assert_error("vertex buffer data");

	glGenBuffers(1, ivbo);
	assert_error("generate index buffer");
	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, *ivbo);
	assert_error("bind index buffer");
	glBufferData(GL_ELEMENT_ARRAY_BUFFER, nindices * sizeof(short), indices, GL_STATIC_DRAW);
	assert_error("index buffer data");

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
	this->parser = new GcodeParser(gcodeFile, this->draw_type);

	unsigned int vertices_size, indices_size;

	this->parser->get_buffer_size(&vertices_size, &indices_size);

	vertices = new float[this->lines_per_run * vertices_size];
	indices = new short[this->lines_per_run * indices_size];

	// Start with a clean slate
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

	this->bufferPart();
	printf("Part buffered\n");

	this->setCamera();
	printf("Camera set\n");

	this->renderBed();
	printf("Bed rendered\n");

	this->renderPart();
	printf("Part rendered\n");

	this->saveRender(imageFile);
	printf("File saved\n");

	delete[] vertices;
	delete[] indices;
	delete this->parser;
	this->buffers.clear();
}

void Renderer::setCamera()
{
	BBox bbox;
	glm::vec3 object_center;
	float scale = 1.0f;

	if (parser->get_bbox(&bbox))
	{
		// Point camera at objecct
		object_center = glm::vec3(bbox.xmax + bbox.xmin / 2, bbox.ymax + bbox.ymin / 2, bbox.zmax + bbox.zmin / 2);
		scale = max(bbox.xmax - bbox.xmin, max(bbox.ymax - bbox.ymin, bbox.zmax - bbox.zmin)) / 175;
	}
	else
	{
		// Point to the middle of the bed
		object_center = glm::vec3(bed_width / 2, bed_depth / 2, 0);
	}

	camera_position = object_center + (camera_distance * scale);

	glm::mat4 mvp, projection, view, model;

	glm::vec3 up = glm::vec3(0, 0, 1);

	model = glm::mat4(1.0f);
	view = glm::lookAt(camera_position, object_center, up);
	projection = glm::perspective<float>((float)(90.0 * M_PI / 180.0), width / (float)height, 0.1f, 10000.0f);

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
	// X, y, z, nx, ny, nz
	const int bedvertices_n = 6 * 4;
	float bedvertices[bedvertices_n] = {
		0, 0, 0, 0, 0, 1.0f,
		0, bed_depth, 0, 0, 0, 1.0f,
		bed_width, bed_depth, 0, 0, 0, 1.0f,
		bed_width, 0, 0, 0, 0, 1.0f
	};

	const int bedindices_n = 6;
	short bedindices[bedindices_n] = { 0, 1, 2, 2, 3, 0 };

	bed_buffer.nindices = bedindices_n;
	bed_buffer.nvertices = bedvertices_n;

	buffer(bedvertices_n, bedvertices, bedindices_n, bedindices, &bed_buffer.vertex_buffer, &bed_buffer.index_buffer);
}

void Renderer::renderBed()
{
	draw(bed_color, bed_buffer.index_buffer, bed_buffer.vertex_buffer, bed_buffer.nindices, GL_TRIANGLES);
}

void Renderer::bufferPart()
{
	printf("Begin buffering part\n");
	int nvertices, nindices;
	while (parser->get_vertices(lines_per_run, &nvertices, vertices, &nindices, indices))
	{
		buffer_info buff = buffer_info();

		buff.nindices = nindices;
		buff.nvertices = nvertices;
		buffer(nvertices, vertices, nindices, indices, &buff.vertex_buffer, &buff.index_buffer);

		buffers.push_back(buff);
	}
}

void Renderer::renderPart()
{
	for (unsigned int i = 0; i < buffers.size(); i++)
	{
		if (draw_type == DRAW_LINES)
			draw(part_color, buffers[i].index_buffer, buffers[i].vertex_buffer, buffers[i].nindices, GL_LINES);
		else
			draw(part_color, buffers[i].index_buffer, buffers[i].vertex_buffer, buffers[i].nindices, GL_TRIANGLES);

		deleteBuffer(buffers[i].index_buffer, buffers[i].vertex_buffer);
	}
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

	printf("imgData: %d %d %d %d %d %d %d %d\n", imgData[0], imgData[1], imgData[2], imgData[3], imgData[4], imgData[5], imgData[6], imgData[7]);

	FILE *fp = NULL;
	png_structp png_ptr = NULL;
	png_infop info_ptr = NULL;

	// Open file for writing (binary mode)
	fp = fopen(imageFile, "wb");
	if (fp == NULL) {
		printf("Could not open file %s for writing\n", imageFile);
		//goto finalise;
	}

	// Initialize write structure
	png_ptr = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
	if (png_ptr == NULL) {
		printf("Could not allocate write struct\n");
		//goto finalise;
	}

	// Initialize info structure
	info_ptr = png_create_info_struct(png_ptr);
	if (info_ptr == NULL) {
		printf("Could not allocate info struct\n");
		//goto finalise;
	}

	// Setup Exception handling
	if (setjmp(png_jmpbuf(png_ptr))) {
		printf("Error during png creation\n");
		//goto finalise;
	}

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
	{ "initialize", initialize_renderer, METH_VARARGS, "Initialize the renderer" },
	{"render_gcode",  render_gcode, METH_VARARGS,
	"Render a gcode file to a PNG image file."},
	{NULL, NULL, 0, NULL}        /* Sentinel */
};

extern "C" void initgcodeparser(void)
{
	printf("Initializing renderer extension\n");

	(void)Py_InitModule("gcodeparser", GcodeParserMethods);
}

PyObject * render_gcode(PyObject *self, PyObject *args)
{
	printf("Begin rendering file\n");

	const char *gcode_file;
	const char *image_file;

	if (!PyArg_ParseTuple(args, "ss", &gcode_file, &image_file))
		return NULL;

	//TODO: Input validation	
	renderer->renderGcode(gcode_file, image_file);

	return Py_BuildValue("i", 0);
}

PyObject * initialize_renderer(PyObject *self, PyObject *args)
{
	printf("Creating renderer\n");

	renderer = new Renderer(250, 250);
	renderer->initialize();

	return Py_BuildValue("i", 0);
}

int main(int argc, char** argv)
{

#ifdef _DEBUG
	if (argc > 1)
	{
		initialize_renderer(NULL, NULL);
		renderer->renderGcode(argv[1], argv[2]);
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
