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
static PyObject * render_gcode(PyObject *self, PyObject *args, PyObject *kwargs, char *keywords[]);

extern "C" void initgcodeparser(void);

#endif /* INTERFACE_H */
