#!/usr/bin/env python3
"""The Rhythm Of The Badge (MOD mix): our eurodance song as a ProTracker module, 134 BPM, E minor, 4 channels.

rhythm_of_the_badge_mod.py   writes out/rhythm_of_the_badge_mod.mod and .mp3

The vocals are ours: the chorus of The Rhythm Of The Badge (code/rhythm_of_the_badge.py: Lem the Shapeshifter DS
2.5 in the Qwen diva voice, with its doubles, octave and vocoder), rendered alone (SOLO=vox PREVIEW=32-40) and cut
into four 2-bar phrases. The hoover is made here as an 8-bit sample, the way the song makes it: detuned saws and a
sub saw, scooping up into the note; it plays the song's 3-3-2 riff, and every other bar the last note dives an
octave (portamento down, 2xx). Drums, bass and the piano (stacked into chords) are from the ST-XX disks.

  channel 1: kick, kick+clap on 2 and 4, open hat on the offbeats      channel 2: the rolling offbeat bass
  channel 3: the hoover riff, or the piano chords                      channel 4: the diva
Verse chords Em C Am B (the riff), chorus Em C G D, a chord a bar.
"""
import os

import numpy as np

import mod
import st_index

HERE = os.path.dirname(os.path.abspath(__file__))
STEM = os.path.join(HERE, "..", "code", "renders", "scratch",
                    "rhythm-of-the-badge_134bpm_Em-preview32-40-solovox.wav")
BPM = 134
R = mod.C3_RATE


def hoover(seconds=1.6, hz=261.63):
    """The hoover: three detuned saws and a sub saw an octave down, scooping up two semitones in 60 ms, filtered a
    little; C (C4) on C-3, looped over its body."""
    t = np.arange(int(seconds * R)) / R
    scoop = 2 ** (-2 / 12 * np.exp(-t / .03))
    y = np.zeros(len(t))
    for det, a in ((-.012, .6), (0, 1.0), (.013, .6), (-.5, .7)):        # .5: the sub, an octave down
        f = hz * (1 + det) * scoop if det > -.4 else hz / 2 * scoop
        ph = np.cumsum(f / R)
        y += a * (2 * (ph % 1) - 1)
    from scipy import signal
    y = signal.sosfilt(signal.butter(2, 5500, fs=R, output="sos"), y)
    return mod.int8(y * np.minimum(t / .004, 1), .9)


m = mod.Module("rhythm of the badge mod")
kick_x, _ = st_index.load("ST-33/bassdrum34")
clap_x, _ = st_index.load("ST-34/claps")
KICK = m.sample(kick_x, name="kick", volume=64)
KICKCLAP = m.sample(mod.mix(kick_x, clap_x), name="kick+clap", volume=64)
OPENHAT = m.sample("ST-83/albanhihatopen", volume=32)
BASS = m.sample("ST-22/Pirates-bass", volume=58, tune=True)
hv = hoover()
HOOVER = m.sample(hv, name="hoover", volume=44, loop=(int(.3 * R) // 2 * 2, (len(hv) - int(.3 * R)) // 2 * 2))
VOICE = {"Em": [59, 64, 67, 71], "C": [60, 64, 67, 72], "G": [59, 62, 67, 71], "D": [57, 62, 66, 69],
         "Am": [57, 60, 64, 69], "B": [59, 63, 66, 71]}
PIANO = {c: m.sample(mod.stack("ST-44/m1piano8'", v), name=f"m1 {c}", volume=42) for c, v in VOICE.items()}
VOX = [m.sample(p, name=f"badge vox {i + 1}", volume=64) for i, p in enumerate(mod.phrases(STEM, BPM))]

VERSE, CHORUS = ["Em", "C", "Am", "B"], ["Em", "C", "G", "D"]
ROOT = {"Em": "E-2", "C": "C-2", "G": "G-1", "D": "D-2", "Am": "A-1", "B": "B-1"}
RIFF = [(0, 0), (3, 0), (6, 12), (8, 0), (11, 7), (14, 12)]          # the song's 3-3-2 riff: (row, semitones)
STABS = (0, 3, 6, 8, 11, 14)


def up(note, st):
    return mod.note_name(mod.note_index(note) + st)


def drums(p, bar, kick=True, clap=True, hats=True, roll=False):
    r0 = bar * 16
    for b in range(4):
        if kick:
            p.put(r0 + 4 * b, 0, "C-2", KICKCLAP if clap and b % 2 else KICK)
        if hats:
            p.put(r0 + 4 * b + 2, 0, "C-3", OPENHAT)
    if roll:
        for k in range(8, 16):
            p.put(r0 + k, 0, "C-2", KICKCLAP, f"C{20 + 6 * (k - 8):02X}")


def bass(p, bar, chord):
    for k in (2, 6, 10, 14):
        p.put(bar * 16 + k, 1, ROOT[chord], BASS)                  # E2 and around: the bass's own register


def riff(p, bar, chord):
    root = ROOT[chord]                               # the hoover sample is C4 on C-3: E-2 sounds E3
    for k, st in RIFF:
        p.put(bar * 16 + k, 2, up(root, st), HOOVER)
    if bar % 2:
        p.put(bar * 16 + 15, 2, None, None, "230")   # the dive: down fast
    else:
        p.put(bar * 16 + 15, 2, None, None, "C00")


def piano(p, bar, chord, held=False):
    for k in ((0,) if held else STABS):
        p.put(bar * 16 + k, 2, "C-3", PIANO[chord])


def section(prog, kick=True, clap=True, hats=True, with_bass=True, part="riff", vox=None, roll=False):
    """Four bars on a progression. part: "riff" (the hoover), "piano" (stabs), "held" (one chord a bar), None.
    vox: (first phrase, second phrase) at bars 0 and 2."""
    p = m.pattern()
    for bar, c in enumerate(prog):
        drums(p, bar, kick, clap, hats, roll and bar == 3)
        if with_bass:
            bass(p, bar, c)
        if part == "riff":
            riff(p, bar, c)
        elif part in ("piano", "held"):
            piano(p, bar, c, part == "held")
    if part is None:
        p.put(1, 2, None, None, "C00")
    if vox:
        for row, i in zip((0, 32), vox):
            if i is not None:
                p.put(row, 3, "C-3", VOX[i])
    return p


INTRO = section(CHORUS, clap=False, hats=False, with_bass=False, part=None)
INTRO.put(0, 1, None, None, "F06")
INTRO.put(0, 3, None, None, "F86")                    # 134 BPM
INTRO2 = section(CHORUS, with_bass=False, part=None, roll=True)
RIFF1 = section(VERSE)
RIFF2 = section(VERSE, roll=True)
RIFF2.put(48, 3, "C-3", VOX[0])                       # "feel the rhythm" as a teaser
CH1 = section(CHORUS, part="piano", vox=(0, 1))
CH2 = section(CHORUS, part="piano", vox=(2, 3), roll=True)
CH1R = section(CHORUS, part="riff", vox=(0, 1))       # the chorus again, over the hoover
CH2R = section(CHORUS, part="riff", vox=(2, 3), roll=True)
BREAK1 = section(CHORUS, kick=False, with_bass=False, hats=False, part="held", vox=(2, None))
BREAK2 = section(CHORUS, kick=False, with_bass=False, part="held", vox=(None, 3), roll=True)
OUT = section(VERSE, part=None)
OUT2 = section(VERSE, clap=False, hats=False, with_bass=False, part=None)
OUT2.put(63, 0, None, None, "D00")

m.order = [p.index for p in [INTRO, INTRO2, RIFF1, RIFF2, CH1, CH2, RIFF1, RIFF2, CH1R, CH2R, BREAK1, BREAK2,
                              CH1, CH2, CH1R, CH2R, RIFF1, RIFF2, OUT, OUT2]]

if __name__ == "__main__":
    m.write("out/rhythm_of_the_badge_mod.mod")
    print(mod.render("out/rhythm_of_the_badge_mod.mod", "out/rhythm_of_the_badge_mod.mp3"))
