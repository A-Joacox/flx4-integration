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

Requiere: VS 2022 Build Tools (workload C++), CMake ≥ 3.21, vcpkg.

Instalar vcpkg (una sola vez):

```powershell
git clone https://github.com/microsoft/vcpkg C:\vcpkg
C:\vcpkg\bootstrap-vcpkg.bat
[Environment]::SetEnvironmentVariable("VCPKG_ROOT", "C:\vcpkg", "User")
# reabrir la terminal
```

Compilar (las comillas en el toolchain son obligatorias en PowerShell):

```powershell
cd render
cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE="$env:VCPKG_ROOT\scripts\buildsystems\vcpkg.cmake"
cmake --build build --config Release
.\build\Release\flx4_render.exe
```

Si una configuración falló antes, borrar el cache: `Remove-Item -Recurse -Force build`.
La primera vez tarda varios minutos (vcpkg compila glfw3/glad/glm).
