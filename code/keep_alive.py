#!/usr/bin/env python3
"""Keep Alive: 90's mellow house, 118 BPM, G minor. Saturday's theme of the AI slop music compo.

keep_alive.py [OUT.wav]   (default renders/keep-alive_118bpm_Gm.wav)   PREVIEW=40-48: the first chorus only

A connection that nobody uses is closed by the routers on the way, so every so often a machine sends one tiny,
empty packet, a keep-alive: "are you still there?", and the other side answers "still here". For the network crowd
that is TCP; for everyone else a late-night love song about two people far apart who send each other one small
sign every night, just to keep the line open.

Every note and every sound is written here, by Claude: no samples, no loops. Deep house in the Chicago late-night
way, sparse like the records (the user, 20 November: "the originals back then were more empty grooving, with at
most a simple vocal take on top"): a warm string pad as the bed, a melodic round bassline that walks through the
chords, a round kick, a clap, swung hats, and the keep-alive itself: one soft ping every two bars, into the echo.
Gm9 - Ebmaj7 - Cm7 - D7sus (D7 on the turn into each chorus). No Rhodes (Common Ground has one), one singer, long
stretches of groove without words.

  bars   0-15  intro: drums only (for the DJ); the first pings
        16-23  the pad fades in, the bass
        24-31  the groove; the hook once, softly, at bar 28 (the title)
        32-39  verse                           40-47  chorus
        48-63  the groove, no words: a soft pluck figure answers the bass
        64-71  breakdown: no kick, the pad alone, the pings louder; a whisper: "Are you still there?"
        72-79  the groove back, the hook twice (her answer)   80-87  chorus
        88-95  the hook once more, fading into the groove
        96-111 outro: drums only (for the DJ), the last pings

The singer: Lem the Shapeshifter DS 2.5 (DiffSinger) sings our notes at the written pitch, alive (parts.LEM: the
rule tuner, vibrato, tension, breaths, phrase dynamics, the comp of four takes); SoulX-Singer SVC turns her into
a warm Qwen voice. No doubles, no harmony. Shape the tune fast with Lem alone:
DS_TIMBRE= PREVIEW=40-48 .venv/bin/python keep_alive.py.
"""
import os

import numpy as np

import engine as e
import parts
import room
import voice as V

# ---------------------------------------------------------------- the knobs
TITLE = "Keep Alive"
DAY = "Saturday: 90's mellow house"
BPM, BARS = 118, 112
KEY = "Gm"
PROG = ["Gm9", "Ebmaj7", "Cm7", "D7sus"]
SCALE = "minor"
GROOVE = parts.GROOVES["house"]       # its swing (.16 of a sixteenth) for every part here
LUFS = -10.0
DIVA = os.environ.get("DIVA", "ds:lem")
TIMBRE = "sing_qwen_soul"             # the lead's voice (Common Ground's: Whisper heard her best of all the voices)
STACK = ""                            # one singer: no doubles, no octave, no vocoder (sparse, like the records)
HARMONY = ""                          # no harmony
ACCENT = {"here": 2}

WHISPER = "cast:whisper"
e.seed(BPM)
S = e.Song(bpm=BPM, bars=BARS)
STEP, B = S.step, S.beat
SWING = GROOVE["swing"] * STEP

# the turns into a chorus: D7 (the F# pulls home) instead of D7sus
TURN = {39, 79}
# the pad's voicings, by hand: close, below the voice (F#3 to Eb4), the top note moving by a step at most
PADS = {"Gm9": [53, 57, 58, 62], "Ebmaj7": [51, 55, 58, 62], "Cm7": [55, 58, 60, 63], "D7sus": [55, 57, 60, 62],
        "D7": [54, 57, 60, 62]}
ROOT = {"Gm9": 43, "Ebmaj7": 39, "Cm7": 36, "D7sus": 38, "D7": 38}          # G2, Eb2, C2, D2
SEVENTH = {"Ebmaj7": 11}                                                     # the others: a minor seventh


def chord_of(bar):
    return "D7" if bar in TURN else PROG[bar % 4]


def sw(k):
    """The time of sixteenth k in a bar, swung."""
    return k * STEP + (SWING if k % 2 else 0)


P = parts.Band(S, PROG, scale=SCALE, diva_voice=DIVA, timbre=TIMBRE, stack=STACK, harmony=HARMONY, accent=ACCENT,
               verse_double=0.0)
P.ds_gain = 2.5                       # her level (DS_GAIN overrides it): Common Ground's, where 2.5 beat 2.0


def is_chorus(bar):
    return 40 <= bar < 48 or 80 <= bar < 88


# ---------------------------------------------------------------- drums
def drums(bar, kick=True, clap=True, hats=True, opens=True, rims=False, crash=False, amp=1.0):
    if not S.live(bar):
        return
    t0 = S.at(bar)
    if kick:      # round and short, a soft click
        for b in range(4):
            S.kick(t0 + b * B, .95 * amp, punch=85, base=45, length=.38, click=.12)
    if clap:
        for b in (1, 3):
            S.put("drums", t0 + b * B, e.clap(.36 * amp), .5, wet=.35)
    if hats:
        for k in range(16):
            if k % 4 == 2:
                if opens:
                    S.put("perc", t0 + sw(k), e.hat(.32 * amp, opened=True), .6, wet=.12)
            elif k % 2:
                S.put("perc", t0 + sw(k), e.hat(.15 * amp * (1 + .2 * np.sin(bar * .9 + k))), .64, wet=.05)
    if rims:      # soft, a figure that turns round every two bars
        for k in ((6, 11) if bar % 2 else (3, 10, 14)):
            S.put("perc", t0 + sw(k), e.rim(.2 * amp), .42, wet=.3, echo=.12)
    if crash:
        S.put("perc", t0, e.crash(.3 * amp), .5, wet=.3)


# ---------------------------------------------------------------- bass: round, melodic, walking through the chord
# (sixteenth, interval from the root, length in sixteenths, velocity); "7" is the chord's own seventh
BASSLINE = [(0, 0, 3, 1.0), (3, 12, 1, .5), (6, 7, 2, .75), (8, 0, 2, .85), (10, 12, 1, .45), (11, "7", 2, .62),
            (14, 7, 2, .7)]


def bass(bar, amp=1.0):
    if not S.live(bar):
        return
    c = chord_of(bar)
    for k, iv, n, a in BASSLINE:
        iv = SEVENTH.get(c, 10) if iv == "7" else iv
        S.put("bass", S.at(bar) + sw(k), e.deep_bass(ROOT[c] + iv, n * STEP * .9), .5, .95 * amp * a, wet=0)


# ---------------------------------------------------------------- the pad, the ping, the pluck
def pad(bar, amp=1.0, cut=1400):
    """The warm bed: one bar of the chord, breathing in and out (the next bar overlaps the release)."""
    if not S.live(bar):
        return
    S.put("pads", S.at(bar), e.pad(PADS[chord_of(bar)], S.bar, cut=cut, a=.6, r=1.0), amp=.5 * amp, wet=.45)


def ping(a=1.0, m=86):
    """The keep-alive: one tiny packet, a soft sine on D6 with a glassy overtone, gone in a moment."""
    t = e.tt(.6)
    f = float(e.hz(m))
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * 14) + .25 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 40)
    return y * e.rise(t, .002) * .11 * a


def pings(bar, amp=1.0):
    """Every other bar, on the last offbeat: the ping, panned off-centre, into the echo."""
    if bar % 2 == 1 and S.live(bar):
        S.put("fx", S.at(bar) + sw(14), ping(amp), .3 if bar % 4 == 1 else .7, wet=.35, echo=.55)


# a two-bar figure on the G minor pentatonic, above the pad and out of the voice's way (only where she is silent)
PLUCK = ["D5 - . F5 - . G5 - . . F5 - D5 - . .", ". . C5 - . D5 - . Bb4 - - - . . . ."]


def pluck(bar, amp=1.0):
    if not S.live(bar):
        return
    for t, m, d in S.notes(bar, PLUCK[bar % 2]):
        S.put("lead", t, e.pluck(m, d, cut=2600, voices=3), .62, .16 * amp, wet=.3, echo=.3)


# ---------------------------------------------------------------- the words and the tunes
# one token per sixteenth, "-" holds, "." rests; words one per note, "+" holds a word over the next note. Lem sings
# the written pitch: the steady notes on G4-Bb4 (F4, D4 below), C5 the top (Lem's realistic range ends at D5).
# The lessons of the week: stressed and consonant-heavy words get a quarter note, a short word never starts high
# after a rest, rests make the hook punch, the title on the strong beats.
HOOK = ("Bb4 - - - A4 - G4 - - - . . D4 - G4 - - - A4 - - - - - - - . . . . . .", "keep alive + I'm still here")
# "every night" on two eighths came out "and I need" (Whisper on Lem alone): "each night", a quarter each
CHORUS = [
    HOOK,
    (". . G4 - - - Bb4 - - - A4 - G4 - - - F4 - G4 - F4 - G4 - - - - - - - . .",
     "each night I send a little + sign"),
    (". . Bb4 - Bb4 - C5 - - - Bb4 - A4 - - - G4 - A4 - - - - - - - - - . . . .",
     "just a pulse across + the line"),
    HOOK,
]
VERSE = [
    (". . G4 - G4 - - - F4 - G4 - F4 - . .  G4 - G4 - - - A4 - G4 - - - - - . .",
     "the room is quiet + the screen is low"),
    (". . G4 - Bb4 - - - A4 - G4 - - - . .  F4 - G4 - - - F4 - D4 - - - - - . .",
     "you're far away + the lights don't show"),
    (". . G4 - Bb4 - - - G4 - Bb4 - - - G4 - . . A4 - G4 - F4 - - - - - - - . .",
     "a tiny + packet + soft and slow"),
    (". . F4 - G4 - G4 - Bb4 - A4 - G4 - . .  F4 - G4 - - - - - - - - - . . . .",
     "a little + signal + lets you know"),
]


def sing(bar, line, words, amp=1.0):
    """A line from `bar`, as long as its tokens (16 a bar)."""
    toks = line.split()
    P.diva(bar, " ".join(toks), words, bars=len(toks) / 16, amp=amp)


def chorus(bar0, amp=1.0):
    """8 bars: four lines of two bars, one voice."""
    for i, (line, words) in enumerate(CHORUS):
        sing(bar0 + 2 * i, line, words, amp=amp)


# ---------------------------------------------------------------- the arrangement
# Sparse, like the records: kick, clap, swung hats, the walking bass and the pad carry it; one singer; long
# stretches of groove without words; the ping every two bars; one whispered line in the breakdown.
for bar in range(BARS):
    intro, outro = bar < 16, bar >= 96
    brk = 64 <= bar < 72
    if intro:
        drums(bar, clap=bar >= 8, opens=bar >= 4, crash=bar == 0)
    elif outro:
        drums(bar, clap=bar < 108, opens=bar < 104, crash=bar == 96)
    elif brk:
        drums(bar, kick=False, clap=False, hats=bar >= 68, opens=False, amp=.6)
    else:
        drums(bar, rims=48 <= bar < 64 or bar >= 88, crash=bar in (32, 72))

    if 16 <= bar < 96 and not brk:
        bass(bar, .7 if bar < 20 else (.85 if bar >= 94 else 1.0))
    if 16 <= bar < 24:
        pad(bar, .35 + .65 * (bar - 16) / 7, cut=600 + 120 * (bar - 16))      # fades in, the filter opening
    elif 24 <= bar < 96:
        pad(bar, 1.3 if brk else (.85 if is_chorus(bar) else 1.0), cut=2000 if brk else 1400)
    if 8 <= bar < 104:
        pings(bar, 1.6 if brk else 1.0)
    if 48 <= bar < 64 or 92 <= bar < 96:
        pluck(bar, .8 if bar >= 92 else 1.0)

    # the voice: one singer
    if bar == 28:                                              # the title, once, softly
        sing(bar, *HOOK, amp=.8)
    if 32 <= bar < 40 and bar % 2 == 0:
        sing(bar, *VERSE[(bar - 32) // 2])
    if bar in (40, 80):
        chorus(bar)
    if bar in (72, 76):                                        # after the breakdown: her answer, the hook alone
        sing(bar, *HOOK, amp=.9)
    if bar == 88:                                              # once more, fading into the groove
        sing(bar, *HOOK, amp=.7)


def speech(text, voice, rms=.14):
    y = V._finish(V.tts(text, voice))
    return y * (rms / (np.sqrt(np.mean(y ** 2)) + 1e-9))


if S.live(66, 3):
    S.put("vox", S.at(66), speech("<whisper> Are you still there?", WHISPER), .5, 1.0, wet=.25, echo=.3)
S.put("fx", S.at(64), e.downlifter(S.bar * 2, .2), .5, wet=.3)
S.put("fx", S.at(70), e.riser(S.bar * 2, .2), .5, wet=.3)

P.finish()   # the singer: the whole part, comped from four takes, converted
cut = [(0, 18000), (S.at(64), 18000), (S.at(64) + .05, 6000), (S.at(70), 6000), (S.at(72), 18000),
       (S.n / e.SR, 18000)]
NAME = f"{os.path.basename(__file__)[:-3].replace('_', '-')}_{BPM}bpm_{KEY}"
S.mixdown(parts.out_path(NAME), {"drums": .85, "perc": .7, "bass": .95, "pads": .9, "keys": 1.0, "lead": 1.0,
                                 "vox": 1.45, "fx": .6},
          cut_keys=cut, duck={"pads": .5, "bass": .35, "lead": .2}, room=.2, echo_mix=.4, lufs=LUFS,
          ir=room.impulse_response((7.0, 5.0, 3.0), rt60=1.6))
print(f"share.SONGS row: (\"{NAME}.wav\", \"{TITLE}\", \"{DAY}\", {BPM}, \"{KEY}\", {BARS}),")
