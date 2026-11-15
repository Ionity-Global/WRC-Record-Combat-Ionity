# Building from Source

```bat
git clone https://github.com/Ionity-Global/wrc-record-combat-ionity
cd wrc-record-combat-ionity\recorder
python -m pip install -r requirements.txt pytest lupa
python -m pytest -q          :: runs the real addon Lua against a mock WoW API
python -m wrc_recorder       :: run from source
build.bat                    :: venv + tests + PyInstaller -> release\WRC-Recorder.exe
```

Python 3.11+ on Windows. Dependencies: numpy, mss, Pillow, tkinter (bundled).

## Layout

```
addon/WRC/        Lua addon (Font, Beacon, Skin, Buttons, Clips, Panel, Settings, Core)
recorder/         Python recorder (beacon, trigger, attune, recorder, clips, winutil, app)
recorder/tests/   pytest suite + live capture fixture
tools/            font generator, icon maker, probes
icons/            app, CurseForge and brand icons
```

`tools/gen_font.py` regenerates `addon/WRC/Font.lua` from `recorder/wrc_recorder/font.py` so both sides share one font.

## Releasing

1. Bump `## Version` in `WRC.toc`, `__version__`, and `CHANGELOG.md`.
2. Zip `addon/WRC` as `WRC-<version>.zip` (folder `WRC` at the root).
3. Build the EXE, attach both to a GitHub release, upload the zip to CurseForge.
