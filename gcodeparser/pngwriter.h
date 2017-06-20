/* 
pngwriter.h

Header file for the PNG writer.

*/

#ifndef PNGWRITER_H
#define PNGWRITER_H 1

// Include libpng
#include <png.h>

#include "helpers.h"

bool writePng(const char * imageFile, unsigned char * imgData, unsigned int width, unsigned int height);
void pngError(png_structp png_ptr,	png_const_charp error_msg);
void pngWarning(png_structp png_ptr,	png_const_charp warning_msg);

void destroyPng();


#endif // !PNGWRITER_H

