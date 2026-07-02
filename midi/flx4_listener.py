"""Fase 1 (entregable): listener del FLX4 con valores normalizados.

Carga presets/midi_map.json y emite (nombre_control, valor) en tiempo real:
  - cc          : 0-127 -> 0.0-1.0
  - cc_relative : delta con signo (jog): +1.0 adelante, -1.0 atras (por tick)
  - note        : 1.0 al presionar, 0.0 al soltar
  - pitchwheel  : -1.0 a 1.0

Uso como CLI (imprime valores en vivo):
    python midi/flx4_listener.py
    python midi/flx4_listener.py --unmapped   # muestra tambien mensajes no mapeados

Uso como modulo (para el bridge OSC de Fase 4):
    from flx4_listener import Flx4Listener
    lis = Flx4Listener("presets/midi_map.json", on_control=lambda n, v, e: ...)
    lis.start()   # no bloquea (callback de mido en su propio hilo)
"""

import argparse
import json
import sys
import time
from pathlib import Path

import mido


def find_flx4_port():
    for name in mido.get_input_names():
        if "flx4" in name.lower().replace(" ", "").replace("-", ""):
            return name
    return None


class Flx4Listener:
    def __init__(self, map_path, on_control=None, on_unmapped=None, port_name=None):
        data = json.loads(Path(map_path).read_text(encoding="utf-8"))
        self.controls = data.get("controls", {})
        self.on_control = on_control
        self.on_unmapped = on_unmapped
        self.port_name = port_name
        self._port = None
        # lookup inverso: (tipo_mensaje, canal, numero) -> (nombre, entry)
        self._lut = {}
        for name, e in self.controls.items():
            t = e.get("type")
            if t in ("cc", "cc_relative"):
                self._lut[("cc", e["channel"], e["cc"])] = (name, e)
            elif t == "note":
                self._lut[("note", e["channel"], e["note"])] = (name, e)
            elif t == "pitchwheel":
                self._lut[("pitchwheel", e["channel"], None)] = (name, e)

    @staticmethod
    def _normalize(entry, msg):
        t = entry["type"]
        if t == "cc":
            lo, hi = entry.get("range", [0, 127])
            return max(0.0, min(1.0, (msg.value - lo) / float(hi - lo or 1)))
        if t == "cc_relative":
            # two's complement centrado en 64: 65,66..=adelante / 63,62..=atras
            return float(msg.value - 64)
        if t == "note":
            return 1.0 if (msg.type == "note_on" and msg.velocity > 0) else 0.0
        if t == "pitchwheel":
            return msg.pitch / 8192.0
        return 0.0

    def _handle(self, msg):
        if msg.type == "control_change":
            key = ("cc", msg.channel, msg.control)
        elif msg.type in ("note_on", "note_off"):
            key = ("note", msg.channel, msg.note)
        elif msg.type == "pitchwheel":
            key = ("pitchwheel", msg.channel, None)
        else:
            return
        hit = self._lut.get(key)
        if hit is None:
            if self.on_unmapped:
                self.on_unmapped(msg)
            return
        name, entry = hit
        if self.on_control:
            self.on_control(name, self._normalize(entry, msg), entry)

    def start(self):
        name = self.port_name or find_flx4_port()
        if name is None:
            raise RuntimeError("No se encontro el FLX4 entre los puertos MIDI.")
        self._port = mido.open_input(name, callback=self._handle)
        return name

    def stop(self):
        if self._port:
            self._port.close()
            self._port = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", default="presets/midi_map.json")
    parser.add_argument("--unmapped", action="store_true", help="mostrar mensajes sin mapear")
    args = parser.parse_args()

    def show(name, value, entry):
        if entry["type"] == "cc_relative":
            print(f"{name:55s} delta {value:+.0f}")
        else:
            print(f"{name:55s} {value:.3f}")

    def show_unmapped(msg):
        print(f"{'?? sin mapear':55s} {msg}")

    lis = Flx4Listener(args.map, on_control=show,
                       on_unmapped=show_unmapped if args.unmapped else None)
    try:
        port = lis.start()
    except RuntimeError as e:
        print(e)
        sys.exit(1)
    print(f"Escuchando '{port}' con {len(lis.controls)} controles mapeados. Ctrl+C para salir.\n")
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nListo.")
    finally:
        lis.stop()


if __name__ == "__main__":
    main()
