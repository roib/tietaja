#!/usr/bin/env python3
"""Synthesizes the music and voices for the third tale, The Fire Fox, with make_audio.py's
instruments: the aurora's glassy shimmer, polar wind, a kantele, the frame drum, choir and
horn. The intro in levels.rs (FOX_INTRO) is timed to this music: the lights die away at
FOX_LIGHTS_OUT, the fox's last spark glimmers at FOX_SPARK, and the title lands at FOX_HIT.

Usage: python3 tools/make_fox_audio.py [part ...]
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_audio as M  # noqa: E402
from make_audio import SR, add, add_once, bell, choir_table, degree_note, drone, frame_drum, freq, pluck, reverb, reverb_once, synth, wavetable, wind, write_ogg  # noqa: E402,E501

FOX_LIGHTS_OUT = 17.0  # the aurora fades away
FOX_SPARK = 26.2  # a single spark glimmers in the snow
FOX_HIT = 28.0
FOX_LENGTH = 52.0


def shimmer(track, rng, start, end, gain, notes=(("D", 6), ("F", 6), ("A", 6), ("E", 6), ("A", 5), ("C", 6)), gap=(0.5, 1.6), once=True):
    """The aurora's glassy bells, scattered through a stretch of time."""
    put = add_once if once else add
    t = start
    while t < end:
        name, octv = rng.choice(notes)
        put(track, t, bell(rng, freq(name, octv), 2.6), gain * rng.uniform(0.6, 1.0))
        t += rng.uniform(*gap)


def sleigh_bell(rng, dur=0.5):
    """A reindeer's bell, far off: a small bright clink."""
    return [v * 0.6 for v in bell(rng, freq("A", 6) * rng.uniform(0.98, 1.02), dur)]


def intro_fox():
    rng = random.Random(91)
    track = [0.0] * int(FOX_LENGTH * SR)
    hit = FOX_HIT
    soft = wavetable(M.SOFT)
    # The sky ablaze: a high shimmering choir, glassy bells, and a kantele tune.
    wind(track, rng, 0.04, 0.0, FOX_LIGHTS_OUT)
    for name, octv in (("D", 4), ("A", 4), ("F", 5), ("A", 5)):
        f = freq(name, octv)
        synth(track, 0.5, FOX_LIGHTS_OUT - 1.5, f, choir_table(f, rng, "o"), 0.035, attack=4.0, release=2.5, vibrato=0.006, vib_rate=4 + rng.random(), rng=rng)
    synth(track, 0.5, FOX_LIGHTS_OUT - 1.0, freq("D", 2), soft, 0.05, attack=4.0, release=1.5)
    shimmer(track, rng, 0.8, FOX_LIGHTS_OUT - 1.5, 0.05)
    beat = 0.78
    tune = [(1, 1), (3, 1), (5, 2), (4, 1), (3, 1), (5, 1), (4, 1), (3, 2), (2, 1), (1, 1), (2, 1), (3, 3),
            (5, 1), (6, 1), (5, 1), (4, 1), (3, 2), (2, 2), (1, 3)]
    t = 3.0
    for degree, beats in tune:
        name, octv = degree_note(degree, 4)
        add_once(track, t + rng.uniform(-0.01, 0.01), pluck(freq(name, octv), 3.0, rng, 0.45, 0.997), 0.15)
        t += beat * beats
    # The lights go out: the bells fall silent, a falling sigh, and only the wind is left.
    for k in range(6):
        add_once(track, FOX_LIGHTS_OUT - 1.0 + k * 0.28, bell(rng, freq("A", 6) * (0.96 ** k), 2.0), 0.05 * (1 - k / 7))
    wind(track, rng, 0.09, FOX_LIGHTS_OUT - 0.5, hit)
    add_once(track, FOX_LIGHTS_OUT, pluck(freq("D", 2), 6.0, rng, 0.3, 0.9994), 0.2)
    add_once(track, FOX_LIGHTS_OUT + 0.05, pluck(freq("A", 1), 6.0, rng, 0.3, 0.9994), 0.16)
    # The long dark: a heartbeat drum quickening, the low drone and choir swelling.
    drum = frame_drum(rng)
    t, gap = 20.5, 1.3
    while t < hit - 0.3:
        add_once(track, t, drum, 0.18 + 0.5 * ((t - 20.5) / (hit - 20.5)) ** 1.5)
        t += gap
        gap = max(0.3, gap * 0.84)
    synth(track, 19.5, hit - 19.55, freq("D", 2), soft, 0.09, attack=6.0, release=0.05)
    for name, octv in (("D", 3), ("F", 3), ("A", 3), ("D", 4)):
        f = freq(name, octv)
        synth(track, 21.0, hit - 21.05, f, choir_table(f, rng, "o"), 0.055, attack=5.5, release=0.05, vibrato=0.006, vib_rate=4.4 + rng.random(), rng=rng)
    add_once(track, hit - 3.6, M.cymbal(rng, 3.6, 3.0), 0.2)
    # A spark in the snow: one bell, bright and warm.
    add_once(track, FOX_SPARK, bell(rng, freq("D", 5), 3.4), 0.09)
    add_once(track, FOX_SPARK + 0.02, pluck(freq("A", 5), 2.5, rng, 0.6, 0.997), 0.1)
    # The title: drums, the full choir moving from minor into a bright major, the horn
    # singing the fox's theme, and the sky shimmering again.
    add_once(track, hit, frame_drum(rng, 0.7), 1.3)
    add_once(track, hit + 0.03, drum, 0.8)
    chords = [(hit, 4.2, [("D", 3), ("A", 3), ("D", 4), ("F", 4), ("A", 4)]),
              (hit + 4.2, 3.0, [("Bb", 2), ("F", 3), ("Bb", 3), ("D", 4), ("F", 4)]),
              (hit + 7.2, 3.0, [("C", 3), ("G", 3), ("C", 4), ("E", 4), ("G", 4)]),
              (hit + 10.2, 3.0, [("A", 2), ("E", 3), ("A", 3), ("C#", 4), ("E", 4)]),
              (hit + 13.2, 9.0, [("D", 3), ("A", 3), ("D", 4), ("F#", 4), ("A", 4)])]
    for i, (start, dur, notes) in enumerate(chords):
        for name, octv in notes:
            f = freq(name, octv)
            synth(track, start, dur, f, choir_table(f, rng), 0.08, attack=0.08 if i == 0 else 0.6,
                  release=4.0 if i == len(chords) - 1 else 0.9, vibrato=0.005, vib_rate=4.4 + rng.random(), rng=rng)
    synth(track, hit, 20.0, freq("D", 2), wavetable(M.HORN), 0.15, attack=0.05, release=4.0)
    horn = wavetable(M.HORN, rng)
    theme = [(1, 1), (3, 1), (5, 2), (4, 1), (5, 1), (6, 2), (5, 2),
             (3, 1), (4, 1), (5, 1), (6, 1), (7, 2), (5, 2),
             (4, 1), (3, 1), (2, 1), ("7-", 1), (1, 4)]
    beat, t = 0.6, hit + 0.6
    for degree, beats in theme:
        name, octv = degree_note(degree, 3)
        f = freq(name, octv)
        synth(track, t, beats * beat * 0.92, f, horn, 0.16, attack=0.09, release=0.35, vibrato=0.004, vib_rate=5.2)
        add_once(track, t, pluck(freq(name, octv + 2), 2.0, rng, 0.7, 0.996), 0.16)
        t += beats * beat
    for bar in range(6):
        bt = hit + 3.0 + bar * 3.0
        add_once(track, bt, drum, 0.6)
        add_once(track, bt + 1.8, drum, 0.38)
    shimmer(track, rng, hit + 0.5, FOX_LENGTH - 3, 0.045, notes=(("D", 6), ("F#", 6), ("A", 6), ("E", 6), ("A", 5)), gap=(0.4, 1.2))
    full = reverb_once(track, 0.45, 0.87)
    write_ogg(full, "music/intro_fox.ogg")
    tail = full[int((FOX_HIT - M.INTRO_SKIP_LEAD) * SR):]
    write_ogg(tail, "music/intro_fox_tail.ogg", peak_level=0.9 * max(map(abs, tail)) / max(map(abs, full)))


def title_fox():
    """The title loop: wind over the fells, a held chord, the aurora shimmering."""
    rng = random.Random(92)
    loop = 24.0
    track = [0.0] * int(loop * SR)
    drone(track, freq("D", 2), 0.09)
    drone(track, freq("A", 2), 0.05)
    for name, octv in (("D", 3), ("A", 3), ("F#", 4), ("A", 4)):
        f = round(freq(name, octv) * loop) / loop
        synth(track, 0, loop, f, choir_table(f, rng, "o"), 0.024, attack=0.001, release=0.0, wrap=True)
    wind(track, rng, 0.06, wrap_period=loop / 3)
    shimmer(track, rng, 0.3, loop, 0.03, notes=(("D", 6), ("F#", 6), ("A", 6), ("E", 6), ("A", 5)), gap=(0.8, 2.2), once=False)
    write_ogg(reverb(track, 0.5, 0.86), "music/title_fox.ogg", peak_level=0.45)


def fells_music():
    """The camp, the lake and the forest in the polar night: wind, a low drone, a slow
    kantele tune in minor, and reindeer bells somewhere out in the dark."""
    rng = random.Random(93)
    beat = 0.85
    bars = 10
    track = [0.0] * int(bars * 5 * beat * SR)
    loop = len(track) / SR
    drone(track, freq("D", 2), 0.08, 0.3)
    drone(track, freq("A", 2), 0.04, 0.3)
    wind(track, rng, 0.07, wrap_period=loop / 4)
    tune = [(1, 2), (0, 1), (3, 1), (2, 1), (1, 2), (5, 1), (4, 2), (0, 2),
            (3, 1), (4, 1), (5, 2), (4, 1), (3, 1), (2, 3), (0, 2),
            (1, 1), (2, 1), (3, 2), (2, 1), (1, 3), (0, 3)]
    t = M.play_melody(track, rng, tune, beat, ["D", "E", "F", "G", "A", "Bb"], 4, 0.28, 0.4, brightness=0.35, decay=0.998)
    M.play_melody(track, rng, tune[::3], beat * 2, ["D", "E", "F", "G", "A", "Bb"], 3, 0.16, t, brightness=0.3, decay=0.998)
    for t in (5.0, 5.4, 6.1, 23.0, 23.3):
        add(track, t, sleigh_bell(rng), 0.05)
    write_ogg(reverb(track, 0.35, 0.8), "music/fells.ogg")


def fell_music():
    """The fell top and the den: the empty sky, a slow choir that never settles, a few
    glassy bells where the lights should be, and the wind."""
    rng = random.Random(94)
    loop = 32.0
    track = [0.0] * int(loop * SR)
    drone(track, freq("D", 2), 0.07, 0.25)
    wind(track, rng, 0.08, wrap_period=loop / 4)
    chords = [[("D", 3), ("A", 3), ("F", 4)], [("Bb", 2), ("F", 3), ("D", 4)], [("C", 3), ("G", 3), ("E", 4)], [("A", 2), ("E", 3), ("C#", 4)]]
    for i, notes in enumerate(chords):
        for name, octv in notes:
            f = freq(name, octv)
            synth(track, i * 8.0, 8.0, f, choir_table(f, rng, "o"), 0.03, attack=2.5, release=2.5, vibrato=0.006, vib_rate=4 + rng.random(), rng=rng, wrap=True)
    shimmer(track, rng, 1.0, loop, 0.025, gap=(1.5, 3.5), once=False)
    for t, degree in ((3.0, 5), (11.0, 3), (19.0, 4), (27.0, 2)):
        name, octv = degree_note(degree, 4)
        add(track, t, pluck(freq(name, octv), 3.5, rng, 0.35, 0.998), 0.1)
    write_ogg(reverb(track, 0.5, 0.86), "music/fell.ogg", peak_level=0.6)


def voices():
    """Mummo, old and warm; Jussi, low and gruff."""
    rng = random.Random(95)
    for i, (onset, vowel) in enumerate(M.SYLLABLES[:M.SYLLABLES_PER_VOICE]):
        old_vowel = "ö" if vowel == "i" else vowel
        write_ogg(M.syllable(rng, 150, old_vowel, 0.12, breath=0.09, vibrato=0.03, glide=-0.1, onset=onset), f"voices/mummo/{i}.ogg", 4)
        write_ogg(M.syllable(rng, 100, "o" if vowel == "ä" else vowel, 0.11, breath=0.12, glide=-0.12, onset=onset), f"voices/jussi/{i}.ogg", 4)


def fox_tale():
    intro_fox()
    title_fox()
    fells_music()
    fell_music()
    voices()


if __name__ == "__main__":
    for name in sys.argv[1:] or ["fox_tale"]:
        print(f"{name}:")
        globals()[name]()
