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

## Troubleshooting (verificado en Fase 0)

### CMake: "Could not find toolchain file"

- **Muestra el literal `$env:VCPKG_ROOT\...`**: faltan las comillas. En PowerShell el argumento debe ir `-DCMAKE_TOOLCHAIN_FILE="$env:VCPKG_ROOT\scripts\buildsystems\vcpkg.cmake"`.
- **Muestra `"\scripts\buildsystems\vcpkg.cmake"` (raíz vacía)**: `VCPKG_ROOT` no existe en esta sesión. `SetEnvironmentVariable(..., "User")` solo afecta terminales nuevas (en VS Code, reiniciar VS Code entero). Fix inmediato: `$env:VCPKG_ROOT = "C:\vcpkg"`.
- Después de cualquier configuración fallida, borrar el cache antes de reintentar: `Remove-Item -Recurse -Force build`.
- Verificar el toolchain: `Test-Path "$env:VCPKG_ROOT\scripts\buildsystems\vcpkg.cmake"` debe dar `True`.

### Audio: loopback del FLX4 falla con -9996 / -9998

rekordbox toma el FLX4 en modo exclusivo aunque esté configurado como "DDJ-FLX4 WASAPI" — su loopback no se puede abrir con rekordbox corriendo. Solución (verificada): activar **PC MASTER OUT** en rekordbox (Preferencias → Audio), que duplica el master hacia los parlantes de la notebook, y capturar el loopback de los parlantes:

```powershell
python .\audio\check_loopback.py            # lista los dispositivos
python .\audio\check_loopback.py --device 13  # Speakers Realtek [Loopback] (el índice puede cambiar)
```

Si el RMS queda en ~0, la música está saliendo por otro dispositivo — verificá cuál loopback corresponde al output que suena.
