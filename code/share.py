#!/usr/bin/env python3
"""Encode the renders for sharing in a chat app such as Signal: MP3 at 320 kbit/s with title tags, under 10 MB per
song (Signal's limit is 100 MB), plays on every phone. The lyric sheets from lyrics/ go in the tags and next to them.

The renders are DJ versions (16 bars of drums at each end, for the compo). For sharing, each song also gets a radio
edit: from where the music comes in (bar 16) to two bars into the outro, with a fade over the last four bars (two
for a song in RADIO_FADE_BARS).

share.py            writes renders/share/NN Title.mp3 (the radio edit) and NN Title - lyrics.txt (its times),
                    and renders/share/dj/NN Title (BPM, key).mp3 (the DJ version) for every song that is rendered
"""
import re
import glob
import os
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
RENDERS = os.path.join(HERE, "renders")
LYRICS = os.path.join(os.path.dirname(HERE), "lyrics")
OUT = os.path.join(RENDERS, "share")

DJ_BARS = 16      # drums only at each end
# file, title, day, BPM, key, bars
SONGS = [
    ("warm-boot_120bpm_Am.wav", "Warm Boot", "Saturday: 90's mellow house", 120, "Am", 120),
    ("packet-loss_122bpm_Fm.wav", "Packet Loss (Of Love)", "Saturday: 90's mellow house", 122, "Fm", 120),
    ("low-battery_120bpm_Dm.wav", "Low Battery Lullaby", "Saturday: 90's mellow house", 120, "Dm", 120),
    ("low-pass-love_122bpm_Am.wav", "Low Pass Love", "Saturday: 90's mellow house", 122, "Am", 128),
    ("segfault_132bpm_Am.wav", "Segfault (In My Heart)", "Sunday: eurodance", 132, "Am", 112),
    ("blinky_132bpm_D.wav", "Blinky (The LED Song)", "Sunday: eurodance", 132, "D", 112),
    ("rhythm-of-the-badge_134bpm_Em.wav", "The Rhythm Of The Badge", "Sunday: eurodance", 134, "Em", 120),
    ("race-condition_174bpm_Fm.wav", "Race Condition", "Rehearsal: drum and bass", 174, "Fm", 144),
    ("sdio-love_120bpm_Dm.wav", "S.D.I.O. (I Love You So)", "Rehearsal: Italo disco", 120, "Dm", 112),
    ("flash-the-c6_174bpm_Fm.wav", "Flash The C Six", "Bonus: digital hardcore", 174, "Fm", 144),
    ("push-it-to-prod_124bpm_Em.wav", "Push It To Prod", "Rehearsal: big beat", 124, "Em", 112),
    ("uptime-fever_120bpm_Am.wav", "Uptime Fever", "Rehearsal: disco", 120, "Am", 112),
    ("rubber-duck_120bpm_Dm.wav", "Rubber Duck", "Rehearsal: disco", 120, "Dm", 112),
    ("common-ground_120bpm_Cm.wav", "Common Ground", "Saturday: 90's mellow house", 120, "Cm", 112),
    ("can-you-tell_136bpm_Cm.wav", "Can You Tell?", "Sunday: eurodance", 136, "Cm", 128),
    ("keep-alive_118bpm_Gm.wav", "Keep Alive", "Saturday: 90's mellow house", 118, "Gm", 112),
    ("nothings-broken_122bpm_F.wav", "Nothing's Broken", "Saturday: 90's mellow house", 122, "F", 112),
    ("lego-op-de-vloer_132bpm_C.wav", "Lego Op De Vloer", "Round two: Kinderen voor Kinderen", 132, "C", 76),
]


RADIO_FADE_BARS = {"flash-the-c6_174bpm_Fm.wav": 2}    # its last bars before the outro are the punchline ("Told you.")
NO_DJ_ENDS = {"lego-op-de-vloer_132bpm_C.wav"}   # round two: no drum ends (the user); the radio edit is it all


def radio_window(bpm, bars, wav=None):
    """(start, length, fade) in seconds: from the end of the DJ intro to two bars into the DJ outro. The fade is four
    bars, or a song's own length in RADIO_FADE_BARS."""
    bar = 240 / bpm
    if wav in NO_DJ_ENDS:
        return 0.0, (bars + 2) * bar, 0.0
    start = DJ_BARS * bar
    end = (bars - DJ_BARS + 2) * bar
    return start, end - start, RADIO_FADE_BARS.get(wav, 4) * bar


def shift_sheet(text, start, length):
    """The lyric sheet with its [m:ss] times moved to the radio edit; sections outside it are left out."""
    out, keep = [], True
    for line in text.splitlines():
        m = re.match(r"\[(\d+):(\d\d)\](.*)", line)
        if m:
            t = int(m.group(1)) * 60 + int(m.group(2)) - start
            keep = 0 <= t + .5 < length - 1
            if keep:
                t = max(t, 0)
                line = f"[{int(t // 60)}:{int(t % 60):02d}]{m.group(3)}"
        if keep or not line.strip():
            out.append(line)
    first = next((i for i, x in enumerate(out) if x.startswith("[")), len(out))
    out.insert(max(first - 1, 0), f"Radio edit, {int(length // 60)}:{int(length % 60):02d}: the times below are for this edit.")
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).rstrip() + "\n"


def encode(src, dst, tags, words, cut=None):
    pre = []
    af = []
    if cut:
        start, length, fade = cut
        pre = ["-ss", f"{start:.4f}", "-t", f"{length:.4f}"]
        af = ["-af", f"afade=t=in:d=0.01,afade=t=out:st={length - fade:.4f}:d={fade:.4f}"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *pre, "-i", src, *af, "-c:a", "libmp3lame", "-b:a", "320k",
                    *tags, *words, "-id3v2_version", "3", dst], check=True)
    print(f"{os.path.relpath(dst, os.path.dirname(os.path.abspath(__file__)))}: {os.path.getsize(dst) / 1e6:.1f} MB")

if __name__ == "__main__":
    import sys
    # share.py [--only song,song]: only these songs (their WAV's name, like warm-boot or warm_boot); all by default
    only = None
    if "--only" in sys.argv:
        only = {x.replace("_", "-") for x in sys.argv[sys.argv.index("--only") + 1].split(",")}
        names = {w.split("_")[0] for w, *_ in SONGS}
        if only - names:
            raise SystemExit(f"not in SONGS: {', '.join(sorted(only - names))} (the names: {', '.join(sorted(names))})")
    os.makedirs(os.path.join(OUT, "dj"), exist_ok=True)
    for old in glob.glob(os.path.join(OUT, "* BPM, *).mp3")):     # the DJ versions used to live at the top
        os.remove(old)
    for n, (wav, title, day, bpm, key, bars) in enumerate(SONGS, 1):
        if only and wav.split("_")[0] not in only:
            continue
        src = os.path.join(RENDERS, wav)
        if not os.path.exists(src):
            print(f"skip {wav}: not rendered")
            continue
        sheets = glob.glob(os.path.join(LYRICS, f"{n:02d}-*.txt"))
        sheet = open(sheets[0], encoding="utf-8").read() if sheets else ""
        cut = radio_window(bpm, bars, wav)
        radio_sheet = shift_sheet(sheet, cut[0], cut[1]) if sheet else ""
        tags = ["-metadata", "artist=sunA", "-metadata", "album=slop-music-compo-entries",
                "-metadata", f"comment={day}", "-metadata", f"genre={day.split(': ')[1]}",
                "-metadata", f"track={n}/{len(SONGS)}", "-metadata", f"TBPM={bpm}", "-metadata", f"TKEY={key}"]
        encode(src, os.path.join(OUT, f"{n:02d} {title}.mp3"), tags + ["-metadata", f"title={title}"],
               ["-metadata", "lyrics=" + radio_sheet] if radio_sheet else [], cut)
        encode(src, os.path.join(OUT, "dj", f"{n:02d} {title} ({bpm} BPM, {key}).mp3"),
               tags + ["-metadata", f"title={title} (DJ version)"], ["-metadata", "lyrics=" + sheet] if sheet else [])
        if radio_sheet:
            with open(os.path.join(OUT, f"{n:02d} {title} - lyrics.txt"), "w", encoding="utf-8") as fh:
                fh.write(radio_sheet)
        if sheet:
            shutil.copyfile(sheets[0], os.path.join(OUT, "dj", f"{n:02d} {title} - lyrics.txt"))
