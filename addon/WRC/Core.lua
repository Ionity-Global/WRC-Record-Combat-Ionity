-- WRC - WoW Record Combat | Ionity (Pty) Ltd | Author: Johan Wilhelm van Antwerp
-- (c) 2018-2026 Antwerp Designs | Ionity (Pty) Ltd | Policy 986 AED | CC BY-NC-SA 4.0
-- https://www.ionity.today
--
-- Works out whether an opposite-faction player is on screen or fighting you and
-- publishes that on the beacon. The addon only DISPLAYS information the game
-- already shows you; it never acts, targets or automates anything.
--
-- State bits (beacon columns 5-12, white = 1):
--   1 enemy player seen     2 PvP combat          3 any combat
--   4 manual record         5 enemy is Horde      6 heartbeat (flips every second)
--   7-8 checksum = (number of set bits in 1-6, plus 1) mod 4, low bit first

local ADDON, ns = ...
local Beacon = ns.Beacon

local VERSION = "1.5.0"
local PREFIX = "|cff00c6ffWRC|r "
local TICK = 0.2          -- seconds between scans
local ENEMY_HOLD = 6      -- an enemy seen this recently still counts for PvP combat

local defaults = {
    enabled = true,
    cell = 3,                  -- beacon cell size in physical pixels
    corner = "TOPLEFT",
    x = 0, y = 0,              -- offset from the corner in physical pixels
    requireAttackable = true,  -- ignore enemy players you cannot attack (sanctuaries, unflagged)
    buttons = true,            -- show the round in-game button with its REC / Folder pop-outs
}

local db
local enemyFaction            -- "Alliance" / "Horde", or nil while neutral
local inPvPZone = false       -- battleground or arena
local manual = false
local lastEnemySeen, lastPvPHit, testUntil, folderUntil = -100, -100, -100, -100
local playUntil, playId = -100, nil
local wasDead = false
local targeters = {}          -- who has been targeting you lately: name -> { t, what }
local TARGETER_WINDOW = 10    -- seconds before a death that still count
local lastBits, lastWord, lastSignal

-- Modern clients (Forever, Midnight) hide some combat values from addons as
-- "secret values". Branching on one is an error, so every unit query goes
-- through safe(): errors and secrets both come back as nil ("unknown").
local issecret = issecretvalue or function() return false end
local MODERN = (issecretvalue ~= nil) or (C_Secrets ~= nil)

local function safe(fn, ...)
    if not fn then return nil end
    local ok, a = pcall(fn, ...)
    if not ok or issecret(a) then return nil end
    return a
end

local UNITS = { "target", "focus", "mouseover", "targettarget", "pettarget" }
for i = 1, 40 do UNITS[#UNITS + 1] = "nameplate" .. i end
for i = 1, 5 do UNITS[#UNITS + 1] = "arena" .. i end

local function isEnemyPlayer(unit)
    if not safe(UnitExists, unit) then return false end
    if not safe(UnitIsPlayer, unit) then return false end
    if safe(UnitFactionGroup, unit) ~= enemyFaction then return false end
    if safe(UnitIsDeadOrGhost, unit) then return false end
    if db.requireAttackable and not safe(UnitCanAttack, "player", unit) then return false end
    return true
end

-- Remember every hostile unit that is targeting you right now. This is what the
-- death report is built from; it only reads what your nameplates already show.
local function trackTargeters(now)
    for i = 1, #UNITS do
        local unit = UNITS[i]
        if safe(UnitExists, unit) and safe(UnitIsUnit, unit .. "target", "player")
            and safe(UnitCanAttack, unit, "player") then
            local name = safe(UnitName, unit)
            if name then
                local what = safe(UnitIsPlayer, unit) and (safe(UnitClass, unit) or "player") or "NPC"
                targeters[name] = { t = now, what = what }
            end
        end
    end
end

-- You just died: say who was on you, and keep it in the death log.
local function onDeath(now)
    local list = {}
    for name, info in pairs(targeters) do
        if now - info.t <= TARGETER_WINDOW then
            list[#list + 1] = name .. " (" .. info.what .. ")"
        end
    end
    table.sort(list)
    targeters = {}
    local by = (#list > 0) and table.concat(list, ", ") or "nobody WRC could see"
    local zone = (GetRealZoneText and GetRealZoneText()) or ""
    db.deaths = db.deaths or {}
    table.insert(db.deaths, 1, { when = date("%d %b %H:%M"), zone = zone, by = by })
    while #db.deaths > 20 do table.remove(db.deaths) end
    print(PREFIX .. "you died" .. (zone ~= "" and (" in " .. zone) or "") .. ". Targeting you: " .. by)
end

local function refreshFaction()
    local mine = safe(UnitFactionGroup, "player")
    if mine == "Alliance" then
        enemyFaction = "Horde"
    elseif mine == "Horde" then
        enemyFaction = "Alliance"
    else
        enemyFaction = nil
    end
end

local function refreshZone()
    local _, kind = IsInInstance()
    inPvPZone = (kind == "pvp" or kind == "arena")
end

local function publish()
    if not db or not db.enabled then return end
    local now = GetTime()

    local seen = false
    if enemyFaction then
        for i = 1, #UNITS do
            if isEnemyPlayer(UNITS[i]) then
                seen = true
                break
            end
        end
    end
    if seen then lastEnemySeen = now end

    local combat = (InCombatLockdown() and true) or (safe(UnitAffectingCombat, "player") and true) or false
    local recent = (now - lastEnemySeen) < ENEMY_HOLD
    local pvp = combat and (recent or inPvPZone or (now - lastPvPHit) < ENEMY_HOLD)
    -- In battlegrounds and arenas unit details can be hidden, so combat there counts as the enemy.
    local enemy = seen or pvp
    if now < testUntil then enemy = true end

    local dead = safe(UnitIsDeadOrGhost, "player") and true or false
    local afk = safe(UnitIsAFK, "player") and true or false
    if combat and not dead then trackTargeters(now) end
    if dead and not wasDead then onDeath(now) end
    wasDead = dead

    local signalling = manual or enemy or (afk and combat)
    if signalling ~= lastSignal then
        lastSignal = signalling
        ns.UpdateButtons(manual, signalling)      -- red, pulsing icon while a recording is wanted
    end

    local horde = (enemyFaction == "Horde")
    local beat = (math.floor(now) % 2) == 1

    local bits = { enemy, pvp, combat, manual, horde, beat, false, false }
    local n = 1
    for i = 1, 6 do
        if bits[i] then n = n + 1 end
    end
    bits[7] = (n % 2) == 1
    bits[8] = (math.floor(n / 2) % 2) == 1

    local word
    if now < playUntil and playId then
        word = "PLAY " .. playId   -- the recorder opens that clip in the PC's video player
    elseif now < folderUntil then
        word = "FOLDER"       -- the recorder opens the clips folder when it reads this
    elseif dead then
        word = "DEAD"         -- death cam: the recorder keeps the seconds before this
    elseif afk and combat then
        word = "AFK"          -- attacked while away: the recorder keeps the clip
    elseif manual then
        word = "REC"
    elseif enemy then
        word = (enemyFaction or "ENEMY"):upper()
    elseif combat then
        word = "COMBAT"
    else
        word = "IDLE"
    end

    local key = 0
    for i = 1, 8 do
        if bits[i] then key = key + 2 ^ (i - 1) end
    end
    if key ~= lastBits then
        lastBits = key
        Beacon:SetBits(bits)
    end
    if word ~= lastWord then
        lastWord = word
        Beacon:SetWord(word)
    end
end

-- The character name goes on the beacon so clips are named after who you played.
-- Only plain letters A-Z fit the pixel font; accented letters are left out.
local function refreshName()
    local name = safe(UnitName, "player") or ""
    Beacon:SetName(name:upper():gsub("[^A-Z]", ""):sub(1, 10))
end

local function layout()
    Beacon:Layout(db.cell, db.corner, db.x, db.y)
    Beacon:SetShown(db.enabled)
    refreshName()
    ns.InitButtons(db)
    lastBits, lastWord = nil, nil
end

ns.Apply = layout      -- used by the settings panel after it changes an option

function ns.ToggleManual()
    if not db or not db.enabled then return end
    manual = not manual
    lastSignal = nil
    ns.UpdateButtons(manual, manual)
    print(PREFIX .. "manual recording " .. (manual and "started" or "stopped"))
end

function ns.OpenFolder()
    if not db or not db.enabled then return end
    folderUntil = GetTime() + 2
    print(PREFIX .. "clips folder opened in Windows. It does not take focus from the game: "
        .. "look on your other monitors or the taskbar.")
end

-- id: the two-letter clip id from Clips.lua.
function ns.PlayClip(id)
    if not db or not db.enabled or type(id) ~= "string" or not id:match("^%u%u$") then return end
    playId, playUntil = id, GetTime() + 2
    print(PREFIX .. "playing the clip on your PC (look on your other monitors or the taskbar)")
end

-- Key bindings (Options > Keybindings > AddOns > WRC). See Bindings.xml.
BINDING_HEADER_WRC = "WRC - WoW Record Combat (Ionity)"
BINDING_NAME_WRC_TOGGLE_REC = "Start / stop recording"
BINDING_NAME_WRC_OPEN_FOLDER = "Show / hide clips"
WRC_ToggleRecording = ns.ToggleManual
WRC_OpenFolder = function() ns.ToggleClips() end

-- Classic-family clients still have the combat log: a hit between you (or your
-- pet) and a hostile player-controlled unit is PvP combat even with no target.
local MINE, HOSTILE_PLAYER = 0x1, 0x140
local band = bit and bit.band
local function onCombatLog()
    if not band or not CombatLogGetCurrentEventInfo then return end
    local _, _, _, _, _, sFlags, _, _, _, dFlags = CombatLogGetCurrentEventInfo()
    if type(sFlags) ~= "number" or type(dFlags) ~= "number" then return end
    local hit = (band(sFlags, MINE) ~= 0 and band(dFlags, HOSTILE_PLAYER) == HOSTILE_PLAYER)
        or (band(dFlags, MINE) ~= 0 and band(sFlags, HOSTILE_PLAYER) == HOSTILE_PLAYER)
    if hit then lastPvPHit = GetTime() end
end

local events = CreateFrame("Frame")
local function listen(event)
    pcall(events.RegisterEvent, events, event) -- an event unknown to this client must not break loading
end

events:SetScript("OnEvent", function(_, event, arg1)
    if event == "PLAYER_LOGIN" then
        WRC_DB = WRC_DB or {}
        db = WRC_DB
        ns.db = db
        for k, v in pairs(defaults) do
            if db[k] == nil then db[k] = v end
        end
        refreshFaction()
        refreshZone()
        layout()
        C_Timer.NewTicker(TICK, publish)
        print(PREFIX .. "v" .. VERSION .. " by |cff00c6ffIonity|r loaded. Type /wrc for options. Recorder: ionity.today")
    elseif event == "COMBAT_LOG_EVENT_UNFILTERED" then
        onCombatLog()
    elseif not db then
        return
    elseif event == "DISPLAY_SIZE_CHANGED" or event == "UI_SCALE_CHANGED" then
        layout()
    elseif event == "UNIT_FACTION" then
        if arg1 == "player" then refreshFaction() end
    else
        refreshFaction()
        refreshZone()
        refreshName()
    end
end)

listen("PLAYER_LOGIN")
listen("PLAYER_ENTERING_WORLD")
listen("ZONE_CHANGED_NEW_AREA")
listen("UNIT_FACTION")
listen("NEUTRAL_FACTION_SELECT_RESULT")
listen("DISPLAY_SIZE_CHANGED")
listen("UI_SCALE_CHANGED")
if not MODERN then listen("COMBAT_LOG_EVENT_UNFILTERED") end

local CORNERS = { TL = "TOPLEFT", TR = "TOPRIGHT", BL = "BOTTOMLEFT", BR = "BOTTOMRIGHT" }

local function help()
    print(PREFIX .. "commands:")
    print("  /wrc on | off - show or hide the beacon (off also stops auto-recording)")
    print("  /wrc rec - start or stop a manual recording (same as the REC button)")
    print("  /wrc settings - options and key bindings (or right-click the round WRC icon)")
    print("  /wrc clips - show your clips in game: where they are saved, and Play buttons")
    print("  /wrc folder - open the clips folder in Windows")
    print("  /wrc deaths - your last deaths and who was targeting you")
    print("  /wrc buttons - show or hide the round WRC button (hover it for REC / Folder)")
    print("  Quick key: Options > Keybindings > AddOns > WRC, or Ctrl+Alt+R in the recorder")
    print("  /wrc test - pretend an enemy is near for 10 seconds")
    print("  /wrc size 2-12 - beacon cell size in pixels (now " .. db.cell .. ")")
    print("  /wrc corner tl|tr|bl|br - screen corner (now " .. db.corner .. ")")
    print("  /wrc offset X Y - pixels in from the corner (now " .. db.x .. " " .. db.y .. ")")
    print("  /wrc attackable on|off - only count enemies you can attack (now " .. (db.requireAttackable and "on" or "off") .. ")")
    print("  /wrc status - what the beacon is showing")
end

SLASH_WRC1 = "/wrc"
SlashCmdList["WRC"] = function(msg)
    if not db then return end
    local cmd, a, b = (msg or ""):lower():match("^%s*(%S*)%s*(%S*)%s*(%S*)")
    if cmd == "on" or cmd == "off" then
        db.enabled = (cmd == "on")
        if not db.enabled then
            manual = false
            lastSignal = nil
            ns.UpdateButtons(false, false)
        end
        layout()
        print(PREFIX .. "beacon " .. cmd)
    elseif cmd == "rec" then
        ns.ToggleManual()
    elseif cmd == "deaths" then
        local log = db.deaths or {}
        if #log == 0 then print(PREFIX .. "no deaths recorded yet") end
        for i = 1, math.min(5, #log) do
            print(PREFIX .. log[i].when .. "  " .. (log[i].zone or "") .. "  -  " .. log[i].by)
        end
    elseif cmd == "clips" then
        ns.ToggleClips()
    elseif cmd == "settings" or cmd == "options" or cmd == "config" then
        ns.ToggleSettings()
    elseif cmd == "folder" then
        ns.OpenFolder()
    elseif cmd == "buttons" then
        db.buttons = not db.buttons
        layout()
        print(PREFIX .. "buttons " .. (db.buttons and "shown" or "hidden"))
    elseif cmd == "test" then
        testUntil = GetTime() + 10
        print(PREFIX .. "test: showing an enemy for 10 seconds")
    elseif cmd == "size" and tonumber(a) then
        db.cell = math.max(2, math.min(12, math.floor(tonumber(a))))
        layout()
        print(PREFIX .. "cell size " .. db.cell)
    elseif cmd == "corner" and CORNERS[a:upper()] then
        db.corner = CORNERS[a:upper()]
        layout()
        print(PREFIX .. "corner " .. db.corner)
    elseif cmd == "offset" and tonumber(a) and tonumber(b) then
        db.x, db.y = math.max(0, math.floor(tonumber(a))), math.max(0, math.floor(tonumber(b)))
        layout()
        print(PREFIX .. "offset " .. db.x .. " " .. db.y)
    elseif cmd == "attackable" and (a == "on" or a == "off") then
        db.requireAttackable = (a == "on")
        print(PREFIX .. "attackable-only " .. a)
    elseif cmd == "status" then
        print(PREFIX .. "showing " .. tostring(lastWord) .. " | enemy faction " .. tostring(enemyFaction)
            .. " | PvP zone " .. tostring(inPvPZone) .. " | beacon " .. (db.enabled and "on" or "off"))
    else
        help()
    end
end
