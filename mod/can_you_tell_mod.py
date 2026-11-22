#!/usr/bin/env python3
"""Can You Tell? (MOD mix): eurodance with vocals as a ProTracker module, 136 BPM, C minor, 4 channels.

can_you_tell_mod.py   writes out/can_you_tell_mod.mod and .mp3

The vocals are ours: the chorus of Can You Tell? (code/can_you_tell.py: Lem the Shapeshifter DS 2.5 in a Qwen diva
voice, with its crowd), rendered alone (SOLO=vox PREVIEW=32-40), cut into four 2-bar phrases and made 8-bit
samples at 16 574 Hz: played at C-3 they keep their pitch and tempo. The band is the ST-XX disks: a kick, a kick
with a clap mixed into one sample (four channels are few: the drums share one), an open hi-hat, a bass on the
offbeats, and piano chord stabs made by stacking the M1 piano at the chord's notes (real chords, not arpeggios).

  channel 1: drums (kick on the beat, kick+clap on 2 and 4, the open hat on the offbeats)
  channel 2: the offbeat bass        channel 3: chord stabs        channel 4: the vocals
"""
import os

import mod
import st_index

HERE = os.path.dirname(os.path.abspath(__file__))
STEM = os.path.join(HERE, "..", "code", "renders", "scratch", "can-you-tell_136bpm_Cm-preview32-40-solovox.wav")
BPM = 136


m = mod.Module("can you tell? mod mix")
kick_x, _ = st_index.load("ST-33/bassdrum34")
clap_x, _ = st_index.load("ST-34/claps")
KICK = m.sample(kick_x, name="kick", volume=64)
KICKCLAP = m.sample(mod.mix(kick_x, clap_x), name="kick+clap", volume=64)
OPENHAT = m.sample("ST-83/albanhihatopen", volume=34)
BASS = m.sample("ST-22/Pirates-bass", volume=58, tune=True)
VOICINGS = {"Cm": [60, 63, 67, 72], "Ab": [56, 60, 63, 68], "Eb": [55, 58, 63, 67], "Bb": [58, 62, 65, 70]}
CHORD = {c: m.sample(mod.stack("ST-44/m1piano8'", v), name=f"m1 {c}", volume=44)
         for c, v in VOICINGS.items()}
VOX = [m.sample(p, name=f"cyt vox {i + 1}", volume=64) for i, p in enumerate(mod.phrases(STEM, BPM))]
ROOT = {"Cm": "C-2", "Ab": "G#1", "Eb": "D#2", "Bb": "A#1"}
PROG = ["Cm", "Cm", "Ab", "Ab", "Eb", "Eb", "Bb", "Bb"]
STABS = (0, 3, 6, 8, 11, 14)


def drums(p, bar, kick=True, hats=True, roll=False):
    r0 = bar * 16
    for b in range(4):
        if kick:
            p.put(r0 + 4 * b, 0, "C-2", KICKCLAP if b % 2 else KICK)
        if hats:
            p.put(r0 + 4 * b + 2, 0, "C-3", OPENHAT)
    if roll:                                           # the last half bar: the clap on every row, rising
        for k in range(8, 16):
            p.put(r0 + k, 0, "C-2", KICKCLAP, f"C{20 + 6 * (k - 8):02X}")


def bass(p, bar, chord):
    for k in (2, 6, 10, 14):
        p.put(bar * 16 + k, 1, mod.note_name(mod.note_index(ROOT[chord]) + 12), BASS)


def stabs(p, bar, chord, held=False):
    for k in ((0,) if held else STABS):
        p.put(bar * 16 + k, 2, "C-3", CHORD[chord])


def section(half, kick=True, hats=True, with_bass=True, chords=True, vox=True, held=False, roll=False):
    """Four bars: the chorus's first half (Cm Cm Ab Ab, phrases 1 and 2) or second (Eb Eb Bb Bb, 3 and 4)."""
    p = m.pattern()
    for bar in range(4):
        c = PROG[half * 4 + bar]
        drums(p, bar, kick, hats, roll and bar == 3)
        if with_bass:
            bass(p, bar, c)
        if chords:
            stabs(p, bar, c, held)
    if vox:
        p.put(0, 3, "C-3", VOX[2 * half])
        p.put(32, 3, "C-3", VOX[2 * half + 1])
    return p


INTRO1 = section(0, hats=False, with_bass=False, chords=False, vox=False)
INTRO1.put(0, 2, None, None, "F06")
INTRO1.put(0, 3, None, None, "F88")                    # 136 BPM
INTRO2 = section(1, chords=False, vox=False, roll=True)
INTRO2.put(48, 3, "C-3", VOX[0])                        # "can you tell" as a teaser
CH = [section(0), section(1, roll=True)]
BR = [section(0, kick=False, with_bass=False, held=True), section(1, kick=False, with_bass=False, held=True,
                                                                  roll=True)]
OUT1 = section(0, chords=False, vox=False)
OUT2 = section(1, with_bass=False, chords=False, vox=False)
OUT2.put(63, 0, None, None, "D00")

m.order = [p.index for p in [INTRO1, INTRO2, *CH, *CH, *BR, *CH, *CH, OUT1, OUT2]]

if __name__ == "__main__":
    m.write("out/can_you_tell_mod.mod")
    print(mod.render("out/can_you_tell_mod.mod", "out/can_you_tell_mod.mp3"))
