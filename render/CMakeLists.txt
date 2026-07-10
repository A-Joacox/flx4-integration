cmake_minimum_required(VERSION 3.21)
project(flx4_render LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(glfw3 CONFIG REQUIRED)
find_package(glad CONFIG REQUIRED)
find_package(glm CONFIG REQUIRED)

# shader embebido en el binario (se regenera si cambia shaders/julia.frag)
set(EMBEDDED_SHADER ${CMAKE_CURRENT_BINARY_DIR}/julia_frag.h)
add_custom_command(
    OUTPUT ${EMBEDDED_SHADER}
    COMMAND ${CMAKE_COMMAND}
        -DSHADER_FILE=${CMAKE_CURRENT_SOURCE_DIR}/../shaders/julia.frag
        -DOUT_FILE=${EMBEDDED_SHADER}
        -P ${CMAKE_CURRENT_SOURCE_DIR}/embed_shader.cmake
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/../shaders/julia.frag
            ${CMAKE_CURRENT_SOURCE_DIR}/embed_shader.cmake
    COMMENT "Embebiendo shaders/julia.frag")

add_executable(flx4_render src/main.cpp ${EMBEDDED_SHADER})
target_include_directories(flx4_render PRIVATE ${CMAKE_CURRENT_BINARY_DIR})
target_link_libraries(flx4_render PRIVATE glfw glad::glad glm::glm)
if(WIN32)
    target_link_libraries(flx4_render PRIVATE ws2_32)  # receptor OSC (osc_receiver.h)
endif()
