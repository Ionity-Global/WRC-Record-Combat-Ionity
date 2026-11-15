# In-Game Guide

## The round button

- **Left-click** — start or stop a manual recording.
- **Right-click** — open Settings.
- **Hover** — *REC/STOP* slides out on the left, *Clips* on the right.
- **Camera-and-sword** (small, on the shield's lower-right edge) — clean screenshot.
- **Drag** — move it. Position is saved.
- Cyan dot = idle. **Red and pulsing** = WRC is asking the recorder to record.

## Clean screenshot

The small **camera-and-sword** on the round icon, `/wrc shot` or its keybind. Makes **all** interface invisible for one second — the whole UI (like Alt+Z), nameplates and other overlays on the world, the WRC strip and button — takes a WoW screenshot while it is gone, and puts everything back. The picture is saved in WoW's own `Screenshots` folder.

- Works in combat too: WoW does not let addons hide the interface in combat, so WRC makes it fully transparent instead — the picture looks the same.
- A recording that is running carries on: the recorder ignores beacon gaps of up to 3 seconds.

## Clips panel

`/wrc clips`, the *Clips* pop-out or its keybind. Shows where clips are saved and the 12 newest: type, character, time, length, size, and a **Play** button.

- **Play** opens the clip in your PC's video player, raised in front of the game on WoW's monitor (it does not steal keyboard focus — click it).
- **Open in Windows** opens the folder the same way.
- **Reload list** — the recorder rewrites the list after every clip; WoW reads it when the UI loads, so this does a `/reload`.

WoW cannot play video, so playback happens outside the game.

## Settings

`/wrc settings` or right-click the round button. Only one WRC window is open at a time.

- Beacon on/off
- Attackable enemies only
- Show round button
- Beacon size (−/+) and corner
- **Keybinds** for Record, Clips and Clean screenshot: click a key field and press a key (Esc cancels). Not available in combat. The same binds are under *Options › Keybindings › AddOns › WRC*.

## Commands

| Command | Does |
|---|---|
| `/wrc on` / `off` | Show or hide the beacon (off stops auto-recording) |
| `/wrc rec` | Start/stop a manual recording |
| `/wrc shot` | Clean screenshot, all interface hidden for 1 s |
| `/wrc settings` | Options and keybinds |
| `/wrc clips` | In-game clips panel |
| `/wrc folder` | Open the clips folder in Windows |
| `/wrc deaths` | Your last 20 deaths: zone and who was targeting you |
| `/wrc buttons` | Show/hide the round button |
| `/wrc test` | Pretend an enemy is near for 10 s |
| `/wrc size 2-12` | Beacon cell size in pixels |
| `/wrc corner tl\|tr\|bl\|br` | Beacon corner |
| `/wrc offset X Y` | Pixels in from the corner |
| `/wrc attackable on\|off` | Count only enemies you can attack (default on) |
| `/wrc status` | What the beacon shows now |

## What counts as an enemy

Target, focus, mouseover, target-of-target, pet target, all nameplates and arena opponents are checked five times a second. A unit counts when it is a **living player of the other faction** you can attack. Your faction is read automatically. Inside battlegrounds and arenas, where modern clients hide unit details from addons, being in combat counts.

## Clip names

`WRC_<Kind>_<Character>_<YYYYMMDD>_<HHMMSS>.mp4` — e.g. `WRC_Alliance_Azzinoth_20261114_205817.mp4`.
Kinds: `Alliance`, `Horde`, `Combat`, `Manual`, `Death`, `AllianceDeath`, `HordeDeath`, `AFK`.
