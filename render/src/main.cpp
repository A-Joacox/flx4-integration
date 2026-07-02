// Fase 0: esqueleto — ventana GLFW con contexto OpenGL 4.6.
// Si esto compila y abre una ventana, el toolchain C++ está OK.
// Fase 3 reemplaza el clear por el fragment shader del Julia set.

#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <cstdio>

int main() {
    if (!glfwInit()) {
        std::fprintf(stderr, "glfwInit falló\n");
        return 1;
    }

    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 4);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 6);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    GLFWwindow* window = glfwCreateWindow(1280, 720, "flx4-render (Fase 0)", nullptr, nullptr);
    if (!window) {
        std::fprintf(stderr, "No se pudo crear la ventana (¿drivers OpenGL 4.6?)\n");
        glfwTerminate();
        return 1;
    }

    glfwMakeContextCurrent(window);
    glfwSwapInterval(1); // vsync

    if (!gladLoadGLLoader(reinterpret_cast<GLADloadproc>(glfwGetProcAddress))) {
        std::fprintf(stderr, "gladLoadGLLoader falló\n");
        glfwTerminate();
        return 1;
    }

    std::printf("OpenGL %s — %s\n", glGetString(GL_VERSION), glGetString(GL_RENDERER));

    while (!glfwWindowShouldClose(window)) {
        if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
            glfwSetWindowShouldClose(window, GLFW_TRUE);

        // Placeholder: pulso de color para confirmar que el loop corre a 60fps
        float t = static_cast<float>(glfwGetTime());
        glClearColor(0.05f + 0.05f * (t - static_cast<int>(t)), 0.02f, 0.10f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        glfwSwapBuffers(window);
        glfwPollEvents();
    }

    glfwDestroyWindow(window);
    glfwTerminate();
    return 0;
}
