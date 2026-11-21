#!/usr/bin/env python3
"""The download page for annejan.com/sunA/: every song in share.SONGS, grouped by day and genre, each with a plain
HTML audio player (the radio edit), the radio edit and the DJ version to download, and the lyric sheet.

site.py [DIR]   (default ../annejan/sunA, next to this repository: the site's own checkout)

Run share.py first: the MP3s and lyric sheets come from renders/share/. Writes DIR/index.html and DIR/sunA.css and
copies the files to DIR/radio/, DIR/dj/ and DIR/lyrics/ under short web names ("15-can-you-tell.mp3"). The page
needs nothing inline (the site's strict Content-Security-Policy) and only the site's /style.css besides its own.
The audio is about 270 MB: it belongs on the server, not in the site's git repository (its .gitignore).
"""
import html
import os
import re
import shutil
import subprocess
import sys

import share

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "annejan", "sunA")
GROUPS = [("Saturday: 90's mellow house", lambda day: day.startswith("Saturday")),
          ("Sunday: eurodance", lambda day: day.startswith("Sunday")),
          ("Rehearsals and a bonus", lambda day: not day.startswith(("Saturday", "Sunday")))]
KEYS = {"m": "minor", "": "major"}

CSS = """/* The sunA download page (site.py in github.com/annejan/sunA writes it). Shared layout comes from /style.css. */

.app .lede { color: var(--fg); font-size: 20px; line-height: 1.5; margin: 0 0 16px; text-wrap: balance; }
.song { margin: 0 0 28px; }
.song h4 { margin: 0; color: var(--fg); font-size: 15px; }
.song .when { margin: 2px 0 8px; color: var(--muted); font-size: 12px; letter-spacing: 1px; }
.song audio { display: block; width: 100%; margin: 0 0 8px; }
.song .get { margin: 0; }
.song .get a { margin-right: 16px; text-decoration: underline; text-decoration-color: var(--muted);
  text-underline-offset: 2px; }
.song .voices { margin: 6px 0 0; color: var(--muted); font-size: 12px; }
.made { margin-top: 40px; color: var(--muted); font-size: 12px; font-style: italic; }
/* The links in the side column stand out by more than colour (WCAG 1.4.1). */
aside li a { text-decoration: underline; text-decoration-color: var(--muted); text-underline-offset: 2px; }
"""


def slug(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower().replace("'", "")).strip("-")


def key_name(key):
    m = re.match(r"([A-G][#b]?)(m?)$", key)
    return f"{m.group(1).replace('b', '♭').replace('#', '♯')} {KEYS[m.group(2)]}"


def seconds(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    s = round(float(out))
    return f"{s // 60}:{s % 60:02d}"


def megabytes(path):
    return f"{os.path.getsize(path) / 1e6:.1f} MB"


def voices(sheet):
    """The voices line of a lyric sheet ("Words by Claude. Voices: ..."), as one line."""
    text = open(sheet, encoding="utf-8").read()
    m = re.search(r"Words by Claude\.(.*?)\n\n", text, re.S)
    return " ".join(m.group(1).split()) if m else ""


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    for d in ("radio", "dj", "lyrics"):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    groups = {g: [] for g, _ in GROUPS}
    for n, (wav, title, day, bpm, key, bars) in enumerate(share.SONGS, 1):
        radio = os.path.join(share.OUT, f"{n:02d} {title}.mp3")
        dj = os.path.join(share.OUT, "dj", f"{n:02d} {title} ({bpm} BPM, {key}).mp3")
        sheet = os.path.join(share.OUT, f"{n:02d} {title} - lyrics.txt")
        if not (os.path.exists(radio) and os.path.exists(dj)):
            print(f"skipped {title}: run share.py first")
            continue
        name = f"{n:02d}-{slug(title)}"
        for src, dst in ((radio, f"radio/{name}.mp3"), (dj, f"dj/{name}-dj.mp3"), (sheet, f"lyrics/{name}.txt")):
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(out, dst))
        genre = day.split(":", 1)[1].strip()
        group = next(g for g, test in GROUPS if test(day))
        e = html.escape
        lyr = f'<a href="lyrics/{name}.txt">Lyrics</a>' if os.path.exists(sheet) else ""
        groups[group].append(f"""          <article class="song" id="{slug(title)}">
            <h4>{e(title)}</h4>
            <p class="when">{e(genre)} · {bpm} BPM · {key_name(key)} · {seconds(radio)}</p>
            <audio controls preload="none" src="radio/{name}.mp3"></audio>
            <p class="get"><a href="radio/{name}.mp3" download>Radio edit <small>MP3, {megabytes(radio)}</small></a> <a href="dj/{name}-dj.mp3" download>DJ version <small>MP3, {megabytes(dj)}, {seconds(dj)}</small></a> {lyr}</p>
            <p class="voices">{e(voices(sheet)) if os.path.exists(sheet) else ""}</p>
          </article>""")
    sections = []
    for i, (group, songs) in enumerate(groups.items()):
        if songs:
            sections.append(f"""          <section aria-labelledby="g{i}">
            <h3 id="g{i}">{html.escape(group)}</h3>
{chr(10).join(songs)}
          </section>""")
    page = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>sunA: all-AI music, written in code – Anne Jan Brouwer</title>
    <meta name="description" content="The songs of an all-AI music compo: 90's mellow house and eurodance, every note and every sound written in code by Claude, sung by a DiffSinger voice. Radio edits and DJ versions to download." />
    <meta name="author" content="Anne Jan Brouwer" />
    <meta name="theme-color" content="#000000" />
    <link rel="icon" href="/favicon.ico" />
    <link rel="canonical" href="https://annejan.com/sunA/" />
    <meta property="og:type" content="website" />
    <meta property="og:url" content="https://annejan.com/sunA/" />
    <meta property="og:site_name" content="Anne Jan Brouwer" />
    <meta property="og:title" content="sunA: all-AI music, written in code" />
    <meta property="og:description" content="90's mellow house and eurodance, every note written in code by Claude. Radio edits and DJ versions." />
    <link rel="stylesheet" href="/style.css" />
    <link rel="stylesheet" href="/sunA/sunA.css" />
  </head>
  <body class="cv app">
    <div class="page">
      <header>
        <a href="/#draw" id="home" class="fade" title="Home"><img src="/ajb.svg" width="603" height="781" alt="Anne Jan Brouwer – home" /></a>
        <div>
          <h1>sunA</h1>
          <h2>All-AI music, written in code</h2>
        </div>
        <p class="www">annejan.com</p>
      </header>

      <div class="columns">
        <main>
          <section class="intro">
            <p class="lede">The songs for an all-AI music compo at a party with friends: Saturday 90's mellow house, Sunday eurodance.</p>
            <p>Every note and every sound is written in code by Claude: no samples, no loops, no song generator. The singer is <a href="https://wik-wav.neocities.org/lem-voicebank-tos">Lem the Shapeshifter DS 2.5</a> (DiffSinger), who sings the written notes and words, turned into Maya and Qwen voices with SoulX-Singer. The whole studio is in the <a href="https://github.com/annejan/sunA">sunA repository</a>.</p>
            <p>Every song comes in two versions. The <strong>radio edit</strong> starts where the music comes in and fades out. The <strong>DJ version</strong> is the whole track, with 16 bars of drums at each end for mixing.</p>
          </section>
{chr(10).join(sections)}
          <p class="made">Made with Claude: the songs, the lyrics and this page were written with an AI.</p>
        </main>

        <aside>
          <section>
            <h3>Source</h3>
            <ul>
              <li><a href="https://github.com/annejan/sunA">sunA</a> <small>MIT, the code</small></li>
            </ul>
          </section>
          <section>
            <h3>Licence</h3>
            <ul>
              <li><a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</a> <small>the music: some voice models are non-commercial</small></li>
            </ul>
          </section>
          <section>
            <h3>Voices</h3>
            <ul>
              <li>Lem the Shapeshifter DS 2.5 <small>DiffSinger</small></li>
              <li>Maya1, Qwen3-TTS <small>the timbres</small></li>
              <li>Piper <small>the rehearsals, choirs, MCs</small></li>
            </ul>
          </section>
        </aside>
      </div>
    </div>
  </body>
</html>
"""
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    with open(os.path.join(out, "sunA.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS)
    total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(out) for f in fs)
    print(f"wrote {out}/index.html: {sum(map(len, groups.values()))} songs, {total / 1e6:.0f} MB in all")


if __name__ == "__main__":
    main()
