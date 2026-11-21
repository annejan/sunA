#!/usr/bin/env python3
"""Segfault (In My Heart): eurodance, 132 BPM, A minor (and B minor after the key change). Sunday's theme of
the AI slop music compo.

segfault.py [OUT.wav]   (default renders/segfault_132bpm_Am.wav)
DIVA=en_US-hfc_female-medium segfault.py OUT.wav    the old Piper diva with her Piper choir (the approved render)
DS_TIMBRE= DS_STACK= DS_HARMONY= SOLO=vox PREVIEW=48-56 segfault.py    shape the melody with Lem alone (fast)

Every note and every sound here is written by Claude, in this file: no samples, no loops. 1994 on a Sunday: a
supersaw riff, a rave piano, an offbeat bass, orchestra hits, an AI diva (Piper and WORLD, voice.py) with a choir
of other voices, and a rapper who spells it out. The key change is two semitones up, for the last chorus. The first and last 16
bars are drums only, for the DJ.

  bars   0-15  intro: kick, hats, clap (drums only)
        16-23  the riff, behind a closing door that opens; the bass comes in
        24-39  verse: the rave piano and the pad; the diva sings, the rapper spells S-E-G-F-A-U-L-T
        40-47  pre-chorus: the kick holds back, a snare roll and a riser
        48-63  chorus: "segfault in my heart, tearing me apart; segfault in my heart, reboot from the start"
        64-71  break: the riff alone, filtered; "signal eleven"
        72-79  build
        80-95  the last chorus, a tone up
        96-111 outro: drums only

The diva is singer D (DIVA=ds:lem, the default since 21 November): parts.Band's produced singer. Lem the
Shapeshifter DS 2.5 sings the written melody and words an octave below the Piper diva's written line (the chorus
A3-G4, B3-A4 after the key change; Lem's realistic range is A2-D5), SoulX-Singer SVC turns the take into the Qwen
diva's voice. In the chorus and the pre-chorus: doubles from takes 2 and 3 in the Qwen pop and Maya pop voices, a
soft octave and a vocoder, and a harmony a third above (Maya soul) instead of the Piper choir. The verse is her
alone. The rapper and the robot's "signal eleven" stay as they were.
"""
import os
import sys

import numpy as np

import engine as e
import parts
import voice as V

e.seed(1994)
S = e.Song(bpm=132, bars=112)
STEP = S.step
B = S.beat

PROG = ["Am", "F", "C", "G"]


def key_of(bar):
    return 2 if 80 <= bar < 96 else 0


def chord_of(bar):
    return PROG[bar % 4]


# ---------------------------------------------------------------- drums
def drums(bar, kick=True, clap=True, hats=True, open_hats=True, crash=False, amp=1.0):
    t0 = S.at(bar)
    if kick:
        for b in range(4):
            S.kick(t0 + b * B, 1.0 * amp, punch=130, base=50, length=.34, click=.4)
    if clap:
        for b in (1, 3):
            S.put("drums", t0 + b * B, e.clap(.6 * amp), .5, wet=.2)
            S.put("drums", t0 + b * B, e.snare(.45 * amp), .5, wet=.25)
    if hats:
        for k in range(16):
            if k % 4 == 2 and open_hats:
                S.put("perc", t0 + k * STEP, e.hat(.6 * amp, opened=True), .55, wet=.08)
            elif k % 4 != 2:
                S.put("perc", t0 + k * STEP, e.hat((.3 if k % 2 else .18) * amp), .65, wet=.04)
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


# ---------------------------------------------------------------- bass
def bass(bar, amp=1.0):
    """The offbeat bass: between the kicks, an octave jump at the end of the bar."""
    root = e.root_note(chord_of(bar), key_of(bar), lo=33)
    for k in (2, 6, 10, 14):
        S.put("bass", S.at(bar) + k * STEP, e.bass_note(root + (12 if k == 14 else 0), STEP * 1.6, cut=1100, decay=3),
              .5, .9 * amp, wet=0)
    S.put("bass", S.at(bar) + 15 * STEP, e.bass_note(root + 12, STEP * .8, cut=1100, decay=3), .5, .5 * amp, wet=0)


# ---------------------------------------------------------------- the riff, the piano, the pad
RIFF_STEPS = (0, 3, 6, 8, 10, 12, 14)


def riff(bar, amp=1.0, cut=6000):
    notes = e.close_voicing(chord_of(bar), key_of(bar), lo=67, hi=81)
    for k in RIFF_STEPS:
        d = STEP * (1.5 if k in (0, 6) else 1)
        S.put("lead", S.at(bar) + k * STEP, e.supersaw(notes, d, spread=.25, a=.003, r=.12, cut=cut),
              amp=.55 * amp, wet=.2, echo=.15)


STABS = (0, 3, 6, 10, 12)


def piano(bar, amp=1.0):
    notes = e.close_voicing(chord_of(bar), key_of(bar), lo=60, hi=76)
    for k in STABS:
        for j, m in enumerate(notes):
            S.put("keys", S.at(bar) + k * STEP + j * .003, e.piano(m, STEP * 2, .9), .4 + .1 * j, .3 * amp, wet=.25)


def pads(bar, amp=1.0, cut=2500):
    notes = e.voicing(chord_of(bar), key_of(bar), lo=55)
    S.put("pads", S.at(bar), e.pad(notes, S.bar, cut=cut, a=.3, r=.6), amp=.45 * amp, wet=.4)


def orch(bar, amp=1.0):
    S.put("fx", S.at(bar), e.orch_hit(e.close_voicing(chord_of(bar), key_of(bar), lo=57, hi=72), amp), wet=.5)


# ---------------------------------------------------------------- the chorus: a melody and its words
CHORUS = [
    ("E5 - E5 - - - D5 - C5 - E5 - - - - -", "segfault + in my heart"),
    ("F5 - E5 - C5 - A4 - C5 - - - - - - .", "tearing + me apart +"),
    ("E5 - G5 - - - E5 - D5 - C5 - - - - -", "segfault + in my heart"),
    ("D5 - D5 - - - B4 - C5 - D5 - - - - .", "reboot + from the start"),
]
# the verse, a line every two bars, on eighths (the words as the voice should say them, one per note)
VERSE = [
    (". C5 C5 C5 B4 C5 D5 E5 - D5 C5 - - . . .", "you told me you'd be there for ev er"),
    (". C5 C5 C5 B4 C5 D5 E5 - G5 E5 - D5 - . .", "you told me we were kum piled to geth er"),
    (". E5 E5 E5 D5 - C5 - D5 C5 - A4 - - . .", "but now I'm reed ding mem oh ree"),
    (". G4 A4 - C5 . C5 D5 - E5 - D5 - - - .", "that duz unt bee long to me"),
]
PRE = [("E5 - - - E5 - - - G5 - - - - - - -", "oh oh oh"),
       (". . E5 D5 C5 - D5 - E5 - - - . . . .", "sum things go wing wrong")]
RAP = ["S! E! G! F! A! U! L! T!",
       "You overflowed the buffer that you gave to me.",
       "Null pointer, no answer, the stack is on fire.",
       "I free the same love twice, I'm a double free liar.",
       "Check the bounds, check the bounds, but you never do.",
       "Val grind in the morning, it was always you.",
       "Get up, get down, get the back trace now!",
       "Seg fault, seg fault, let me show you how!"]
WORDS = {"seg": ("s", ["e"], "g"), "fault": ("f", ["o", "l"], "t"), "in": ("", ["i", "n"], ""),
         "my": ("", ["m", "ah", "i"], ""), "heart": ("h", ["ah", "r"], "t"), "tear": ("t", ["e", "r"], ""),
         "ing": ("", ["i", "n"], ""), "me": ("", ["m", "i"], ""), "a": ("", ["ah"], ""),
         "part": ("p", ["ah", "r"], "t"), "re": ("", ["r", "i"], ""), "boot": ("b", ["u"], "t"),
         "from": ("f", ["r", "ah", "m"], ""), "the": ("d", ["ah"], ""), "start": ("s", ["ah", "r"], "t"),
         "sig": ("s", ["i"], "g"), "nal": ("", ["n", "ah", "l"], ""), "e": ("", ["i"], ""), "lev": ("", ["l", "e"], ""),
         "en": ("", ["ah", "n"], ""), "oh": ("", ["o", "u"], "")}


def sing_notes(notes, words, octave=-12, amp=1.0, wet=.3, echo=.2):
    """The robot sings each word on its own note, at the note's own time (so rests stay rests)."""
    for (t, m, d), w in zip(notes, words.split()):
        onset, vowels, coda = WORDS[w]
        S.sing(t, [(onset, vowels, m + octave, d, coda)], amp=amp, wet=wet, echo=echo)


CHORUS_STYLE = os.environ.get("CHORUS_STYLE", "choir")   # octave | doubles | harmony | choir
# the choir: other voices around the diva. Left double, right double, a third above; and in the last chorus a man
# an octave down and one more a sixth down
CHOIR = os.environ.get("CHOIR", ",".join([
    "en_US-ljspeech-high", "en_US-kristin-medium", "en_GB-cori-high",
    "en_US-hfc_male-medium", "festival:cmu_us_slt_cg"])).split(",")


def third_above(m, key):
    """The note two steps up the (natural minor) scale of the key: a diatonic third."""
    scale = sorted((pc + 9 + key) % 12 for pc in (0, 2, 3, 5, 7, 8, 10))
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


# DIVA=ds:hanami (or the Piper default): the old diva, below. DIVA=ds:lem (the default): singer D (sing(), further down)
DIVA = os.environ.get("DIVA", "ds:lem")
SINGER_D = DIVA == "ds:lem"
# DIVA=ds:hanami: a DiffSinger voicebank sings the diva's part (ds.py), at the written pitch, in one take. The
# words as written for it (real words, "+" holds a word over the next note; the lines above are spelled for Piper)
DS = not SINGER_D and V.DIVA.startswith("ds:")
DS_PART = None
DS_GAIN = []                 # (from, to, amp) per line
DS_TEXT = {
    "you told me you'd be there for ev er": "you told me you'd be there for ever +",
    "you told me we were kum piled to geth er": "you told me we were compiled + together + +",
    "but now I'm reed ding mem oh ree": "but now I'm reading + memory + +",
    "that duz unt bee long to me": "that doesn't + belong + to me",
    "sum things go wing wrong": "something's + going + wrong",
}
if DS:
    import ds
    DS_PART = ds.Part(S.bpm)


def diva(bar, line, words, octave=-12, bars=1, amp=1.0, double=0.0, key=None, style="octave", big=False):
    """The diva sings a line: a word on its notes, the consonants before the beat; an echo on the last word.
    double: how loud the stack is. style "octave": an octave up, left and right (one take, offset); "doubles": two
    more takes of the same notes, a little out of time and tune, left and right; "harmony": those two takes and a
    third above in the middle; "choir": other voices (CHOIR) for the doubles and the third, and with big=True a man
    an octave down and a sixth down as well."""
    key = key_of(bar) if key is None else key
    pairs = words_on(S.notes(bar, line, key, bars), words)
    if DS:   # the lead: DiffSinger, an octave above the Piper diva (the written pitch); the choir stays below
        for w, ns in words_on(S.notes(bar, line, key, bars), DS_TEXT.get(words, words)):
            for k, (t, m, d) in enumerate(ns):
                DS_PART.note(t, m + octave + 12, d * .97, w if k == 0 else "+")
        DS_GAIN.append((S.at(bar), S.at(bar + bars), amp))
    for i, (w, ns) in enumerate(pairs):
        last = i == len(pairs) - 1
        t = ns[0][0]
        if not DS:
            li, y = V.sing(w, [(m + octave, d * .97) for _, m, d in ns])
            S.put("vox", t - li, y, .5, amp, wet=.12, echo=.35 if last else .05)
        if not double:
            continue
        if style == "choir":
            notes = [(m + octave, d * .95) for _, m, d in ns]
            third = [(third_above(m, key) + octave, d * .95) for _, m, d in ns]
            parts = [(CHOIR[0], notes, 8, .018, .15, .75), (CHOIR[1], notes, -8, .009, .85, .75),
                     (CHOIR[2], third, 0, .006, .4, .6)]
            if big:
                parts += [(CHOIR[3], [(n - 12, d) for n, d in notes], 0, .012, .55, .7),
                          (CHOIR[4], [(n - 12, d) for n, d in third], 5, .015, .7, .45)]
            for voice, ns2, cents, late, pan, g in parts:   # vowels only: the diva's consonants stay clean
                _, y = V.sing(w, ns2, voice=voice, cents=cents, vibrato=.15, vowel_only=True)
                S.put("vox", t + late, y, pan, amp * double * g, wet=.15, echo=.05)
            continue
        if style == "octave":
            li, y = V.sing(w, [(m + octave + 12, d * .97) for _, m, d in ns], formant=1.08)
            S.put("vox", t - li, y, .25, amp * double, wet=.15, echo=.05)
            S.put("vox", t - li + .012, y, .75, amp * double, wet=.15, echo=.05)
            continue
        for take, cents, late, pan in ((1, 8, .018, .2), (2, -8, .009, .8)):
            li, y = V.sing(w, [(m + octave, d * .95) for _, m, d in ns], take=take, cents=cents)
            S.put("vox", t - li + late, y, pan, amp * double * .8, wet=.15, echo=.05)
        if style == "harmony":
            li, y = V.sing(w, [(third_above(m, key) + octave, d * .95) for _, m, d in ns], take=3)
            S.put("vox", t - li + .006, y, .5, amp * double * .7, wet=.2, echo=.08)


# ---------------------------------------------------------------- singer D: Lem, converted and stacked
TIMBRE = "qwen_diva"                   # the lead's voice (the Badge's)
STACK = "sing_qwen_pop,sing_maya_pop,octave,vocoder"
HARMONY = "sing_maya_soul"
ACCENT = {"seg": 3, "fault": 3}        # the hook word
D_OCTAVE = -24                         # an octave below the Piper diva's written line: steady notes C4-E4 (D4-F#4
                                       # after the key change), nothing above A4; the written pitch reached G5-A5
D_TEXT = dict(DS_TEXT, **{"segfault + in my heart": "seg fault in my heart"})   # the words as DiffSinger reads them
# singer D's rhythm where the Piper line slurs (Whisper on Lem alone): "seg" on an eighth came out "sick" or "tick",
# now a dotted eighth; a sixteenth rest after "heart" so "tearing" starts clean (it was "staying"); "there" a quarter
# and "for" an eighth ("be there forever" was "be the fiver")
D_LINE = {CHORUS[0][0]: "E5 - - E5 - - D5 - C5 - E5 - - - - .",
          CHORUS[2][0]: "E5 - - G5 - - E5 - D5 - C5 - - - - .",
          VERSE[0][0]: ". C5 C5 C5 B4 C5 D5 - E5 D5 C5 - - . . ."}
P = None
if SINGER_D:
    P = parts.Band(S, PROG, scale="minor", key_of=key_of, tonic="A", diva_voice=DIVA, timbre=TIMBRE, stack=STACK,
                   harmony=HARMONY, accent=ACCENT, verse_double=0.0)
    P.knobs["cons"] = "1"   # Lem's consonants under the Qwen diva: "reboot" heard 2 of 2 (without: "free boot")


def sing(bar, line, words, bars=1, amp=1.0, dbl=0.0, harm=0.0, echo=.35, octave=D_OCTAVE):
    """Singer D sings a line (Lem's one take, parts.Band). dbl: the doubles' level (0: her alone; octave and vocoder
    follow it); harm: a harmony a third above at amp * harm (below when above would pass D5); echo: the last word
    into the delay."""
    if not S.live(bar, bars):
        return
    ds_words = D_TEXT.get(words)
    line = D_LINE.get(line, line)
    P.diva(bar, line, words, bars=bars, octave=octave, amp=amp, ds_words=ds_words)
    t0, t1, a, last, _ = P.ds_lines[-1]
    P.ds_lines[-1] = (t0, t1, a, last, echo)
    P.ds_double[-1] = (t0, t1, dbl)
    if harm:
        key = key_of(bar)
        pairs = parts.words_on(S.notes(bar, line, key, bars), ds_words or words)
        up = max(P.step_up(m, 2, key) for _, ns in pairs for _, m, _ in ns) + octave + 12 <= 74
        for w, ns in pairs:
            for k, (t, m, d) in enumerate(ns):
                h = (P.step_up if up else P.step_down)(m, 2, key) + octave + 12
                P.ds_harm.note(t, h, d * .97, w if k == 0 else "+")
        P.ds_choir.append((t0, t1, amp * harm))


def chorus_line(bar, lead_amp=1.0):
    line, words = CHORUS[bar % 4]
    if SINGER_D:
        sing(bar, line, words, dbl=.55, harm=.6 if bar >= 80 else .5)
    else:
        diva(bar, line, words, double=.37, style=CHORUS_STYLE, big=bar >= 80)
    if SINGER_D:
        line = D_LINE.get(line, line)
    for t, m, d in S.notes(bar, line, key_of(bar)):   # the riff synth doubles the hook, under the voice
        S.put("lead", t, e.lead(m, d * .95), amp=.16 * lead_amp, wet=.3, echo=.2)


SPELL = ["S!", "E!", "G!", "F!", "A!", "U!", "L!", "T!"]   # one letter each, shouted: eSpeak reads them right
SPELL_RHYTHM = [(0, 1.8), (2, 1.8), (4, 1.8), (6, 1.8), (8, .95), (9, .95), (10, 1.8), (12, 3.5)]   # sixteenths:
# S . E . G . F . A U L . T - - -  (A-U on one beat: a chant, not the alphabet song)


def rapper(bar, text, bars=1, amp=1.0):
    """A rap line, from the downbeat, fitted to the bar (a sixteenth short, to breathe). The spelled line goes letter
    by letter on the SPELL_RHYTHM grid: a whole line squeezed into a bar turns to mush."""
    if text == RAP[0]:
        for letter, (k, n) in zip(SPELL, SPELL_RHYTHM):
            y = V.rap(letter, STEP * n)
            last = letter == SPELL[-1]
            S.put("vox", S.at(bar) + k * STEP, y, .5, amp * (1.15 if k == 0 or last else 1.0), wet=.06,
                  echo=.12 if last else .02)
        return
    y = V.rap(text, bars * S.bar - STEP)
    S.put("vox", S.at(bar), y, .5, amp, wet=.06, echo=.04)


def signal_eleven(bar):
    line = "A4 - - - A4 - - - . . E5 - C5 - A4 - - - - - - - - - . . . . . . . ."
    words = "sig nal e lev en"
    sing_notes(S.notes(bar, line, bars=2), words, -12, 1.1, wet=.4, echo=.45)


# ---------------------------------------------------------------- the arrangement
for bar in range(112):
    intro, outro = bar < 16, bar >= 96
    chorus = 48 <= bar < 64 or 80 <= bar < 96
    brk = 64 <= bar < 72
    build = 72 <= bar < 80
    pre = 40 <= bar < 48

    if intro:
        drums(bar, clap=bar >= 8, open_hats=bar >= 4, crash=bar == 0)
    elif outro:
        drums(bar, clap=bar < 108, open_hats=bar < 104, crash=bar == 96)
    elif brk:
        drums(bar, kick=False, clap=False, hats=bar >= 68, open_hats=False, amp=.8)
    elif build:
        drums(bar, kick=bar < 76, clap=False, open_hats=False, amp=.9)
    elif pre:
        drums(bar, kick=bar < 44, clap=bar < 44, open_hats=False)
    else:
        drums(bar, crash=bar in (24, 48, 80))

    if 16 <= bar < 24:
        riff(bar, .9, cut=500 * 1.3 ** (bar - 16))
    if (20 <= bar < 40) or chorus:
        bass(bar, .7 if bar < 24 else 1.0)
    if pre:
        bass(bar, .8) if bar < 44 else None
    if 24 <= bar < 48 or chorus:
        piano(bar, .8 if chorus else 1.0)
    if 24 <= bar < 96 and not brk:
        pads(bar, 1.3 if pre or build else 1.0)
    if chorus:
        riff(bar)
    if brk:
        riff(bar, .9, cut=1200 + 300 * (bar - 64))
        pads(bar, .8, cut=1500)
    if build:
        riff(bar, .8, cut=2000 + 600 * (bar - 72))

    # orchestra hits on the downbeats that matter
    if bar in (16, 24, 48, 56, 80, 88):
        orch(bar)

    # the voices: the diva's verse, the rap, the pre-chorus, the chorus; the robot in the break
    if 24 <= bar < 32 and bar % 2 == 0:
        if SINGER_D:
            sing(bar, *VERSE[(bar - 24) // 2], bars=2, amp=.9)
        else:
            diva(bar, *VERSE[(bar - 24) // 2], bars=2, amp=.9)
    if 32 <= bar < 40:
        rapper(bar, RAP[bar - 32])
    if bar in (42, 46) and SINGER_D:
        sing(bar, *PRE[0], dbl=.55, harm=.5)
        sing(bar + 1, *PRE[1], dbl=.55, harm=.5)
    elif bar in (42, 46):
        diva(bar, *PRE[0], octave=-12, double=.27, style=CHORUS_STYLE)
        diva(bar + 1, *PRE[1], octave=-12, double=.2, style=CHORUS_STYLE)
    if chorus:
        chorus_line(bar, 1.2 if bar >= 80 else 1.0)
    if brk and bar % 4 == 0:
        signal_eleven(bar)
    if build and bar in (72, 73, 74, 75):
        rapper(bar, RAP[[0, 6, 0, 7][bar - 72]], amp=1.1)

if DS:   # the whole diva part in one take, each line at its own level
    y = DS_PART.render(bank=V.DIVA.split(":", 1)[1], voice=os.environ.get("DS_VOICE", "Fragrance"),
                       pitch=os.environ.get("DS_PITCH", "0.5"),
                       seed=int(os.environ.get("DS_SEED", "1")), timbre=os.environ.get("DS_TIMBRE"))
    # DS_PITCH: hard | free | 0..1 (see ds.py), 0.5: half her own scoops; DS_SEED: another take of the same score;
    # DS_TIMBRE: another singer for the same performance (a voice.CAST name: maya_diva, qwen_diva; ds.convert)
    g = np.ones(len(y))
    for t0, t1, a in DS_GAIN:
        g[int(t0 * e.SR):int(t1 * e.SR)] = a
    S.put("vox", 0.0, y * g, .5, 1.0, wet=.12, echo=.12)

if SINGER_D:
    P.finish()          # singer D's whole part: Lem's take, converted, stacked

snare_roll(44, 4)
snare_roll(76, 4, 1.1)
S.put("fx", S.at(44), e.riser(S.bar * 4, .35), .5, wet=.3)
S.put("fx", S.at(76), e.riser(S.bar * 4, .4), .5, wet=.3)
S.put("fx", S.at(64), e.downlifter(S.bar * 2, .3), .5, wet=.3)
S.put("fx", S.at(96), e.downlifter(S.bar * 2, .25), .5, wet=.3)

cut = [(0, 18000), (S.at(64), 18000), (S.at(64) + .05, 2500), (S.at(72), 2500), (S.at(80) - .02, 12000),
       (S.at(80), 18000), (S.n / e.SR, 18000)]
here = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "renders", "segfault_132bpm_Am.wav")
os.makedirs(os.path.dirname(out), exist_ok=True)
S.mixdown(out, {"drums": .95, "perc": .7, "bass": .85, "pads": .8, "keys": 1.0, "lead": 1.0, "vox": 1.4, "fx": .55},
          cut_keys=cut, duck={"pads": .7, "bass": .3, "keys": .3, "lead": .35}, room=.2, echo_mix=.4, lufs=-9.0)
