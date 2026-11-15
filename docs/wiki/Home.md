# WRC — WoW Record Combat · Ionity

**WRC records your World of Warcraft PvP by itself.** When a player of the opposite faction shows up, recording starts. Ten seconds after they are gone, it stops. You get short, sharp clips of the fights — not hours of footage — at high quality and small file size.

| | |
|---|---|
| **Version** | 1.6.0 (2026-11-15) |
| **Clients** | WoW: Forever 1.60.1 (tested live). TOC also lists Retail 12.0, Mists Classic, Cata/Wrath Classic and Classic Era (untested) |
| **Platform** | Windows 10/11 |
| **Licence** | CC BY-NC-SA 4.0 · Policy 986 AED |
| **Author** | Johan Wilhelm van Antwerp · Ionity (Pty) Ltd |

## Two parts

| Part | What it does |
|---|---|
| **WRC addon** | Detects enemy players, draws a small coded strip (the *beacon*) in a screen corner, gives you a round in-game button, a clips panel, a clean-screenshot button, settings and keybinds, and a death report. |
| **WRC Recorder** | Small Windows app. Reads the beacon from the screen and runs FFmpeg with the best encoder your PC has (AV1 › HEVC › H.264). |

The recorder only reads screen pixels. It never reads game memory, injects code, or sends keys or clicks to the game.

## Start here

1. [[Installation]] — addon + recorder in two minutes
2. [[In Game Guide]] — the round button, clips panel, settings, keybinds, `/wrc` commands
3. [[Recorder Guide]] — the recorder window, `config.json`, command-line switches
4. [[Death Cam and AFK]] — how death and AFK clips work
5. [[How It Works]] — the beacon protocol, trigger logic and encoder auto-attune
6. [[Troubleshooting]]
7. [[Building from Source]]
8. [[Roadmap]]
9. [[FAQ]]

## Downloads

- **Addon:** [CurseForge — WRC Record Combat - Ionity](https://www.curseforge.com/wow/addons/wrc-record-combat-ionity) (pending approval) or the [Releases](https://github.com/Ionity-Global/wrc-record-combat-ionity/releases) page
- **Recorder:** `WRC-Recorder.exe` on the [Releases](https://github.com/Ionity-Global/wrc-record-combat-ionity/releases) page
