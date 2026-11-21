#!/usr/bin/env python3
"""The Rhythm Of The Badge: eurodance, 134 BPM, E minor (and F# minor after the key change). Sunday's theme of the
AI slop music compo.

rhythm_of_the_badge.py [OUT.wav]   (default renders/rhythm-of-the-badge_134bpm_Em.wav)

Every note and every sound here is written by Claude, in this file: no samples, no loops. A dark, Italo-style
night club in 1995, in a tent at a hacker camp: a 909 kick, a big reverb snare, a rolling offbeat bass, a dark
hoover (detuned PWM saws that scoop in and dive down, through a chorus), a minor-key DX7 piano, lasers, a
dramatic diva who sings to the badge round her neck, and a deep-voiced MC who raps the upload procedure.
The key change is two semitones up, for the last chorus. The first and last 16 bars are drums only, for the DJ.

  bars   0-15  intro: kick, hats, then the big snare (drums only)
        16-23  the hoover riff, behind a filter that opens; the rolling bass comes in; lasers
        24-31  verse: the piano and the pad; "round my neck you're glowing"
        32-39  chorus: "feel the rhythm of the badge ... flash me, flash me, one more time"
        40-47  the hoover riff again, with the piano
        48-55  rap: "plug it in, U S B, let the firmware flow"
        56-63  chorus
        64-71  break: no kick; the piano alone, "flash me" in the echo, and a safety notice from the MC
        72-79  build: a snare roll and a riser while the MC reads out the upload progress
        80-95  the last chorus, twice, a tone up, with the whole choir
        96-103 the hoover riff, the lasers, "feel the rhythm of the badge" twice more
       104-119 outro: drums only

The diva is sung on our own notes by Lem the Shapeshifter DS 2.5 (DiffSinger, voice Civet), converted into the
Qwen diva voice (SoulX-Singer SVC), with doubles from two more takes in two more voices, an octave and a vocoder
(DS_* below; the user's pick, 20 November). The MC is Piper's en_GB-alan-medium pitched down with WORLD (voice.py);
the chorus stacks Piper voices around the diva (CHOIR below). DIVA=en_US-amy-medium: the old Piper diva.
The reverb is a simulated big dark club (room.py).
"""
import functools
import os
import sys

import numpy as np

import engine as e
import parts
import dx7
import room
import voice as V

e.seed(1995)
SR = e.SR
S = e.Song(bpm=134, bars=120)
STEP = S.step
B = S.beat

DIVA = os.environ.get("DIVA", "ds:lem")
RAPPER = os.environ.get("RAPPER", "en_GB-alan-medium")      # the user kept Piper over a Maya and a Qwen MC (21 November, an ABC)
# the deep-voiced MC of the song's idea, a Maya voice of our own (RAPPER=maya_mc_deep; maya_hype and qwen_hype are
# the cast's rave MCs). A Maya or Qwen MC speaks at its own pace and is squeezed only when a line runs long
V.CAST.setdefault("maya_mc_deep", "maya:Realistic male voice in the 30s age with a american accent. Low pitch, deep "
                                  "timbre, moderate pacing, excited tone delivery at high intensity, entertainment "
                                  "domain, event_host role, confident delivery. A deep-voiced eurodance rap MC.#301")
V.CAST.setdefault("qwen_mc_deep", "qwen:Male, adult, deep low-pitched voice. A confident 90s eurodance rap MC, "
                                  "punchy and rhythmic, every word clear, riding the beat.#301")
# CROWD=1 (19 November, an A/B; research/toolkit-2026-11-19.md): crowd moments. The title in the echo while the riff
# comes in (the first title came 28 s after the music); the band stops for the bar before the last chorus
# ("Everybody!"); in the second pass of the last chorus the diva leaves the first line to the room ("Sing it!", 16
# voices of a many-speaker Piper model over the piano's tune); a punchline before the drums-only outro.
CROWD = os.environ.get("CROWD") == "1"
ROOM = [f"en_US-libritts_r-medium#{k}" for k in (3, 17, 41, 58, 102, 140, 199, 237, 301, 355, 412, 480, 533, 610,
                                                  702, 851)]
# the choir: left double, right double, a third above; in the last chorus also a man an octave down, and one
# more voice a sixth down
CHOIR = os.environ.get("CHOIR", ",".join([
    "en_GB-jenny_dioco-medium", "en_US-lessac-high", "en_GB-cori-high",
    "en_US-norman-medium", "en_US-kristin-medium"])).split(",")

VERSE_PROG = ["Em", "C", "Am", "B"]      # i - VI - iv - V: the dark one, with the harmonic minor's D#
CHORUS_PROG = ["Em", "C", "G", "D"]      # i - VI - III - VII: the big one


def is_chorus(bar):
    return 32 <= bar < 40 or 56 <= bar < 64 or 80 <= bar < 96


def key_of(bar):
    """Two semitones up from the last chorus on: E minor becomes F# minor (the B major before it leads there)."""
    return 2 if 80 <= bar < 104 else 0


def chord_of(bar):
    return (CHORUS_PROG if is_chorus(bar) else VERSE_PROG)[bar % 4]


# ---------------------------------------------------------------- the hoover
def chorus_fx(x, depth=.0025, base=.009, rates=(.7, .9)):
    """A stereo chorus for a mono signal: two delay lines that wobble, one left and one right, mixed with the dry."""
    n = len(x)
    i = np.arange(n)
    out = np.zeros((n, 2))
    for ch, (rate, ph) in enumerate(zip(rates, (0, 1.7))):
        d = (base + depth * np.sin(2 * np.pi * rate * i / SR + ph)) * SR
        out[:, ch] = .6 * x + .55 * np.interp(i - d, i, x, left=0)
    return out


def pwm_saw(f, t, rate=5.0, depth=.18):
    """The Alpha Juno trick: a saw minus a copy of itself whose phase offset wobbles (the "pulse width"). It cuts
    moving holes in the spectrum and sounds an octave doubled. The copy's offset moves by running it a little
    faster or slower than the first saw."""
    duty = .5 + depth * np.sin(2 * np.pi * rate * t + e.rng.uniform(0, 6.3))
    p0 = e.rng.random()
    s1 = e.saw(f, t, p0)
    f2 = np.asarray(f, float) + np.diff(duty, prepend=duty[0]) * SR
    s2 = e.saw(f2, t, (p0 + duty[0]) % 1.0)
    return s1 - .7 * s2


@functools.lru_cache(maxsize=1024)
def _hoover(m, n, dive, cut):
    d = n / SR
    r = .35 if dive else .08
    t = e.tt(d + r)
    # the pitch: a scoop up from a fifth below at the start; with dive, a fall of an octave after the key lets go
    bend = -7 * np.exp(-t / .045)
    if dive:
        bend = bend - 12 * np.clip((t - d) / r, 0, 1) ** 1.5
    g = np.zeros(len(t))
    # three saws on the note, two an octave up, one an octave down; all a little out of tune with each other
    for det, octave, a in ((-.12, 0, 1.0), (.11, 0, 1.0), (0, 0, .8), (-.06, 12, .55), (.07, 12, .55), (0, -12, .3)):
        g += a * pwm_saw(e.hz(m + octave + det + bend), t, rate=4.3 + 1.7 * e.rng.random())
    g = e.lowpass(e.lowpass(g, cut), cut * 1.6)       # dark: four poles, nothing shrill on top
    y = chorus_fx(g * e.rise(t, .006) * e.gate(t, d, r / 2.5) / 4.0)
    y.flags.writeable = False
    return y


def hoover(m, d, dive=False, cut=2600):
    """Stereo: the hoover, one note of d seconds (cached per note, length and cutoff)."""
    return _hoover(int(m), int(d * SR), bool(dive), int(cut)).copy()


# the riff, one bar: (sixteenth, length in sixteenths, semitones above the chord's root); the 3-3-2 of the 90s
RIFF = [(0, 3, 0), (3, 3, 0), (6, 2, 12), (8, 3, 0), (11, 3, 7), (14, 2, 12)]


def hoover_riff(bar, amp=1.0, cut=2600):
    root = e.root_note(chord_of(bar), key_of(bar), lo=47)
    for k, n, iv in RIFF:
        dive = bar % 2 == 1 and k == 14          # every other bar the last note dives an octave
        S.put("lead", S.at(bar) + k * STEP, hoover(root + iv, n * STEP * .92, dive, cut), amp=.5 * amp,
              wet=.25, echo=.1 if dive else 0)


# ---------------------------------------------------------------- the minor-key piano (DX7)
# a bright house piano on the DX7 (dx7.py): three pairs of operators, a hammer on operator 4 (ratio 3), and keyboard
# scaling on the modulators so the top notes go darker instead of shrill
dx7.PATCHES["badgepiano"] = dict(algo=5, feedback=0, gain=1.6, ops=[
    dx7.op(1, 0, 0, 99, (99, 30, 22, 55), (99, 75, 0, 0), vel=.3),
    dx7.op(1, 0, 0, 78, (99, 35, 25, 60), (99, 60, 0, 0), vel=.8, ks=6),
    dx7.op(1, 0, 2, 95, (99, 28, 20, 55), (99, 75, 0, 0), vel=.3),
    dx7.op(3, 0, 0, 66, (99, 55, 30, 60), (99, 40, 0, 0), vel=1.0, ks=9),
    dx7.op(2, 0, -2, 80, (99, 32, 22, 55), (99, 70, 0, 0), vel=.4),
    dx7.op(1, 0, 0, 70, (99, 45, 25, 60), (99, 50, 0, 0), vel=.7, ks=8),
])


def pno(m, d, vel=.8):
    return dx7.note("badgepiano", m, d, vel, tail=.6)


STABS = [(0, 3, .9), (3, 3, .7), (6, 4, .8), (10, 2, .6), (12, 4, .75)]   # sixteenth, length, velocity


def piano(bar, amp=1.0):
    notes = e.close_voicing(chord_of(bar), key_of(bar), lo=59, hi=74)
    for k, n, vel in STABS:
        for j, m in enumerate(notes):
            S.put("keys", S.at(bar) + k * STEP + j * .004, pno(m, n * STEP, vel), .35 + .15 * j, .32 * amp,
                  wet=.3, echo=.06)


def piano_arp(bar, amp=1.0):
    """The break: the chord broken up in eighths, up and down, the bass note on the downbeat."""
    notes = e.close_voicing(chord_of(bar), key_of(bar), lo=59, hi=79)
    order = [0, 1, 2, 3, 2, 1, 2, 3]
    S.put("keys", S.at(bar), pno(e.root_note(chord_of(bar), key_of(bar), lo=40) + 12, S.bar, .7), .5, .35 * amp,
          wet=.4)
    for i, j in enumerate(order):
        m = notes[min(j, len(notes) - 1)]
        S.put("keys", S.at(bar) + i * 2 * STEP, pno(m, 2 * STEP, .55 + .1 * (i % 2 == 0)), .3 + .4 * (i % 2), .3 * amp,
              wet=.45, echo=.2)


def pads(bar, amp=1.0, cut=1800):
    notes = e.voicing(chord_of(bar), key_of(bar), lo=52)
    S.put("pads", S.at(bar), e.pad(notes, S.bar, cut=cut, a=.25, r=.6), amp=.45 * amp, wet=.45)


def orch(bar, amp=1.0):
    S.put("fx", S.at(bar), e.orch_hit(e.close_voicing(chord_of(bar), key_of(bar), lo=55, hi=70), amp), wet=.5)


# ---------------------------------------------------------------- drums
def big_snare(a=1.0):
    """The big snare: a 909-ish snare and a clap, with a long dark tail of noise (a 1980s gated plate, faked)."""
    t = e.tt(.7)
    tail = e.lowpass(e.highpass(e.rng.standard_normal(len(t)), 400), 5000) * np.exp(-t * 6) * .35
    tail *= e.rise(t, .012)
    g = e.snare(.6)[:len(t)]
    out = tail.copy()
    out[:len(g)] += g
    c = e.clap(.4)
    out[:len(c)] += c
    return out * a


def drums(bar, kick=True, snare=True, hats=True, open_hats=True, crash=False, amp=1.0):
    t0 = S.at(bar)
    if kick:
        for b in range(4):
            # the 909: a long pitch sweep down to about E1, a soft click
            S.kick(t0 + b * B, 1.0 * amp, punch=160, base=44, length=.4, click=.3)
    if snare:
        for b in (1, 3):
            S.put("drums", t0 + b * B, big_snare(.7 * amp), .5, wet=.55)
    if hats:
        for k in range(16):
            if k % 4 == 2 and open_hats:
                S.put("perc", t0 + k * STEP, e.hat(.55 * amp, opened=True), .58, wet=.1)
            elif k % 4 != 2:
                S.put("perc", t0 + k * STEP, e.hat((.3 if k % 2 else .16) * amp), .64, wet=.05)
    if crash:
        S.put("perc", t0, e.crash(.7), .5, wet=.35)


def snare_roll(bar0, bars=4, amp=1.0):
    """Sixteenths, climbing, and thirty-seconds in the last bar."""
    total = bars * 16
    for k in range(total):
        u = k / total
        t = S.at(bar0) + k * STEP
        S.put("drums", t, e.snare((.12 + .6 * u ** 1.5) * amp), .5, wet=.35)
        if k >= total - 16:
            S.put("drums", t + STEP / 2, e.snare((.12 + .6 * u ** 1.5) * amp * .8), .5, wet=.35)


# ---------------------------------------------------------------- the rolling bass
def bass(bar, amp=1.0):
    """Three sixteenths after every kick: a ghost, the offbeat (the loud one) and the octave. An FM growl (the
    DX7 bass) on top of a saw and a sub."""
    root = e.root_note(chord_of(bar), key_of(bar), lo=28)
    for b in range(4):
        for k, iv, a in ((1, 0, .35), (2, 0, 1.0), (3, 12, .55)):
            t = S.at(bar) + (4 * b + k) * STEP
            S.put("bass", t, e.bass_note(root + iv, STEP * .85, cut=900, decay=4), .5, .85 * amp * a, wet=0)
            S.put("bass", t, dx7.note("bass", root + iv + 12, STEP * .7, .5 + .4 * a, tail=.05), .5, .3 * amp * a,
                  wet=0)


# ---------------------------------------------------------------- lasers
def laser(a=1.0, f0=2600, f1=180, d=.28):
    """Pew: a soft-clipped sine falling fast from f0 to f1."""
    t = e.tt(d)
    f = f1 + (f0 - f1) * np.exp(-t / (d / 5))
    ph = np.cumsum(f) / SR
    g = np.tanh(2.5 * np.sin(2 * np.pi * ph)) * .7 + .3 * np.sin(4 * np.pi * ph)
    return e.lowpass(g, 5000) * e.rise(t, .002) * np.exp(-t * 7) * a


def lasers(bar, steps=(14,), amp=1.0):
    for i, k in enumerate(steps):
        S.put("fx", S.at(bar) + k * STEP, laser(.35 * amp, 2600 - 500 * (i % 2), 180 + 60 * i), .25 + .5 * (i % 2),
              wet=.3, echo=.35)


# ---------------------------------------------------------------- the words and the tunes
# a line is a tune on an even grid ("-" holds, "." rests) and its words; a word with "+" after it is sung over
# that many more notes. The tunes are written an octave above where the diva sings them.
VERSE = [
    (". B4 B4 B4 A4 - B4 - G4 - - - - - . .", "round my neck you're glowing +"),
    (". A4 A4 A4 G4 - A4 - F#4 - - - - - . .", "in the dark you're showing +"),
    (". B4 B4 D5 - B4 - A4 G4 - - E4 - - - .", "every + pixel + calling + me"),
    (". A4 B4 C5 - B4 A4 G4 - A4 - - - B4 - -", "into + the ee lek trih sih tee"),
]
CHORUS = [
    ("E5 - D5 B4 - B4 A4 G4 B4 - - - - - . .", "feel the rhythm + of the badge"),
    ("E5 - D5 B4 - B4 A4 G4 A4 - - - - - . .", "feel the rhythm + of the badge"),
    ("E5 D5 - . E5 D5 - . B4 - D5 - E5 - - -", "flash me flash me one more time"),
    ("E5 - D5 B4 - B4 A4 G4 F#4 - - - - - . .", "feel the rhythm + of the badge"),
]
# the MC: half a line a bar, so the words come out stiff and on the beat
RAP = ["Plug it in, U S B,", "let the firm ware flow!",
       "From the C six to the P four,", "here we go!",
       "Badgelink, app store,", "upload complete.",
       "Now the whole tent is moving", "to the beat!"]
SAFETY = ["Warning. That is the C six.", "Do not flash the C six."]
PROGRESS = ["Uploading.", "Fifty percent.", "Ninety nine percent.", "Upload complete!"]


def third_above(m, key):
    """The note two steps up the (natural minor) scale of the key: a diatonic third."""
    scale = sorted((pc + 4 + key) % 12 for pc in (0, 2, 3, 5, 7, 8, 10))
    for up in (3, 4):
        if (m + up) % 12 in scale:
            return m + up
    return m + 3


def words_on(notes, words):
    """Pair words with notes: a word takes its note and one more for each "+" after it (sung as one word)."""
    out, toks, i = [], words.split(), 0
    for k, w in enumerate(toks):
        if w == "+":
            continue
        span = 1
        while k + span < len(toks) and toks[k + span] == "+":
            span += 1
        out.append((w, notes[i:i + span]))
        i += span
    assert i == len(notes), (words, len(notes))
    return out


# DIVA=ds:lem (DIVA=ds:hanami for Segfault's singer): a DiffSinger voicebank sings the diva's part (ds.py) at the written pitch, in one take; the
# Piper choir stays below her. The words as written for it (real words; "+" holds a word over the next note)
DS = DIVA.startswith("ds:")
DS_GAIN = []                 # (from, to, amp, last word at, its echo) per line
DS_TEXT = {"into + the ee lek trih sih tee": "into + the electricity + + + +"}
# Lines rewritten for a real singer: "flash" on an eighth (224 ms; the line spans 2 bars) came out "fs me" or "fish
# me"; on a quarter it says "flash" (the user's pick of five, 20 November). Even quarters had no punch: the rests
# after "me" and short "one, more" give it back, with "flash" 4 dB up (DS_ACCENT; the user's pick of four)
DS_LINE = {"flash me flash me one more time": "E5 - D5 . E5 - D5 . B4 . D5 . E5 - - -"}
# DS_FLASH (a test switch): another rhythm for that line ("E5 - D5 - E5 - D5 - B4 - D5 - E5 - - -": even quarters)
if os.environ.get("DS_FLASH"):
    DS_LINE["flash me flash me one more time"] = os.environ["DS_FLASH"]
DS_ACCENT = []               # (from, to) of each sung "flash"
# the production (the user's pick of four, 20 November): Lem's Civet sings, the Qwen diva's voice; doubles from takes
# 2 and 3 in the Qwen pop and Maya pop voices, a soft octave above, a vocoder on the chords. DS_STACK= (empty): the
# lead alone; DS_TIMBRE= (empty): Lem's own voice. Only for Lem: Hanami's terms forbid conversion
LEM = DIVA == "ds:lem"
DS_VOICE = os.environ.get("DS_VOICE", "Civet" if LEM else "Fragrance")
DS_TIMBRE = os.environ.get("DS_TIMBRE", "qwen_diva" if LEM else "") or None
DS_STACK = os.environ.get("DS_STACK", "sing_qwen_pop,sing_maya_pop,octave,vocoder" if LEM else "")
if DS:
    import ds
    DS_PART = ds.Part(S.bpm)


def diva(bar, line, words, bars=2, amp=1.0, choir=0.0, big=False, key=None, echo_last=.35, pan=.5):
    """The diva sings a line, a word on its notes, the consonants before the beat, an echo on the last word.
    choir: how loud the other voices are (left and right doubles and a third above; with big=True also a man an
    octave down and a voice a sixth down)."""
    key = key_of(bar) if key is None else key
    pairs = words_on(S.notes(bar, line, key, bars), words)
    if DS:
        ds_pairs = words_on(S.notes(bar, DS_LINE.get(words, line), key, bars), DS_TEXT.get(words, words))
        for w, ns in ds_pairs:
            for k, (t, m, d) in enumerate(ns):
                DS_PART.note(t, m, d * .97, w if k == 0 else "+")
            if w == "flash":
                DS_ACCENT.append((ns[0][0] - .06, ns[-1][0] + ns[-1][2]))
        DS_GAIN.append((S.at(bar), S.at(bar + bars), amp, ds_pairs[-1][1][0][0], echo_last))
    for i, (w, ns) in enumerate(pairs):
        last = i == len(pairs) - 1
        t = ns[0][0]
        if not DS:
            li, y = V.sing(w, [(m - 12, d * .97) for _, m, d in ns], voice=DIVA)
            S.put("vox", t - li, y, pan, amp, wet=.18, echo=echo_last if last else .05)
        if not choir:
            continue
        notes = [(m - 12, d * .95) for _, m, d in ns]
        third = [(third_above(m, key) - 12, d * .95) for _, m, d in ns]
        parts = [(CHOIR[0], notes, 8, .018, .15, .7), (CHOIR[1], notes, -8, .009, .85, .7),
                 (CHOIR[2], third, 0, .006, .45, .55)]
        if big:
            parts += [(CHOIR[3], [(n - 12, d) for n, d in notes], 0, .012, .55, .6),
                      (CHOIR[4], [(n - 12, d) for n, d in third], 5, .015, .7, .4)]
        for v, ns2, cents, late, p, g in parts:
            # vowels only, in a straighter tone: the diva sings the words (see voice.sing)
            _, y = V.sing(w, ns2, voice=v, cents=cents, vibrato=.15, vowel_only=True)
            S.put("vox", t + late, y, p, amp * choir * g, wet=.2, echo=.05)


def chorus_lines(bar0, big=False, gap=False):
    """The chorus, 8 bars: four lines of two; the piano doubles the tune an octave above the voice, lasers answer
    "flash me". gap: the first line is the room's (CROWD)."""
    for i, (line, words) in enumerate(CHORUS):
        bar = bar0 + 2 * i
        if gap and i == 0:
            room_shout(bar, "Feel the rhythm of the badge!")
        else:
            diva(bar, line, words, choir=.45, big=big)
        for t, m, d in S.notes(bar, line, key_of(bar), bars=2):
            S.put("keys", t, pno(m, d * .9, .7), .5, .2, wet=.3, echo=.15)
        if i == 2:
            lasers(bar, steps=(6, 14))
            lasers(bar + 1, steps=(14,), amp=.7)


def room_shout(bar, text, bars=2, amp=1.0):
    """The room shouts a line: the ROOM voices, each fitted to the bars, a little apart in time and pitch, spread
    left to right."""
    if not S.live(bar, bars):
        return
    for i, v in enumerate(ROOM):
        y = V.rap(text, bars * S.bar - STEP, voice=v, pitch=.9 + .015 * (i % 8))
        S.put("vox", S.at(bar) + .006 * (i % 5), y, .15 + .7 * i / (len(ROOM) - 1), amp * .3, wet=.25, echo=.05)


MC_TAKES = int(os.environ.get("MC_TAKES", "4"))
MC_PICKS = []                # (bar, line, (seed, score, heard)) of the Maya or Qwen MC's picked takes


def mc(bar, text, bars=1, amp=1.0, wet=.06, echo=.04):
    """A rap line from the downbeat, fitted to the bars (a sixteenth short, to breathe); deep and flat. A Maya or
    Qwen MC (a CAST name) says it at its own pace, in its own words ("U S B" as "USB"), squeezed only when longer."""
    if not S.live(bar, bars):
        return
    if RAPPER.startswith("en_"):           # a Piper voice, pitched down
        y = V.rap(text, bars * S.bar - STEP, voice=RAPPER, pitch=.84)
    else:
        said = text.replace("U S B", "USB").replace("firm ware", "firmware")
        tag = "<excited> " if V.CAST.get(RAPPER, RAPPER).startswith("maya:") else ""
        # the producer: three directions (as written; punched, every comma a shout; told to rap on the beat), each
        # MC_TAKES takes (seeds); the take Whisper hears best that fills the bars without a squeeze, lively
        punched = said.replace(",", "!").replace(".", "!")
        directions = [(tag, said, ""), (tag, punched, ""),
                      (tag, said, "Rapping on the beat, punchy and rhythmic, every word clear and confident.")]
        y, rows = V.best_take(said, RAPPER, bars * S.bar - STEP, seeds=range(301, 301 + MC_TAKES),
                              directions=directions)
        MC_PICKS.append((bar, said, rows[0]))
        if len(y) > (bars * S.bar - STEP) * e.SR:
            y = V.rap(said, bars * S.bar - STEP, voice=RAPPER, pitch=1.0)
        y = y * (.14 / (np.sqrt(np.mean(y ** 2)) + 1e-9))
    S.put("vox", S.at(bar), y, .5, amp, wet=wet, echo=echo)


# ---------------------------------------------------------------- the arrangement
for bar in range(120):
    if CROWD and bar == 79:                     # the band stops for one bar: only the MC
        if S.live(bar):
            y = V.rap("Everybody!", S.bar / 2, voice=RAPPER, pitch=.84)
            S.put("vox", S.at(bar, 1), y, .5, 1.15, wet=.25, echo=.35)
        continue
    intro, outro = bar < 16, bar >= 104
    chorus = is_chorus(bar)
    riff = 16 <= bar < 24 or 40 <= bar < 48 or 96 <= bar < 104
    verse = 24 <= bar < 32
    rap = 48 <= bar < 56
    brk = 64 <= bar < 72
    build = 72 <= bar < 80

    if intro:
        drums(bar, snare=bar >= 8, open_hats=bar >= 4, crash=bar == 0)
    elif outro:
        drums(bar, snare=bar < 112, open_hats=bar < 116, crash=bar == 104)
    elif brk:
        drums(bar, kick=False, snare=bar % 4 == 3, hats=bar >= 68, open_hats=False, amp=.7)
    elif build:
        drums(bar, kick=bar < 76, snare=False, open_hats=False, amp=.9)
    else:
        drums(bar, crash=bar in (16, 24, 32, 40, 48, 56, 80, 88, 96))

    if 16 <= bar < 104 and not (brk or build):
        bass(bar, .7 if bar < 20 else 1.0)
    if build and bar < 76:
        bass(bar, .6)

    if 16 <= bar < 24:
        hoover_riff(bar, .9, cut=500 * 1.25 ** (bar - 16))    # the filter opens, bar by bar
    elif riff:
        hoover_riff(bar)
    elif chorus:
        hoover_riff(bar, .55, cut=1800)
    elif rap:
        hoover_riff(bar, .45, cut=1400)
    elif build:
        hoover_riff(bar, .7, cut=900 + 300 * (bar - 72))

    if verse or chorus or rap or 40 <= bar < 48:
        piano(bar, .8 if chorus else 1.0)
    if brk:
        piano_arp(bar, 1.1)
    if 24 <= bar < 104 and not riff:
        pads(bar, 1.3 if brk or build else 1.0, cut=2200 if brk else 1800)

    if bar in (16, 32, 56, 80, 88):
        orch(bar)
    if riff and bar % 4 == 3:
        lasers(bar, steps=(10, 14))
    if riff and bar % 8 == 7:
        lasers(bar, steps=(4, 6))

    # the voices
    if verse and bar % 2 == 0:
        diva(bar, *VERSE[(bar - 24) // 2], amp=.9)
    if bar in (32, 56, 80, 88):
        chorus_lines(bar, big=bar >= 80, gap=CROWD and bar == 88)
    if CROWD and bar == 87 and S.live(bar):     # the call before the room's line
        y = V.rap("Sing it!", S.bar / 2, voice=RAPPER, pitch=.84)
        S.put("vox", S.at(bar, 2), y, .5, 1.1, wet=.15, echo=.3)
    if CROWD and bar in (20, 22):               # the title early, in the echo, while the riff comes in
        diva(bar, *CHORUS[0], amp=.55, echo_last=.7)
    if CROWD and bar == 102:                    # the punchline, before the drums-only outro
        mc(bar, "Badge updated. Please reboot the dance floor.", bars=2, amp=1.0, wet=.15, echo=.2)
    if rap:
        mc(bar, RAP[bar - 48])
    if bar in (64, 68):                         # the break: "flash me, flash me" alone, in the echo
        line, words = CHORUS[2]
        diva(bar, line, words, amp=.9, echo_last=.6)
    if bar in (66, 70):
        mc(bar, SAFETY[(bar - 66) // 4], amp=.9, wet=.25, echo=.25)
    if build and bar % 2 == 0:                  # the upload progress, over the snare roll
        mc(bar, PROGRESS[(bar - 72) // 2], amp=1.05)
    if bar in (96, 100):
        diva(bar, *CHORUS[0], amp=.8, choir=.4, echo_last=.6)

if DS:   # the whole diva part in one take, each line at its own level
    # the singer made alive (parts.LEM, the user's picks on Can You Tell?, 20 November; "ja, overzetten" for the
    # Badge): Lem's pitch drawn by warble's rule tuner, vibrato 1.6, tension 25, breaths, phrase dynamics. Each
    # switch (DS_PITCH=0.5 DS_VIB=1 DS_TENSION=0 DS_BREATH=0 DS_DYN=0: the earlier flat singer) is a test render
    knob = (lambda k: os.environ.get("DS_" + k.upper(), parts.LEM[k])) if LEM else \
        (lambda k: os.environ.get("DS_" + k.upper(), {"pitch": "0.5", "tension": "0", "vib": "1", "breath": "0",
                                                      "dyn": "0"}[k]))
    ALIVE = dict(pitch=knob("pitch"), tension=float(knob("tension")), vib=float(knob("vib")),
                 breaths=knob("breath") == "1", dynamics=knob("dyn") == "1")
    y = DS_PART.render(bank=DIVA.split(":", 1)[1], voice=DS_VOICE,
                       seed=int(os.environ.get("DS_SEED", "1")), timbre=DS_TIMBRE, **ALIVE)
    # DS_PITCH: rule | hard | free | 0..1 (see ds.py); DS_SEED: another take of the same score;
    # DS_TIMBRE: another singer for the same performance (a voice.CAST name: maya_diva, qwen_diva; ds.convert)
    g = np.ones(len(y))
    for t0, t1, a, _, _ in DS_GAIN:
        g[int(t0 * e.SR):int(t1 * e.SR)] = a
    for t0, t1 in DS_ACCENT:
        g[int(t0 * e.SR):int(t1 * e.SR)] *= 10 ** (float(os.environ.get("DS_ACCENT", "4")) / 20)
    y = y * g
    S.put("vox", 0.0, y, .5, 1.0, wet=.18, echo=.05)
    if DS_STACK:   # the produced stack: DS_STACK="voiceL,voiceR[,octave][,vocoder]"
        import vfx
        names = DS_STACK.split(",")
        bank, mode = DIVA.split(":", 1)[1], DS_VOICE
        for seed, timbre, pan, delay in ((2, names[0], .12, .012), (3, names[1], .88, .019)):
            d = DS_PART.render(bank=bank, voice=mode, seed=seed, timbre=timbre, **ALIVE) * g
            S.put("vox", delay, d, pan, .55, wet=.22, echo=.05)     # the doubles: other takes, other singers
        if "octave" in names:
            S.put("vox", 0.0, vfx.harmony(y, [12], [1.0])[:len(y)] - y, .5, .22, wet=.3, echo=.08)
        if "vocoder" in names:
            S.put("vox", 0.0, vfx.vocoder(y, [(chord_of(b), key_of(b)) for b in range(int(len(y) / e.SR / S.bar) + 1)], S.bpm),
                  .5, .35, wet=.25, echo=.1)
    for t0, t1, a, last, echo_last in DS_GAIN:   # the echo on each line's last word, as the Piper diva has it
        i, j = int((last - .08) * e.SR), min(int(t1 * e.SR), len(y))
        if j > i:            # straight into the echo send (centre: cos 45 degrees on each side)
            S.echo[i:j] += (np.stack([y[i:j], y[i:j]], 1) * (echo_last * np.cos(np.pi / 4))).astype(np.float32)

snare_roll(76, 3 if CROWD else 4, 1.1)
S.put("fx", S.at(76), e.riser(S.bar * (3 if CROWD else 4), .4), .5, wet=.3)
S.put("fx", S.at(64), e.downlifter(S.bar * 2, .3), .5, wet=.3)
S.put("fx", S.at(102), e.downlifter(S.bar * 2, .25), .5, wet=.3)   # out before the drums-only outro
# the big laser sweep into the last chorus
if not CROWD:
    S.put("fx", S.at(79, 2), laser(.5, 3000, 90, d=B * 2), .5, wet=.4, echo=.4)

# the master filter: closed down in the break, opening through the build
cut = [(0, 18000), (S.at(64), 18000), (S.at(64) + .05, 2800), (S.at(72), 3000), (S.at(80) - .02, 12000),
       (S.at(80), 18000), (S.n / e.SR, 18000)]
here = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "renders", "rhythm-of-the-badge_134bpm_Em.wav")
os.makedirs(os.path.dirname(out), exist_ok=True)
S.mixdown(out, {"drums": .9, "perc": .7, "bass": 1.0, "pads": .8, "keys": 1.35, "lead": 1.0, "vox": 1.9, "fx": .6},
          cut_keys=cut, duck={"pads": .7, "bass": .3, "keys": .3, "lead": .4}, room=.22, echo_mix=.4, lufs=-9.0,
          ir=room.impulse_response((12.0, 9.0, 5.0), rt60=2.4))
for bar, line, (take, score, heard) in MC_PICKS:     # the producer's picks, for the record
    print(f"MC bar {bar}: {take}, {score:.2f}: {line!r} heard as {heard!r}")
