# Death Cam and AFK

## Death cam

With `deathcam` on, the recorder starts a **standby recording** whenever you enter combat, PvE included.

- Survive → it is deleted three seconds after the fight ends.
- Die → the last **20 s before** and **5 s after** the death are kept as `WRC_Death_<Character>_….mp4`. The trim is a stream copy, so no quality is lost and it is instant.
- If an enemy-triggered clip is already running when you die, it is kept in full and renamed `…AllianceDeath…` / `…HordeDeath…`.

The encoder runs during every fight. On a hardware encoder the cost is small; turn `deathcam` off if you do not want it.

## Death report

On death the addon prints the zone and who was targeting you in the last 10 seconds (name and class, or NPC). The last 20 deaths are kept: `/wrc deaths`.

## AFK

Attacked while flagged AFK, the clip is kept as `WRC_AFK_….mp4` (`afk_record`).
