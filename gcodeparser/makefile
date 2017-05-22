CC=gcc
CXX=g++ -std=gnu++11
RM=rm -f
CP=cp -f
MKDIR=mkdir -p
ODIR=build
CPPFLAGS=-g $(shell root-config --cflags)
INC=-I ../include
SRCS=renderer.cpp gcodeparser.cpp RenderContextEGL.cpp shader.cpp
OBJS=$(subst .cc,.o,$(SRCS))
LDFLAGS=-lm -L/opt/vc/lib -L/usr/local/lib -lEGL -lGLESv2 -lpng -lz
	
all: gcodeparser

gcodeparser: $(OBJS)
	$(MKDIR) $(ODIR)
	$(CP) *.glsl $(ODIR)/.
	$(CXX) $(LDFLAGS) $(INC) -o $(ODIR)/gcodeparser $(OBJS) $(LDLIBS) 

depend: .depend

.depend: $(SRCS)
	$(RM) ./.depend
	$(CXX) $(CPPFLAGS) -MM $^>>./.depend;

clean:
	$(RM) $(OBJS)

distclean: clean
	$(RM) *~ .depend

include .depend
