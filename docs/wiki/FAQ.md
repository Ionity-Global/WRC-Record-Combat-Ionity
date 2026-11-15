# FAQ

**Is this allowed / safe?**
The addon uses only the normal addon API and shows what the game already shows you. The recorder reads screen pixels only — like any screen recorder or stream software. It does not read memory, inject, automate input or click anything in the game.

**Why does a strip show in my clips?**
That is the beacon; the recorder needs to see it. It is 390 × 27 px in a corner. Make it smaller with `/wrc size 2`.

**Can WRC play clips inside WoW?**
No addon can play video in WoW. Play opens your PC's player in front of the game.

**Does it work for Horde and Alliance?**
Yes, your faction is detected and the other one triggers.

**Does it record PvE?**
Only with `trigger_mode = any_combat`, or the death cam if you die, or manual recording.

**Why is FFmpeg downloaded?**
FFmpeg does the capture and encoding. WRC fetches an official Windows build on first start if none is found.

**Licence?**
CC BY-NC-SA 4.0 under Policy 986 AED — free to use and modify with credit, not for commercial resale.
