#!/usr/bin/env python3
"""A cappella takes from ACE-Step for a song's lines, and a file to listen to: the song's own bars, then the same
bars with each take laid over them, with spoken labels. The technique of the practice rounds (Push It To Prod,
Uptime Fever): the 4B LM and the SFT DiT sing the lines a cappella, several seeds, the user picks one by ear, and
the take plays whole from a downbeat (no cutting, no time-fitting).

takes.py SONG --bar 48 --lines "Segfault in my heart|Tearing me apart" --caption "mid 1990s eurodance, a female diva"
         [--tag Chorus] [--bars 8] [--seeds 1,2,3,4] [--db -8] [--lift 3]
takes.py --menu [--seeds 1,2,3]      the voice menu: kinds of voice that ACE-Step sings a cappella, one MP3
takes.py [SONG] --drafts --caption "..." --lines "a|b" --bpm 128 --key "B minor" --chords "Bm Em A F#" [--bars 16]
         [--lift 3] [--n 4] [--lm-seed 1000] [--name chorus]
                                     a draft round: 4 tunes from one LM run, turbo, ranked by fit.py, best first
takes.py --keep DRAFT.json [--guidance 7 --shift 3] [--chords "Bm Em A F#"]   the pick again with SFT; --chords measures it

--caption: the genre and the voice ("a cappella vocals only, no instruments" is added). --lines: the words, one sung
line per "|" (respelled for ACE-Step: ace.ACE_SPELL). --bars: the length of the take (8 bars: 16 s at 120 BPM).
--db: the take's level against the mix in those bars (-8: a layer, as in Push It To Prod).
--lift 3: ACE-Step sings 3 semitones lower and slower (the tempo / LIFT_SPEED), Rubber Band lifts the take to the
song's tempo and key: the sped-up voice of 90s eurodance (needs rubberband-cli).

Writes renders/ace/takes/<song>/ (the takes, cached by their request) and "<title>, ACE takes at bar N.mp3" there;
the song's render is not changed. A take is about 20 s of work on the iGPU (the 4B LM and the SFT DiT load each
time, so nothing stays in memory between takes).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from math import gcd

import numpy as np
from scipy import signal

import ace
import engine as e
import master
import room
import share
import voice as V

TAKES = os.path.join(ace.HERE, "renders", "ace", "takes")
MODEL = dict(lm_model=ace.LM, **ace.SYNTH["sft"])
A_CAPPELLA = "a cappella vocals only, no instruments"
LABEL_VOICE = "en_US-lessac-high"
WORDS = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen".split()


def slug(x):
    return re.sub(r"[^a-z0-9]+", "-", x.lower()).strip("-")[:40] or "take"


def ace_words(lines, tag="Chorus"):
    """The lines as ACE-Step's lyrics: one tag above them, respelled where ACE-Step reads a word wrong."""
    text = f"[{tag}]\n" + "\n".join(x.strip() for x in lines if x.strip()) + "\n"
    for pat, rep in ace.ACE_SPELL:
        text = re.sub(pat, rep, text)
    return text


def run(cmd, log, timeout):
    """One ACE-Step step through ace.gpu (the GPU lock, ace.GPU_LOCK or ACE_LOCK=FILE; a timeout that counts the
    wait for the lock; one retry after a VAE crash); False when it failed."""
    return ace.gpu(cmd, log, timeout + 600)


NOTES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
SAME = {"Db": "C#", "D#": "Eb", "Gb": "F#", "G#": "Ab", "A#": "Bb"}
# The lift (19 November): ACE-Step sings slower and lower, Rubber Band brings the take up to the song's tempo and key.
# By ear "really 90s eurotrash"; an A/B of a trance take from 138 to 170 BPM: 3 semitones up, formants NOT kept, beat
# a plain speed-up, the same pitch, and 3 up with the formants kept.
LIFT_SPEED = 170 / 138


def transpose(keyscale, semis):
    """ACE-Step's key name moved by `semis` semitones: transpose("F major", -3) -> "D major"."""
    note, mode = keyscale.split()
    return f"{NOTES[(NOTES.index(SAME.get(note, note)) + semis) % 12]} {mode}"


def take(caption, lyrics, bpm, key, bars, seed, out, name="take", lang="en", lift=0):
    """One take, `bars` long at `bpm`: the WAV's path, or None when ACE-Step failed. Cached by the request (the same
    request and seed give the same audio).
    lift (semitones, 0 = off): ACE-Step sings `lift` semitones lower at the tempo divided by LIFT_SPEED, then Rubber
    Band (R3 engine, `rubberband-cli`) brings the take up to `bpm` and `key`: the sped-up voice of 90s eurodance."""
    if lift:
        slow = round(bpm / LIFT_SPEED)
        src = take(caption, lyrics, slow, transpose(key, -lift), bars, seed, out, name, lang)
        if not src:
            return None
        dst = f"{src[:-4]}_lift{lift}_{bpm:g}.wav"
        if not os.path.exists(dst):
            r = subprocess.run(["rubberband", "-3", "-q", "-T", f"{slow}:{bpm:g}", "-p", str(lift), src, dst],
                               capture_output=True, text=True)
            if r.returncode:
                print(f"rubberband failed: {r.stderr.strip()[-300:]}", file=sys.stderr)
                return None
        return dst
    req = {"caption": f"{caption}, {A_CAPPELLA}", "lyrics": lyrics, "bpm": int(round(bpm)), "keyscale": key,
           "timesignature": "4", "vocal_language": lang, "output_format": "wav16",
           "duration": round(bars * 240 / bpm, 2), "seed": seed, **MODEL}
    h = hashlib.sha1(json.dumps(req, sort_keys=True).encode()).hexdigest()[:8]
    base = os.path.join(out, f"{name}_s{seed}_{h}")
    wav = base + ".wav"
    if os.path.exists(wav):
        return wav
    os.makedirs(out, exist_ok=True)
    json.dump(req, open(base + ".json", "w"), indent=1, ensure_ascii=False)
    build = os.path.join(ace.ACESTEP, "build")
    if not run([os.path.join(build, "ace-lm"), "--models", ace.MODELS, "--request", base + ".json",
                "--device", "Vulkan0"], base + ".lm.log", 300):
        return None
    if not run([os.path.join(build, "ace-synth"), "--models", ace.MODELS, "--request", base + "0.json",
                "--device", "Vulkan0", "--vae-chunk", "512"], base + ".synth.log", 300):
        return None
    os.replace(base + "00.wav", wav)
    return wav


# ---------------------------------------------------------------- drafts: several tunes fast, the keeper in SFT
# (research/toolkit-2026-11-19.md: a take's time is LM decoding and DiT steps, not model loading; the key is a
# lottery, so make several cheap drafts, rank them with fit.py, and let the ear pick)
# The draft round's request (the lab of 19 November, 8 rounds of 4 on the Pull-Up Resistor and Overclocked Heart
# choruses, every take split by sep.py): the band ACE-Step puts under a take is a low drone (bass and pads, no
# drums), and the turbo DiT adds it. The same LM codes with turbo: band -4 to -12 dB; with SFT: -9 to -39 dB (two of
# four clean, two with residue only). The negative prompt and a caption without genre words keep it out of the LM;
# lm_cfg_scale 3.5 changed nothing. SFT costs about 2 minutes a round instead of 50 s. keep() at the SFT preset then
# renders the same audio again: keep only for --guidance 7 --shift 3.
LM_NEGATIVE = ("drums, bass, sub bass, bassline, synth bass, pad, drone, organ, strings, piano, keyboard, guitar, "
               "synthesizer, chords, beat, instrumental, accompaniment, backing track, full band, music, "
               "electronic dance music, high pitched, shrill, squeaky, chipmunk, helium voice")
DRAFT = dict(lm_model=ace.LM, lm_negative_prompt=LM_NEGATIVE, **ace.SYNTH["sft"])


def drafts(caption, lyrics, bpm, key, bars, out, name="draft", lang="en", n=4, lm_seed=1000, lift=0, extra=None):
    """`n` takes for the ear to choose from: one ace-lm run makes n tunes (lm_batch_size: one prefill, the KV cache
    copied, consecutive LM seeds from lm_seed), one ace-synth run renders them all with the SFT DiT (DRAFT: about
    2 minutes for four; extra={"synth_model": ..., **ace.SYNTH["turbo"]} for the old 50 s turbo round). Returns [(wav, json, sung_bpm)]; each JSON keeps the LM's codes, so keep() renders a picked tune
    again with SFT: the same words and rhythm in the better voice (the key can move: measure the keeper). lift: sung `lift` semitones lower at the tempo
    divided by LIFT_SPEED (finish() brings it to the song; the shift there comes from fit.py and the ear).
    extra: more request fields for ace-lm and ace-synth (lm_negative_prompt, lm_cfg_scale, ...). Reproducible:
    lm_seed fixes the tunes (without it ace-lm draws a random LM seed every run). A second of
    headroom: acestep.cpp cuts the duration to whole seconds and the LM stops about 0.8 s early, which cut the
    last word of 14 of 137 takes on disk."""
    sung = round(bpm / LIFT_SPEED) if lift else bpm
    ask = transpose(key, -lift) if lift else key
    req = {"caption": f"{caption}, {A_CAPPELLA}", "lyrics": lyrics, "bpm": int(round(sung)), "keyscale": ask,
           "timesignature": "4", "vocal_language": lang, "output_format": "wav16",
           "duration": float(int(bars * 240 / sung) + 2), "seed": 1, "lm_seed": int(lm_seed), "lm_batch_size": n,
           **DRAFT, **(extra or {})}
    h = hashlib.sha1(json.dumps(req, sort_keys=True).encode()).hexdigest()[:8]
    base = os.path.join(out, f"{name}_l{lm_seed}_{h}")
    got = [(f"{base}_{b}.wav", f"{base}{b}.json", sung) for b in range(n)]
    if all(os.path.exists(w) for w, _, _ in got):
        return got
    os.makedirs(out, exist_ok=True)
    json.dump(req, open(base + ".json", "w"), indent=1, ensure_ascii=False)
    build = os.path.join(ace.ACESTEP, "build")
    if not run([os.path.join(build, "ace-lm"), "--models", ace.MODELS, "--request", base + ".json",
                "--device", "Vulkan0", "--max-seq", "2048"], base + ".lm.log", 300):
        return []
    if not run([os.path.join(build, "ace-synth"), "--models", ace.MODELS, "--request", *[j for _, j, _ in got],
                "--device", "Vulkan0", "--vae-chunk", ace.VAE_CHUNK], base + ".synth.log", 300):
        return []
    for b, (w, _, _) in enumerate(got):
        os.replace(f"{base}{b}0.wav", w)
    return got


def keep(draft_json, guidance=None, shift=None, ref=None):
    """A picked draft rendered again from its JSON with the SFT DiT (50 steps): the same LM codes, so the same words
    and rhythm in the better voice; but not always the same key (the rehearsals of 19 November: a draft at +3
    semitones came back at -2 with guidance 1 and at +3 with guidance 7; Overclocked Heart's -1 at +5 and +0), so
    measure the keeper (takes.py --keep JSON --chords "...") before takes.finish. guidance / shift: the SFT preset is guidance 1.0 (CFG off) and shift 1.0; the
    official docs' guidance on (7.0) with shift 3.0 doubles the DiT time and is an A/B for the ear. ref: a WAV whose
    timbre the voice takes (--ref-audio; about 3 s to encode): the chosen chorus take, so that verse, chorus and rap
    sound like one singer."""
    req = json.load(open(draft_json))
    req.update(ace.SYNTH["sft"])
    if guidance is not None:
        req["guidance_scale"] = float(guidance)
    if shift is not None:
        req["shift"] = float(shift)
    base = f"{draft_json[:-5]}_sft_g{req['guidance_scale']:g}_s{req['shift']:g}"
    if ref:
        base += "_ref" + hashlib.sha1(open(ref, "rb").read()).hexdigest()[:6]
    wav = base + ".wav"
    if os.path.exists(wav):
        return wav
    json.dump(req, open(base + ".json", "w"), indent=1, ensure_ascii=False)
    if not run([os.path.join(ace.ACESTEP, "build", "ace-synth"), "--models", ace.MODELS, "--request",
                base + ".json", "--device", "Vulkan0", "--vae-chunk", ace.VAE_CHUNK,
                *(["--ref-audio", ref] if ref else [])], base + ".synth.log", 400):
        return None
    os.replace(base + "0.wav", wav)
    return wav


def finish(wav, sung, bpm, shift=0):
    """A take at the song's tempo and key: Rubber Band (R3 engine) from the sung tempo to `bpm` and `shift`
    semitones up in one pass, formants not kept (the lift A/B of 19 November: the user's pick)."""
    if sung == bpm and not shift:
        return wav
    dst = f"{wav[:-4]}_to{bpm:g}_{shift:+d}.wav"
    if not os.path.exists(dst):
        cmd = (["rubberband", "-3", "-q"] + (["-T", f"{sung:g}:{bpm:g}"] if sung != bpm else [])
               + (["-p", str(shift)] if shift else []) + [wav, dst])
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            print(f"rubberband failed: {r.stderr.strip()[-300:]}", file=sys.stderr)
            return None
    return dst


def pin(wav, song, label):
    """The take a song uses, as a file of its own: renders/ace/takes/<song>/pinned/<label>.wav (with its JSON when
    there is one). Song scripts read the pinned file and never make their take while rendering: a changed request
    or a lost WAV would make a different take without a word."""
    import shutil
    d = os.path.join(TAKES, song, "pinned")
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, f"{slug(label)}.wav")
    shutil.copyfile(wav, dst)
    stem = re.sub(r"_to[\d.]+_[+-]\d+$", "", wav[:-4])      # a finished file: its keeper or draft
    stem = re.sub(r"_vox$", "", stem)                          # the voice alone (sep.py): its take
    for j in (stem + ".json", re.sub(r"_(\d+)$", r"\1", stem) + ".json"):
        if os.path.exists(j):
            shutil.copyfile(j, dst[:-4] + ".json")
            break
    return dst


def draft_round(caption, lines, bpm, key, chords, bars=16, tag="Chorus", lift=0, n=4, lm_seed=1000, out=None,
                name="draft", lang="en", extra=None):
    """The compo-day round: n drafts, each split from the band ACE-Step may have put under it (sep.voice: the voice
    alone when the band is louder than sep.CLEAN_DB), ranked by fit.py against the band's chords and by register,
    each brought to the song's tempo and the measured key shift, one listen file best-first (with the bar offset
    fit.py liked spoken), and the table. The ear picks; keep() renders the pick in SFT."""
    import fit
    import sep
    out = out or os.path.join(TAKES, "drafts")
    if len(lines) * 2 < bars - 1:     # the rehearsal of 19 November: 4 lines in 16 bars sang 8 bars, then nothing
        print(f"note: {len(lines)} lines for {bars} bars; ACE-Step sings about one line in 2 bars: repeat the "
              f"chorus ({bars // 2} lines)", file=sys.stderr)
    got = drafts(caption, ace_words(lines, tag), bpm, key, bars, out, name, lang, n, lm_seed, lift, extra)
    if not got:
        return None
    sung = got[0][2]
    voices = [sep.voice(w) for w, _, _ in got]               # (the WAV to use, the band's level)
    ranked = fit.rank([v for v, _ in voices], chords, sung)
    jsons = {v: j for (v, _), (_, j, _) in zip(voices, got)}
    bands = dict(voices)
    parts, rows = [], []
    for i, (w, f, cut) in enumerate(ranked):
        s, o = f["best"]
        fin = finish(w, sung, bpm, s)
        b = int(re.search(r"_(\d+)(?:_vox)?\.wav$", w).group(1))
        rows.append(f"{i + 1}. draft {b} ({os.path.basename(jsons[w])}): {fit.describe((w, f, cut))}; "
                    f"{sep.describe(bands[w])}")
        where = {0: "", -2: ", two bars early", 2: ", two bars late", -1: ", one bar early",
                 1: ", one bar late"}.get(o, "")
        parts += [label(f"Draft {WORDS[b + 1] if b + 1 < len(WORDS) else b + 1}{where}."),
                  master.master(roomy(e.bandpass(mono(fin), 80, 12000), .15), -16.0), gap(.5)]
    # the LM seed in the names: a second round (another --lm-seed) keeps the first round's table and listen file
    mp3 = listen(parts, os.path.join(out, f"{name} drafts l{lm_seed}, best first.mp3"),
                 f"{name}: drafts l{lm_seed}, best first")
    open(os.path.join(out, f"{name} drafts l{lm_seed}.txt"), "w").write("\n".join(rows) + "\n")
    print("\n".join(rows))
    return mp3, ranked


def mono(path):
    """A take as mono at our rate."""
    x, sr = master.read(path)
    x = x.mean(1)
    if sr != e.SR:
        g = gcd(e.SR, sr)
        x = signal.resample_poly(x, e.SR // g, sr // g)
    return x


def rms(x):
    return float(np.sqrt(np.mean(np.square(x)) + 1e-12))


_IR = []


def roomy(y, wet=.22):
    """A mono line in a room, stereo (room.py, the room of the disco rounds)."""
    if not _IR:
        _IR.append(room.impulse_response((9.0, 6.0, 3.5), rt60=1.4))
    ir = _IR[0]
    out = np.repeat(y[:, None], 2, axis=1)
    for c in range(2):
        out[:, c] += wet * signal.fftconvolve(y, ir[:, c])[:len(y)]
    return out


def lay(song, take_wav, bpm, bar, bars, db=-8.0, lead=2):
    """Bars `bar - lead` up to `bar + bars + 1` of the song's render, with the take laid over it from the downbeat of
    `bar`, at `db` against the mix there, then limited back to the excerpt's own loudness."""
    b = 240 / bpm
    i0, i1 = int(round((bar - lead) * b * e.SR)), int(round((bar + bars + 1) * b * e.SR))
    part = song[max(i0, 0):i1].copy()
    if take_wav:
        y = e.bandpass(mono(take_wav), 110, 9000)
        k = int(round(lead * b * e.SR))
        y = y[:len(part) - k]
        y = y * (rms(part[k:k + len(y)]) * 10 ** (db / 20) / rms(y))
        part[k:k + len(y)] += roomy(y)
        part = master.master(part, e.integrated_lufs(song[max(i0, 0):i1]))
    f = int(.4 * e.SR)
    part[-f:] *= np.linspace(1, 0, f)[:, None]
    return part


def label(text, level=.08):
    """A spoken label (Lessac), stereo, with a little silence after it."""
    y = V._finish(V.tts(text, LABEL_VOICE))
    y = y * (level / rms(y))
    return np.concatenate([np.repeat(y[:, None], 2, axis=1), np.zeros((int(.35 * e.SR), 2))])


def gap(seconds=.6):
    return np.zeros((int(seconds * e.SR), 2))


def listen(parts, mp3, title):
    """The parts back to back, written as WAV and MP3 (title tag, artist sunA)."""
    x = np.clip(np.concatenate(parts), -1, 1)
    wav = mp3[:-4] + ".wav"
    master.write(wav, x)
    share.encode(wav, mp3, ["-metadata", f"title={title}", "-metadata", "artist=sunA"], [])
    os.remove(wav)
    return mp3


def song_takes(name, bar, lines, caption, tag="Chorus", bars=8, seeds=(1, 2, 3, 4), db=-8.0, lift=0):
    """The takes for one song's lines and the listen file: ours, then each seed laid over ours."""
    song = ace.script_name(name)
    n, wav, title, day, bpm, key, nbars = ace.song_info(song)
    out = os.path.join(TAKES, song)
    lyrics = ace_words(lines, tag)
    got = [(s, take(caption, lyrics, bpm, ace.keyscale(key), bars, s, out, f"{tag.lower()}{bar}", lift=lift))
           for s in seeds]
    if lift:
        tag = f"{tag}, lifted {lift}"
    x, _ = master.read(os.path.join(share.RENDERS, wav))
    parts = [label("Ours."), lay(x, None, bpm, bar, bars), gap()]
    for s, w in got:
        if w:
            parts += [label(f"Seed {WORDS[s]}."), lay(x, w, bpm, bar, bars, db), gap()]
        else:
            print(f"seed {s}: no take", file=sys.stderr)
    mp3 = os.path.join(out, f"{title}, ACE takes at bar {bar} ({tag.lower()}).mp3")
    return listen(parts, mp3, f"{title}: ACE takes at bar {bar}")


# ---------------------------------------------------------------- the voice menu: what ACE-Step sings a cappella
SING = ["We light up the night", "Hold on to me tight", "We light up the night", "And everything's alright"]
RAP = ["Step to the front and let the speakers shake", "Every single beat is a move we make",
       "Hands in the air from the floor to the sky", "This is the sound and we never say goodbye"]
SHOUT = ["Hey! Hey! Turn it up!", "Hey! Hey! Never stop!", "Hey! Hey! Turn it up!", "Hey! Hey! Never stop!"]
DUTCH = ["Hossen door de nacht", "Iedereen doet mee", "Hossen door de nacht", "Nog een keer, olé"]
MENU = [  # (the kind, for the label; the caption; the words; the tag; the language)
    ("house diva", "early 1990s deep house, a powerful soulful female diva, gospel runs", SING, "Chorus", "en"),
    ("soul man", "1970s soul, a warm soulful male singer, smooth gospel runs", SING, "Chorus", "en"),
    ("falsetto", "late 1990s French house, a smooth male falsetto singer, disco soul", SING, "Chorus", "en"),
    ("whisper", "early 1990s deep house, a breathy intimate female spoken word voice, close to the microphone",
     SING, "Verse", "en"),
    ("eurodance diva", "mid 1990s eurodance, a bright powerful female dance diva, soaring", SING, "Chorus", "en"),
    ("bubblegum", "late 1990s bubblegum pop, a bright playful high female pop singer", SING, "Chorus", "en"),
    ("male rapper", "mid 1990s eurodance, a male rapper, confident rhythmic flow, clear words", RAP, "Rap", "en"),
    ("female rapper", "1990s hip hop, a female rapper, sharp confident flow, clear words", RAP, "Rap", "en"),
    ("gang chant", "a crowd of men and women shouting together, a terrace chant", SHOUT, "Chorus", "en"),
    ("gospel choir", "a gospel choir, men and women, rich harmonies, call and response", SING, "Chorus", "en"),
    ("punk shout", "1980s punk, a raw shouting male punk singer, hoarse and angry", SHOUT, "Chorus", "en"),
    ("crooner", "1950s lounge, a smooth male crooner, deep baritone, slow vibrato", SING, "Chorus", "en"),
    ("carnival", "Dutch carnival schlager, a cheerful male sing-along singer, beer hall", DUTCH, "Chorus", "nl"),
    ("reggae", "1970s roots reggae, a laid-back warm male reggae singer", SING, "Chorus", "en"),
    ("country", "1990s country, a female country singer with a twang", SING, "Chorus", "en"),
    ("opera", "classical opera, a dramatic operatic soprano", SING, "Chorus", "en"),
    ("kids choir", "a children's choir, bright and innocent", SING, "Chorus", "en"),
    ("robot", "late 1990s French house, robotic vocoder vocals, a talk box", SING, "Chorus", "en"),
]


def menu(seeds=(1, 2, 3), bpm=120, key="A minor", bars=8):
    """Each kind of voice, a few seeds, a cappella, one MP3 with the number and kind spoken before each."""
    out = os.path.join(TAKES, "menu")
    parts, sheet = [], []
    for i, (kind, caption, lines, tag, lang) in enumerate(MENU, 1):
        sheet.append(f"{i:2d}. {kind}: {caption}")
        parts.append(label(f"{WORDS[i] if i < len(WORDS) else i}. {kind}."))
        for s in seeds:
            w = take(caption, ace_words(lines, tag), bpm, key, bars, s, out, slug(kind), lang)
            if not w:
                print(f"{kind}, seed {s}: no take", file=sys.stderr)
                continue
            y = roomy(e.bandpass(mono(w), 80, 12000), .15)
            parts += [label(WORDS[s], .06), master.master(y, -16.0), gap(.5)]
        parts.append(gap(.4))
    open(os.path.join(out, "menu.txt"), "w").write("\n".join(sheet) + "\n")
    return listen(parts, os.path.join(out, "ACE voice menu.mp3"), "ACE voice menu")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("song", nargs="?")
    ap.add_argument("--menu", action="store_true", help="the voice menu instead of a song")
    ap.add_argument("--bar", type=int, help="the downbeat where the take starts")
    ap.add_argument("--lines", help='the words, one sung line per "|"')
    ap.add_argument("--caption", help="the genre and the voice")
    ap.add_argument("--tag", default="Chorus", help="the lyrics tag: Chorus, Verse, Rap, ...")
    ap.add_argument("--bars", type=int, default=8)
    ap.add_argument("--seeds", default=None, help="for example 1,2,3,4 (default: 1-4, the menu 1-3)")
    ap.add_argument("--db", type=float, default=-8.0, help="the take against the mix there (default -8 dB)")
    ap.add_argument("--lift", type=int, default=0, help="sung N semitones lower and slower, lifted by Rubber Band "
                    "(3: the 90s eurodance voice)")
    ap.add_argument("--drafts", action="store_true", help="a draft round: --n turbo drafts from one LM run, ranked "
                    "against --chords, best first (needs --caption, --lines, --bpm, --key, --chords)")
    ap.add_argument("--bpm", type=float, help="drafts: the song's tempo")
    ap.add_argument("--key", help='drafts: the song\'s key, "B minor"')
    ap.add_argument("--chords", help='drafts: the band\'s chords, one a bar, repeating: "Bm Em A F#"')
    ap.add_argument("--n", type=int, default=4, help="drafts: how many (default 4)")
    ap.add_argument("--lm-seed", type=int, default=1000, help="drafts: the first LM seed (the tunes)")
    ap.add_argument("--name", default="draft", help="drafts: the files' name")
    ap.add_argument("--lang", default="en", help="drafts: the sung language (ACE-Step's vocal_language: en, nl, ...)")
    ap.add_argument("--keep", metavar="JSON", help="render a picked draft's JSON again with SFT (with --chords: its own fit)")
    ap.add_argument("--guidance", type=float, help="keep: the DiT's guidance (SFT preset 1.0; docs 7.0)")
    ap.add_argument("--shift", type=float, help="keep: the schedule shift (SFT preset 1.0; docs 3.0)")
    ap.add_argument("--ref", help="keep: a WAV for the voice's timbre (--ref-audio), e.g. the chosen chorus take")
    a = ap.parse_args()
    if a.keep:
        w = keep(a.keep, a.guidance, a.shift, a.ref)
        if w:                         # the keeper sings the draft's codes: a band in the draft is in the keeper too
            import sep
            w, band_db = sep.voice(w)
            print(f"{w} ({sep.describe(band_db)})")
        if w and a.chords:            # the keeper's own fit: SFT can sing the tune in another key than its draft
            import fit
            sung = json.load(open(a.keep))["bpm"]
            r = fit.rank([w], a.chords.split(), sung)[0]
            print(f"keeper, sung at {sung} BPM: {fit.describe(r)}")
        return
    if a.drafts:
        if not (a.caption and a.lines and a.bpm and a.key and a.chords):
            ap.error("--drafts needs --caption, --lines, --bpm, --key and --chords")
        out = os.path.join(TAKES, ace.script_name(a.song)) if a.song else None
        draft_round(a.caption, a.lines.split("|"), a.bpm, a.key, a.chords.split(), a.bars, a.tag, a.lift, a.n,
                    a.lm_seed, out, a.name, a.lang)
        return
    seeds = [int(s) for s in a.seeds.split(",")] if a.seeds else None
    if a.menu:
        print(menu(seeds or (1, 2, 3)))
        return
    if not (a.song and a.bar is not None and a.lines and a.caption):
        ap.error("a song needs --bar, --lines and --caption (or use --menu)")
    print(song_takes(a.song, a.bar, a.lines.split("|"), a.caption, a.tag, a.bars, seeds or (1, 2, 3, 4), a.db,
                     a.lift))


if __name__ == "__main__":
    main()
