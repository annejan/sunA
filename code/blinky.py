#!/usr/bin/env python3
"""Blinky (The LED Song): bubblegum eurodance, 132 BPM, D major (and E major after the key change). Sunday's
theme of the AI slop music compo.

blinky.py [OUT.wav]   (default renders/blinky_132bpm_D.wav)
PREVIEW=32-40 blinky.py   only bars 32 to 39 (a test render in renders/scratch/)
DIVA=piper blinky.py      the old diva (Piper re-pitched, with the Piper choir), for an A/B: to renders/scratch/

Every note and every sound here is written by Claude, in this file: no samples, no loops. 1998 at a children's
party, but the birthday child is a badge: a bouncy pulse riff, pizzicato strings, a happy piano (a rave piano
with a DX7 E.Piano under it), a toy glockenspiel, an offbeat bass, LED "blink" bleeps, a slide whistle, a diva
(singer D, below), a man who raps "hello world" and a gang of men who shout "hey!". In the break the LED blinks B-L-I-N-K-Y in Morse code: 63 sixteenths, so it fits four bars.
The key change is two semitones up, for the last chorus. The first and last 16 bars are drums only, for the DJ.

  bars   0-15  intro: kick, hats, clap (drums only)
        16-23  the riff and the pizzicato, the bass comes in; the gang shouts "hey!"
        24-31  verse: "I'm a little LED, on a little PCB"; the piano and the pad
        32-47  chorus, twice: "blink blink, blinky, on and off all night"
        48-55  rap: "hey! hello world!", "set the pin to out", "delay one second"
        56-59  break: no kick; the LED blinks BLINKY in Morse; the riff behind a closed door
        60-63  build: a snare roll and a riser; the gang counts in from zero
        64-79  the last chorus, a tone up (E major)
        80-87  post-chorus: the riff, the gang, the slide whistle
        88-95  winding down: the LED blinks BLINKY again, "light up the sky" in the echo
        96-111 outro: drums only

The diva is parts.Band's produced singer (diva_voice="ds:lem", "singer D"): Lem the Shapeshifter DS 2.5 sings our
notes and words, an octave below the written line (Lem's range: the chorus sits A3-A4, B3-B4 after the key change),
SoulX-Singer SVC turns the take into the Qwen diva's voice; in the chorus doubles from takes 2 and 3 in the Qwen pop
and Maya pop voices, a soft octave up and a vocoder, and a real harmony a third above (Maya soul; a third below on a
line where above would pass D5) instead of the Piper choir; "blink" 3 dB louder. Shape the melody with Lem alone:
DS_TIMBRE= DS_STACK= DS_HARMONY= SOLO=vox PREVIEW=32-40.
"""
import os
import sys

import numpy as np

import engine as e
import dx7
import parts
import room
import voice as V

e.seed(1998)
S = e.Song(bpm=132, bars=112)
STEP = S.step
B = S.beat

SINGER = os.environ.get("DIVA", "ds:lem")   # "piper": the old diva below, for an A/B
PIPER = SINGER == "piper"
DIVA = "en_US-lessac-high"           # the old diva: segfault has hfc_female; lessac is the roundest of the girls up high
RAPPER = "en_US-bryce-medium"         # the "hello world" man
GANG = [("en_US-joe-medium", .2), ("en_US-john-medium", .8), ("en_GB-alan-medium", .35),
        ("en_US-norman-medium", .65)]   # the men who shout "hey!", panned around the room
# the old diva's choir: left double, right double, a third above; in the last chorus a man an octave down
CHOIR = ["en_US-amy-medium", "en_GB-jenny_dioco-medium", "en_GB-cori-high", "en_US-hfc_male-medium"]

HOOK = ["D", "A", "Bm", "G"]                       # the intro, the break, the post-chorus
VERSE_PROG = ["D", "Bm", "G", "A"]                 # the doo-wop changes, for the cute verse
CHORUS_PROG = ["D", "A", "Bm", "G", "D", "A", "G", "A"]


def key_of(bar):
    return 2 if 64 <= bar < 96 else 0


def chord_of(bar):
    if 24 <= bar < 32:
        return VERSE_PROG[bar % 4]
    if 32 <= bar < 48 or 64 <= bar < 80:
        return CHORUS_PROG[bar % 8]
    return HOOK[bar % 4]


# singer D: Lem sings, the Qwen diva's voice, the eurodance stack (the Badge's and Can You Tell?'s chain). The lead
# is qwen_diva, not the brighter sing_qwen_pop: the bubblegum is in the band and the toy glockenspiel; the doubles
# already carry sing_qwen_pop, and the lead in the same voice would blur into them.
TIMBRE = "qwen_diva"
STACK = "sing_qwen_pop,sing_maya_pop,octave,vocoder"
HARMONY = "sing_maya_soul"
ACCENT = {"blink": 3}
OCTAVE = -12                  # Lem sings the written line an octave lower: written, the chorus reaches F#5-A5
if not PIPER:
    P = parts.Band(S, CHORUS_PROG, scale="major", key_of=key_of, tonic="D", diva_voice=SINGER, timbre=TIMBRE,
                   stack=STACK, harmony=HARMONY, accent=ACCENT)
    P.chord = chord_of        # the section's chord, for the vocoder


# ---------------------------------------------------------------- our own instruments
def pizz(m, vel=1.0):
    """A plucked violin string: harmonics that die away, the high ones first, and the click of the finger."""
    f = float(e.hz(m))
    t = e.tt(.55)
    g = np.zeros_like(t)
    for n in range(1, 16):
        fn = f * n * np.sqrt(1 + .00015 * n * n)
        if fn > 7000:                     # nothing above 7 kHz: a string, not a harpsichord
            break
        a = vel ** (.3 + .1 * n) / n ** 1.5
        g += a * np.sin(2 * np.pi * fn * t + e.rng.uniform(0, 6.3)) * np.exp(-t * (6 + 3.2 * n))
    click = e.bandpass(e.rng.standard_normal(len(t)), 600, 3000) * np.exp(-t * 400) * .08
    return (g + click) * e.rise(t, .0015) * .8


def pizz_section(m, vel=1.0):
    """Three players, a few cents and a few milliseconds apart, left, middle and right."""
    out = np.zeros((int(.58 * e.SR), 2))
    for cents, late, pan in ((-6, .0, .25), (0, .006, .5), (7, .011, .75)):
        g = pizz(m + cents / 100, vel)
        i = int(late * e.SR)
        out[i:i + len(g), 0] += g[:len(out) - i] * np.cos(pan * np.pi / 2)
        out[i:i + len(g), 1] += g[:len(out) - i] * np.sin(pan * np.pi / 2)
    return out / 2


def bouncy(m, d):
    """The bubblegum riff synth: two pulses and a sub, a little "boing" in the pitch on the attack, a filter that
    snaps shut. The filter follows the note but stops at 3.2 kHz, so the high notes stay round."""
    t = e.tt(d + .1)
    f = float(e.hz(m)) * (1 + .025 * np.exp(-t * 70))
    g = .5 * e.pulse(f, t, .3) + .45 * e.pulse(f * 1.005, t, .5) + .55 * e.sine(f / 2, t)
    cut = min(3200.0, float(e.hz(m)) * 4.5) * (.3 + .7 * np.exp(-t * 14)) + 350
    g = e.sweep(g, cut, 1.1, 64)
    return g * e.rise(t, .002) * (.55 + .45 * np.exp(-t * 9)) * e.gate(t, d, .04)


def bleep(m, d=.06):
    """An LED blinking, as a sound: a sine with a quick chirp down on the attack, and a soft second harmonic."""
    t = e.tt(d + .03)
    f = float(e.hz(m)) * (1 + .15 * np.exp(-t * 300))
    g = e.sine(f, t, 0.0) + .2 * e.sine(2 * f, t, 0.0)
    return g * e.rise(t, .003) * e.gate(t, d, .012) * .5


def whistle(m0, m1, d):
    """A party slide whistle: a sine that slides from one note to the other, a wobble, a breath."""
    t = e.tt(d)
    u = t / d
    m = m0 + (m1 - m0) * (3 * u ** 2 - 2 * u ** 3) + .25 * np.sin(2 * np.pi * 6 * t) * u
    f = e.hz(m)
    breath = e.highpass(e.lowpass(e.rng.standard_normal(len(t)), 3500), 900) * .06
    g = e.sine(f, t, 0.0) + .1 * e.sine(2 * f, t, 0.0) + breath
    return g * e.rise(t, .03) * np.minimum((d - t) / .05, 1) * .4


# A DX7 toy glockenspiel, ours: two carriers with a hard metal modulator each, keyboard-scaled so that the high
# notes lose their edge (the lesson of the shrill harpsichord).
dx7.PATCHES["toy_glock"] = dict(algo=5, feedback=0, gain=.5, ops=[
    dx7.op(1, 0, 0, 99, (99, 32, 25, 45), (99, 70, 0, 0), vel=.5),
    dx7.op(3, 50, 0, 70, (99, 45, 25, 45), (99, 40, 0, 0), vel=.8, ks=6),       # 2 -> 1: ratio 3.5, the clang
    dx7.op(4, 0, 2, 80, (99, 40, 25, 45), (99, 60, 0, 0), vel=.5),
    dx7.op(1, 0, 0, 62, (99, 60, 25, 45), (99, 30, 0, 0), vel=.9, ks=6),         # 4 -> 3
    dx7.op(1, 0, -2, 0, (99, 50, 20, 50), (99, 0, 0, 0)),
    dx7.op(1, 0, 0, 0, (99, 50, 20, 50), (99, 0, 0, 0)),
])


# ---------------------------------------------------------------- drums
def drums(bar, kick=True, clap=True, hats=True, open_hats=True, tamb=False, crash=False, amp=1.0):
    t0 = S.at(bar)
    if kick:
        for b in range(4):
            S.kick(t0 + b * B, 1.0 * amp, punch=140, base=52, length=.32, click=.4)
    if clap:
        for b in (1, 3):
            S.put("drums", t0 + b * B, e.clap(.6 * amp), .5, wet=.2)
            S.put("drums", t0 + b * B, e.snare(.4 * amp), .5, wet=.22)
    if hats:
        for k in range(16):
            if k % 4 == 2 and open_hats:
                S.put("perc", t0 + k * STEP, e.hat(.6 * amp, opened=True), .55, wet=.08)
            elif k % 4 != 2:
                S.put("perc", t0 + k * STEP, e.hat((.3 if k % 2 else .18) * amp), .65, wet=.04)
    if tamb:      # the tambourine of the children's party: a shaker on the sixteenths, accents on the offbeats
        for k in range(16):
            S.put("perc", t0 + k * STEP, e.shaker((.45 if k % 4 == 2 else .18) * amp), .3, wet=.08)
    if crash:
        S.put("perc", t0, e.crash(.7), .5, wet=.3)


def snare_roll(bar0, bars=4, amp=1.0):
    """Sixteenths, climbing, and thirty-seconds in the last bar."""
    total = bars * 16
    for k in range(total):
        u = k / total
        t = S.at(bar0) + k * STEP
        S.put("drums", t, e.snare((.15 + .6 * u ** 1.5) * amp), .5, wet=.25)
        if k >= total - 16:
            S.put("drums", t + STEP / 2, e.snare((.15 + .6 * u ** 1.5) * amp * .8), .5, wet=.25)


# ---------------------------------------------------------------- bass, pizzicato, riff, piano, pad
def bass(bar, amp=1.0):
    """The offbeat bass: between the kicks, an octave jump at the end of the bar."""
    root = e.root_note(chord_of(bar), key_of(bar), lo=33)
    for k in (2, 6, 10, 14):
        S.put("bass", S.at(bar) + k * STEP, e.bass_note(root + (12 if k == 14 else 0), STEP * 1.6, cut=1200, decay=3),
              .5, .9 * amp, wet=0)
    S.put("bass", S.at(bar) + 15 * STEP, e.bass_note(root + 12, STEP * .8, cut=1200, decay=3), .5, .5 * amp, wet=0)


# the pizzicato: eighths up and down the chord (root, fifth, octave, fifth, third, fifth, octave, fifth)
PIZZ_SHAPE = (0, 2, 3, 2, 1, 2, 3, 2)


def pizzicato(bar, amp=1.0):
    root, iv = e.chord(chord_of(bar), key_of(bar))
    lo = 62 + (root - 62) % 12                  # the root between D4 and C#5
    tones = [lo, lo + iv[1], lo + iv[2], lo + 12]
    for j, s in enumerate(PIZZ_SHAPE):
        vel = 1.0 if j % 2 == 0 else .75
        S.put("keys", S.at(bar) + j * 2 * STEP, pizz_section(tones[s], vel), amp=.5 * amp * vel, wet=.25, echo=.05)


RIFF = {   # one bar per chord, on sixteenths: up the chord, a bounce to the top, back down
    "D": "A4 . D5 . F#5 . D5 A5 . F#5 . D5 E5 . F#5 .",
    "A": "A4 . C#5 . E5 . C#5 A5 . E5 . C#5 D5 . E5 .",
    "Bm": "B4 . D5 . F#5 . D5 B5 . F#5 . D5 E5 . F#5 .",
    "G": "B4 . D5 . G5 . D5 B5 . G5 . D5 E5 . D5 .",
}


def riff(bar, amp=1.0, cut=None):
    for t, m, d in S.notes(bar, RIFF[chord_of(bar)], key_of(bar)):
        g = bouncy(m, STEP * .9)
        if cut:
            g = e.lowpass(g, cut)
        S.put("lead", t, g, .55, .45 * amp, wet=.18, echo=.18)
        S.put("lead", t + .011, g, .45, .25 * amp, wet=.18)     # a second one, a hair late: wider


STABS = (0, 3, 6, 10, 13)


def piano(bar, amp=1.0):
    """The happy piano: a rave piano and the DX7 E.Piano under it, the same chord on the same offbeats."""
    notes = e.close_voicing(chord_of(bar), key_of(bar), lo=62, hi=78)
    for k in STABS:
        for j, m in enumerate(notes):
            t = S.at(bar) + k * STEP + j * .003
            S.put("keys", t, e.piano(m, STEP * 2, .9), .35 + .15 * j, .26 * amp, wet=.25)
            S.put("keys", t, dx7.note("epiano", m, STEP * 2, .8, tail=.4), .65 - .15 * j, .3 * amp, wet=.25, echo=.08)


def pads(bar, amp=1.0, cut=2500):
    notes = e.voicing(chord_of(bar), key_of(bar), lo=55)
    S.put("pads", S.at(bar), e.pad(notes, S.bar, cut=cut, a=.3, r=.6), amp=.4 * amp, wet=.4)


def orch(bar, amp=1.0):
    S.put("fx", S.at(bar), e.orch_hit(e.close_voicing(chord_of(bar), key_of(bar), lo=57, hi=72), amp), wet=.5)


# ---------------------------------------------------------------- the LED: bleeps and Morse code
MORSE = {"B": "-...", "L": ".-..", "I": "..", "N": "-.", "K": "-.-", "Y": "-.--"}


def morse(bar, word="BLINKY", m=81, amp=1.0):
    """The LED spells a word in Morse code on the sixteenth grid: a dot is one sixteenth, a dash three, one off
    between the marks, three between the letters. BLINKY is 63 sixteenths: four bars, one to spare."""
    k = 0
    for i, letter in enumerate(word):
        for mark in MORSE[letter]:
            n = 1 if mark == "." else 3
            S.put("fx", S.at(bar) + k * STEP, bleep(m + key_of(bar), n * STEP * .8), .5 + .25 * np.sin(k),
                  .4 * amp, wet=.25, echo=.3)
            k += n + 1
        k += 2


def blinks(bar, steps=(12, 14), m=86, amp=1.0):
    """Two blinks of the LED in the gap after "blinky"."""
    for k in steps:
        S.put("fx", S.at(bar) + k * STEP, bleep(m + key_of(bar), STEP * .5), .3 if k == steps[0] else .7, .35 * amp,
              wet=.2, echo=.25)


# ---------------------------------------------------------------- the diva: the melody and its words
# the verse, a line every two bars, on eighths (the words as the voice should say them, one per note; then the
# words as DiffSinger reads them, None when the same)
VERSE = [
    (". A4 B4 A4 F#4 D5 - D5 - D5 - - - . . .", "I'm a lit tle ell ee dee", "I'm a little + el ee dee"),
    (". A4 B4 A4 F#4 E5 - E5 - C#5 - - - . . .", "on a lit tle pee see bee", "on a little + pee see bee"),
    (". F#4 F#4 A4 B4 D5 - - B4 A4 - - - . . .", "when you write a one to me", None),
    (". G4 A4 B4 - . B4 C#5 E5 - - - - - . .", "I light up can't you see", None),
]
# the chorus, a line a bar, on sixteenths
BLINKY = "blink blink blinky +"
CHORUS = [
    ("A4 - - A4 - - D5 - F#5 - - - - - . .", "blink blink blink kee", BLINKY),
    ("E5 - E5 - D5 - C#5 - - - A4 - - - . .", "on and off all night", None),
    ("B4 - - B4 - - D5 - F#5 - - - - - . .", "blink blink blink kee", BLINKY),
    ("E5 - D5 - B4 - - A4 B4 - - - - - . .", "red and green and white", None),
    ("F#5 - - E5 - - D5 - E5 - D5 - - - . .", "tog gull me bay bee", "toggle + me baby +"),
    ("E5 - C#5 - D5 - E5 - A5 - - - - - . .", "gee pee eye oh high", None),
    ("B4 - - B4 - - D5 - E5 - - - - - . .", "blink blink blink kee", BLINKY),
    ("A4 - - C#5 - - D5 - E5 - - - - - . .", "light up the sky", None),
]


def third_above(m, key):
    """The note two steps up the D major scale (moved with the key change): a diatonic third."""
    scale = {(2 + key + pc) % 12 for pc in (0, 2, 4, 5, 7, 9, 11)}
    for up in (3, 4):
        if (m + up) % 12 in scale:
            return m + up
    return m + 4


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


def diva(bar, line, words, ds_words=None, bars=1, amp=1.0, choir=0.0, big=False, echo_last=.35):
    """A line for the diva: singer D (Lem, sing()), or with DIVA=piper the old one (piper_diva())."""
    if PIPER:
        piper_diva(bar, line, words, bars, amp, choir, big, echo_last)
    else:
        sing(bar, line, words, ds_words, bars, amp, choir * (1.2 if big else 1.0), echo_last)


# BLINK_GAP=1 (an A/B, 21 November): a sixteenth rest after each "blink", so its "k" is heard before the next "b".
# Whisper heard "bling" without it and "drink" or "thank" with it, and the whole song worse (36 % against 43 %): off
D_LINE = {} if os.environ.get("BLINK_GAP") != "1" else {
    line: line.replace(f"{a} - - {b} - -", f"{a} - . {b} - .", 1)
    for line, _, w in CHORUS if w == BLINKY for a, b in [line.split()[0:4:3]]}


def sing(bar, line, words, ds_words=None, bars=1, amp=1.0, harm=0.0, echo=.35):
    """Singer D sings a line, an octave below the written notes. harm > 0 (the chorus): the doubles at .55 and a
    harmony a third above at amp * harm (a third below when above would pass D5); else the doubles at the verse's
    level. echo: the last word into the delay."""
    if not S.live(bar, bars):
        return
    line = D_LINE.get(line, line)
    P.diva(bar, line, words, bars=bars, amp=amp, octave=OCTAVE - 12, ds_words=ds_words)   # Band: +12
    t0, t1, a, last, _ = P.ds_lines[-1]
    P.ds_lines[-1] = (t0, t1, a, last, echo)
    if not harm:
        return
    P.ds_double[-1] = (t0, t1, .55)
    key = key_of(bar)
    pairs = parts.words_on(S.notes(bar, line, key, bars), ds_words or words)
    sung = [m + OCTAVE for _, ns in pairs for _, m, _ in ns]
    up = max(P.step_up(m, 2, key) for m in sung) <= 74          # D5
    for w, ns in pairs:
        for k, (t, m, d) in enumerate(ns):
            m = P.step_up(m + OCTAVE, 2, key) if up else P.step_down(m + OCTAVE, 2, key)
            P.ds_harm.note(t, m, d * .97, w if k == 0 else "+")
    P.ds_choir.append((t0, t1, amp * harm))


def piper_diva(bar, line, words, bars=1, amp=1.0, choir=0.0, big=False, echo_last=.35):
    """The old diva sings a line: a word on its notes, the consonants before the beat, an echo on the last word.
    choir: how loud the other voices are (a double left, a double right, a third above in the middle); with
    big=True a man an octave down as well."""
    key = key_of(bar)
    pairs = words_on(S.notes(bar, line, key, bars), words)
    for i, (w, ns) in enumerate(pairs):
        last = i == len(pairs) - 1
        t = ns[0][0]
        notes = [(m, d * .97) for _, m, d in ns]
        li, y = V.sing(w, notes, voice=DIVA, formant=1.05)
        S.put("vox", t - li, y, .5, amp, wet=.12, echo=echo_last if last else .05)
        if not choir:
            continue
        third = [(third_above(m, key), d) for m, d in notes]
        parts = [(CHOIR[0], notes, 8, .018, .15, .7), (CHOIR[1], notes, -8, .009, .85, .7),
                 (CHOIR[2], third, 0, .006, .4, .55)]
        if big:
            parts.append((CHOIR[3], [(m - 12, d) for m, d in notes], 0, .012, .6, .6))
        for v, ns2, cents, late, pan, g in parts:   # vowels only: the diva's consonants stay clean
            _, y = V.sing(w, ns2, voice=v, cents=cents, vibrato=.15, vowel_only=True)
            S.put("vox", t + late, y, pan, amp * choir * g, wet=.15, echo=.05)


def chorus_line(bar, big=False):
    line, words, ds_words = CHORUS[bar % 8]
    diva(bar, line, words, ds_words, choir=.42, big=big)
    # the toy glockenspiel doubles the hook, under the voices
    for t, m, d in S.notes(bar, line, key_of(bar)):
        S.put("lead", t, dx7.note("toy_glock", m, min(d, B), .8, tail=.6), .6, .3, wet=.3, echo=.15)
    if bar % 8 in (0, 2, 6):
        blinks(bar)


# ---------------------------------------------------------------- the men: the rap and the gang
def rapper(bar, text, beats=4.0, beat=0.0, amp=1.0):
    """A rap line from a beat, fitted to some beats (a sixteenth short, to breathe)."""
    y = V.rap(text, beats * B - STEP, voice=RAPPER, pitch=.95)
    S.put("vox", S.at(bar, beat), y, .5, amp, wet=.06, echo=.06)


def gang(bar, beat=0.0, word="Hey!", amp=1.0, beats=.75):
    """Four men shout a word together, a little apart in time and pitch, around the room."""
    for i, (v, pan) in enumerate(GANG):
        y = V.rap(word, beats * B, voice=v, pitch=.9 + .06 * i)
        S.put("vox", S.at(bar, beat) + .008 * i - .02, y, pan, .5 * amp, wet=.15, echo=.04)


RAP = [(48, "Hello world!", 3, 1), (49, "Hello world!", 3, 1),
       (50, "Put your hands up, everybody, set the pin to out!", 8, 0),
       (52, "Delay one second, now everybody shout!", 7, 0)]


# ---------------------------------------------------------------- the arrangement
def arrange():
    for bar in range(112):
        intro, outro = bar < 16, bar >= 96
        chorus = 32 <= bar < 48 or 64 <= bar < 80
        rap = 48 <= bar < 56
        brk = 56 <= bar < 60
        build = 60 <= bar < 64
        post = 80 <= bar < 88
        down = 88 <= bar < 96

        if intro:
            drums(bar, clap=bar >= 8, open_hats=bar >= 4, crash=bar == 0)
        elif outro:
            drums(bar, clap=bar < 108, open_hats=bar < 104, crash=bar == 96)
        elif brk:
            drums(bar, kick=False, clap=False, open_hats=False, amp=.7)
        elif build:
            drums(bar, kick=bar < 62, clap=False, open_hats=False, amp=.9)
        else:
            drums(bar, tamb=chorus or post or rap, crash=bar in (16, 24, 32, 40, 48, 64, 72, 80))

        # the band
        if 16 <= bar < 24:
            riff(bar, .9, cut=700 * 1.32 ** (bar - 16))
        if 16 <= bar < 96 and not (brk or build):
            bass(bar, .7 if bar < 20 else 1.0)
        if 16 <= bar < 96 and not build:
            pizzicato(bar, .7 if brk or down else 1.0)
        if 24 <= bar < 56 or chorus or post:
            piano(bar, .8 if chorus else 1.0)
        if 24 <= bar < 96:
            pads(bar, 1.3 if brk or build else .9, cut=1500 if brk else 2500)
        if chorus or rap or post:
            riff(bar, .7 if chorus else 1.0)
        if brk:
            riff(bar, .8, cut=900)
        if build:
            riff(bar, .85, cut=1200 + 700 * (bar - 60))
        if down:
            riff(bar, .6, cut=2400 - 200 * (bar - 88))

        if bar in (16, 24, 32, 48, 64, 80):
            orch(bar)

        # the voices
        if bar in (16, 18, 20, 22):
            gang(bar, 0)
        if 24 <= bar < 32 and bar % 2 == 0:
            diva(bar, *VERSE[(bar - 24) // 2], bars=2, amp=.95)
        if chorus:
            chorus_line(bar, big=bar >= 64)
            if bar in (40, 44, 72, 76):      # the gang joins the second time round
                gang(bar, 0, amp=.7)
        if rap:
            for b0, text, beats, beat in RAP:
                if bar == b0:
                    if beat:
                        gang(bar, 0)
                    rapper(bar, text, beats, beat)
            if bar == 54:
                gang(bar, 0, "Hey!", 1.2)
                gang(bar, 2, "Hey!", 1.2)
            if bar == 55:
                for b in range(4):
                    gang(bar, b, "Hey!", 1.0)
        if bar == 58:
            diva(bar, *CHORUS[7], amp=.8, echo_last=.6)
        if bar == 62:
            rapper(bar, "Set the pin high!", 3, 0, amp=1.1)
        if bar == 63:     # programmers count from zero
            for b, word in enumerate(["Zero!", "One!", "Two!", "Three!"]):
                gang(bar, b, word, 1.1, beats=.7)
        if post:
            if bar % 2 == 0:
                gang(bar, 0)
            if bar in (82, 86):
                rapper(bar, "Hello world!", 3, 1)
        if down and bar in (90, 94):
            diva(bar, *CHORUS[7], amp=.75, echo_last=.7)

    # the LED in Morse code, the blinks, the whistles, the risers
    morse(56)
    morse(88, amp=.8)
    S.put("fx", S.at(50, 2), whistle(76, 88, 1.0), .7, .5, wet=.3)
    S.put("fx", S.at(54, 3), whistle(88, 74, .8), .3, .5, wet=.3)
    S.put("fx", S.at(84, 2), whistle(76, 90, 1.0), .7, .5, wet=.3)
    snare_roll(60, 4, 1.1)
    S.put("fx", S.at(60), e.riser(S.bar * 4, .4), .5, wet=.3)
    S.put("fx", S.at(56), e.downlifter(S.bar * 2, .3), .5, wet=.3)
    S.put("fx", S.at(96), e.downlifter(S.bar * 2, .25), .5, wet=.3)


def main():
    arrange()
    if not PIPER:
        P.finish()            # singer D's whole part: Lem's take, converted, stacked
    cut = [(0, 18000), (S.at(56), 18000), (S.at(56) + .05, 3000), (S.at(60), 3000), (S.at(64) - .02, 12000),
           (S.at(64), 18000), (S.n / e.SR, 18000)]
    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "renders", "blinky_132bpm_D.wav")
    if PIPER and len(sys.argv) < 2:     # the A/B: never in place of the song's render (DIVA is no engine switch)
        out = os.path.join(here, "renders", "scratch", "blinky_132bpm_D-divapiper.wav")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    S.mixdown(out, {"drums": .95, "perc": .7, "bass": .85, "pads": .85, "keys": .85, "lead": .6, "vox": 1.8,
                    "fx": .6},
              cut_keys=cut, duck={"pads": .7, "bass": .3, "keys": .3, "lead": .35}, room=.2, echo_mix=.4,
              lufs=-9.0, ir=room.impulse_response((9.0, 6.0, 3.5), rt60=1.3))


if __name__ == "__main__":
    main()
