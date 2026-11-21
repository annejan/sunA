#!/usr/bin/env python3
"""Packet Loss (Of Love): early 90s garage house, mellow, 122 BPM, F minor. Saturday's theme of the AI slop
music compo.

packet_loss.py [OUT.wav]   (default renders/packet-loss_122bpm_Fm.wav)

Every note and every sound here is written by Claude, in this file: no samples, no loops. Late at night, rain on
the window, two lovers on a bad connection. He sends his feelings in tiny little parts; she only gets the header.
A swung garage shuffle, an M1-style organ bass, a DX7 electric piano, warm gospel piano chords in the chorus, a
saxophone made from a saw wave and a breath, and a duet: a man and a woman, one voice at a time, and a lot of TCP
jokes. In the second chorus the lead vocal really does lose packets. The first and last 16 bars are drums only,
for the DJ.

  bars   0-15  intro: kick, shuffled hats, then clap, shaker and congas (drums only; the rain starts)
        16-23  the organ bass; the electric piano behind a door that opens
        24-31  verse 1, him: "I sent you all my feelings in tiny little parts" (she answers "ACK", then "NACK")
        32-39  verse 2, her: "I only got the header" (he answers "ACK")
        40-55  chorus: her "packet loss of love" / him "say it once again"; gospel piano; sonar pings
        56-63  the saxophone solo, the band behind it
        64-71  break: no kick, no bass, thunder; the sax goes on; "64 bytes from your heart"; a riser
        72-87  chorus again; from bar 80 the lead vocal drops packets
        88-103 winding down: "ping me when you're ready" / "I'll be waiting up"; "request timed out"
       104-119 outro: drums only (the rain stops)

The electric piano is the DX7 E.Piano (dx7.py); the reverb is a small simulated room (room.py), a flat at night.

The singers (singer D, 21 November): Lem the Shapeshifter DS 2.5 (DiffSinger) sings our notes and words at the
written pitch, alive (warble's rule tuner, vibrato, tension, breaths, phrase dynamics: parts.LEM); SoulX-Singer SVC
turns her take into a soulful Qwen voice (her) and a second take into a Qwen baritone (him). Sparse, like the 90's
house records: one voice at a time, no doubles, no harmony, no vocoder, no choir; the answer "say it once again" is
his now. Shape the tune fast with Lem alone: DS_TIMBRE= SOLO=vox PREVIEW=40-48 .venv/bin/python packet_loss.py.
DIVA=piper: the old voices (two Piper voices re-pitched, a duet on the hook, a Piper choir on the answer), for A/B.
"""
import functools
import os
import sys

import numpy as np

import engine as e
import dx7
import room
import voice as V

e.seed(122)
S = e.Song(bpm=122, bars=120)
STEP = S.step
B = S.beat
SWING = .2 * STEP           # a 60 % shuffle on the sixteenths: the garage swing

# the voices: the duet, the choir that answers (all different voices, no doubles), and the computer
HIM = "en_US-hfc_male-medium"
HER = "en_US-hfc_female-medium"
CHOIR = ["en_GB-cori-high", "en_US-kristin-medium", "en_US-ljspeech-high", "en_GB-alan-medium",
         "en_US-john-medium"]
COMPUTER = "en_US-lessac-high"

# singer D (the default): Lem sings both parts, converted into two voices; DIVA=piper: the Piper duet and choir
DIVA = os.environ.get("DIVA", "ds:lem")
LEM = DIVA.startswith("ds:")
HER_TIMBRE = "sing_qwen_soul"         # her voice (fallback: sing_maya_soul, sing_qwen_husky)
HIM_TIMBRE = "sing_qwen_tenor"        # his (C3-F4): the baritone blurred more verse words (Whisper)
ACCENT = {"loss": 2}
LOSSY = []                            # (from, to) seconds of each line that loses packets (singer D)

VERSE_PROG = ["Fm9", "Dbmaj9", "Bbm9", "Eb9"]
CHORUS_PROG = ["Dbmaj9", "Eb9", "Cm7", "Fm9", "Dbmaj9", "Eb9", "Bbm9", "C7"]   # C7 pulls home to F minor

if LEM:
    import parts

    def _singer(timbre):
        b = parts.Band(S, VERSE_PROG, diva_voice=DIVA, timbre=timbre,
                       stack="", harmony="", accent=ACCENT, verse_double=0.0)
        b.ds_gain = 1.8               # 1.45 buried the words (Whisper 31 % -> 53 %)
        return b

    SINGER = {HER: _singer(HER_TIMBRE), HIM: _singer(HIM_TIMBRE)}


def chorus_bar(bar):
    return 40 <= bar < 56 or 72 <= bar < 88


def chord_of(bar):
    return CHORUS_PROG[bar % 8] if chorus_bar(bar) else VERSE_PROG[bar % 4]


def sw(k):
    """The time of sixteenth k in a bar, swung (the odd sixteenths come late)."""
    return k * STEP + (SWING if k % 2 else 0)


def notes(bar, line, bars=1):
    """S.notes, with the shuffle: a note on an odd sixteenth comes late, like the hats."""
    out = []
    for t, m, d in S.notes(bar, line, bars=bars):
        k = round((t - S.at(bar)) / STEP)
        out.append((t + (SWING if k % 2 else 0), m, d))
    return out


def rootless(name, lo, hi, n=4):
    """A keys player's voicing: the chord's tones between lo and hi without the root, the lowest n of them."""
    root, iv = e.chord(name)
    pcs = {i % 12 for i in iv if i % 12}
    return [m for m in range(lo, hi + 1) if (m - root) % 12 in pcs][:n]


# ---------------------------------------------------------------- drums
def drums(bar, kick=True, clap=True, hats=True, shaker=False, congas=False, rimshots=False, crash=False, amp=1.0):
    t0 = S.at(bar)
    if kick:
        for b in range(4):
            S.kick(t0 + b * B, .95 * amp, punch=85, base=45, length=.4, click=.12)
    if clap:
        for b in (1, 3):
            S.put("drums", t0 + b * B, e.clap(.5 * amp), .5, wet=.25)
            S.put("drums", t0 + b * B, e.snare(.16 * amp), .5, wet=.2)
        if bar % 4 == 3:    # the garage ghost clap, on the last swung sixteenth of the phrase
            S.put("drums", t0 + sw(15), e.clap(.22 * amp), .45, wet=.3)
    if hats:
        for k in range(16):
            if k % 4 == 2:
                S.put("perc", t0 + sw(k), e.hat(.4 * amp, opened=True), .6, wet=.1)
            else:
                a = (.24 if k % 2 else .3) * amp * (1 + .15 * np.sin(bar * 3 + k))
                S.put("perc", t0 + sw(k), e.hat(a), .62, wet=.05)
    if shaker:
        for k in range(16):
            S.put("perc", t0 + sw(k), e.shaker((.32 if k % 2 else .18) * amp), .32, wet=.08)
    if congas:   # a low and a high conga, shuffled, left and right
        for k, m, a in ((3, 62, .3), (6, 55, .35), (10, 62, .25), (11, 67, .2), (14, 55, .3)):
            S.put("perc", t0 + sw(k), e.conga(m, a * amp), .3 if m < 60 else .7, wet=.2)
    if rimshots:
        for k in (3, 7, 13) if bar % 2 else (5, 10, 13):
            S.put("perc", t0 + sw(k), e.rim(.3 * amp), .4, wet=.25, echo=.15)
    if crash:
        S.put("perc", t0, e.crash(.45), .5, wet=.3)


# ---------------------------------------------------------------- the organ bass (the M1's "Organ 2", more or less)
@functools.lru_cache(maxsize=256)
def _organ_bass(m, n):
    d = n / e.SR
    t = e.tt(d + .05)
    f = float(e.hz(m))
    g = sum(a * np.sin(2 * np.pi * f * r * t) for r, a in ((1, 1.0), (2, .55), (3, .3), (4, .18), (6, .06)))
    g = np.tanh(1.4 * g) * .8 + .35 * np.sin(2 * np.pi * f * t)      # drawbars into a warm amp, a sine under it
    g = e.lowpass(g, 1400)
    click = e.bandpass(e.rng.standard_normal(len(t)), 1000, 4000) * np.exp(-t * 500) * .15
    env = (.55 + .45 * np.exp(-t * 9)) * e.rise(t, .003) * e.gate(t, d, .03)
    return (g + click) * env


def organ_bass(m, d):
    return _organ_bass(int(m), int(d * e.SR)).copy()


# sixteenth, interval from the root, length in sixteenths: the Robin S bounce, slowed down and made polite
BASSLINE = [(0, 0, 2), (3, 0, 1), (6, 12, 1), (7, 0, 2), (10, 7, 1), (11, 10, 1), (14, 12, 2)]


def bass(bar, amp=1.0):
    root = e.root_note(chord_of(bar), lo=29)    # F1 .. E2
    for k, iv, n in BASSLINE:
        S.put("bass", S.at(bar) + sw(k), organ_bass(root + iv, n * STEP * .85), .5, .8 * amp, wet=0)


# ---------------------------------------------------------------- keys
def epiano(m, d, vel):
    return dx7.note("epiano", m, d, vel, tail=.9)


EP_COMP = [(0, 3, .7), (6, 2, .5), (10, 3, .65), (13, 2, .45)]    # sixteenth, length in sixteenths, velocity


def ep_comp(bar, amp=1.0, cut=None):
    """The DX7 electric piano on the offbeats, a slow tremolo panning it left and right."""
    for k, n, vel in EP_COMP:
        for j, m in enumerate(rootless(chord_of(bar), 56, 75)):
            g = epiano(m, n * STEP, vel)
            if cut:
                g = e.lowpass(g, cut)
            pan = .5 + .28 * np.sin(2 * np.pi * (bar + k / 16) / 2)
            S.put("keys", S.at(bar) + sw(k) + j * .005, g, pan, .4 * amp, wet=.3, echo=.1)


@functools.lru_cache(maxsize=512)
def _warm_piano(m, n, vel):
    """The gospel piano: engine.piano with the brightness taken off, so it sits behind the voices."""
    g = e.piano(m, n / e.SR, vel)
    return e.lowpass(g, 1200 + 1800 * vel, order=1)


def warm_piano(m, d, vel=.8):
    return _warm_piano(int(m), int(d * e.SR), round(vel, 2)).copy()


PIANO = [(0, 4, .75), (3, 3, .6), (6, 2, .55), (10, 4, .7), (14, 2, .5)]


def gospel_piano(bar, amp=1.0):
    root = e.root_note(chord_of(bar), lo=41)
    for k, n, vel in PIANO:
        for j, m in enumerate([root] + rootless(chord_of(bar), 55, 74, 5)):
            S.put("keys", S.at(bar) + sw(k) + j * .004, warm_piano(m, n * STEP, vel * (.7 if j == 0 else 1)),
                  .35 + .06 * j, .3 * amp, wet=.3)


def pads(bar, amp=1.0, cut=1300):
    S.put("pads", S.at(bar), e.pad(rootless(chord_of(bar), 53, 72), S.bar, cut=cut), amp=.45 * amp, wet=.4)


# ---------------------------------------------------------------- the saxophone
def sax(ns, vel=.9):
    """A tenor sax from a saw wave: the notes glide into each other, a detached note scoops up into its pitch,
    a vibrato comes in on the long notes, and the filter opens with the breath (louder is brighter, but never
    more than about four harmonics, so it stays warm high up). ns: [(second, midi, seconds)].
    Returns (start second, mono)."""
    t0 = ns[0][0]
    end = max(tn + d for tn, _, d in ns) - t0
    n = int((end + .5) * e.SR)
    t = np.arange(n) / e.SR
    target, pitch, onset, scoop = np.zeros(n), np.full(n, float(ns[0][1])), np.zeros(n), np.zeros(n)
    prev_end = -1.0
    for tn, m, d in ns:
        a, b = int((tn - t0) * e.SR), int((tn - t0 + d) * e.SR)
        pitch[a:], onset[a:] = m, tn - t0
        target[a:b] = 1.0
        if (tn - t0) - prev_end < .02:              # tongue the legato notes: a little dip in the breath
            target[a:a + int(.018 * e.SR)] = .6
        else:                                        # a detached note: scoop up into it
            scoop[a:] -= .8 * np.exp(-(t[a:] - t[a]) / .045)
        prev_end = tn - t0 + d
    env = e.one_pole(target, .022)
    p = e.one_pole(pitch - pitch[0], .02) + pitch[0] + scoop
    p += .16 * np.sin(2 * np.pi * 5.1 * t) * np.clip((t - onset - .28) / .3, 0, 1)
    f = e.hz(p)
    src = e.saw(f, t) + .25 * e.saw(f * 1.003, t)
    y = e.sweep(src, np.minimum(700 + 2000 * env ** 1.6 * vel, f * 4.5 + 300), .8, 64)
    y = y + .6 * e.bandpass(y, 300, 800)            # the body of the horn
    breath = e.bandpass(e.rng.standard_normal(n), 1200, 3200) * .06
    return t0, np.tanh(1.6 * (y + breath) * env) / 1.6


# the solo, two bars a line, on the verse chords (Fm9 Dbmaj9 | Bbm9 Eb9)
SOLO = [
    ". . . . C4 - Eb4 F4 - - - - Ab4 - F4 - - - - - . . Eb4 F4 Ab4 - C5 - Ab4 - F4 -",
    "Db5 - - - C5 - Bb4 - Ab4 - F4 - - - . . G4 - Ab4 - Bb4 - - - Db5 - C5 - Bb4 - G4 -",
    "Ab4 - - - - - - - . . F4 - G4 Ab4 C5 - Eb5 - - - - - C5 - Ab4 - F4 - - - . .",
    "Db5 - C5 Bb4 - - Ab4 - F4 - - - Db4 - F4 - Eb4 - - - - - - - . . Bb3 - Db4 - Eb4 -",
    "F4 - - - - - - - - - - - . . Ab4 Bb4 C5 - - - Bb4 - Ab4 - F4 - - - Eb4 - F4 -",
    "Ab4 - - - F4 - Db4 - - - F4 - Ab4 - C5 - Bb4 - - - - - - - G4 - Bb4 - Db5 - C5 -",
    "C5 - - - - - Ab4 - G4 - F4 - Eb4 - F4 - - - - - - - - - . . . . . . . .",
    ". . Db4 - F4 - Ab4 - C5 - - - Bb4 - Ab4 - G4 - - - - - - - - - - - . . . .",
]


def sax_line(bar, line, amp=1.0, pan=.58, vel=.9):
    t0, y = sax(notes(bar, line, bars=2), vel)
    S.put("lead", t0, y, pan, .32 * amp, wet=.35, echo=.18)


# ---------------------------------------------------------------- rain, thunder and a sonar ping
def rain(seconds):
    """Stereo: rain on the window, heard from inside: a soft wash, and drops that tick on the glass."""
    n = int(seconds * e.SR)
    out = np.zeros((n, 2))
    for ch in range(2):
        wash = e.lowpass(e.highpass(e.rng.standard_normal(n), 300), 3500) * .03
        wash *= 1 + .3 * np.sin(2 * np.pi * np.arange(n) / e.SR / (7.3 + ch))     # gusts
        drops = np.zeros(n)
        k = e.rng.integers(0, n, int(seconds * 22))
        drops[k] = e.rng.uniform(.2, 1, len(k)) ** 3 * e.rng.choice([-1, 1], len(k))
        drops = e.bandpass(drops, 1800, 4500) * 2.5              # through the glass: no sharp highs
        out[:, ch] = wash + drops
    return out


def thunder(seconds=7.0, a=1.0):
    t = e.tt(seconds)
    g = e.lowpass(np.cumsum(e.rng.standard_normal(len(t))) * .02, 180)   # brown noise, far away
    g = e.highpass(g, 25)
    env = np.minimum(t / 1.2, 1) * np.exp(-np.maximum(t - 1.2, 0) * .8) * (1 + .5 * np.sin(2 * np.pi * 1.3 * t))
    return g / (np.abs(g).max() + 1e-9) * env * a


def ping(m=77, a=1.0):
    """A sonar ping on the key's own F, a soft sine that rings."""
    t = e.tt(2.5)
    g = np.sin(2 * np.pi * float(e.hz(m)) * t) + .15 * np.sin(2 * np.pi * float(e.hz(m)) * 2.01 * t)
    return g * e.rise(t, .003) * np.exp(-t * 2.2) * a


# ---------------------------------------------------------------- the voices
# the verse, a line every two bars, on eighths, in his register; she sings it an octave up.
# The words are spelled as the voice should say them, a syllable per word; "+" holds a syllable over one more note.
VERSE_TUNE = [
    ". C3 Eb3 F3 - F3 Eb3 F3 - Ab3 - F3 - - . .",
    ". Db3 Db3 C3 Db3 - F3 - Eb3 - - - Db3 - . .",
    ". C3 Eb3 F3 F3 Eb3 - Ab3 - - - F3 - - . .",
    ". Db3 Db3 C3 Bb2 - C3 - Eb3 - - - - - . .",
]
VERSE_HIM = ["I sent you all my feel + ings", "in tie nee lit tull + parts", "but sum of them got lost girl",
             "sum wear bee tween our hearts"]
VERSE_HER = ["I on lee got the hed ur +", "I on lee got your name +", "ree trans mit it bay bee +",
             "say it once uh gen +"]

# the chorus, a line a bar on sixteenths, in her register; he sings the hook an octave under her
HOOK = [("F4 - F4 - Ab4 - - - F4 - Eb4 - - - - .", "pack it loss of love"),          # Dbmaj9
        ("Eb4 - Eb4 - G4 - - - Eb4 - C4 - - - - .", "pack it loss of love")]         # Cm7
ANSWER = [(". . Eb4 - Eb4 - Eb4 - Db4 - Eb4 - F4 - - .", "say it once uh gen +"),     # Eb9
          (". . C4 - C4 - C4 - Ab3 - Bb3 - C4 - - .", "say it once uh gen +")]        # Fm9
PING_ME = (". . F4 - F4 - Ab4 - Ab4 - Bb4 - Ab4 - - .", "ping me when your red dee")
WAITING = (". . Eb4 - F4 - G4 - - - F4 - Eb4 - - .", "I'll bee way ting up")
WAITING_DB = (". . Eb4 - F4 - Ab4 - - - F4 - Eb4 - - .", "I'll bee way ting up")    # over Dbmaj9
if LEM:   # Lem says a short first word on an eighth after a rest badly ("ping" came out "think", "I'll" "help"):
    # it starts on the downbeat and lasts a quarter; the rest of the line stays where it was
    PING_ME = ("F4 - - - F4 - Ab4 - Ab4 - Bb4 - Ab4 - - .", PING_ME[1])
    WAITING = ("Eb4 - - - F4 - G4 - - - F4 - Eb4 - - .", WAITING[1])
    WAITING_DB = ("Eb4 - - - F4 - Ab4 - - - F4 - Eb4 - - .", WAITING_DB[1])
LAST = ("F4 - F4 - Ab4 - - - F4 - Db4 - - - - - C4 - - - - - - - . . . . . . . .", "pack it loss of love +")

# the same words as Lem reads them: real English, one word over its notes ("+" holds it over one more)
DS_WORDS = {
    "I sent you all my feel + ings": "I sent you all my feelings + +",
    "in tie nee lit tull + parts": "in tiny + little + + parts",
    "but sum of them got lost girl": "but some of them got lost girl",
    "sum wear bee tween our hearts": "some where between + our hearts",
    "I on lee got the hed ur +": "I only + got the + header +",
    "I on lee got your name +": "I only + got your name +",
    "ree trans mit it bay bee +": "retransmit + + it + baby +",
    "say it once uh gen +": "say it once again + +",           # the answer; in the verse "a gain +" (below)
    "pack it loss of love": "pack it loss of love",
    "pack it loss of love +": "pack it loss of love +",
    "ping me when your red dee": "ping me when you're ready +",
    "I'll bee way ting up": "I'll be waiting + up",
}


def words_on(ns, words):
    """Pair words with notes: a word takes its note and one more for each "+" after it (sung as one word)."""
    out, toks, i = [], words.split(), 0
    for k, w in enumerate(toks):
        if w == "+":
            continue
        span = 1
        while k + span < len(toks) and toks[k + span] == "+":
            span += 1
        out.append((w, ns[i:i + span]))
        i += span
    assert i == len(ns), (words, len(ns))
    return out


def lossy(y, seed, p=.3):
    """Packet loss: the audio cut in 30 ms packets, and some of them never arrive (a 3 ms fade at each edge)."""
    r = np.random.default_rng(seed)
    pk = int(.03 * e.SR)
    mask = np.repeat((r.random(len(y) // pk + 1) > p).astype(float), pk)[:len(y)]
    mask[:pk] = 1.0                                 # the first packet always arrives: you hear who it is
    return y * e.one_pole(mask, .003)


def scale_third_below(m):
    """The note two steps down the F minor scale (F G Ab Bb C Db Eb): the choir's harmony under the tune."""
    scale = {5, 7, 8, 10, 0, 1, 3}
    for down in (3, 4):
        if (m - down) % 12 in scale:
            return m - down
    return m - 3


def sing(bar, line, words, who, octave=0, bars=1, amp=1.0, pan=.5, loss=0.0, echo_last=.3, cents=0.0,
         ds_words=None):
    """One voice sings a line: each word on its notes, the consonants just before the beat, an echo on the last
    word. loss > 0: some packets of the voice get lost. Singer D: the line goes into his or her Lem take (centre,
    one voice; octave is from the written pitch, as for Piper; ds_words: Lem's words, by default DS_WORDS)."""
    if LEM:
        P = SINGER[who]
        n = len(P.ds_lines)
        P.diva(bar, line, words, bars=bars, octave=octave - 12, amp=amp, ds_words=ds_words or DS_WORDS.get(words, words))
        if len(P.ds_lines) > n:           # live in the PREVIEW window: the echo on the last word as asked
            P.ds_lines[-1] = P.ds_lines[-1][:4] + (echo_last,)
            if loss:
                LOSSY.append((S.at(bar), S.at(bar + bars)))
        return
    pairs = words_on(notes(bar, line, bars), words)
    for i, (w, ns) in enumerate(pairs):
        last = i == len(pairs) - 1
        li, y = V.sing(w, [(m + octave, d * .96) for _, m, d in ns], voice=who, cents=cents)
        if loss:
            y = lossy(y, bar * 100 + i, loss)
        S.put("vox", ns[0][0] - li, y, pan, amp, wet=.15, echo=echo_last if last else .04)


def duet(bar, line, words, loss=0.0, bars=1, amp=1.0):
    """Both of them on the hook: her on the tune, him an octave under, a little to each side. Singer D: her
    alone (sparse, one voice at a time)."""
    sing(bar, line, words, HER, 0, bars, amp, .56, loss)
    if not LEM:
        sing(bar, line, words, HIM, -12, bars, .8 * amp, .44, loss, cents=-4)


def choir(bar, line, words, amp=1.0):
    """The answer: five other voices, women on the tune and a third under it, men an octave down. Singer D: him
    alone, at the written pitch (Ab3-F4), no choir."""
    if LEM:
        sing(bar, line, words, HIM, 0, amp=amp)
        return
    ns = notes(bar, line)
    # the first voice sings the words; the others only the vowels, on its vowel onsets, so the consonants of five
    # different speakers do not smear
    parts = [(CHOIR[0], 0, False, 6, .010, .2, .55), (CHOIR[1], 0, True, -6, .018, .8, .5),
             (CHOIR[2], 0, False, 0, .022, .5, .4), (CHOIR[3], -12, False, -8, .014, .35, .45),
             (CHOIR[4], -12, True, 8, .02, .65, .4)]
    for voice, octave, third, cents, late, pan, g in parts:
        words_first = voice == CHOIR[0]
        for w, wn in words_on(ns, words):
            tune = [((scale_third_below(m) if third else m) + octave, d * .94) for _, m, d in wn]
            if words_first:
                li, y = V.sing(w, tune, voice=voice, cents=cents)
                S.put("vox", wn[0][0] - li + late, y, pan, .55 * amp * g, wet=.3, echo=.05)
            else:
                _, y = V.sing(w, tune, voice=voice, cents=cents, vibrato=.15, vowel_only=True)
                S.put("vox", wn[0][0] + late, y, pan, .25 * amp * g, wet=.3, echo=.05)   # under the words


def say(bar, beat, text, who, seconds, amp=1.0, pan=.5, phone=False, wet=.2, echo=.25):
    """A spoken line (V.rap fits it to the length). phone=True: thin, like a voice in a terminal, and on the fx
    bus, so the break's closed filter does not muffle it."""
    if LEM and who in (HER, HIM):        # the acks in the singers' own voices (spoken)
        who = HER_TIMBRE if who == HER else HIM_TIMBRE
    y = V.rap(text, seconds, voice=who, pitch=1.0)
    if phone:
        y = e.bandpass(y, 350, 3400) * 1.6
    S.put("fx" if phone else "vox", S.at(bar, beat), y, pan, amp, wet=wet, echo=echo)


def chorus(bar0, loss=0.0):
    """Eight bars: the hook and the answer twice, then him, her, and the hook to close."""
    for half in (0, 2):
        duet(bar0 + half, *HOOK[half // 2], loss=loss)
        choir(bar0 + half + 1, *ANSWER[half // 2])
    sing(bar0 + 4, *PING_ME, HIM, -12, pan=.42, loss=loss)
    sing(bar0 + 5, *WAITING, HER, 0, pan=.58, loss=loss)
    duet(bar0 + 6, *LAST, loss=loss, bars=2)
    S.put("fx", S.at(bar0 + 7, 2), ping(72, .12), .3, wet=.3, echo=.5)     # on C, over the C7


# ---------------------------------------------------------------- the arrangement
for bar in range(120):
    if not S.live(bar, 2):          # PREVIEW: only the bars that can be heard (a sax line lasts two)
        continue
    intro, outro = bar < 16, bar >= 104
    brk = 64 <= bar < 72
    cho = chorus_bar(bar)
    if intro:
        drums(bar, clap=bar >= 8, shaker=bar >= 8, congas=bar >= 12, crash=bar == 0)
    elif outro:
        drums(bar, clap=bar < 116, shaker=bar < 112, congas=bar < 108, crash=bar == 104)
    elif brk:
        drums(bar, kick=False, clap=bar >= 68, hats=bar >= 66, shaker=True, amp=.65)
    else:
        drums(bar, shaker=True, congas=True, rimshots=24 <= bar < 40 or bar >= 88,
              crash=bar in (24, 40, 56, 72, 88))

    if 16 <= bar < 104 and not brk:
        bass(bar, .6 if bar < 20 else 1.0)
    if bar in (70, 71):
        bass(bar, .5)
    if 16 <= bar < 24:
        ep_comp(bar, .85, cut=700 + (bar - 16) * 450)       # the door opens
    if (24 <= bar < 40) or (56 <= bar < 72) or (88 <= bar < 104):
        ep_comp(bar, .8 if brk else 1.0)
    if cho:
        gospel_piano(bar)
    if 24 <= bar < 96:
        pads(bar, 1.3 if brk else (.8 if bar < 40 else 1.0), cut=2000 if brk else 1300)

    # the sax: the solo, and a few lines when it all winds down
    if 56 <= bar < 72 and bar % 2 == 0:
        sax_line(bar, SOLO[(bar - 56) // 2], .75 if brk else 1.0)
    if bar in (90, 94, 98):
        sax_line(bar, SOLO[{90: 0, 94: 2, 98: 6}[bar]], .6, pan=.62, vel=.75)
    if bar in (78, 86):     # an answer from the sax at the end of each chorus block
        sax_line(bar, ". . . . . . . . . . . . . . . . . . . . . . . . C5 Bb4 Ab4 - G4 - E4 -", .5, vel=.7)

# the verses: him, then her, a line every two bars; the other one acknowledges
for i in range(4):
    sing(24 + 2 * i, VERSE_TUNE[i], VERSE_HIM[i], HIM, 0, bars=2, pan=.46)
    sing(32 + 2 * i, VERSE_TUNE[i], VERSE_HER[i], HER, 12, bars=2, pan=.54,
         ds_words="say it once a gain +" if i == 3 else None)   # "again + +" here: "Sape on soggy" (Whisper)
say(27, 2.5, "Ack.", HER, .35, .7, pan=.7)
say(31, 2.5, "Nack!", HER, .4, .8, pan=.7)
say(33, 2.5, "Ack.", HIM, .35, .7, pan=.3)
say(39, 2.5, "Ack, ack.", HIM, .6, .7, pan=.3)

# the choruses; the second one drops packets in its second half
chorus(40)
chorus(48)
chorus(72)
chorus(80, loss=.3)

# the break: the computer reads out the ping, the sonar answers
say(64, 0, "Sixty four bytes from your heart. Time: one hundred twenty two milliseconds.", COMPUTER, 2 * S.bar - B,
    .8, phone=True, wet=.3, echo=.15)
say(68, 0, "Packet loss: fifty percent.", COMPUTER, S.bar, .8, phone=True, wet=.3, echo=.3)
for bar in (64, 66, 68, 70):
    S.put("fx", S.at(bar, 3), ping(77, .14), .65, wet=.4, echo=.5)

# winding down: the two of them, far apart now
for bar in (88, 92):
    sing(bar, *PING_ME, HIM, -12, pan=.4, echo_last=.45)
    sing(bar + 1, *WAITING_DB, HER, 0, pan=.6, echo_last=.45)
sing(96, *ANSWER[1], HER, 0, amp=.8, pan=.55, echo_last=.5)
say(100, 0, "Request timed out.", COMPUTER, S.bar * .75, .8, phone=True, wet=.3, echo=.4)
S.put("fx", S.at(101, 2), ping(77, .1), .5, wet=.4, echo=.6)

# rain all night (it comes in over the first bars and stops at the outro, a soft rumble in the break)
r = rain(S.length)
tsec = np.arange(len(r)) / e.SR
level = np.clip(tsec / S.at(4), 0, 1) * np.clip((S.at(110) - tsec) / S.at(6), 0, 1)
level *= 1 + .6 * ((tsec > S.at(64)) & (tsec < S.at(72)))
S.put("fx", 0, r * level[:, None], .5, 1.0, wet=0)
S.put("fx", S.at(64), thunder(8.0, .35), .4, wet=.2)
S.put("fx", S.at(70), e.riser(S.bar * 2, .2), .5, wet=.3)
S.put("fx", S.at(56), e.downlifter(S.bar * 2, .12), .5, wet=.3)

def packet_mask(t0, t1, seed, p=.3):
    """Packet loss for singer D's takes: 30 ms packets from t0 to t1, some never arrive; the packet at the start of
    each word always does (you hear who it is); 3 ms fades at the edges."""
    r = np.random.default_rng(seed)
    pk = int(.03 * e.SR)
    n = int((t1 - t0) * e.SR)
    m = np.repeat((r.random(n // pk + 1) > p).astype(float), pk)[:n]
    for P in SINGER.values():
        for t, _, _, w in P.ds_part.notes:
            if w != "+" and t0 <= t < t1:
                i = int((t - t0) * e.SR)
                m[max(0, i - pk):i + pk] = 1.0
    return e.one_pole(m, .003)


if LEM:   # both takes into the mix; the lines of the second chorus lose packets (dry, reverb send and echo alike)
    i0 = int(min((a for a, _ in LOSSY), default=0) * e.SR)
    i1 = int(max((b for _, b in LOSSY), default=0) * e.SR)
    before = [x[i0:i1].copy() for x in (S.bus["vox"], S.send, S.echo)]
    for P in SINGER.values():
        P.finish()
    if i1 > i0:
        mask = np.ones(i1 - i0)
        for k, (a, b) in enumerate(LOSSY):
            pm, j = packet_mask(a, b, 8000 + k), int(a * e.SR) - i0
            pm = pm[:len(mask) - j]
            mask[j:j + len(pm)] = pm
        for x, old in zip((S.bus["vox"], S.send, S.echo), before):
            x[i0:i1] = old + (x[i0:i1] - old) * mask[:, None]

cut = [(0, 18000), (S.at(64), 18000), (S.at(64) + .05, 1500), (S.at(70), 2600), (S.at(72) - .02, 9000),
       (S.at(72), 18000), (S.n / e.SR, 18000)]
here = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "renders", "packet-loss_122bpm_Fm.wav")
os.makedirs(os.path.dirname(out), exist_ok=True)
S.mixdown(out, {"drums": .85, "perc": .7, "bass": .78, "pads": 1.0, "keys": .9, "lead": 1.6, "vox": 2.0, "fx": .6},
          cut_keys=cut, duck={"pads": .5, "bass": .35, "keys": .2}, room=.22, echo_mix=.4, lufs=-10.0,
          ir=room.impulse_response((5.5, 4.0, 2.6), rt60=1.3))
