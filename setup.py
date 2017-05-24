# coding=utf-8

########################################################################################################################
### Do not forget to adjust the following variables to your own plugin.

# The plugin's identifier, has to be unique
plugin_identifier = "gcoderender"

# The plugin's python package, should be "octoprint_<plugin identifier>", has to be unique
plugin_package = "octoprint_gcoderender"

# The plugin's human readable name. Can be overwritten within OctoPrint's internal data via __plugin_name__ in the
# plugin module
plugin_name = "OctoPrint-gcodeRender"

# The plugin's version. Can be overwritten within OctoPrint's internal data via __plugin_version__ in the plugin module
plugin_version = "1.1.0"

# The plugin's description. Can be overwritten within OctoPrint's internal data via __plugin_description__ in the plugin
# module
plugin_description = """Renders gcode previews"""

# The plugin's author. Can be overwritten within OctoPrint's internal data via __plugin_author__ in the plugin module
plugin_author = "Erik Heidstra"

# The plugin's author's mail address.
plugin_author_email = "erikheidstra@live.nl"

# The plugin's homepage URL. Can be overwritten within OctoPrint's internal data via __plugin_url__ in the plugin module
plugin_url = "https://github.com/Leapfrog3DPrinters/OctoPrint-gcodeRender"

# The plugin's license. Can be overwritten within OctoPrint's internal data via __plugin_license__ in the plugin module
plugin_license = "AGPLv3"

# Any additional requirements besides OctoPrint should be listed here
plugin_requires = ["tinydb>=3.2.1"]

### --------------------------------------------------------------------------------------------------------------------
### More advanced options that you usually shouldn't have to touch follow after this point
### --------------------------------------------------------------------------------------------------------------------

# Additional package data to install for this plugin. The subfolders "templates", "static" and "translations" will
# already be installed automatically if they exist.
plugin_additional_data = []

# Any additional python packages you need to install with your plugin that are not contains in <plugin_package>.*
plugin_addtional_packages = []

# Any python packages within <plugin_package>.* you do NOT want to install with your plugin
plugin_ignored_packages = []

# Additional parameters for the call to setuptools.setup. If your plugin wants to register additional entry points,
# define dependency links or other things like that, this is the place to go. Will be merged recursively with the
# default setup parameters as provided by octoprint_setuptools.create_plugin_setup_parameters using
# octoprint.util.dict_merge.
#
# Example:
#     plugin_requires = ["someDependency==dev"]
#     additional_setup_parameters = {"dependency_links": ["https://github.com/someUser/someRepo/archive/master.zip#egg=someDependency-dev"]}
from setuptools import setup, Extension
import sys

if sys.platform == "win32":
    import os
    # We can't build with the default VS2008 compiler, 
    # therefore we rely on the Windows SDK with >=VS2015
    # see http://pywavelets.readthedocs.io/en/latest/dev/preparing_windows_build_environment.html
    # for help.
    os.environ["MSSdk"] = "1"
    os.environ["DISTUTILS_USE_SDK"] = "1"

    libraries = ['glew32', 'glfw3dll', 'OpenGL32', 'libpng', 'zlibstat']
    data_files = [
        ('', ['lib/glew32.dll','lib/glfw3.dll','lib/libpng12.dll','lib/zlib1.dll'])
    ]

else:
    libraries = [ 'EGL', 'GLESv2', 'png', 'z']
    data_files = []

gcodeparser_module = Extension('gcodeparser',
                    include_dirs = ['/usr/include', '/usr/include/libpng12', 'include'],
                    libraries = libraries,
                    library_dirs = ['/opt/vc/lib', '/usr/local/lib', 'lib'],
                    language = "c++",
                    extra_compile_args=['-std=c++11'],
                    sources = ['gcodeparser/renderer.cpp', 'gcodeparser/gcodeparser.cpp', 'gcodeparser/RenderContextEGL.cpp', 'gcodeparser/RenderContextGLFW.cpp', 'gcodeparser/shader.cpp', 'gcodeparser/interface.cpp' ])

additional_setup_parameters = { "ext_modules": [gcodeparser_module], "data_files": data_files }

########################################################################################################################

try:
	import octoprint_setuptools
except:
	print("Could not import OctoPrint's setuptools, are you sure you are running that under "
	      "the same python installation that OctoPrint is installed under?")
	sys.exit(-1)


setup_parameters = octoprint_setuptools.create_plugin_setup_parameters(
	identifier=plugin_identifier,
	package=plugin_package,
	name=plugin_name,
	version=plugin_version,
	description=plugin_description,
	author=plugin_author,
	mail=plugin_author_email,
	url=plugin_url,
	license=plugin_license,
	requires=plugin_requires,
	additional_packages=plugin_addtional_packages,
	ignored_packages=plugin_ignored_packages,
	additional_data=plugin_additional_data
)

if len(additional_setup_parameters):
	from octoprint.util import dict_merge
	setup_parameters = dict_merge(setup_parameters, additional_setup_parameters)

setup(**setup_parameters)
