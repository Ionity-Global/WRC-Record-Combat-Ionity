```
========================================================================================
WRC - WOW RECORD COMBAT - IONITY
Author: Johan Wilhelm van Antwerp | Ionity (Pty) Ltd | AEDI
Version: 1.6.0 | Updated: 2026-11-15 SAST | Classification: PUBLIC
Governance: Policy 986 AED | License: CC BY-NC-SA 4.0 where stated
(c) 2018-2026 Antwerp Designs | Ionity (Pty) Ltd - All Rights Reserved
Web: https://www.ionity.today | https://www.ionity.world | Ref: https://www.ionity.co.za
========================================================================================
```

# WRC - WoW Record Combat

Records your World of Warcraft PvP by itself. When a player of the opposite
faction shows up, WRC starts recording; ten seconds after they are gone, it
stops. You get short clips of the fights instead of hours of footage.

It has two parts:

| Part | What it is | Where it goes |
|---|---|---|
| **WRC addon** (`addon/WRC`) | Lua addon. Draws a tiny coded strip (the *beacon*) in a screen corner that says IDLE, ALLIANCE, HORDE, COMBAT or REC. | `World of Warcraft\_forever_\Interface\AddOns\WRC` (CurseForge) |
| **WRC Recorder** (`recorder/`) | Windows app with Record and Open folder buttons. Reads the beacon off the screen and runs FFmpeg. | Anywhere; `release\WRC-Recorder.exe` |

The recorder only looks at screen pixels. It does not read game memory, inject
anything, or press keys, and the addon only displays what the game already
shows you.

## Download

| | |
|---|---|
| **Addon + Recorder** | [Latest release](https://github.com/Ionity-Global/WRC-Record-Combat-Ionity/releases/latest) — `WRC-<version>.zip` and `WRC-Recorder.exe` |
| **Addon on CurseForge** | [WRC Record Combat - Ionity](https://www.curseforge.com/wow/addons/wrc-record-combat-ionity) (pending approval) |
| **Guide** | [Wiki](https://github.com/Ionity-Global/WRC-Record-Combat-Ionity/wiki) (source copy in `docs/wiki`) |

## Quick start

1. Run `install_addon.bat` (or copy `addon\WRC` into `Interface\AddOns`).
2. Run `recorder\build.bat` once to make `release\WRC-Recorder.exe`, then start it
   (or download it from the latest release).
   The first start downloads FFmpeg if you do not have it and tests your
   hardware (a few seconds).
3. Log in. A small strip appears top-left. Type `/wrc test`: the strip reads
   ALLIANCE or HORDE and a clip lands in `Videos\WRC`.

## How detection works

The addon checks your target, focus, mouseover, every nameplate and arena
opponents five times a second. A unit counts when it is a living player of the
other faction that you can attack. Your own faction is read automatically, so
the same addon works for Horde and Alliance. Inside battlegrounds and arenas,
where modern clients hide unit details from addons, being in combat counts.

The beacon is 130 x 9 cells of solid colour, 3 pixels per cell by default
(390 x 27 pixels): the status, then your character's name, which goes into
the clip's file name. Magenta and cyan bars at both ends let the recorder find it
and measure the cell size, so it needs no setup at any resolution. Between
them sit 8 state bits with a checksum and an 8-letter word in a 5x7 pixel
font, which the recorder reads with a 27-glyph matcher. That is the whole OCR:
no OCR engine, no model, about 1 ms per reading.

## Small files, good quality

At first start the recorder tries encoders on your PC, best compression first,
and keeps the first one that really encodes a real screen capture:

`AV1 (NVIDIA / AMD / Intel)` > `HEVC (NVIDIA / AMD / Intel)` > `H.264 hardware` > `H.264 software`

Recording uses constant-quality encoding with a bitrate ceiling of
`width x height x fps x 0.045` bits per second: about 5.6 Mbit/s at 1080p60 and
10 Mbit/s at 1440p60 (roughly 40-75 MB per minute at most, usually less).
Capture is GPU Desktop Duplication straight into the encoder when the hardware
allows it. Clips under 5 seconds are dropped, and the oldest clips are removed
once the folder passes 20 GB (set `max_storage_gb` to 0 to never delete).

## Addon commands

| Command | Does |
|---|---|
| `/wrc on` / `off` | Show or hide the beacon (off stops auto-recording) |
| `/wrc rec` | Start or stop a manual recording (same as the in-game REC button) |
| `/wrc shot` | Clean screenshot: all interface hidden for 1 second (also the SHOT pop-out and a key binding) |
| `/wrc settings` | Options and key bindings (also: right-click the round icon) |
| `/wrc clips` | In-game clips panel: where clips are saved, the newest clips, Play buttons |
| `/wrc folder` | Open the clips folder in Windows |
| `/wrc deaths` | Your last deaths and who was targeting you |
| `/wrc buttons` | Show or hide the round WRC button (hover it for the REC / Folder pop-outs) |
| `/wrc test` | Pretend an enemy is near for 10 seconds |
| `/wrc size 2-12` | Beacon cell size in pixels |
| `/wrc corner tl\|tr\|bl\|br` | Screen corner |
| `/wrc offset X Y` | Pixels in from the corner |
| `/wrc attackable on\|off` | Count only enemies you can attack (default on) |
| `/wrc status` | What the beacon shows now |

## Where clips go and how to see them

Clips are saved in `Videos\WRC` in your user folder (`output_dir` in
`config.json` changes that). In game, the Clips pop-out or `/wrc clips` shows
that path and your newest clips. WoW cannot play video files, so **Play**
opens the clip in your PC's video player and **Open in Windows** opens the
folder. WRC raises that window in front of the game on WoW's monitor; it does
not take keyboard focus, so click it to use it. The recorder rewrites the list after every recording, and WoW reads
it when the UI loads: press **Reload list** to refresh.

## Quick record key

- **Ctrl+Alt+R** starts and stops a manual recording from anywhere while the
  recorder is running. Change it with `hotkey` in `config.json`.
- In game: `/wrc settings` (or right-click the round icon), click the key
  field and press the key you want. The same bindings are listed under
  Options > Keybindings > AddOns > WRC.

## Recorder settings

The **Settings** button in the recorder window covers the common ones.
`WRC-Recorder.exe --write-config` writes `config.json` next to the EXE with
every setting.

| Setting | Default | Meaning |
|---|---|---|
| `trigger_mode` | `enemy` | `enemy` = opposite faction on screen or fighting you. `pvp_combat` = only once you are in combat with them. `any_combat` = every fight. |
| `linger_seconds` | 10 | Keep recording this long after the enemy is gone |
| `codec` | `auto` | `auto`, `av1`, `hevc`, `h264` |
| `quality` | 0 (auto) | Lower is better and bigger. Auto: AV1 32, HEVC 27, H.264 23 |
| `fps` | 0 (auto) | Monitor rate, capped at 60 |
| `max_height` | 0 (native) | e.g. 1440 to downscale a 4K screen |
| `audio_device` | `auto` | `none`, or an exact DirectShow device name |
| `output_dir` | `Videos\WRC` | Where clips go |
| `max_storage_gb` | 20 | Oldest clips are deleted beyond this |
| `deathcam` | on | Record every fight on standby; keep the last `deathcam_seconds` (20) before a death plus `deathcam_after` (5) |
| `afk_record` | on | Keep the clip when you are attacked while AFK |
| `hotkey` | `ctrl+alt+r` | Quick record key, works while WoW has focus. Empty string turns it off |

Other switches: `--attune` (re-test hardware), `--snapshot` (save what WRC
sees and what it read), `--selftest`, `--no-gui`, `--debug`.

## Death cam and AFK

With the death cam on, the recorder starts a standby recording whenever you
enter combat and deletes it three seconds after the fight ends. If you die,
it keeps the last 20 seconds before the death and 5 after. This means the
encoder runs during every fight, PvE included; turn `deathcam` off if you do
not want that. On death the addon also prints who was targeting you.

## Known limits

- **Game sound** is recorded only if Windows has a loopback recording device
  (Stereo Mix, VB-CABLE, virtual-audio-capturer) that is carrying sound when
  WRC attunes. A silent device is skipped and clips are video only; the log
  says so. Route the game sound to the device and run `--attune`, or name a
  device in `config.json`. `tools/audio_probe.py` lists the devices.
- **Start delay**: about half a second without audio and about two seconds
  with audio (measured), because the audio device takes that long to open.
  With the default `enemy` mode the recording normally begins when the
  nameplate appears, before the fight.
- The beacon is visible in the clip (a small strip in the corner).
- WoW must be windowed or borderless (the modern clients are), not hidden
  behind another window.
- HDR displays are not handled specially.

## Development

```
cd recorder
pip install -r requirements.txt pytest lupa
python -m pytest -q          # 67 tests; runs the real addon Lua against a mock WoW API
python -m wrc_recorder       # run from source
```

`tools/gen_font.py` regenerates `addon/WRC/Font.lua` from the Python font.

BUILDING TOMORROW, TODAY
