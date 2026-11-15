# Publishing WRC on CurseForge

## What to upload

Upload **`release/WRC-1.5.0.zip`** only. It holds the `WRC` folder with the
`.toc`, eight Lua files, `Bindings.xml` and four `.tga` textures, and nothing else.

CurseForge's automated check rejects archives that contain executable or
runnable files (.exe, .bat, .sh), so the recorder can never go in the addon
zip. Its moderation policy also says external download links for files are
not allowed. Describe the recorder as a separate companion app and name the
website; if a moderator objects to the link, remove it and keep the name.
Publish the recorder itself as a GitHub release.

## Steps

1. Sign in at https://authors.curseforge.com and choose **Create project**.
2. Game: **World of Warcraft**. Class: **Addons**.
3. Name: `WRC - WoW Record Combat`. Summary and description: below.
4. Categories: **PvP** (main), **Combat**, **Audio & Video**.
5. License: **Custom License** and paste the text of `LICENSE.md`
   (or pick All Rights Reserved; your choice).
6. Logo: `icons/wrc-curseforge-avatar-400.png` (drawn by `tools/make_icons.py`
   with plain geometry, not AI-generated).
7. Save, then **Files > Upload file**, pick `WRC-1.5.0.zip`.
   - Release type: **Release** (or Beta until you have played with it).
   - Game versions: CurseForge reads them from the `## Interface:` line.
     Check that **Forever 1.60.1** is ticked; untick any client you have not
     tested.
   - Changelog: paste the 1.5.0 down to 1.0.0 sections of `CHANGELOG.md`.
8. Submit. The project and the file are both reviewed before they go public.

## Before you submit

- Log in on WoW Forever and run `/dump select(4, GetBuildInfo())`. It must
  print a number that is on the `## Interface:` line of `WRC.toc`
  (16001 at launch). If Blizzard has bumped it, edit the line and re-zip.
- `/wrc test` shows the word on the beacon and the recorder saves a clip.
- Take two or three screenshots for the project page: beacon idle, beacon
  showing ALLIANCE, the clips folder.

## Summary (max 256 characters)

Auto-record your PvP. WRC shows a tiny beacon when opposite-faction players are near or fighting you; the free WRC Recorder app sees it and saves a small, sharp clip of every fight.

## Description

**WRC - WoW Record Combat** turns world PvP, battlegrounds and arenas into short clips without you pressing anything.

**How it works**

- The addon watches your target, focus, mouseover, nameplates and arena opponents for living players of the other faction that you can attack. Your own faction is detected automatically.
- When one appears, a small strip in the corner of the screen switches from IDLE to ALLIANCE or HORDE.
- The companion app **WRC Recorder** (Windows, free, open source, from Ionity) reads that strip from the screen and records until 10 seconds after the enemy is gone.

**What you get**

- Clips of fights only, named by faction, character and time.
- Small files: the recorder picks the best encoder your graphics card has (AV1, HEVC or H.264) and caps the bitrate.
- No setup: the recorder finds the strip by itself at any resolution.

**Buttons and keys**: a round movable icon whose side pop-outs give you REC (record by hand) and Folder (open your clips), and a settings panel (`/wrc settings`) where you set options and press the keys you want for both.

**Commands**: `/wrc` lists them. `/wrc test` shows an enemy for 10 seconds, `/wrc rec` records by hand, `/wrc size`, `/wrc corner` and `/wrc offset` move and resize the strip, `/wrc off` hides it.

**Fair play**: the addon only displays information the game already gives you. It does not target, cast, move or automate anything, and the recorder only looks at the screen.

**Death cam**: die in a fight and the recorder keeps the last 20 seconds; the addon tells you who was targeting you (`/wrc deaths`). Attacked while AFK is kept too.

**Clips in game**: `/wrc clips` shows where your clips are saved and lists the newest ones with Play buttons (the recorder opens them on your PC).

**Without the recorder** the addon still works as a compact enemy-faction indicator.

Supports WoW Forever (1.60.1), Midnight, Mists of Pandaria Classic, Burning Crusade Classic Anniversary and Classic Era.

Made by Johan Wilhelm van Antwerp, Ionity (Pty) Ltd. Building Tomorrow, Today.
