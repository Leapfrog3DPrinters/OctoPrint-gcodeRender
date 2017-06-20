#include "shader.h"

using namespace std;

// Create an OpenGL(ES) shader program using the given source code
bool loadShaders(const char * vertexShaderSource, const char * fragmentShaderSource, GLuint * program, GLuint * vertexShader, GLuint * fragmentShader)
{
	GLint result = GL_FALSE;
	int infoLogLength;

	// Create the shaders
	GLuint vertexShaderId = glCreateShader(GL_VERTEX_SHADER);
	GLuint fragmentShaderId = glCreateShader(GL_FRAGMENT_SHADER);

	*vertexShader = vertexShaderId;
	*fragmentShader = fragmentShaderId;

	// Compile Vertex Shader
	log_msg(debug, "Compiling vertex shader");
	
	glShaderSource(vertexShaderId, 1, &vertexShaderSource, NULL);
	glCompileShader(vertexShaderId);

	// Check Vertex Shader
	glGetShaderiv(vertexShaderId, GL_COMPILE_STATUS, &result);
	glGetShaderiv(vertexShaderId, GL_INFO_LOG_LENGTH, &infoLogLength);
	if (infoLogLength > 0) {
		std::vector<char> vertexShaderErrorMessage(infoLogLength + 1);
		glGetShaderInfoLog(vertexShaderId, infoLogLength, NULL, &vertexShaderErrorMessage[0]);
		log_msg(debug, &vertexShaderErrorMessage[0]);
	}

	// Compile Fragment Shader
	log_msg(debug, "Compiling fragment shader");

	glShaderSource(fragmentShaderId, 1, &fragmentShaderSource, NULL);
	glCompileShader(fragmentShaderId);

	// Check Fragment Shader
	glGetShaderiv(fragmentShaderId, GL_COMPILE_STATUS, &result);
	glGetShaderiv(fragmentShaderId, GL_INFO_LOG_LENGTH, &infoLogLength);
	if (infoLogLength > 0) {
		std::vector<char> fragmentShaderErrorMessage(infoLogLength + 1);
		glGetShaderInfoLog(fragmentShaderId, infoLogLength, NULL, &fragmentShaderErrorMessage[0]);
		log_msg(debug, &fragmentShaderErrorMessage[0]);
	}

	// Link the program
	log_msg(debug, "Linking program");
	GLuint programId = glCreateProgram();

	*program = programId;

	glAttachShader(programId, vertexShaderId);
	glAttachShader(programId, fragmentShaderId);
	glLinkProgram(programId);

	// Check the program
	glGetProgramiv(programId, GL_LINK_STATUS, &result);
	glGetProgramiv(programId, GL_INFO_LOG_LENGTH, &infoLogLength);
	if (infoLogLength > 0) {
		std::vector<char> programErrorMessage(infoLogLength + 1);
		glGetProgramInfoLog(programId, infoLogLength, NULL, &programErrorMessage[0]);
		log_msg(debug, &programErrorMessage[0]);
	}

	return result == GL_TRUE;
}

// Unloads a given program from GPU memory
void unloadShaders(GLuint program, GLuint vertexShader, GLuint fragmentShader)
{
	glDetachShader(program, vertexShader);
	glDetachShader(program, fragmentShader);
	
	glDeleteShader(vertexShader);
	glDeleteShader(fragmentShader);

	glDeleteProgram(program);
}
