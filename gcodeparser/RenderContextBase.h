#pragma once
class RenderContextBase
{
protected:
	int width, height;
public:
	RenderContextBase(int width, int height) { this->width = width; this->height = height; };
	virtual bool activate()=0;
	~RenderContextBase() {};
};

