# WRC changelog

## 1.6.0 - 2026-11-15
- **Clean screenshot**: the new **SHOT** pop-out under the round icon, `/wrc shot` or a key binding hides ALL interface for one second - the whole UI (like Alt+Z), nameplates and other overlays on the world, and the WRC strip and button - takes a WoW screenshot while it is gone, then puts everything back. Pictures go to WoW's own `Screenshots` folder.
  - WoW does not let addons hide the interface in combat: there it takes a normal screenshot and says so. If combat starts during the hidden second, the interface comes back at once.
  - Key binding in `/wrc settings` (Clean screenshot key) and under Options > Keybindings > AddOns > WRC.
- Recorder: a beacon that vanishes for up to 3 seconds (clean screenshot, loading screen) no longer changes anything. Before, a gap in the beacon stopped a recording started in game.

## 1.5.0 - 2026-11-14
- **Death cam**: every fight is recorded on standby and thrown away if you survive. If you die, the last 20 seconds before the death plus 5 after are kept as `WRC_Death_<Character>_...`. A PvP clip you die in is named `...AllianceDeath...` / `...HordeDeath...`. Switch it off in the recorder's Settings (`deathcam`).
- **AFK recording**: attacked while flagged AFK, the clip is kept as `WRC_AFK_...` (`afk_record`).
- **Death report**: on death the addon prints who was targeting you in the last 10 seconds (name and class, or NPC) and keeps the last 20 in a log (`/wrc deaths`).
- The round icon turns red and pulses while WRC is asking for a recording; the recorder window's dot pulses while it records.
- Icons redrawn with a war shield and crossed swords.
- Only one WRC window is open at a time in game (Settings and Clips no longer stack).

## 1.4.0 - 2026-11-14
- Clip names carry the character: `WRC_Alliance_Azzinoth_20261114_205817.mp4`. The addon shows the name on the beacon, to the right of the status word (A-Z only, 10 letters; accented letters are dropped), and the clips panel has a character column. The beacon is now 390 x 27 px.
- In-game settings panel (`/wrc settings`, right-click the round icon, or Settings in the clips panel): beacon on/off, attackable-only, round button, beacon size and corner, and key bindings for Record and Clips set by pressing the key.
- Recorder window redrawn with smooth, anti-aliased rounded shapes, a status card, and a Settings dialog (trigger, linger, quick record key, clips folder, storage limit, quality).
- In-game panels and pop-outs have rounded corners.
- Recorder: the clips folder and the video player are raised in front of the game, centred on WoW's monitor, without stealing focus or faking input.

## 1.3.0 - 2026-11-14
- Addon: the button bar is now a round WRC icon with side pop-outs. Hover it and REC slides out on the left, Clips on the right. Click the icon to start or stop recording, drag to move. The dot is cyan when idle and red while recording.
- Addon: in-game clips panel (`/wrc clips`, the Clips pop-out, or the key binding). Shows where clips are saved and the 12 newest clips with type, time, length, size and a Play button. Play opens the clip in the PC's video player; "Open in Windows" opens the folder. The list refreshes on `/reload` (Reload list button).
- Recorder: writes the clip list into the addon folder (`Clips.lua`) after every recording, opens clips on Play, and keeps recordings you start by hand however short they are.

## 1.2.1 - 2026-11-14
- Recorder: the beacon reader now keys on the magenta-to-cyan edge of the finder, so it still reads the beacon when another overlay touches or covers its top edge (found on a live client where a second addon draws a colour strip in the same corner). The live capture is now a test fixture.

## 1.2.0 - 2026-11-14
- Quick record key: **Ctrl+Alt+R** in the recorder (system-wide, change `hotkey` in `config.json`), and in-game key bindings under Options > Keybindings > AddOns > WRC.
- Ionity branding: wordmark on the icons and in the recorder window, cyan accent and title on the in-game bar.
- Icons redrawn with gradient, glow and highlight.

## 1.1.0 - 2026-11-14
- Addon: movable in-game **REC** and **Folder** buttons (`/wrc buttons` hides them), `/wrc folder`, addon-list icon.
- Recorder: window with status, **Record / Stop** and **Open folder** buttons replaces the tray icon. Manual recording works with no beacon on screen and stops at once. Clips from the buttons are named `WRC_Manual_...`.
- Recorder fixes found by recording on real hardware: constant 60 fps output (variable rate lost most frames when an audio device was attached), silent audio devices are skipped, and monitors are matched to capture outputs by content (multi-monitor setups).
- Icons: app icon, CurseForge avatar, addon icon (`tools/make_icons.py`).

## 1.0.0 - 2026-11-14
- First release.
- Addon: opposite-faction detection (target, focus, mouseover, nameplates, arena), auto faction, pixel beacon, `/wrc` commands. Interface 16001 (Forever), 120105, 50504, 20506, 11509.
- Recorder: self-calibrating beacon reader with 5x7 glyph OCR, hardware auto-attune (AV1 / HEVC / H.264), bitrate ceiling, storage limit, tray icon.
