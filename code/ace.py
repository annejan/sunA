#!/usr/bin/env python3
"""One command for the ACE-Step route: our song script -> our render (and stems) -> ACE-Step -> mastered for the
DJ -> a radio edit and a DJ version as MP3.

ace.py SONG [--mode cover|vocals|lego|text] [--strength 0.85] [--model base|turbo] [--ref] [--ace 1.0] [--era 90s] [--match 0.7]
            [--seed 1] [--caption "..."] [--tag NAME] [--check]

  SONG      a song script without .py, e.g. rhythm_of_the_badge (it must be in share.SONGS)
  cover     ACE-Step re-plays the whole song from our render (cover-nofsq): its sound and voices on our structure,
            tempo, key and melody; our 16-bar DJ intro and outro are spliced back in (master.py --dj-from)
  vocals    ACE-Step re-sings only our vocal stem; its take is lined up, gated by our vocals and woven over our own,
            unchanged instrumental (weave.py), --ace of it in the vocals
  lego      ACE-Step sings a new vocal track over our instrumental stem (base model, with the LM): our music, its
            voices and its own melody on our words; our DJ intro and outro are spliced back in
  text      ACE-Step makes its own song from a caption and our lyrics, at our tempo and key (it sets the
            arrangement itself); mastered onto the beat grid
  --strength how many of ACE-Step's steps see our audio (cover modes): 1 follows us closely, 0.3 loosely
  --ref     also pass our audio as the timbre reference: closer to our sound (and to Piper's robot voices)
  --check   run the speech recognizer over the result (asr.py) and report the words it hears

The lyrics come from lyrics/NN-*.txt, respelled for ACE-Step (ACE_SPELL: it reads text itself, not through
eSpeak). Everything lands in renders/ace/<song>/<tag>.wav and renders/ace/<song>/<Title> (<tag>, radio edit).mp3;
the request and the logs stay next to it. ACE-Step is acestep.cpp in ~/Projects/acestep.cpp (ACESTEP to move it).
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

import master
import share
import weave

HERE = os.path.dirname(os.path.abspath(__file__))
ACESTEP = os.environ.get("ACESTEP", os.path.expanduser("~/Projects/acestep.cpp"))
MODELS = os.path.join(ACESTEP, "models")
SYNTH = {"turbo": dict(synth_model="acestep-v15-turbo-Q8_0.gguf", inference_steps=8, guidance_scale=1.0, shift=3.0),
         "base": dict(synth_model="acestep-v15-base-Q8_0.gguf", inference_steps=50, guidance_scale=1.0, shift=1.0),
         # the tuned 50-step DiT: by ear far cleaner than base for text to music (gag.py, 18 November)
         "sft": dict(synth_model="acestep-v15-sft-Q8_0.gguf", inference_steps=50, guidance_scale=1.0, shift=1.0)}
LM = "acestep-5Hz-lm-4B-Q8_0.gguf"
# VAE tiles of 512 latent frames: the default 1024 crashed the GPU (vk::DeviceLostError) in 15 of 15 runs with
# the CPU busy, 512 in none of 15 (the soak of 19 November, research/night-tests.md)
VAE_CHUNK = "512"
def keyscale(key):
    """ACE-Step's key name: "F#m" -> "F# minor", "Bb" -> "Bb major"."""
    return f"{key[:-1]} minor" if key.endswith("m") else f"{key} major"

# ACE-Step reads the lyrics itself: these spellings come out right (found by ear: "Badgelink" gave badge-E-link,
# "Badglink" bad link)
ACE_SPELL = [
    (r"\bBadgelink\b|\bBadge link\b", "badge-link"),
    (r"\bUSB\b", "U S B"), (r"\bC6\b", "C six"), (r"\bP4\b", "P four"), (r"\bLED\b", "L E D"),
    (r"\bGPIO\b", "G P I O"), (r"\bPCB\b", "P C B"), (r"\bThreadSanitizer\b", "Thread Sanitizer"),
    (r"S-E-G-F-A-U-L-T!?", "S! E! G! F! A! U! L! T!"),
]

# the sound of each song, for the caption (from the style prompts in suno/, without the DJ intro and outro)
CAPTIONS = {
    "warm_boot": "90s deep house, mellow, warm Rhodes electric piano chords, Korg M1 organ stabs, round analog "
                 "bassline, shuffled 909 hi-hats, soft four on the floor kick, vinyl crackle, lush string pad, "
                 "soulful female vocal, breathy, sunrise, laid back",
    "packet_loss": "early 90s garage house, mellow, swung shuffle beat, deep organ bass, warm piano chords, soulful "
                   "male and female duet, call and response, smooth saxophone, rain on the window, late night",
    "low_battery": "instrumental 90s deep house, mellow, dreamy Rhodes chords, warm sub bass, shuffled 909 hats, "
                   "soft rimshots, airy pad, vinyl warmth, chopped female vocal sample, sunrise chill",
    "low_pass_love": "late 90s French house, filtered disco loop, slow low-pass filter sweeps, phaser, sidechain "
                     "pumping, funky bass guitar, Rhodes, talk box vocal hook, male disco vocal, warm and sunny",
    "segfault": "90s eurodance, powerful female diva vocal chorus, male rap verses, stabbing supersaw synth riff, "
                "Korg M1 piano, four on the floor kick, offbeat bass, open hi-hats, orchestra hits, euphoric, 1994, "
                "key change up for the last chorus",
    "blinky": "90s bubblegum eurodance, cute high female vocal, playful male shout-outs, bouncy synth riff, "
              "pizzicato strings, happy piano, four on the floor, offbeat bass, euphoric",
    "rhythm_of_the_badge": "mid 90s eurodance, dramatic female vocal, deep male rap, dark hoover synth, minor key "
                           "piano, big reverb snare, 909 kick, rolling offbeat bass, laser effects, dramatic, night "
                           "club, key change in the last chorus",
    "race_condition": "90s liquid drum and bass, chopped breakbeat, deep rolling sub bass, jazzy Rhodes chords, "
                      "soulful female vocal, male MC",
    "sdio_love": "80s Italo disco, male and female vocal duet, vocoder robot, arpeggiated octave synth bass, drum "
                 "machine, DX7 electric piano stabs and bells, dreamy synth melody, key change up for the last chorus",
    "flash_the_c6": "late 90s digital hardcore punk, distorted breakbeat, distorted gabber kick, noise guitar power "
                    "chords, sirens, shouted male and female punk vocals, gang vocal terrace chant, glitch stutter "
                    "edits, bit crush, tape stops, chiptune bleeps, riot, aggressive",
}
VOCALS_CAPTION = ("a cappella vocals only, no instruments: natural, warm, human voices, the same melody, words and "
                  "timing, 1994 studio recording, expressive, breathing, not robotic")


def song_info(script):
    """(n, wav, title, day, bpm, key, bars) from share.SONGS, matched by the render's name."""
    prefix = script.replace("_", "-") + "_"
    for n, row in enumerate(share.SONGS, 1):
        if row[0].startswith(prefix):
            return (n,) + row
    sys.exit(f"{script}: not in share.SONGS (add the song there first)")


# ACE-Step was trained on plain structure tags: our sheet's section names and roles mapped onto them (--native-tags)
NATIVE = [(r"intro", "Intro"), (r"outro", "Outro"), (r"pre.?chorus", "Pre-Chorus"), (r"chorus|hook|refrain", "Chorus"),
          (r"verse", "Verse"), (r"rap|mc|rapper", "Rap"), (r"bridge", "Bridge"), (r"build", "Build-up"),
          (r"break", "Break"), (r"drop", "Drop"), (r"spoken|system|computer|voice|robot|sanitizer", "Spoken"),
          (r"diva|her|him|singer|choir|vocal", "Verse")]


def native_tag(section):
    low = section.lower()
    for pat, tag in NATIVE:
        if re.search(pat, low):
            return tag
    return "Instrumental"


def ace_lyrics(n, t0=None, t1=None, native=False):
    """The lyric sheet as ACE-Step lyrics: [Section] tags, the sung words without the roles, respelled. With t0 and
    t1 (seconds): only the sections that start inside that stretch, or sing into it."""
    sheets = glob.glob(os.path.join(share.LYRICS, f"{n:02d}-*.txt"))
    if not sheets:
        return "[Instrumental]"
    lines = open(sheets[0], encoding="utf-8").read().splitlines()
    if t0 is not None:
        keep, times = [], []
        for line in lines:
            m = re.match(r"\[(\d+):(\d\d)\]", line.strip())
            times.append(int(m.group(1)) * 60 + int(m.group(2)) if m else None)
        starts = [t for t in times if t is not None]
        cur = None
        for line, t in zip(lines, times):
            if t is not None:
                nxt = next((s for s in starts if s > t), 10 ** 6)
                cur = t < t1 and nxt > t0
            if cur:
                keep.append(line)
        lines = keep
    out, started = [], False
    for line in lines:
        line = line.strip()
        m = re.match(r"\[\d+:\d\d\]\s*(.*)", line)
        started = started or bool(m)              # the header (title, voices) ends at the first time stamp
        if not started:
            continue
        if m:
            section = re.sub(r"\s*\(.*?\)", "", m.group(1)).strip()
            out += ["", f"[{section}]"]
            if ":" in section:     # "[1:58] MC: Warning..." : a timed line, the words after the role
                role, words = section.split(":", 1)
                out[-1] = f"[{role.strip()}]"
                out.append(words.strip())
        elif ":" in line and not line.startswith("("):
            out.append(line.split(":", 1)[1].strip())
    text = "\n".join(out).strip()
    text = re.sub(r"[ \t]*\([^)]*\)", "", text)          # stage directions in the sheet: "(in the echo)"
    if native:
        text = re.sub(r"\[([^\]]+)\]", lambda m: f"[{native_tag(m.group(1))}]", text)
        text = re.sub(r"(\[Instrumental\]\n*)+(?=\[Instrumental\])", "", text)   # one tag for a run of them
    for pat, rep in ACE_SPELL:
        text = re.sub(pat, rep, text)
    return re.sub(r"\n{3,}", "\n\n", text)


# One GPU door (19 November): every ACE-Step step goes through gpu(). The lock (flock on GPU_LOCK) lets several
# queues share the iGPU one job at a time (other GPU tools can take the same file); a timeout kills the job's whole
# process group (flock and the step under it); a VAE crash (vk::DeviceLostError) is tried once more. Before this only
# takes.py had a lock, and nothing had a timeout (research/toolkit-2026-11-19.md).
GPU_LOCK = os.environ.get("ACE_LOCK") or os.path.join(HERE, "renders", ".gpu.lock")


def gpu(cmd, log, timeout=1800, retries=1):
    """Run one GPU step behind the lock, its output to `log`; True when it worked. `timeout` (s) counts the wait for
    the lock too."""
    import signal
    import time
    os.makedirs(os.path.dirname(GPU_LOCK), exist_ok=True)
    for attempt in range(retries + 1):
        with open(log, "w") as fh:
            p = subprocess.Popen(["flock", GPU_LOCK, *cmd], stdout=fh, stderr=subprocess.STDOUT,
                                 start_new_session=True)
            try:
                rc = p.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
                print(f"killed after {timeout} s: {os.path.basename(cmd[0])} (see {log})", file=sys.stderr)
                return False
        if rc == 0:
            return True
        lost = "DeviceLost" in open(log, errors="replace").read()
        print(f"{os.path.basename(cmd[0])} failed (exit {rc}{', DeviceLost' if lost else ''}): see {log}",
              file=sys.stderr)
        if not lost or attempt == retries:
            return False
        time.sleep(5)
    return False


def run(cmd, log):
    if not gpu(cmd, log):
        sys.exit(f"failed: {' '.join(cmd)} (see {log})")


import engine as _engine  # noqa: E402
TEST_VARS = _engine.AB_VARS      # engine.mixdown sends renders with these switches to renders/scratch/


def script_name(song):
    """The song script's name: as given when code/<song>.py exists, else with - for _ (sdio-love: sdio_love)."""
    return song if os.path.exists(os.path.join(HERE, song + ".py")) else song.replace("-", "_")


def render(script, wav, env=None):
    """Our render: the song script, again only when the script is newer than the render."""
    test = [k for k in TEST_VARS if os.environ.get(k)]
    if test:
        sys.exit(f"{', '.join(test)} set: that render goes to renders/scratch/, not to the song's render. Unset it, "
                 f"or render the test to a file and give it with produce.py --ours FILE")
    out = os.path.join(share.RENDERS, wav) if not os.path.isabs(wav) else wav
    src = os.path.join(HERE, script + ".py")
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        print(f"render {os.path.basename(out)}", flush=True)
        subprocess.run([sys.executable, "-W", "ignore", src, out], env=dict(os.environ, **(env or {})), check=True,
                       stdout=subprocess.DEVNULL)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("song")
    ap.add_argument("--mode", choices=["cover", "vocals", "lego", "text"], default="cover")
    ap.add_argument("--strength", type=float, default=.85)
    ap.add_argument("--model", choices=["base", "turbo", "sft"], default="base")
    ap.add_argument("--ref", action="store_true", help="our audio as the timbre reference too")
    ap.add_argument("--ace", type=float, default=1.0, help="vocals mode: ACE-Step's share of the vocals")
    ap.add_argument("--era", choices=["90s"])
    ap.add_argument("--match", type=float, default=0.0, help="cover, lego: 0-1, the tonal balance of our render")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--guidance", type=float, help="the DiT's CFG (SFT preset 1.0; 7.0 with --shift 3 won round two)")
    ap.add_argument("--shift", type=float, help="the DiT's schedule shift (SFT preset 1.0)")
    ap.add_argument("--caption", help="replace the song's caption")
    ap.add_argument("--lyrics", help="a text file with the lyrics (ACE-Step format, [Section] tags) instead of the sheet")
    ap.add_argument("--native-tags", action="store_true", help="map the sheet's sections to ACE-Step's own tags")
    ap.add_argument("--tag", help="the output's name (default: mode, model, strength, seed)")
    ap.add_argument("--check", action="store_true", help="the speech recognizer over the result")
    a = ap.parse_args()
    a.song = script_name(a.song)        # sdio-love works too

    n, wav, title, day, bpm, key, bars = song_info(a.song)
    tag = a.tag or (f"{a.mode}-{a.model}-{a.strength:g}-s{a.seed}" if a.mode in ("cover", "vocals")
                    else f"{a.mode}-s{a.seed}")
    if a.era:
        tag += f"-{a.era}"
    if a.match:
        tag += f"-m{a.match:g}"
    out = os.path.join(share.RENDERS, "ace", a.song)
    os.makedirs(out, exist_ok=True)
    t0 = time.time()

    full = render(a.song, wav)
    src = full
    if a.mode in ("vocals", "lego"):
        inst = render(a.song, os.path.join(out, "stem_inst.wav"), {"MUTE": "vox"})
        vox = render(a.song, os.path.join(out, "stem_vox.wav"), {"MUTE": "drums,perc,bass,pads,keys,lead,fx"})
        src = vox if a.mode == "vocals" else inst
    if a.mode == "lego" and a.model != "base":
        sys.exit("lego needs the base model (--model base)")

    caption = a.caption or (VOCALS_CAPTION if a.mode == "vocals" else CAPTIONS.get(a.song, day.split(": ")[1]))
    lyrics = open(a.lyrics, encoding="utf-8").read() if a.lyrics else ace_lyrics(n, native=a.native_tags)
    req = {"caption": caption, "lyrics": lyrics, "bpm": bpm, "keyscale": keyscale(key),
           "timesignature": "4", "vocal_language": "en", "seed": a.seed, "output_format": "wav16", **SYNTH[a.model]}
    if a.guidance:
        req["guidance_scale"] = a.guidance
    if a.shift:
        req["shift"] = a.shift
    base = os.path.join(out, tag)
    if a.mode in ("text", "lego"):
        req.update(duration=round(bars * 240 / bpm + 2), lm_model=LM)
        if a.mode == "lego":
            req.update(task_type="lego", track="vocals")
        json.dump(req, open(base + ".json", "w"), indent=1)
        run([os.path.join(ACESTEP, "build", "ace-lm"), "--models", MODELS, "--request", base + ".json",
             "--device", "Vulkan0"], base + ".lm.log")
        synth_req = base + "0.json"
        cmd = ["--src-audio", src] if a.mode == "lego" else []
    else:
        req.update(task_type="cover-nofsq", audio_cover_strength=a.strength)
        json.dump(req, open(base + ".json", "w"), indent=1)
        synth_req = base + ".json"
        cmd = ["--src-audio", src] + (["--ref-audio", src] if a.ref else [])
    run([os.path.join(ACESTEP, "build", "ace-synth"), "--models", MODELS, "--request", synth_req, *cmd,
         "--device", "Vulkan0", "--vae-chunk", VAE_CHUNK], base + ".synth.log")
    raw = synth_req[:-5] + "0.wav"
    print(f"ACE-Step: {time.time() - t0:.0f} s", flush=True)

    final = base + ".wav"
    if a.mode in ("cover", "lego"):
        print(master.process(raw, final, bpm, era=a.era, dj_from=full, bars=bars, match=a.match))
    elif a.mode == "vocals":
        print(weave.process(inst, vox, raw, full, final, bpm, ace=a.ace))
    else:
        print(master.process(raw, final, bpm, era=a.era))

    tags = ["-metadata", f"title={title} ({tag})", "-metadata", "artist=sunA"]
    share.encode(final, os.path.join(out, f"{title} ({tag}, radio edit).mp3"), tags, [],
                 share.radio_window(bpm, bars, wav))
    if a.check:
        import asr
        sheet = glob.glob(os.path.join(share.LYRICS, f"{n:02d}-*.txt"))
        print(asr.report(final, asr.sheet_text(sheet[0])) if sheet else "no lyric sheet to check against")
    print(f"done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
