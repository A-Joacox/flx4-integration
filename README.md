# flx4-integration

Visualizador de fractales audiorreactivo controlado por Numark/Denon FLX4. Python (MIDI + audio) + C++ (OpenGL 4.6), comunicados por OSC.

Plan completo en [PLAN.md](PLAN.md).

## Setup rápido (Windows 11)

### Python

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Verificaciones Fase 0
python midi\check_midi.py        # el FLX4 debe aparecer en la lista
python audio\check_loopback.py   # debe abrir el loopback WASAPI y mostrar niveles
```

O simplemente: `.\setup.ps1`

### C++ (render)

Requiere: VS 2022 Build Tools (workload C++), CMake ≥ 3.21, vcpkg integrado.

```powershell
cd render
cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=$env:VCPKG_ROOT\scripts\buildsystems\vcpkg.cmake
cmake --build build --config Release
.\build\Release\flx4_render.exe
```

vcpkg instala las dependencias automáticamente desde `render/vcpkg.json` (modo manifest).

## Estructura

```
midi/     scripts Python de captura MIDI
audio/    captura/análisis de audio (WASAPI loopback, FFT, beat)
bridge/   servidor OSC Python -> C++
render/   proyecto C++ OpenGL (CMake + vcpkg)
shaders/  fragment shaders .glsl
presets/  midi_map.json y presets de visuales
common/   docs y configs compartidas
```
