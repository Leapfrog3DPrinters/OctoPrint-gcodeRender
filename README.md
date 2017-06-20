# OctoPrint-gcodeRender

An OctoPrint plugin to create previews of gcode files using OpenGL (ES). Uses a Python C++ extension for fast rendering. Optimized to work with the OctoPrint-LUI plugin.

## Installation

This plugin requires zlib and libpng to create images. TinyDB is used to keep a database of the previews. Setuptools is used to compile and install the plugin.

At the moment only Windows and Raspberry Pi environments are supported.

0. Open a command prompt or shell
1. Clone the repository to any desired location
2. Activate the OctoPrint virtual environment
3. Navigate to the OctoPrint-gcodeRender repository
4. Run `python setup.py install' or `python setup.py develop'

### Windows
To compile the C++ extension, setuptools needs to use the VC2015 compiler. See
http://pywavelets.readthedocs.io/en/latest/dev/preparing_windows_build_environment.html to setup the environment. If you have Visual Studio 2015 installed, you may use the "VS2015 x86 Native Tools Command Prompt".

If you run a `develop` installation, you may need  to copy the DLL files in lib/ to the root folder (where gcoderender.pyd is generated).