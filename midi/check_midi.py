"""Fase 0: verificar que el FLX4 aparece como dispositivo MIDI y loguear mensajes en crudo.

Uso:
    python midi/check_midi.py           # lista puertos y escucha el FLX4 si lo encuentra
    python midi/check_midi.py --port N  # escucha el puerto N de la lista
"""

import argparse
import sys
import time

import mido


def list_ports() -> list[str]:
    ports = mido.get_input_names()
    print("Puertos MIDI de entrada:")
    if not ports:
        print("  (ninguno — ¿está conectado y encendido el FLX4?)")
    for i, name in enumerate(ports):
        print(f"  [{i}] {name}")
    return ports


def find_flx4(ports: list[str]) -> int | None:
    for i, name in enumerate(ports):
        if "flx4" in name.lower().replace(" ", "").replace("-", ""):
            return i
    return None


def listen(port_name: str) -> None:
    print(f"\nEscuchando '{port_name}' — mové knobs/faders/pads (Ctrl+C para salir)\n")
    with mido.open_input(port_name) as port:
        try:
            while True:
                for msg in port.iter_pending():
                    t = time.strftime("%H:%M:%S")
                    if msg.type == "control_change":
                        norm = msg.value / 127.0
                        print(f"[{t}] CC  ch={msg.channel} cc={msg.control:3d} val={msg.value:3d} norm={norm:.3f}")
                    elif msg.type in ("note_on", "note_off"):
                        print(f"[{t}] {msg.type.upper():8s} ch={msg.channel} note={msg.note} vel={msg.velocity}")
                    elif msg.type == "pitchwheel":
                        print(f"[{t}] PITCH ch={msg.channel} value={msg.pitch}")
                    else:
                        print(f"[{t}] {msg}")
                time.sleep(0.001)
        except KeyboardInterrupt:
            print("\nListo.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=None, help="índice del puerto a escuchar")
    args = parser.parse_args()

    ports = list_ports()
    if not ports:
        sys.exit(1)

    idx = args.port if args.port is not None else find_flx4(ports)
    if idx is None:
        print("\nNo se detectó el FLX4 por nombre. Usá --port N para elegir manualmente.")
        sys.exit(1)
    if not 0 <= idx < len(ports):
        print(f"Índice fuera de rango: {idx}")
        sys.exit(1)

    listen(ports[idx])


if __name__ == "__main__":
    main()
