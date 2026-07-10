cmake_minimum_required(VERSION 3.21)
project(flx4_render LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(glfw3 CONFIG REQUIRED)
find_package(glad CONFIG REQUIRED)
find_package(glm CONFIG REQUIRED)

add_executable(flx4_render src/main.cpp)
target_link_libraries(flx4_render PRIVATE glfw glad::glad glm::glm)
if(WIN32)
    target_link_libraries(flx4_render PRIVATE ws2_32)  # receptor OSC (osc_receiver.h)
endif()
