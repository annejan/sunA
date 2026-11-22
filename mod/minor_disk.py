#!/usr/bin/env python3
"""Minor Disk: an Amiga demo tune in A minor, 125 BPM, 4 channels, samples from the ST-XX disks picked with the
index (st_index.py) and played in tune (tune=True). Channel 1 the drums (kick, snare and hi-hat on one channel, the
old way), 2 the bass, 3 the chords as arpeggios (0xy), 4 the lead with vibrato (4xy).

minor_disk.py   writes out/minor_disk.mod and .mp3

Am F C G | Am F G E, a chord a bar, and a B part (Dm Am F G | Dm Am E E) with its own melody. Intro (chords and
hi-hats), the bass joins, the theme, the B part, a breakdown without drums, the theme and the B part again, the
theme with its first half an octave up, and a last chord. A snare fill ends every eight bars.
"""
import mod

m = mod.Module("minor disk")
KICK = m.sample("ST-33/bassdrum34", volume=64)
SNARE = m.sample("ST-60/stand.snare", volume=60)
HAT = m.sample("ST-03/thehihatclosed", volume=40)
BASS = m.sample("ST-22/Pirates-bass", volume=60, tune=True)
CHORD = m.sample("ST-B0/polystring", volume=34, tune=True, loop="auto")
LEAD = m.sample("ST-94/lead.korg31", volume=50, tune=True, loop="auto")
# the same lead an octave up (every other byte: ProTracker's notes end at B-3, the old trick)
LEAD_HI = m.sample(LEAD.data[::2].copy(), volume=46, name="lead.korg31 hi",
                   loop=(LEAD.loop[0] // 2 // 2 * 2, LEAD.loop[1] // 2 // 2 * 2) if LEAD.loop else None)
LEAD_HI.st, LEAD_HI.finetune = LEAD.st, LEAD.finetune

# a chord a bar: (root for the bass, root for the arpeggio, arpeggio effect)
CHORDS = [("A-1", "A-2", "037"), ("F-1", "F-2", "047"), ("C-2", "C-3", "047"), ("G-1", "G-2", "047"),
          ("A-1", "A-2", "037"), ("F-1", "F-2", "047"), ("G-1", "G-2", "047"), ("E-1", "E-2", "047")]
# the lead: per bar, (row, note, effect); a note rings until the next one, 4xy is vibrato on a held note
MELODY = [
    [(0, "A-2", None), (4, "C-3", None), (6, "E-3", None), (8, "D-3", None), (12, "C-3", None), (14, "B-2", None)],
    [(0, "C-3", None), (4, None, "446"), (12, "A-2", None), (14, "C-3", None)],
    [(0, "E-3", None), (4, "D-3", None), (6, "C-3", None), (8, "G-2", None), (10, None, "446"), (14, "C-3", None)],
    [(0, "D-3", None), (4, None, "446"), (8, "B-2", None), (12, "D-3", None), (14, "C-3", None)],
    [(0, "E-3", None), (2, "E-3", None), (4, "D-3", None), (6, "E-3", None), (8, "C-3", None), (12, "B-2", None)],
    [(0, "A-2", None), (4, None, "446"), (8, "F-2", None), (12, "A-2", None), (14, "C-3", None)],
    [(0, "B-2", None), (4, "D-3", None), (6, "G-2", None), (8, "B-2", None), (12, "D-3", None)],
    [(0, "E-3", None), (4, None, "448"), (8, "G#2", None), (12, "B-2", None), (14, "G#2", None)],
]

# the B part (the user: "after 1:32 it gets very monotonous"): new chords and a new melody
B_CHORDS = [("D-1", "D-2", "037"), ("A-1", "A-2", "037"), ("F-1", "F-2", "047"), ("G-1", "G-2", "047"),
            ("D-1", "D-2", "037"), ("A-1", "A-2", "037"), ("E-1", "E-2", "047"), ("E-1", "E-2", "047")]
B_MELODY = [
    [(0, "F-3", None), (4, "E-3", None), (6, "D-3", None), (8, "A-2", None), (10, None, "446")],
    [(0, "C-3", None), (4, "B-2", None), (6, "A-2", None), (8, "E-3", None), (10, None, "446")],
    [(0, "F-3", None), (2, "E-3", None), (4, "F-3", None), (6, "G-3", None), (8, "A-3", None), (10, None, "446")],
    [(0, "G-3", None), (4, "F-3", None), (6, "E-3", None), (8, "D-3", None), (12, "B-2", None)],
    [(0, "D-3", None), (4, "F-3", None), (6, "A-3", None), (8, "G-3", None), (12, "F-3", None)],
    [(0, "E-3", None), (4, None, "446"), (8, "C-3", None), (12, "E-3", None)],
    [(0, "B-2", None), (4, "E-3", None), (6, "G#2", None), (8, "B-2", None), (10, None, "446")],
    [(0, "E-3", None), (4, None, "448"), (12, "D-3", None), (14, "B-2", None)],
]


def drums(p, bar, full=True):
    r0 = bar * 16
    for k in range(0, 16, 2):
        if full and k in (0, 6, 10):
            p.put(r0 + k, 0, "C-2", KICK)
        elif full and k in (4, 12):
            p.put(r0 + k, 0, "C-2", SNARE)
        else:
            p.put(r0 + k, 0, "C-3", HAT)


def fill(p, bar):
    """The last half bar: the snare on every row, louder each time."""
    r0 = bar * 16
    for k in range(8, 16):
        p.put(r0 + k, 0, "C-2", SNARE, f"C{24 + 5 * (k - 8):02X}")


def bass(p, bar, root):
    r0 = bar * 16
    for k in range(0, 16, 2):
        n = root if k % 4 == 0 else mod.note_name(mod.note_index(root) + 12)
        p.put(r0 + k, 1, n, BASS)


def chords(p, bar, root, arp, held=False):
    r0 = bar * 16
    if held:                                            # the breakdown: one long chord a bar
        p.put(r0, 2, root, CHORD, arp)
        for k in range(1, 16):
            p.put(r0 + k, 2, None, None, arp)           # the arpeggio keeps cycling
        return
    hits = (0, 3, 6, 8, 11, 14)
    for k in range(16):                                 # the arpeggio on every row: it lasts one row
        p.put(r0 + k, 2, root if k in hits else None, CHORD if k in hits else None, arp)


def lead(p, bar, cycle_bar, melody=None, up=False):
    r0 = bar * 16
    smp = LEAD_HI if up else LEAD
    for k, note, eff in (melody or MELODY)[cycle_bar]:
        p.put(r0 + k, 3, note, smp if note else None, eff)


def section(half, drum=True, full=True, with_bass=True, with_lead=False, held=False, prog=None, melody=None,
            up=False, fills=False):
    """One pattern: bars 0-3 (half 0) or 4-7 (half 1) of a progression (CHORDS, or B_CHORDS with B_MELODY).
    up: the lead an octave higher; fills: a snare fill in the pattern's last bar."""
    p = m.pattern()
    for bar in range(4):
        cb = half * 4 + bar
        broot, aroot, arp = (prog or CHORDS)[cb]
        if drum:
            drums(p, bar, full)
        if with_bass:
            bass(p, bar, broot)
        chords(p, bar, aroot, "0" + arp[1:], held)
        if with_lead:
            lead(p, bar, cb, melody, up)
    if fills and drum:
        fill(p, 3)
    if not with_lead:      # the lead's sample loops: without this its last note rang on (v1 from 1:32, "a tone hangs")
        p.put(1, 3, None, None, "C00")
    return p


def ending():
    """The last chord: everything on A, ringing for two bars, then the song ends (Dxx: the next pattern; there is
    none)."""
    p = m.pattern()
    p.put(0, 0, "C-2", KICK)
    p.put(0, 1, "A-1", BASS)
    p.put(0, 2, "A-2", CHORD, "037")
    for k in range(1, 32):
        p.put(k, 2, None, None, "037")
    p.put(0, 3, "A-2", LEAD)
    p.put(8, 3, None, None, "446")
    p.put(31, 0, None, None, "D00")
    return p


INTRO = [section(h, full=False, with_bass=False) for h in (0, 1)]
INTRO[0].put(0, 1, None, None, "F06")
INTRO[0].put(0, 3, None, None, "F7D")                   # 125 BPM
GROOVE = [section(h, fills=h == 1) for h in (0, 1)]
THEME = [section(h, with_lead=True, fills=h == 1) for h in (0, 1)]
BPART = [section(h, with_lead=True, prog=B_CHORDS, melody=B_MELODY, fills=h == 1) for h in (0, 1)]
DOWN = [section(h, drum=False, with_bass=False, with_lead=True, held=True) for h in (0, 1)]
HIGH = [section(h, with_lead=True, up=h == 0, fills=h == 1) for h in (0, 1)]

order = INTRO + GROOVE + THEME + BPART + DOWN + THEME + BPART + HIGH + [ending()]
m.order = [p.index for p in order]

if __name__ == "__main__":
    m.write("out/minor_disk.mod")
    print(mod.render("out/minor_disk.mod", "out/minor_disk.mp3"))
