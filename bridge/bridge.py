"""Fase 4: puente OSC — audio (analyzer) + MIDI (flx4_listener) -> UDP localhost.

Correr desde la raiz del repo, con rekordbox sonando y el FLX4 conectado:
    python bridge/bridge.py
    python bridge/bridge.py --no-midi      # solo audio
    python bridge/bridge.py --no-audio     # solo MIDI

Mensajes OSC emitidos (todos float32):
    /audio/bass /audio/mid /audio/treble   0-1, ~47 veces/seg
    /audio/beat                            1.0 solo en el frame del beat
    /ctl/zoom /ctl/speed /ctl/hue          0-1, controles semanticos del FLX4
    /midi/<nombre>                         todo lo demas del midi_map (debug/Fase 5)
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "midi"))
sys.path.insert(0, str(ROOT / "audio"))

from pythonosc.udp_client import SimpleUDPClient

from analyzer import AudioAnalyzer
from flx4_listener import Flx4Listener

# control fisico del FLX4 -> direccion semantica (Fase 5 movera esto a presets/)
SEMANTIC = {
    "crossfader": "/ctl/zoom",
    "crossfader_slider": "/ctl/zoom",
    "filter_ch1_rotate_filter_effect_knob": "/ctl/speed",
    "filter_ch2_rotate_filter_effect_knob": "/ctl/hue",
}

# pads (solo al presionar, value==1.0) -> mensajes discretos
PAD_ACTIONS = {
    "pad_1_deck1_hot_cue_mode_press_set_hotcue": ("/ctl/mode", 0.0),  # manual
    "pad_2_deck1_hot_cue_mode_press_set_hotcue": ("/ctl/mode", 1.0),  # morph
    "pad_3_deck1_hot_cue_mode_press_set_hotcue": ("/ctl/mode", 2.0),  # tunel
    "pad_4_deck1_hot_cue_mode_press_set_hotcue": ("/ctl/reset", 1.0),
    "pad_5_deck1_hot_cue_mode_press_set_hotcue": ("/ctl/mode", 3.0),  # viaje
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--no-midi", action="store_true")
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--map", default=str(ROOT / "presets" / "midi_map.json"))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    client = SimpleUDPClient(args.host, args.port)
    print(f"OSC -> {args.host}:{args.port}")

    stats = {"audio": 0, "midi": 0}

    analyzer = None
    silent = {"chunks": 0, "warned": False}
    if not args.no_audio:
        def on_frame(f):
            client.send_message("/audio/bass", float(f.bass))
            client.send_message("/audio/mid", float(f.mid))
            client.send_message("/audio/treble", float(f.treble))
            if f.beat:
                client.send_message("/audio/beat", 1.0)
            stats["audio"] += 1
            # diagnostico: señal muerta aunque haya musica sonando
            if f.rms < 1e-5:
                silent["chunks"] += 1
                if silent["chunks"] > 140 and not silent["warned"]:  # ~3 seg
                    silent["warned"] = True
                    print("\n[bridge] AVISO: el loopback recibe SILENCIO hace 3s.")
                    print("         Si hay musica sonando, revisa que los parlantes de Windows")
                    print("         no esten muteados ni al 0% (el loopback captura ese volumen).")
            else:
                silent["chunks"] = 0
                silent["warned"] = False
        analyzer = AudioAnalyzer(on_frame=on_frame)
        analyzer.start()

    listener = None
    if not args.no_midi:
        def on_control(name, value, entry):
            pad = PAD_ACTIONS.get(name)
            if pad is not None:
                if value >= 0.5:  # solo el press, no el release
                    client.send_message(pad[0], pad[1])
                    stats["midi"] += 1
                    if args.verbose:
                        print(f"  {pad[0]} {pad[1]}")
                return
            addr = SEMANTIC.get(name, f"/midi/{name}")
            client.send_message(addr, float(value))
            stats["midi"] += 1
            if args.verbose:
                print(f"  {addr} {value:.3f}")
        listener = Flx4Listener(args.map, on_control=on_control)
        try:
            port_name = listener.start()
            print(f"MIDI: {port_name}")
        except RuntimeError as e:
            print(f"MIDI deshabilitado: {e}")
            listener = None

    print("Bridge corriendo (Ctrl+C para salir).")
    try:
        while True:
            time.sleep(2)
            print(f"\r[bridge] audio {stats['audio']} msg | midi {stats['midi']} msg ", end="", flush=True)
    except KeyboardInterrupt:
        print("\nListo.")
    finally:
        if analyzer:
            analyzer.stop()
        if listener:
            listener.stop()


if __name__ == "__main__":
    main()
