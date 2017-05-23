#include "shader.h"

using namespace std;

//GLuint LoadShaders(const char * vertex_file_path,const char * fragment_file_path){
//
//	// Read the Vertex Shader code from the file
//	std::string VertexShaderCode;
//	std::ifstream VertexShaderStream(vertex_file_path, std::ios::in);
//	if(VertexShaderStream.is_open()){
//		std::string Line = "";
//		while(getline(VertexShaderStream, Line))
//			VertexShaderCode += "\n" + Line;
//		VertexShaderStream.close();
//	}else{
//		printf("Impossible to open %s. Are you in the right directory ? \n", vertex_file_path);
//		getchar();
//		return 0;
//	}
//
//	// Read the Fragment Shader code from the file
//	std::string FragmentShaderCode;
//	std::ifstream FragmentShaderStream(fragment_file_path, std::ios::in);
//	if(FragmentShaderStream.is_open()){
//		std::string Line = "";
//		while(getline(FragmentShaderStream, Line))
//			FragmentShaderCode += "\n" + Line;
//		FragmentShaderStream.close();
//	}
//
//
//	char const * VertexSourcePointer = VertexShaderCode.c_str();
//	char const * FragmentSourcePointer = FragmentShaderCode.c_str();
//
//	return LoadShadersFromSource(VertexSourcePointer, FragmentSourcePointer);
//}

GLuint LoadShadersFromSource(const char * vertex_shader, const char * fragment_shader, GLuint * program_id, GLuint * vertex_shader_id, GLuint * fragment_shader_id)
{
	GLint Result = GL_FALSE;
	int InfoLogLength;

	// Create the shaders
	GLuint VertexShaderID = glCreateShader(GL_VERTEX_SHADER);

	*vertex_shader_id = VertexShaderID;

	GLuint FragmentShaderID = glCreateShader(GL_FRAGMENT_SHADER);

	*fragment_shader_id = FragmentShaderID;

	// Compile Vertex Shader
	printf("Compiling vertex shader\n");
	
	glShaderSource(VertexShaderID, 1, &vertex_shader, NULL);
	glCompileShader(VertexShaderID);

	// Check Vertex Shader
	glGetShaderiv(VertexShaderID, GL_COMPILE_STATUS, &Result);
	glGetShaderiv(VertexShaderID, GL_INFO_LOG_LENGTH, &InfoLogLength);
	if (InfoLogLength > 0) {
		std::vector<char> VertexShaderErrorMessage(InfoLogLength + 1);
		glGetShaderInfoLog(VertexShaderID, InfoLogLength, NULL, &VertexShaderErrorMessage[0]);
		printf("%s\n", &VertexShaderErrorMessage[0]);
	}


	// Compile Fragment Shader
	printf("Compiling fragment shader\n");

	glShaderSource(FragmentShaderID, 1, &fragment_shader, NULL);
	glCompileShader(FragmentShaderID);

	// Check Fragment Shader
	glGetShaderiv(FragmentShaderID, GL_COMPILE_STATUS, &Result);
	glGetShaderiv(FragmentShaderID, GL_INFO_LOG_LENGTH, &InfoLogLength);
	if (InfoLogLength > 0) {
		std::vector<char> FragmentShaderErrorMessage(InfoLogLength + 1);
		glGetShaderInfoLog(FragmentShaderID, InfoLogLength, NULL, &FragmentShaderErrorMessage[0]);
		printf("%s\n", &FragmentShaderErrorMessage[0]);
	}



	// Link the program
	printf("Linking program\n");
	GLuint ProgramID = glCreateProgram();

	*program_id = ProgramID;

	glAttachShader(ProgramID, VertexShaderID);
	glAttachShader(ProgramID, FragmentShaderID);
	glLinkProgram(ProgramID);

	// Check the program
	glGetProgramiv(ProgramID, GL_LINK_STATUS, &Result);
	glGetProgramiv(ProgramID, GL_INFO_LOG_LENGTH, &InfoLogLength);
	if (InfoLogLength > 0) {
		std::vector<char> ProgramErrorMessage(InfoLogLength + 1);
		glGetProgramInfoLog(ProgramID, InfoLogLength, NULL, &ProgramErrorMessage[0]);
		printf("%s\n", &ProgramErrorMessage[0]);
	}

	return ProgramID;
}

void UnloadShaders(GLuint program_id, GLuint vertex_shader_id, GLuint fragment_shader_id)
{
	glDetachShader(program_id, vertex_shader_id);
	glDetachShader(program_id, fragment_shader_id);
	
	glDeleteShader(vertex_shader_id);
	glDeleteShader(fragment_shader_id);

	glDeleteProgram(program_id);
}
