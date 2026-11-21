#!/usr/bin/env python3
"""A quick ACE-Step song from words and a style, for a laugh in the group chat (not for the DJ: no drums-only ends,
no ear check). The 4B LM writes the song, the SFT DiT (50 steps) makes the audio, master.py brings it to -10 LUFS
and -1.2 dBTP, then an MP3.

Chosen by ear on 18 November, from five versions of the same song with the same seed: the 1.7B or 4B LM with the
turbo, base or SFT DiT. The 4B LM with SFT sounded best; base was "a mess, as if you listen half way through the
process". It takes about 2.5 minutes for 2 minutes of music (--fast: the 1.7B LM and turbo, about 70 s).

gag.py "Escaleren kun je leren" --lyrics words.txt --style "early 90s Rotterdam gabber, distorted 909 kick, ..."
       --bpm 170 --key "A minor" [--lang nl] [--seconds 120] [--seed 1] [--fast]

The words: ACE-Step's format, a [Verse] / [Chorus] / [Bridge] tag above each part. Writes
renders/ace/gags/<name>/<title>.mp3 (renders/ is not in git).
"""
import argparse
import json
import os
import re
import time

import ace
import master

GAGS = os.path.join(ace.HERE, "renders", "ace", "gags")
MODELS = {"best": dict(lm_model=ace.LM, **ace.SYNTH["sft"]),
          "fast": dict(lm_model="acestep-5Hz-lm-1.7B-Q8_0.gguf", **ace.SYNTH["turbo"])}


def make(title, lyrics, style, bpm, key="A minor", lang="en", seconds=120, seed=1, fast=False, out=None, guidance=None,
         shift=None):
    """The song: the request, the LM, the DiT, the master, the MP3. Returns (mp3, seconds per stage)."""
    name = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "gag"
    if seed != 1:                    # each seed its own folder and file: the same title used to overwrite seed 1
        name += f"-seed{seed}"
    out = out or os.path.join(GAGS, name)
    os.makedirs(out, exist_ok=True)
    req = {"caption": style, "lyrics": lyrics, "bpm": int(bpm), "keyscale": key, "timesignature": "4",
           "vocal_language": lang, "seed": seed, "output_format": "wav16", "duration": int(seconds),
           **MODELS["fast" if fast else "best"]}
    if guidance:                     # CFG on (the docs' 7.0 with shift 3.0): cleaner, about twice as slow
        req["guidance_scale"] = guidance
    if shift:
        req["shift"] = shift
    base = os.path.join(out, "request")
    json.dump(req, open(base + ".json", "w"), indent=1, ensure_ascii=False)

    t0 = time.time()
    ace.run([os.path.join(ace.ACESTEP, "build", "ace-lm"), "--models", ace.MODELS, "--request", base + ".json",
             "--device", "Vulkan0"], base + ".lm.log")
    t1 = time.time()
    # VAE tiles of 512: 1024 crashed the GPU once while the CPU was busy (the APU shares its memory)
    ace.run([os.path.join(ace.ACESTEP, "build", "ace-synth"), "--models", ace.MODELS, "--request", base + "0.json",
             "--device", "Vulkan0", "--vae-chunk", "512"], base + ".synth.log")
    t2 = time.time()
    wav = os.path.join(out, title.replace("/", "-") + (f" (seed {seed})" if seed != 1 else "") + ".wav")
    print(master.process(base + "00.wav" if os.path.exists(base + "00.wav") else base + "0.wav", wav, int(bpm)))
    mp3 = wav[:-4] + ".mp3"
    ace.share.encode(wav, mp3, ["-metadata", f"title={title}", "-metadata", "artist=sunA"], [])
    t3 = time.time()
    return mp3, dict(lm=t1 - t0, audio=t2 - t1, master=t3 - t2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("title")
    ap.add_argument("--lyrics", required=True, help="a text file with the words, [Verse] / [Chorus] tags")
    ap.add_argument("--style", required=True, help="the caption: genre, instruments, voice, mood (no artist names)")
    ap.add_argument("--bpm", type=int, required=True)
    ap.add_argument("--key", default="A minor", help='for example "G major", "F# minor"')
    ap.add_argument("--lang", default="en", help="the language of the words: en, nl, de, ...")
    ap.add_argument("--seconds", type=int, default=120)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--fast", action="store_true", help="the 1.7B LM and turbo: about 70 s instead of 150 s")
    ap.add_argument("--guidance", type=float, help="the DiT's CFG (SFT preset 1.0; the docs: 7.0, twice as slow)")
    ap.add_argument("--shift", type=float, help="the DiT's schedule shift (SFT preset 1.0; the docs: 3.0)")
    a = ap.parse_args()
    mp3, t = make(a.title, open(a.lyrics, encoding="utf-8").read(), a.style, a.bpm, a.key, a.lang, a.seconds, a.seed,
                  a.fast, guidance=a.guidance, shift=a.shift)
    print(f"LM {t['lm']:.0f} s, audio {t['audio']:.0f} s, master and MP3 {t['master']:.0f} s: {sum(t.values()):.0f} s "
          f"in all")
    print(mp3)


if __name__ == "__main__":
    main()
