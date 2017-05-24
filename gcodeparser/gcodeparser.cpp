#include "gcodeparser.h"

GcodeParser::GcodeParser(const char *file, uint8_t drawType, BBox bedBbox, const unsigned int throttlingInterval, const unsigned int throttlingDuration)
{
	this->file = file;

	this->throttlingDuration = throttlingDuration;
	this->throttlingInterval = throttlingInterval;

	this->number_of_lines = get_number_of_lines();
	this->draw = drawType;

	// Mirror the bounding box of the bed to that of the part, so we know when we have valid
	// part dimensions or not
	this->bedBbox = bedBbox;

	this->bbox.xmin = bedBbox.xmax;
	this->bbox.xmax = bedBbox.xmin;
	this->bbox.ymin = bedBbox.ymax;
	this->bbox.ymax = bedBbox.ymin;
	this->bbox.zmin = bedBbox.zmax;
	this->bbox.zmax = bedBbox.zmin;

	// create a file-reading object
	fin.open(file);
}

GcodeParser::~GcodeParser()
{
	fin.close();
}

float GcodeParser::code_value(const char * line)
{
	if (strchr_pointer != NULL)
		return strtof(&line[strchr_pointer - line + 1], NULL);
	else
		return 0;
}

bool GcodeParser::code_seen(const char code, const char * line)
{
	strchr_pointer = strchr(line, code);

	return (strchr_pointer != NULL);
}

void GcodeParser::build_vertices_lines()
{
	// from
	vertices[vertex_i]	   = absolute[X] + offset[X];
	vertices[vertex_i + 1] = absolute[Y] + offset[Y];
	vertices[vertex_i + 2] = absolute[Z] + offset[Z];

	// normals
	//vertices[vertex_i + 3] = 0;
	//vertices[vertex_i + 4] = 0;
	//vertices[vertex_i + 5] = 0;

	// to
	vertices[vertex_i + 3] = relative[X];
	vertices[vertex_i + 4] = relative[Y];
	vertices[vertex_i + 5] = relative[Z];

	// normals
	//vertices[vertex_i + 9] = 0;
	//vertices[vertex_i + 10] = 0;
	//vertices[vertex_i + 11] = 0;

	int vi = vertex_i / 3;

	indices[index_i] = vi;
	indices[index_i + 1] = vi + 1;

	vertex_i += 6;
	index_i += 2;
}

void GcodeParser::cross(const float v1[3], const float v2[3], float * result)
{
	result[0] = v1[Y] * v2[Z] - v2[Y] * v1[Z];
	result[1] = v1[Z] * v2[X] - v2[Z] * v1[X];
	result[2] = v1[X] * v2[Y] - v2[X] * v1[Y];
}

void GcodeParser::normalize(const float * v, float * result)
{
	float l = sqrt(v[X] * v[X] + v[Y] * v[Y] + v[Z] * v[Z]);
	result[0] = v[X] / l;
	result[1] = v[Y] / l;
	result[2] = v[Z] / l;
}

void GcodeParser::build_vertices_tubes()
{
	int i = vertex_i;

	// Build a cylinder vertices
	float direction[3] = { absolute[X] + offset[X] - relative[X], absolute[Y] + offset[Y] - relative[Y], absolute[Z] + offset[Z] - relative[Z] };

	if (abs(direction[0]) <= eps && abs(direction[1]) <= eps && abs(direction[2]) <= eps)
		return;

	float temp1[3] = { 0, 0, 0 };
	float temp2[3] = { 0, 0, 0 };
	float perp1[3] = { 0, 0, 0 };
	float perp2[3] = { 0, 0, 0 };

	cross(direction, dirA, temp1);

	if (abs(temp1[0]) <= eps && abs(temp1[1]) <= eps && abs(temp1[2]) <= eps)
		cross(direction, dirB, temp1);

	normalize(temp1, perp1);
	cross(direction, perp1, temp2);
	normalize(temp2, perp2);

	float angle = 0.0;

	float sina, cosa;

	for (int k = 0; k < NUM_VERTICES; ++k)
	{
		sina = sin(angle);
		cosa = cos(angle);

		// Calculate normals first
		vertices[i + 3] = sina * (perp1[0]) + cosa * (perp2[0]);
		vertices[i + 4] = sina*perp1[1] + cosa*perp2[1];
		vertices[i + 5] = sina*perp1[2] + cosa*perp2[2];

		// Copy them for the second ring of vertices
		vertices[i + 9] = vertices[i + 3];
		vertices[i + 10] = vertices[i + 4];
		vertices[i + 11] = vertices[i + 5];

		// Calculate position of first ring
		vertices[i] = R * vertices[i + 3] + relative[X];
		vertices[i + 1] = R * vertices[i + 4] + relative[Y];
		vertices[i + 2] = R * vertices[i + 5] + relative[Z];

		// Calculate position of second ring
		vertices[i + 6] = R * vertices[i + 3] + absolute[X] + offset[X];
		vertices[i + 7] = R * vertices[i + 4] + absolute[Y] + offset[Y];
		vertices[i + 8] = R * vertices[i + 5] + absolute[Z] + offset[Z];

		angle += STEP_SIZE;

		i += 12;
	}

	// Build the faces of the cylinder
	int vi = vertex_i / 6;
	int j = index_i;
	int tri = 0;
	for (; tri < (NUM_VERTICES - 1) * 2; tri += 2) {
		indices[j] = (tri + vi);
		indices[j + 1] = (tri + vi + 1);
		indices[j + 2] = (tri + vi + 2);
		indices[j + 3] = (tri + vi + 1);
		indices[j + 4] = (tri + vi + 3);
		indices[j + 5] = (tri + vi + 2);
		j += 6;
	}

	// Close the gap
	indices[j] = (tri + vi);
	indices[j + 1] = (tri + vi + 1);
	indices[j + 2] = (vi);
	indices[j + 3] = (tri + vi + 1);
	indices[j + 4] = (vi + 1);
	indices[j + 5] = (vi);
	j += 6;


	// Link the tubes
	if (!after_fly)
	{
		for (int tri = 0; tri < (NUM_VERTICES - 1); ++tri)
		{
			indices[j] = (tri + vi);
			indices[j + 1] = (tri + vi + 1);
			indices[j + 2] = (tri + vi - NUM_VERTICES);
			indices[j + 3] = (tri + vi - NUM_VERTICES + 1);
			indices[j + 4] = (tri + vi + 1);
			indices[j + 5] = (tri + vi - NUM_VERTICES);
			j += 6;
		}
	}
	
	vertex_i = i;
	index_i = j;
}

void GcodeParser::parse_g1(const char * line)
{
	//TODO: Work with glm vectors here

	float rel[NUMCOORDS] = {};

	if (is_relative) 
		memcpy(&rel, &relative, NUMCOORDS * sizeof(float));

	for (int i = 0; i < NUMCOORDS; ++i)
	{
		if (code_seen(coords[i], line))
			absolute[i] = code_value(line) + rel[i];
		else
			absolute[i] = relative[i];
	}

	if (absolute[E] - relative[E] > eps
		&&
		(abs(absolute[X] + offset[X] - relative[X]) >= eps || abs(absolute[Y] + offset[Y] - relative[Y]) >= eps || abs(absolute[Z] + offset[Z] - relative[Z]) >= eps))
	{
		style = EXTRUDE;

		// Update the part's bounding box if it is within
		// the bounding box of the bed. (i.e. don't include
		// wiping sequences etc.)

		if(absolute[X] >= bedBbox.xmin)
			bbox.xmin = min(bbox.xmin, absolute[X]);

		if (absolute[X] <= bedBbox.xmax)
			bbox.xmax = max(bbox.xmax, absolute[X]);

		if (absolute[Y] >= bedBbox.ymin)
			bbox.ymin = min(bbox.ymin, absolute[Y]);

		if (absolute[Y] <= bedBbox.ymax)
			bbox.ymax = max(bbox.ymax, absolute[Y]);
		
		if (absolute[Z] >= bedBbox.zmin)
			bbox.zmin = min(bbox.zmin, absolute[Z]);

		if (absolute[Z] <= bedBbox.zmax)
			bbox.zmax = max(bbox.zmax, absolute[Z]);

		if(draw == DRAW_LINES)
			build_vertices_lines();
		else
			build_vertices_tubes();

		after_fly = false;
	}
	else {
		style = FLY;
		after_fly = true;
	}

	memcpy(&relative, &absolute, NUMCOORDS * sizeof(float));

}

void GcodeParser::parse_g92(const char * line)
{
	float val;
	for (int i = 0; i < NUMCOORDS; ++i)
	{
		if (code_seen(coords[i], line))
		{
			val = code_value(line);
			offset[i] = offset[i] + relative[i] - val;
			relative[i] = val;
		}
	}
}

int GcodeParser::get_number_of_lines()
{
	const int SZ = 1024 * 1024;
	char * buff = new char[SZ];
	ifstream ifs(file);
	while (int cc = file_read(ifs, buff, SZ)) {
		number_of_lines += count_lines(buff, cc);
	}
	ifs.close();
	delete buff;

	return number_of_lines;
}

unsigned int GcodeParser::file_read(istream & is, char * buff, int buff_size) {
	is.read(buff, buff_size);
	return (unsigned int)is.gcount();
}

unsigned int GcodeParser::count_lines(const char * buff, int buff_size) {
	int newlines = 0;
	for (int i = 0; i < buff_size; i++) {
		if (buff[i] == '\n') {
			newlines++;
		}
	}
	return newlines;
}

void GcodeParser::get_buffer_size(unsigned int * vertices_size, unsigned int * indices_size)
{
	if (draw == DRAW_LINES)
	{
		*vertices_size = 6 * sizeof *vertices;
		*indices_size = 2 * sizeof *indices;
	}
	else
	{
		*vertices_size = NUM_VERTICES * 12 * sizeof *vertices;
		*indices_size = NUM_VERTICES * 12 * sizeof *indices;
	}
}

unsigned int GcodeParser::get_vertices(const unsigned int n_lines, int * nVertices, float * vertices, int * nIndices, short * indices)
{
	if (!fin.good())
		return 0; // exit if file not found

	unsigned int n = 0; // a for-loop index
	char line[MAX_CHARS_PER_LINE]; // line buffer

	this->vertices = vertices;
	this->indices = indices;

	vertex_i = 0;
	index_i = 0;

	// read each line of the file
	while (!fin.eof())
	{
		fin.getline(line, MAX_CHARS_PER_LINE);
		parse_line(line);

		if (throttlingInterval > 0 && n % throttlingInterval == 0)
			Sleep(throttlingDuration);

		n++;
		if (n-1 >= n_lines)
			break;
	}

	*nVertices = vertex_i + 1;
	*nIndices = index_i + 1;

	return n;
}

void GcodeParser::parse_line(const char *line)
{
	// parse the line into blank-delimited tokens

	if (!skip && line[0] == 'G')
	{
		if (line[1] == '1' || line[1] == '0')
			parse_g1(line);
		else if (line[1] == '9')
		{
			if (line[2] == '0')
				is_relative = false;
			else if (line[2] == '1')
				is_relative = true;
			else if (line[2] == '2')
				parse_g92(line);
		}
	}
	else if (line[0] == ';')
	{
		skip = true;

		for (int i = 0; i < nincludes; ++i)
		{
			if (strstr(line, includes[i]))
			{
				skip = false;
				break;
			}
		}
	}
}

bool GcodeParser::get_bbox(BBox * bbox)
{
	*bbox = this->bbox;

	return this->bbox.xmin < bedBbox.xmax
		&& this->bbox.xmax > bedBbox.xmin
		&& this->bbox.ymin < bedBbox.ymax
		&& this->bbox.ymax > bedBbox.ymin
		&& this->bbox.zmin < bedBbox.zmax
		&& this->bbox.zmax > bedBbox.zmin;

}


