# MOD music

ProTracker modules (M.K., 4 channels, 31 samples) written from Python, with the ST-XX sample disks (the Amiga
Soundtracker instrument disks, 1987-1991, from Aminet) in `~/Music/st-xx` (`ST_PACK` to move it). The samples are
not in this repository; the modules (`out/`, not in git) carry them.

| File | What |
|---|---|
| `mod.py` | the writer: `Module`, `sample()`, `pattern()`, `put(row, ch, note, sample, effect)`, `write()`, and `render()` (libopenmpt through ffmpeg, to WAV or MP3) |
| `st_index.py`, `st_index.csv` | the index of all 10 646 samples: kind, pitch (note at C-2 and how sure), tonal or noisy, percussive or held, length, loudness, the 8SVX header's rate and loop, and the transpose and finetune that put it in tune |
| `floppy_hardcore.py` | early rave (1991), 134 BPM, A minor: break, bass, M1 piano arpeggios, orchestra hits |
| `break_test.py`, `bass_test.py` | auditions: breaks and basses from the pack |

```sh
../code/.venv/bin/python st_index.py build                              # about 2 seconds, 16 processes
../code/.venv/bin/python st_index.py find --cat piano --tonal --max 10    # the clearest pianos first
../code/.venv/bin/python st_index.py find --cat bass --note C --min-conf 40
../code/.venv/bin/python st_index.py show "ST-44/m1piano8'"
../code/.venv/bin/python floppy_hardcore.py                              # out/floppy_hardcore.mod and .mp3
```

- `m.sample(path, tune=True)`: the notes you write sound as written (the index's transpose and finetune). Without
  it a sample plays at its own pitch: the M1 piano on ST-44 sounds F# at C-2, so every chord came out a tritone off.
- Half the pack is IFF 8SVX (a header, then the audio): `st_index.load` reads both kinds, so no header plays as a
  click. `loop="auto"` takes the 8SVX header's loop.
- `rate` is the 8SVX header's sample rate (IFF files only; raw files have no header). `bandwidth` is measured for
  every sample: Hz below which 99 % of its energy lies, played at C-2 (at most 4143); `find --min-bw 3000` keeps the
  bright ones. `render(..., bitrate="320k", rate=44100)` sets the MP3's bitrate and the output rate.
- Drums (kick, snare, hat, cymbal, tom, perc, break) get no tuning: their pitch is not a note.
- The categories are a guess: the name first (English, German and Dutch names of the time), then the sound.
- Tempo: speed 6 (`F06`) and the BPM (`F86` is 134). A break plays one bar when its length matches: break004 at B-2
  is one bar at 134 BPM. `9xx` starts a sample xx*256 bytes in (chops, snare rolls); `0xy` is the arpeggio chord.
