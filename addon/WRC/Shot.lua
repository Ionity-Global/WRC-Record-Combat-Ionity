-- WRC - WoW Record Combat | Ionity (Pty) Ltd | Author: Johan Wilhelm van Antwerp
-- (c) 2018-2026 Antwerp Designs | Ionity (Pty) Ltd | Policy 986 AED | CC BY-NC-SA 4.0
--
-- Clean screenshot: hides ALL interface for one second - the whole UI (like
-- Alt+Z), nameplates and every other overlay drawn on the world, the WRC strip
-- and button - takes a WoW screenshot while it is all gone, then puts everything
-- back. The picture lands in WoW's own Screenshots folder.
--
-- WoW does not let addons hide the interface during combat. In combat WRC takes
-- a normal screenshot instead and says so. If combat starts during the second
-- the UI is hidden, it comes back at once (before combat lockdown begins).

local _, ns = ...

local PREFIX = "|cff00c6ffWRC|r "
local HOLD = 1.0          -- seconds the interface stays hidden
local SHOOT_AFTER = 0.15  -- let a few frames render without UI before the picture

local busy = false
local shot = false
local hidUI = false
local dimmed = {}         -- world overlays we faded out: frame -> its alpha before

-- Fade out everything drawn on top of the 3D world (nameplates, chat bubbles,
-- overlays of other addons). Forbidden and protected frames are left alone;
-- any frame that refuses is simply skipped.
local function dimWorld()
    if not WorldFrame or not WorldFrame.GetChildren then return end
    local kids = { pcall(WorldFrame.GetChildren, WorldFrame) }
    if not table.remove(kids, 1) then return end
    for i = 1, #kids do
        local f = kids[i]
        local okF, forbidden = pcall(function() return f.IsForbidden and f:IsForbidden() end)
        local okP, protected = pcall(function() return f.IsProtected and f:IsProtected() end)
        if okF and not forbidden and okP and not protected then
            local okA, a = pcall(f.GetAlpha, f)
            if okA and type(a) == "number" and a > 0 and pcall(f.SetAlpha, f, 0) then
                dimmed[f] = a
            end
        end
    end
end

local function undimWorld()
    for f, a in pairs(dimmed) do
        pcall(f.SetAlpha, f, a)
    end
    dimmed = {}
end

local function restore()
    if not busy then return end
    if hidUI and UIParent and not UIParent:IsShown() then
        UIParent:Show()
    end
    hidUI = false
    undimWorld()
    if ns.Beacon and ns.db then ns.Beacon:SetShown(ns.db.enabled) end
    busy = false
end

-- Combat is about to start: put the interface back now, while that is still allowed.
local guard = CreateFrame("Frame")
guard:RegisterEvent("PLAYER_REGEN_DISABLED")
guard:SetScript("OnEvent", restore)

function ns.CleanScreenshot()
    if busy then return end
    if not Screenshot then
        print(PREFIX .. "this client has no screenshot function")
        return
    end
    if InCombatLockdown() then
        print(PREFIX .. "WoW does not allow hiding the interface in combat - normal screenshot taken")
        Screenshot()
        return
    end
    busy, shot = true, false
    ns.HideSettings()
    ns.HideClips()
    if ns.Beacon then ns.Beacon:SetShown(false) end
    dimWorld()
    if UIParent and UIParent:IsShown() then
        UIParent:Hide()
        hidUI = true
    end
    C_Timer.After(SHOOT_AFTER, function()
        if busy then
            Screenshot()
            shot = true
        end
    end)
    C_Timer.After(HOLD, function()
        restore()
        if shot then
            print(PREFIX .. "clean screenshot saved in WoW's Screenshots folder")
        else
            print(PREFIX .. "combat started - screenshot cancelled, interface restored")
        end
    end)
end
