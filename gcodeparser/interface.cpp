#pragma once
/*
interface.cpp

The main API to interface with Python. Also defines the implementation
of the log function and the main entry point.

*/
#include "interface.h"

static PyMethodDef GcodeParserMethods[] = {
	{ "initialize", (PyCFunction)initialize_renderer, METH_VARARGS | METH_KEYWORDS, "Initialize the renderer" },
	{ "set_print_area", (PyCFunction)set_print_area, METH_VARARGS | METH_KEYWORDS, "Set the camera target and distance" },
	{ "set_camera", (PyCFunction)set_camera, METH_VARARGS | METH_KEYWORDS, "Define the print area" },
	{ "render_gcode",  (PyCFunction)render_gcode, METH_VARARGS | METH_KEYWORDS, "Render a gcode file to a PNG image file." },
	{ NULL, NULL, 0, NULL }        /* Sentinel */
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

	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "ss", kwlist,
		&gcode_file, &image_file))
		return NULL;

	//TODO: Input validation	
	bool result = renderer->renderGcode(gcode_file, image_file);

	return Py_BuildValue("O", result ? Py_True : Py_False);
}

PyObject * initialize_renderer(PyObject *self, PyObject *args, PyObject *kwargs, char *keywords[])
{
	char *kwlist[] = { "width", "height", "logger", "throttling_interval", "throttling_duration", NULL };

	unsigned int width = 250, height = 250, throttlingInterval = 0, throttlingDuration = 0;

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


void log_msg(int type, char *msg)
{
	if (pyLogger == NULL)
	{
		cout << msg << '\n';
		return;
	}
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
