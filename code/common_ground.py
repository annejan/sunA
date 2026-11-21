#!/usr/bin/env python3
"""Common Ground: 90's mellow house, 120 BPM, C minor. Saturday's theme of the AI slop music compo.

common_ground.py [OUT.wav]   (default renders/common-ground_120bpm_Cm.wav)   PREVIEW=44-52: the first chorus only

Two boards on different power supplies cannot understand each other: their signals float, highs read as lows,
every word arrives as noise. Then one black wire joins their grounds. For the soldering crowd the oldest rule on
the bench (connect ground first, the pull-down resistor); for everyone else a late-night love song about two people
who find a place where they can both stand. The night is a hacker-camp field with a thousand blinking badges.

Every note and every sound is written here, by Claude: no samples, no loops. Deep house, sparse like the records
(the user, 20 November: "the originals back then were more empty grooving, with at most a simple vocal take on
top"): a round kick, a clap, swung hats, a round muted bass and a Rhodes comp on minor 9th chords (Cm9 - Fm9 -
Abmaj7 - G7sus, G7 on the turn into each chorus). One singer, long stretches of groove without words.

  bars   0-15  intro: drums only (for the DJ)
        16-19  the Rhodes comes in behind a filter, the bass
        20-31  the groove; the hook once, softly, at bar 24 (the title)
        32-39  verse                           40-47  chorus
        48-63  the groove, no words
        64-71  breakdown: no kick, the Rhodes held, a pad; a whisper: "Always... connect ground first."
        72-79  the groove back, the hook twice   80-87  chorus
        88-95  the hook once more, fading into the groove
        96-111 outro: drums only (for the DJ)

The singer: Lem the Shapeshifter DS 2.5 (DiffSinger) sings our notes at the written pitch; SoulX-Singer SVC turns
her into a soulful Qwen voice. No doubles, no harmony. Shape the tune fast with Lem alone:
DS_TIMBRE= PREVIEW=40-48 .venv/bin/python common_ground.py. The busier first version (organ, strings, shaker,
doubles, harmony, a field call and a crowd) is renders/scratch/common-ground_120bpm_Cm-busy.wav.
"""
import os

import numpy as np

import engine as e
import parts
import room
import voice as V

# ---------------------------------------------------------------- the knobs
TITLE = "Common Ground"
DAY = "Saturday: 90's mellow house"
BPM, BARS = 120, 112
KEY = "Cm"
PROG = ["Cm9", "Fm9", "Abmaj7", "G7sus"]
SCALE = "minor"
GROOVE = parts.GROOVES["house"]       # its swing (.16 of a sixteenth) for every part here
LUFS = -10.0
KEY_CHANGE = 0                        # none: mellow
DIVA = os.environ.get("DIVA", "ds:lem")
TIMBRE = "sing_qwen_soul"             # the lead's voice (fallback: sing_maya_soul)
STACK = ""                            # one singer: no doubles, no octave, no vocoder (sparse, like the records)
HARMONY = ""                          # no harmony
ACCENT = {"ground": 2}

WHISPER = "cast:whisper"
e.seed(BPM)
S = e.Song(bpm=BPM, bars=BARS)
STEP, B = S.step, S.beat
SWING = GROOVE["swing"] * STEP

# the turns into a chorus: G7 (the B natural pulls home) instead of G7sus
TURN = {39, 79}
# the Rhodes voicings, by hand: rootless, close, below the voice (Eb3 to E4), the top note moving by a step at most
KEYS = {"Cm9": [51, 55, 58, 62], "Fm9": [55, 56, 60, 63], "Abmaj7": [55, 58, 60, 63], "G7sus": [53, 55, 60, 62],
        "G7": [53, 59, 62, 64]}


def chord_of(bar):
    return "G7" if bar in TURN else PROG[bar % 4]


def sw(k):
    """The time of sixteenth k in a bar, swung."""
    return k * STEP + (SWING if k % 2 else 0)


P = parts.Band(S, PROG, scale=SCALE, diva_voice=DIVA, timbre=TIMBRE, stack=STACK, harmony=HARMONY, accent=ACCENT,
               verse_double=0.0)
P.ds_gain = 2.5                       # her level (DS_GAIN overrides it); 2.0: Whisper 53 %, 2.5: 74 %


def is_chorus(bar):
    return 40 <= bar < 48 or 80 <= bar < 88


# ---------------------------------------------------------------- drums
def drums(bar, kick=True, clap=True, hats=True, opens=True, shaker=False, rims=False, crash=False, amp=1.0):
    if not S.live(bar):
        return
    t0 = S.at(bar)
    if kick:      # round and short, a soft click
        for b in range(4):
            S.kick(t0 + b * B, .95 * amp, punch=90, base=46, length=.36, click=.15)
    if clap:
        for b in (1, 3):
            S.put("drums", t0 + b * B, e.clap(.4 * amp), .5, wet=.3)
            S.put("drums", t0 + b * B, e.snare(.12 * amp), .5, wet=.2)
    if hats:
        for k in range(16):
            if k % 4 == 2:
                if opens:
                    S.put("perc", t0 + sw(k), e.hat(.36 * amp, opened=True), .58, wet=.1)
            else:
                a = (.17 if k % 2 else .26) * amp * (1 + .15 * np.sin(bar * 1.3 + k))
                S.put("perc", t0 + sw(k), e.hat(a), .62, wet=.05)
    if shaker:
        for k in range(16):
            S.put("perc", t0 + sw(k), e.shaker((.28 if k % 2 else .16) * amp), .4, wet=.08)
    if rims:      # soft, between the claps, another figure every other bar
        for k in ((3, 6, 11, 14) if bar % 2 else (3, 10, 13)):
            S.put("perc", t0 + sw(k), e.rim(.22 * amp), .45, wet=.25, echo=.1)
    if crash:
        S.put("perc", t0, e.crash(.35 * amp), .5, wet=.3)


# ---------------------------------------------------------------- bass: round, muted, a little bounce
BASSLINE = [(0, 0, 2, .85), (3, 0, 3, 1.0), (7, 12, 1, .5), (10, 0, 3, .9), (14, 7, 2, .6)]


def bass(bar, amp=1.0):
    if not S.live(bar):
        return
    root = e.root_note(chord_of(bar).replace("7sus", "7"), lo=33)          # C2, F2, Ab2, G2: low but still on a laptop's speaker
    for k, iv, n, a in BASSLINE:
        S.put("bass", S.at(bar) + sw(k), e.deep_bass(root + iv, n * STEP * .9), .5, .95 * amp * a, wet=0)


# ---------------------------------------------------------------- keys
COMP = [(0, 5, .62), (6, 2, .48), (10, 5, .58)]          # sixteenth, length in sixteenths, velocity


def rhodes_comp(bar, amp=1.0, cut=None, held=False):
    """The Rhodes on the chord: a syncopated comp (or one held chord), a push into the next bar every 4 bars, a
    tremolo that pans gently (one cycle in 2 bars)."""
    if not S.live(bar):
        return
    hits = [(0, 15, .55)] if held else COMP + ([(15, 1, .42)] if bar % 4 == 3 else [])
    for k, n, vel in hits:
        notes = KEYS[chord_of(bar + 1 if k == 15 else bar)]
        for j, m in enumerate(notes):
            g = e.rhodes(m, n * STEP, vel)
            if cut:
                g = e.lowpass(g, cut)
            pan = .5 + .18 * np.sin(2 * np.pi * (bar + k / 16) / 2)
            S.put("keys", S.at(bar) + sw(k) + j * .006, g, pan, .42 * amp, wet=.3, echo=.08)


def pad(bar, amp=1.0, cut=1500):
    if not S.live(bar):
        return
    S.put("pads", S.at(bar), e.pad(KEYS[chord_of(bar)], S.bar, cut=cut, a=.5, r=.8), amp=.4 * amp, wet=.4)


# ---------------------------------------------------------------- the words and the tunes
# one token per sixteenth, "-" holds, "." rests; words one per note, "+" holds a word over the next note. Lem sings
# the written pitch. The verse stays on G4-Ab4 (Eb4-F4 below), the hook peaks on C5 (no D5: "close" on D5 came
# out "cuss" in two of three takes). Stressed and consonant-heavy words get a quarter note, rests after "come" and
# "down" for punch. Lem says a short word that starts high after a rest badly ("down" on Bb4: "bent", "bam"), so
# "come" takes the Bb4 and "down" the G4 (Whisper: 3 of 3 takes "come down to common ground").
HOOK = ("Bb4 - - . G4 - - . G4 - G4 - Bb4 - C5 -  - - - - - - . .", "come down to common + ground")
CHORUS = [
    HOOK,
    (". . Eb4 - Eb4 - G4 - - - Ab4 - - - . .  G4 - - - F4 - G4 - - - - - - - . .", "where the noise can't make a sound"),
    ("G4 - G4 - Bb4 - - - G4 - Bb4 - C5 - - -  - - - - - - . .", "pull me close pull me down"),
    HOOK,
]
VERSE1 = [
    (". . G4 - G4 - - - G4 - Bb4 - - - . .  Ab4 - Ab4 - - - G4 - F4 - - - - - . .", "I sent you words you heard the noise"),
    (". . G4 - Ab4 - - - G4 - Eb4 - - - . .  . . F4 - G4 - - - F4 - G4 - - - . .", "your high came low I lost your voice"),
    (". . G4 - G4 - - - Bb4 - - - G4 - - .  . . Ab4 - Ab4 - - - G4 - F4 - - - . .", "two souls floating + no place to stand"),
    (". . Eb4 - G4 - Ab4 - - - G4 - - - . .  G4 - - - F4 - G4 - - - - - - - . .", "till one black wire held my hand"),
]
def sing(bar, line, words, amp=1.0, harmony=False, doubles=False):
    """A diva line from `bar`, as long as its tokens (16 a bar). harmony: the third above in the harmony voice (and
    the doubles); doubles: the doubles without the harmony (the hook, whose third would go above C5)."""
    toks = line.split()
    bars = len(toks) / 16
    P.diva(bar, " ".join(toks), words, bars=bars, amp=amp, choir=.6 if harmony else 0.0)
    if doubles and not harmony and P.ds and S.live(bar, bars):
        t0, t1, _ = P.ds_double[-1]
        P.ds_double[-1] = (t0, t1, .55)


def chorus(bar0, amp=1.0):
    """8 bars: four lines of two bars, one voice."""
    for i, (line, words) in enumerate(CHORUS):
        sing(bar0 + 2 * i, line, words, amp=amp)


# ---------------------------------------------------------------- spoken voices
def speech(text, voice, rms=.14):
    y = V._finish(V.tts(text, voice))
    return y * (rms / (np.sqrt(np.mean(y ** 2)) + 1e-9))


def say(t, text, voice, amp=.8, pan=.5, wet=.15, echo=.12):
    """A spoken line at its own pace from second t; returns when it ends (seconds)."""
    bar = int(t / S.bar)
    y = speech(text, voice)
    if S.live(bar, 3):
        S.put("vox", t, y, pan, amp, wet=wet, echo=echo)
    return t + len(y) / e.SR


# ---------------------------------------------------------------- the arrangement
# Sparse, like the records (the user, 20 November: "the originals back then were more empty grooving, with at most a
# simple vocal take on top"): kick, clap, swung hats, the round bass and the Rhodes comp carry it; one singer, no
# doubles, no harmony; long stretches of groove without words; one whispered line in the breakdown.
for bar in range(BARS):
    intro, outro = bar < 16, bar >= 96
    brk = 64 <= bar < 72
    entry = 16 <= bar < 20
    if intro:
        drums(bar, clap=bar >= 8, opens=bar >= 4, crash=bar == 0)
    elif outro:
        drums(bar, clap=bar < 108, opens=bar < 104, crash=bar == 96)
    elif brk:
        drums(bar, kick=False, clap=False, hats=bar >= 68, opens=False, amp=.6)
    else:
        drums(bar)

    if 16 <= bar < 96 and not brk:
        bass(bar, .7 if entry else (.85 if bar >= 94 else 1.0))
    if entry:
        rhodes_comp(bar, cut=500 * 2 ** (bar - 16))           # the filter opens over 4 bars
    elif 20 <= bar < 96 and not brk:
        rhodes_comp(bar, .9 if is_chorus(bar) else 1.0, cut=2500 if bar >= 94 else None)
    elif brk:
        rhodes_comp(bar, 1.1, held=True)
        pad(bar, .8)

    # the voice: one singer
    if bar == 24:                                              # the title, once, softly (8 bars after the entry)
        sing(bar, *HOOK, amp=.8)
    if 32 <= bar < 40 and bar % 2 == 0:
        sing(bar, *VERSE1[(bar - 32) // 2])
    if bar in (40, 80):
        chorus(bar)
    if bar in (72, 76):                                        # after the breakdown: the hook alone
        sing(bar, *HOOK, amp=.9)
    if bar == 88:                                              # once more, fading into the groove
        sing(bar, *HOOK, amp=.7)

say(S.at(66), "<whisper> Always... connect ground first.", WHISPER, amp=1.0, wet=.25, echo=.25)
S.put("fx", S.at(64), e.downlifter(S.bar * 2, .2), .5, wet=.3)

P.finish()   # the produced diva: the whole part in one take, converted, doubled, the harmony
# the master filter: the breakdown a little darker, open again for the build
cut = [(0, 18000), (S.at(76), 18000), (S.at(76) + .05, 7000), (S.at(88), 7000), (S.at(91), 18000),
       (S.n / e.SR, 18000)]
NAME = f"{os.path.basename(__file__)[:-3].replace('_', '-')}_{BPM}bpm_{KEY}"
S.mixdown(parts.out_path(NAME), {"drums": .85, "perc": .7, "bass": .9, "pads": .9, "keys": 1.05, "lead": 1.0,
                                 "vox": 1.45, "fx": .5},
          cut_keys=cut, duck={"pads": .5, "bass": .35, "keys": .2}, room=.2, echo_mix=.4, lufs=LUFS,
          ir=room.impulse_response((7.0, 5.0, 3.0), rt60=1.6))
print(f"share.SONGS row: (\"{NAME}.wav\", \"{TITLE}\", \"{DAY}\", {BPM}, \"{KEY}\", {BARS}),")
