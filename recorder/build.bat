@echo off
rem WRC Recorder - builds release\WRC-Recorder.exe  |  Ionity (Pty) Ltd
rem Needs Python 3.10+ from python.org (tick "Add python.exe to PATH").
setlocal
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% --version || (echo Python was not found. Install it from https://www.python.org/downloads/ & exit /b 1)
if not exist .venv %PY% -m venv .venv || exit /b 1
call .venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt pyinstaller pytest lupa || exit /b 1
echo.
echo === Running tests ===
python -m pytest -q || (echo Tests failed - not building. & exit /b 1)
echo.
echo === Building EXE ===
rem Work files go to a fresh temp folder: a locked leftover build folder cannot block the build.
set WORK=%TEMP%\wrc-build-%RANDOM%
pyinstaller --noconfirm --clean --workpath "%WORK%" --onefile --windowed --name WRC-Recorder --icon wrc.ico --add-data "wrc.ico;." --add-data "ionity_logo.png;." --hidden-import PIL.ImageTk --hidden-import PIL._tkinter_finder run_wrc.py || exit /b 1
if not exist ..\release mkdir ..\release
copy /y dist\WRC-Recorder.exe ..\release\WRC-Recorder.exe >nul
echo.
echo === Checking the EXE ===
..\release\WRC-Recorder.exe --selftest || exit /b 1
echo.
echo Done: release\WRC-Recorder.exe
