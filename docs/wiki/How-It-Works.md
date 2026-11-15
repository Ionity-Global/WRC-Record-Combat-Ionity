# How It Works

## Why a beacon?

An addon cannot write files or talk to other programs, and the recorder must not read game memory. So the addon *draws* its state and the recorder *reads* it from the screen — a tiny OCR, no OCR engine, ~1 ms per reading.

## Beacon layout

130 × 9 cells, default 3 px per cell → **390 × 27 px**. Drawn on a parentless frame scaled `768 / physicalHeight` so every cell is pixel-exact at any UI scale.

| Columns | Content |
|---|---|
| 1–3 | Finder: magenta, cyan, magenta |
| 5–12 | 8 state bits |
| 14–60 | Status word: 8 glyphs, 5×7 font |
| 62–64 | Finder: cyan, magenta, cyan |
| 66–68 | Name marker (rows 2–6) |
| 70–128 | Character name: 10 glyphs, A–Z |

**Bits:** 1 enemy · 2 PvP combat · 3 any combat · 4 manual · 5 enemy is Horde · 6 heartbeat (flips every second) · 7–8 checksum = (popcount(bits 1–6) + 1) mod 4.

**Words (priority):** `PLAY xx`, `FOLDER`, `DEAD`, `AFK`, `REC`, `ALLIANCE`/`HORDE`, `COMBAT`, `IDLE`.

The reader finds the beacon by the **magenta→cyan edge** of the finder (robust when another addon's overlay touches it), measures cell size from the finder, then matches each glyph against a 27-glyph set by Hamming distance. A reading is trusted only when the checksum and word agree.

## Trigger

A small state machine: start after `start_confirm` matching readings, keep going `linger_seconds` after the signal ends, split at `max_clip_minutes`, drop clips under `min_clip_seconds` (except manual).

## Capture and encode

- Capture: FFmpeg **ddagrab** (Desktop Duplication) zero-copy into NVENC/AMF where possible, else ddagrab + download, else gdigrab.
- The monitor WoW is on is matched to the DXGI output by content, so multi-monitor setups work.
- **Auto-attune:** tries AV1 › HEVC › hardware H.264 › libx264 on a real capture and keeps the first that truly encodes. Results are cached in `attune.json`.
- Constant frame rate (`-fps_mode cfr`), constant quality with a bitrate ceiling.
- Audio: only a DirectShow loopback device that is actually carrying sound is used; silent devices are skipped.

## Modern client restrictions

Retail-era clients return "secret values" for some unit queries; every unit call is wrapped and secret values are treated as unknown. Combat log parsing is only used on clients that allow it.
