"""Fase 0: verificar captura WASAPI loopback con pyaudiowpatch.

Lista los dispositivos loopback, abre el del output default y muestra el nivel RMS
en tiempo real. Poné música y deberías ver la barra moverse.

Uso:
    python audio/check_loopback.py
"""

import sys
import time

import numpy as np

try:
    import pyaudiowpatch as pyaudio
except ImportError:
    print("Falta pyaudiowpatch: pip install pyaudiowpatch")
    sys.exit(1)

CHUNK = 1024


def main() -> None:
    with pyaudio.PyAudio() as p:
        try:
            wasapi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            print("WASAPI no disponible en este sistema.")
            sys.exit(1)

        print("Dispositivos loopback disponibles:")
        for dev in p.get_loopback_device_info_generator():
            print(f"  [{dev['index']}] {dev['name']} ({int(dev['maxInputChannels'])}ch @ {int(dev['defaultSampleRate'])}Hz)")

        # Loopback del output default
        default_out = p.get_device_info_by_index(wasapi["defaultOutputDevice"])
        loopback = None
        if not default_out.get("isLoopbackDevice", False):
            for dev in p.get_loopback_device_info_generator():
                if default_out["name"] in dev["name"]:
                    loopback = dev
                    break
        else:
            loopback = default_out

        if loopback is None:
            print("\nNo se encontró loopback para el output default.")
            sys.exit(1)

        rate = int(loopback["defaultSampleRate"])
        channels = int(loopback["maxInputChannels"])
        print(f"\nCapturando: {loopback['name']} ({channels}ch @ {rate}Hz, chunk={CHUNK})")
        print("Poné música. Ctrl+C para salir.\n")

        stream = p.open(
            format=pyaudio.paFloat32,
            channels=channels,
            rate=rate,
            frames_per_buffer=CHUNK,
            input=True,
            input_device_index=loopback["index"],
        )
        try:
            while True:
                data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.float32)
                rms = float(np.sqrt(np.mean(data**2))) if data.size else 0.0
                bar = "#" * min(60, int(rms * 300))
                print(f"\rRMS {rms:.4f} |{bar:<60}|", end="", flush=True)
                time.sleep(0.01)
        except KeyboardInterrupt:
            print("\nListo.")
        finally:
            stream.stop_stream()
            stream.close()


if __name__ == "__main__":
    main()
