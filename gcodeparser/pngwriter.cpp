/*

pngwriter.cpp

We're breaking out of the class structure here, for better compatibility with libpng

*/
#include "pngwriter.h"

bool writePng(const char * imageFile, unsigned char * imgData, unsigned int width, unsigned int height)
{
	// Reset the error state
	png_err = false;

	// Open file for writing (binary mode)
	fpng = fopen(imageFile, "wb");
	if (fpng == NULL) {
		log_msg(error, "Could not open image file for writing");
		destroyPng();
		return false;
	}

	// Initialize write structure
	png_ptr = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, pngError, pngWarning);
	if (png_ptr == NULL) {
		log_msg(error, "Could not allocate PNG write struct");
		destroyPng();
		return false;
	}

	// Initialize info structure
	info_ptr = png_create_info_struct(png_ptr);
	if (info_ptr == NULL) {
		log_msg(error, "Could not allocate PNG info struct");
		destroyPng();
		return false;
	}

	// Initialize PNG IO, return if failed
	png_init_io(png_ptr, fpng);
	if (png_err) return false;

	// Write header (8 bit colour depth)
	png_set_IHDR(png_ptr, info_ptr, width, height,
		8, PNG_COLOR_TYPE_RGBA, PNG_INTERLACE_NONE,
		PNG_COMPRESSION_TYPE_BASE, PNG_FILTER_TYPE_BASE);
	if (png_err) return false;

	// Write image data row-by-row inversively (flip Y)
	png_bytepp rows = (png_bytepp)png_malloc(png_ptr, height * sizeof(png_bytep));

	if (rows == NULL)
	{
		log_msg(error, "Could not allocate memory for PNG image data");
		destroyPng();
		return false;
	}

	for (unsigned int i = 0; i < height; ++i) {
		rows[i] = &imgData[(height - i - 1) * width * 4];
	}

	png_set_rows(png_ptr, info_ptr, rows);
	if (png_err) return false;

	// Encode and write the PNG file
	png_write_png(png_ptr, info_ptr, PNG_TRANSFORM_IDENTITY, NULL);
	if (png_err) return false;

	png_write_end(png_ptr, info_ptr);
	if (png_err) return false;

	// Clean
	png_free(png_ptr, rows);
	destroyPng();

	return true;
}


// Set the error state to true (so the caller can return) and log a message
void pngError(png_structp png_ptr, png_const_charp error_msg)
{
	log_msg(error, (char*)error_msg);
	png_err = true;
	destroyPng();
}

// Log a warning message using our own log handler
void pngWarning(png_structp png_ptr, png_const_charp warning_msg)
{
	log_msg(warning, (char*)warning_msg);
}

// Free up PNG resources
void destroyPng()
{
	// Clean up
	if (fpng != NULL) fclose(fpng);
	if (info_ptr != NULL) png_free_data(png_ptr, info_ptr, PNG_FREE_ALL, -1);
	if (png_ptr != NULL) png_destroy_write_struct(&png_ptr, (png_infopp)NULL);
}
