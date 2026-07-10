"""Fase 2: analizador de audio en tiempo real (WASAPI loopback -> FFT -> bandas + beat).

Pipeline (ver PLAN.md): rekordbox con PC MASTER OUT -> parlantes -> loopback.
El dispositivo se elige por NOMBRE (los indices cambian entre sesiones) y se
excluye el FLX4, que rekordbox toma en exclusivo.

Uso como CLI (barras en consola):
    python audio/analyzer.py
    python audio/analyzer.py --name "Speakers"   # substring del loopback a usar

Uso como modulo (para el bridge OSC de Fase 4):
    from analyzer import AudioAnalyzer
    an = AudioAnalyzer(on_frame=lambda f: ...)  # f.bass/f.mid/f.treble en 0-1, f.beat bool
    an.start()   # hilo propio; an.stop() para cerrar

La parte DSP (clase BandAnalyzer) es pura numpy y no depende de pyaudiowpatch,
para poder testearla sin hardware.
"""

import argparse
import sys
import threading
import time
from dataclasses import dataclass

import numpy as np

CHUNK = 1024
BANDS = {"bass": (20, 250), "mid": (250, 4000), "treble": (4000, 16000)}
SMOOTH_ATTACK = 0.6    # subida rapida
SMOOTH_RELEASE = 0.15  # bajada suave
NORM_DECAY = 0.9995    # decaimiento del maximo adaptativo por frame
BEAT_HISTORY_SEC = 1.0
BEAT_THRESHOLD = 1.4   # energia bass vs media movil
BEAT_MIN_INTERVAL = 0.25  # seg entre beats (240 BPM max)


@dataclass
class Frame:
    bass: float
    mid: float
    treble: float
    beat: bool
    rms: float


class BandAnalyzer:
    """DSP puro: chunks mono -> bandas normalizadas 0-1 + deteccion de beat."""

    def __init__(self, sample_rate, chunk=CHUNK):
        self.rate = sample_rate
        self.chunk = chunk
        self.window = np.hanning(chunk).astype(np.float32)
        freqs = np.fft.rfftfreq(chunk, 1.0 / sample_rate)
        self._masks = {n: (freqs >= lo) & (freqs < hi) for n, (lo, hi) in BANDS.items()}
        self._smoothed = {n: 0.0 for n in BANDS}
        self._peak = {n: 1e-6 for n in BANDS}
        self._global_peak = 1e-6
        hist_len = max(4, int(BEAT_HISTORY_SEC * sample_rate / chunk))
        self._bass_hist = np.zeros(hist_len, dtype=np.float32)
        self._hist_i = 0
        self._hist_filled = 0
        self._last_beat_t = 0.0

    def process(self, mono, t=None):
        """mono: np.float32 de tamano chunk, en -1..1. t: timestamp opcional (seg)."""
        if t is None:
            t = time.monotonic()
        rms = float(np.sqrt(np.mean(mono**2)))
        spec = np.abs(np.fft.rfft(mono * self.window))

        raw = {n: (float(np.mean(spec[m])) if m.any() else 0.0)
               for n, m in self._masks.items()}
        # maximo global adaptativo: define el piso de todas las bandas, asi una
        # banda casi vacia (solo leakage/ruido) no se normaliza a 1 contra si misma
        self._global_peak = max(max(raw.values()), self._global_peak * NORM_DECAY, 1e-6)
        floor = 0.02 * self._global_peak
        for name, e in raw.items():
            self._peak[name] = max(e, self._peak[name] * NORM_DECAY, floor)
            norm = e / self._peak[name]
            a = SMOOTH_ATTACK if norm > self._smoothed[name] else SMOOTH_RELEASE
            self._smoothed[name] += a * (norm - self._smoothed[name])

        # beat: energia bass cruda vs media movil
        beat = False
        hist = self._bass_hist[: self._hist_filled] if self._hist_filled else None
        if hist is not None and len(hist) >= 4:
            avg = float(np.mean(hist))
            if (raw["bass"] > avg * BEAT_THRESHOLD
                    and raw["bass"] > 1e-5
                    and t - self._last_beat_t >= BEAT_MIN_INTERVAL):
                beat = True
                self._last_beat_t = t
        self._bass_hist[self._hist_i] = raw["bass"]
        self._hist_i = (self._hist_i + 1) % len(self._bass_hist)
        self._hist_filled = min(self._hist_filled + 1, len(self._bass_hist))

        return Frame(bass=self._smoothed["bass"], mid=self._smoothed["mid"],
                     treble=self._smoothed["treble"], beat=beat, rms=rms)


def pick_loopback(p, name_filter=None):
    """Elige el loopback por nombre. Prefiere parlantes; nunca el FLX4."""
    devs = list(p.get_loopback_device_info_generator())
    usable = [d for d in devs if "flx4" not in d["name"].lower()]
    if name_filter:
        match = [d for d in usable if name_filter.lower() in d["name"].lower()]
        if match:
            return match[0], devs
    for pref in ("speaker", "parlante", "altavo"):
        match = [d for d in usable if pref in d["name"].lower()]
        if match:
            return match[0], devs
    return (usable[0] if usable else None), devs


class AudioAnalyzer:
    """Captura WASAPI loopback en un hilo y llama on_frame(Frame) por chunk."""

    def __init__(self, on_frame=None, name_filter=None, chunk=CHUNK):
        self.on_frame = on_frame
        self.name_filter = name_filter
        self.chunk = chunk
        self.device_name = None
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _open(self, p):
        dev, _ = pick_loopback(p, self.name_filter)
        if dev is None:
            raise RuntimeError("No hay dispositivos loopback utilizables.")
        rate = int(dev["defaultSampleRate"])
        ch = int(dev["maxInputChannels"])
        stream = p.open(format=self._pa.paFloat32, channels=ch, rate=rate,
                        frames_per_buffer=self.chunk, input=True,
                        input_device_index=dev["index"])
        self.device_name = dev["name"]
        return stream, rate, ch

    def _run(self):
        import pyaudiowpatch as pa
        self._pa = pa
        with pa.PyAudio() as p:
            stream = None
            while not self._stop.is_set():
                try:
                    if stream is None:
                        stream, rate, ch = self._open(p)
                        dsp = BandAnalyzer(rate, self.chunk)
                        print(f"[analyzer] capturando: {self.device_name} ({ch}ch @ {rate}Hz)")
                    raw = stream.read(self.chunk, exception_on_overflow=False)
                    data = np.frombuffer(raw, dtype=np.float32)
                    mono = data.reshape(-1, ch).mean(axis=1) if ch > 1 else data
                    frame = dsp.process(mono)
                    if self.on_frame:
                        self.on_frame(frame)
                except OSError:
                    # device switching / desconexion: reintentar
                    if stream is not None:
                        try:
                            stream.close()
                        except OSError:
                            pass
                        stream = None
                    print("[analyzer] dispositivo perdido, re-detectando...")
                    time.sleep(0.5)
            if stream is not None:
                stream.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default=None, help="substring del nombre del loopback")
    args = parser.parse_args()

    W = 25

    def show(f):
        def bar(v):
            return ("#" * int(v * W)).ljust(W)
        flash = " BEAT!" if f.beat else ""
        print(f"\rbass |{bar(f.bass)}| mid |{bar(f.mid)}| treble |{bar(f.treble)}|{flash:6s}",
              end="", flush=True)

    an = AudioAnalyzer(on_frame=show, name_filter=args.name)
    an.start()
    print("Analizando (Ctrl+C para salir)...")
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nListo.")
    finally:
        an.stop()


if __name__ == "__main__":
    main()
