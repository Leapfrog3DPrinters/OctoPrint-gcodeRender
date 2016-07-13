from __future__ import absolute_import, division

import os, sys, imp

from random import randint

try:
    imp.find_module('octoprint')
    inocto = True
except ImportError:
    inocto = False

# coding=utf-8
#TODO: Make this a lot neater
if inocto:
    import octoprint.plugin
    import octoprint.filemanager
    import octoprint.filemanager.util
    from octoprint_gcoderender.gcoderenderplugin import GCodeRenderPlugin
    from octoprint_gcoderender.rendering.renderer import *
else:
     from rendering.renderer import *

# Register plugin
__plugin_name__ = "GCode render"

def __plugin_load__():
    global __plugin_implementation__, __plugin_hooks__

    __plugin_implementation__ = GCodeRenderPlugin()
    
    __plugin_hooks__ = {
        "octoprint.filemanager.preprocessor": __plugin_implementation__.render_gcode_hook
    }

### Standalone starts here
# If started standalone, do some sample rendering
# TODO: Remove this debugging feature
if __name__ == "__main__":
    # Find file paths
    scriptPath = os.path.realpath(__file__)
    scriptDir = os.path.dirname(scriptPath)
    gCodePath = os.path.join(scriptDir, "sample/spiral.gcode")

    if sys.platform == "win32":
        imagePath = os.path.join(scriptDir, "images/spiral.bmp")
        render = RendererWindows()
    else:
        imagePath = os.path.join(scriptDir, "images/leapfrog_small.png")
        render = RendererLinux()

    # Start rendering the part
    render.initialize(bedWidth = 365, bedDepth = 350, partColor = (67/255, 74/255, 84/255), bedColor = (0.7, 0.7, 0.7), showWindow = False)
    render.renderModel(gCodePath, True)
    render.save(imagePath)