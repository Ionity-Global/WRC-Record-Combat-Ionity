-- WRC - WoW Record Combat | Ionity (Pty) Ltd | Author: Johan Wilhelm van Antwerp
-- (c) 2018-2026 Antwerp Designs | Ionity (Pty) Ltd | Policy 986 AED | CC BY-NC-SA 4.0
--
-- The beacon: a strip of solid colour cells drawn in exact physical pixels.
-- Layout in cells (66 wide, 9 tall, 1 cell of black quiet zone all round):
--   col 0        quiet
--   col 1-3      left finder   magenta, cyan, magenta
--   col 4        quiet
--   col 5-12     8 state bits  (white = 1)
--   col 13       quiet
--   col 14-60    8 characters of 5x7 pixel font, 1 column apart
--   col 61       quiet
--   col 62-64    right finder  cyan, magenta, cyan
--   col 65       quiet
-- To the right of that, on the same line (so nothing below is covered):
--   col 66-68    name marker   cyan, magenta, cyan (5 cells tall)
--   col 69       quiet
--   col 70-128   up to 10 letters of the character name, which the recorder
--                puts in the clip's file name
--   col 129      quiet
-- The recorder finds the finders, measures the cell size from them (so any
-- resolution or cell size works) and reads the bits and the word.

local _, ns = ...

local B = {}
ns.Beacon = B

local COLS, ROWS = 130, 9
local STATE_COL, TEXT_COL, CHARS = 5, 14, 8
local NAME_COL, NAME_CHARS = 70, 10

-- No parent on purpose: the beacon stays on screen when the UI is hidden (Alt+Z).
local frame = CreateFrame("Frame", "WRCBeaconFrame", nil)
frame:SetFrameStrata("TOOLTIP")
frame:Show()
B.frame = frame

local function newTex(layer, r, g, b)
    local t = frame:CreateTexture(nil, layer)
    t:SetColorTexture(r, g, b, 1)
    if t.SetSnapToPixelGrid then
        t:SetSnapToPixelGrid(false)
        t:SetTexelSnappingBias(0)
    end
    return t
end

-- Every texture remembers its cell rectangle so Layout() can re-place it.
local placed = {}
local function place(t, col, row, w, h)
    t.wrcCol, t.wrcRow, t.wrcW, t.wrcH = col, row, w, h
    placed[#placed + 1] = t
    return t
end

place(newTex("BACKGROUND", 0, 0, 0), 0, 0, COLS, ROWS)

local M, C = { 1, 0, 1 }, { 0, 1, 1 }
local finder = { [1] = M, [2] = C, [3] = M, [62] = C, [63] = M, [64] = C }
for col, rgb in pairs(finder) do
    place(newTex("ARTWORK", rgb[1], rgb[2], rgb[3]), col, 1, 1, 7)
end

local stateTex = {}
for i = 1, 8 do
    stateTex[i] = place(newTex("ARTWORK", 1, 1, 1), STATE_COL + i - 1, 1, 1, 7)
    stateTex[i]:Hide()
end

local textTex = {}
for ch = 1, CHARS do
    textTex[ch] = {}
    for py = 0, 6 do
        for px = 0, 4 do
            local t = place(newTex("ARTWORK", 1, 1, 1), TEXT_COL + (ch - 1) * 6 + px, 1 + py, 1, 1)
            t:Hide()
            textTex[ch][py * 5 + px + 1] = t
        end
    end
end

for col, rgb in pairs({ [66] = C, [67] = M, [68] = C }) do
    place(newTex("ARTWORK", rgb[1], rgb[2], rgb[3]), col, 2, 1, 5)
end

local nameTex = {}
for ch = 1, NAME_CHARS do
    nameTex[ch] = {}
    for py = 0, 6 do
        for px = 0, 4 do
            local t = place(newTex("ARTWORK", 1, 1, 1), NAME_COL + (ch - 1) * 6 + px, 1 + py, 1, 1)
            t:Hide()
            nameTex[ch][py * 5 + px + 1] = t
        end
    end
end

-- cell: size of one cell in physical pixels. corner: TOPLEFT/TOPRIGHT/BOTTOMLEFT/BOTTOMRIGHT.
-- ox, oy: offset from that corner in physical pixels, always pushing inward.
function B:Layout(cell, corner, ox, oy)
    cell = math.max(2, math.min(12, math.floor(tonumber(cell) or 3)))
    corner = corner or "TOPLEFT"
    ox, oy = math.floor(tonumber(ox) or 0), math.floor(tonumber(oy) or 0)

    -- The UI is always 768 units tall, so this scale makes 1 unit = 1 physical pixel.
    local _, physH = GetPhysicalScreenSize()
    if not physH or physH <= 0 then physH = 768 end
    frame:SetScale(768 / physH)

    frame:SetSize(COLS * cell, ROWS * cell)
    frame:ClearAllPoints()
    local sx = corner:find("RIGHT") and -1 or 1
    local sy = corner:find("TOP") and -1 or 1
    frame:SetPoint(corner, WorldFrame, corner, sx * ox, sy * oy)

    for i = 1, #placed do
        local t = placed[i]
        t:ClearAllPoints()
        t:SetPoint("TOPLEFT", frame, "TOPLEFT", t.wrcCol * cell, -t.wrcRow * cell)
        t:SetSize(t.wrcW * cell, t.wrcH * cell)
    end
end

-- bits: array of 8 booleans.
function B:SetBits(bits)
    for i = 1, 8 do
        stateTex[i]:SetShown(bits[i] and true or false)
    end
end

function B:SetWord(word)
    word = (word or ""):upper()
    for ch = 1, CHARS do
        local glyph = ns.Font[word:sub(ch, ch)] or ns.Font[" "]
        local cells = textTex[ch]
        for i = 1, 35 do
            cells[i]:SetShown(glyph:byte(i) == 49) -- 49 = "1"
        end
    end
end

-- name: letters A-Z only, at most 10 (anything else is dropped by the caller).
function B:SetName(name)
    name = (name or ""):upper()
    for ch = 1, NAME_CHARS do
        local glyph = ns.Font[name:sub(ch, ch)] or ns.Font[" "]
        local cells = nameTex[ch]
        for i = 1, 35 do
            cells[i]:SetShown(glyph:byte(i) == 49)
        end
    end
end

function B:SetShown(shown)
    frame:SetShown(shown)
end
