"""Fase 1: MIDI-learn interactivo para el FLX4.

Construye presets/midi_map.json sin anotar CCs a mano:
  1. Escribi el nombre del control (ej: crossfader, jog_left, pad_1a) y Enter.
  2. Move/toca SOLO ese control en el FLX4.
  3. El script detecta el mensaje dominante y clasifica:
       - cc          : knob/fader absoluto (0-127)
       - cc_relative : jog wheel u otro control relativo (valores alrededor de 64)
       - note        : boton/pad (note_on/note_off)
       - pitchwheel  : jog/pitch que manda pitch bend
  4. Enter con nombre vacio para guardar y salir.

Uso:
    python midi/learn_map.py             # autodetecta el FLX4
    python midi/learn_map.py --port N    # puerto especifico
    python midi/learn_map.py --out presets/midi_map.json
"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import mido

CAPTURE_SECONDS = 2.0


def find_flx4(ports):
    for i, name in enumerate(ports):
        if "flx4" in name.lower().replace(" ", "").replace("-", ""):
            return i
    return None


def capture(port, seconds=CAPTURE_SECONDS):
    """Espera el primer mensaje y captura durante `seconds` a partir de ahi."""
    # descartar mensajes viejos en el buffer
    for _ in port.iter_pending():
        pass
    print(f"  Move/toca el control ahora (esperando)...", flush=True)
    msgs = []
    deadline = None
    while True:
        for msg in port.iter_pending():
            if msg.type in ("control_change", "note_on", "note_off", "pitchwheel"):
                if deadline is None:
                    deadline = time.monotonic() + seconds
                msgs.append(msg)
        if deadline is not None and time.monotonic() > deadline:
            return msgs
        time.sleep(0.002)


def classify(msgs):
    """Devuelve (entry_dict, resumen legible) para el mensaje dominante."""
    keys = Counter()
    for m in msgs:
        if m.type == "control_change":
            keys[("cc", m.channel, m.control)] += 1
        elif m.type in ("note_on", "note_off"):
            keys[("note", m.channel, m.note)] += 1
        elif m.type == "pitchwheel":
            keys[("pitchwheel", m.channel, None)] += 1
    if not keys:
        return None, "no se recibio nada"

    (kind, channel, num), count = keys.most_common(1)[0]

    if kind == "note":
        entry = {"type": "note", "channel": channel, "note": num}
        return entry, f"note {num} ch{channel} ({count} msgs) -> boton/pad"

    if kind == "pitchwheel":
        entry = {"type": "pitchwheel", "channel": channel}
        return entry, f"pitchwheel ch{channel} ({count} msgs)"

    values = [m.value for m in msgs
              if m.type == "control_change" and m.channel == channel and m.control == num]
    # heuristica relativo: muchos mensajes con valores concentrados alrededor de 64
    # (two's complement: 65,66=adelante / 63,62=atras) o saltando entre extremos
    near_64 = sum(1 for v in values if 56 <= v <= 72)
    relative = len(values) >= 6 and near_64 / len(values) > 0.9 and len(set(values)) <= 8
    if relative:
        entry = {"type": "cc_relative", "channel": channel, "cc": num}
        return entry, f"CC {num} ch{channel} ({count} msgs, valores {sorted(set(values))}) -> RELATIVO (jog?)"
    entry = {"type": "cc", "channel": channel, "cc": num, "range": [0, 127]}
    return entry, f"CC {num} ch{channel} ({count} msgs, min={min(values)} max={max(values)}) -> absoluto"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--out", default="presets/midi_map.json")
    args = parser.parse_args()

    ports = mido.get_input_names()
    if not ports:
        print("No hay puertos MIDI. Conecta el FLX4.")
        sys.exit(1)
    for i, name in enumerate(ports):
        print(f"  [{i}] {name}")
    idx = args.port if args.port is not None else find_flx4(ports)
    if idx is None or not 0 <= idx < len(ports):
        print("No se detecto el FLX4. Usa --port N.")
        sys.exit(1)

    out_path = Path(args.out)
    controls = {}
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            controls = existing.get("controls", {}) or {}
            if controls:
                print(f"\nCargado {args.out} con {len(controls)} controles (se agregan/pisan por nombre).")
        except (json.JSONDecodeError, OSError):
            pass

    print(f"\nEscuchando '{ports[idx]}'. Enter vacio para guardar y salir.\n")
    with mido.open_input(ports[idx]) as port:
        while True:
            try:
                name = input("Nombre del control: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not name:
                break
            msgs = capture(port)
            entry, summary = classify(msgs)
            if entry is None:
                print(f"  ! {summary}, proba de nuevo\n")
                continue
            controls[name] = entry
            print(f"  OK {name}: {summary}\n")

    data = {
        "device_name_contains": "FLX4",
        "controls": controls,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Guardado {out_path} con {len(controls)} controles.")


if __name__ == "__main__":
    main()
