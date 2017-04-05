from __future__ import division, absolute_import
__author__ = "Erik Heidstra <ErikHeidstra@live.nl>"

import math, time, array, ctypes
from octoprint_gcoderender.rendering.vector3 import *

X = 0
Y = 1
Z = 2
E = 3
R = 0.5
NUM_VERTICES = 6
STEP_SIZE = (math.pi*2/NUM_VERTICES)
class GcodeParser:

    FLY=0
    EXTRUDE=1
    RETRACT=2
    RESTORE=3


    
    def __init__(self, verbose = False):
        
        self.parts_to_parse = set(["CONTOUR", "LAYER_NO", "BRIM", "SKIRT"]) 
        self.skip_gcode_part = False # Ensure first bits are parsed no matter what
        self.verbose = verbose
                
    def parseFile(self, path):
       
        # read the gcode file
        t0 = time.clock()

        #TODO: Findout if it's worth it to open the file twice. It's here to estimate the vertex buffer size
        with open(path, 'r') as f:
            num_lines = sum(1 for line in f)

        self.model = GcodeModel(num_lines, True)
        do_g1 = self.model.do_G1

        with open(path, 'r') as f:
            # init line counter
            self.lineNb = 0
            # for all lines
            for line in f:
                self.lineNb += 1
                if self.verbose and self.lineNb % 100000 == 0:
                    print self.lineNb
                # strip comments:
                bits = line.split(';',1)
                if (len(bits) > 1):
                    comment = bits[1].strip()
                else:
                    comment = None

                if not comment and not self.skip_gcode_part:
                    # extract & clean command
                    command = bits[0].strip()
        
                    # TODO strip logical line number & checksum

                    # code is fist word, then args
                    comm = command.split(None, 1)
                    code = comm[0] if (len(comm)>0) else None
                    args = comm[1] if (len(comm)>1) else None
            
                    if code == "G1" or code == "G0":
                        do_g1(self.parseArgs(args)) #Speed optimization. Somehow it's faster to keep parseArgs as function call
                    elif code == "G20":
                        self.parse_G20(args)
                    elif code == "G21":
                        self.parse_G21(args)
                    elif code == "G28":
                        self.parse_G28(args)
                    elif code == "G90":
                        self.parse_G90(args)
                    elif code == "G91":
                        self.parse_G91(args)
                    elif code == "G92":
                        self.parse_G92(args)
                    elif code == "M605":
                        self.parse_M605(args)
                elif comment:
                    comment_parts = comment.split(' ', 1)
                    if comment_parts[0] in self.parts_to_parse:
                        self.skip_gcode_part = False
                    else:
                        self.skip_gcode_part = True
        t1 = time.clock()            
        if self.verbose:
            print "Parse: %s" % (t1-t0)

        return self.model
        
    def parseLine(self, line):
       pass 
        
    def parseArgs(self, args):
        dic = {}
        if args:
            bits = args.split()
            for bit in bits:
                letter = bit[0]
                coord = float(bit[1:])
                dic[letter] = coord
        return dic
       
    def parse_G20(self, args):
        # G20: Set Units to Inches
        self.error("Unsupported & incompatible: G20: Set Units to Inches")
        
    def parse_G21(self, args):
        # G21: Set Units to Millimeters
        # Default, nothing to do
        pass
        
    def parse_G28(self, args):
        # G28: Move to Origin
        self.model.do_G28(self.parseArgs(args))
        
    def parse_G90(self, args):
        # G90: Set to Absolute Positioning
        self.model.setRelative(False)
        
    def parse_G91(self, args):
        # G91: Set to Relative Positioning
        self.model.setRelative(True)
        
    def parse_G92(self, args):
        # G92: Set Position
        self.model.do_G92(self.parseArgs(args))
    
    def parse_M605(self, args):
        #M605 Print mode
        self.model.setPrintMode(self.parseArgs(args))        

class BBox(object):
    
    def __init__(self, coords):
        self.xmin = self.xmax = coords[X]
        self.ymin = self.ymax = coords[Y]
        self.zmin = self.zmax = coords[Z]
        
    def dx(self):
        return self.xmax - self.xmin
    
    def dy(self):
        return self.ymax - self.ymin
    
    def dz(self):
        return self.zmax - self.zmin
        
    def cx(self):
        return (self.xmax + self.xmin)/2
    
    def cy(self):
        return (self.ymax + self.ymin)/2
    
    def cz(self):
        return (self.zmax + self.zmin)/2
    
    def extend(self, coords):
        self.xmin = min(self.xmin, coords[X])
        self.xmax = max(self.xmax, coords[X])
        self.ymin = min(self.ymin, coords[Y])
        self.ymax = max(self.ymax, coords[Y])
        self.zmin = min(self.zmin, coords[Z])
        self.zmax = max(self.zmax, coords[Z])
        
class GcodeModel:
    
    def __init__(self, n = 0, verbose = False):
        # latest coordinates & extrusion relative to offset, feedrate
        self.relative = (0.0, 0.0, 0.0, 0.0)
        # offsets for relative coordinates and position reset (G92)
        self.offset = (0.0, 0.0, 0.0, 0.0)
        # if true, args for move (G1) are given relatively (default: absolute)
        self.isRelative = False
        #self.segments = array.array('f')
        #TODO: Rename to vertices?
        self.segments = (ctypes.c_float*((n-1)*(NUM_VERTICES*2*6)))() # Works with a ctype to prevent casting a large number of floats afterwards
        self.segmentidx = 0
        self.indices = (ctypes.c_uint*((n-1)*NUM_VERTICES*2*3*2))() 
        self.idxidx = 0
        self.bbox = None
        self.printMode = 'normal'
        self.syncOffset = -1
        self.verbose = verbose
        self.afterFly = True
        #self.appendsegment = self.segments.extend
    
    def do_G1(self, args):
        # G0/G1: Rapid/Controlled move

        if self.isRelative:
            rel = self.relative
        else:
            rel = (0.0,0.0,0.0,0.0)

        if args.has_key("X"):
            x = args.get("X") + rel[X]
        else:
            x = self.relative[X]

        if args.has_key("Y"):
            y = args.get("Y") + rel[Y]
        else:
            y = self.relative[Y]

        if args.has_key("Z"):
            z = args.get("Z") + rel[Z]
        else:
            z = self.relative[Z]

        if args.has_key("E"):
            e = args.get("E") + rel[E]
        else:
            e = self.relative[E]
        
        absolute = (x,y,z,e)
        
        if e > self.relative[E]:
            style = GcodeParser.EXTRUDE
            if self.bbox:
                self.bbox.extend(absolute)
            else:
                self.bbox = BBox(absolute)
            
            i = self.segmentidx
            

            # Build a cylinder vertices
            direction = Vector3((x + self.offset[X]) - self.relative[X], (y + self.offset[Y]) - self.relative[Y], (z + self.offset[Z]) - self.relative[Z])

            if direction.as_tuple() == (0,0,0):
                return

            temp=direction.cross(Vector3(1,0,0));
            if temp[0] == 0.0 and temp[1] == 0.0 and temp[2] == 0.0:
                temp=direction.cross(Vector3(0,1,0))
                
            perp1=temp.get_normalised()
            perp2=(direction.cross(perp1)).get_normalised()

            angle = 0

            for step in xrange(NUM_VERTICES):
                sina = math.sin(angle)
                cosa = math.cos(angle)

                # Calculate normals first
                self.segments[i+3] = sina*perp1[0] + cosa*perp2[0]
                self.segments[i+4] = sina*perp1[1] + cosa*perp2[1]
                self.segments[i+5] = sina*perp1[2] + cosa*perp2[2]

                # Copy them for the second ring of vertices
                self.segments[i+9] = self.segments[i+3]
                self.segments[i+10] = self.segments[i+4]
                self.segments[i+11] = self.segments[i+5]

                # Calculate position of first ring
                self.segments[i] =   R * self.segments[i+3] + self.relative[X]
                self.segments[i+1] = R * self.segments[i+4] + self.relative[Y]
                self.segments[i+2] = R * self.segments[i+5] + self.relative[Z]

                # Calculate position of second ring
                self.segments[i+6] = R * self.segments[i+3] + x + self.offset[X]
                self.segments[i+7] = R * self.segments[i+4] + y + self.offset[Y]
                self.segments[i+8] = R * self.segments[i+5] + z + self.offset[Z]

                angle+=STEP_SIZE

                i += 12

            # Build the faces of the cylinder
            vi = int(self.segmentidx / 6)
            j = self.idxidx
            for tri in xrange(0, (NUM_VERTICES-1)*2, 2):
                self.indices[j] = (tri + vi) 
                self.indices[j+1] = (tri + vi + 1) 
                self.indices[j+2] = (tri + vi + 2) 
                self.indices[j+3] = (tri + vi + 1)
                self.indices[j+4] = (tri + vi + 3) 
                self.indices[j+5] = (tri + vi + 2)
                j += 6
            
            # Close the gap
            tri += 2
            self.indices[j] = (tri + vi) 
            self.indices[j+1] = (tri + vi + 1) 
            self.indices[j+2] = (vi) 
            self.indices[j+3] = (tri + vi + 1)
            self.indices[j+4] = (vi + 1) 
            self.indices[j+5] = (vi)
            j += 6

            ## Link the tubes
            #if not self.afterFly:
            #    for tri in xrange(NUM_VERTICES-1):
            #        self.indices[j] = (tri + vi) 
            #        self.indices[j+1] = (tri + vi + 1) 
            #        self.indices[j+2] = (tri + vi - NUM_VERTICES) 
            #        self.indices[j+3] = (tri + vi - NUM_VERTICES + 1)
            #        self.indices[j+4] = (tri + vi + 1) 
            #        self.indices[j+5] = (tri + vi - NUM_VERTICES)
            #        j += 6

            self.afterFly = False
            self.segmentidx = i
            self.idxidx = j
            
        else:
            style = GcodeParser.FLY
            self.afterFly = True

        self.relative = absolute
        
    def do_G28(self, args):
        # G28: Move to Origin
        pass
        
    def do_G92(self, args):
        # G92: Set Position
        # this changes the current coords, without moving, so do not generate a segment
        
        # no axes mentioned == all axes to 0
        if not len(args.keys()):
            args = {"X":0.0, "Y":0.0, "Z":0.0, "E":0.0}

        if args.has_key("X"):
            x = args["X"]
            offset_x = self.offset[X] + self.relative[X] - x
        else:
            x = self.relative[X]
            offset_x = self.offset[X]

        if args.has_key("Y"):
            y = args["Y"]
            offset_y = self.offset[Y] + self.relative[Y] - y
        else:
            y = self.relative[Y]
            offset_y = self.offset[Y]

        if args.has_key("Z"):
            z = args["Z"]
            offset_z = self.offset[Z] + self.relative[Z] - z
        else:
            z = self.relative[Z]
            offset_z = self.offset[Z]

        if args.has_key("E"):
            e = args["E"]
            offset_e = self.offset[E] + self.relative[E] - e
        else:
            e = self.relative[E]
            offset_e = self.offset[E]

        self.offset = (offset_x, offset_y, offset_z, offset_e)
        self.relative = (x,y,z,e)     

    def setPrintMode(self, args):
        # TODO: Make sure vertices are added twice if sync/mirror mode is enabled. 
        # Was previously a responsibility of the renderer, but this has been removed
        if 'S' in args:
            if args['S'] == 0 or args['S'] == 1:
                self.printMode = 'normal'
            elif args['S'] == 2:
                self.printMode = 'sync'
                if 'X' in args:
                    self.syncOffset = args['X']
            elif args['S'] == 3:
                self.printMode = 'mirror'              

    def setRelative(self, isRelative):
        self.isRelative = isRelative
