# Troubleshooting

| Problem | Fix |
|---|---|
| Recorder says **No beacon** | WoW must be windowed/borderless and visible. Check the strip is on screen (`/wrc on`). Run `--snapshot` and look at the saved image. |
| Beacon covered by another addon | `/wrc corner tr` or `/wrc offset 10 10`. |
| Clips have **no sound** | Windows needs a loopback recording device (Stereo Mix, VB-CABLE…) actually carrying game sound when WRC attunes. Route sound to it and run `--attune`, or set `audio_device`. The log says when a device was skipped as silent. |
| Choppy or 26 fps clips | Update to 1.1.0+ (forces constant 60 fps). |
| Files too big | Raise `quality` (e.g. AV1 36), set `max_height`, or lower `bits_per_pixel`. |
| Wrong monitor recorded | Fixed in 1.1.0 (content matching). Run `--attune` after changing monitors. |
| Play / Open in Windows "does nothing" | The window opens on WoW's monitor in front of the game without focus — click it. The recorder must be running. |
| Clips list empty in game | Press *Reload list*. If still empty set `wow_path` in `config.json`. |
| SmartScreen warning | The EXE is not code-signed yet. *More info › Run anyway*. |
| First start slow | One-time FFmpeg download and encoder test. |

**Reporting a bug:** open an [issue](https://github.com/Ionity-Global/wrc-record-combat-ionity/issues) with `wrc.log`, your client and version, and a `--snapshot` image.
