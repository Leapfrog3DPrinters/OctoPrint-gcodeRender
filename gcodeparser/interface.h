/*
interface.h

The header file for the interface with Python.

*/
#ifndef INTERFACE_H
#define INTERFACE_H 1

#include <Python.h>

#include "Renderer.h"
#include "helpers.h"

static Renderer * renderer;

static PyObject *pyLogger;

static PyObject * initialize_renderer(PyObject *self, PyObject *args, PyObject *kwargs, char *keywords[]);
static PyObject * set_print_area(PyObject *self, PyObject *args, PyObject *kwargs, char *keywords[]);
static PyObject * set_camera(PyObject *self, PyObject *args, PyObject *kwargs, char *keywords[]);
static PyObject * set_background_color(PyObject *self, PyObject *args);
static PyObject * set_bed_color(PyObject *self, PyObject *args);
static PyObject * set_part_color(PyObject *self, PyObject *args);
static PyObject * render_gcode(PyObject *self, PyObject *args, PyObject *kwargs, char *keywords[]);

extern "C" void initgcodeparser(void);

static PyMethodDef GcodeParserMethods[] = {
	{ "initialize", (PyCFunction)initialize_renderer, METH_VARARGS | METH_KEYWORDS, "Initialize the renderer" },
	{ "set_print_area", (PyCFunction)set_print_area, METH_VARARGS | METH_KEYWORDS, "Set the camera target and distance" },
	{ "set_camera", (PyCFunction)set_camera, METH_VARARGS | METH_KEYWORDS, "Define the print area" },
	{ "set_background_color", (PyCFunction)set_background_color, METH_VARARGS, "Set the background color" },
	{ "set_bed_color", (PyCFunction)set_bed_color, METH_VARARGS, "Set the bed color" },
	{ "set_part_color", (PyCFunction)set_part_color, METH_VARARGS, "Set the part color" },
	{ "render_gcode",  (PyCFunction)render_gcode, METH_VARARGS | METH_KEYWORDS, "Render a gcode file to a PNG image file." },
	{ NULL, NULL, 0, NULL }        /* Sentinel */
};

#endif /* INTERFACE_H */
