# sunA

sunA is the AI artist behind these entries for an AI slop music compo at a
party with friends. Every day of the party has two themes. The first theme of
each day is known in advance. The second theme comes two hours before the
deadline.

| Day | Theme | Tempo |
|---|---|---|
| Saturday | 90's mellow house | 120 BPM |
| Saturday | surprise | genre norm |
| Sunday | eurodance | 132 BPM |
| Sunday | surprise | genre norm |

The DJ mixes the tracks live, so each track keeps one tempo from start to end,
and starts and ends with 16 bars of drums only.

**For the compo weekend: [WEEKEND.md](WEEKEND.md)**, the playbook: the surprise round step by step, the
commands, the voice cast, what the ears decided, trouble and fixes, timings.

## Our rules

- **All AI.** Every part of every entry is made by AI: the music, the voices
  and the lyrics. Nobody edits the audio by hand.
- **Open tools only.** We use software and models under open terms: public
  domain, CC (non-commercial is fine, this is a fun competition), MIT, BSD,
  GPL. No closed music services such as Suno. One voicebank (Hoshino Hanami)
  has its own free licence; we allowed it.

[SONGS.md](SONGS.md) lists, per song, which AI made which part and which tools,
sounds and voices it uses. The lyric sheets are in [lyrics/](lyrics/).

## The songs

Claude writes every song as a Python script: every note and every sound is in
the source, with no samples and no loops. Warm Boot and Segfault are our
entries; the other five are the other takes from `suno/`, made as code tracks
for fun. Race Condition and S.D.I.O. are rehearsals for the surprise themes,
and Flash The C Six is a bonus: digital hardcore.

| Script | Theme | Tempo, key | Length |
|---|---|---|---|
| [warm_boot.py](code/warm_boot.py) | 90's mellow house | 120 BPM, A minor | 4:02 |
| [packet_loss.py](code/packet_loss.py) | 90's mellow house | 122 BPM, F minor | 3:58 |
| [low_battery.py](code/low_battery.py) | 90's mellow house | 120 BPM, D minor | 4:02 |
| [low_pass_love.py](code/low_pass_love.py) | 90's mellow house (French house) | 122 BPM, A minor | 4:14 |
| [segfault.py](code/segfault.py) | eurodance | 132 BPM, A minor, then B minor | 3:26 |
| [blinky.py](code/blinky.py) | eurodance | 132 BPM, D major, then E major | 3:26 |
| [rhythm_of_the_badge.py](code/rhythm_of_the_badge.py) | eurodance | 134 BPM, E minor, then F# minor | 3:37 |
| [race_condition.py](code/race_condition.py) | rehearsal: drum and bass | 174 BPM, F minor | 3:21 |
| [sdio_love.py](code/sdio_love.py) | rehearsal: Italo disco | 120 BPM, D minor, then E minor | 3:46 |
| [push_it_to_prod.py](code/push_it_to_prod.py) | rehearsal: big beat | 124 BPM, E minor | 3:39 |
| [uptime_fever.py](code/uptime_fever.py) | rehearsal: disco | 120 BPM, A minor | 3:46 |
| [rubber_duck.py](code/rubber_duck.py) | rehearsal: disco | 120 BPM, D minor | 3:46 |
| [flash_the_c6.py](code/flash_the_c6.py) | bonus: digital hardcore | 174 BPM, F minor | 3:21 |

## How a song is made

```
compose   song script (code/*.py), PREVIEW per section
render    renders/*.wav (the DJ version), stems with MUTE
produce   produce.py: ACE-Step re-plays it, section by section (projects/<song>.toml)
          or ace.py: one ACE-Step pass (cover, vocals, lego, text)
master    master.py / weave.py: on the grid, our DJ intro and outro, -9/-10 LUFS, -1.2 dBTP
check     asr.py: which words come through
deliver   share.py (radio edit + DJ version as MP3), dj.py (the USB stick),
          mix.py (a day as the DJ would play it: to hear that the songs mix)
```

1. **The code track.** The script writes a 44.1 kHz, 16-bit stereo WAV. The
   beat grid starts at sample 0 and the tempo is exact. A song renders in 18 to
   34 seconds once its speech is cached (see
   [render-speed.md](research/render-speed.md)).
2. **ACE-Step (optional).** [ace.py](code/ace.py) gives the render to
   [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5), an open song
   generator by ACE Studio and StepFun (MIT) that runs on this laptop's GPU
   through Vulkan ([acestep.cpp](https://github.com/ServeurpersoCom/acestep.cpp)),
   and masters the result for the DJ. See "ACE-Step" below.
3. **Sharing.** [share.py](code/share.py) makes a radio edit of every song
   (from where the music comes in to two bars into the outro, with a fade) and
   the DJ version, as 320 kbit/s MP3 with the lyrics in the tags.
4. **The DJ.** [dj.py](code/dj.py) puts every song as a WAV with its tempo and
   Camelot key in the name in `renders/dj/`, with a track list, and checks the
   true peak, the loudness, the beat grid and the drums-only intro and outro.

## Setup

```sh
cd code
uv venv .venv && uv pip install --python .venv/bin/python piper-tts pyworld 'setuptools<81' numpy scipy faster-whisper
mkdir -p voices && cd voices
../.venv/bin/python -m piper.download_voices en_US-hfc_female-medium en_US-ryan-high   # and the other voices the songs use
# more voices (19 November): Dutch (nl_NL pim, ronnie, alex; nl_BE nathalie, rdh, flemishguy; CC0), characters
# (en_GB-semaine-medium: prudence, spike (angry), obadiah (gloomy), poppy (cheerful); CC BY-NC-SA), and many-speaker
# models for gang shouts (en_US-libritts_r-medium, 904 speakers; en_GB-vctk-medium, 109; CC BY 4.0). A speaker of a
# many-speaker model is "voice#speaker", by name or number: en_GB-semaine-medium#spike, en_US-libritts_r-medium#12
# three more voice engines (19 November; the user: "way better than other options so far"), installed outside
# this repository (research/toolkit-2026-11-19.md): "kokoro:af_bella" or "kokoro:am_fenrir@1.2" (Kokoro-82M presets,
# CPU, ~/Projects/kokoro), "qwen:<a voice described in words>#42" (Qwen3-TTS VoiceDesign, GPU, ~/Projects/qwentts.cpp;
# the seed keeps one voice), "maya:<a voice described in words>#301" with tags like <excited>, <whisper>, <angry> in
# the text (Maya1, GPU, slow: about 17 s for a 4 s line, ~/Projects/maya1 and ~/Projects/llama.cpp); GPU engines take
# the ACE-Step GPU lock
# the cast (voice.CAST, voice.ROLES): named voices for spoken parts. A song asks for a part by its role, "cast:mc"
# (mc, narrator, announcer, robot, whisper, diva, angry, dutch; Maya1 by default, the user's pick); CAST="mc=qwen_hype,
# narrator=piper_ryan" switches voices for one render. Emotion tags in the text reach only Maya. To hear a line in
# 15 voices, one MP3 (about 3 minutes):  .venv/bin/python voice.py --audition "<excited> Make some noise!" [--voices a,b]
../.venv/bin/python -m piper.download_voices nl_NL-pim-medium nl_NL-ronnie-medium nl_NL-alex-medium nl_BE-nathalie-medium \
  nl_BE-rdh-medium nl_BE-flemishguy-medium en_GB-semaine-medium en_GB-vctk-medium en_US-libritts_r-medium \
  en_GB-northern_english_male-medium en_US-mike-medium
cd ..
.venv/bin/python warm_boot.py      # writes renders/warm-boot_120bpm_Am.wav
```

Optional parts, outside this repository:

| Part | For | Where |
|---|---|---|
| [eSpeak NG](https://github.com/espeak-ng/espeak-ng), [Flite](http://www.festvox.org/flite/), [Festival](https://www.cstr.ed.ac.uk/projects/festival/) | the classic voices in `trials.py` | `sudo zypper in espeak-ng flite festival` |
| [Mimic 3](https://github.com/MycroftAI/mimic3) | more classic voices | its own Python 3.11 venv, `code/.venv-mimic3` |
| [warble](https://github.com/erz0r/warble) and [DiffSinger](https://github.com/openvpi/DiffSinger) voicebanks ([Hoshino Hanami](https://lottev.moe/hoshino-hanami-ai%e2%9d%a4dol-for-diffsinger-v1-0-is-out/), [TIGER](https://tigermeat.xyz/cast/tiger/)) | `ds.py`: a DiffSinger singer | `~/Projects/diffsinger/warble`, `~/Projects/diffsinger/banks` (or `WARBLE`, `WARBLE_BANKS`) |
| [acestep.cpp](https://github.com/ServeurpersoCom/acestep.cpp) and its [GGUF models](https://huggingface.co/Serveurperso/ACE-Step-1.5-GGUF) (12 GB), converted from [ACE-Step 1.5](https://huggingface.co/ACE-Step/Ace-Step1.5) | `ace.py`: ACE-Step | `~/Projects/acestep.cpp`, built with `./buildvulkan.sh` (needs `spirv-headers`) |

## The tools in `code/`

| File | What it does |
|---|---|
| [engine.py](code/engine.py) | oscillators, instruments, drums, the formant robot, and the mixdown: sidechain, delay, reverb, glue compressor, true-peak limiter to a loudness target |
| [dx7.py](code/dx7.py) | a DX7-style FM synthesizer: six operators, the 32 algorithms, feedback, keyboard scaling (ported from an NPU demo in `~/Projects/npu`) |
| [room.py](code/room.py) | a 3-D wave simulation of the air in a room; its impulse response is a song's reverb (also from the NPU demos) |
| [voice.py](code/voice.py) | Piper speaks each word, WORLD puts it on our notes (see Voices) |
| [ds.py](code/ds.py) | a DiffSinger voicebank sings a whole part, through warble; `render(timbre=...)` sings the same performance again in another voice (SoulX-Singer SVC, audio.cpp, about 2x real time on the GPU, cached): our notes and words, a Maya or Qwen voice from `voice.CAST` (`maya_diva`, `qwen_diva`, the `sing_*` cast) |
| [vfx.py](code/vfx.py) | the vocal rack for a dry sung part: `vocoder()` (the voice's formants on a saw-chord carrier, consonants kept), `autotune()` (fit.snap hard or natural), `harmony()` (Rubber Band stacks, formants kept), `stack()` (doubles: other takes, other singers, panned and a few ms apart) |
| [parts.py](code/parts.py), [template.py](code/template.py) | ready parts and a whole song to start from, for the surprise themes |
| [ace.py](code/ace.py) | one command for ACE-Step: render, stems, ACE-Step, mastering, MP3. `ace.gpu()` is the one GPU door for every ACE-Step step (ace.py, takes.py, produce.py, gag.py): a lock (`ACE_LOCK=FILE`, default `renders/.gpu.lock`) so queues take turns, a timeout that kills the whole job, one retry after a VAE crash |
| [produce.py](code/produce.py) | a song section by section from a project file: an ACE-Step take of the whole song, then per section our own render, the take, or a `repaint` with several seeds of which the ear picks the best; everything cached |
| [master.py](code/master.py) | another generator's take to DJ shape: on the beat grid, 44.1 kHz, -10 LUFS, -1.2 dBTP; `--dj-from` splices our DJ intro and outro back in; `--era 90s`; `--match 0.7` our render's tonal balance and width |
| [weave.py](code/weave.py) | our instrumental, unchanged, under a blend of our vocals and another generator's take of them |
| [asr.py](code/asr.py) | a speech recognizer ([faster-whisper](https://github.com/SYSTRAN/faster-whisper), OpenAI's [Whisper](https://github.com/openai/whisper) base.en) checks which words of the lyrics can be heard |
| [share.py](code/share.py), [dj.py](code/dj.py) | MP3s for sharing; WAVs and a track list for the DJ. `share.py --only warm-boot,segfault` encodes only those; `dj.py --only` and `--use` stop on a name that is not in share.SONGS (it used to write nothing, without a word); a DJ line says when a render is older than its script |
| [site.py](code/site.py) | the download page for annejan.com/sunA/: every song with a plain HTML player, the radio edit and the DJ version, the lyric sheet, by day and genre; writes `../annejan/sunA/` (run `share.py` first). The MP3s go to the server with rsync, not into the site's git |
| `gag.py --guidance 7 --shift 3`, `takes.py --drafts --lang nl` | ACE-Step with CFG on (the docs' values; the SFT preset is 1.0 and 1.0): about twice as slow, for a keeper; `--lang` sets the sung language of a draft round (Dutch for round two, Lego Op De Vloer) |
| [mix.py](code/mix.py) | a day's songs as one DJ set: one tempo (varispeed), each song over the 16-bar outro of the one before, the lows swapped 4 bars before the end, the keys checked on the Camelot wheel; `--order auto` for the fewest key clashes, `--use` for produced versions |
| [trials.py](code/trials.py) | renders Segfault with many voice pairs, to compare them |
| [quick_gag.py](code/quick_gag.py) | a gag from one line ("Dubstep, English, time to take the bus"): Qwen 3.5 9B on the NPU (FastFlowLM, its own server) writes the title, words, style, tempo, key and language, ACE-Step's 1.7B LM and turbo make it; about 2 minutes, all on this laptop (no internet). About the request only; `--nerd` bends it towards the hardware-hacker crowd. When Qwen's words are not in sung lines, Qwen sets them itself in a second pass. `--best` for the 4B LM and SFT |
| [gag.py](code/gag.py) | a quick ACE-Step song from words and a style, for the group chat (not for the DJ): the 4B LM and the SFT DiT, about 2.5 minutes for 2 minutes of music; `--fast` about 70 s Each seed other than 1 gets its own folder and file (`<title>-seed2/`): the same title used to overwrite seed 1. |
| [takes.py](code/takes.py) | research: ACE-Step sings a song's lines a cappella (4B LM and SFT DiT) in several seeds, about 25 s a take; one MP3 with our bars, then each take laid over them at -8 dB, with spoken labels. `--menu`: kinds of voice for surprise day. `--lift 3`: sung 3 semitones lower and slower, lifted to the song's tempo and key by Rubber Band (`rubberband-cli`): the sped-up 90s eurodance voice, picked by ear. `--drafts`: a draft round, 4 tunes from one LM run (`lm_batch_size`, fixed `lm_seed`) rendered with the SFT DiT and a negative prompt against instruments (`takes.LM_NEGATIVE`; about 2 minutes for 4), each split by sep.py when ACE-Step still put a band under the voice, ranked by fit.py (chord fit and register), best first, brought to the song's tempo and measured key; `--keep DRAFT.json` renders the pick again with SFT at `--guidance 7 --shift 3` (an A/B; the key can move, so `--chords` measures the keeper; a keeper with a band gives its voice alone); `pin()` gives a song its take as a file. `ACE_LOCK=FILE` shares the GPU with another queue |
| [kit_template.py](code/kit_template.py) | the start of a surprise-round song on one of the 11 kits (`cp kit_template.py my_song.py`; set `KIT_NAME`, `TITLE`, `DAY`, the spoken lines): the kit's parts, the pinned ACE-Step diva take (`renders/ace/takes/<name>/pinned/chorus.wav`) played whole in the choruses, spoken parts by cast role; the file name gives the render's name. A test render passes dj.check |
| [chops.py](code/chops.py) | ACE-voiced sampler chops, the 1990s house vocal stab: words cut from an ACE-Step a cappella take (faster-whisper's word times), each tuned with WORLD to the tone of the bar's chord nearest its own pitch, played from a 16-step pattern (a chop stops where the next starts; swing as the song's). `warm_boot.py` with `CHOPS=1` uses it while the song winds down (an A/B, not heard yet) |
| [sep.py](code/sep.py) | the voice alone from an ACE take: Mel-Band RoFormer (audio.cpp v0.9.5 prebuilt, `~/Projects/audiocpp/v095`, model in `~/Projects/audiocpp-models/Mel-Band-RoFormer-GGUF`, behind the GPU lock), about 0.8x real time; `<take>_vox.wav` and the band's level (clean below -25 dB). ACE-Step ignores "a cappella" in about half the takes on disk: the rehearsal's Pull-Up Resistor diva had a band at -3 dB under her |
| [fit.py](code/fit.py) | how a free ACE take fits the band: its steady notes (pyworld) against the chord tones bar by bar; the scale fit narrows the key shifts, the chord fit and the register pick one, offsets in 2-bar steps (the phrase grid); the register after the shift (HIGH above A#4 / G5, ranked lower); flags takes that end mid-word. About 2 s a take, CPU. It decides what the user hears first, never what is used (Uptime Fever's approved take measures poorly). `--snap natural|hard` retunes a take onto the chords with WORLD (each steady note to the nearest tone of the chord under it, at most 2 semitones; natural keeps the vibrato, hard is the Cher effect; frame-exact, so it stays on the grid): the Hi-NRG take went from 26 to 55-58 % on the chord tones, about 10 s |
| [kits.py](code/kits.py) | research: genre kits for the 11 untried surprise genres (trance, eurobeat, hardstyle, gabber, happy hardcore, chiptune, techno, acid house, synthwave, Hi-NRG, carnaval): tempo, key, chords and the band, one bar at a time (`kits.play(name, S, P, bar, part)`); `kits.py NAME` renders a 24-bar sketch. Built by agents on the night of 19 November, not heard yet |
| [outrun_the_watchdog.py](code/outrun_the_watchdog.py), [hard_reset.py](code/hard_reset.py), [solder_harder.py](code/solder_harder.py) | research: three dry-run surprise rounds (synthwave, hardstyle, gabber) made by agents alone and timed (research/night-tests.md); not heard yet, not in share.SONGS |
| [overclocked_heart.py](code/overclocked_heart.py) | research: the dress rehearsal of 19 November (Hi-NRG, 30 min from the draw to the DJ file, the user picking by ear). Free ACE takes ignored the asked key (fixed by measuring it, Rubber Band); a band re-harmonized to the take, an ACE cover of our vocal stem (a near copy at every strength) and ACE lego lost by ear. Not in share.SONGS |
| [pull_up_resistor.py](code/pull_up_resistor.py) | research: a dress rehearsal by an agent alone, following only WEEKEND.md (happy hardcore, drawn on 19 November; 25 minutes to the DJ file, dj.check clean, picked by fit.py and Whisper, not heard yet). Its findings are fixed in the tools and the playbook: the keeper's key can move, 8 lines for 16 bars, a second draft round keeps the first's files, the diva's level in dense kits (`DIVA_GAIN`), no hook under the diva in any kit, the take cut before the outro. The user's verdict: "sucks ... mostly the high pitched singing, but also some of the rest"; the post-mortem is research/rehearsal-pull-up-resistor.md. `DIVA_GAIN=` is a test switch. Not in share.SONGS |

Render options (environment variables):

| Variable | Effect |
|---|---|
| `PREVIEW=48-64` | render only these bars (here 48 to 63), for a quick listen: `parts.Band` makes only the parts in them, so the template previews in about 8 s (a whole song: 39 s). A song's own parts can skip too: `if not S.live(bar): return` |
| `STEMS=1` | print the loudness of each bus |
| `SOLO=vox` | render only these buses (comma separated), dry: for auditions |
| `MUTE=vox` | render without these buses; the rest keeps its reverb and echo: stems |
| `GAIN=keys:0.5` | these buses' gains times these factors (comma separated), for mixing tests without editing the song |
| `AIR=1` | made-up highs above 11 kHz on every voice (voice.air: harmonics of the 5-11 kHz band): all our speech stops at 11-12 kHz (Piper is 22.05 kHz; Kokoro, Qwen3-TTS and Maya1 make 24 kHz) against about 20 kHz for the music. An A/B, off by default |
| `DIVA=<voice>`, `RAPPER=<voice>` | a Piper voice name, or `espeak:`, `flite:`, `festival:` or `mimic3:` plus a voice; `DIVA=ds:hanami` or `ds:lem` for DiffSinger (Segfault: Hanami; the Badge: Lem by default, `DIVA=en_US-amy-medium` for its old Piper diva) |
| `VOX_HUMAN=1` | a sung voice as a singer instead of a tuner (0..1, default 0: hard tuned, the robot diva): scoops into the notes, a slow drift, a vibrato of its own, a swell on long notes, breath at their end (`voice._humanise`) |
| `DS_VOICE`, `DS_PITCH` | the DiffSinger voice mode (default `Fragrance`; Lem: `Civet`, the Badge's default, `Phascogale`, `Quoll`), and `free`, `hard` or 0..1 for how freely it moves between notes (default 0.5) |
| `DS_SEED`, `DS_TIMBRE`, `DS_STACK` | another take of the same score; another singer for the same performance (a `voice.CAST` name, e.g. `qwen_diva`); the Badge only: doubles from takes 2 and 3 in two more voices, `DS_STACK=sing_qwen_pop,sing_maya_pop[,octave][,vocoder]`. The Badge's defaults with Lem: `DS_TIMBRE=qwen_diva`, the whole stack; empty for off |
| `DS_FLASH`, `DS_ACCENT` | the Badge only: another rhythm for its "flash me" line (notes as in `Song.notes`), and "flash" that many dB up (default 4) |
| `DS_PITCH`, `DS_VIB`, `DS_TENSION`, `DS_BREATH`, `DS_DYN` | how alive the DiffSinger singer is. Lem has no pitch model: without help every note is flat ("almost GLaDOS, but more dead inside"). `DS_PITCH=rule`: warble's rule tuner draws scoops, overshoot, vibrato and drift (`ds.tuned`); `DS_VIB` scales its vibrato; `DS_TENSION` the DiffSinger tension (+ more power); `DS_BREATH=1` a breath before each phrase; `DS_DYN=1` louder high notes and swelling long notes. Template songs with Lem default to rule, 1.6, 25, 1, 1 (the user's picks); the Badge keeps its own approved settings |
| `DS_GAIN=2.5` | singer D's level in the mix (each song sets its own `ds_gain`); an A/B switch since 21 November, so a test goes to renders/scratch. Measure a change with Whisper on the whole mix in 15 s windows: one whole-song pass gets stuck in loops ("start sick fold in my heart" five times) and two renders can differ by 10 points from a small change, so trust only a big gain (Packet Loss 1.8: 31 % to 53 %; Common Ground 2.5: 53 % to 74 %; Warm Boot and Low Pass Love louder: worse) |
| `BLINK_GAP=1` | Blinky: a sixteenth rest after each "blink" in the hook (Whisper: "drink" instead of "bling", the whole song 36 % against 43 %; off) |
| `P.knobs["cons"] = "1"` (code) | a song's own singer D settings over `parts.LEM`; the `DS_*` switches still win. Segfault sets `cons` (Lem's consonants under the Qwen diva: "reboot" heard 2 of 2 in the chorus, "free boot" without; the whole song the same, 58 % against 60 %) |
| `DS_COMP=0`, `DS_COMP_TAKES=4` | the producer's comp, on by default for Lem in a `parts.Band` singer (`DS_COMP=0`: one take). `DS_CONS=1`: Lem's consonants above 4 kHz under the converted voice (no gain measured, off). The breath before a phrase is left out before a word that starts with a vowel, h or l (it sounded like an h). The comp: Lem sings the part 4 times, Whisper hears every line of every take, each line comes from the best take, cut in the rest before it (`ds.Part.comped`); the doubles then come from takes 5 and 6 |
| `RAPPER=maya_mc_deep` or `qwen_mc_deep`, `MC_TAKES=4` | the Badge's MC: a Maya or Qwen voice at its own pace instead of the Piper MC (the user kept the Piper MC, 21 November); per line `voice.best_take` tries three directions (as written, punched, told to rap on the beat) times `MC_TAKES` seeds and keeps the take Whisper hears best that fills the bar without a squeeze |
| `DS_HARMONY` | a template song (`parts.Band`) with `DIVA=ds:lem`: the voice of the real harmony, a third above on lines with choir (default `sing_maya_soul`; it replaces the Piper choir). There `DS_ACCENT=word:dB,...` too, and `DS_TIMBRE`, `DS_STACK` default to the Badge's pick; empty for off (Lem alone: fast, for shaping the melody) |
| `CHORUS_STYLE`, `CHOIR` | how the Segfault chorus is stacked (default `choir`: five other voices) |
| `KEYS=fm`, `ROOM=noise` | Warm Boot with the simple FM Rhodes and the noise reverb |
| `UNMASK=6` | pads, keys and lead make room (up to 6 dB, 250-6000 Hz) only where and in the band where the voice sings (`engine.make_room`); on by default (6), `UNMASK=0` for the old mix |
| `VOXCHAIN=1` | a 1995 vocal channel strip on the vox bus: mud out, fast compressor, presence, de-esser, exciter, leveler (`engine.vocal_chain`); on by default, `VOXCHAIN=0` for the old mix |

Both together let the ear hear more of the words in every song (section by
section, 18 November): Segfault 16 to 53 %, The Rhythm Of The Badge 70 to
84 %, Packet Loss 29 to 40 %, Low Pass Love 17 to 21 %, Blinky 7 to 18 %, Race
Condition 38 to 41 %, Low Battery Lullaby 8 to 26 %. Alone, UNMASK 6 gave 31 %
on average, UNMASK 9 35 %, VOXCHAIN 38 %, both 40 % (none: 26 %).

A render with `PREVIEW`, `SOLO`, `MUTE` or `GAIN` that would go to `renders/`
goes to `renders/scratch/` instead, with the settings in its name, and an MP3
next to it to listen to on a phone: a test never replaces the song's render,
which `share.py`, `dj.py` and `produce.py` use.
`dj.py` flags a file whose length does not match the song's bars.

## Voices

[voice.py](code/voice.py) uses [Piper](https://github.com/OHF-Voice/piper1-gpl),
a neural text-to-speech model, to speak each word. Then
[WORLD](https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder)
(`pyworld`) re-pitches the word onto our melody notes. It stretches only the
vowel, so the consonants stay crisp, and tunes the pitch hard to the note: the
eurodance "robot diva". The rap is spoken and fitted to the bar.

- **Choirs.** Other voices double the lead and sing a third above, but only
  the vowels (`vowel_only=True`, low-passed at 6 kHz), about 6 dB under the
  lead: whole words from five different speakers smear.
- **Spelling.** Piper reads through eSpeak. Check new syllables with
  `espeak-ng -v en-us -q --ipa "..."`: "Ay" is "eye", "Eff" is E-F-F.
  Spelled-out letters work best as single capitals with "!" (`S! E! G!`), one
  per beat. `asr.py` checks the result by ear. Sung letters need room: in
  S.D.I.O. they came through only with the choir at 0.15 or less under them,
  the voice at 1.3-1.4 and no lead synth doubling them.
- **Men who can sing.** A male verse with spelled letters, sung an octave under
  the diva with no music, words heard of 39 (18 November): `en_GB-alan-medium`
  32, `en_US-bryce-medium` 30, `en_US-john-medium` 30, `en_US-joe-medium` 14,
  `en_US-ryan-high` 7 (5 at -12), `en_US-norman-medium` 5. Ryan and Norman are
  fine for rap and speech, not for singing.
- **The formant robot** (`engine.robot`, the vocoder sound) is for hooks
  without words: the ear has never heard a word it sang.
- **DiffSinger.** [ds.py](code/ds.py) lets a [DiffSinger](https://github.com/openvpi/DiffSinger) voicebank sing a whole
  part on our notes, through [warble](https://github.com/erz0r/warble) (MIT,
  ONNX on the CPU). [Hoshino Hanami](https://lottev.moe/hoshino-hanami-ai%e2%9d%a4dol-for-diffsinger-v1-0-is-out/) (Lotte V; any use with credit, vocoder CC
  BY-NC-SA 4.0) sings in her "Fragrance" (power) mode. Her terms forbid
  pitch-shifting finished renders, so DiffSinger sings the key changes itself.
  [TIGER](https://tigermeat.xyz/cast/tiger/) (male, CC BY-NC-ND) is installed as well.
  **Lem the Shapeshifter DS 2.5** (bank `lem`, English 12.5 h, voice colours Civet, Phascogale, Quoll; realistic
  range A2-D5; commercial use and use outside singing synthesizers allowed; a release must name it exactly
  "Lem the Shapeshifter DS 2.5"; https://wik-wav.neocities.org/lem-voicebank-tos) is the source for voice
  conversion: `DIVA=ds:lem DS_VOICE=Civet DS_TIMBRE=qwen_diva`. Its vocoder, `pc_nsf_hifigan_44.1k_hop512_128bin_2025.02`
  (openvpi, CC BY-NC-SA), sits in its `dsvocoder/`. Hanami's terms forbid her renders as a conversion source: no
  `DS_TIMBRE` with Hanami. A short word on a high note needs time: "flash" on an eighth at 134 BPM became "fs" or
  "fish", on a quarter it says "flash" (`DS_LINE` in the Badge); rests after "me" keep the punch.
  `parts.Band(diva_voice="ds:lem")` has the whole chain for any template song (`timbre`, `stack`, `harmony`,
  `accent`); a conversion converts only the sung stretches (`ds.sung`): 8 bars of chorus in four voices take about
  3 minutes.

## ACE-Step

`ace.py SONG --mode ...` runs the whole route; the results land in
`renders/ace/<song>/`.

| Mode | ACE-Step does | Our part |
|---|---|---|
| `cover` | re-plays the whole song (`cover-nofsq`); `--strength` 1 follows us closely, 0.3 loosely | structure, tempo, key, melody, the DJ intro and outro |
| `vocals` | re-sings only our vocal stem; its take is lined up, gated by our vocals and woven over our instrumental (`--ace` of it in the vocals) | all the music |
| `lego` | sings a new vocal track over our instrumental, with its own melody | all the music, the words |
| `text` | makes its own song from a caption and our lyrics | tempo, key, words |

What we found:

- ACE-Step's own songs (`text`) sound good but too modern for the 90s themes.
  `--era 90s` (narrower, less sub, no air, tape) helps a little. Measured, the
  "modern" is a darker, wider sound than our code makes (Warm Boot: centroid
  251 Hz against our 356 Hz, sides -11.7 dB against -17.8 dB).
  `--match 0.7` (master.py, ace.py, `match` in produce.py) gives the take the
  tonal balance and stereo width of our own render: one static zero-phase EQ
  from the two long-term spectra per third octave (at most 8 dB either way),
  and the sides scaled. At 0.7 the Badge and Packet Loss covers land on our
  centroid and width; Warm Boot moves about half way. The words do not change
  with it (the ear: Badge +17, Race Condition +5, Packet Loss -1, Low Pass
  Love -10 points, about the ear's own spread); `--era 90s` on top cost the
  Badge 24 points, the others nothing.
- In covers, ACE-Step does not keep the 16 bars of drums at each end, so
  `master.py --dj-from` splices ours back in.
- `lego` on the Badge was "an esoteric mess", but interesting: ACE-Step sang
  its own words (the ear heard 1 % of ours) and re-made most of the music.
- For the vocals, the base model is the faithful one: it puts 9 % of its sound
  where our voices are silent, the turbo model 48 %.
- ACE-Step reads the lyrics itself, not through eSpeak: `ace.py` respells them
  (`ACE_SPELL`): "badge-link", "C six", "U S B". `--native-tags` maps our sheet's
  section names to the tags ACE-Step was trained on (`[Verse]`, `[Rap]`,
  `[Chorus]`, `[Break]`, `[Instrumental]`); measured, they lose words (Low
  Pass Love 39 to 36 %, Race Condition 55 to 53 %, Packet Loss 65 to 57 %),
  so the default stays our own names.
- A timbre reference of 30 s of our render where the words are sung
  (`ref = "sung"` in produce.py): with three stretches picked by hand the
  Badge cover went from 78 % to 87 % of the words, but picked by the most
  words per section it lost words on three of four songs (Low Pass Love 39 to
  32 %, Race Condition 55 to 48 %, Packet Loss 65 to 57 %; the Badge 81 to
  84 %). Off by default.
- Text to music, small against big (the same words and seed, two songs, by
  ear, 18 November): the 1.7B LM with the turbo DiT came out clean, the 4B LM
  with the base DiT (50 steps) "a lot messier and fuller, as if you listen
  half way through the process" in both songs, at 2.4 times the time. The
  base DiT is the raw pretrained model, and acestep.cpp's base preset runs
  it without CFG. The tuned 50-step model is SFT
  (`acestep-v15-sft-Q8_0.gguf`, `--model sft`). Five versions of the same song,
  by ear: the 4B LM with SFT best, then the 4B LM with turbo and the 1.7B LM
  with SFT, then the 1.7B LM with turbo; base last. From scratch, for 2
  minutes of music: 1.7B + turbo 71 s, 4B + turbo 83 s, 1.7B + SFT 136 s,
  4B + SFT 154 s. `gag.py` uses 4B + SFT.
- Speed on the Radeon 860M: a 3:30 song in about 2 minutes with the turbo
  model, about 5 minutes with the base model. The VAE decode runs in tiles of
  512 latent frames (`ace.VAE_CHUNK`, in every tool): with the CPU busy, the
  default 1024 crashed the GPU (`vk::DeviceLostError`) in 15 of 15 runs of a
  soak, 512 in none (research/night-tests.md); 2048 and 4096 crash always.

## Producing section by section

`produce.py SONG` reads `code/projects/<song>.toml`; `produce.py SONG --map`
prints the song's sections with their bars, from the lyric sheet:

```toml
take = "cover"        # the whole song first: ACE-Step re-plays our render ("ours": no ACE-Step)
strength = 0.85       # how closely it follows our render
model = "turbo"       # turbo (8 steps) or base (50)

[[section]]
name = "verse"
bars = [24, 32]
use = "repaint"       # ACE-Step makes these bars again, once per seed; the ear keeps the best,
                      # and only if it beats what is there
window = 4            # repaint only this section plus 4 bars of context
lyrics = "section"    # with only the lines sung in that window
noise = 0.65          # starting from a noised copy of the take, so the words are already there
seeds = [2, 3]

[[section]]
name = "rap"
bars = [48, 56]
use = "ours"          # our own render here: the machine flow

# at the end (top-level keys, before the first [[section]]):
# match = 0.7         # the tonal balance and width of our render (master.match_tone)
# era = "90s"         # master.py's 90s stage
# lufs = -10.0        # default -9 for eurodance, -10 for house
```

Every ACE-Step result is cached by its request, so changing one section only
redoes that section. A `repaint` from pure noise (`noise = 0`) comes back
without words. From the take noised, it polishes: on the Badge verse (65 % of
the words in the take) `noise` 0.35 gave 18-59 %, 0.5 gave 76 %, 0.65 gave
82 %. The turbo model has 8 steps, so `noise` snaps to its schedule: 0.65 and
up is one step of ACE-Step on the take, 0.5 two, 0.35 three.

`noise` at the top of a project does the same to the whole song, starting
from our own render instead of a cover: ACE-Step only cleans up, it adds no
parts and no words of its own. Words heard, section by section, on the new
default mix (UNMASK and VOXCHAIN; in brackets: the old mix):

| Song | Our render | 1 step (`noise = 0.65`) | 2 steps (`noise = 0.5`) |
|---|---|---|---|
| Race Condition | 49 % | **59 %** | 50 % |
| The Rhythm Of The Badge | 83 % (73) | **89 %** (77) | **89 %** (72) |
| Segfault | 52 % (14) | 56 % (15) | **57 %** (34) |
| Packet Loss | 43 % (29) | **46 %** (43) | 44 % (37) |
| Low Pass Love | 20 % (17) | 21 % (15) | **23 %** (16) |
| Blinky | 17 % | 18 % | 18 % |
| Low Battery Lullaby | **24 %** | 18 % | 18 % |

On the new mix one step adds 1 to 10 points on six songs (on average 41 to
44 %); the mix itself gained more. Low Battery Lullaby loses words: its vocal
chops do not survive ACE-Step, so it stays ours.

The DJ intro and outro are always ours. The result is in
`renders/produce/<song>/`, with a radio edit and an ear report per section.

What the ear (`produce.py`'s, section by section) hears of the lyrics in our
full mixes, with UNMASK and VOXCHAIN (the default since 18 November): The
Rhythm Of The Badge 84 %, Segfault 53 %, Race Condition 41 %, Packet Loss
40 %, Low Battery Lullaby 26 %, Low Pass Love 21 %, Blinky 18 % (Warm Boot's
robot: 0 %). The low ones are the songs to produce.

The voices alone (`SOLO=vox`, through the same channel strip) against the
full mix, section by section: Low Battery Lullaby 54 % against 26 %, Low Pass
Love 44 % against 21 %, Blinky 30 % against 18 %. In these three the music
hides about half the words; in Blinky the chorus is hard to hear even alone
(0 to 32 %). No one bus is to blame: muting one bus at a time (`MUTE=`) moved
Blinky and Low Pass Love by at most 3 points. In Low Battery Lullaby muting
the keys gave 36 %, but turning them down step by step (`GAIN=keys:0.7`, 0.5,
0.35: 23, 24, 28 %) and UNMASK 9 or 12 (26 %) did not: changes of a few points
are within the ear's noise, so the mix is as clear as these numbers can show.

## Surprise theme (two hours)

1. Copy [code/template.py](code/template.py) to `code/<name>.py` (`<name>` in
   lowercase with `_`, like `sdio_love`). Set the
   knobs (`TITLE`, `DAY`, `BPM`, `KEY`, chords, groove, bass, keys, voices),
   write the words and the melody. Grooves for the likely genres are in
   `parts.GROOVES` (`disco`, `italo`, `house`, `eurodance`, `techno`, ...);
   `BASS = "octave"` is the Italo and Hi-NRG gallop. Give the words room:
   Blinky's chorus (four or five short syllables in three quarters of a bar
   at 132 BPM) is hard to hear even with no music.
   `DIVA=ds:hanami` lets the DiffSinger voice sing the whole diva part
   (`parts.Band`, then `P.finish()` before the mixdown); `ds_words=` where
   her words differ from the Piper spelling. She sings an octave above the
   Piper diva, in the keys' range, so she sits at twice the level (`DS_GAIN`,
   default 2.0): at 1.0 the ear heard none of the template's verse words in
   the mix, at 2.0 to 2.5 more than with Piper. A whole song with her takes
   46 s (Piper: 29 s).
   Work in short rounds with someone listening: change a part, render its bars
   (`PREVIEW=48-64 .venv/bin/python <name>.py`, about 8 s), send the MP3 from
   `renders/scratch/` to a phone, and let their ears decide; two versions of
   a part make an A/B. The software ear (step 3) is a check at the end, not
   what steers the changes.
2. Render it. The template prints the line for `share.SONGS`: add it at the
   end of the list, and write the lyric sheet as `lyrics/NN-<name>.txt` (NN:
   its row number) with `[m:ss]` times (a bar is 240/BPM seconds). If the last
   chorus changes key, `KEY_CHANGE` is enough: `dj.py` and `mix.py` read it.
3. The ear, once the song is done, section by section: `produce.py <name> --project
   <file with take = "ours"> --tag ours`. A section moves up to about 20
   points between two renders of the same thing: act on bigger changes, or on
   what the voices alone (`MUTE=drums,perc,bass,pads,keys,lead,fx`) confirm.
   A test render (`MUTE=`, `GAIN=`, ...) goes to `renders/scratch/`; give it
   to the ear with `--ours renders/scratch/<file>.wav`.
4. The polish: `produce.py <name> --project projects/_polish.toml --tag
   polish` (one ACE-Step step from our render, about 1.5 minutes).
5. `share.py` and `dj.py` (it only writes `renders/dj/`: safe to run), then
   copy `renders/dj/` to the USB stick. If the polish is the better one:
   `dj.py --use <name>=renders/produce/<name>/<name>-polish.wav` (and the same
   `--use` for `mix.py`).
6. `mix.py saturday --order auto` to hear the day as the DJ will play it.

A soulful sung line (a soul or disco "sample", a diva) sounds choppy from Piper,
syllable by syllable. Let ACE-Step sing it instead. Use text to music, a cappella,
with the 4B LM and the SFT DiT, and make a few seeds. Pick a take by ear and play
it whole on the grid; cutting it to the melody made it choppy again. In Push It
To Prod (`push_it_to_prod.dame_take`) the takes make themselves from the
request in the script. A 16 s take is eight bars at 124 BPM, and a whole take
is about 20 s of computing.

A timebox for the two hours: the first full render by 0:20, the words frozen
by 0:45, no more changes after 1:15, `share.py` and `dj.py` by 1:30, the stick
by 1:40.

Four rehearsals so far. Race Condition (drum and bass) took about 4 minutes
from the theme to the finished render. S.D.I.O. (Italo disco, drawn at random
on 18 November) went through the whole line in 32:45: three songwriters
pitched in parallel and a judge picked one (15:38), the first full render at
19:08, five renders with ear checks to 27:00, then the polish, `share.py` and
`dj.py`. Words heard: 56 % ours, 64 % polished. Push It To Prod (big beat,
drawn on 18 November) was made in short rounds with the user listening to
snippets on a phone, and took 26 minutes from the draw to the DJ files. Disco (drawn the same evening) gave two songs, Uptime Fever and Rubber Duck, in 24 minutes from the
draw to both DJ files, made the same way: the diva is an ACE-Step take, sung a cappella and played whole.

## Research: `research/`

Notes written by Claude research agents, with their web sources at the bottom of
each file.

| File | About |
|---|---|
| [mellow-house-90s.md](research/mellow-house-90s.md) | tempo, chords, sounds, sub-styles and reference tracks of 90s mellow house |
| [eurodance.md](research/eurodance.md) | the eurodance formula, tempo per year, progressions, 31 reference tracks |
| [surprise-genres.md](research/surprise-genres.md) | 16 likely surprise genres, each with a tempo range and a ready prompt |
| [hooks-and-humor.md](research/hooks-and-humor.md) | how dance hooks work, sing-along rules, 30 title ideas, three finished lyrics |
| [local-and-alt-generators.md](research/local-and-alt-generators.md) | open AI music and singing models that run on this laptop |
| [sound-design-and-dj.md](research/sound-design-and-dj.md) | synth recipes, harmonic mixing, file format and loudness for the DJ |
| [render-speed.md](research/render-speed.md) | how fast the code tracks, DiffSinger and ACE-Step render on this laptop |
| [night-tests.md](research/night-tests.md) | the night of 19 November: ACE singers for the weekend songs, voices per genre, the SFT polish, VAE stability, genre kits, dry-run rounds (not heard yet) |
| [toolkit-2026-11-19.md](research/toolkit-2026-11-19.md) | what more to prepare before the weekend: ACE-Step's key is a lottery (22 % of 166 takes in the asked key), take drafts with `lm_batch_size` and turbo, band fit and slower harmony under a free take, singing voice conversion through audio.cpp (Seed-VC, SoulX-Singer) with ACE takes as the voice, Piper's Dutch and many-speaker voices, voices designed from text (Qwen3-TTS, Maya1); fact-checked, nothing installed or heard yet |
| [suno-tips.md](research/suno-tips.md) | Suno v6 (not used) |

## Other options we might try

- **OpenUtau** (MIT) with a DiffSinger voicebank, to tune a phrase by hand in
  its piano roll. The AppImage is in `~/Projects/diffsinger/dl/`.
- **The prompts in `suno/`**: style prompts and lyrics written by Claude for
  each theme, in Suno's format. We do not use Suno, because it is a closed
  service; `ace.py` uses the style prompts as ACE-Step captions.

## License

MIT for everything in this repository. See [LICENSE](LICENSE). The repository
follows the [REUSE](https://reuse.software) specification: [REUSE.toml](REUSE.toml)
gives the copyright and licence of every file, and `uvx reuse lint` checks it.
The voice models, the Python packages, ACE-Step's models and the renders are not
in the repository; [SONGS.md](SONGS.md#software-and-licences) lists their
licences.
