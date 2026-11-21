#!/usr/bin/env python3
"""Op Een Onbewoond Eiland: a very short extra for round two (a children's choir song with comic violence, Dutch).
The words, all of them: "Op een onbewoond eiland, gaan alle kinderen dood". The melody is the one the user wrote
out as sheet music (21 November, two images), in G major.

onbewoond_eiland.py [OUT.wav]   (default renders/onbewoond-eiland_100bpm_G.wav)

Two bars of glockenspiel and piano play the first half of the tune, then a child sings the line and the song stops
on "dood". The singer: Lem the Shapeshifter DS 2.5 (DiffSinger) sings the written notes (the Dutch spelled for its
English phonemes), SoulX-Singer SVC turns it into a child's Qwen voice.
"""
import os

import dx7
import engine as e
import parts
import voice as V

TITLE = "Op Een Onbewoond Eiland"
DAY = "Round two: Kinderen voor Kinderen"
BPM, KEY = 100, "G"
PROG = ["G", "D7", "G", "D7", "C", "G"]
BARS = 7
V.CAST.setdefault("qwen_kid", "qwen:Child, a young girl about ten years old, a high, clear and sweet voice, singing a "
                              "children's song on television.#42")

e.seed(BPM)
S = e.Song(bpm=BPM, bars=BARS)
B = S.beat

dx7.PATCHES.setdefault("toy_glock", dict(algo=5, feedback=0, gain=.5, ops=[
    dx7.op(1, 0, 0, 99, (99, 32, 25, 45), (99, 70, 0, 0), vel=.5),
    dx7.op(3, 50, 0, 70, (99, 45, 25, 45), (99, 40, 0, 0), vel=.8, ks=6),
    dx7.op(4, 0, 2, 80, (99, 40, 25, 45), (99, 60, 0, 0), vel=.5),
    dx7.op(1, 0, 0, 62, (99, 60, 25, 45), (99, 30, 0, 0), vel=.9, ks=6),
    dx7.op(1, 0, -2, 0, (99, 50, 20, 50), (99, 0, 0, 0)),
    dx7.op(1, 0, 0, 0, (99, 50, 20, 50), (99, 0, 0, 0)),
]))

# the user's notes, one token a sixteenth: a quarter's pickup, then the bars as written
LINE1 = [". . . . G4 - - F#4 G4 - - F#4 G4 - - -", "A4 - - G4 A4 - - G4 . . . . . . . ."]
LINE2 = [". . . . E4 - - E4 - - - C4 C4 - - E4", "D4 - - - - - . . . . . . . . . ."]
WORDS1 = ("op een on be woond ei + land +", "op un on buh wohnt ay + lant +")
WORDS2 = ("gaan al le kin dren dood", "hahn ah luh kin drun dote")
CHORDS = {0: "G", 1: "D7", 2: "G", 3: "D7", 4: "C", 5: "G"}

P = parts.Band(S, ["G"], scale="major", diva_voice="ds:lem", timbre="qwen_kid", stack="", harmony="",
               verse_double=0.0)
P.ds_gain = 2.5


def piano(bar, amp=1.0):
    notes = e.close_voicing(CHORDS[bar], lo=55, hi=67)
    for b in range(4):
        for j, m in enumerate(notes):
            S.put("keys", S.at(bar, b) + j * .004, e.piano(m, B * .8, .5 if b % 2 else .6), .45, .28 * amp, wet=.25)


for bar, line in enumerate(LINE1):                      # the intro: the glockenspiel plays the first half
    for t, m, d in S.notes(bar, line):
        S.put("lead", t, dx7.note("toy_glock", m + 12, min(d, B), .8, tail=.6), .6, .4, wet=.3, echo=.1)
for bar in range(6):
    piano(bar, .8 if bar < 2 else 1.0)
S.put("keys", S.at(6), e.piano(43, 2.0, .7), .45, .35, wet=.3)    # the last low G under "dood"

line1, line2 = " ".join(LINE1), " ".join(LINE2)
P.diva(2, line1, WORDS1[0], bars=2, ds_words=WORDS1[1])
P.diva(4, line2, WORDS2[0], bars=2, ds_words=WORDS2[1])
P.finish()

NAME = f"onbewoond-eiland_{BPM}bpm_{KEY}"
S.mixdown(parts.out_path(NAME), {"keys": 1.0, "lead": .9, "vox": 1.5}, room=.2, echo_mix=.3, lufs=-11.0,
          tail_fade=1.5)
print(f"share.SONGS row: (\"{NAME}.wav\", \"{TITLE}\", \"{DAY}\", {BPM}, \"{KEY}\", {BARS}),")
