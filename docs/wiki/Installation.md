# Installation

## 1. The addon

**CurseForge app:** search *WRC Record Combat* and install.

**By hand:**
1. Download `WRC-<version>.zip` from Releases.
2. Unzip so you get a `WRC` folder.
3. Put it in your client's AddOns folder, for example:
   - WoW: Forever — `World of Warcraft\_forever_\Interface\AddOns\WRC`
   - Retail — `World of Warcraft\_retail_\Interface\AddOns\WRC`
   - Classic Era — `World of Warcraft\_classic_era_\Interface\AddOns\WRC`
4. Or run `install_addon.bat` from the repository; it looks in the common install locations.

Log in. Chat shows `WRC v1.6.0 by Ionity loaded`, a thin strip appears top-left and the round WRC button sits on screen.

## 2. The recorder

1. Download `WRC-Recorder.exe` from Releases and put it in its own folder (it writes `config.json`, `attune.json` and `wrc.log` next to itself).
2. Run it. Windows SmartScreen may warn because the EXE is not code-signed yet — choose *More info › Run anyway*.
3. First start:
   - If FFmpeg is not found, WRC downloads it (one time, ~170 MB).
   - It tests your encoders on a real screen capture and keeps the best one that works (a few seconds).
4. The window shows **Watching** once it sees the beacon.

## 3. Test

In game type `/wrc test`. The strip reads ALLIANCE or HORDE for 10 seconds and a clip appears in `Videos\WRC`.

## Requirements

- Windows 10 or 11, a GPU from the last ~8 years recommended (NVIDIA NVENC, AMD AMF or Intel QSV). Software H.264 works without one but uses more CPU.
- WoW in **windowed** or **borderless** mode, not covered by another window.
- The beacon must stay visible (do not hide it under another addon's frame).
