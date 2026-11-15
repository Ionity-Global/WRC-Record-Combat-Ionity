-- WRC - WoW Record Combat | Ionity (Pty) Ltd | Author: Johan Wilhelm van Antwerp
-- (c) 2018-2026 Antwerp Designs | Ionity (Pty) Ltd | Policy 986 AED | CC BY-NC-SA 4.0
--
-- In-game settings: the beacon options and the two key bindings. Open with
-- /wrc settings, the Settings button in the clips panel, or a right-click on
-- the round WRC icon. Keys set here are ordinary WoW key bindings (the same
-- ones listed under Options > Keybindings > AddOns > WRC).

local _, ns = ...

local PREFIX = "|cff00c6ffWRC|r "
local WIDTH, ROW_H = 400, 28
local CORNERS = { "TOPLEFT", "TOPRIGHT", "BOTTOMLEFT", "BOTTOMRIGHT" }
local CORNER_NAMES = { TOPLEFT = "Top left", TOPRIGHT = "Top right", BOTTOMLEFT = "Bottom left", BOTTOMRIGHT = "Bottom right" }
local MODIFIERS = { LSHIFT = true, RSHIFT = true, LCTRL = true, RCTRL = true, LALT = true, RALT = true,
                    LMETA = true, RMETA = true, UNKNOWN = true }

local panel, refreshers, capturing = nil, {}, nil

local function refresh()
    for i = 1, #refreshers do refreshers[i]() end
end

local function stopCapture()
    capturing = nil
    if panel then panel:EnableKeyboard(false) end
    refresh()
end

-- Bind `key` (or clear when nil) to a WRC binding and save it.
local function setKey(binding, key)
    if InCombatLockdown() then
        print(PREFIX .. "key bindings cannot be changed in combat")
        return
    end
    local old1, old2 = GetBindingKey(binding)
    if old1 then SetBinding(old1) end
    if old2 then SetBinding(old2) end
    if key then SetBinding(key, binding) end
    SaveBindings(GetCurrentBindingSet())
    print(PREFIX .. (key and ("bound to " .. key) or "key cleared"))
end

local function onKeyDown(_, key)
    if not capturing or MODIFIERS[key] then return end
    local binding = capturing
    if key ~= "ESCAPE" then
        local combo = (IsAltKeyDown() and "ALT-" or "") .. (IsControlKeyDown() and "CTRL-" or "")
            .. (IsShiftKeyDown() and "SHIFT-" or "") .. key
        setKey(binding, combo)
    end
    stopCapture()
end

local function build()
    local db = ns.db
    panel = CreateFrame("Frame", "WRCSettingsPanel", UIParent)
    panel:SetSize(WIDTH, 78 + 7 * ROW_H)
    panel:SetPoint("CENTER", UIParent, "CENTER", 0, 40)
    panel:SetFrameStrata("DIALOG")
    panel:SetToplevel(true)
    panel:SetMovable(true)
    panel:EnableMouse(true)
    panel:SetClampedToScreen(true)
    panel:RegisterForDrag("LeftButton")
    panel:SetScript("OnDragStart", panel.StartMoving)
    panel:SetScript("OnDragStop", panel.StopMovingOrSizing)
    panel:SetScript("OnKeyDown", onKeyDown)
    panel:SetScript("OnHide", function() capturing = nil end)
    panel:EnableKeyboard(false)

    ns.Rounded(panel, "BACKGROUND", ns.CYAN[1], ns.CYAN[2], ns.CYAN[3], 0.9)
    ns.Rounded(panel, "BORDER", ns.NAVY[1], ns.NAVY[2], ns.NAVY[3], 0.97, 1)

    local title = panel:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    title:SetPoint("TOPLEFT", panel, "TOPLEFT", 14, -12)
    title:SetText("|cffffffffWRC Settings|r  |cff00c6ffIONITY|r")
    ns.Pill(panel, "X", 22, 20, function() panel:Hide() end):SetPoint("TOPRIGHT", panel, "TOPRIGHT", -10, -8)

    local row = 0
    local function line(caption)
        row = row + 1
        local y = -36 - (row - 1) * ROW_H
        local fs = panel:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
        fs:SetPoint("TOPLEFT", panel, "TOPLEFT", 16, y - 7)
        fs:SetText(caption)
        return y
    end

    -- A row whose pill shows a value and changes it when clicked.
    local function option(caption, width, value, onClick)
        local y = line(caption)
        local pill = ns.Pill(panel, "", width, 22, function() onClick() refresh() end)
        pill:SetPoint("TOPRIGHT", panel, "TOPRIGHT", -16, y)
        refreshers[#refreshers + 1] = function() pill:SetText(value()) end
        return pill, y
    end

    local function apply() ns.Apply() end

    option("Beacon strip (off also stops auto-recording)", 70,
        function() return db.enabled and "On" or "Off" end,
        function() db.enabled = not db.enabled apply() end)
    option("Count only enemies you can attack", 70,
        function() return db.requireAttackable and "On" or "Off" end,
        function() db.requireAttackable = not db.requireAttackable end)
    option("Round WRC button", 70,
        function() return db.buttons and "Shown" or "Hidden" end,
        function() db.buttons = not db.buttons apply() end)

    local _, y = option("Beacon size (pixels per cell)", 34,
        function() return tostring(db.cell) end, function() end)
    ns.Pill(panel, "-", 24, 22, function() db.cell = math.max(2, db.cell - 1) apply() refresh() end)
        :SetPoint("TOPRIGHT", panel, "TOPRIGHT", -82, y)
    ns.Pill(panel, "+", 24, 22, function() db.cell = math.min(12, db.cell + 1) apply() refresh() end)
        :SetPoint("TOPRIGHT", panel, "TOPRIGHT", -54, y)

    option("Beacon corner", 100,
        function() return CORNER_NAMES[db.corner] or db.corner end,
        function()
            for i = 1, #CORNERS do
                if CORNERS[i] == db.corner then
                    db.corner = CORNERS[i % #CORNERS + 1]
                    break
                end
            end
            apply()
        end)

    local function keyRow(caption, binding)
        local _, ky = option(caption, 130,
            function()
                if capturing == binding then return "Press a key..." end
                return GetBindingKey(binding) or "Click to set"
            end,
            function()
                if InCombatLockdown() then
                    print(PREFIX .. "key bindings cannot be changed in combat")
                elseif capturing == binding then
                    capturing = nil
                    panel:EnableKeyboard(false)
                else
                    capturing = binding
                    panel:EnableKeyboard(true)       -- the next key press goes to onKeyDown
                end
            end)
        ns.Pill(panel, "Clear", 46, 22, function() capturing = nil setKey(binding, nil) refresh() end)
            :SetPoint("TOPRIGHT", panel, "TOPRIGHT", -152, ky)
    end
    keyRow("Record key (start / stop)", "WRC_TOGGLE_REC")
    keyRow("Clips key (show / hide)", "WRC_OPEN_FOLDER")

    local note = panel:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
    note:SetPoint("BOTTOMLEFT", panel, "BOTTOMLEFT", 16, 12)
    note:SetText("Esc cancels a key. The recorder has its own key too (Ctrl+Alt+R).")
    panel:Hide()
end

function ns.HideSettings()
    if panel then panel:Hide() end
end

function ns.ToggleSettings()
    if not ns.db then return end
    if not panel then build() end
    if panel:IsShown() then
        panel:Hide()
    else
        ns.HideClips()             -- one WRC window at a time
        stopCapture()
        panel:Show()
    end
end
