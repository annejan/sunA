#!/usr/bin/env python3
"""Floppy Hardcore: early rave (1991) as a ProTracker module, 4 channels, 134 BPM, A minor, samples from the
ST-XX disks. Channel 1 the break, 2 the bass, 3 the piano (arpeggio chords, 0xy), 4 orchestra hits and a shout.

floppy_hardcore.py   writes out/floppy_hardcore.mod and .mp3

Picked by ear (22 November): ST-38/break004 played at B-2 (one bar at 134 BPM), ST-01/MonsterBass.
"""
import mod

m = mod.Module("floppy hardcore")
BREAK = m.sample("ST-38/break004")
BASS = m.sample("ST-01/MonsterBass", volume=56)
# tune=True: the index (st_index.csv) plays them in tune. The M1 piano sounds F# at C-2 (v1 played every chord a
# tritone off: "rather out of tune, but funny"), the orchestra hit D; the M1 piano is an IFF 8SVX file (v1 played
# its header as sound)
PIANO = m.sample("ST-44/m1piano8'", volume=46, tune=True)
ORCH = m.sample("ST-17/orch.hit", volume=50, tune=True)
PIANO_ST, ORCH_ST = 0, 0
YEAH = m.sample("ST-20/YEAAH!", volume=58)
BEAT = 0x1B             # sample offset (9xx, 256-byte steps) of the break's second beat: 28128 B / 4 / 256

# two bars a row each: a note or "." (16 rows a bar); the bass an octave up from the token (C-1 is the floor)
BASSLINE = ("A-1 . . A-1 . . A-2 . A-1 . A-1 A-2 . A-1 G-1 . "
            "F-1 . . F-1 . . F-2 . G-1 . . G-1 . G-2 E-1 G-1").split()
# the piano riff: (row in the two bars, root, arpeggio) - Am, then F and G
RIFF = [(0, "A-2", "037"), (3, "A-2", "037"), (6, "A-2", "037"), (10, "A-2", "037"), (12, "A-2", "037"),
        (16, "F-2", "047"), (19, "F-2", "047"), (22, "F-2", "047"), (24, "G-2", "047"), (27, "G-2", "047"),
        (30, "G-2", "047")]
# the breakdown's chords, a bar each, on three channels
CHORDS = [("A-2", "C-3", "E-3"), ("F-2", "A-2", "C-3"), ("G-2", "B-2", "D-3"), ("E-2", "G#2", "B-2")]


def up(note, st=12):
    return mod.note_name(mod.note_index(note) + st)


def breakbeat(p, fill=False):
    for bar in range(4):
        p.put(bar * 16, 0, "B-2", BREAK)
    if fill:            # the last bar: the snare, every other row, then every row
        for r in list(range(48, 56, 2)) + list(range(56, 64)):
            p.put(r, 0, "B-2", BREAK, f"9{BEAT:02X}")


def bass(p):
    for r in range(64):
        tok = BASSLINE[r % 32]
        if tok != ".":
            p.put(r, 1, up(tok), BASS)


def piano(p, ch=2):
    for half in (0, 32):
        for r, root, arp in RIFF:
            p.put(half + r, ch, up(root, PIANO_ST), PIANO, "0" + arp[1:])


def orch(p, rows=(0, 32)):
    for r in rows:
        p.put(r, 3, up("A-2", ORCH_ST), ORCH)


# ---------------------------------------------------------------- the patterns (4 bars each)
INTRO = m.pattern()
breakbeat(INTRO)
INTRO.put(0, 2, None, None, "F06")
INTRO.put(0, 3, None, None, "F86")             # 134 BPM
INTRO.put(48, 3, "C-2", YEAH)

GROOVE = m.pattern()
breakbeat(GROOVE)
bass(GROOVE)

PIANO1 = m.pattern()
breakbeat(PIANO1)
bass(PIANO1)
piano(PIANO1)

FULL = m.pattern()
breakbeat(FULL)
bass(FULL)
piano(FULL)
orch(FULL)
FULL.put(16, 3, "C-2", YEAH)

FULL_FILL = m.pattern()
breakbeat(FULL_FILL, fill=True)
bass(FULL_FILL)
piano(FULL_FILL)
orch(FULL_FILL, rows=(0,))

DOWN = m.pattern()                              # the breakdown: no break, no bass, the chord on three channels
for bar, chord in enumerate(CHORDS):
    for ch, n in zip((1, 2, 3), chord):
        DOWN.put(bar * 16, ch, up(n, PIANO_ST - 12), PIANO)        # an octave under the riff: warmer
DOWN.put(0, 0, up("A-2", ORCH_ST), ORCH)

BUILD = m.pattern()                             # the piano riff alone, the break comes back chopped
piano(BUILD)
for r in list(range(32, 48, 4)) + list(range(48, 56, 2)) + list(range(56, 64)):    # quarters, eighths, sixteenths
    BUILD.put(r, 0, "B-2", BREAK, f"9{BEAT:02X}")
BUILD.put(60, 3, "C-2", YEAH)

m.order = [INTRO.index, GROOVE.index, GROOVE.index, PIANO1.index, PIANO1.index, FULL.index, FULL_FILL.index,
           DOWN.index, DOWN.index, BUILD.index, FULL.index, FULL_FILL.index, FULL.index, PIANO1.index,
           GROOVE.index, INTRO.index]

if __name__ == "__main__":
    m.write("out/floppy_hardcore.mod")
    print(mod.render("out/floppy_hardcore.mod", "out/floppy_hardcore.mp3"))
