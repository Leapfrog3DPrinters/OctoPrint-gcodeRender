from __future__ import absolute_import, division
__author__ = "Erik Heidstra <ErikHeidstra@live.nl>"

import os, sys, imp

from random import randint

# coding=utf-8
import octoprint.plugin
import octoprint.filemanager
import octoprint.filemanager.util
from octoprint_gcoderender.gcoderenderplugin import GCodeRenderPlugin

# Register plugin
__plugin_name__ = "GCode render"

def __plugin_load__():
    global __plugin_implementation__, __plugin_hooks__

    __plugin_implementation__ = GCodeRenderPlugin()
    
    __plugin_hooks__ = {
    }
