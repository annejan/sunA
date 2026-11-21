"""Parts for a new song in a hurry (the surprise themes): drums from step patterns, basslines, chords, keys, a
diva with a choir of other voices, a rapper, a spoken voice. The same parts as in segfault.py, made reusable.

    import engine as e
    import parts
    S = e.Song(bpm=174, bars=128)
    P = parts.Band(S, prog=["Am", "F", "C", "G"], scale="minor")
    P.drums(bar, parts.GROOVES["dnb"])
    P.bass(bar, "offbeat")
    P.diva(bar, "E5 - D5 - C5 - - - . . . . . . . .", "hel lo + world")
    P.rap(bar, "Ten print hello, twenty go to ten.")

Every part takes `bar` and works out the chord and the key change (key_of) itself. The words for the diva are as
the voice should say them, one per note; "+" holds a word over one more note.

diva_voice="ds:hanami" (or DIVA=ds:hanami in the template): a DiffSinger voicebank sings the whole diva part in one
take (ds.py, DS_VOICE and DS_PITCH as in the Badge), the Piper choir stays under it. DiffSinger reads real words:
give `ds_words` when the Piper spelling differs ("ee lek trih sih tee" -> "electricity + + + +"). Call
P.finish() before S.mixdown().

diva_voice="ds:lem": the produced singer, the chain the user picked on The Rhythm Of The Badge (20 November). Lem the
Shapeshifter DS 2.5 sings our notes, converted into a Maya or Qwen voice (timbre); doubles from takes 2 and 3 in two
more voices left and right, a soft octave, a vocoder (stack); where a line has choir > 0, a real harmony a third
above in a fourth voice (harmony) instead of the Piper choir; some words louder (accent, {"flash": 4}). Every
conversion is a few minutes of GPU per voice (cached after): shape the melody with DS_TIMBRE= DS_STACK=
DS_HARMONY= (empty: Lem alone, fast), then render the whole chain once. Only Lem may be converted: Hanami's terms
forbid it.
"""
import os

import numpy as np

import dx7
import engine as e
import voice as V

# drum patterns, 16 steps a bar: x = hit, o = soft hit, . = rest (kick, clap, closed hat, open hat, extra)
GROOVES = {
    "four":      dict(kick="x...x...x...x...", clap="....x.......x...", hat="..x...x...x...x.", open="..x...x...x...x."),
    "house":     dict(kick="x...x...x...x...", clap="....x.......x...", hat="o.x.o.x.o.x.o.x.", open="..x...x...x...x.",
                      swing=.16),
    "garage":    dict(kick="x......x..x.....", clap="....x.......x...", hat="o.x.o.xoo.x.o.xo", swing=.2),
    "techno":    dict(kick="x...x...x...x...", clap="....x.......x...", hat="xoxoxoxoxoxoxoxo", open="..x...x...x...x."),
    "eurodance": dict(kick="x...x...x...x...", clap="....x.......x...", hat="o...o...o...o...", open="..x...x...x...x."),
    "dnb":       dict(kick="x.........x.....", clap="....x.......x...", hat="x.x.x.x.x.x.x.x.", extra="..o.......o..o.."),
    "breakbeat": dict(kick="x.........x..x..", clap="....x.......x...", hat="x.x.x.x.x.x.x.x.", extra=".......o.o......"),
    "hardstyle": dict(kick="x...x...x...x...", clap="....x.......x...", hat="..x...x...x...x.", open="..x...x...x...x."),
    "hiphop":    dict(kick="x......x..x.....", clap="....x.......x...", hat="x.x.x.x.x.x.x.x.", swing=.18),
    "reggaeton": dict(kick="x...x...x...x...", clap="...x..x....x..x.", hat="x.x.x.x.x.x.x.x."),
    "schlager":  dict(kick="x...x...x...x...", clap="....x.......x...", hat="..x...x...x...x."),
    "halftime":  dict(kick="x.......x.......", clap="........x.......", hat="x.x.x.x.x.x.x.x."),
    "disco":     dict(kick="x...x...x...x...", clap="....x.......x...", hat="x.o.x.o.x.o.x.o.", open="..x...x...x...x."),
    "italo":     dict(kick="x...x...x...x...", clap="....x.......x...", hat="xoxoxoxoxoxoxoxo"),   # LinnDrum, DMX
}

SCALES = {"minor": (0, 2, 3, 5, 7, 8, 10), "major": (0, 2, 4, 5, 7, 9, 11)}
TONIC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
         "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}

CONVERTIBLE = {"lem"}          # voicebanks whose renders may be converted into other voices (licences)
# the produced singer's defaults (the Badge's pick): DS_VOICE, DS_TIMBRE, DS_STACK, DS_HARMONY override them
LEM = dict(ds_voice="Civet", timbre="qwen_diva", stack="sing_qwen_pop,sing_maya_pop,octave,vocoder",
           harmony="sing_maya_soul", pitch="rule", tension="25", vib="1.6", breath="1", dyn="1", cons="0",
           comp="1")
# comp: the producer's comp of four takes (the user: "more takes is no shame when you make a jewel"); cons 0: Lem's
# consonants under the converted voice did not help Whisper (0.75 / 0.69 / 0.76 at 0 / 0.5 / 1.0, Common Ground)
# pitch rule, vib 1.6, tension 25: the user's pick of three on Can You Tell? (20 November: "C is best, but still far
# from ideal"); Lem has no pitch model, without them every note is flat ("almost GLaDOS, but more dead inside")

CHOIR = ["en_US-ljspeech-high", "en_US-kristin-medium", "en_GB-cori-high", "en_US-hfc_male-medium",
         "en_GB-alan-medium"]


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
    assert i == len(notes), f"{len(notes)} notes but the words fill {i}: {words!r}"
    return out


class Band:
    def __init__(self, S, prog, scale="minor", key_of=None, tonic=None, diva_voice=None, rapper_voice=None,
                 choir=None, kick=None, ds_voice=None, timbre=None, stack=None, harmony=None, accent=None,
                 verse_double=.25):
        """prog: one chord name a bar, repeating ("Am", "F", "C", "G", "Dm9", ...). tonic: the key's root ("A");
        by default the root of the first chord. key_of(bar): semitones up (a key change).
        The DiffSinger diva (diva_voice="ds:<bank>"): ds_voice, the bank's voice mode; with ds:lem also timbre (a
        voice.CAST name: the lead's voice), stack ("voiceL,voiceR[,octave][,vocoder]": the doubles), harmony (the
        voice of the third above on lines with choir > 0), accent ({word: dB}); defaults in LEM. verse_double: the
        doubles' level on lines without choir (on lines with choir: .55)."""
        self.S, self.prog, self.scale = S, prog, SCALES[scale]
        self.key_of = key_of or (lambda bar: 0)
        root = prog[0][:2] if prog[0][1:2] in ("#", "b") else prog[0][:1]
        self.tonic = TONIC[tonic or root]
        self.diva_voice = diva_voice or V.DIVA
        self.rapper_voice = rapper_voice or V.RAPPER
        self.choir = choir or CHOIR
        self.kick_kw = kick or dict(punch=130, base=50, length=.34, click=.4)
        self.ds = self.diva_voice.startswith("ds:")
        self.knobs = {}             # a song's own singer D settings over parts.LEM (cons="1"); DS_* still win
        self.ds_gain = 2.0          # the DiffSinger diva's level (DS_GAIN overrides it): an octave above the Piper
                                    # diva she sits in the keys' range; in the template the ear heard 0 of 32 verse
                                    # words at 1.0, 18 at 1.6, 22 at 2.5 (the Piper diva: 14)
        self.ds_lines = []                          # (from, to, amp, last word at, its echo) per diva line
        self.ds_double = []                         # (from, to, the doubles' level) per diva line
        self.ds_words = []                          # (first note, last note's end, the words) per diva line
        self.ds_accent = []                         # (from, to, dB) per accented word
        self.ds_choir = []                          # (from, to, amp) per line with a harmony
        self.verse_double = verse_double
        if self.ds:
            import ds
            self.ds_part = ds.Part(S.bpm)
            self.ds_harm = ds.Part(S.bpm)
            bank = self.diva_voice.split(":", 1)[1]
            d = dict(LEM if bank == "lem" else {}, **self.knobs)       # a song's own settings over the defaults
            env = lambda k, v: os.environ.get(k, v if v is not None else d.get(k[3:].lower(), ""))   # noqa: E731
            self.ds_voice = os.environ.get("DS_VOICE", ds_voice or d.get("ds_voice", "Fragrance"))
            self.timbre = env("DS_TIMBRE", timbre) or None
            self.stack = env("DS_STACK", stack) or ""
            self.harmony = env("DS_HARMONY", harmony) or None
            if bank not in CONVERTIBLE and (self.timbre or self.stack or self.harmony):
                raise ValueError(f"ds:{bank} may not be converted into other voices (its terms): no timbre, stack or "
                                 "harmony")
            self.accent = dict(accent or {})
            for kv in filter(None, os.environ.get("DS_ACCENT", "").split(",")):   # DS_ACCENT=flash:4,badge:2
                if ":" not in kv:       # DS_ACCENT=4: every accented word that many dB
                    self.accent = {w: float(kv) for w in self.accent}
                    continue
                w, db = kv.split(":")
                self.accent[w] = float(db)

    # ------------------------------------------------------------ harmony
    def chord(self, bar):
        return self.prog[bar % len(self.prog)]

    def in_scale(self, m, key=0):
        return (m - self.tonic - key) % 12 in self.scale

    def step_up(self, m, steps=2, key=0):
        """The note `steps` scale steps above m (2 = a third)."""
        for _ in range(steps):
            m += 1
            while not self.in_scale(m, key):
                m += 1
        return m

    def step_down(self, m, steps=2, key=0):
        for _ in range(steps):
            m -= 1
            while not self.in_scale(m, key):
                m -= 1
        return m

    # ------------------------------------------------------------ drums
    def drums(self, bar, groove, amp=1.0, kick=True, clap=True, hats=True, crash=False):
        """One bar of a groove from GROOVES (or your own dict of 16-step strings)."""
        if not self.S.live(bar):
            return
        S, t0 = self.S, self.S.at(bar)
        swing = groove.get("swing", 0.0) * S.step

        def when(k):
            return t0 + k * S.step + (swing if k % 2 else 0.0)

        def hits(name):
            return [(k, 1.0 if c == "x" else .55) for k, c in enumerate(groove.get(name, "")) if c in "xo"]

        if kick:
            for k, v in hits("kick"):
                S.kick(when(k), v * amp, **self.kick_kw)
        if clap:
            for k, v in hits("clap"):
                S.put("drums", when(k), e.clap(.6 * v * amp), .5, wet=.2)
                S.put("drums", when(k), e.snare(.4 * v * amp), .5, wet=.25)
        if hats:
            for k, v in hits("hat"):
                S.put("perc", when(k), e.hat(.28 * v * amp), .62, wet=.04)
            for k, v in hits("open"):
                S.put("perc", when(k), e.hat(.5 * v * amp, opened=True), .55, wet=.08)
            for k, v in hits("extra"):
                S.put("drums", when(k), e.snare(.3 * v * amp), .45, wet=.2)
        if crash:
            S.put("perc", t0, e.crash(.7 * amp), .5, wet=.3)

    def roll(self, bar0, bars=4, amp=1.0):
        """A snare roll that climbs to the drop, thirty-seconds in the last bar."""
        if not self.S.live(bar0, bars):
            return
        S, total = self.S, bars * 16
        for k in range(total):
            u = k / total
            t = S.at(bar0) + k * S.step
            S.put("drums", t, e.snare((.15 + .6 * u ** 1.5) * amp), .5, wet=.25)
            if k >= total - 16:
                S.put("drums", t + S.step / 2, e.snare((.15 + .6 * u ** 1.5) * amp * .8), .5, wet=.25)

    # ------------------------------------------------------------ bass
    def bass(self, bar, style="offbeat", amp=1.0, lo=33, cut=1100):
        """offbeat (eurodance, trance), root (house: on the beats), eighths (rolling), reese (dnb: one long note),
        dx7 (FM bass on the offbeats), octave (Italo disco, Hi-NRG: eighths, the octave up on each "and")."""
        if not self.S.live(bar):
            return
        S = self.S
        root = e.root_note(self.chord(bar), self.key_of(bar), lo=lo)
        if style == "reese":
            g = sum(e.saw(e.hz(root) * f, e.tt(S.bar)) for f in (1, 1.007, .993)) / 3
            g = e.lowpass(g, 400) * e.gate(e.tt(S.bar), S.bar - .05, .05)
            S.put("bass", S.at(bar), g, .5, .5 * amp, wet=0)
            return
        steps = {"offbeat": (2, 6, 10, 14), "root": (0, 4, 8, 12), "eighths": tuple(range(0, 16, 2)),
                 "octave": tuple(range(0, 16, 2))}.get(style, (2, 6, 10, 14))
        for k in steps:
            if style == "dx7":
                g = dx7.note("bass", root, S.step * 1.6, .9, tail=.1)
            elif style == "octave":
                g = e.bass_note(root + 12 * (k % 4 == 2), S.step * 1.6, cut=max(cut, 1400), decay=3)
            else:
                g = e.bass_note(root, S.step * 1.6, cut=cut, decay=3)
            S.put("bass", S.at(bar) + k * S.step, g, .5, .9 * amp, wet=0)

    # ------------------------------------------------------------ chords
    def stabs(self, bar, steps=(0, 3, 6, 10, 12), sound="piano", amp=1.0, lo=60, hi=76):
        """Chord stabs on these sixteenths: piano (rave piano), epiano (DX7), organ (M1), supersaw."""
        if not self.S.live(bar):
            return
        S = self.S
        notes = e.close_voicing(self.chord(bar), self.key_of(bar), lo=lo, hi=hi)
        for k in steps:
            t = S.at(bar) + k * S.step
            if sound == "supersaw":
                S.put("lead", t, e.supersaw(notes, S.step * 1.5, spread=.25, a=.003, r=.12, cut=6000), amp=.5 * amp,
                      wet=.2, echo=.15)
                continue
            for j, m in enumerate(notes):
                g = {"piano": lambda: e.piano(m, S.step * 2, .9), "organ": lambda: e.organ(m, S.step * 1.2),
                     "epiano": lambda: dx7.note("epiano", m, S.step * 2, .7, tail=.6)}[sound]()
                S.put("keys", t + j * .003, g, .4 + .1 * j, .3 * amp, wet=.25)

    def pad(self, bar, amp=1.0, cut=2500):
        if not self.S.live(bar):
            return
        S = self.S
        S.put("pads", S.at(bar), e.pad(e.voicing(self.chord(bar), self.key_of(bar), lo=55), S.bar, cut=cut, a=.3,
                                          r=.6), amp=.45 * amp, wet=.4)

    def lead(self, bar, line, amp=1.0, bars=1, sound="lead"):
        """A melody line ("E5 - D5 . ...") on the lead synth, or "epiano" / "bells" / "brass" (DX7)."""
        if not self.S.live(bar, bars):
            return
        S = self.S
        for t, m, d in S.notes(bar, line, self.key_of(bar), bars):
            g = e.lead(m, d * .95) if sound == "lead" else dx7.note(sound, m, d * .95, .8, tail=.4)
            S.put("lead", t, g, amp=.25 * amp, wet=.3, echo=.2)

    # ------------------------------------------------------------ voices
    def diva(self, bar, line, words, bars=1, octave=-12, amp=1.0, choir=0.0, big=False, voice=None, ds_words=None):
        """The diva sings a line: each word on its notes, the consonants just before the beat, an echo on the last
        word. choir > 0: other voices double her left and right and sing a third above; big: a man an octave down
        and a fifth voice a sixth down as well. The choir sings only the vowels (every voice has its own consonant
        lengths, which would smear hers), with less vibrato. With a DiffSinger diva (ds:...) the line goes into
        her one take, an octave above the Piper diva (her own range); ds_words: the words as DiffSinger reads them."""
        if not self.S.live(bar, bars):
            return
        S, key = self.S, self.key_of(bar)
        pairs = words_on(S.notes(bar, line, key, bars), words)
        ds_here = self.ds and not voice
        if ds_here:
            ds_pairs = words_on(S.notes(bar, line, key, bars), ds_words or words)
            human = bool(self.harmony)          # a real harmony replaces the Piper choir
            for w, ns in ds_pairs:
                for k, (t, m, d) in enumerate(ns):
                    self.ds_part.note(t, m + octave + 12, d * .97, w if k == 0 else "+")
                    if choir and human:
                        self.ds_harm.note(t, self.step_up(m, 2, key) + octave + 12, d * .97, w if k == 0 else "+")
                if w in self.accent:
                    self.ds_accent.append((ns[0][0] - .06, ns[-1][0] + ns[-1][2], self.accent[w]))
            self.ds_lines.append((S.at(bar), S.at(bar + bars), amp, ds_pairs[-1][1][0][0], .35))
            self.ds_words.append((ds_pairs[0][1][0][0], ds_pairs[-1][1][-1][0] + ds_pairs[-1][1][-1][2],
                                  " ".join(w for w, _ in ds_pairs)))
            self.ds_double.append((S.at(bar), S.at(bar + bars), .55 if choir else self.verse_double))
            if choir and human:
                self.ds_choir.append((S.at(bar), S.at(bar + bars), amp * choir))
                choir = 0.0
        for i, (w, ns) in enumerate(pairs):
            t = ns[0][0]
            notes = [(m + octave, d * .97) for _, m, d in ns]
            if not ds_here:
                li, y = V.sing(w, notes, voice=voice or self.diva_voice)
                S.put("vox", t - li, y, .5, amp, wet=.12, echo=.35 if i == len(pairs) - 1 else .05)
            if not choir:
                continue
            third = [(self.step_up(m, 2, key), d) for m, d in notes]
            parts = [(self.choir[0], notes, 8, .018, .15, .75), (self.choir[1], notes, -8, .009, .85, .75),
                     (self.choir[2], third, 0, .006, .4, .6)]
            if big:
                parts += [(self.choir[3], [(m - 12, d) for m, d in notes], 0, .012, .55, .7),
                          (self.choir[4], [(m - 12, d) for m, d in third], 5, .015, .7, .45)]
            for v, ns2, cents, late, pan, g in parts:   # vowels only: the diva's consonants stay clean
                _, y = V.sing(w, ns2, voice=v, cents=cents, vibrato=.15, vowel_only=True)
                S.put("vox", t + late, y, pan, amp * choir * g, wet=.15, echo=.05)

    def finish(self):
        """The DiffSinger diva's one take into the mix, each line at its own level, the echo on each line's last
        word. Nothing to do with a Piper diva. Call it once, before S.mixdown()."""
        if not self.ds or not self.ds_part.notes:
            return
        S = self.S
        bank = self.diva_voice.split(":", 1)[1]
        d = dict(LEM if bank == "lem" else {}, **self.knobs)       # a song's own settings over the defaults
        knob = lambda k, v: os.environ.get("DS_" + k.upper(), d.get(k, v))   # noqa: E731
        pitch = knob("pitch", "0.5")
        tension, vib = float(knob("tension", "0")), float(knob("vib", "1"))
        breaths, dyn = knob("breath", "0") == "1", knob("dyn", "0") == "1"
        cons = float(knob("cons", "0"))      # DS_CONS: Lem's consonants (above 4 kHz) under the converted voice
        sing = lambda part, seed, timbre: part.render(bank=bank, voice=self.ds_voice, pitch=pitch,  # noqa: E731
                                                      seed=seed, timbre=timbre, tension=tension, vib=vib,
                                                      breaths=breaths, dynamics=dyn, consonants=cons)
        # DS_COMP=1: the producer's comp: Lem sings the part DS_COMP_TAKES times, each line from the take Whisper
        # hears best (ds.Part.comped); the doubles then come from takes 5 and 6
        comp = knob("comp", "0") == "1"
        if comp:
            k = int(knob("comp_takes", "4"))
            y = self.ds_part.render(bank=bank, voice=self.ds_voice, pitch=pitch, timbre=self.timbre, tension=tension,
                                    vib=vib, breaths=breaths, dynamics=dyn, consonants=cons, comp=self.ds_words,
                                    comp_seeds=tuple(range(1, k + 1)))
            for t0, words, best, sc in self.ds_part.picks:
                print(f"comp {t0:7.2f}s take {best} ({sc:.2f}): {words}")
        else:
            y = sing(self.ds_part, int(os.environ.get("DS_SEED", "1")), self.timbre)

        def env(spans, n, base=1.0, mul=False):
            g = np.full(n, base)
            for t0, t1, a in spans:
                i, j = int(t0 * e.SR), int(t1 * e.SR)
                g[i:j] = g[i:j] * a if mul else a
            return g

        g = env([(t0, t1, a) for t0, t1, a, _, _ in self.ds_lines], len(y))   # 1 between the lines: breaths
        g = g * env([(t0, t1, 10 ** (db / 20)) for t0, t1, db in self.ds_accent], len(y), mul=True)
        gain = float(os.environ.get("DS_GAIN", self.ds_gain))
        y = y * g * gain
        S.put("vox", 0.0, y, .5, 1.0, wet=.12, echo=.05)
        names = [v for v in self.stack.split(",") if v]
        voices = [v for v in names if v not in ("octave", "vocoder")]
        dbl = env(self.ds_double, len(y), base=0.0)
        if len(voices) >= 2:            # the doubles: other takes in other voices, a few ms late, wide
            s2, s3 = (5, 6) if comp else (2, 3)
            for seed, timbre, pan, delay in ((s2, voices[0], .12, .012), (s3, voices[1], .88, .019)):
                d = sing(self.ds_part, seed, timbre)[:len(y)]
                d = np.pad(d, (0, len(y) - len(d))) * g * dbl * gain
                S.put("vox", delay, d, pan, 1.0, wet=.22, echo=.05)
        if "octave" in names or "vocoder" in names:
            import vfx
            soft = dbl / .55
            if "octave" in names:
                S.put("vox", 0.0, (vfx.harmony(y, [12], [1.0])[:len(y)] - y) * soft, .5, .22, wet=.3, echo=.08)
            if "vocoder" in names:
                chords = [(self.chord(b), self.key_of(b)) for b in range(int(len(y) / e.SR / S.bar) + 1)]
                S.put("vox", 0.0, vfx.vocoder(y, chords, S.bpm) * soft, .5, .35, wet=.25, echo=.1)
        if self.ds_choir and self.ds_harm.notes:     # the harmony: a third above, a fourth singer
            h = sing(self.ds_harm, 4, self.harmony)[:len(y)]
            h = np.pad(h, (0, len(y) - len(h))) * env(self.ds_choir, len(y), base=0.0) * gain
            S.put("vox", .008, h, .35, 1.0, wet=.25, echo=.05)
        for t0, t1, a, last, echo_last in self.ds_lines:
            i, j = int((last - .08) * e.SR), min(int(t1 * e.SR), len(y))
            if j > i:            # straight into the echo send (centre: cos 45 degrees on each side)
                S.echo[i:j] += (np.stack([y[i:j], y[i:j]], 1) * (echo_last * np.cos(np.pi / 4))).astype(np.float32)

    def rap(self, bar, text, bars=1, amp=1.0, voice=None, pitch=.92):
        """A spoken line from the downbeat, fitted to the bars (a sixteenth short, to breathe)."""
        if not self.S.live(bar, bars):
            return
        S = self.S
        y = V.rap(text, bars * S.bar - S.step, voice=voice or self.rapper_voice, pitch=pitch)
        S.put("vox", S.at(bar), y, .5, amp, wet=.06, echo=.04)

    def say(self, bar, text, voice="en_US-lessac-high", amp=.8, beat=0.0, phone=False):
        """A spoken announcement at its own pace (a computer, an MC); phone=True: through a small speaker."""
        if not self.S.live(bar, 2):
            return
        S = self.S
        y = V._finish(V.tts(text, voice))
        y = y * (.14 / (np.sqrt(np.mean(y ** 2)) + 1e-9))
        if phone:
            y = np.tanh(2 * e.bandpass(y, 300, 3400)) * .6
        S.put("vox", S.at(bar, beat), y, .5, amp, wet=.15, echo=.15)


def out_path(name):
    """renders/<name>.wav, or the first argument."""
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "renders", name + ".wav")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    return out
