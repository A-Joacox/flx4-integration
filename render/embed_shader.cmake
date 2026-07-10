# Genera un header con el shader embebido (fallback si no existe shaders/julia.frag
# junto al exe). Uso: cmake -DSHADER_FILE=... -DOUT_FILE=... -P embed_shader.cmake
file(READ "${SHADER_FILE}" SRC)
file(WRITE "${OUT_FILE}" "// generado automaticamente desde shaders/julia.frag - NO EDITAR\n#pragma once\nstatic const char* kEmbeddedJuliaFrag = R\"GLSLSRC(\n${SRC}\n)GLSLSRC\";\n")
