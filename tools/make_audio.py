#!/usr/bin/env python3
"""Synthesizes the placeholder music and babble voices in assets/. Needs ffmpeg.

Music: plucked kantele strings (Karplus-Strong) playing runo-song style melodies,
which traditionally use the first five notes of a minor scale in 5/4 time,
the same five notes the old five-string kantele was tuned to. Tracks loop seamlessly.

Voices: a handful of short synthesized syllables per character. The game plays
them at random pitches while a line is on screen, Animal Crossing style.

Usage: python3 tools/make_audio.py
"""
import math
import random
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SR = 22050
SYLLABLES_PER_VOICE = 6

# ---------------------------------------------------------------- output


def lowpass(samples, cutoff):
    """One-pole low-pass: takes the edge off clicks, bursts and bright harmonics."""
    a = 1 - math.exp(-2 * math.pi * cutoff / SR)
    y = 0.0
    out = []
    for x in samples:
        y += a * (x - y)
        out.append(y)
    return out


def write_ogg(samples, path, quality=3, peak_level=0.9, cutoff=2200):
    samples = lowpass(lowpass(samples, cutoff), cutoff)
    peak = max(1e-9, max(abs(s) for s in samples))
    gain = peak_level / peak
    out = ASSETS / path
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        with wave.open(tmp.name, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(b"".join(struct.pack("<h", int(s * gain * 32767)) for s in samples))
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", tmp.name, "-c:a", "libvorbis", "-q:a", str(quality), str(out)],
            check=True,
        )
    print(f"  {path}  ({len(samples) / SR:.1f}s)")


# ---------------------------------------------------------------- music

# All music sounds this many semitones below the written notes (lower is easier on the ear).
TRANSPOSE = -3
NOTE = {"C": -9, "D": -7, "E": -5, "F": -4, "F#": -3, "G": -2, "A": 0, "Bb": 1, "B": 2}


def freq(name, octave):
    return 440.0 * 2 ** ((NOTE[name] + 12 * (octave - 4) + TRANSPOSE) / 12)


def pluck(f, dur, rng, brightness=0.5, decay=0.996):
    """Karplus-Strong plucked string: a noise burst circulating in a damped delay line."""
    n = max(2, int(SR / f))
    buf = [rng.uniform(-1, 1) for _ in range(n)]
    # Smoother initial noise = darker, softer pluck.
    for _ in range(int((1 - brightness) * 4) + 2):
        buf = [(buf[i] + buf[i - 1]) * 0.5 for i in range(n)]
    out = []
    total = int(dur * SR)
    i = 0
    for _ in range(total):
        a = buf[i]
        b = buf[(i + 1) % n]
        buf[i] = decay * 0.5 * (a + b)
        out.append(a)
        i = (i + 1) % n
    return out


def add(track, start, samples, gain):
    """Mix into a looping track: anything past the end wraps to the start."""
    n = len(track)
    s = int(start * SR)
    for i, v in enumerate(samples):
        track[(s + i) % n] += v * gain


def drone(track, f, gain, wobble=0.15):
    """A soft sustained hum with slow swells, for the grove."""
    n = len(track)
    loop_seconds = n / SR
    # Whole number of cycles so the drone loops cleanly.
    f = round(f * loop_seconds) / loop_seconds
    swell = 2 / loop_seconds
    for i in range(n):
        t = i / SR
        amp = gain * (1 - wobble + wobble * math.sin(2 * math.pi * swell * t))
        track[i] += amp * (math.sin(2 * math.pi * f * t) + 0.3 * math.sin(4 * math.pi * f * t))


def reverb(track, wet=0.3, room=0.8):
    """Schroeder-style comb reverb, run over two passes so the tail wraps into the loop."""
    combs = [int(SR * d) for d in (0.0297, 0.0371, 0.0411, 0.0437)]
    n = len(track)
    bufs = [[0.0] * d for d in combs]
    idx = [0] * len(combs)
    out = [0.0] * n
    for pass_ in range(2):
        for i in range(n):
            x = track[i]
            acc = 0.0
            for c in range(len(combs)):
                b = bufs[c]
                y = b[idx[c]]
                b[idx[c]] = x + y * room
                idx[c] = (idx[c] + 1) % combs[c]
                acc += y
            if pass_ == 1:
                out[i] = x + wet * acc / len(combs)
    return out


def play_melody(track, rng, melody, beat, scale, octave, gain, start=0.0, brightness=0.6, decay=0.996):
    """melody: list of (scale degree, beats). Degree 0 is a rest; '+'/'-' suffix shifts octave."""
    t = start
    for degree, beats in melody:
        if degree != 0:
            d, oct_shift = degree, 0
            if isinstance(degree, str):
                oct_shift = degree.count("+") - degree.count("-")
                d = int(degree.strip("+-"))
            name = scale[d - 1]
            jitter = rng.uniform(-0.012, 0.012)
            vel = gain * rng.uniform(0.8, 1.0)
            add(track, t + jitter, pluck(freq(name, octave + oct_shift), beat * beats + 1.2, rng, brightness, decay), vel)
        t += beat * beats
    return t


def strum(track, rng, t, notes, gain, spread=0.035, brightness=0.4):
    """Several strings brushed together, like a kantele chord."""
    for k, (name, octave) in enumerate(notes):
        add(track, t + k * spread, pluck(freq(name, octave), 2.5, rng, brightness, 0.997), gain * rng.uniform(0.7, 1.0))


# Runo-song phrases: five notes, five beats to a bar.
RUNO_A = [(1, 1), (1, 1), (2, 1), (3, 1), (3, 1), (4, 1), (3, 1), (2, 1), (1, 2)]
RUNO_B = [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (4, 1), (3, 1), (2, 1), (2, 1), (1, 1)]
RUNO_C = [(5, 1), (5, 1), (4, 1), (3, 1), (3, 1), (4, 1), (3, 1), (2, 1), (1, 2)]
RUNO_D = [(3, 1), (4, 1), (5, 2), (4, 1), (3, 1), (2, 1), (3, 1), (1, 2)]


def village():
    rng = random.Random(10)
    scale = ["D", "E", "F", "G", "A"]
    beat = 0.62
    bars = 16
    track = [0.0] * int(bars * 5 * beat * SR)
    phrases = [RUNO_A, RUNO_B, RUNO_A, RUNO_C, RUNO_D, RUNO_B, RUNO_C, RUNO_A]
    t = 0.0
    for i, p in enumerate(phrases):
        t = play_melody(track, rng, p, beat, scale, 4 if i < 4 else 5, 0.5, t, brightness=0.65)
    for bar in range(bars):
        bt = bar * 5 * beat
        add(track, bt, pluck(freq("D", 3), 3.0, rng, 0.3, 0.998), 0.45)
        add(track, bt + 3 * beat, pluck(freq("A", 2), 2.0, rng, 0.3, 0.998), 0.3)
        if bar % 2 == 0:
            strum(track, rng, bt + 0.01, [("D", 4), ("F", 4), ("A", 4)], 0.18)
    write_ogg(reverb(track, 0.35), "music/village.ogg", peak_level=0.6)


def path():
    rng = random.Random(20)
    scale = ["D", "E", "F", "G", "A"]
    beat = 0.42
    bars = 16
    track = [0.0] * int(bars * 5 * beat * SR)
    # Walking feel: eighth-note pairs and a steady bass.
    walk = [("5", 0.5), ("4", 0.5), (3, 1), (2, 1), (3, 0.5), (4, 0.5), (5, 1), (0, 1),
            (4, 0.5), (3, 0.5), (2, 1), (1, 1), (2, 0.5), (3, 0.5), (1, 1), (0, 1)]
    hop = [(1, 0.5), (2, 0.5), (3, 0.5), (5, 0.5), ("1+", 1), (5, 1), (4, 1), (3, 0.5), (2, 0.5), (1, 1), (0, 1),
           (3, 1), (2, 1), (1, 2)]
    t = 0.0
    for p in [walk, walk, hop, walk, hop, walk]:
        t = play_melody(track, rng, p, beat, scale, 4, 0.45, t, brightness=0.7, decay=0.994)
        if t >= len(track) / SR - 0.1:
            break
    for b in range(bars * 5):
        if b % 5 in (0, 3):
            add(track, b * beat, pluck(freq("D" if b % 10 < 5 else "A", 3 if b % 10 < 5 else 2), 1.0, rng, 0.25, 0.995), 0.35)
    # A bird somewhere.
    for bt in (6.0, 19.5, 27.0):
        for k in range(3):
            add(track, bt + k * 0.09, pluck(freq("A", 6) * (1 + 0.06 * k), 0.15, rng, 0.9, 0.98), 0.08)
    write_ogg(reverb(track, 0.3), "music/path.ogg")


def grove():
    rng = random.Random(30)
    scale = ["D", "E", "F", "G", "A"]
    beat = 0.9
    bars = 8
    track = [0.0] * int(bars * 5 * beat * SR)
    drone(track, freq("D", 2), 0.12)
    drone(track, freq("A", 2), 0.07)
    sparse = [(5, 2), (0, 1), (4, 1), (3, 1), (0, 3), (2, 1), (1, 1),
              (0, 2), ("1+", 1), (5, 2), (0, 2), (3, 1), (2, 1), (1, 2), (0, 3)]
    t = play_melody(track, rng, sparse, beat, scale, 4, 0.4, 0.5, brightness=0.35, decay=0.998)
    play_melody(track, rng, sparse[::-1], beat, scale, 5, 0.22, t, brightness=0.3, decay=0.998)
    write_ogg(reverb(track, 0.6, 0.86), "music/grove.ogg")


def ending():
    rng = random.Random(40)
    # Retuned to major for the celebration.
    scale = ["D", "E", "F#", "G", "A"]
    beat = 0.36
    bars = 12
    track = [0.0] * int(bars * 5 * beat * SR)
    joy = [(1, 0.5), (3, 0.5), (5, 1), ("1+", 1), (5, 1), (3, 0.5), (4, 0.5),
           (5, 1), (4, 0.5), (3, 0.5), (2, 1), (1, 2)]
    t = 0.0
    while t < len(track) / SR - 2:
        t = play_melody(track, rng, joy + RUNO_B, beat, scale, 4, 0.45, t, brightness=0.75)
    for bar in range(bars):
        strum(track, rng, bar * 5 * beat, [("D", 3), ("A", 3), ("D", 4), ("F#", 4), ("A", 4)], 0.18, 0.025, 0.6)
    write_ogg(reverb(track, 0.35), "music/ending.ogg")


# ---------------------------------------------------------------- voices

VOWELS = {  # formant frequencies F1, F2, F3 (Hz), roughly an adult female voice
    "a": (750, 1250, 2700), "e": (500, 1900, 2700), "o": (520, 900, 2600),
    "ä": (700, 1700, 2650), "ö": (480, 1550, 2550), "i": (330, 2300, 3000),
}


def resonance(f, center, bandwidth):
    return 1.0 / (1.0 + ((f - center) / bandwidth) ** 2)


def highpass(samples, passes=2):
    for _ in range(passes):
        prev = 0.0
        out = []
        for x in samples:
            out.append(x - prev)
            prev = x
        samples = out
    return samples


def consonant(rng, kind, f0):
    """A short sound before the vowel, so syllables read as "ka", "se", "mo"..."""
    if kind == "s":  # hiss
        n = int(0.045 * SR)
        noise = highpass([rng.uniform(-1, 1) for _ in range(n)], 2)
        return [0.04 * x * math.sin(math.pi * i / n) for i, x in enumerate(noise)]
    if kind in "kt":  # stop: brief silence, then a burst
        burst = int(0.008 * SR)
        noise = highpass([rng.uniform(-1, 1) for _ in range(burst)], 1 if kind == "k" else 2)
        return [0.0] * int(0.02 * SR) + [0.1 * x * (1 - i / burst) for i, x in enumerate(noise)]
    if kind in "mn":  # hum through the nose: just the low harmonics
        n = int(0.05 * SR)
        f2 = 1.9 if kind == "m" else 2.4
        return [0.35 * min(1.0, i / (0.01 * SR)) * (math.sin(2 * math.pi * f0 * i / SR)
                + 0.25 * math.sin(2 * math.pi * f0 * f2 * i / SR)) for i in range(n)]
    return []


def syllable(rng, f0, vowel, dur, breath=0.05, vibrato=0.0, glide=-0.08, onset=""):
    """Additive formant synthesis with a natural source.

    A real voice's harmonics fall off steadily (about 1/k) and the vowel only
    *shapes* them, so every harmonic keeps some energy. Three resonances plus a
    floor give body; slight random pitch drift (jitter) keeps it from sounding
    like a pure, hollow tone. Above ~1.8 kHz the harmonics roll off faster and
    their phases are scattered, which keeps it from sounding buzzy or harsh.
    """
    f1, f2, f3 = VOWELS[vowel]
    harmonics = []
    k = 1
    while k * f0 < 4000:
        h = k * f0
        shape = 0.15 + resonance(h, f1, 120) + 0.6 * resonance(h, f2, 160) + 0.2 * resonance(h, f3, 240)
        rolloff = 1 / (1 + (h / 1300) ** 2)
        harmonics.append((k, shape * rolloff / k, rng.uniform(0, 2 * math.pi)))
        k += 1
    pre = consonant(rng, onset, f0)
    n = int(dur * SR)
    out = []
    phase = 0.0
    drift = 0.0
    hiss = 0.0
    for i in range(n):
        t = i / SR
        p = i / n
        drift = 0.995 * drift + 0.005 * rng.gauss(0, 1)
        f = f0 * (1 + glide * p) * (1 + vibrato * math.sin(2 * math.pi * 5.5 * t)) * (1 + 0.05 * drift)
        phase += 2 * math.pi * f / SR
        voiced = sum(a * math.sin(k * phase + ph) for k, a, ph in harmonics)
        # Quick attack, hold, then fall away, like a spoken syllable.
        env = min(1.0, i / (0.015 * SR)) * (1.0 if p < 0.55 else (1 - p) / 0.45) ** 1.3
        hiss = 0.75 * hiss + 0.25 * rng.uniform(-1, 1)  # softened breath noise
        out.append(env * (voiced + 2 * breath * hiss))
    return pre + out + [0.0] * int(0.02 * SR)


def chirp(rng, dur, f_start, f_end, harsh=0.4):
    """Magpie noises: a fast pitch sweep with a scratchy onset."""
    n = int(dur * SR)
    out = []
    phase = 0.0
    for i in range(n):
        p = i / n
        f = f_start + (f_end - f_start) * p
        phase += 2 * math.pi * f / SR
        env = min(1.0, i / (0.004 * SR)) * (1 - p) ** 2
        tone = math.sin(phase) + harsh * math.copysign(1, math.sin(2 * phase))
        scratch = rng.uniform(-1, 1) * (1 - min(1.0, i / (0.03 * SR)))
        out.append(env * (0.6 * tone + 0.2 * scratch))
    return out + [0.0] * int(0.02 * SR)


def echo(samples, delay=0.12, feedback=0.45, taps=4):
    d = int(delay * SR)
    out = samples + [0.0] * d * taps
    for i in range(len(samples)):
        g = 1.0
        for k in range(1, taps + 1):
            g *= feedback
            out[i + d * k] += samples[i] * g
    return out


# Finnish-sounding syllables: (consonant, vowel).
SYLLABLES = [("k", "a"), ("t", "e"), ("s", "ä"), ("m", "o"), ("", "a"), ("n", "i")]


def voice_clips(rng):
    """name -> list of syllable clips."""
    clips = {"vilja": [], "kyllikki": [], "spirit": [], "magpie": []}
    for onset, vowel in SYLLABLES[:SYLLABLES_PER_VOICE]:
        clips["vilja"].append(syllable(rng, 205, vowel, 0.1, breath=0.03, glide=-0.05, onset=onset))
        old_vowel = "ö" if vowel == "i" else vowel
        clips["kyllikki"].append(syllable(rng, 140, old_vowel, 0.13, breath=0.08, vibrato=0.025, glide=-0.1, onset=onset))
        clips["spirit"].append(echo(syllable(rng, 80, "o" if vowel in "ie" else vowel, 0.24, breath=0.3, glide=0.04,
                                             onset="m" if onset else ""), 0.15, 0.5))
        f = rng.uniform(750, 1050)
        clips["magpie"].append(chirp(rng, rng.uniform(0.07, 0.11), f, f * rng.uniform(1.2, 1.45), harsh=0.12))
    return clips


def voices():
    for name, clips in voice_clips(random.Random(50)).items():
        for i, clip in enumerate(clips):
            write_ogg(clip, f"voices/{name}/{i}.ogg", 4, peak_level=0.55 if name == "magpie" else 0.9)


# ---------------------------------------------------------------- intro score
#
# The intro sequence in src/main.rs is timed to this music (INTRO_* constants there).

INTRO_FIRE_OUT = 16.0  # the last ember dies
INTRO_HIT = 28.0  # the title lands
INTRO_LENGTH = 52.0
INTRO_SKIP_LEAD = 0.6  # skipping lands this many seconds before the hit
MINOR = ["D", "E", "F", "G", "A", "Bb", "C"]


def add_once(track, start, samples, gain):
    """Mix into a one-shot track (no wrapping; anything past the end is dropped)."""
    s0 = int(start * SR)
    for i, v in enumerate(samples[: max(0, len(track) - s0)]):
        track[s0 + i] += v * gain


def wavetable(amps, rng=None, size=2048):
    """One cycle of a waveform made of harmonics with the given amplitudes."""
    phases = [0.0] + [rng.uniform(0, 6.28) if rng else 0.0 for _ in amps[1:]]
    return [sum(a * math.sin(2 * math.pi * (k + 1) * i / size + phases[k]) for k, a in enumerate(amps)) for i in range(size)]


def choir_table(f0, rng, vowel="a"):
    f1, f2, f3 = {"a": (730, 1100, 2600), "o": (500, 850, 2500)}[vowel]
    amps, k = [], 1
    while k * f0 < 4500 and k <= 40:
        h = k * f0
        amps.append((0.22 + resonance(h, f1, 110) + 0.6 * resonance(h, f2, 150) + 0.2 * resonance(h, f3, 220)) / k)
        k += 1
    return wavetable(amps, rng)


HORN = [1.0, 0.75, 0.55, 0.4, 0.28, 0.18, 0.12, 0.08, 0.05, 0.03]
SOFT = [1.0, 0.45, 0.25, 0.12, 0.06]


def synth(track, start, dur, f, table, gain, attack=0.3, release=0.8, vibrato=0.0, vib_rate=5.0, rng=None, wrap=False):
    """Play a sustained note from a wavetable with an attack/release envelope."""
    size = len(table)
    n = int((dur + release) * SR)
    s0 = int(start * SR)
    phase = rng.random() * size if rng else 0.0
    length = len(track)
    for i in range(n):
        idx = s0 + i
        if idx >= length:
            if not wrap:
                break
            idx %= length
        t = i / SR
        env = min(1.0, t / attack) if t < dur else max(0.0, 1 - (t - dur) / release)
        ff = f * (1 + vibrato * math.sin(2 * math.pi * vib_rate * t)) if vibrato else f
        phase += ff * size / SR
        track[idx] += table[int(phase) % size] * env * gain


def frame_drum(rng, pitch=1.0):
    """A shaman's frame drum: a deep thud that falls in pitch, with a skin slap on top."""
    out, ph = [], 0.0
    n = int(1.1 * SR)
    for i in range(n):
        t = i / SR
        f = (50 + 48 * math.exp(-t * 16)) * pitch
        ph += 2 * math.pi * f / SR
        v = math.sin(ph) * math.exp(-t * 4.2) + 0.3 * math.sin(ph * 2.3) * math.exp(-t * 9)
        if i < 0.014 * SR:
            v += rng.uniform(-1, 1) * 0.45 * (1 - i / (0.014 * SR))
        out.append(v)
    return out


def bell(rng, f, dur=2.5):
    """Glassy aurora shimmer: inharmonic partials that ring and fade."""
    parts = [(1.0, 1.0, 1.2), (2.76, 0.45, 2.0), (5.4, 0.22, 3.0), (8.93, 0.1, 4.2)]
    phases = [rng.uniform(0, 6.28) for _ in parts]
    n = int(dur * SR)
    return [sum(a * math.sin(2 * math.pi * f * m * i / SR + p) * math.exp(-i / SR * d)
                for (m, a, d), p in zip(parts, phases)) * min(1.0, i / (0.004 * SR)) for i in range(n)]


def wind(track, rng, gain, start=0.0, end=None, wrap_period=None):
    """Night wind: low-passed noise that gusts slowly."""
    end = end if end is not None else len(track) / SR
    lp1 = lp2 = 0.0
    period = wrap_period or 7.3
    for i in range(int(start * SR), min(len(track), int(end * SR))):
        x = rng.uniform(-1, 1)
        lp1 += 0.03 * (x - lp1)
        lp2 += 0.004 * (x - lp2)
        t = i / SR
        gust = 0.55 + 0.45 * math.sin(2 * math.pi * t / period) * math.sin(2 * math.pi * t / (period * 2.7) + 1)
        track[i] += (lp1 - lp2) * 6 * gain * gust


def cymbal(rng, swell, ring):
    """A rolled cymbal: a hissing crescendo, then the crash ringing out."""
    out, prev, prev2 = [], 0.0, 0.0
    n_s, n_r = int(swell * SR), int(ring * SR)
    for i in range(n_s + n_r):
        x = rng.uniform(-1, 1)
        hp = x - 2 * prev + prev2
        prev2, prev = prev, x
        env = (i / n_s) ** 3 if i < n_s else math.exp(-(i - n_s) / SR * 1.6)
        out.append(hp * env * 0.5)
    return out


def reverb_once(track, wet=0.4, room=0.85):
    """Comb reverb for a one-shot piece: the tail rings past the end instead of wrapping."""
    combs = [int(SR * d) for d in (0.0297, 0.0371, 0.0411, 0.0437)]
    tail = int(SR * 2.5)
    src = track + [0.0] * tail
    bufs = [[0.0] * d for d in combs]
    idx = [0] * len(combs)
    out = []
    for x in src:
        acc = 0.0
        for c, size in enumerate(combs):
            b = bufs[c]
            y = b[idx[c]]
            b[idx[c]] = x + y * room
            idx[c] = (idx[c] + 1) % size
            acc += y
        out.append(x + wet * acc / len(combs))
    return out


def degree_note(degree, octave):
    """Scale degree like 3, or '1+' (an octave up), to (name, octave) in D minor."""
    shift = 0
    if isinstance(degree, str):
        shift = degree.count("+") - degree.count("-")
        degree = int(degree.strip("+-"))
    return MINOR[(degree - 1) % 7], octave + shift + (degree - 1) // 7


def intro_music():
    rng = random.Random(77)
    track = [0.0] * int(INTRO_LENGTH * SR)
    hit = INTRO_HIT

    # Night air: wind throughout and a low drone gathering underneath.
    # Hushed at first; when the ember dies the wind drops and the drone falls away.
    wind(track, rng, 0.035, 0.0, INTRO_FIRE_OUT + 0.5)
    wind(track, rng, 0.012, INTRO_FIRE_OUT + 0.5, 19.0)
    wind(track, rng, 0.03, 19.0, INTRO_LENGTH)
    soft = wavetable(SOFT)
    synth(track, 0.5, INTRO_FIRE_OUT - 0.5, freq("D", 2), soft, 0.06, attack=5.0, release=2.0)
    synth(track, 19.0, hit - 19.05, freq("D", 2), soft, 0.08, attack=6.0, release=0.05)
    synth(track, 21.0, hit - 21.05, freq("A", 2), soft, 0.05, attack=6.0, release=0.05)

    # A lone kantele plays the old runo tune, slow and mournful.
    beat = 0.72
    tune = [(1, 1), (1, 1), (2, 1), (3, 1), (3, 1), (4, 1), (3, 1), (2, 1), (1, 2),
            (3, 1), (4, 1), (5, 2), (4, 1), (3, 1), (2, 1)]
    t = 2.6
    for degree, beats in tune:
        name, octv = degree_note(degree, 4)
        add_once(track, t + rng.uniform(-0.01, 0.01), pluck(freq(name, octv), 3.0, rng, 0.45, 0.997), 0.17)
        t += beat * beats
    # The ember dies: a falling figure, slowing, then a single low string.
    t = INTRO_FIRE_OUT - 1.4
    for name, octv, dt in (("A", 4, 0.5), ("G", 4, 0.58), ("F", 4, 0.7), ("E", 4, 0.9), ("D", 4, 1.7)):
        add_once(track, t, pluck(freq(name, octv), 3.5, rng, 0.4, 0.998), 0.17)
        t += dt
    add_once(track, INTRO_FIRE_OUT + 1.6, pluck(freq("D", 2), 5.0, rng, 0.3, 0.9993), 0.25)

    # Tilting up to the sky: a heartbeat drum quickening, a choir rising, the aurora shimmering.
    drum = frame_drum(rng)
    t, gap = 19.6, 1.3
    while t < hit - 0.3:
        add_once(track, t, drum, 0.2 + 0.5 * ((t - 19.6) / (hit - 19.6)) ** 1.5)
        t += gap
        gap = max(0.3, gap * 0.85)
    for name, octv in (("D", 3), ("F", 3), ("A", 3), ("D", 4)):
        f = freq(name, octv)
        synth(track, 20.4, hit - 20.45, f, choir_table(f, rng), 0.06, attack=7.5, release=0.05,
              vibrato=0.006, vib_rate=4.6 + rng.random(), rng=rng)
    t = 20.0
    while t < hit:
        name, octv = rng.choice([("D", 6), ("F", 6), ("A", 6), ("C", 7), ("E", 6), ("A", 5)])
        add_once(track, t, bell(rng, freq(name, octv)), 0.03 + 0.05 * (t - 20) / (hit - 20))
        t += rng.uniform(0.12, 0.45) * (1.5 - (t - 20) / (hit - 20))
    add_once(track, hit - 3.5, cymbal(rng, 3.5, 4.0), 0.22)

    # The title: drums, the full choir, a horn singing the runo theme, kantele above.
    add_once(track, hit, frame_drum(rng, 0.75), 1.3)
    add_once(track, hit + 0.03, drum, 0.8)
    add_once(track, hit, cymbal(rng, 0.001, 5.0), 0.3)
    chords = [(hit, 4.2, [("D", 3), ("A", 3), ("D", 4), ("F", 4), ("A", 4)]),
              (hit + 4.2, 3.0, [("C", 3), ("G", 3), ("C", 4), ("E", 4), ("G", 4)]),
              (hit + 7.2, 3.0, [("Bb", 2), ("F", 3), ("Bb", 3), ("D", 4), ("F", 4)]),
              (hit + 10.2, 3.0, [("C", 3), ("G", 3), ("C", 4), ("E", 4), ("G", 4)]),
              (hit + 13.2, 9.0, [("D", 3), ("A", 3), ("D", 4), ("F", 4), ("A", 4)])]
    for i, (start, dur, notes) in enumerate(chords):
        for name, octv in notes:
            f = freq(name, octv)
            synth(track, start, dur, f, choir_table(f, rng), 0.085, attack=0.08 if i == 0 else 0.6,
                  release=4.0 if i == len(chords) - 1 else 0.9, vibrato=0.005, vib_rate=4.4 + rng.random(), rng=rng)
    synth(track, hit, 20.0, freq("D", 2), wavetable(HORN), 0.16, attack=0.05, release=4.0)
    horn = wavetable(HORN, rng)
    theme = [(1, 2), (5, 3), (4, 1), (3, 1), (2, 1), (1, 2),
             (3, 1), (4, 1), (5, 2), (6, 1), (5, 1), (4, 1), (5, 3),
             ("1+", 2), (7, 1), (6, 1), (5, 2), (4, 1), (3, 1), (2, 1), (1, 4)]
    beat, t = 0.6, hit + 0.6
    for degree, beats in theme:
        name, octv = degree_note(degree, 3)
        f = freq(name, octv)
        synth(track, t, beats * beat * 0.92, f, horn, 0.17, attack=0.09, release=0.35, vibrato=0.004, vib_rate=5.2)
        add_once(track, t, pluck(freq(name, octv + 2), 2.0, rng, 0.75, 0.996), 0.2)
        t += beats * beat
    for bar in range(6):  # steady drums in five: strong on one, lighter on four
        bt = hit + 3.0 + bar * 3.0
        add_once(track, bt, drum, 0.6)
        add_once(track, bt + 1.8, drum, 0.38)
    t = hit + 1.0
    while t < hit + 18:
        name, octv = rng.choice([("D", 6), ("F", 6), ("A", 6), ("E", 6)])
        add_once(track, t, bell(rng, freq(name, octv)), 0.035)
        t += rng.uniform(0.6, 1.4)
    add_once(track, INTRO_LENGTH - 4.5, pluck(freq("D", 5), 4.0, rng, 0.6, 0.998), 0.2)
    full = reverb_once(track, 0.42, 0.86)
    write_ogg(full, "music/intro.ogg")
    # Skipping the intro jumps to the title. The game can't seek inside an OGG file, so the
    # end of the piece, from just before the hit, is also its own file (at the same loudness).
    tail = full[int((INTRO_HIT - INTRO_SKIP_LEAD) * SR):]
    write_ogg(tail, "music/intro_tail.ogg", peak_level=0.9 * max(map(abs, tail)) / max(map(abs, full)))


def title_music():
    """A quiet loop for the title screen: the aurora shimmering over a held chord."""
    rng = random.Random(78)
    loop = 24.0
    track = [0.0] * int(loop * SR)
    drone(track, freq("D", 2), 0.1)
    drone(track, freq("A", 2), 0.05)
    for name, octv in (("D", 3), ("A", 3), ("F", 4)):
        f = round(freq(name, octv) * loop) / loop  # whole cycles per loop, so it joins seamlessly
        synth(track, 0, loop, f, choir_table(f, rng, "o"), 0.03, attack=0.001, release=0.0, wrap=True)
    wind(track, rng, 0.05, wrap_period=loop / 3)
    t = 0.3
    while t < loop:
        name, octv = rng.choice([("D", 6), ("F", 6), ("A", 6), ("E", 6), ("A", 5)])
        add(track, t, bell(rng, freq(name, octv)), 0.03)
        t += rng.uniform(0.8, 2.2)
    write_ogg(reverb(track, 0.5, 0.86), "music/title.ogg", peak_level=0.45)


if __name__ == "__main__":
    print("music:")
    village()
    path()
    grove()
    ending()
    intro_music()
    title_music()
    print("voices:")
    voices()
