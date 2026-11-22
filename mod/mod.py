#!/usr/bin/env python3
"""A ProTracker module (M.K., 4 channels, 31 samples, 64-row patterns) written from Python, and its render.

    import mod
    m = mod.Module("rave 91")
    kick = m.sample("ST-01/BassDrum1")                  # a raw 8-bit sample from the ST-XX pack (~/Music/st-xx)
    p = m.pattern()
    p.put(0, 0, "C-2", kick)                            # row, channel, note, sample, effect (e.g. "C40")
    m.order = [p.index]
    m.write("out/song.mod"); mod.render("out/song.mod", "out/song.wav")

The samples are the ST-XX disks (Amiga Soundtracker instrument disks, 1987-1991, on Aminet; not in this repository).
Half are raw signed 8-bit PCM, half IFF 8SVX files (st_index.load reads both). st_index.py indexes the pack: the
pitch of every sample, its kind, its loop; tune=True plays a sample's notes in tune. render() plays the module with
libopenmpt through ffmpeg.
"""
import os
import struct
import subprocess

import numpy as np

PACK = os.path.expanduser(os.environ.get("ST_PACK", "~/Music/st-xx"))
NAMES = ["C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-"]
# ProTracker's periods, finetune 0, from C-1 to B-3
PERIODS = [856, 808, 762, 720, 678, 640, 604, 570, 538, 508, 480, 453,
           428, 404, 381, 360, 339, 320, 302, 285, 269, 254, 240, 226,
           214, 202, 190, 180, 170, 160, 151, 143, 135, 127, 120, 113]
PAL = 7093789.2 / 2          # the Amiga's PAL clock: a period of 428 plays 8287 Hz (C-2)


def note_index(note):
    """"C-2" -> 12 (C-1 is 0, B-3 is 35)."""
    return NAMES.index(note[:2]) + 12 * (int(note[2]) - 1)


def note_name(i):
    return f"{NAMES[i % 12]}{i // 12 + 1}"


class Sample:
    def __init__(self, data, name, volume=64, finetune=0, loop=None):
        self.data = np.asarray(data, dtype=np.int8)[:131070]
        if len(self.data) % 2:
            self.data = self.data[:-1]
        self.name, self.volume, self.finetune, self.loop = name[:22], volume, finetune, loop
        self.index = 0             # 1..31, set by Module.sample()
        self.st = 0                # semitones added to every note written for it (tune=True: from st_index)


class Pattern:
    def __init__(self, index):
        self.index = index
        self.cells = [[(0, 0, 0, 0) for _ in range(4)] for _ in range(64)]

    def put(self, row, ch, note=None, sample=None, effect=None):
        """A cell. note: "C-2" (or None: no new note); sample: a Sample (or None); effect: "C40", "F06", "900"."""
        if note and sample and sample.st:
            note = note_name(note_index(note) + sample.st)
        period = PERIODS[note_index(note)] if note else 0
        s = sample.index if sample else 0
        e, p = (int(effect[0], 16), int(effect[1:], 16)) if effect else (0, 0)
        old = self.cells[row][ch]
        if not note and not sample and old != (0, 0, 0, 0):       # an effect added to a cell that has a note
            self.cells[row][ch] = (old[0], old[1], e, p)
            return
        self.cells[row][ch] = (period, s, e, p)

    def bytes(self):
        out = bytearray()
        for row in self.cells:
            for period, s, e, p in row:
                out += bytes([(s & 0xF0) | (period >> 8), period & 0xFF, ((s & 0x0F) << 4) | e, p])
        return bytes(out)


class Module:
    def __init__(self, title):
        self.title = title[:20]
        self.samples = []
        self.patterns = []
        self.order = []

    def sample(self, path, volume=64, loop=None, start=0, end=None, gain=1.0, name=None, tune=False):
        """A sample from the pack (a path under PACK; an IFF 8SVX file's BODY, not its header), or a numpy int8
        array. loop: (start, length) in bytes, True for the whole sample, or "auto" for the 8SVX header's loop;
        start/end trim it (bytes); gain scales it (clipped). tune: the written notes sound as written, by the
        index (st_index.csv: a transpose added to every note, and the finetune)."""
        row = None
        if isinstance(path, str):
            import st_index
            data, info = st_index.load(path)
            row = st_index.lookup(path)
            name = name or os.path.basename(path)
            if loop == "auto":
                loop = (info["loop_start"], info["loop_len"]) if info["loop_len"] else None
        else:
            data = path
        data = data[start:end]
        if gain != 1.0:
            data = np.clip(np.round(data.astype(float) * gain), -128, 127).astype(np.int8)
        if loop is True:
            loop = (0, len(data) - len(data) % 2)
        s = Sample(data, name or "sample", volume, loop=loop)
        if tune and row and row.get("transpose") not in (None, ""):
            s.st, s.finetune = int(row["transpose"]), int(row["finetune"])
        self.samples.append(s)
        s.index = len(self.samples)
        assert s.index <= 31, "31 samples at most"
        return s

    def pattern(self):
        p = Pattern(len(self.patterns))
        self.patterns.append(p)
        return p

    def write(self, path):
        out = bytearray(self.title.encode("ascii", "replace").ljust(20, b"\0"))
        for i in range(31):
            if i < len(self.samples):
                s = self.samples[i]
                ls, ll = (s.loop[0] // 2, max(1, s.loop[1] // 2)) if s.loop else (0, 1)
                out += s.name.encode("ascii", "replace").ljust(22, b"\0")
                out += struct.pack(">HBBHH", len(s.data) // 2, s.finetune & 0x0F, s.volume, ls, ll)
            else:
                out += b"\0" * 22 + struct.pack(">HBBHH", 0, 0, 0, 0, 1)
        out += bytes([len(self.order), 127])
        out += bytes(self.order + [0] * (128 - len(self.order)))
        out += b"M.K."
        for p in self.patterns:
            out += p.bytes()
        for s in self.samples:
            out += s.data.tobytes()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(out)
        return path


def render(src, dst, seconds=None):
    """The module played by libopenmpt (ffmpeg), as WAV or MP3 (by the extension)."""
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", src]
    if seconds:
        cmd += ["-t", str(seconds)]
    if dst.endswith(".mp3"):
        cmd += ["-b:a", "256k"]
    subprocess.run(cmd + [dst], check=True)
    return dst


def pitch(path, rate=PAL / 428):
    """The fundamental of a sample played at C-2 (8287 Hz), in semitones above C (0..11.99), and its Hz; from the
    autocorrelation of its loudest stretch. For tuning a melodic sample: play it that many semitones lower."""
    x = np.fromfile(os.path.join(PACK, path), dtype=np.int8).astype(float)
    i = int(np.argmax(np.convolve(np.abs(x), np.ones(512), "same")))
    seg = x[max(0, i - 1024):i + 1024]
    seg = seg - seg.mean()
    ac = np.correlate(seg, seg, "full")[len(seg) - 1:]
    lo, hi = int(rate / 1000), int(rate / 40)         # 40 Hz .. 1 kHz
    lag = lo + int(np.argmax(ac[lo:hi]))
    f = rate / lag
    semis = 12 * np.log2(f / 16.3516) % 12           # above C
    return semis, f
