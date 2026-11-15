-- WRC - WoW Record Combat | Ionity (Pty) Ltd | Author: Johan Wilhelm van Antwerp
-- (c) 2018-2026 Antwerp Designs | Ionity (Pty) Ltd | Policy 986 AED | CC BY-NC-SA 4.0
--
-- The in-game clips panel: where clips are saved and the newest clips, each
-- with a Play button. The list comes from Clips.lua, which the WRC Recorder
-- rewrites after every recording; WoW only reads it when the UI loads, so the
-- panel has a Reload button. Play and "Open in Windows" ask the recorder to
-- open the clip or the folder on your PC (WoW cannot play video files itself).

local _, ns = ...

local ROWS, ROW_H, WIDTH = 12, 22, 540
local CYAN = { 0, 0.776, 1 }
local panel, rows, pathText, infoText

local function solid(parent, layer, r, g, b, a)
    local t = parent:CreateTexture(nil, layer)
    t:SetColorTexture(r, g, b, a or 1)
    return t
end

local function text(parent, template, point, rel, relPoint, x, y)
    local fs = parent:CreateFontString(nil, "OVERLAY", template or "GameFontHighlightSmall")
    fs:SetPoint(point, rel, relPoint, x, y)
    return fs
end

local function pill(parent, label, width, onClick)
    return ns.Pill(parent, label, width, 20, onClick)
end

local function length(secs)
    secs = math.floor(tonumber(secs) or 0)
    if secs <= 0 then return "" end
    return string.format("%d:%02d", math.floor(secs / 60), secs % 60)
end

-- "WRC_Alliance_Azzinoth_20261114_205817.mp4" -> "Alliance", "Azzinoth"
local function kind(name)
    return (name or ""):match("^WRC_(%a+)_") or "Clip"
end

local function character(name)
    return (name or ""):match("^WRC_%a+_(%a+)_%d") or ""
end

local function build()
    panel = CreateFrame("Frame", "WRCClipsPanel", UIParent)
    panel:SetSize(WIDTH, 100 + ROWS * ROW_H)
    panel:SetPoint("CENTER", UIParent, "CENTER", 0, 40)
    panel:SetFrameStrata("DIALOG")
    panel:SetToplevel(true)
    panel:SetMovable(true)
    panel:EnableMouse(true)
    panel:SetClampedToScreen(true)
    panel:RegisterForDrag("LeftButton")
    panel:SetScript("OnDragStart", panel.StartMoving)
    panel:SetScript("OnDragStop", panel.StopMovingOrSizing)

    ns.Rounded(panel, "BACKGROUND", CYAN[1], CYAN[2], CYAN[3], 0.9)            -- thin cyan outline
    ns.Rounded(panel, "BORDER", 0.05, 0.11, 0.16, 0.97, 1)                    -- navy body, rounded corners

    text(panel, "GameFontNormal", "TOPLEFT", panel, "TOPLEFT", 12, -10):SetText("|cffffffffWRC Clips|r  |cff00c6ffIONITY|r")
    pill(panel, "X", 22, function() panel:Hide() end):SetPoint("TOPRIGHT", panel, "TOPRIGHT", -10, -8)

    pathText = text(panel, nil, "TOPLEFT", panel, "TOPLEFT", 12, -32)
    infoText = text(panel, "GameFontDisableSmall", "TOPLEFT", panel, "TOPLEFT", 12, -46)

    rows = {}
    for i = 1, ROWS do
        local row = CreateFrame("Frame", nil, panel)
        row:SetSize(WIDTH - 24, ROW_H)
        row:SetPoint("TOPLEFT", panel, "TOPLEFT", 12, -62 - (i - 1) * ROW_H)
        if i % 2 == 0 then
            ns.Rounded(row, "ARTWORK", 1, 1, 1, 0.05)
        end
        row.kind = text(row, nil, "LEFT", row, "LEFT", 4, 0)
        row.who = text(row, nil, "LEFT", row, "LEFT", 76, 0)
        row.when = text(row, nil, "LEFT", row, "LEFT", 176, 0)
        row.len = text(row, nil, "LEFT", row, "LEFT", 290, 0)
        row.size = text(row, nil, "LEFT", row, "LEFT", 345, 0)
        row.play = pill(row, "Play", 48, function()
            if row.clipId then ns.PlayClip(row.clipId) end
        end)
        row.play:SetPoint("RIGHT", row, "RIGHT", -4, 0)
        rows[i] = row
    end

    pill(panel, "Reload list", 92, function() ReloadUI() end):SetPoint("BOTTOMLEFT", panel, "BOTTOMLEFT", 12, 10)
    pill(panel, "Open in Windows", 124, function() ns.OpenFolder() end):SetPoint("BOTTOMLEFT", panel, "BOTTOMLEFT", 112, 10)
    pill(panel, "Settings", 76, function() ns.ToggleSettings() end):SetPoint("BOTTOMLEFT", panel, "BOTTOMLEFT", 244, 10)
    text(panel, "GameFontDisableSmall", "BOTTOMRIGHT", panel, "BOTTOMRIGHT", -12, 14):SetText("Play opens the clip on your PC")
    panel:Hide()
end

local function refresh()
    local data = type(WRC_CLIPS) == "table" and WRC_CLIPS or {}
    if (data.folder or "") == "" then
        pathText:SetText("Start WRC Recorder once, then press Reload list.")
        infoText:SetText("")
    else
        pathText:SetText("Saved in:  |cff00c6ff" .. data.folder .. "|r")
        infoText:SetText((data.total or #data) .. " clips  -  list written " .. (data.updated or "?")
            .. "  -  Reload list to refresh")
    end
    for i = 1, ROWS do
        local row, clip = rows[i], data[i]
        if clip then
            row.clipId = clip.id
            row.kind:SetText(kind(clip.name))
            row.who:SetText("|cff00c6ff" .. character(clip.name) .. "|r")
            row.when:SetText(clip.when or "")
            row.len:SetText(length(clip.secs))
            row.size:SetText(clip.mb and (clip.mb .. " MB") or "")
            row:Show()
        else
            row.clipId = nil
            row:Hide()
        end
    end
end

function ns.HideClips()
    if panel then panel:Hide() end
end

function ns.ToggleClips()
    if not panel then build() end
    if panel:IsShown() then
        panel:Hide()
    else
        ns.HideSettings()          -- one WRC window at a time
        refresh()
        panel:Show()
    end
end
