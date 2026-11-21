#!/usr/bin/env python3
"""Lego Op De Vloer: a children's choir song with cartoon violence, 126 BPM, C major, 4/4. Round two of the compo:
"Kinderen voor Kinderen kinderliedjes met komisch geweld" (Dutch children's choir songs, with comic violence).

lego_op_de_vloer.py [OUT.wav]   (default renders/lego-op-de-vloer_126bpm_C.wav)   PREVIEW=32-48: the first chorus

A child builds a Lego castle and leaves one brick on the stairs. Dad steps on it barefoot, hops down the hall,
grabs the cat; the cat flies into grandma's bath; grandma slips on a Lego car and rolls out of the front door, down
the street, into the bakery. Boom. Who left that brick there? "Not me!" Everyone shouts "OW!" in the chorus.

The band is ours, written here by Claude (no samples, no loops): a bright, full 80s/90s children's TV pop band
(the user on the first version: "rather sparse; this genre is children's music, it may be fuller, and happier"):
a pop beat (kick on 1 and 3, the snare on 2 and 4), a bouncy synth bass, an oom-pah piano, warm strings, a toy
glockenspiel with the hook (it answers the verse lines and plays along in the chorus), synth horns, a tambourine
and hand claps in the chorus, and cartoon sound effects where the story hurts: a slide whistle when the
cat flies, a splash, a crash and an orchestra hit on "boem". C - G - Am - F, a chord a bar.

The singers are ACE-Step takes, a cappella, played whole over the band (the way that works, WEEKEND.md): a
children's choir sings the chorus, one child the verses, in Dutch. takes.py makes the drafts, the ear picks,
takes.pin puts them in renders/ace/takes/lego_op_de_vloer/pinned/ (chorus.wav: 16 bars; verse.wav: the three verses,
8 bars each). The bridge's shouts are Piper's Dutch voices: dad, and the kids pitched up.

  bars   0-15  intro: drums only (for the DJ)
        16-19  the band: the glockenspiel plays the hook
        20-27  verse 1 (the castle, the brick on the stairs)
        28-43  chorus: "Lego op de vloer! AU!"
        44-51  verse 2 (dad, the cat, grandma's bath): a slide whistle, a splash
        52-67  chorus
        68-71  bridge: no kick; dad: "Wie heeft dat daar neergelegd?" the kids: "Niet ik!" ... "Het was de kat!"
        72-79  verse 3 (grandma rolls to the bakery): "boem!", a crash and an orchestra hit
        80-95  the last chorus
        96-111 outro: drums only (for the DJ)
3:33 (the theme: "about 3.5 minutes").
"""
import os

import numpy as np

import dx7
import engine as e
import parts
import room
import voice as V

# ---------------------------------------------------------------- the knobs
TITLE = "Lego Op De Vloer"
DAY = "Round two: Kinderen voor Kinderen"
BPM, BARS = 126, 112
KEY = "C"
PROG = ["C", "G", "Am", "F"]
LUFS = -10.0
TAKE_GAIN = float(os.environ.get("TAKE_GAIN", "1.0"))
DAD = "nl_NL-pim-medium"                 # Pim (Piper): the user: "die is leuk"
KIDS = ["nl_BE-nathalie-medium", "nl_NL-alex-medium", "nl_NL-ronnie-medium"]

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.basename(__file__)[:-3]
NAME = f"{SCRIPT.replace('_', '-')}_{BPM}bpm_{KEY}"
PINNED = os.path.join(HERE, "renders", "ace", "takes", SCRIPT, "pinned")

# ACE_SONG=<wav> (gag.py's whole ACE-Step song, on the beat grid): ACE-Step's band and children's choir together
# (the user: "a really good prompt for ACE?"). DJ_ENDS=1 puts our 16 bars of drums before it and after it; off for
# this round (the user: "no drum intro and outro, that does not work anyway")
# the pick (the user, 23:25: "this one is quite good", then "but shorter is better"): the CFG 7 take, seed 3, cut
# after "Nee!"; ACE_SONG= (empty) renders our own band with the pinned takes instead
ACE_SONG = os.environ.get("ACE_SONG", os.path.join(HERE, "renders", "ace", "gags", "lego-op-de-vloer-seed3",
                                                   "Lego Op De Vloer (seed 3).wav"))
ACE_GAIN = float(os.environ.get("ACE_GAIN", "1.0"))
ACE_X = None
if ACE_SONG:
    import master
    BPM = int(os.environ.get("ACE_BPM", "132"))           # the wild version (gag.py --bpm 132)
    NAME = f"{SCRIPT.replace('_', '-')}_{BPM}bpm_{KEY}"
    ACE_X, _ = master.read(ACE_SONG)
    loud = np.nonzero(np.abs(ACE_X).max(1) > 10 ** (-50 / 20))[0]
    ACE_X = ACE_X[:loud[-1] + 1]
    ACE_BARS = int(np.ceil(len(ACE_X) / (240 / BPM * e.SR)))
    if os.environ.get("ACE_CUT", "75"):   # end after this bar: the take ends in 80 s of "ho ho" and "la la"
        ACE_BARS = min(ACE_BARS, int(os.environ.get("ACE_CUT", "75")))
        ACE_X = ACE_X[:int(ACE_BARS * 240 / BPM * e.SR)]
        ACE_BARS += 1                   # one more bar: our "BOEM" ends it (an orchestra hit and a crash on C)
    DJ = 16 if os.environ.get("DJ_ENDS") == "1" else 0
    BARS = DJ + ACE_BARS + DJ

e.seed(BPM)
S = e.Song(bpm=BPM, bars=BARS)
STEP, B = S.step, S.beat


def chord_of(bar):
    return PROG[bar % 4]


# A DX7 toy glockenspiel (Blinky's patch): two carriers, each with a hard metal modulator, keyboard-scaled
dx7.PATCHES.setdefault("toy_glock", dict(algo=5, feedback=0, gain=.5, ops=[
    dx7.op(1, 0, 0, 99, (99, 32, 25, 45), (99, 70, 0, 0), vel=.5),
    dx7.op(3, 50, 0, 70, (99, 45, 25, 45), (99, 40, 0, 0), vel=.8, ks=6),
    dx7.op(4, 0, 2, 80, (99, 40, 25, 45), (99, 60, 0, 0), vel=.5),
    dx7.op(1, 0, 0, 62, (99, 60, 25, 45), (99, 30, 0, 0), vel=.9, ks=6),
    dx7.op(1, 0, -2, 0, (99, 50, 20, 50), (99, 0, 0, 0)),
    dx7.op(1, 0, 0, 0, (99, 50, 20, 50), (99, 0, 0, 0)),
]))


# ---------------------------------------------------------------- drums: a children's TV pop beat
def drums(bar, kick=True, snare=True, hats=True, crash=False, fill=False, amp=1.0):
    if not S.live(bar):
        return
    t0 = S.at(bar)
    if kick:
        for beat in (0, 1.5, 2):                  # 1, the "and" of 2, 3
            S.kick(t0 + beat * B, .9 * amp, punch=110, base=50, length=.3, click=.3)
    if snare:
        for b in (1, 3):
            S.put("drums", t0 + b * B, e.snare(.42 * amp), .5, wet=.25)
            S.put("drums", t0 + b * B, e.clap(.18 * amp), .5, wet=.25)
    if hats:
        for k in range(8):
            S.put("perc", t0 + k * B / 2, e.hat((.24 if k % 2 == 0 else .16) * amp), .6, wet=.05)
    if fill:                                       # the last two beats: eighths on the snare, louder
        for k in range(4):
            S.put("drums", t0 + 2 * B + k * B / 2, e.snare((.25 + .08 * k) * amp), .5, wet=.25)
    if crash:
        S.put("perc", t0, e.crash(.35 * amp), .5, wet=.3)


if ACE_X is not None:
    for bar in range(BARS if DJ else 0):
        if bar < DJ:
            drums(bar, snare=bar >= 4, crash=bar == 0, fill=bar == DJ - 1)
        elif bar >= DJ + ACE_BARS:
            drums(bar, crash=bar == DJ + ACE_BARS)
    f = int((240 / BPM / 2 if os.environ.get("ACE_CUT", "75") else .5) * e.SR)     # a cut ends in a half-bar fade
    x = ACE_X.copy()
    x[-f:] *= np.linspace(1, 0, f)[:, None]
    S.put("keys", S.at(DJ), x, amp=ACE_GAIN, wet=0)
    if os.environ.get("ACE_CUT", "75"):
        t = S.at(DJ) + len(x) / e.SR
        S.put("fx", t, e.orch_hit(e.close_voicing("C", lo=55, hi=72), 1.0), .5, wet=.5)
        S.put("perc", t, e.crash(.5), .5, wet=.3)
        S.kick(t, 1.0, punch=140, base=40, length=.6, click=.5)
    S.mixdown(parts.out_path(NAME), {"drums": .9, "perc": .7, "keys": 1.0, "fx": .8}, room=.1, lufs=LUFS)
    print(f"share.SONGS row: (\"{NAME}.wav\", \"{TITLE}\", \"{DAY}\", {BPM}, \"{KEY}\", {BARS}),")
    raise SystemExit


# ---------------------------------------------------------------- the band
def bass(bar, amp=1.0):
    """A bouncy synth bass on the eighths: root, root, octave, root, fifth, root, octave, fifth."""
    if not S.live(bar):
        return
    root = e.root_note(chord_of(bar), lo=36)
    for k, iv in enumerate((0, 0, 12, 0, 7, 0, 12, 7)):
        S.put("bass", S.at(bar) + k * B / 2, e.bass_note(root + iv, B / 2 * .8, cut=1300, decay=4), .5, .7 * amp,
              wet=0)


def piano(bar, amp=1.0, full=False):
    """A bouncy piano: the low root on the beats, the chord on the offbeats (oom-pah); full: the chord on every
    eighth (the chorus)."""
    if not S.live(bar):
        return
    notes = e.close_voicing(chord_of(bar), lo=55, hi=69)
    root = e.root_note(chord_of(bar), lo=43)
    for k in range(8):
        t = S.at(bar) + k * B / 2
        if k % 2 == 0 and not full:
            S.put("keys", t, e.piano(root, B * .4, .7), .4, .35 * amp, wet=.15)
        else:
            for j, m in enumerate(notes):
                S.put("keys", t + j * .003, e.piano(m, B * .35, .62 if k % 2 else .7), .45 + .1 * (j % 2),
                      .26 * amp, wet=.18)


def pad(bar, amp=1.0):
    """Warm strings under it all, a bar long."""
    if not S.live(bar):
        return
    S.put("pads", S.at(bar), e.pad(e.close_voicing(chord_of(bar), lo=60, hi=76), S.bar, cut=2600, a=.25, r=.6),
          amp=.32 * amp, wet=.35)


def brass(bar, amp=1.0):
    """Synth brass stabs: on 1 and on the "and" of 2, bright and short (the children's TV band's horns)."""
    if not S.live(bar):
        return
    notes = e.close_voicing(chord_of(bar), lo=60, hi=74)
    for beat, d in ((0, .28), (1.5, .2)):
        g = e.supersaw(notes, d, spread=.15, voices=5, a=.008, r=.08, cut=3800)
        S.put("lead", S.at(bar, beat), g, .5, .3 * amp, wet=.2, echo=.05)


def tambourine(bar, amp=1.0):
    if not S.live(bar):
        return
    for k in range(8):
        S.put("perc", S.at(bar) + k * B / 2, e.shaker((.3 if k % 2 else .18) * amp), .35, wet=.1)
    for b in (1, 3):                                  # hand claps on the backbeat
        S.put("perc", S.at(bar, b) + .006, e.clap(.3 * amp), .62, wet=.3)


# the hook on the glockenspiel: two bars, played twice (sixteenth tokens; C major)
HOOK = ["E5 - - - G5 - - - E5 - - - D5 - C5 -", "D5 - - - B4 - - - C5 - - - - - . .",
        "E5 - - - G5 - - - A5 - G5 - E5 - - -", "D5 - - - E5 - D5 - C5 - - - - - . ."]


def glock(bar, amp=1.0):
    if not S.live(bar):
        return
    for t, m, d in S.notes(bar, HOOK[bar % 4]):
        S.put("lead", t, dx7.note("toy_glock", m, min(d, B), .8, tail=.6), .6, .35 * amp, wet=.3, echo=.12)


# ---------------------------------------------------------------- cartoon sounds
def whistle(m0, m1, d):
    """A party slide whistle (Blinky's): a sine sliding from one note to the other, a wobble, a breath."""
    t = e.tt(d)
    u = t / d
    m = m0 + (m1 - m0) * (3 * u ** 2 - 2 * u ** 3) + .25 * np.sin(2 * np.pi * 6 * t) * u
    f = e.hz(m)
    breath = e.highpass(e.lowpass(e.rng.standard_normal(len(t)), 3500), 900) * .06
    g = e.sine(f, t, 0.0) + .1 * e.sine(2 * f, t, 0.0) + breath
    return g * e.rise(t, .03) * np.minimum((d - t) / .05, 1) * .4


def splash(a=1.0):
    """Water: a noise burst, filtered, that falls away, with a few drops after it."""
    t = e.tt(1.2)
    n = e.rng.standard_normal(len(t))
    body = e.bandpass(n, 300, 3000) * np.exp(-t * 5)
    drops = sum(np.sin(2 * np.pi * (900 + 400 * k) * t) * np.exp(-((t - .25 - .15 * k) * 60) ** 2) for k in range(4))
    return (body * .5 + drops * .15) * a


def boom(bar, beat=0.0):
    S.put("fx", S.at(bar, beat), e.orch_hit(e.close_voicing(chord_of(bar), lo=55, hi=72), .9), .5, wet=.5)
    S.put("perc", S.at(bar, beat), e.crash(.45), .5, wet=.3)
    S.kick(S.at(bar, beat), 1.0, punch=140, base=40, length=.6, click=.5)


# ---------------------------------------------------------------- the singers: ACE-Step takes, whole
def take(name):
    import takes
    path = os.path.join(PINNED, f"{name}.wav")
    if not os.path.exists(path):
        return None
    x = e.bandpass(takes.mono(path), 120, 11000)
    return x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * .1 * TAKE_GAIN


def cut_at_quiet(x, n):
    """x cut near sample n: at its quietest 50 ms in the half bar before n, with a short fade."""
    if len(x) <= n:
        return x
    a, w = max(0, n - int(S.bar / 2 * e.SR)), int(.05 * e.SR)
    env = np.convolve(np.abs(x[a:n]), np.ones(w) / w, "valid")
    c = a + int(np.argmin(env)) + w // 2 if len(env) else n
    x = x[:c].copy()
    f = min(int(.06 * e.SR), len(x))
    x[len(x) - f:] *= np.linspace(1, 0, f)
    return x


def sing(name, bar, b0=0, bars=16, amp=1.0, wet=.2):
    """Bars b0 to b0 + bars of a pinned take, from the downbeat of `bar` (the slice starts at its quietest point
    in the half bar before b0, so a pickup note comes along)."""
    x = TAKES.get(name)
    if x is None or not S.live(bar, bars):
        return
    s0 = int(b0 * S.bar * e.SR)
    lead = 0
    if b0:
        a, w = max(0, s0 - int(S.bar / 2 * e.SR)), int(.05 * e.SR)
        env = np.convolve(np.abs(x[a:s0]), np.ones(w) / w, "valid")
        lead = s0 - (a + int(np.argmin(env)) + w // 2) if len(env) else 0
    y = cut_at_quiet(x[s0 - lead:], lead + int(bars * S.bar * e.SR))
    f = min(int(.02 * e.SR), len(y))
    y = y.copy()
    y[:f] *= np.linspace(0, 1, f)
    S.put("vox", S.at(bar) - lead / e.SR, y, .5, amp, wet=wet, echo=.08)


TAKES = {n: take(n) for n in ("chorus", "verse")}
# the verse take's first line starts this many bars in (fit.py: "two bars earlier")
VERSE_AT = int(os.environ.get("VERSE_AT", "2"))


def shout(bar, beat, text, voice, beats, pitch=1.0, amp=1.0, pan=.5):
    """A shouted line fitted to `beats`, pitched (1.45: an adult Piper voice as a child)."""
    if not S.live(bar):
        return
    y = V.rap(text, beats * B, voice=voice, pitch=pitch)
    y = y * (.14 / (np.sqrt(np.mean(y ** 2)) + 1e-9))
    S.put("vox", S.at(bar, beat), y, pan, amp, wet=.15, echo=.1)


# ---------------------------------------------------------------- the arrangement
for bar in range(BARS):
    intro, outro = bar < 16, bar >= 96
    bridge = 68 <= bar < 72
    chorus = 28 <= bar < 44 or 52 <= bar < 68 or 80 <= bar < 96
    if intro:
        drums(bar, snare=bar >= 4, crash=bar == 0, fill=bar == 15)
    elif outro:
        drums(bar, crash=bar == 96)
    elif bridge:
        drums(bar, kick=False, snare=bar >= 70, hats=bar >= 69, amp=.7, fill=bar == 71)
    else:
        drums(bar, crash=bar in (16, 28, 52, 80), fill=bar in (27, 51))

    if 16 <= bar < 96 and not bridge:
        bass(bar, 1.1 if chorus else 1.0)
        piano(bar, .9 if chorus else 1.0, full=chorus)
        pad(bar, 1.0 if chorus else .6)
    if chorus:                    # the chorus is the party: horns, tambourine and claps, the glockenspiel along
        brass(bar)
        tambourine(bar)
        glock(bar, .5)
    if bridge:
        piano(bar, .6)
        pad(bar, .8)
    if 16 <= bar < 20 or 70 <= bar < 72:
        glock(bar)
    if 20 <= bar < 28 or 44 <= bar < 52 or 72 <= bar < 80:      # the verses: the glockenspiel answers each line
        if bar % 2 == 1:
            glock(bar, .6)

sing("verse", 20, VERSE_AT, 8)
sing("chorus", 28)
sing("verse", 44, VERSE_AT + 8, 8)
sing("chorus", 52)
sing("verse", 72, VERSE_AT + 16, 8)
sing("chorus", 80)

# the story's cartoon sounds
S.put("fx", S.at(49, 2), whistle(72, 91, 1.1), .7, .55, wet=.3)          # the cat flies
S.put("fx", S.at(51, 2.5), splash(.9), .5, wet=.35)                     # into grandma's bath
S.put("fx", S.at(77, 0), whistle(84, 64, 1.6), .3, .45, wet=.3)         # grandma rolls down the street
boom(79, 2)                                                             # into the bakery

# the bridge: who left that there?
shout(68, 0, "Wie heeft dat daar neergelegd?", DAD, 5, pitch=.95, amp=1.1)
for i, v in enumerate(KIDS):
    shout(70, i * 1.0, "Niet ik!", v, .9, pitch=1.45, pan=.3 + .2 * i)
for i, v in enumerate(KIDS):
    shout(71, 0, "Het was de kat!", v, 2, pitch=1.45, amp=.8, pan=.3 + .2 * i)
S.put("fx", S.at(71, 2.5), whistle(86, 79, .35), .6, .4, wet=.3)        # the cat, offended

S.mixdown(parts.out_path(NAME), {"drums": .9, "perc": .7, "bass": .85, "pads": .8, "keys": .9, "lead": .9,
                                 "vox": 1.4, "fx": .7},
          room=.18, echo_mix=.3, lufs=LUFS, ir=room.impulse_response((6.0, 5.0, 3.0), rt60=1.0))
print(f"share.SONGS row: (\"{NAME}.wav\", \"{TITLE}\", \"{DAY}\", {BPM}, \"{KEY}\", {BARS}),")
