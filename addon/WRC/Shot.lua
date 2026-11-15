-- WRC - WoW Record Combat | Ionity (Pty) Ltd | Author: Johan Wilhelm van Antwerp
-- (c) 2018-2026 Antwerp Designs | Ionity (Pty) Ltd | Policy 986 AED | CC BY-NC-SA 4.0
--
-- Clean screenshot: makes ALL interface invisible for one second - the whole UI,
-- nameplates and every other overlay drawn on the world, the WRC strip and
-- button - takes a WoW screenshot while it is gone, then puts everything back.
-- The picture lands in WoW's own Screenshots folder.
--
-- Works in combat too: addons may not Hide() the interface in combat, but they
-- may make it fully transparent (SetAlpha 0), which looks the same in a picture.
-- Frames WoW forbids addons to touch are left alone.

local _, ns = ...

local PREFIX = "|cff00c6ffWRC|r "
local HOLD = 1.0          -- seconds the interface stays invisible
local SHOOT_AFTER = 0.15  -- let a few frames render without UI before the picture

local busy = false
local faded = {}          -- frame -> its alpha before we faded it

local function fade(f)
    if not f or faded[f] ~= nil then return end
    local okF, forbidden = pcall(function() return f.IsForbidden and f:IsForbidden() end)
    if not okF or forbidden then return end
    local okA, a = pcall(f.GetAlpha, f)
    if okA and type(a) == "number" and a > 0 and pcall(f.SetAlpha, f, 0) then
        faded[f] = a
    end
end

-- Everything drawn on top of the 3D world that is not part of UIParent:
-- nameplates (their visible part, which is not a protected frame), chat bubbles
-- and other addons' world overlays. Protected and forbidden frames are skipped.
local function fadeWorld()
    if C_NamePlate and C_NamePlate.GetNamePlates then
        local ok, plates = pcall(C_NamePlate.GetNamePlates)
        if ok and type(plates) == "table" then
            for _, plate in pairs(plates) do
                local okU, uf = pcall(function() return plate.UnitFrame end)
                if okU and uf then fade(uf) end
            end
        end
    end
    if WorldFrame and WorldFrame.GetChildren then
        local kids = { pcall(WorldFrame.GetChildren, WorldFrame) }
        if table.remove(kids, 1) then
            for i = 1, #kids do
                local f = kids[i]
                local okP, protected = pcall(function() return f.IsProtected and f:IsProtected() end)
                if okP and not protected then fade(f) end
            end
        end
    end
end

local function restore()
    for f, a in pairs(faded) do
        pcall(f.SetAlpha, f, a)
    end
    faded = {}
    if ns.Beacon and ns.db then ns.Beacon:SetShown(ns.db.enabled) end
    busy = false
end

function ns.CleanScreenshot()
    if busy then return end
    if not Screenshot then
        print(PREFIX .. "this client has no screenshot function")
        return
    end
    busy = true
    ns.HideSettings()
    ns.HideClips()
    if GameTooltip and GameTooltip.Hide then GameTooltip:Hide() end
    if ns.Beacon then ns.Beacon:SetShown(false) end
    fade(UIParent)            -- the whole interface, in combat as well
    fadeWorld()
    C_Timer.After(SHOOT_AFTER, function() Screenshot() end)
    C_Timer.After(HOLD, function()
        restore()
        print(PREFIX .. "clean screenshot saved in WoW's Screenshots folder")
    end)
end
