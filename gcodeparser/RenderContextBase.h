/*

RenderContextBase.h

Base class definition of for the render contexts

*/


#ifndef RENDERCONTEXTBASE_H
#define RENDERCONTEXTBASE_H 1

/*
Base class for render contexts (EGL / GLFW / ...)
*/
class RenderContextBase
{
protected:
	int width, height;
public:
	RenderContextBase(int width, int height) { this->width = width; this->height = height; };
	virtual bool activate() = 0;
	~RenderContextBase() {};
};



#endif /* RENDERCONTEXTBASE_H */
