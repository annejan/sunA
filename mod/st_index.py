#!/usr/bin/env python3
"""An index of the ST-XX sample pack (~/Music/st-xx, 10 646 files): what each sample is, how it sounds and how to
tune it, so a module needs no guessing (Floppy Hardcore's M1 piano was an F#, not a C: every chord a tritone off).

st_index.py build                       analyse every sample (16 processes, about a minute): writes st_index.csv
st_index.py find piano --tonal          search: words in the path, and filters
st_index.py find --cat bass --note C --min-conf 4 --max 20
st_index.py show ST-44/m1piano8'        one sample's row

Per sample (st_index.csv, one row each):
  path, bytes, iff (an IFF 8SVX file: its header read, the audio is its BODY), rate (8SVX samples per second, the
  rate it was sampled at; 0 for raw files: they have no header), loop_start, loop_len (bytes, from the 8SVX header;
  0 without), seconds (at C-2, 8287 Hz), bandwidth (Hz below which 99 % of its energy lies, played at C-2: at most
  4143; double it for C-3; a low value is a dull or lo-fi sample),
  f0 (Hz at C-2),
  note (the pitch it sounds at C-2, e.g. F#4), st (semitones above C, 0-12), conf (how clearly it has one pitch: the
  harmonic product spectrum's peak against its median, in dB; tonal samples score above about 20), tonal,
  flatness (0 a pure tone .. 1 noise), attack (s to the peak), decay (s from the peak to -20 dB; -1: it does not
  fall that far: a sustained or looped sound), percussive, peak_db, rms_db, lead (s of silence at the start),
  category (a guess: kick, snare, hat, cymbal, tom, perc, break, bass, piano, organ, string, brass, pad, vox, lead,
  hit, fx; from the name first, then the sound), transpose, finetune (play it that many semitones and eighths away
  so its written note sounds right: mod.Module.sample(..., tune=True) applies them).
"""
import csv
import os
import re
import struct
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.expanduser(os.environ.get("ST_PACK", "~/Music/st-xx"))
CSV = os.path.join(HERE, "st_index.csv")
RATE = 7093789.2 / 2 / 428          # C-2 on a PAL Amiga: 8287 Hz
NAMES = ["C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-"]
FIELDS = ["path", "bytes", "iff", "rate", "loop_start", "loop_len", "seconds", "bandwidth", "f0", "note", "st",
          "conf", "tonal", "flatness", "attack", "decay", "percussive", "peak_db", "rms_db", "lead", "category", "transpose",
          "finetune"]

# the name says it best (English, German and Dutch sample names, abbreviations of the time)
CATS = [("break", r"break|brk|beat(?!.*(drum|bass))|loop|groove|funky"),
        ("kick", r"b(ass)?[-_ ]?drum|bd\b|bdrum|kick|bassd|\bbd\d|trommel"),
        ("snare", r"snare|sn\b|sdrum|\bsd\d?\b|rim"),
        ("hat", r"hi[-_ ]?hat|hh\b|hihat|hat\b|\bhh\d"),
        ("cymbal", r"crash|ride|cymb|splash|china"),
        ("tom", r"tom\b|toms|tom\d|tomtom"),
        ("perc", r"conga|bongo|clap|cowbell|clave|tamb|shak|timbal|agogo|cabasa|wood|perc|guiro|triangle"),
        ("bass", r"bass(?!.*drum)|\bbs\b|sub"),
        ("piano", r"piano|pno|\bep\b|epian|rhodes|clav|harpsi"),
        ("organ", r"organ|orgel|hammond"),
        ("string", r"string|strg|violin|cello|viol|arco|pizz"),
        ("brass", r"brass|trump|horn|sax|tromb|tuba"),
        ("pad", r"pad\b|pads|choir|chor|aah|ahh|ooh|vox|voice|voic"),
        ("hit", r"hit\b|hit\d|stab|orch"),
        ("lead", r"lead|synth|solo|flute|guitar|gtr|bell|marimba|vibra|xylo|harp\b|sitar|kalimba|lute")]


DRUMS = {"kick", "snare", "hat", "cymbal", "tom", "perc", "break"}   # their pitch is not a note: no tuning


def name_cat(path):
    low = path.lower()
    for cat, rx in CATS:
        if re.search(rx, low):
            return cat
    return ""


def load(path):
    """(int8 audio, info) of a sample: an IFF 8SVX file's BODY and header (rate, loop), or the raw bytes."""
    raw = open(path if os.path.isabs(path) else os.path.join(PACK, path), "rb").read()
    info = dict(iff=0, rate=0, loop_start=0, loop_len=0)
    if raw[:4] == b"FORM" and raw[8:12] == b"8SVX":
        i, body, vhdr = 12, None, None
        while i + 8 <= len(raw):
            cid, size = raw[i:i + 4], struct.unpack(">I", raw[i + 4:i + 8])[0]
            chunk = raw[i + 8:i + 8 + size]
            if cid == b"VHDR":
                vhdr = struct.unpack(">IIIHBBI", chunk[:20])
            elif cid == b"BODY":
                body = chunk
            i += 8 + size + (size & 1)
        if body is not None:
            info["iff"] = 1
            if vhdr:
                one, rep, _, sps, octs, comp, _ = vhdr
                info.update(rate=sps, loop_start=one if rep > 2 else 0, loop_len=rep if rep > 2 else 0)
                if octs == 1 and one + rep and one + rep <= len(body):
                    body = body[:one + rep]          # the first octave only (more octaves follow it)
            raw = body
    return np.frombuffer(raw, dtype=np.int8), info


def analyse(rel):
    try:
        x8, info = load(rel)
    except Exception as err:          # unreadable: listed, not analysed
        return dict(path=rel, bytes=0, category="error:" + type(err).__name__)
    x = x8.astype(float) / 128
    n = len(x)
    row = dict(path=rel, bytes=n, **info, seconds=round(n / RATE, 3))
    if n < 64 or np.abs(x).max() < 1e-3:
        return dict(row, category=name_cat(rel) or "empty")
    a = np.abs(x)
    h = max(1, int(RATE / 200))                               # 5 ms frames
    env = np.sqrt(np.add.reduceat(x ** 2, np.arange(0, n, h)) / h)
    pk = int(np.argmax(env))
    peak_db = 20 * np.log10(a.max() + 1e-9)
    rms_db = 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
    lead = (np.argmax(a > .02) / RATE) if (a > .02).any() else 0.0
    below = np.nonzero(env[pk:] < env[pk] * .1)[0]
    decay = below[0] * h / RATE if len(below) else -1.0
    attack = pk * h / RATE
    # pitch: the harmonic product spectrum of the steadiest stretch after the attack (up to 0.4 s)
    a0 = min(n - 1, int(pk * h + .02 * RATE))
    seg = x[a0:a0 + int(.4 * RATE)]
    if len(seg) < 256:
        seg = x[max(0, n - 4096):]
    seg = (seg - seg.mean()) * np.hanning(len(seg))
    N = 1 << 16
    S = np.abs(np.fft.rfft(seg, N)) + 1e-12
    f = np.fft.rfftfreq(N, 1 / RATE)
    hp = np.log(S.copy())
    for k in (2, 3, 4):
        d = np.log(S[::k])
        hp[:len(d)] += d
    band = (f > 25) & (f < 1500)
    i0 = np.argmax(hp[band])
    f0 = float(f[band][i0])
    conf = float((hp[band][i0] - np.median(hp[band])) * 20 / np.log(10) / 4)   # dB, per harmonic
    flat = float(np.exp(np.mean(np.log(S[1:]))) / np.mean(S[1:]))
    # the bandwidth: below which 99 % of the energy lies, played at C-2 (8287 Hz: at most 4143 Hz); a dull, low-rate
    # or filtered sample sits far under it. Scale it by the playback rate: at C-3 it is twice as high
    full = np.abs(np.fft.rfft(x - x.mean())) ** 2
    cum = np.cumsum(full) / (full.sum() + 1e-12)
    bw = float(np.searchsorted(cum, .99) / len(full) * RATE / 2)
    st = 12 * np.log2(f0 / 16.3516)
    nearest = int(round(st))
    tonal = conf > 20 and flat < .5               # an orchestra hit (a chord, .47) still counts
    perc = decay >= 0 and decay < .25
    cat = name_cat(rel)
    if not cat:
        if n / RATE > 1.2 and perc is False and not tonal and flat > .2:
            cat = "break" if decay < 0 else "fx"
        elif perc and not tonal:
            cat = "hat" if f0 > 500 or flat > .5 else "perc"
        elif tonal:
            cat = "bass" if f0 < 140 else ("lead" if perc else "pad")
        else:
            cat = "fx"
    # to sound the written note: play it (st mod 12) semitones lower, the rest as finetune (eighths, -8..7)
    off = st - 12 * np.floor(st / 12)
    tr = -int(round(off)) if round(off) <= 6 else 12 - int(round(off))
    fine = int(np.clip(round((round(off) - off) * 8), -8, 7))
    return dict(row, bandwidth=int(bw), f0=round(f0, 2), note=f"{NAMES[nearest % 12]}{nearest // 12}", st=round(off, 2),
                conf=round(conf, 1), tonal=int(tonal), flatness=round(flat, 3), attack=round(attack, 3),
                decay=round(decay, 3), percussive=int(perc), peak_db=round(peak_db, 1), rms_db=round(rms_db, 1),
                lead=round(lead, 3), category=cat, transpose=tr if tonal and cat not in DRUMS else 0,
                finetune=fine if tonal and cat not in DRUMS else 0)


def build():
    rels = sorted(os.path.relpath(os.path.join(r, f), PACK) for r, _, fs in os.walk(PACK) for f in fs
                  if not f.endswith(".txt"))
    with Pool(max(1, (os.cpu_count() or 2) - 2)) as pool:
        rows = pool.map(analyse, rels, chunksize=64)
    with open(CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    cats = {}
    for r in rows:
        cats[r.get("category", "")] = cats.get(r.get("category", ""), 0) + 1
    print(f"{len(rows)} samples -> {CSV}")
    print("  " + ", ".join(f"{c} {k}" for c, k in sorted(cats.items(), key=lambda t: -t[1])))


def rows():
    with open(CSV, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


_BY_PATH = None


def lookup(path):
    """The index row of a sample (a path under the pack), or None."""
    global _BY_PATH
    if _BY_PATH is None:
        _BY_PATH = {r["path"]: r for r in rows()} if os.path.exists(CSV) else {}
    return _BY_PATH.get(path)


def find(words=(), cat=None, note=None, tonal=None, percussive=None, min_conf=None, min_s=None, max_s=None,
         limit=30, min_bw=None):
    out = []
    for r in rows():
        low = r["path"].lower()
        if any(w.lower() not in low for w in words):
            continue
        if cat and r["category"] != cat:
            continue
        if note and not r["note"].startswith(note):
            continue
        if tonal is not None and r["tonal"] != str(int(tonal)):
            continue
        if percussive is not None and r["percussive"] != str(int(percussive)):
            continue
        if min_conf is not None and (not r["conf"] or float(r["conf"]) < min_conf):
            continue
        if min_bw is not None and float(r.get("bandwidth") or 0) < min_bw:
            continue
        s = float(r["seconds"] or 0)
        if (min_s is not None and s < min_s) or (max_s is not None and s > max_s):
            continue
        out.append(r)
    out.sort(key=lambda r: -float(r["conf"] or 0))
    return out[:limit]


def show(r):
    loop = f" loop {r['loop_start']}+{r['loop_len']}" if r.get("loop_len") not in ("", "0") else ""
    iff = f" 8SVX {r['rate']} Hz" if r.get("iff") == "1" else ""
    return (f"{r['path']:34s} {r['category']:7s} {float(r['seconds'] or 0):5.2f}s bw {r.get('bandwidth') or '-':>4} "
            f"{r['note'] or '-':4s} "
            f"conf {r['conf'] or '-':>5} {'tonal' if r['tonal'] == '1' else '     '} "
            f"{'perc' if r['percussive'] == '1' else '    '} tr {r['transpose'] or 0:>3} ft {r['finetune'] or 0:>2}"
            f"{iff}{loop}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "find", "show"])
    ap.add_argument("words", nargs="*")
    ap.add_argument("--cat")
    ap.add_argument("--note", help="the pitch class it sounds at C-2, e.g. C or F#")
    ap.add_argument("--tonal", action="store_true")
    ap.add_argument("--perc", action="store_true")
    ap.add_argument("--min-conf", type=float)
    ap.add_argument("--min-s", type=float)
    ap.add_argument("--max-s", type=float)
    ap.add_argument("--min-bw", type=float, help="the bandwidth at C-2 at least (Hz): bright samples")
    ap.add_argument("--max", type=int, default=30)
    a = ap.parse_args()
    if a.cmd == "build":
        build()
    elif a.cmd == "show":
        for w in a.words:
            r = lookup(w)
            print(show(r) if r else f"{w}: not in the index")
    else:
        for r in find(a.words, a.cat, a.note, True if a.tonal else None, True if a.perc else None, a.min_conf,
                      a.min_s, a.max_s, a.max, a.min_bw):
            print(show(r))
