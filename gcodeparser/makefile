CC=gcc
CXX=g++ -std=gnu++11
RM=rm -f
MKDIR=mkdir -p
ODIR=build
CPPFLAGS=-g
INC=-I /usr/include/libpng12 -I ../include -I /usr/include/python2.7
SRCS=renderer.cpp gcodeparser.cpp RenderContextEGL.cpp RenderContextGLFW.cpp shader.cpp interface.cpp
OBJS=$(subst .cc,.o,$(SRCS))
LDFLAGS=-lm -L/opt/vc/lib -L/usr/local/lib -lEGL -lGLESv2 -lpng -lz -lpython2.7
	
all: gcodeparser

gcodeparser: $(OBJS)
	$(MKDIR) $(ODIR)
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
