-- WRC - WoW Record Combat | Ionity (Pty) Ltd | Author: Johan Wilhelm van Antwerp
-- (c) 2018-2026 Antwerp Designs | Ionity (Pty) Ltd | Policy 986 AED | CC BY-NC-SA 4.0
--
-- Shared look: Ionity colours and rounded, anti-aliased shapes. rounded.tga is
-- a white rounded square; the client stretches its middle and keeps its corners
-- (nine-slice), so one small texture gives any size a smooth 8 px corner.

local _, ns = ...

ns.CYAN = { 0, 0.776, 1 }
ns.NAVY = { 0.05, 0.11, 0.16 }

local ROUNDED = "Interface\\AddOns\\WRC\\rounded.tga"
local CORNER = 8

-- A rounded, tinted shape filling `parent` (inset by `inset` pixels on every side).
function ns.Rounded(parent, layer, r, g, b, a, inset)
    local t = parent:CreateTexture(nil, layer)
    inset = inset or 0
    t:SetPoint("TOPLEFT", parent, "TOPLEFT", inset, -inset)
    t:SetPoint("BOTTOMRIGHT", parent, "BOTTOMRIGHT", -inset, inset)
    local sliced = t.SetTextureSliceMargins and pcall(function()
        t:SetTexture(ROUNDED)
        t:SetTextureSliceMargins(CORNER, CORNER, CORNER, CORNER)
    end)
    if sliced then
        t:SetVertexColor(r, g, b, a or 1)
    else
        t:SetColorTexture(r, g, b, a or 1)       -- very old client: square corners
    end
    return t
end

-- A rounded pill button: cyan outline, navy fill, soft highlight on hover.
function ns.Pill(parent, label, width, height, onClick)
    local b = CreateFrame("Button", nil, parent)
    b:SetSize(width, height)
    ns.Rounded(b, "BACKGROUND", ns.CYAN[1], ns.CYAN[2], ns.CYAN[3], 1)
    ns.Rounded(b, "BORDER", ns.NAVY[1], ns.NAVY[2], ns.NAVY[3], 1, 1)
    ns.Rounded(b, "HIGHLIGHT", ns.CYAN[1], ns.CYAN[2], ns.CYAN[3], 0.28, 1)
    local fs = b:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    fs:SetPoint("CENTER", b, "CENTER", 0, 0)
    b:SetFontString(fs)
    b:SetText(label)
    b:SetScript("OnClick", onClick)
    return b
end
