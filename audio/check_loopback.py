"""Fase 0: verificar captura WASAPI loopback con pyaudiowpatch.

Lista los dispositivos loopback, abre uno y muestra el nivel RMS en tiempo real.
Pone musica y deberias ver la barra moverse.

Uso:
    python audio/check_loopback.py              # loopback del output default
    python audio/check_loopback.py --device 13  # dispositivo especifico de la lista

Nota rekordbox (verificado 2026-07): rekordbox toma el FLX4 en modo exclusivo
aunque este configurado como "DDJ-FLX4 WASAPI" (-9996/-9998 al abrir su loopback).
Pipeline que funciona: activar "PC MASTER OUT" en rekordbox (duplica el master
hacia los parlantes de la notebook) y capturar el loopback de los parlantes:

    python audio/check_loopback.py --device 13   # Speakers Realtek [Loopback]

(el indice puede cambiar entre sesiones; verificar en la lista)
"""

import argparse
import sys
import time

import numpy as np

try:
    import pyaudiowpatch as pyaudio
except ImportError:
    print("Falta pyaudiowpatch: pip install pyaudiowpatch")
    sys.exit(1)

CHUNK = 1024


def open_stream(p, dev):
    """Intenta abrir el loopback con varias combinaciones formato/canales."""
    rate = int(dev["defaultSampleRate"])
    dev_ch = int(dev["maxInputChannels"])
    attempts = [
        (pyaudio.paFloat32, dev_ch),
        (pyaudio.paInt16, dev_ch),
        (pyaudio.paFloat32, 2),
        (pyaudio.paInt16, 2),
    ]
    last_err = None
    for fmt, ch in attempts:
        if ch > dev_ch:
            continue
        try:
            stream = p.open(
                format=fmt,
                channels=ch,
                rate=rate,
                frames_per_buffer=CHUNK,
                input=True,
                input_device_index=dev["index"],
            )
            return stream, fmt, ch, rate
        except OSError as e:
            last_err = e
    raise last_err


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=int, default=None, help="indice del dispositivo loopback")
    args = parser.parse_args()

    with pyaudio.PyAudio() as p:
        try:
            wasapi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            print("WASAPI no disponible en este sistema.")
            sys.exit(1)

        loopbacks = list(p.get_loopback_device_info_generator())
        print("Dispositivos loopback disponibles:")
        for dev in loopbacks:
            print(f"  [{dev['index']}] {dev['name']} ({int(dev['maxInputChannels'])}ch @ {int(dev['defaultSampleRate'])}Hz)")

        loopback = None
        if args.device is not None:
            loopback = next((d for d in loopbacks if d["index"] == args.device), None)
            if loopback is None:
                print(f"\nEl indice {args.device} no es un dispositivo loopback de la lista.")
                sys.exit(1)
        else:
            default_out = p.get_device_info_by_index(wasapi["defaultOutputDevice"])
            if default_out.get("isLoopbackDevice", False):
                loopback = default_out
            else:
                loopback = next((d for d in loopbacks if default_out["name"] in d["name"]), None)

        if loopback is None:
            print("\nNo se encontro loopback para el output default. Usa --device N.")
            sys.exit(1)

        print(f"\nAbriendo: {loopback['name']}")
        try:
            stream, fmt, channels, rate = open_stream(p, loopback)
        except OSError as e:
            print(f"\nNo se pudo abrir el dispositivo ({e}).")
            print("Causas tipicas:")
            print("  - Otra app lo tiene en modo exclusivo (rekordbox toma el FLX4 siempre,")
            print("    incluso configurado como WASAPI).")
            print("    -> Usar el loopback de los parlantes con PC MASTER OUT activado en rekordbox.")
            print("  - El dispositivo se desconecto o cambio de indice: volve a correr el script.")
            print("  - Proba otro de la lista con --device N.")
            sys.exit(1)

        dtype = np.float32 if fmt == pyaudio.paFloat32 else np.int16
        scale = 1.0 if fmt == pyaudio.paFloat32 else 32768.0
        fmt_name = "float32" if fmt == pyaudio.paFloat32 else "int16"
        print(f"Capturando: {channels}ch @ {rate}Hz, {fmt_name}, chunk={CHUNK}")
        print("Pone musica. Ctrl+C para salir.\n")

        try:
            while True:
                raw = stream.read(CHUNK, exception_on_overflow=False)
                data = np.frombuffer(raw, dtype=dtype).astype(np.float32) / scale
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
