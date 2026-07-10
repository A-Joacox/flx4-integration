// Fase 3: fractal Julia renderizado por fragment shader, controlable por teclado.
// Los mismos uniforms se conectan al bridge OSC en Fase 4.
//
// Controles:
//   Flechas      : mover offset          | W / S      : zoom in / out
//   A / D        : c.x -/+               | Z / C      : c.y -/+
//   Q / E        : iteraciones -/+       | H / J      : hue shift -/+
//   ESPACIO      : "beat" manual (flash) | R          : reset
//   ESC          : salir
//
// El titulo de la ventana muestra los FPS (verificar 60 estables a 1080p).

#include <glad/glad.h>
#include <GLFW/glfw3.h>

#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

namespace {

struct Params {
    float cx = -0.7f, cy = 0.27015f;
    float zoom = 0.8f;
    float offx = 0.0f, offy = 0.0f;
    int   iterations = 200;
    float hueShift = 0.0f;
    float beat = 0.0f;  // 1.0 al disparar, decae por frame
};

std::string loadFile(const char* path) {
    std::ifstream f(path);
    if (!f) return {};
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

std::string findShaderSource(const char* name) {
    const char* prefixes[] = {"shaders/", "../shaders/", "../../shaders/",
                              "../../../shaders/", "../../../../shaders/"};
    for (const char* p : prefixes) {
        std::string src = loadFile((std::string(p) + name).c_str());
        if (!src.empty()) {
            std::printf("shader: %s%s\n", p, name);
            return src;
        }
    }
    return {};
}

GLuint compile(GLenum type, const char* src) {
    GLuint s = glCreateShader(type);
    glShaderSource(s, 1, &src, nullptr);
    glCompileShader(s);
    GLint ok = 0;
    glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char log[2048];
        glGetShaderInfoLog(s, sizeof log, nullptr, log);
        std::fprintf(stderr, "error compilando shader:\n%s\n", log);
        return 0;
    }
    return s;
}

const char* kVertexSrc = R"(#version 460 core
// fullscreen triangle sin VBO
void main() {
    vec2 pos = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    gl_Position = vec4(pos * 2.0 - 1.0, 0.0, 1.0);
}
)";

Params params;

void handleKeys(GLFWwindow* win, float dt) {
    auto down = [&](int k) { return glfwGetKey(win, k) == GLFW_PRESS; };
    float panSpeed = 1.0f * dt / params.zoom;
    float zoomSpeed = 1.5f * dt;

    if (down(GLFW_KEY_LEFT))  params.offx -= panSpeed;
    if (down(GLFW_KEY_RIGHT)) params.offx += panSpeed;
    if (down(GLFW_KEY_DOWN))  params.offy -= panSpeed;
    if (down(GLFW_KEY_UP))    params.offy += panSpeed;
    if (down(GLFW_KEY_W)) params.zoom *= 1.0f + zoomSpeed;
    if (down(GLFW_KEY_S)) params.zoom /= 1.0f + zoomSpeed;
    if (down(GLFW_KEY_A)) params.cx -= 0.2f * dt;
    if (down(GLFW_KEY_D)) params.cx += 0.2f * dt;
    if (down(GLFW_KEY_Z)) params.cy -= 0.2f * dt;
    if (down(GLFW_KEY_C)) params.cy += 0.2f * dt;
    if (down(GLFW_KEY_H)) params.hueShift -= 0.3f * dt;
    if (down(GLFW_KEY_J)) params.hueShift += 0.3f * dt;
}

void keyCallback(GLFWwindow* win, int key, int, int action, int) {
    if (action != GLFW_PRESS) return;
    switch (key) {
        case GLFW_KEY_ESCAPE: glfwSetWindowShouldClose(win, GLFW_TRUE); break;
        case GLFW_KEY_SPACE:  params.beat = 1.0f; break;
        case GLFW_KEY_Q:      params.iterations = params.iterations > 40 ? params.iterations - 20 : 20; break;
        case GLFW_KEY_E:      params.iterations = params.iterations < 980 ? params.iterations + 20 : 1000; break;
        case GLFW_KEY_R:      params = Params{}; break;
        default: break;
    }
}

} // namespace

int main() {
    if (!glfwInit()) {
        std::fprintf(stderr, "glfwInit fallo\n");
        return 1;
    }
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 6);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    GLFWwindow* window = glfwCreateWindow(1920, 1080, "flx4-render", nullptr, nullptr);
    if (!window) {
        std::fprintf(stderr, "no se pudo crear la ventana\n");
        glfwTerminate();
        return 1;
    }
    glfwMakeContextCurrent(window);
    glfwSwapInterval(1);
    glfwSetKeyCallback(window, keyCallback);

    if (!gladLoadGLLoader(reinterpret_cast<GLADloadproc>(glfwGetProcAddress))) {
        std::fprintf(stderr, "gladLoadGLLoader fallo\n");
        glfwTerminate();
        return 1;
    }
    std::printf("OpenGL %s - %s\n", glGetString(GL_VERSION), glGetString(GL_RENDERER));

    std::string fragSrc = findShaderSource("julia.frag");
    if (fragSrc.empty()) {
        std::fprintf(stderr, "no se encontro shaders/julia.frag (correr desde la raiz del repo o render/)\n");
        glfwTerminate();
        return 1;
    }

    GLuint vs = compile(GL_VERTEX_SHADER, kVertexSrc);
    GLuint fs = compile(GL_FRAGMENT_SHADER, fragSrc.c_str());
    if (!vs || !fs) { glfwTerminate(); return 1; }

    GLuint prog = glCreateProgram();
    glAttachShader(prog, vs);
    glAttachShader(prog, fs);
    glLinkProgram(prog);
    GLint ok = 0;
    glGetProgramiv(prog, GL_LINK_STATUS, &ok);
    if (!ok) {
        char log[2048];
        glGetProgramInfoLog(prog, sizeof log, nullptr, log);
        std::fprintf(stderr, "error linkeando programa:\n%s\n", log);
        glfwTerminate();
        return 1;
    }
    glDeleteShader(vs);
    glDeleteShader(fs);

    GLuint vao;
    glGenVertexArrays(1, &vao);
    glBindVertexArray(vao);
    glUseProgram(prog);

    const GLint uRes  = glGetUniformLocation(prog, "uResolution");
    const GLint uTime = glGetUniformLocation(prog, "uTime");
    const GLint uC    = glGetUniformLocation(prog, "uC");
    const GLint uZoom = glGetUniformLocation(prog, "uZoom");
    const GLint uOff  = glGetUniformLocation(prog, "uOffset");
    const GLint uIter = glGetUniformLocation(prog, "uIterations");
    const GLint uHue  = glGetUniformLocation(prog, "uHueShift");
    const GLint uBeat = glGetUniformLocation(prog, "uBeat");

    double lastT = glfwGetTime();
    double fpsT = lastT;
    int frames = 0;

    while (!glfwWindowShouldClose(window)) {
        double now = glfwGetTime();
        float dt = static_cast<float>(now - lastT);
        lastT = now;

        handleKeys(window, dt);
        params.beat = std::fmax(0.0f, params.beat - 3.0f * dt);  // decae en ~0.33s

        int w, h;
        glfwGetFramebufferSize(window, &w, &h);
        glViewport(0, 0, w, h);

        glUniform2f(uRes, static_cast<float>(w), static_cast<float>(h));
        glUniform1f(uTime, static_cast<float>(now));
        glUniform2f(uC, params.cx, params.cy);
        glUniform1f(uZoom, params.zoom);
        glUniform2f(uOff, params.offx, params.offy);
        glUniform1i(uIter, params.iterations);
        glUniform1f(uHue, params.hueShift);
        glUniform1f(uBeat, params.beat);

        glDrawArrays(GL_TRIANGLES, 0, 3);
        glfwSwapBuffers(window);
        glfwPollEvents();

        ++frames;
        if (now - fpsT >= 1.0) {
            char title[128];
            std::snprintf(title, sizeof title,
                          "flx4-render | %d fps | iter=%d zoom=%.2f c=(%.3f,%.3f)",
                          frames, params.iterations, params.zoom, params.cx, params.cy);
            glfwSetWindowTitle(window, title);
            frames = 0;
            fpsT = now;
        }
    }

    glfwDestroyWindow(window);
    glfwTerminate();
    return 0;
}
