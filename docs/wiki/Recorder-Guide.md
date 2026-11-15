# Recorder Guide

## The window

Status card (Watching / Recording / Standby / No beacon), **Record/Stop**, **Open folder** and **Settings**. The dot pulses while recording.

**Quick record key:** `Ctrl+Alt+R` anywhere while the recorder runs (change `hotkey`).

## config.json

`WRC-Recorder.exe --write-config` writes every setting next to the EXE. The Settings dialog covers the common ones.

| Setting | Default | Meaning |
|---|---|---|
| `trigger_mode` | `enemy` | `enemy` = opposite faction seen or fighting you · `pvp_combat` = only once in combat with them · `any_combat` = every fight |
| `linger_seconds` | 10 | Keep recording after the enemy is gone |
| `start_confirm` | 2 | Readings needed before starting (filters flicker) |
| `min_clip_seconds` | 5 | Shorter automatic clips are dropped (manual clips are always kept) |
| `max_clip_minutes` | 30 | Long fights are split |
| `deathcam` | true | See [[Death Cam and AFK]] |
| `deathcam_seconds` / `deathcam_after` | 20 / 5 | Seconds kept before / after a death |
| `afk_record` | true | Keep the clip when attacked while AFK |
| `codec` | `auto` | `auto`, `av1`, `hevc`, `h264` |
| `quality` | 0 (auto) | Lower = better and bigger. Auto: AV1 32, HEVC 27, H.264 23 |
| `fps` | 0 (auto) | Monitor refresh, capped at 60 |
| `max_height` | 0 | e.g. `1440` to downscale a 4K screen |
| `bits_per_pixel` | 0.045 | Bitrate ceiling = width × height × fps × this |
| `audio_device` | `auto` | `none`, or an exact DirectShow device name |
| `output_dir` | `Videos\WRC` | Where clips go |
| `max_storage_gb` | 20 | Oldest clips deleted beyond this (0 = never) |
| `wow_path` | "" | WoW install folder, if not found automatically |
| `hotkey` | `ctrl+alt+r` | Quick record key; empty = off |
| `scan_hz` | 8 | Beacon readings per second |
| `ffmpeg_path` | "" | Use a specific ffmpeg.exe |

## Command-line switches

| Switch | Does |
|---|---|
| `--attune` | Re-test encoders and audio |
| `--snapshot` | Save what WRC sees and what it read (for bug reports) |
| `--selftest` | Built-in checks |
| `--write-config` | Write `config.json` with all settings |
| `--no-gui` | Run without the window |
| `--debug` | Verbose log |

## File sizes

Constant-quality encoding with a ceiling of `w × h × fps × 0.045` bit/s: about **5.6 Mbit/s at 1080p60** and **10 Mbit/s at 1440p60** — at most 40–75 MB a minute, usually less. Measured: AV1 at 2560×1440 60 fps ≈ 6 Mbit/s.

## Where the clip list goes

After each clip the recorder writes `Clips.lua` into every WRC addon folder it finds (from the registry and the Battle.net install database), so the in-game panel can list your clips.
