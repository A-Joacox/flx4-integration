"""Regenera presets/midi_map.json desde common/mixxx_ddj_flx4.midi.xml.

Correr desde la raiz del repo:
    python midi/gen_map_from_mixxx.py

Mantiene la entrada 'crossfader' verificada a mano y agrega las que existan
en el JSON actual que no vengan del XML (aprendidas con learn_map.py).
"""

import json
import re
from collections import OrderedDict
from pathlib import Path

XML = Path("common/mixxx_ddj_flx4.midi.xml")
OUT = Path("presets/midi_map.json")

VERIFIED = {
    "crossfader": {"type": "cc", "channel": 6, "cc": 31, "range": [0, 127],
                   "description": "Crossfader (verificado con learn_map)"},
}


def field(b, tag):
    m = re.search(rf"<{tag}>(.*?)</{tag}>", b, re.DOTALL)
    return m.group(1).strip() if m else None


def slugify(desc):
    return re.sub(r"[^a-z0-9]+", "_", desc.lower().replace("+shift", "shift")).strip("_")


def main():
    xml = XML.read_text(encoding="utf-8")
    out = OrderedDict()
    seen = set()
    for b in re.findall(r"<control>(.*?)</control>", xml, re.DOTALL):
        desc = field(b, "description") or ""
        status, midino = field(b, "status"), field(b, "midino")
        if not status or not midino:
            continue
        st, num = int(status, 16), int(midino, 16)
        msg_type, channel = st & 0xF0, st & 0x0F
        if (st, num) in seen:
            continue
        seen.add((st, num))
        if msg_type == 0xB0:
            if "jog" in desc.lower():
                entry = {"type": "cc_relative", "channel": channel, "cc": num}
            else:
                entry = {"type": "cc", "channel": channel, "cc": num, "range": [0, 127]}
        elif msg_type in (0x90, 0x80):
            entry = {"type": "note", "channel": channel, "note": num}
        else:
            continue
        entry["description"] = desc
        name = slugify(desc) or f"unknown_{st:02x}_{num:02x}"
        base, i = name, 2
        while name in out:
            name = f"{base}_{i}"
            i += 1
        out[name] = entry

    # conservar entradas aprendidas a mano si el JSON actual es valido
    if OUT.exists():
        try:
            cur = json.loads(OUT.read_text(encoding="utf-8")).get("controls", {})
            for k, v in cur.items():
                if k not in out:
                    out[k] = v
        except (json.JSONDecodeError, OSError):
            pass
    out.update(VERIFIED)

    data = {
        "device_name_contains": "FLX4",
        "source": "Mixxx Pioneer-DDJ-FLX4.midi.xml (github.com/mixxxdj/mixxx)",
        "note": "Regenerable con midi/gen_map_from_mixxx.py. Tempo sliders y algunos knobs mandan MSB+LSB (14 bits): aca figura el MSB.",
        "controls": out,
    }
    OUT.unlink(missing_ok=True)
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    check = json.loads(OUT.read_text(encoding="utf-8"))
    print(f"OK: {OUT} con {len(check['controls'])} controles")


if __name__ == "__main__":
    main()
