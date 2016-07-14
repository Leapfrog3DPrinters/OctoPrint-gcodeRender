#!/usr/bin/env python

import math, time

class GcodeParser:
    
    def __init__(self):
        self.model = GcodeModel(self)
        self.parts_to_parse = set(["BRIM", "CONTOUR", "LAYER_NO", "layer", "skirt", "solid", "outer", "inner"]) 
        self.skip_gcode_part = False # Ensure first bits are parsed no matter what
        
        
    def parseFile(self, path):
        do_g1 = self.model.do_G1
        # read the gcode file
        #t0 = time.clock()
        with open(path, 'r') as f:
            # init line counter
            self.lineNb = 0
            # for all lines
            for line in f:
                self.lineNb += 1
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
        #t1 = time.clock()    
        #print "Parse: %s" % (t1-t0)
        self.model.postProcess()
        #t2 = time.clock()
        #print "Post process: %s" % (t2-t1)

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

    def warn(self, msg):
        pass
        #print "[WARN] Line %d: %s (Text:'%s')" % (self.lineNb, msg, self.line)
        
    def error(self, msg):
        pass
        #print "[ERROR] Line %d: %s (Text:'%s')" % (self.lineNb, msg, self.line)
        #raise Exception("[ERROR] Line %d: %s (Text:'%s')" % (self.lineNb, msg, self.line))

class BBox(object):
    
    def __init__(self, coords):
        self.xmin = self.xmax = coords["X"]
        self.ymin = self.ymax = coords["Y"]
        self.zmin = self.zmax = coords["Z"]
        
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
        self.xmin = min(self.xmin, coords["X"])
        self.xmax = max(self.xmax, coords["X"])
        self.ymin = min(self.ymin, coords["Y"])
        self.ymax = max(self.ymax, coords["Y"])
        self.zmin = min(self.zmin, coords["Z"])
        self.zmax = max(self.zmax, coords["Z"])
        
class GcodeModel:
    
    def __init__(self, parser):
        # save parser for messages
        self.parser = parser
        # latest coordinates & extrusion relative to offset, feedrate
        self.relative = {
            "X":0.0,
            "Y":0.0,
            "Z":0.0,
            "F":0.0,
            "E":0.0}
        # offsets for relative coordinates and position reset (G92)
        self.offset = {
            "X":0.0,
            "Y":0.0,
            "Z":0.0,
            "E":0.0}
        # if true, args for move (G1) are given relatively (default: absolute)
        self.isRelative = False
        # the segments
        self.segments = []
        self.layers = None
        self.distance = None
        self.extrudate = None
        self.bbox = None
        self.printMode = 'normal'
        self.syncOffset = -1
        self._appendsegment = self.segments.append
    
    def do_G1(self, args):
        # G0/G1: Rapid/Controlled move
        # clone previous coords
        coords = dict(self.relative)
        # update changed coords
        for axis in args.keys():
            if coords.has_key(axis):
                if self.isRelative:
                    coords[axis] += args[axis]
                else:
                    coords[axis] = args[axis]
            else:
                self.warn("Unknown axis '%s'"%axis)
        # build segment
        absolute = {
            "X": self.offset["X"] + coords["X"],
            "Y": self.offset["Y"] + coords["Y"],
            "Z": self.offset["Z"] + coords["Z"],
            "F": coords["F"],    # no feedrate offset
            "E": self.offset["E"] + coords["E"]
        }
        seg = Segment(
            absolute)
        self.addSegment(seg)
        # update model coords
        self.relative = coords
        
    def do_G28(self, args):
        # G28: Move to Origin
        self.warn("G28 unimplemented")
        
    def do_G92(self, args):
        # G92: Set Position
        # this changes the current coords, without moving, so do not generate a segment
        
        # no axes mentioned == all axes to 0
        if not len(args.keys()):
            args = {"X":0.0, "Y":0.0, "Z":0.0, "E":0.0}
        # update specified axes
        for axis in args.keys():
            if self.offset.has_key(axis):
                # transfer value from relative to offset
                self.offset[axis] += self.relative[axis] - args[axis]
                self.relative[axis] = args[axis]
            else:
                self.warn("Unknown axis '%s'"%axis)
    def setPrintMode(self, args):
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
        
    def addSegment(self, segment):
        #self.segments.append(segment)
        self._appendsegment(segment) #Faster than above
        
    def warn(self, msg):
        self.parser.warn(msg)
        
    def error(self, msg):
        self.parser.error(msg)
        
    def postProcess(self):
        # init model bbox
        self.bbox = None

        coords = {
            "X":0.0,
            "Y":0.0,
            "Z":0.0,
            "F":0.0,
            "E":0.0}

        for seg in self.segments:
            style = "fly"
            if (
                (seg.coords["X"] == coords["X"]) and
                (seg.coords["Y"] == coords["Y"]) and
                (seg.coords["E"] != coords["E"]) ):
                    seg.style = "retract" if (seg.coords["E"] < coords["E"]) else "restore"
            
            # some horizontal movement, and positive extruder movement: extrusion
            if (
                ( (seg.coords["X"] != coords["X"]) or (seg.coords["Y"] != coords["Y"]) ) and
                (seg.coords["E"] > coords["E"]) ):
                seg.style = "extrude"
                if self.bbox:
                    self.bbox.extend(coords)
                else:
                    self.bbox = BBox(coords)

            coords = seg.coords
           
class Segment:
    def __init__(self, coords):
        self.coords = coords
        self.style = None
        self.layerIdx = None
        self.distance = None
        self.extrudate = None
        
class Layer:
    def __init__(self, Z):
        self.Z = Z
        self.segments = []
        self.distance = None
        self.extrudate = None
