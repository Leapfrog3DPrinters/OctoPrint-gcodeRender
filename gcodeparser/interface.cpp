#pragma once
/*
interface.cpp

The main API to interface with Python. Also defines the implementation
of the log function and the main entry point.

*/
#include "interface.h"

static PyMethodDef GcodeParserMethods[] = {
	{ "initialize", (PyCFunction)initialize_renderer, METH_VARARGS | METH_KEYWORDS, "Initialize the renderer" },
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
		renderer = new Renderer(2048, 2048);
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
