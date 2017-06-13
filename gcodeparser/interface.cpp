/*
interface.cpp

The main API to interface with Python. Also defines the implementation
of the log function and the main entry point.

*/
#include "interface.h"

static Renderer * renderer;
static PyThreadState *_save;
static PyObject *pyLogger;

extern "C" void initgcodeparser(void)
{
	(void)Py_InitModule("gcodeparser", GcodeParserMethods);
}

PyObject * render_gcode(PyObject *self, PyObject *args, PyObject *kwargs, char *keywords[])
{
	log_msg(debug, "Begin rendering file");

	// This is throwing warnings, but PyArg_ParseTupleAndKeywords doesn't
	// take a const char **
	char *kwlist[] = { "gcode_file", "image_file", NULL };

	char *gcode_file;
	char *image_file;

	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "ss", kwlist,
		&gcode_file, &image_file))
		return NULL;

	bool result;

	//TODO: Input validation
	_save = PyEval_SaveThread();
	result = renderer->renderGcode(gcode_file, image_file);
	PyEval_RestoreThread(_save);
	_save = NULL;

	return Py_BuildValue("O", result ? Py_True : Py_False);
}

PyObject * initialize_renderer(PyObject *self, PyObject *args, PyObject *kwargs, char *keywords[])
{
	char *kwlist[] = { "width", "height", "logger", "throttling_interval", "throttling_duration", NULL };

	unsigned int width = 250, height = 250, throttlingInterval = 0, throttlingDuration = 0;

	//TODO: validate throttlingInterval <= Renderer::linesPerRun

	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "IIOII", kwlist,
		&width, &height, &pyLogger, &throttlingInterval, &throttlingDuration))
		return NULL;

	renderer = new Renderer(width, height, throttlingInterval, throttlingDuration);

	bool result = renderer->initialize();

	return Py_BuildValue("O", result ? Py_True : Py_False);
}

PyObject * set_print_area(PyObject *self, PyObject *args, PyObject *kwargs, char *keywords[])
{
	char *kwlist[] = { "x_min", "x_max", "y_min", "y_max", "z_min", "z_max", NULL };

	BBox printArea = BBox(-37.0f, 328.0f, -33.0f, 317.0f, 0.0f, 200.0f);
		
	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "ffffff", kwlist,
		&printArea.xmin, &printArea.xmax, &printArea.ymin, &printArea.ymax, &printArea.zmin, &printArea.zmax))
		return NULL;

	renderer->configurePrintArea(&printArea);

	return Py_BuildValue("O", Py_True);
}

PyObject * set_camera(PyObject *self, PyObject *args, PyObject *kwargs, char *keywords[])
{
	char *kwlist[] = { "target", "distance", NULL };

	char camTarget[8];
	float camDistance[3] = { -300.f, -300.f, 150.f };

	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "z(fff)", kwlist,
		&camTarget, &camDistance[0], &camDistance[1], &camDistance[2]))
		return NULL;

	renderer->configureCamera(strstr(camTarget, "part") == 0, camDistance);

	return Py_BuildValue("O", Py_True);
}

PyObject * set_background_color(PyObject *self, PyObject *args)
{
	float backgroundColor[4] = { 1.0f, 1.0f, 1.0f, 1.0f };

	if (!PyArg_ParseTuple(args, "(ffff)",
		&backgroundColor[0], &backgroundColor[1], &backgroundColor[2], &backgroundColor[3]))
		return NULL;

	renderer->configureBackgroundColor(backgroundColor);

	return Py_BuildValue("O", Py_True);
}

PyObject * set_bed_color(PyObject *self, PyObject *args)
{
	float bedColor[4] = { 0.75f, 0.75f, 0.75f, 1.0f };

	if (!PyArg_ParseTuple(args, "(ffff)",
		&bedColor[0], &bedColor[1], &bedColor[2], &bedColor[3]))
		return NULL;

	renderer->configureBedColor(bedColor);

	return Py_BuildValue("O", Py_True);
}

PyObject * set_part_color(PyObject *self, PyObject *args)
{
	float partColor[4] = { 67.f / 255.f, 74.f / 255.f, 84.f / 255.f, 1.0f };

	if (!PyArg_ParseTuple(args, "(ffff)",
		&partColor[0], &partColor[1], &partColor[2], &partColor[3]))
		return NULL;

	renderer->configurePartColor(partColor);

	return Py_BuildValue("O", Py_True);
}

void log_msg(int type, const char *msg)
{
	if (pyLogger == NULL)
	{
		cout << msg << '\n';
		return;
	}

	if(_save != NULL)
		PyEval_RestoreThread(_save);

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

	if (_save != NULL)
		_save = PyEval_SaveThread();
}

int main(int argc, char** argv)
{

#ifdef _DEBUG
	if (argc > 1)
	{
		renderer = new Renderer(2048, 2048, 0, 0);
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
