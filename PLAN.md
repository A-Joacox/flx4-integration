# Plan de Trabajo: Aplicación Nativa de Fractales Reactivos (FLX4 + Audio)

## Contexto del proyecto

Aplicación híbrida (Python + C++) que se conecta al controlador MIDI Numark/Denon FLX4, captura audio en tiempo real, y genera fractales reactivos renderizados por GPU. El objetivo es un visualizador audiorreactivo controlable en vivo, pensado para sets de DJ.

## Entorno de desarrollo

- OS: Windows 11
- Hardware: Razer Blade, CPU AMD Ryzen AI 9 365, GPU RTX 5060
- Arquitectura: híbrida — Python para MIDI + captura/análisis de audio, C++ con OpenGL para el render de fractales, comunicados vía shared memory o UDP/OSC local
- Controlador: Numark/Denon FLX4

## Decisiones técnicas clave

- **Captura de audio en Windows**: no existe un "monitor" nativo como en PulseAudio/PipeWire. Usar WASAPI loopback mediante `pyaudiowpatch` (fork de PyAudio con soporte WASAPI loopback) o `soundcard`. Esto captura el audio de salida del sistema sin cables físicos.
- **MIDI en Windows**: `mido` + `python-rtmidi`, backend WinMM automático.
- **Render en C++**: GLFW + GLAD para contexto OpenGL 4.6, dependencias vía vcpkg.
- **Toolchain C++**: Visual Studio 2022 Build Tools + CMake. La RTX 5060 soporta OpenGL 4.6 vía drivers NVIDIA estándar.
- **Puente Python ↔ C++**: OSC (`python-osc` / `oscpack`) por robustez y debug fácil. Alternativa de menor latencia: shared memory (`multiprocessing.shared_memory` + `CreateFileMapping`/`MapViewOfFile`).

## Estructura del repo

```
/midi          -> scripts Python de captura MIDI
/audio         -> scripts Python de captura/análisis de audio
/bridge        -> lógica OSC/shared memory
/render        -> proyecto C++ (CMakeLists.txt, src/)
/shaders       -> archivos .glsl
/presets       -> configs JSON de mapeos
/common        -> docs, configs compartidas
```

## Fase 0 — Setup del entorno (1-2 días)

- [ ] Instalar Python 3.11+ y crear entorno virtual (`venv`)
- [ ] Instalar dependencias Python: `mido`, `python-rtmidi`, `pyaudiowpatch`, `numpy`, `python-osc`
- [ ] Verificar que el FLX4 aparece como dispositivo MIDI: `python midi/check_midi.py`
- [ ] Verificar captura WASAPI loopback: `python audio/check_loopback.py`
- [ ] Instalar Visual Studio 2022 Build Tools (workload "Desktop development with C++")
- [ ] Instalar CMake y vcpkg; integrar vcpkg (`vcpkg integrate install`)
- [ ] Compilar el esqueleto de `render/` (ventana GLFW vacía)
- [x] Crear repo Git con estructura

## Fase 1 — Captura MIDI aislada (2-3 días)

- [ ] Script que escuche el FLX4 y loguee todos los mensajes CC/nota en crudo
- [ ] Documentar mapeo CC→control en `presets/midi_map.json`
- [ ] Normalizar valores (0-127 → 0.0-1.0)
- [ ] Manejar el jog wheel (relative CC o pitch bend — confirmar comportamiento real)
- **Entregable**: consola imprimiendo valores normalizados en tiempo real

## Fase 2 — Captura y análisis de audio (3-4 días)

- [ ] WASAPI loopback con buffer pequeño (512-1024 samples)
- [ ] FFT en tiempo real con `numpy.fft.rfft`
- [ ] 3 bandas de energía (bass/mid/treble)
- [ ] Detector de beat: energía actual vs. media móvil con umbral adaptativo
- [ ] Manejar device switching de Windows (re-detección del loopback)
- **Entregable**: visualización simple con 3 bandas + flag de beat

## Fase 3 — Render base en OpenGL/C++ (4-5 días)

- [ ] Proyecto CMake con GLFW + GLAD, ventana con contexto OpenGL 4.6
- [ ] Fragment shader con fractal tipo Julia set
- [ ] Uniforms controlables por teclado (zoom, offset, iteraciones, color)
- [ ] Confirmar 60fps estables a 1920x1080
- **Entregable**: fractal a 60fps controlable con teclas

## Fase 4 — Puente Python ↔ C++ (2-3 días)

- [ ] Servidor OSC en Python: bandas de audio, beat flag, valores MIDI normalizados
- [ ] Cliente OSC en C++ (`oscpack` vía vcpkg)
- [ ] Loop C++: recibir OSC no bloqueante cada frame, actualizar uniforms
- **Entregable**: knob del FLX4 cambia el zoom del fractal en tiempo real

## Fase 5 — Reactividad completa (4-5 días)

- [ ] bass → zoom/escala, mid → color (HSV shift), treble → distorsión/ruido
- [ ] Beat → flash o cambio de paleta
- [ ] Pads/jog wheels → cambio de fractal o presets
- [ ] Suavizado (lerp/easing) de todos los valores
- **Entregable**: sistema completo reaccionando en vivo

## Fase 6 — Polish y presets (3-4 días)

- [ ] Presets en JSON (mapeos, paletas, tipo de fractal)
- [ ] Transiciones suaves entre presets
- [ ] Grabación a video vía `ffmpeg` (pipe desde framebuffer)
- [ ] Reconexión automática FLX4, fallback de dispositivo de audio

## Consideraciones de rendimiento

- Pipeline completo en <16ms para 60fps sin lag perceptible
- Audio analyzer en hilo propio con prioridad alta (`SetThreadPriority` vía `ctypes` si hay jitter)
- Evaluar shared memory sobre OSC si la latencia UDP local es perceptible

## Timeline

~3-4 semanas part-time (una fase cada 2-5 días)

## Notas

- Priorizar `pyaudiowpatch`; validarlo temprano (es el punto más frágil en Windows)
- vcpkg en modo manifest (`vcpkg.json`) para reproducibilidad
- Cada fase deja un entregable ejecutable antes de avanzar
