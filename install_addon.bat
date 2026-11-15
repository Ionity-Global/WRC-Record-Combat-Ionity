@echo off
rem Copies the WRC addon into every WoW client found in the usual install folders.
setlocal enabledelayedexpansion
cd /d "%~dp0"
set COUNT=0
for %%R in ("C:\Program Files (x86)\World of Warcraft" "C:\Program Files\World of Warcraft" "C:\World of Warcraft" "D:\World of Warcraft" "C:\Games\World of Warcraft" "D:\Games\World of Warcraft" "E:\World of Warcraft" "E:\Games\World of Warcraft") do (
  for %%F in (_forever_ _retail_ _classic_ _classic_era_ _anniversary_) do (
    if exist "%%~R\%%F\Interface\AddOns" (
      xcopy /e /i /y /q "addon\WRC" "%%~R\%%F\Interface\AddOns\WRC" >nul
      echo Installed to %%~R\%%F\Interface\AddOns\WRC
      set /a COUNT+=1
    )
  )
)
if !COUNT!==0 echo No WoW install found. Copy the folder addon\WRC into your "Interface\AddOns" folder by hand.
pause
