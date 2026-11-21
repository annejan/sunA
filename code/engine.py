"""A small song engine: buses, instruments, drums, a vocoder robot and a mixdown with a master chain.

Taken from qtpass-world-v2/audio.py and made free of the film: a Song has its own tempo and length, and
writes a 44.1 kHz 16-bit stereo WAV that a DJ can beat-match (the tempo is exact, the grid starts at 0).
"""
import math
import os
import re
import wave

import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter1d, minimum_filter1d

SR = 44100
rng = np.random.default_rng(1)


def seed(n):
    global rng
    rng = np.random.default_rng(n)


# ---------------------------------------------------------------- filters
def lowpass(x, f, order=2):
    b, a = signal.butter(order, min(f, SR * .45) / (SR / 2))
    return signal.lfilter(b, a, x, axis=0)


def highpass(x, f, order=2):
    b, a = signal.butter(order, f / (SR / 2), btype="high")
    return signal.lfilter(b, a, x, axis=0)


def bandpass(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), min(hi, SR / 2.1) / (SR / 2)], btype="band")
    return signal.lfilter(b, a, x, axis=0)


def rbj_lowpass(fc, q):
    w = 2 * math.pi * min(max(fc, 20.0), SR * .45) / SR
    alpha, c = math.sin(w) / (2 * q), math.cos(w)
    b = np.array([(1 - c) / 2, 1 - c, (1 - c) / 2])
    a = np.array([1 + alpha, -2 * c, 1 - alpha])
    return b / a[0], a / a[0]


def sweep(x, cutoff, q=.707, block=128):
    """A lowpass whose cutoff (Hz, one per sample) moves: biquads block by block, the state carried over."""
    y = np.empty_like(x)
    zi = np.zeros(2)
    for i in range(0, len(x), block):
        b, a = rbj_lowpass(cutoff[i], q)
        y[i:i + block], zi = signal.lfilter(b, a, x[i:i + block], zi=zi)
    return y


def one_pole(x, seconds):
    a = math.exp(-1 / (seconds * SR))
    return signal.lfilter([1 - a], [1, -a], x)


# ---------------------------------------------------------------- time and envelopes
def hz(m):
    return 440.0 * 2 ** ((np.asarray(m) - 69) / 12)


def tt(d):
    return np.arange(max(int(d * SR), 1)) / SR


def rise(t, a):
    return np.minimum(t / a, 1.0)


def gate(t, d, rel):
    """1 for d seconds, then an exponential release of rel seconds."""
    return np.where(t < d, 1.0, np.exp(-np.maximum(t - d, 0) / rel))


# ---------------------------------------------------------------- oscillators
def phase(f, n, p0=None):
    inc = (np.full(n, float(f)) if np.ndim(f) == 0 else np.asarray(f, dtype=float)) / SR
    return (rng.random() if p0 is None else p0) + np.cumsum(inc), inc


def saw(f, t, p0=None):
    """A band-limited saw (polyBLEP); f in Hz, a number or one per sample."""
    ph, dt = phase(f, len(t), p0)
    ph %= 1.0
    s = 2 * ph - 1
    m = ph < dt
    x = ph[m] / dt[m]
    s[m] -= 2 * x - x * x - 1
    m = ph > 1 - dt
    x = (ph[m] - 1) / dt[m]
    s[m] -= x * x + 2 * x + 1
    return s


def pulse(f, t, duty=.5):
    p0 = rng.random()
    return saw(f, t, p0) - saw(f, t, (p0 + duty) % 1.0)


def sine(f, t, p0=None):
    ph, _ = phase(f, len(t), p0)
    return np.sin(2 * np.pi * ph)


# ---------------------------------------------------------------- instruments (mono unless noted)
def supersaw(notes, d, spread=.22, voices=7, a=.02, r=.25, cut=5000):
    """Stereo: a stack of detuned saws for every note, odd voices left, even right; low-passed."""
    t = tt(d + r)
    out = np.zeros((len(t), 2))
    for m in notes:
        for v in range(voices):
            det = (v / (voices - 1) - .5) * 2 * spread
            s = saw(hz(m + det), t) * (1.0 if v == voices // 2 else .75)
            side = v % 2
            out[:, 0] += s * (1 - side * .6)
            out[:, 1] += s * (.4 + side * .6)
    out = lowpass(out, cut) / (voices * max(len(notes), 1)) * 2.2
    return out * (rise(t, a) * gate(t, d, r / 3))[:, None]


def pluck(m, d, cut=6000, voices=5):
    """A trance pluck: detuned saws through a filter that closes fast."""
    t = tt(d + .25)
    g = sum(saw(hz(m + (v / (voices - 1) - .5) * .25), t) for v in range(voices)) / voices
    g = sweep(g, cut * np.exp(-t * 14) + 300, .9, 64)
    return g * rise(t, .002) * np.exp(-t * 6) * gate(t, d, .06) * 1.4


def lead(m, d, cut=7000):
    """Stereo: a bright supersaw lead, an octave under it, a slow vibrato."""
    t = tt(d + .2)
    vib = .12 * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - .2) / .3, 0, 1)
    out = np.zeros((len(t), 2))
    for v in range(7):
        out[:, v % 2] += saw(hz(m + (v / 6 - .5) * .3 + vib), t)
    out += saw(hz(m - 12 + vib), t)[:, None] * .5
    out = lowpass(out, cut) / 5
    return out * (rise(t, .01) * gate(t, d, .08))[:, None]


def piano(m, d=.5, vel=1.0):
    """A rave piano: bright, a little out of tune with itself, a hammer on every note."""
    f = float(hz(m))
    t = tt(min(d, 1.6) + .35)
    g = np.zeros_like(t)
    for n in range(1, 14):
        fn = f * n * math.sqrt(1 + .0004 * n * n)
        if fn > SR / 2.3:
            break
        a = vel ** (.4 + .08 * n) / n ** 1.05
        p = rng.uniform(0, 6.3)
        g += a * (np.sin(2 * np.pi * fn * t + p) + .5 * np.sin(2 * np.pi * fn * 1.002 * t + p)) * np.exp(-t * (1.4 + .5 * n))
    hammer = bandpass(rng.standard_normal(len(t)), 900, 5000) * np.exp(-t * 180) * .25
    return (g * .5 + hammer) * gate(t, d, .07) * rise(t, .001)


def organ(m, d=.12):
    """The M1 organ: a bright, punchy stab."""
    f = float(hz(m))
    t = tt(d + .08)
    g = sum(a * np.sin(2 * np.pi * f * r * t) for r, a in ((.5, .6), (1, 1), (2, .8), (3, .5), (4, .45), (6, .2), (8, .15))
            if f * r < SR / 2.3)
    click = bandpass(rng.standard_normal(len(t)), 2000, 8000) * np.exp(-t * 600) * .4
    return (g * np.exp(-t * 7) + click) * gate(t, d, .02) * .45


def rhodes(m, d=.6, vel=.8):
    """An FM electric piano: a tine that barks when hit hard, a soft body under it."""
    f = float(hz(m))
    t = tt(d + .9)
    bark = (1.0 + 2.2 * vel) * np.exp(-t * 9)
    tine = np.sin(2 * np.pi * f * t + bark * np.sin(2 * np.pi * f * t))
    body = np.sin(2 * np.pi * f * t + .4 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 2))
    high = .12 * vel * np.sin(2 * np.pi * f * 7.1 * t) * np.exp(-t * 30)
    g = (.55 * tine + .6 * body + high) * np.exp(-t * (1.1 + f / 2000))
    return g * gate(t, d, .18) * rise(t, .002) * .5 * (.5 + .5 * vel)


def pad(notes, d, cut=1800, a=.8, r=1.2):
    """Stereo: a slow string pad, a supersaw with the edges off, breathing in and out."""
    return supersaw(notes, d, spread=.12, voices=5, a=a, r=r, cut=cut)


def vox(m, d, vowel="a"):
    """A sung 'ah', 'oh' or 'oo', from formants."""
    t = tt(d + .2)
    src = saw(hz(m) * (1 + .006 * np.sin(2 * np.pi * 5.5 * t)), t)
    formants = {"a": ((800, 1.0, 90), (1150, .5, 100), (2900, .25, 150)),
                "o": ((450, 1.0, 70), (800, .45, 90), (2830, .1, 140)),
                "u": ((325, 1.0, 60), (700, .3, 80), (2530, .08, 140))}[vowel]
    g = sum(a * bandpass(src, f - bw, f + bw) for f, a, bw in formants)
    return g * rise(t, .03) * gate(t, d, .08) * 3


def bass_note(m, d, cut=900, sub=.8, decay=1.5):
    """Saw and sub, plucked."""
    t = tt(d + .04)
    g = saw(hz(m), t) * .6 + sine(hz(m), t) * sub
    g = sweep(g, cut * (1 + 2 * np.exp(-t * 25)), .8, 64)
    return g * rise(t, .002) * gate(t, d, .02) * np.exp(-t * decay)


def deep_bass(m, d):
    """A round deep-house bass: mostly sine, a little warmth on top, a soft pluck."""
    t = tt(d + .06)
    g = sine(hz(m), t) + .25 * np.tanh(3 * sine(hz(m), t)) + .12 * lowpass(saw(hz(m), t), 500)
    return g * rise(t, .004) * gate(t, d, .04) * (.7 + .3 * np.exp(-t * 8))


def orch_hit(notes, a=1.0):
    """Stereo: the 1990s orchestra hit, brass and strings and a timpani all at once."""
    t = tt(.7)
    out = np.zeros((len(t), 2))
    for m in notes:
        for v in range(4):
            s = saw(hz(m + (v - 1.5) * .08), t) + .5 * saw(hz(m + 12), t)
            out[:, v % 2] += s
    out = lowpass(out, 5000) / (4 * len(notes))
    timp = np.sin(2 * np.pi * np.cumsum(hz(notes[0] - 24) * (1 + .3 * np.exp(-t * 30))) / SR) * .8
    out += timp[:, None]
    return out * (np.exp(-t * 5) * rise(t, .002))[:, None] * a


# ---------------------------------------------------------------- drums
def kick(a=1.0, punch=110, base=48, length=.38, click=.35):
    t = tt(length)
    ph = np.cumsum(base + punch * np.exp(-t * 28)) / SR
    g = np.sin(2 * np.pi * ph) * np.exp(-t * 10) + bandpass(rng.standard_normal(len(t)), 1500, 6000) * np.exp(-t * 500) * click
    return np.tanh(g * 1.1) * a


METAL = (205.3, 304.4, 369.6, 522.7, 540.0, 800.0)   # the 808's cymbal, six squares


def hat(a=1.0, opened=False):
    t = tt(.32 if opened else .06)
    g = sum(np.sign(np.sin(2 * np.pi * f * 1.7 * t)) for f in METAL) / 6 + rng.standard_normal(len(t)) * .5
    return lowpass(highpass(g, 7500), 13000) * np.exp(-t * (11 if opened else 75)) * a * 1.1


def shaker(a=1.0):
    t = tt(.09)
    env = np.minimum(t / .02, 1) * np.exp(-np.maximum(t - .02, 0) * 60)
    return bandpass(rng.standard_normal(len(t)), 5000, 11000) * env * a * .7


def clap(a=1.0):
    t = tt(.3)
    env = sum((t >= o) * np.exp(-np.maximum(t - o, 0) * 140) for o in (0, .009, .019))
    env = env + (t >= .027) * np.exp(-np.maximum(t - .027, 0) * 17) * .7
    return bandpass(rng.standard_normal(len(t)), 900, 5500) * env * a * .9


def snare(a=1.0):
    t = tt(.22)
    return (bandpass(rng.standard_normal(len(t)), 1200, 8000) * np.exp(-t * 20) * 1.2
            + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 28) * .6) * a


def rim(a=1.0):
    t = tt(.08)
    g = np.sin(2 * np.pi * 1700 * t) * .6 + np.sin(2 * np.pi * 460 * t) + bandpass(rng.standard_normal(len(t)), 2000, 7000) * .4
    return g * np.exp(-t * 70) * a * .6


def conga(m, a=1.0):
    t = tt(.3)
    f = hz(m) * (1 + .5 * np.exp(-t * 60))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14) * a


def crash(a=1.0):
    t = tt(2.8)
    g = highpass(rng.standard_normal(len(t)) + sum(np.sign(np.sin(2 * np.pi * f * 2.3 * t)) for f in METAL) * .1, 3500)
    return g * np.exp(-t * 1.4) * a * .5


def riser(d, a=1.0):
    """White noise climbing to the drop, and a saw climbing with it."""
    t = tt(d)
    u = t / d
    g = sweep(rng.standard_normal(len(t)), 300 * 40 ** u, 2.0, 256) * u ** 2
    g += saw(hz(48 + 24 * u ** 1.5), t) * .15 * u ** 2
    return g * a


def downlifter(d, a=1.0):
    t = tt(d)
    u = t / d
    return sweep(rng.standard_normal(len(t)), 9000 * .02 ** u + 200, 2.0, 256) * (1 - u) ** 2 * a


def crackle(d, a=1.0):
    """Vinyl: a soft hiss, a slow rumble and the pops of the dust."""
    n = int(d * SR)
    hiss = lowpass(highpass(rng.standard_normal(n), 3000), 9000) * .05
    pops = np.zeros(n)
    k = rng.integers(0, n, int(d * 9))
    pops[k] = rng.uniform(-1, 1, len(k)) * rng.uniform(.2, 1, len(k)) ** 3
    pops = highpass(lowpass(pops, 7000), 1200) * 2
    return (hiss + pops) * a


# ---------------------------------------------------------------- harmony
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
QUALITY = {"": (0, 4, 7), "m": (0, 3, 7), "7": (0, 4, 7, 10), "sus4": (0, 5, 7), "maj7": (0, 4, 7, 11),
           "m7": (0, 3, 7, 10), "6": (0, 4, 7, 9), "m9": (0, 3, 7, 10, 14), "maj9": (0, 4, 7, 11, 14),
           "m11": (0, 3, 7, 10, 14, 17), "add9": (0, 4, 7, 14), "9": (0, 4, 7, 10, 14)}


def midi(name):
    """"F#5" -> 78."""
    pc, i = PC[name[0]], 1
    if name[1] in "#b":
        pc, i = pc + (1 if name[1] == "#" else -1), 2
    return 12 * (int(name[i:]) + 1) + pc


def chord(name, key=0):
    i = 2 if len(name) > 1 and name[1] in "#b" else 1
    root = (PC[name[0]] + (1 if name[1:i] == "#" else -1 if name[1:i] == "b" else 0) + key) % 12
    return root, QUALITY[name[i:]]


def voicing(name, key=0, lo=57, drop_root=False):
    """The chord stacked up from the first root at or above lo (the root left out for a keys player's voicing)."""
    root, iv = chord(name, key)
    base = lo + (root - lo) % 12
    return [base + i for i in iv if not (drop_root and i == 0)]


def close_voicing(name, key=0, lo=59, hi=74):
    root, iv = chord(name, key)
    return sorted(m for m in range(lo, hi + 1) if (m - root) % 12 in {i % 12 for i in iv})[:len(iv)]


def root_note(name, key=0, lo=33):
    return lo + (chord(name, key)[0] - lo) % 12


# ---------------------------------------------------------------- the vocoder robot
VOWELS = {"a": (730, 1090, 2440), "e": (530, 1840, 2480), "i": (270, 2290, 3010), "u": (300, 870, 2240),
          "o": (570, 840, 2410), "ah": (660, 1200, 2550), "n": (250, 1700, 2600), "m": (250, 1000, 2200),
          "r": (450, 1200, 1600), "l": (360, 1100, 2600), "w": (300, 610, 2200)}
BURST = {"k": (1500, 4500, .03), "g": (1000, 3500, .025), "t": (3000, 9000, .02), "d": (2000, 6000, .018),
         "p": (200, 1500, .02), "b": (150, 1000, .018), "s": (4500, 11000, .09), "f": (1800, 8000, .07),
         "h": (500, 4000, .05), "sh": (2000, 6000, .09)}


def robot(syllables):
    """A vocoder robot singing: a saw on each syllable's note through the formants of its vowels (gliding from the
    first to the last), the consonants bursts of noise. syllables: (onset, vowels, note, seconds, coda);
    the vowels are a list of VOWELS keys. Returns (offset seconds, mono) pieces to put."""
    out = []
    t0 = 0.0
    for onset, vowels, note, d, coda in syllables:
        pre = BURST[onset][2] if onset else 0.0
        if onset:
            b = tt(BURST[onset][2])
            lo, hi, ln = BURST[onset]
            out.append((t0, bandpass(rng.standard_normal(len(b)), lo, hi) * np.exp(-b / ln * 2.5) * .5))
        n = tt(max(d - pre, .05))
        u = n / n[-1] if len(n) > 1 else n
        f = hz(note) * (1 + .004 * np.sin(2 * np.pi * 5.5 * n) * np.clip((n - .15) / .2, 0, 1))
        src = saw(f, n) + .35 * saw(f * 2, n) + .15 * rng.standard_normal(len(n))
        g = np.zeros_like(n)
        for j, v in enumerate(vowels):
            f1, f2, f3 = VOWELS[v]
            w = np.clip(1 - abs(u * (len(vowels) - 1) - j), 0, 1) if len(vowels) > 1 else np.ones_like(u)
            g += w * (bandpass(src, f1 * .85, f1 * 1.15) + .6 * bandpass(src, f2 * .9, f2 * 1.1)
                      + .3 * bandpass(src, f3 * .92, f3 * 1.08))
        g *= rise(n, .012) * gate(n, len(n) / SR * .88, .03) * 2.5
        out.append((t0 + pre, g))
        if coda:
            lo, hi, ln = BURST[coda]
            b = tt(ln)
            out.append((t0 + d * .86, bandpass(rng.standard_normal(len(b)), lo, hi) * np.exp(-b / ln * 2.5) * .45))
        t0 += d
    return out


# ---------------------------------------------------------------- loudness (ITU-R BS.1770) and true peak
def k_weight(x):
    """The K-weighting: a high shelf (+4 dB above about 1.7 kHz) and a high-pass at about 38 Hz."""
    g, fc, q = 3.999843853973347, 1681.974450955533, .7071752369554196
    A, w = 10 ** (g / 40), 2 * math.pi * fc / SR
    c, al = math.cos(w), math.sin(w) / (2 * q)
    b = [A * ((A + 1) + (A - 1) * c + 2 * math.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * c),
         A * ((A + 1) + (A - 1) * c - 2 * math.sqrt(A) * al)]
    a = [(A + 1) - (A - 1) * c + 2 * math.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * c),
         (A + 1) - (A - 1) * c - 2 * math.sqrt(A) * al]
    x = signal.lfilter(b, a, x, axis=0)
    fc, q = 38.13547087602444, .5003270373238773
    w = 2 * math.pi * fc / SR
    c, al = math.cos(w), math.sin(w) / (2 * q)
    return signal.lfilter([(1 + c) / 2, -(1 + c), (1 + c) / 2], [1 + al, -2 * c, 1 - al], x, axis=0)


def integrated_lufs(x):
    """Integrated loudness: 400 ms blocks, 75 % overlap, the absolute gate at -70 LUFS, the relative at -10 LU."""
    y = k_weight(x) ** 2
    n, hop = int(.4 * SR), int(.1 * SR)
    c = np.concatenate([np.zeros((1, y.shape[1])), np.cumsum(y, axis=0)])
    starts = np.arange(0, len(y) - n + 1, hop)
    z = ((c[starts + n] - c[starts]) / n).sum(1)
    z = z[-.691 + 10 * np.log10(z + 1e-12) > -70]
    rel = -.691 + 10 * np.log10(z.mean()) - 10
    z = z[-.691 + 10 * np.log10(z + 1e-12) > rel]
    return -.691 + 10 * np.log10(z.mean())


_TP_FIR = (signal.firwin(2 * 10 * 4 + 1, 1 / 4, window=("kaiser", 5.0)) * 4).astype(np.float32)   # resample_poly's own


def true_peak(x):
    """The peak of each sample's neighbourhood, 4 times oversampled (the peaks between the samples), both channels.
    The same filter as resample_poly(x, 4, 1), in float32, with the maxima taken column by column (fast)."""
    d = (len(_TP_FIR) - 1) // 2
    up = np.abs(signal.upfirdn(_TP_FIR, np.asarray(x, np.float32), 4, axis=0)[d:d + 4 * len(x)])
    m = np.maximum(up[:, 0], up[:, 1]).reshape(-1, 4)
    return np.maximum(np.maximum(m[:, 0], m[:, 1]), np.maximum(m[:, 2], m[:, 3])).astype(np.float64)


def limit(x, ceiling):
    """A look-ahead limiter on the true peak: the gain comes down 4 ms before a peak and goes back up slowly."""
    look = int(.004 * SR)
    tp = true_peak(x)
    if tp.max() <= ceiling:
        return x
    g = np.minimum(1.0, ceiling / np.maximum(tp, 1e-9))
    g = minimum_filter1d(g, 2 * look + 1)
    g = np.minimum(g, one_pole(g, .002))
    return x * g[:, None]


def peaking(x, f0, gain_db, q=1.0):
    """An RBJ peaking EQ."""
    A, w = 10 ** (gain_db / 40), 2 * np.pi * f0 / SR
    al = np.sin(w) / (2 * q)
    return signal.lfilter([1 + al * A, -2 * np.cos(w), 1 - al * A], [1 + al / A, -2 * np.cos(w), 1 - al / A], x, axis=0)


def compress(x, below_db=6.0, ratio=4.0, att=.002, rel=.06, knee=6.0):
    """A feed-forward compressor, stereo linked, its threshold `below_db` under the signal's loud level (the 95th
    percentile of its envelope while it sounds), so it works at any bus level; the output at the input's RMS."""
    lv = np.abs(x).max(1)
    a_, r_ = np.exp(-1 / (att * SR)), np.exp(-1 / (rel * SR))
    env = np.maximum(signal.lfilter([1 - r_], [1, -r_], lv), signal.lfilter([1 - a_], [1, -a_], lv))
    db = 20 * np.log10(env + 1e-9)
    loud = np.percentile(db[db > db.max() - 50], 95)
    over = db - (loud - below_db)
    gr = np.where(over > knee / 2, over, np.where(over > -knee / 2, (over + knee / 2) ** 2 / (2 * knee), 0))
    y = x * (10 ** (-gr * (1 - 1 / ratio) / 20))[:, None]
    return y * np.sqrt(np.mean(x ** 2) / (np.mean(y ** 2) + 1e-12))


def deess(x, lo=5500, thr=.35, depth_db=6.0):
    """Split-band de-esser: the band above `lo` turned down when it is a large share of the voice."""
    s = highpass(x, lo, 4)
    ls = np.sqrt(one_pole((s ** 2).mean(1), .005))
    lt = np.sqrt(one_pole((x ** 2).mean(1), .005)) + 1e-9
    g = 10 ** (-depth_db * np.clip((ls / lt - thr) / thr, 0, 1) / 20)
    return (x - s) + s * g[:, None]


def vocal_chain(v):
    """A 1995 vocal channel strip: the mud out (300 Hz -3 dB), a fast 1176-style compressor (4:1), presence (3 kHz
    +3 dB), a de-esser, an Aphex-style exciter (harmonics above 6 kHz: Piper's voices stop at 11 kHz), and a slow
    LA-2A-style leveler (2:1). Consonants and short words come up against the vowels. The output at the input's RMS."""
    if np.abs(v).max() == 0:
        return v
    rms0 = np.sqrt(np.mean(v ** 2))
    y = peaking(v, 300, -3, .8)
    y = compress(y, 6, 4, .002, .06)
    y = peaking(y, 3000, 3, .9)
    y = deess(y)
    h = highpass(y, 3000, 2)
    y = y + .12 * highpass(np.tanh(4 * h) / 4, 6000, 2)
    y = compress(y, 4, 2, .01, .25)
    return y * rms0 / (np.sqrt(np.mean(y ** 2)) + 1e-12)


def make_room(music, voice, depth_db=6.0, lo=250, hi=6000, nper=2048):
    """music ducked per STFT bin where the voice has energy, in the band lo..hi, by up to depth_db: the words come
    through, and between the lines nothing changes. The voice's power is smoothed over 9 bins (about a third of an
    octave at 1 kHz) and held with a 120 ms release; each bin is measured against its own loud level."""
    if np.abs(voice).max() == 0:
        return music
    hop = nper // 4
    f, _, V = signal.stft(voice.mean(1).astype(np.float32), SR, nperseg=nper, noverlap=nper - hop)
    P = signal.convolve2d(np.abs(V) ** 2, np.ones((9, 1), np.float32) / 9, mode="same").astype(np.float32)
    del V                                   # float32 throughout: a whole song's STFT is large
    rel = np.exp(-hop / SR / .12)
    S = np.empty_like(P)
    acc = np.zeros(P.shape[0])
    for k in range(P.shape[1]):
        acc = np.maximum(P[:, k], acc * rel)
        S[:, k] = acc
    db = 10 * np.log10(S + 1e-12)
    ref = np.percentile(db[:, db.max(0) > db.max() - 40], 98, axis=1, keepdims=True)
    m = np.clip((db - (ref - 30)) / 30, 0, 1)
    band = ((f >= lo) & (f <= hi)).astype(float)[:, None]
    g = (10 ** (-depth_db * m * band / 20)).astype(np.float32)
    del S, db, m
    out = np.zeros_like(music)
    for ch in range(2):
        _, _, X = signal.stft(music[:, ch].astype(np.float32), SR, nperseg=nper, noverlap=nper - hop)
        _, y = signal.istft(X * g[:, :X.shape[1]], SR, nperseg=nper, noverlap=nper - hop)
        out[:len(y), ch] = y[:len(music)]
    return out


# ---------------------------------------------------------------- the song
BUSES = ("drums", "perc", "bass", "pads", "keys", "lead", "vox", "fx")
MUTED = set(filter(None, os.environ.get("MUTE", "").split(",")))
# The switches that make a test render: it goes to renders/scratch/ with the switch in its name, and never replaces
# the song's render in renders/ (share.py, dj.py and produce.py would take it for the song). The A/B switches of
# 19 November are here too: a full CROWD=1 render overwrote nothing only by luck (the playbook check).
AB_VARS = ("PREVIEW", "SOLO", "MUTE", "GAIN", "AIR", "CAST", "CROWD", "CHOPS", "VAMP", "HARM", "SINGER", "NARRATORS",
           "DIVA_WAV", "DIVA_OFFSET", "DIVA_GAIN", "DS_WAV",
           # the songs' own voice and sound switches (their defaults are the approved renders; DIVA stays out: a
           # template song may pick its diva with it)
           "RAPPER", "SYSTEM", "MOUTH", "CHOIR", "CHORUS_STYLE", "KEYS", "ROOM", "GLITCH", "VOX_HUMAN", "VOXCHAIN",
           "UNMASK", "DS_VOICE", "DS_PITCH", "DS_SEED", "DS_TIMBRE", "DS_STACK", "DS_FLASH", "DS_ACCENT", "DS_HARMONY", "DS_TENSION", "DS_VIB", "DS_BREATH", "DS_DYN", "DS_COMP", "DS_COMP_TAKES", "DS_GAIN", "DS_CONS", "DIVA_SEED", "TAKE_SEED", "MC_SEED", "MC_VOICE", "MC_TAKES", "SINGER_SEED",
           "SOUL_VINYL", "SOUL_VOICE", "SOUL_STEM", "SOUL_PIPER", "SOUL_PACE", "SOUL_OURS", "SOUL_ACE")


def _ab_tag(k, v):
    """A switch and its value for a file name: short values as they are, long ones (voice descriptions) as a hash."""
    import hashlib
    v = re.sub(r"[^\w.+-]", "", v)
    return k.lower() + (v if len(v) <= 24 else hashlib.sha1(v.encode()).hexdigest()[:8])


class Song:
    def __init__(self, bpm, bars, tail=4.0):
        self.bpm = bpm
        self.beat = 60.0 / bpm
        self.bar = 4 * self.beat
        self.step = self.beat / 4
        self.bars = bars
        self.length = bars * self.bar
        self.n = int((self.length + tail) * SR)
        self.bus = {k: np.zeros((self.n, 2), np.float32) for k in BUSES}
        self.send = np.zeros((self.n, 2), np.float32)    # to the room
        self.echo = np.zeros((self.n, 2), np.float32)    # to the dotted-eighth delay
        self.kicks = []
        p = os.environ.get("PREVIEW")
        self.window = tuple(int(v) for v in p.split("-")) if p else None

    def live(self, bar, bars=1):
        """False when a part from `bar` lasting `bars` bars cannot be heard in the PREVIEW window: then the part
        need not be made (parts.Band skips it), so a preview takes seconds. One bar of margin before the window,
        for what rings into it."""
        if not self.window:
            return True
        a, b = self.window
        return bar + bars > a - 1 and bar < b

    def at(self, bar, beat=0.0):
        return bar * self.bar + beat * self.beat

    def put(self, bus, t, g, pan=.5, amp=1.0, wet=.15, echo=0.0):
        """Mix g (mono, or stereo as (n, 2)) into a bus at second t, panned 0 (left) .. 1 (right).
        MUTE=vox (environment, comma separated): those buses stay out, their reverb and echo too (for stems)."""
        if bus in MUTED:
            return
        i = int(round(t * SR))
        if i >= self.n or len(g) == 0:
            return
        if i < 0:
            g, i = g[-i:], 0
        j = min(i + len(g), self.n)
        seg = np.asarray(g[:j - i]) * amp
        if seg.ndim == 1:
            seg = np.stack([seg * math.cos(pan * math.pi / 2), seg * math.sin(pan * math.pi / 2)], axis=1)
        self.bus[bus][i:j] += seg
        if wet:
            self.send[i:j] += seg * wet
        if echo:
            self.echo[i:j] += seg * echo

    def kick(self, t, a=1.0, **kw):
        self.put("drums", t, kick(a, **kw), .5, 1.0, wet=0)
        self.kicks.append(t)

    def notes(self, bar, line, key=0, bars=1):
        """[(second, midi, seconds)] of a line over some bars: notes, "-" to hold, "." to rest, on an even grid."""
        toks = line.split()
        step = bars * self.bar / len(toks)
        out = []
        for k, tok in enumerate(toks):
            if tok in "-.":
                continue
            n = 1
            while k + n < len(toks) and toks[k + n] == "-":
                n += 1
            out.append((self.at(bar) + k * step, midi(tok) + key, n * step))
        return out

    def sing(self, t, syllables, pan=.5, amp=1.0, wet=.3, echo=.25):
        for off, g in robot(syllables):
            self.put("vox", t + off, g, pan, amp, wet=wet, echo=echo)

    def mixdown(self, path, gains, cut_keys=None, duck=None, room=.25, echo_mix=.5, lufs=-10.0, fade_in=0.0, ir=None,
                tail_fade=2.0, ceiling_db=-1.2, unmask=6.0, voxchain=True):
        """Duck, delay, room, master filter, glue, then a true-peak limiter to the loudness target; write a dithered
        16-bit WAV of the song's length plus the reverb's tail.

        PREVIEW=48-64 (environment): mix only bars 48 to 63, for a quick listen; the loudness is aimed at them.
        GAIN=keys:0.5,pads:0.8 (environment): these buses' gains times these factors, for mixing tests."""
        gains = dict(gains)
        for kv in filter(None, os.environ.get("GAIN", "").split(",")):
            k, v = kv.split(":")
            gains[k] = gains.get(k, 1.0) * float(v)
        preview = os.environ.get("PREVIEW")
        if preview:
            a, b = (int(v) for v in preview.split("-"))
            t0, t1 = self.at(a), min(self.at(b), self.length)
            i0, i1 = int(t0 * SR), min(int((t1 + tail_fade + .5) * SR), self.n)
            for k in BUSES:
                self.bus[k] = self.bus[k][i0:i1]
            self.send, self.echo = self.send[i0:i1], self.echo[i0:i1]
            self.kicks = [t - t0 for t in self.kicks if t0 <= t < t1]
            if cut_keys:
                cut_keys = [(t - t0, v) for t, v in cut_keys]
            self.n, self.length, fade_in = i1 - i0, t1 - t0, 0.0
            self.bars = f"{b - a} (bars {a}-{b - 1})"
        n = self.n
        duck = duck or {"pads": .7, "bass": .45, "keys": .25}
        env = np.zeros(n)
        for t in self.kicks:
            if int(t * SR) < n:
                env[int(t * SR)] = 1.0
        kern = np.exp(-np.arange(int(.25 * SR)) / SR / (self.beat * .18))
        env = np.minimum(signal.fftconvolve(env, kern)[:n], 1.0)
        for k, amount in duck.items():
            self.bus[k] *= (1 - amount * env)[:, None].astype(np.float32)
        for k in ("pads", "keys", "lead", "vox"):     # the lows are the kick's and the bass's
            self.bus[k] = highpass(self.bus[k], 100 if k == "vox" else 160).astype(np.float32)   # a man raps
        if os.environ.get("VOXCHAIN", "1" if voxchain else "0") == "1":   # the 1995 channel strip on the voices
            self.bus["vox"] = vocal_chain(self.bus["vox"].astype(np.float64)).astype(np.float32)
        # SOLO: only these buses (comma separated), for auditions; dry: cleared before the delay is built (it used to
        # keep the dotted-eighth delay of every bus, 19 November)
        solo = os.environ.get("SOLO")
        if solo:
            keep = solo.split(",")
            for k in BUSES:
                if k not in keep:
                    self.bus[k][:] = 0
            self.send[:] = 0
            self.echo[:] = 0
            self.kicks = []
        # the delay: dotted eighths, ping-pong, fading
        d = int(3 * self.step * SR)
        echo = np.zeros((n, 2))
        src = lowpass(highpass(self.echo, 300), 5500)
        for k in range(1, 6):
            side = k % 2
            echo[k * d:, side] += (src[:n - k * d, 0] + src[:n - k * d, 1] * .3) * .5 ** k
        if os.environ.get("STEMS"):   # how loud each bus is, for mixing by numbers
            for k in BUSES:
                x = self.bus[k].astype(np.float64) * gains.get(k, 1.0)
                if np.abs(x).max() > 0:
                    print(f"  {k:6s} {integrated_lufs(x):6.1f} LUFS")
        unmask_db = float(os.environ.get("UNMASK", unmask))
        if unmask_db > 0:            # the pads, keys and lead make room where (and in the band where) the voice sings
            vox = self.bus["vox"].astype(np.float64) * gains.get("vox", 1.0)
            soft = sum(self.bus[k].astype(np.float64) * gains.get(k, 1.0) for k in ("pads", "keys", "lead"))
            rest = sum(self.bus[k].astype(np.float64) * gains.get(k, 1.0) for k in ("drums", "perc", "bass"))
            music = rest + make_room(soft, vox, unmask_db) + vox + echo * echo_mix
        else:
            music = sum(self.bus[k].astype(np.float64) * gains.get(k, 1.0) for k in BUSES if k != "fx") + echo * echo_mix
        if cut_keys:
            ks, vs = zip(*cut_keys)
            cutoff = np.exp(np.interp(np.arange(n) / SR, ks, np.log(vs)))
            for ch in range(2):
                music[:, ch] = sweep(music[:, ch], cutoff, .9, 256)
        mix = music + self.bus["fx"] * gains.get("fx", 1.0)
        # the room
        # the room: an impulse response (stereo, unit energy per channel, e.g. from room.py), or decaying noise
        ir_len = int(2.2 * SR)
        ti = np.arange(ir_len) / SR
        for ch in range(2):
            if ir is not None:
                h = ir[:, ch]
            else:
                h = lowpass(rng.standard_normal(ir_len) * np.exp(-ti * 2.8), 6500)
                h /= np.sqrt(np.sum(h ** 2))
            mix[:, ch] += signal.fftconvolve(highpass(self.send[:, ch], 250), h)[:n] * room
        mix = highpass(mix, 28)
        tt_ = np.arange(n) / SR
        if fade_in:
            mix *= np.minimum(tt_ / fade_in, 1)[:, None]
        end = self.length + tail_fade
        mix *= np.clip((end - tt_) / tail_fade, 0, 1)[:, None]
        mix = mix[:int(end * SR)]
        # glue: stereo linked, 3:1 above where the loud parts sit
        level = np.sqrt(one_pole((mix ** 2).mean(1), .03)) + 1e-9
        db = 20 * np.log10(level)
        threshold = np.percentile(db[db > -60], 85) - 4
        reduce_db = np.maximum(db - threshold, 0) * (1 - 1 / 3.0)
        reduce_db = np.maximum(one_pole(reduce_db, .12), reduce_db * .6)
        mix *= (10 ** (-reduce_db / 20))[:, None]
        # to the loudness target, under a true-peak ceiling: the limiter takes the loudness down a little, so
        # aim again and limit again until both hold
        ceiling = 10 ** (ceiling_db / 20)
        level = integrated_lufs(mix)
        for _ in range(4):               # one limiter pass per round: the loudness settles, the last overs go below
            mix = limit(mix * 10 ** ((lufs - level) / 20), ceiling)
            level = integrated_lufs(mix)
            if abs(level - lufs) < .1:
                break
        for _ in range(3):               # the gain changes move a few peaks between the samples: limit again
            mix = limit(mix, ceiling)
        # TPDF dither to 16 bits
        q = 1 / 32767
        out = np.round((mix + (rng.random(mix.shape) - rng.random(mix.shape)) * q) * 32767)
        out = np.clip(out, -32767, 32767).astype("<i2")
        # a test render (a preview, solo, stems, other gains) never replaces the song's render in renders/: share.py,
        # dj.py and produce.py would take it for the song (it is newer than the script)
        test = [_ab_tag(k, os.environ[k]) for k in AB_VARS if os.environ.get(k)]
        renders = os.path.join(os.path.dirname(os.path.abspath(__file__)), "renders")
        if test and os.path.dirname(os.path.abspath(path)) == renders:
            stem = os.path.splitext(os.path.basename(path))[0]
            path = os.path.join(renders, "scratch", re.sub(r"[^\w.+-]", "", f"{stem}-{'-'.join(test)}") + ".wav")
            os.makedirs(os.path.dirname(path), exist_ok=True)
        with wave.open(path, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(out.tobytes())
        m, s = divmod(len(mix) / SR, 60)
        tp = 20 * np.log10(true_peak(out / 32767).max())
        print(f"wrote {path}: {int(m)}:{s:04.1f}, {self.bars} bars at {self.bpm} BPM, "
              f"{integrated_lufs(out / 32767):.1f} LUFS, {tp:+.1f} dBTP")
        if test:                         # a test render: an MP3 next to it, small enough for a phone
            import subprocess
            mp3 = path[:-4] + ".mp3"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-c:a", "libmp3lame", "-b:a", "192k", mp3],
                           check=False)
            print(f"listen: {mp3}")
