// Fase 3: fractal Julia renderizado por fragment shader, controlable por teclado.
// Los mismos uniforms se conectan al bridge OSC en Fase 4.
//
// Controles:
//   1 / 2 / 3    : modo manual / morph (c orbita solo) / tunel infinito
//   Flechas      : mover offset          | W / S      : zoom in / out
//   A / D        : c.x -/+ (o velocidad de morph/tunel en modos 1-2)
//   Z / C        : c.y -/+               | Q / E      : iteraciones -/+
//   H / J        : hue shift -/+         | ESPACIO    : "beat" manual (flash)
//   R            : reset                 | ESC        : salir
//
// El titulo de la ventana muestra los FPS (verificar 60 estables a 1080p).
//
// Fase 4: escucha OSC en 127.0.0.1:9000 (correr bridge/bridge.py en paralelo).
//   /audio/bass|mid|treble -> reactividad, /audio/beat -> flash
//   /ctl/zoom /ctl/speed /ctl/hue -> knobs del FLX4

#include <glad/glad.h>
#include <GLFW/glfw3.h>

#include "osc_receiver.h"

#include <cmath>
#include <cstdio>
#include <cstring>
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
    float beat = 0.0f;      // 1.0 al disparar, decae por frame
    int   mode = 1;         // 0 manual, 1 morph, 2 tunel (arranca en morph)
    float speed = 1.0f;     // multiplicador de autopilot (A/D en modos 1-2)
    float morphPhase = 0.0f;
    float travel = 0.0f;    // profundidad acumulada del tunel
    // audio (0 hasta Fase 4; el bridge OSC los va a llenar)
    float bass = 0.0f, mid = 0.0f, treble = 0.0f;
    // targets OSC: el loop hace lerp hacia estos (evita saltos bruscos del MIDI)
    float zoomTarget = 0.8f, speedTarget = 1.0f, hueTarget = 0.0f;
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
    if (down(GLFW_KEY_W)) params.zoomTarget *= 1.0f + zoomSpeed;
    if (down(GLFW_KEY_S)) params.zoomTarget /= 1.0f + zoomSpeed;
    if (params.mode == 0) {
        if (down(GLFW_KEY_A)) params.cx -= 0.2f * dt;
        if (down(GLFW_KEY_D)) params.cx += 0.2f * dt;
    } else {
        if (down(GLFW_KEY_A)) params.speedTarget = std::fmax(0.05f, params.speedTarget - 1.0f * dt);
        if (down(GLFW_KEY_D)) params.speedTarget = std::fmin(4.0f, params.speedTarget + 1.0f * dt);
    }
    if (down(GLFW_KEY_Z)) params.cy -= 0.2f * dt;
    if (down(GLFW_KEY_C)) params.cy += 0.2f * dt;
    if (down(GLFW_KEY_H)) params.hueTarget -= 0.3f * dt;
    if (down(GLFW_KEY_J)) params.hueTarget += 0.3f * dt;
}

void keyCallback(GLFWwindow* win, int key, int, int action, int) {
    if (action != GLFW_PRESS) return;
    switch (key) {
        case GLFW_KEY_ESCAPE: glfwSetWindowShouldClose(win, GLFW_TRUE); break;
        case GLFW_KEY_SPACE:  params.beat = 1.0f; break;
        case GLFW_KEY_Q:      params.iterations = params.iterations > 40 ? params.iterations - 20 : 20; break;
        case GLFW_KEY_E:      params.iterations = params.iterations < 980 ? params.iterations + 20 : 1000; break;
        case GLFW_KEY_R:      params = Params{}; break;
        case GLFW_KEY_1:      params.mode = 0; break;
        case GLFW_KEY_2:      params.mode = 1; break;
        case GLFW_KEY_3:      params.mode = 2; break;
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
    const GLint uMode = glGetUniformLocation(prog, "uMode");
    const GLint uTrav = glGetUniformLocation(prog, "uTravel");
    const GLint uBass = glGetUniformLocation(prog, "uBass");
    const GLint uMid  = glGetUniformLocation(prog, "uMid");
    const GLint uTreb = glGetUniformLocation(prog, "uTreble");

    OscReceiver osc;
    if (osc.init(9000)) {
        std::printf("OSC escuchando en 127.0.0.1:9000\n");
    } else {
        std::fprintf(stderr, "aviso: no se pudo abrir OSC :9000 (sigue sin audio/MIDI)\n");
    }

    double lastT = glfwGetTime();
    double fpsT = lastT;
    int frames = 0;

    while (!glfwWindowShouldClose(window)) {
        double now = glfwGetTime();
        float dt = static_cast<float>(now - lastT);
        lastT = now;

        handleKeys(window, dt);
        params.beat = std::fmax(0.0f, params.beat - 3.0f * dt);  // decae en ~0.33s

        osc.poll([](const char* addr, float v) {
            if      (!std::strcmp(addr, "/audio/bass"))   params.bass = v;
            else if (!std::strcmp(addr, "/audio/mid"))    params.mid = v;
            else if (!std::strcmp(addr, "/audio/treble")) params.treble = v;
            else if (!std::strcmp(addr, "/audio/beat"))   params.beat = 1.0f;
            else if (!std::strcmp(addr, "/ctl/zoom"))     params.zoomTarget = 0.4f * std::pow(7.5f, v);
            else if (!std::strcmp(addr, "/ctl/speed"))    params.speedTarget = 0.05f + 3.95f * v;
            else if (!std::strcmp(addr, "/ctl/hue"))      params.hueTarget = v;
            else if (!std::strcmp(addr, "/ctl/mode"))     params.mode = static_cast<int>(v + 0.5f);
            else if (!std::strcmp(addr, "/ctl/reset")) {
                float b = params.bass, m = params.mid, tr = params.treble;
                params = Params{};
                params.bass = b; params.mid = m; params.treble = tr;
            }
        });

        // suavizado exponencial hacia los targets OSC (~8 Hz de respuesta)
        float k = 1.0f - std::exp(-8.0f * dt);
        params.zoom     += k * (params.zoomTarget - params.zoom);
        params.speed    += k * (params.speedTarget - params.speed);
        params.hueShift += k * (params.hueTarget - params.hueShift);

        // autopilot: la musica va a modular esto mismo en Fase 4/5
        if (params.mode == 1) {
            // c recorre el borde de la cardioide de Mandelbrot: c = u/2 - u^2/4, u = e^(i*theta).
            // Sobre el borde los Julia son dendritas finas (nunca interior lleno).
            // "breath" respira apenas hacia afuera/adentro del borde para variar densidad.
            params.morphPhase += (0.08f + 0.20f * params.mid) * params.speed * dt;
            float th = params.morphPhase;
            // siempre apenas AFUERA del borde: adentro el Julia se llena de negro
            float breath = 1.012f + 0.008f * std::sin(th * 0.31f) + 0.008f * params.bass;
            float cx = 0.5f * std::cos(th) - 0.25f * std::cos(2.0f * th);
            float cy = 0.5f * std::sin(th) - 0.25f * std::sin(2.0f * th);
            params.cx = cx * breath;
            params.cy = cy * breath;
        } else if (params.mode == 2) {
            // el tunel avanza solo; el bass lo acelera (Fase 5)
            params.travel += (0.35f + 1.2f * params.bass + 0.5f * params.beat) * params.speed * dt;
            params.morphPhase += 0.05f * params.speed * dt;  // morph lento del c dentro del tunel
            params.cx = -0.745f + 0.06f * std::cos(params.morphPhase);
            params.cy =  0.148f + 0.05f * std::sin(params.morphPhase * 0.83f);
        }

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
        glUniform1i(uMode, params.mode);
        glUniform1f(uTrav, params.travel);
        glUniform1f(uBass, params.bass);
        glUniform1f(uMid, params.mid);
        glUniform1f(uTreb, params.treble);

        glDrawArrays(GL_TRIANGLES, 0, 3);
        glfwSwapBuffers(window);
        glfwPollEvents();

        ++frames;
        if (now - fpsT >= 1.0) {
            char title[128];
            const char* modeName = params.mode == 0 ? "manual" : params.mode == 1 ? "morph" : "tunel";
            std::snprintf(title, sizeof title,
                          "flx4-render | %d fps | %s x%.1f | iter=%d zoom=%.2f c=(%.3f,%.3f)",
                          frames, modeName, params.speed, params.iterations, params.zoom,
                          params.cx, params.cy);
            glfwSetWindowTitle(window, title);
            frames = 0;
            fpsT = now;
        }
    }

    glfwDestroyWindow(window);
    glfwTerminate();
    return 0;
}
