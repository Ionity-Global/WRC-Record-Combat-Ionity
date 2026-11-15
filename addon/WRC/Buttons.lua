-- WRC - WoW Record Combat | Ionity (Pty) Ltd | Author: Johan Wilhelm van Antwerp
-- (c) 2018-2026 Antwerp Designs | Ionity (Pty) Ltd | Policy 986 AED | CC BY-NC-SA 4.0
--
-- A round WRC icon with two side pop-outs. Hover the icon and REC slides out on
-- the left, Clips (the in-game clips panel) on the right. A small camera with a
-- sword through it sits on the shield's lower-right edge: click it for a clean screenshot (all interface
-- hidden for a second). Click the icon itself to start or stop a
-- recording; drag it to move it. The dot in the icon is cyan when idle; while WRC
-- is asking for a recording it turns red and the icon pulses.
-- An addon cannot open folders or record by itself: these controls only change
-- what the beacon shows, and the WRC Recorder app acts on it.

local _, ns = ...

local ICON_IDLE = "Interface\\AddOns\\WRC\\round_idle.tga"
local ICON_REC = "Interface\\AddOns\\WRC\\round_rec.tga"
local ICON_SWORD = "Interface\\AddOns\\WRC\\sword.tga"
local SWORD = 24
local SIZE, POP_W, POP_H, GAP = 44, 62, 24, 4
local HIDE_DELAY = 0.8

local round, icon, pulse, popRec, popFolder, shotBtn

local function anyHovered()
    return round:IsMouseOver() or popRec:IsMouseOver() or popFolder:IsMouseOver()
end

local function showPops()
    popRec:Show()
    popFolder:Show()
end

local function hidePopsLater()
    C_Timer.After(HIDE_DELAY, function()
        if not anyHovered() then
            popRec:Hide()
            popFolder:Hide()
        end
    end)
end

local function makePop(text, point, relPoint, x, y, onClick)
    local b = ns.Pill(round, text, POP_W, POP_H, onClick)
    b:SetPoint(point, round, relPoint, x, y)
    b:SetScript("OnEnter", showPops)
    b:SetScript("OnLeave", hidePopsLater)
    b:Hide()
    return b
end

function ns.InitButtons(db)
    if not round then
        round = CreateFrame("Button", "WRCRoundButton", UIParent)
        round:SetSize(SIZE, SIZE)
        round:SetMovable(true)
        round:SetClampedToScreen(true)
        round:RegisterForDrag("LeftButton")
        round:SetScript("OnDragStart", round.StartMoving)
        round:SetScript("OnDragStop", function(self)
            self:StopMovingOrSizing()
            local point, _, relPoint, x, y = self:GetPoint(1)
            db.btnPos = { point, relPoint, x, y }
        end)

        icon = round:CreateTexture(nil, "ARTWORK")
        icon:SetAllPoints(round)
        icon:SetTexture(ICON_IDLE)

        -- Pulse: the icon fades down and back while WRC is asking for a recording.
        pulse = icon:CreateAnimationGroup()
        pulse:SetLooping("BOUNCE")
        local fade = pulse:CreateAnimation("Alpha")
        fade:SetFromAlpha(1)
        fade:SetToAlpha(0.35)
        fade:SetDuration(0.55)
        fade:SetSmoothing("IN_OUT")

        local pos = db.btnPos
        if type(pos) == "table" and pos[1] then
            round:SetPoint(pos[1], UIParent, pos[2], pos[3], pos[4])
        else
            round:SetPoint("TOP", UIParent, "TOP", 0, -60)
        end

        popRec = makePop("REC", "RIGHT", "LEFT", -GAP, 0, function() ns.ToggleManual() end)
        popFolder = makePop("Clips", "LEFT", "RIGHT", GAP, 0, function() ns.ToggleClips() end)

        -- The camera-and-sword: clean screenshot. Always visible next to the shield.
        shotBtn = CreateFrame("Button", "WRCShotButton", round)
        shotBtn:SetSize(SWORD, SWORD)
        shotBtn:SetPoint("CENTER", round, "BOTTOMRIGHT", -4, 4)
        shotBtn:SetFrameLevel((round:GetFrameLevel() or 1) + 2)
        local sw = shotBtn:CreateTexture(nil, "ARTWORK")
        sw:SetAllPoints(shotBtn)
        sw:SetTexture(ICON_SWORD)
        sw:SetAlpha(0.85)
        shotBtn:RegisterForClicks("LeftButtonUp")
        shotBtn:SetScript("OnClick", function() ns.Shot() end)
        shotBtn:SetScript("OnEnter", function(self)
            sw:SetAlpha(1)
            self:SetSize(SWORD + 4, SWORD + 4)
            if GameTooltip then
                GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
                GameTooltip:SetText("Clean screenshot  |cff00c6ffWRC|r")
                GameTooltip:AddLine("Hides all interface for 1 second and takes a screenshot", 1, 1, 1)
                GameTooltip:Show()
            end
        end)
        shotBtn:SetScript("OnLeave", function(self)
            sw:SetAlpha(0.85)
            self:SetSize(SWORD, SWORD)
            if GameTooltip then GameTooltip:Hide() end
        end)

        round:RegisterForClicks("LeftButtonUp", "RightButtonUp")
        round:SetScript("OnClick", function(_, button)
            if button == "RightButton" then
                ns.ToggleSettings()
            else
                ns.ToggleManual()
            end
        end)
        round:SetScript("OnEnter", function(self)
            showPops()
            if GameTooltip then
                GameTooltip:SetOwner(self, "ANCHOR_BOTTOM")
                GameTooltip:SetText("WRC  |cff00c6ffIONITY|r")
                GameTooltip:AddLine("Click: start / stop recording", 1, 1, 1)
                GameTooltip:AddLine("Right-click: settings and keys", 1, 1, 1)
                GameTooltip:AddLine("Camera: screenshot with all interface hidden", 1, 1, 1)
                GameTooltip:AddLine("Drag: move", 1, 1, 1)
                GameTooltip:Show()
            end
        end)
        round:SetScript("OnLeave", function()
            if GameTooltip then GameTooltip:Hide() end
            hidePopsLater()
        end)
    end
    round:SetShown(db.buttons and db.enabled)
end

-- manual    : a recording you started by hand is running (the pop-out reads STOP)
-- signalling: the beacon is asking the recorder to record, for any reason
--             (manual, enemy on screen, attacked while AFK). The icon turns red
--             and pulses. The addon cannot see the recorder, so this shows what
--             it is asking for, not proof that the recorder is running.
function ns.UpdateButtons(manual, signalling)
    if not icon then return end
    popRec:SetText(manual and "STOP" or "REC")
    icon:SetTexture(signalling and ICON_REC or ICON_IDLE)
    if signalling then
        if not pulse:IsPlaying() then pulse:Play() end
    else
        pulse:Stop()
        icon:SetAlpha(1)
    end
end
