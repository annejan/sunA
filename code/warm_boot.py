#!/usr/bin/env python3
"""Warm Boot: 90's mellow house, 120 BPM, A minor. Saturday's theme of the AI slop music compo.

warm_boot.py [OUT.wav]   (default renders/warm-boot_120bpm_Am.wav)

Every note and every sound here is written by Claude, in this file: no samples, no loops. A slow morning after a
night of hacking: shuffled 909 hats, a Rhodes, an M1 organ, a round bass, vinyl dust, and one singer who asks for
a warm boot. The first and last 16 bars are drums only, for the DJ.

  bars   0-15  intro: kick and hats, then clap and shaker (drums only)
        16-31  the bass, and a Rhodes behind a door
        32-47  verse: the Rhodes, the pad (and the robot's "ooh"s; singer D has them only in the break); two
               soft lines (40, 44): "bring me back slow"
        48-63  chorus: M1 organ stabs; a line every 4 bars: "hold me tight / we made it through the night /
               warm boot, baby / you light me up"
        64-71  break: no kick, no bass, filtered; one soft "hold on"; a riser out of it
        72-87  chorus again, with a Rhodes melody on top
        88-103 winding down: the pad and the organ go, the bass and the Rhodes stay; "warm boot, baby",
               "you light me up"
       104-119 outro: drums only

The singer (21 November): Lem the Shapeshifter DS 2.5 (DiffSinger) sings our notes and words at the written pitch;
Lem sings it four times and each line comes from the take Whisper hears best (the comp); SoulX-Singer SVC
turns her into a soulful Qwen voice. One singer, no doubles, no harmony, no vocoder, long stretches
of groove without words (90's mellow house, the user: "the originals back then were more empty grooving, with at
most a simple vocal take on top"). Shape the tune fast with Lem alone: DS_TIMBRE= PREVIEW=48-64 .venv/bin/python
warm_boot.py. SINGER=robot: the approved version's vocoder robot ("warm boot, baby / all night long", "standby")
instead; CHOPS=1: the ACE-Step vocal chops while the song winds down (both A/B switches, renders to scratch).

The Rhodes is a DX7-style FM electric piano (dx7.py) and the reverb is a simulated room (room.py), both ported
from the NPU demos in ~/Projects/npu. KEYS=fm and ROOM=noise switch back to the simple versions in engine.py.
"""
import os
import sys

import numpy as np

import engine as e
import dx7
import parts
import room

KEYS = os.environ.get("KEYS", "dx7")
ROOM = os.environ.get("ROOM", "sim")


def rhodes(m, d, vel):
    """The electric piano: the DX7 E.Piano (dx7.py), or the simple FM one from engine.py with KEYS=fm."""
    if KEYS == "fm":
        return e.rhodes(m, d, vel)
    return dx7.note("epiano", m, d, vel, tail=.9)

e.seed(120)
S = e.Song(bpm=120, bars=120)
STEP = S.step
SWING = .16 * STEP          # 58 % shuffle on the sixteenths

PROG = ["Am9", "Fmaj9", "Dm9", "Em7"]
# the voice: "ds", singer D (Lem the Shapeshifter DS 2.5 in a Qwen soul voice, our notes and words); SINGER=robot:
# the approved render's vocoder robot (engine.robot), for an A/B
SINGER = os.environ.get("SINGER", "ds")
DIVA = os.environ.get("DIVA", "ds:lem")
TIMBRE = "sing_qwen_soul"             # the lead's voice (fallback: sing_maya_soul)
STACK = ""                            # one singer: no doubles, no octave, no vocoder (sparse, like the records)
HARMONY = ""                          # no harmony
ACCENT = {"tight": 2}
# CHOPS=1 (19 November, an A/B; research/toolkit-2026-11-19.md): the 1990s house vocal stab while the song winds
# down: words of an ACE-Step house diva (the voice menu's take, a cappella), each tuned to the bar's chord (chops.py)
CHOPS = os.environ.get("CHOPS") == "1"
CHOP_TAKE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "renders", "ace", "takes", "menu",
                         "house-diva_s2_46f86529.wav")
CHOP_PATTERNS = ["hold . . on . . tight . . . night . . . . .",
                 ". . light . up . . . night . . . hold . on ."]


def chord_of(bar):
    return PROG[bar % 4]


def sw(k):
    """The time of sixteenth k in a bar, swung."""
    return k * STEP + (SWING if k % 2 else 0)


# ---------------------------------------------------------------- drums
def drums(bar, kick=True, clap=True, hats=True, shaker=False, rimshots=False, crash=False, amp=1.0):
    t0 = S.at(bar)
    if kick:
        for b in range(4):
            S.kick(t0 + b * S.beat, .95 * amp, punch=90, base=46, length=.42, click=.15)
    if clap:
        for b in (1, 3):
            S.put("drums", t0 + b * S.beat, e.clap(.5 * amp), .52, wet=.25)
            S.put("drums", t0 + b * S.beat, e.snare(.18 * amp), .5, wet=.2)
    if hats:
        for k in range(16):
            if k % 4 == 2:
                S.put("perc", t0 + sw(k), e.hat(.42 * amp, opened=True), .6, wet=.1)
            else:
                a = (.22 if k % 2 else .3) * amp * (1 + .15 * np.sin(bar + k))
                S.put("perc", t0 + sw(k), e.hat(a), .62, wet=.05)
    if shaker:
        for k in range(16):
            S.put("perc", t0 + sw(k), e.shaker((.35 if k % 2 else .2) * amp), .3, wet=.08)
    if rimshots:
        for k in (3, 7, 11, 14) if bar % 2 else (3, 10, 13):
            S.put("perc", t0 + sw(k), e.rim(.35 * amp), .38, wet=.2, echo=.15)
    if crash:
        S.put("perc", t0, e.crash(.5), .5, wet=.3)


# ---------------------------------------------------------------- bass
BASSLINE = [(0, 0, 3), (3, 0, 1), (6, 12, 1), (8, 0, 2), (11, 7, 2), (14, 12, 1)]


def bass(bar, amp=1.0):
    root = e.root_note(chord_of(bar), lo=33)
    for k, iv, n in BASSLINE:
        S.put("bass", S.at(bar) + sw(k), e.deep_bass(root + iv, n * STEP * .9), .5, .9 * amp, wet=0)


# ---------------------------------------------------------------- keys
RHODES_COMP = [(0, 3, .75), (6, 2, .55), (10, 4, .7)]    # sixteenth, length in sixteenths, velocity


def rhodes_comp(bar, amp=1.0, cut=None):
    notes = e.voicing(chord_of(bar), lo=55, drop_root=True)
    for k, n, vel in RHODES_COMP:
        for j, m in enumerate(notes):
            g = rhodes(m, n * STEP, vel)
            if cut:
                g = e.lowpass(g, cut)
            # a tremolo that pans the Rhodes side to side, one cycle a bar
            pan = .5 + .3 * np.sin(2 * np.pi * (bar + k / 16) / 2)
            S.put("keys", S.at(bar) + sw(k) + j * .006, g, pan, .4 * amp, wet=.3, echo=.12)


ORGAN = [2, 6, 10, 13]


def organ_stabs(bar, amp=1.0):
    notes = e.close_voicing(chord_of(bar), lo=60, hi=76)[:4]
    for k in ORGAN:
        for m in notes:
            S.put("keys", S.at(bar) + sw(k), e.organ(m, STEP * 1.2), .45, .35 * amp, wet=.2, echo=.18)


def pads(bar, amp=1.0, cut=1600):
    notes = e.voicing(chord_of(bar), lo=52)
    S.put("pads", S.at(bar), e.pad(notes, S.bar, cut=cut), amp=.5 * amp, wet=.4)


def oohs(bar, amp=1.0):
    """A choir's 'ooh' on the top of the chord, every other bar, left and right."""
    top = e.close_voicing(chord_of(bar), lo=64, hi=76)
    for j, m in enumerate(top[-2:]):
        S.put("pads", S.at(bar, .5), e.vox(m, S.bar * 1.6, "u"), .25 + .5 * j, .18 * amp, wet=.6, echo=.2)


MELODY = [
    "E5 - - D5 E5 - G5 - . . E5 - D5 - C5 -", "A4 - - - - - . . C5 - - D5 E5 - - -",
    "F5 - - E5 D5 - C5 - . . A4 - C5 - D5 -", "B4 - - - - - . . G4 - B4 - D5 - E5 -",
]


def melody(bar, amp=1.0):
    for t, m, d in S.notes(bar, MELODY[bar % 4]):
        S.put("lead", t, rhodes(m + 12, d, .95), .55, .24 * amp, wet=.35, echo=.35)
        S.put("lead", t, rhodes(m, d, .6), .45, .135 * amp, wet=.3)


# ---------------------------------------------------------------- the robot
B = S.beat


def warm_boot_baby(bar, amp=1.0):
    S.sing(S.at(bar), [("", ["w", "o", "r", "m"], 64, B * 1.0, ""), ("b", ["u"], 64, B * 1.0, "t"),
                       ("b", ["e", "i"], 62, B * .5, ""), ("b", ["i"], 60, B * 1.5, "")], amp=amp)


def all_night_long(bar, amp=1.0):
    S.sing(S.at(bar), [("", ["o", "l"], 57, B * 1.0, ""), ("", ["n", "ah", "i"], 60, B * 1.0, "t"),
                       ("", ["l", "o", "n"], 59, B * 2.0, "")], amp=amp)


def bring_me_back(bar, amp=1.0):
    S.sing(S.at(bar), [("b", ["r", "i", "n"], 57, B * .5, ""), ("", ["m", "i"], 57, B * .5, ""),
                       ("b", ["a"], 60, B * .5, "k"), ("", ["ah"], 62, B * .5, "p"),
                       ("s", ["l", "o", "u"], 64, B * 2.0, "")], amp=amp)


def standby(bar, amp=1.0):
    S.sing(S.at(bar, 1), [("s", ["a", "e", "n"], 64, B * 1.0, "d"), ("b", ["ah", "i"], 60, B * 2.0, "")], amp=amp)


# ---------------------------------------------------------------- singer D
# one token per sixteenth, "-" holds, "." rests; words one per note, "+" holds a word over the next note. Lem sings
# the written pitch. Every line starts on an Am9 bar and rings into the Fmaj9 (Dm9 - Em7 in the break): A4, G4, E4
# and C5 are chord tones of both, the long notes land on them. Steady on G4-A4, the peak C5 (nothing above), the
# stressed and consonant-heavy words a quarter note. Whisper on Lem alone and in the mix (21 November): "through"
# on an eighth came out "to" (a half note: "through"); "light" after a rest came out "night" or "let" ("you light":
# mostly "light me up"); "hold on tight" on the downbeat (the crash, the "h" lost) came out "all the time", so the
# hook starts on beat 2 and says "hold me tight"; "warm" stays the weak word ("one boot baby" in about half the
# takes: Lem's held "aw" with a soft r), whatever its length or note.
HOLD_ON = (". . . . A4 - - - G4 - - - A4 - - -  - - - - - - - - . . . . . . . .", "hold me tight")
THROUGH = ("E4 - G4 - - - G4 - - - A4 - - - - -  G4 - - - A4 - - - - - - - . . . .", "we made it through the night")
WARM_BOOT = ("E4 - - - G4 - - . A4 - G4 - - - - -  - - - - - - . . . . . . . . . .", "warm boot baby +")
LIGHT_ME = (". . E4 - G4 - - - A4 - - - C5 - - -  - - - - . . . . . . . . . . . .", "you light me up")
CHORUS = [HOLD_ON, THROUGH, WARM_BOOT, LIGHT_ME]          # a line every 4 bars, 2 bars of groove after each
VERSE = [(". . E4 - - - E4 - G4 - - - A4 - - -  - - - - - - - - . . . . . . . .", "bring me back slow"),
         (". . E4 - G4 - - - A4 - - - G4 - - -  - - E4 - - - - - . . . . . . . .", "the screens still glow +")]
BREAK = (". . . . A4 - - - - - - . G4 - - -  - - - - - - - - . . . . . . . .", "hold on")

P = None
if SINGER != "robot":
    P = parts.Band(S, PROG, scale="minor", diva_voice=DIVA, timbre=TIMBRE, stack=STACK, harmony=HARMONY,
                   accent=ACCENT, verse_double=0.0)
    P.ds_gain = 2.0                   # the singer's level (DS_GAIN overrides it)


def sing(bar, line, words, amp=1.0):
    """A line of singer D from `bar`, as long as its tokens (16 a bar)."""
    toks = line.split()
    P.diva(bar, " ".join(toks), words, bars=len(toks) / 16, amp=amp)


# ---------------------------------------------------------------- the arrangement
for bar in range(120):
    c = chord_of(bar)
    intro, outro = bar < 16, bar >= 104
    brk = 64 <= bar < 72
    if intro:
        drums(bar, clap=bar >= 8, shaker=bar >= 8, crash=bar == 0)
    elif outro:
        drums(bar, clap=bar < 112, shaker=bar < 116, rimshots=bar < 108, crash=bar == 104)
    elif brk:
        drums(bar, kick=False, clap=bar >= 68, hats=bar >= 66, shaker=True, amp=.7)
    else:
        drums(bar, shaker=True, rimshots=bar >= 24, crash=bar in (32, 48, 72, 88))

    if 16 <= bar < 104 and not brk:
        bass(bar, .6 if bar < 20 else 1.0)
    if 24 <= bar < 32:
        rhodes_comp(bar, .8, cut=900 + (bar - 24) * 300)
    if 32 <= bar < 104:
        rhodes_comp(bar, .85 if brk else 1.0)
    # singer D gets room (the producer, 21 November: "too busy" in the vocal range): the "ooh"s only in the break,
    # the organ and the Rhodes melody only in the two bars after each sung line (an answer, not a second singer),
    # the pad softer. The robot keeps the approved arrangement
    room_for_her = SINGER != "robot"
    answer = not room_for_her or bar % 4 >= 2
    if 32 <= bar < 88:
        pads(bar, 1.2 if brk else (.7 if room_for_her else 1.0), cut=2400 if brk else 1600)
    if 32 <= bar < 88 and bar % 2 == 0 and (brk or not room_for_her):
        oohs(bar, 1.4 if brk else 1.0)
    if ((48 <= bar < 64) or (72 <= bar < 88)) and answer:
        organ_stabs(bar)
    if 72 <= bar < 88 and answer:
        melody(bar)
    if 96 <= bar < 104:
        pads(bar, .5, cut=900)

    if SINGER == "robot":             # the approved render's vocoder robot
        if bar in (40, 44):
            bring_me_back(bar, .8)
        if (48 <= bar < 64 or 72 <= bar < 88) and bar % 4 == 0:
            warm_boot_baby(bar)
        if (48 <= bar < 64 or 72 <= bar < 88) and bar % 4 == 2:
            all_night_long(bar)
        if brk and bar % 2 == 0:
            standby(bar, 1.1)
        if bar in (92, 100):
            warm_boot_baby(bar, .7)
    else:                             # singer D: one voice, a line every 4 bars at most
        if bar in (40, 44):
            sing(bar, *VERSE[(bar - 40) // 4], amp=.85)
        if (48 <= bar < 64 or 72 <= bar < 88) and bar % 4 == 0:
            sing(bar, *CHORUS[(bar - (48 if bar < 64 else 72)) // 4])
        if bar == 66:
            sing(bar, *BREAK, amp=.8)
        if bar == 92:
            sing(bar, *WARM_BOOT, amp=.8)
        if bar == 100:
            sing(bar, *LIGHT_ME, amp=.7)
    if CHOPS and 88 <= bar < 104 and bar not in (92, 93, 100, 101):
        import chops
        if "BANK" not in globals():
            BANK = chops.bank(CHOP_TAKE, {"hold", "on", "tight", "night", "light", "up"})
        chops.play(S, bar, BANK, CHOP_PATTERNS[bar % 2], c, amp=.9, swing=SWING)

# the dust on the record, all the way through (a little louder at the start, before the music comes)
dust = e.crackle(S.length)
S.put("fx", 0, dust, .5, 1.0, wet=0)
S.put("fx", S.at(70), e.riser(S.bar * 2, .25), .5, wet=.3)
S.put("fx", S.at(64), e.downlifter(S.bar * 2, .2), .5, wet=.3)

if P:
    # the producer's comp (parts.Band, DS_COMP): Lem sings the part 4 times and each line comes from the take
    # Whisper hears best; Lem's takes differ line by line ("hold me tight" came out "on the side" in one take of
    # three). Set here, not as a default in the environment: DS_COMP is an A/B switch, it would send the song's
    # render to scratch. DS_COMP=0 for a single take.
    comp_here = "DS_COMP" not in os.environ
    if comp_here:
        os.environ["DS_COMP"] = "1"
    P.finish()                        # singer D's one take into the mix (converted into the Qwen soul voice)
    if comp_here:
        del os.environ["DS_COMP"]
cut = [(0, 18000), (S.at(64), 18000), (S.at(64) + .05, 1800), (S.at(70), 2600), (S.at(72) - .02, 9000),
       (S.at(72), 18000), (S.n / e.SR, 18000)]
here = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "renders", "warm-boot_120bpm_Am.wav")
os.makedirs(os.path.dirname(out), exist_ok=True)
S.mixdown(out, {"drums": .85, "perc": .7, "bass": .9, "pads": 1.0, "keys": 1.1, "lead": 1.2,
                "vox": 1.3 if SINGER == "robot" else 1.5, "fx": .5},
          cut_keys=cut, room=.22, echo_mix=.45, lufs=-10.0,
          ir=room.impulse_response((7.0, 5.0, 3.0), rt60=1.8) if ROOM == "sim" else None)
