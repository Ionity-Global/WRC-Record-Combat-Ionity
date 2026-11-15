# WRC tests. Run from the recorder folder:  python -m pytest -q
import os
import shutil
import sys
import time

import numpy as np
import pytest
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "recorder"))

from wrc_recorder import attune, beacon, config, recorder  # noqa: E402
from wrc_recorder.trigger import SPLIT, START, STOP, Trigger, wanted  # noqa: E402

ADDON = os.path.join(ROOT, "addon", "WRC")


def on_screen(img, w=1280, h=720, x=0, y=0, seed=1):
    screen = np.random.default_rng(seed).integers(0, 256, size=(h, w, 3), dtype=np.uint8)
    screen[y:y + img.shape[0], x:x + img.shape[1]] = img
    return screen


# --- beacon reader --------------------------------------------------------
@pytest.mark.parametrize("cell", [2, 3, 4, 5, 8, 12])
@pytest.mark.parametrize("pos", [(0, 0), (37, 91), (1280 - 66 * 12, 720 - 9 * 12)])
def test_reads_beacon_anywhere(cell, pos):
    img = beacon.render(beacon.make_bits(enemy=True, pvp=True, combat=True), "ALLIANCE", cell)
    hit = beacon.locate(on_screen(img, x=pos[0], y=pos[1]))
    assert hit and hit.checksum_ok and hit.word == "ALLIANCE"
    assert hit.enemy and hit.pvp_combat and hit.enemy_faction == "Alliance"
    assert abs(hit.x - pos[0]) < 1.5 and abs(hit.y - pos[1]) < 1.5
    assert abs(hit.cell_w - cell) < 0.1


@pytest.mark.parametrize("factor", [0.75, 1.25, 1.5, 1.77])
def test_reads_blurred_fractional_scaling(factor):
    """Windows display scaling or a resampled game window blurs the cells."""
    img = beacon.render(beacon.make_bits(enemy=True, horde=True), "HORDE", 4)
    pil = Image.fromarray(on_screen(img, 900, 300, 50, 40))
    scaled = np.asarray(pil.resize((int(900 * factor), int(300 * factor)), Image.BILINEAR))
    hit = beacon.locate(scaled)
    assert hit and hit.checksum_ok and hit.word == "HORDE" and hit.enemy_faction == "Horde"


def test_reads_dimmed_colours():
    """Gamma / brightness / night-light shifts must not break the reader."""
    img = beacon.render(beacon.make_bits(enemy=True), "ALLIANCE", 3).astype(np.float32)
    dim = (img * 0.8 + 12).clip(0, 255).astype(np.uint8)
    dim[..., 2] = (dim[..., 2] * 0.85).astype(np.uint8)      # warm tint
    hit = beacon.locate(on_screen(dim, x=10, y=10))
    assert hit and hit.checksum_ok and hit.word == "ALLIANCE"


def test_no_false_positive_on_noise_and_magenta():
    screen = np.random.default_rng(7).integers(0, 256, size=(720, 1280, 3), dtype=np.uint8)
    screen[100:200, 300:320] = (255, 0, 255)          # a lone magenta bar is not a beacon
    assert beacon.locate(screen) is None


def test_reads_real_capture_with_another_overlay_on_top():
    """Captured from Johan's live WoW Forever client: another addon's 4 px colour
    strip covers the top of the beacon and its magenta block touches our finder."""
    img = np.asarray(Image.open(os.path.join(os.path.dirname(__file__), "fixtures",
                                             "live_forever_overlapped.png")).convert("RGB"))
    hit = beacon.locate(img)
    assert hit and hit.checksum_ok and hit.word == "COMBAT"
    assert hit.combat and not hit.enemy and abs(hit.cell_w - 3) < 0.05


def test_reads_beacon_with_magenta_block_touching_from_above_and_left():
    img = beacon.render(beacon.make_bits(enemy=True), "ALLIANCE", 3)
    screen = on_screen(img, x=40, y=40)
    screen[30:43, 30:52] = (229, 0, 229)              # overlaps the quiet zone and touches the finder
    hit = beacon.locate(screen)
    assert hit and hit.checksum_ok and hit.word == "ALLIANCE"


def test_damaged_bits_are_not_trusted():
    bits = beacon.make_bits(enemy=True)
    bits[6] = not bits[6]                              # break the checksum
    hit = beacon.locate(on_screen(beacon.render(bits, "IDLE", 3)))
    assert hit and not hit.checksum_ok
    assert not hit.enemy                               # falls back to the word, which says IDLE


# --- the real addon, run against a mock of the WoW API ---------------------
MOCK = r"""
units, now, combat, instance, phys_h = {}, 100, false, "none", 1440
fontstrings = {}
textures, tickers, printed = {}, {}, {}
local noop = function() end
local function widget()
  local w = setmetatable({ shown = true, points = {} }, { __index = function(_, k) if type(k) == "string" and k:match("^%u") then return noop end end })
  function w:SetText(t) self.text = t end
  function w:GetPoint() return self.point, nil, self.point, self.px, self.py end
  function w:SetFrameStrata() end   function w:Show() self.shown = true end
  function w:Hide() self.shown = false end
  function w:SetShown(s) self.shown = s and true or false end
  function w:SetScale(s) self.scale = s end
  function w:SetSize(a, b) self.w, self.h = a, b end
  function w:ClearAllPoints() self.points = {} end
  function w:SetPoint(p, rel, rp, x, y) self.point, self.px, self.py = p, x or 0, y or 0 end
  function w:SetColorTexture(r, g, b) self.r, self.g, self.b = r, g, b end
  function w:SetSnapToPixelGrid() end   function w:SetTexelSnappingBias() end
  function w:RegisterEvent(e) self.events = self.events or {}; self.events[e] = true end
  function w:SetScript(kind, fn)
    self.scripts = self.scripts or {}; self.scripts[kind] = fn
    if kind == "OnEvent" or kind == "OnClick" then self.handler = fn end end
  function w:IsMouseOver() return hovered[self] == true end
  function w:SetTexture(file) self.file = file end
  function w:CreateAnimationGroup() local g = widget(); g.owner = self; g.playing = false
    function g:CreateAnimation() return widget() end
    function g:Play() self.playing = true end   function g:Stop() self.playing = false end
    function g:IsPlaying() return self.playing end
    self.pulse = g; return g end
  function w:CreateFontString() local f = widget(); fontstrings[#fontstrings+1] = f; return f end
  function w:IsShown() return self.shown end
  function w:CreateTexture(_, layer) local t = widget(); t.layer = layer; t.owner = self; textures[#textures+1] = t; return t end
  return w
end
frames = {}
function CreateFrame(kind, name) local f = widget(); f.kind, f.name = kind, name; frames[#frames+1] = f; return f end
WorldFrame = widget()
UIParent = widget()
function click(text) for _, f in ipairs(frames) do
  if f.kind == "Button" and f.text == text then f.handler(f) return true end end return false end
function button_texts() local t = {} for _, f in ipairs(frames) do
  if f.kind == "Button" then t[#t+1] = f.text end end return table.concat(t, ",") end
function GetPhysicalScreenSize() return phys_h * 16 / 9, phys_h end
function GetTime() return now end
function InCombatLockdown() return combat end
function IsInInstance() return instance ~= "none", instance end
C_Timer = { NewTicker = function(_, fn) tickers[#tickers+1] = fn end,
            After = function(_, fn) if defer_timers then pending[#pending+1] = fn else fn() end end }
pending, defer_timers, shots = {}, false, {}
function run_pending() local p = pending; pending = {}; for _, fn in ipairs(p) do fn() end end
overlay = widget(); overlay.alpha = 1
function overlay:GetAlpha() return self.alpha end
function overlay:SetAlpha(a) self.alpha = a end
function overlay:IsForbidden() return false end
function overlay:IsProtected() return false end
locked = widget(); locked.alpha = 1
function locked:GetAlpha() return self.alpha end
function locked:SetAlpha(a) self.alpha = a end
function locked:IsForbidden() return true end
function WorldFrame:GetChildren() return overlay, locked end
function Screenshot()
  local beaconShown = false
  for _, f in ipairs(frames) do if f.name == "WRCBeaconFrame" then beaconShown = f.shown end end
  shots[#shots+1] = { ui = UIParent.shown, beacon = beaconShown, overlay = overlay.alpha, locked = locked.alpha }
end
GameTooltip = nil
hovered = {}
function click_name(name) for _, f in ipairs(frames) do
  if f.name == name and f.scripts and f.scripts.OnClick then f.scripts.OnClick(f) return true end end return false end
function hover(name_or_text, on) for _, f in ipairs(frames) do
  if f.name == name_or_text or f.text == name_or_text then
    hovered[f] = on or nil
    local s = f.scripts and f.scripts[on and "OnEnter" or "OnLeave"]
    if s then s(f) end return true end end return false end
function shown_buttons() local t = {} for _, f in ipairs(frames) do
  if f.kind == "Button" and f.text and f.shown then t[#t+1] = f.text end end return table.concat(t, ",") end
function pulsing(name) for _, t in ipairs(textures) do
  if t.owner.name == name and t.pulse then return t.pulse.playing end end end
function texture_of(name) for _, t in ipairs(textures) do
  if t.owner.name == name and t.file then return t.file end end end
SlashCmdList = {}
print = function(...) printed[#printed+1] = table.concat({...}, " ") end
local function u(unit) return units[unit] end
function UnitExists(unit) return u(unit) ~= nil end
function UnitIsPlayer(unit) return u(unit) and u(unit).player end
function UnitFactionGroup(unit) return u(unit) and u(unit).faction end
function UnitIsDeadOrGhost(unit) return u(unit) and u(unit).dead end
function UnitCanAttack(a, b) local other = (a == "player") and b or a
  return u(other) and u(other).attackable end
function UnitAffectingCombat() return combat end
function UnitName(unit) return u(unit) and u(unit).name end
function UnitIsAFK(unit) return u(unit) and u(unit).afk end
function UnitIsUnit(a, b) return units[a] ~= nil and units[a] == units[b] end
function UnitClass(unit) return u(unit) and u(unit).class end
function GetRealZoneText() return "Razorfen Kraul" end
date = os.date
function target_player(unit) units[unit .. "target"] = units.player end
bindings, mods, saved_bindings = {}, {}, 0
function GetBindingKey(b) for k, v in pairs(bindings) do if v == b then return k end end end
function SetBinding(k, b) bindings[k] = b return true end
function SaveBindings() saved_bindings = saved_bindings + 1 end
function GetCurrentBindingSet() return 1 end
function IsAltKeyDown() return mods.alt end
function IsControlKeyDown() return mods.ctrl end
function IsShiftKeyDown() return mods.shift end
function key_down(name, key) for _, f in ipairs(frames) do
  if f.name == name then f.scripts.OnKeyDown(f, key) return true end end return false end
function right_click(name) for _, f in ipairs(frames) do
  if f.name == name then f.scripts.OnClick(f, "RightButton") return true end end return false end
function fire(event, ...) for _, f in ipairs(frames) do
  if f.handler and f.events and f.events[event] then f.handler(f, event, ...) end end end
function tick() for _, fn in ipairs(tickers) do fn() end end
"""


class Game:
    """Loads the shipped addon files into Lua and rasterises what it draws."""

    def __init__(self, my_faction="Horde", phys_h=1440, char_name="Azzinoth"):
        from lupa import LuaRuntime
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(MOCK)
        g = self.lua.globals()
        g.phys_h = phys_h
        self.g = g
        self.unit("player", player=True, faction=my_faction, name=char_name)
        ns = self.lua.table()
        toc = open(os.path.join(ADDON, "WRC.toc"), encoding="utf-8").read().splitlines()
        for name in [l.strip() for l in toc if l.strip().endswith(".lua")]:
            src = open(os.path.join(ADDON, name), encoding="utf-8").read()
            chunk = self.lua.eval("function(src, name) return assert(load(src, name)) end")(src, name)
            chunk("WRC", ns)
        g.fire("PLAYER_LOGIN")
        g.fire("PLAYER_ENTERING_WORLD")

    def unit(self, token, **fields):
        self.g.units[token] = self.lua.table(**fields) if fields else None

    def slash(self, text):
        self.g.SlashCmdList["WRC"](text)

    def advance(self, seconds):
        self.g.now = self.g.now + seconds
        self.g.tick()

    def frame_px(self):
        """Rasterise the beacon in physical pixels: returns (image, x, y) on the screen."""
        g = self.g
        frame = g.frames[1]
        scale = frame.scale
        px = lambda v: v * scale * g.phys_h / 768.0          # UI units -> physical pixels
        w, h = round(px(frame.w)), round(px(frame.h))
        img = np.zeros((h, w, 3), dtype=np.uint8)
        layers = {"BACKGROUND": 0, "ARTWORK": 1}
        mine = [t for t in g.textures.values() if t.owner.name == "WRCBeaconFrame" and t.shown]
        for t in sorted(mine, key=lambda t: layers[t.layer]):
            x0, y0 = round(px(t.px)), round(px(-t.py))
            img[y0:y0 + round(px(t.h)), x0:x0 + round(px(t.w))] = (t.r * 255, t.g * 255, t.b * 255)
        return img, frame


def read(game):
    game.g.tick()
    img, _ = game.frame_px()
    return beacon.locate(on_screen(img, x=5, y=5))


@pytest.mark.parametrize("phys_h", [1080, 1440, 2160])
def test_addon_draws_pixel_exact_beacon(phys_h):
    game = Game(phys_h=phys_h)
    img, frame = game.frame_px()
    assert img.shape[:2] == (9 * 3, 130 * 3)                 # 3 physical pixels per cell at any resolution
    hit = read(game)
    assert hit and hit.checksum_ok and hit.word == "IDLE" and not hit.enemy
    assert hit.name == "AZZINOTH" and hit.cols == 130        # character name to the right of the strip


def test_addon_flags_opposite_faction_and_reader_agrees():
    game = Game(my_faction="Horde")
    game.unit("nameplate7", player=True, faction="Alliance", attackable=True)
    hit = read(game)
    assert hit.word == "ALLIANCE" and hit.enemy and not hit.pvp_combat
    game.g.combat = True
    hit = read(game)
    assert hit.enemy and hit.pvp_combat and hit.combat
    game.unit("nameplate7")                                   # enemy gone, fight over
    game.g.combat = False
    game.advance(7)
    hit = read(game)
    assert hit.word == "IDLE" and not hit.enemy


def test_addon_auto_detects_faction_for_alliance_players():
    game = Game(my_faction="Alliance")
    game.unit("target", player=True, faction="Horde", attackable=True)
    hit = read(game)
    assert hit.word == "HORDE" and hit.enemy and hit.enemy_faction == "Horde"


def test_addon_ignores_own_faction_npcs_dead_and_unattackable():
    game = Game(my_faction="Horde")
    game.unit("target", player=True, faction="Horde", attackable=False)
    game.unit("mouseover", player=False, faction="Alliance", attackable=True)     # an NPC guard
    game.unit("focus", player=True, faction="Alliance", attackable=True, dead=True)
    game.unit("nameplate1", player=True, faction="Alliance", attackable=False)    # sanctuary
    assert not read(game).enemy
    game.slash("attackable off")
    assert read(game).enemy                                    # now the unattackable one counts


def test_addon_battleground_combat_counts_without_unit_details():
    game = Game()
    game.g.instance = "pvp"
    game.g.fire("PLAYER_ENTERING_WORLD")
    assert not read(game).enemy
    game.g.combat = True
    hit = read(game)
    assert hit.enemy and hit.pvp_combat and hit.word == "ALLIANCE"


def test_addon_slash_commands_manual_test_size_corner_off():
    game = Game()
    game.slash("rec")
    hit = read(game)
    assert hit.manual and hit.word == "REC"
    game.slash("rec")
    game.slash("test")
    assert read(game).enemy
    game.advance(11)
    assert not read(game).enemy
    game.slash("size 5")
    game.slash("corner br")
    img, frame = game.frame_px()
    assert img.shape[:2] == (45, 650) and frame.point == "BOTTOMRIGHT"
    assert read(game).checksum_ok
    game.slash("off")
    assert game.g.frames[1].shown is False


def test_addon_ingame_buttons_rec_and_folder():
    game = Game()
    assert game.g.button_texts() == "REC,Clips,SHOT"
    assert game.g.click("REC")
    hit = read(game)
    assert hit.manual and hit.word == "REC" and game.g.button_texts() == "STOP,Clips,SHOT"
    assert game.g.click("STOP")
    assert not read(game).manual and game.g.button_texts() == "REC,Clips,SHOT"
    game.slash("folder")
    hit = read(game)
    assert hit.folder and hit.checksum_ok and not hit.enemy and not hit.manual
    game.advance(3)
    assert not read(game).folder                       # the request is a short pulse
    game.slash("buttons")
    holder = [f for f in game.g.frames.values() if f.name == "WRCRoundButton"][0]
    assert holder.shown is False


def test_addon_round_button_popouts_and_icon_state():
    game = Game()
    g = game.g
    assert g.shown_buttons() == ""                      # pop-outs are hidden until you hover
    assert g.hover("WRCRoundButton", True)
    assert g.shown_buttons() == "REC,Clips,SHOT"
    g.hover("WRCRoundButton", False)                    # mouse moves onto a pop-out: they stay
    g.hover("REC", True)
    assert g.shown_buttons() == "REC,Clips,SHOT"
    g.hover("REC", False)                               # mouse leaves everything: they close
    assert g.shown_buttons() == ""
    assert g.texture_of("WRCRoundButton").endswith("round_idle.tga")
    assert g.click_name("WRCRoundButton")               # clicking the round icon records
    assert read(game).manual and g.texture_of("WRCRoundButton").endswith("round_rec.tga")
    assert g.pulsing("WRCRoundButton")                  # pulses while recording
    assert g.click_name("WRCRoundButton")
    assert not read(game).manual and g.texture_of("WRCRoundButton").endswith("round_idle.tga")
    assert not g.pulsing("WRCRoundButton")
    game.unit("target", player=True, faction="Alliance", attackable=True)        # an enemy appears
    assert read(game).enemy and g.pulsing("WRCRoundButton")
    assert g.texture_of("WRCRoundButton").endswith("round_rec.tga") and g.button_texts() == "REC,Clips,SHOT"
    game.unit("target")
    game.advance(1)
    assert not g.pulsing("WRCRoundButton")
    for name in ("round_idle.tga", "round_rec.tga"):
        im = Image.open(os.path.join(ADDON, name))
        assert im.size == (128, 128) and im.mode == "RGBA"
        assert im.getpixel((0, 0))[3] == 0 and im.getpixel((64, 64))[3] == 255     # round: clear corners


def test_addon_clips_panel_lists_clips_and_play_reaches_the_recorder(tmp_path):
    from wrc_recorder import clips
    cfg = config.Config(output_dir=str(tmp_path))
    for i, name in enumerate(["WRC_Alliance_20261114_200000.mp4", "WRC_Manual_20261114_205817.mp4"]):
        (tmp_path / name).write_bytes(b"x" * 1500000)
        os.utime(tmp_path / name, (1794680000 + i * 60, 1794680000 + i * 60))
    addon_copy = tmp_path / "AddOns" / "WRC"
    addon_copy.mkdir(parents=True)
    (addon_copy / "WRC.toc").write_text("x")
    listed = clips.publish(cfg, [str(addon_copy)], {"WRC_Manual_20261114_205817.mp4": 83.4})
    assert [c["name"] for c in listed] == ["WRC_Manual_20261114_205817.mp4", "WRC_Alliance_20261114_200000.mp4"]
    lua_text = (addon_copy / "Clips.lua").read_text()

    game = Game()
    game.lua.execute(lua_text)                          # what WoW does with Clips.lua on /reload
    g = game.g
    assert g.WRC_CLIPS.folder == str(tmp_path) and g.WRC_CLIPS.total == 2
    assert g.WRC_CLIPS[1].secs == 83.4 and g.WRC_CLIPS[1].mb == 1.5
    game.slash("clips")
    assert [f for f in g.frames.values() if f.name == "WRCClipsPanel"][0].shown
    texts = [f.text for f in g.fontstrings.values() if f.text]
    assert any(str(tmp_path) in t for t in texts) and "Manual" in texts and "1:23" in texts
    assert g.click("Play")                              # first row = newest clip
    hit = read(game)
    assert hit.checksum_ok and hit.play_id == listed[0]["id"]
    assert clips.find_by_id(cfg, hit.play_id).endswith("WRC_Manual_20261114_205817.mp4")
    assert clips.find_by_id(cfg, "ZZ") is None
    game.advance(3)
    assert read(game).play_id is None

    again = clips.publish(cfg, [str(addon_copy)])       # ids stay the same between runs
    assert [c["id"] for c in again] == [c["id"] for c in listed]


@pytest.mark.parametrize("raw,expected", [("Azzinoth", "AZZINOTH"), ("Thrallslayerx", "THRALLSLAY"),
                                          ("L\u00e9gol\u00e4s", "LGOLS"), ("", "")])
def test_addon_character_name_variants(raw, expected):
    """Long names are cut to 10 letters; accented letters are dropped (the pixel font is A-Z)."""
    game = Game(char_name=raw)
    hit = read(game)
    assert hit.checksum_ok and hit.name == expected


def test_reader_accepts_old_one_line_beacon_and_reads_name_at_any_size():
    old = beacon.locate(on_screen(beacon.render(beacon.make_bits(), "IDLE", 3), x=20, y=20))
    assert old.checksum_ok and old.name == "" and old.cols == 66
    for cell in (2, 3, 5):
        img = beacon.render(beacon.make_bits(enemy=True), "HORDE", cell, name="Premature")
        hit = beacon.locate(on_screen(img, x=11, y=7))
        assert hit.checksum_ok and hit.word == "HORDE" and hit.name == "PREMATURE"
        assert abs(hit.width - 130 * cell) < 1.5 and abs(hit.height - 9 * cell) < 1


def test_clip_file_name_carries_the_character(tmp_path, monkeypatch):
    seen = {}

    class FakePopen:
        def __init__(self, cmd, **kw): seen["out"] = cmd[-1]
        def poll(self): return None
    monkeypatch.setattr(recorder.subprocess, "Popen", FakePopen)
    rec = recorder.Recorder(plan(), config.Config(output_dir=str(tmp_path)))
    rec.start(recorder.Geometry(0, 0, 1920, 1080), "Alliance", "Azzinoth")
    import re
    assert re.fullmatch(r"WRC_Alliance_Azzinoth_\d{8}_\d{6}\.mp4", os.path.basename(seen["out"]))
    rec.start(recorder.Geometry(0, 0, 1920, 1080), "Manual", "")
    assert re.fullmatch(r"WRC_Manual_\d{8}_\d{6}\.mp4", os.path.basename(seen["out"]))


def test_addon_settings_panel_options_and_key_binding():
    game = Game()
    g = game.g
    assert g.right_click("WRCRoundButton")                      # right-click the round icon
    panel = [f for f in g.frames.values() if f.name == "WRCSettingsPanel"][0]
    assert panel.shown

    assert g.click("Click to set")                              # first key row = Record key
    g.key_down("WRCSettingsPanel", "LCTRL")                     # a modifier alone does nothing
    assert g.bindings["LCTRL"] is None
    g.mods.ctrl, g.mods.alt = True, True
    g.key_down("WRCSettingsPanel", "R")
    assert g.bindings["ALT-CTRL-R"] == "WRC_TOGGLE_REC" and g.saved_bindings == 1
    g.mods.ctrl, g.mods.alt = False, False

    assert g.click("ALT-CTRL-R")                                # rebind: the old key is released
    g.key_down("WRCSettingsPanel", "F9")
    assert g.bindings["F9"] == "WRC_TOGGLE_REC" and g.bindings["ALT-CTRL-R"] is None

    assert g.click("Click to set")                              # Clips key; Esc cancels
    g.key_down("WRCSettingsPanel", "ESCAPE")
    assert g.GetBindingKey("WRC_OPEN_FOLDER") is None

    g.combat = True                                             # no rebinding in combat
    assert g.click("Click to set")
    g.key_down("WRCSettingsPanel", "F10")
    assert g.GetBindingKey("WRC_OPEN_FOLDER") is None
    g.combat = False

    assert g.click("+")                                         # beacon size 3 -> 4, applied at once
    img, _ = game.frame_px()
    assert img.shape[:2] == (9 * 4, 130 * 4) and read(game).checksum_ok
    assert g.click("Top left")                                  # corner cycles
    assert g.frames[1].point == "TOPRIGHT"
    assert g.click("Shown")                                     # hide the round button
    assert [f for f in g.frames.values() if f.name == "WRCRoundButton"][0].shown is False
    game.slash("settings")
    assert panel.shown is False


def test_addon_death_report_dead_word_and_afk_word():
    game = Game()
    g = game.g
    game.unit("nameplate3", player=True, faction="Alliance", attackable=True, name="Stabby", **{"class": "Rogue"})
    game.unit("nameplate5", player=False, attackable=True, name="Raging Agam'ar")
    game.unit("nameplate6", player=True, faction="Alliance", attackable=True, name="Bystander", **{"class": "Mage"})
    g.target_player("nameplate3")
    g.target_player("nameplate5")                       # Bystander is not targeting you
    g.combat = True
    assert read(game).word == "ALLIANCE"
    g.units.player.dead = True
    g.combat = False
    hit = read(game)
    assert hit.dead and hit.checksum_ok
    report = [m for m in g.printed.values() if "you died" in m][-1]
    assert "Razorfen Kraul" in report and "Stabby (Rogue)" in report and "Raging Agam'ar (NPC)" in report
    assert "Bystander" not in report
    assert g.WRC_DB.deaths[1].by == "Raging Agam'ar (NPC), Stabby (Rogue)"
    game.advance(1)
    assert len([m for m in g.printed.values() if "you died" in m]) == 1      # reported once per death
    game.slash("deaths")
    assert "Stabby (Rogue)" in list(g.printed.values())[-1]

    afk = Game()
    afk.g.units.player.afk = True
    assert read(afk).word == "IDLE"                     # AFK alone is nothing
    afk.g.combat = True
    hit = read(afk)
    assert hit.afk and hit.combat and not hit.enemy


def test_addon_only_one_wrc_window_at_a_time():
    game = Game()
    g = game.g
    shown = lambda name: [f for f in g.frames.values() if f.name == name][0].shown
    game.slash("clips")
    game.slash("settings")
    assert shown("WRCSettingsPanel") and not shown("WRCClipsPanel")
    game.slash("clips")
    assert shown("WRCClipsPanel") and not shown("WRCSettingsPanel")


def test_addon_heartbeat_flips():
    game = Game()
    a = read(game).heartbeat
    game.advance(1)
    assert read(game).heartbeat != a


# --- trigger --------------------------------------------------------------
def test_trigger_start_linger_stop_split():
    t = Trigger(start_confirm=2, linger=10, max_clip=60)
    assert t.update(True, 0) is None                 # one reading is not enough
    assert t.update(True, 0.1) == START
    assert t.update(False, 5) is None                # enemy gone, still lingering
    assert t.update(True, 8) is None                 # came back: keep the same clip
    assert t.update(False, 17.9) is None
    assert t.update(False, 18.1) == STOP
    assert t.update(True, 20) is None and t.update(True, 20.1) == START
    assert t.update(True, 81) == SPLIT
    assert t.update(True, 82) is None


def test_finds_addon_copies_under_a_wow_folder(tmp_path):
    from wrc_recorder.winutil import find_addon_dirs
    for client in ("_forever_", "_retail_"):
        d = tmp_path / "World of Warcraft" / client / "Interface" / "AddOns" / "WRC"
        d.mkdir(parents=True)
        (d / "WRC.toc").write_text("x")
    (tmp_path / "World of Warcraft" / "_classic_" / "Interface" / "AddOns").mkdir(parents=True)   # no WRC here
    root = str(tmp_path / "World of Warcraft")
    here = lambda dirs: [d for d in dirs if d.startswith(str(tmp_path))]    # ignore a real install on this PC
    assert len(here(find_addon_dirs([root]))) == 2
    assert len(here(find_addon_dirs([os.path.join(root, "_retail_")]))) == 2   # a client folder works too
    assert here(find_addon_dirs([str(tmp_path / "nowhere"), ""])) == []


def test_hotkey_parsing():
    from wrc_recorder.winutil import parse_hotkey
    assert parse_hotkey("ctrl+alt+r") == (0x3, ord("R"))
    assert parse_hotkey("F9") == (0, 0x78)
    assert parse_hotkey("Shift + Win + 5") == (0xC, ord("5"))
    assert parse_hotkey("ctrl+") is None and parse_hotkey("ctrl+banana") is None and parse_hotkey("") is None


def test_addon_key_binding_functions_exist_and_work():
    game = Game()
    g = game.g
    assert g.BINDING_NAME_WRC_TOGGLE_REC and g.BINDING_HEADER_WRC
    g.WRC_ToggleRecording()
    assert read(game).manual
    g.WRC_ToggleRecording()
    assert not read(game).manual
    g.WRC_OpenFolder()                                  # this key now shows the in-game clips panel
    assert [f for f in g.frames.values() if f.name == "WRCClipsPanel"][0].shown
    xml = open(os.path.join(ADDON, "Bindings.xml"), encoding="utf-8").read()
    assert "WRC_ToggleRecording()" in xml and "WRC_OpenFolder()" in xml


def test_trigger_force_stop_skips_linger():
    t = Trigger(start_confirm=2, linger=10)
    assert t.force_stop() is None
    t.update(True, 0)
    assert t.update(True, 0.1) == START
    assert t.force_stop() == STOP and not t.recording
    assert t.update(False, 0.2) is None


def test_trigger_modes():
    def b(**flags):
        return beacon.locate(on_screen(beacon.render(beacon.make_bits(**flags), "IDLE", 3)))
    seen, fight, pve = b(enemy=True), b(enemy=True, pvp=True, combat=True), b(combat=True)
    assert wanted(seen, "enemy") and wanted(fight, "enemy") and not wanted(pve, "enemy")
    assert not wanted(seen, "pvp_combat") and wanted(fight, "pvp_combat")
    assert wanted(pve, "any_combat") and not wanted(seen, "any_combat")
    assert wanted(b(manual=True), "pvp_combat") and not wanted(None, "enemy")


# --- FFmpeg ---------------------------------------------------------------
FFMPEG = shutil.which("ffmpeg")


def plan(encoder="hevc_nvenc", family="hevc", kind="nvenc", capture="dda_gpu_init", audio=""):
    return attune.Plan(ffmpeg="ffmpeg", encoder=encoder, family=family, kind=kind, capture=capture, audio=audio)


def test_command_gpu_capture_full_monitor():
    cfg = config.Config()
    geom = recorder.Geometry(0, 0, 2560, 1440, output_idx=1, fps=60)
    cmd = recorder.build_command(plan(), cfg, geom, "out.mp4")
    s = " ".join(cmd)
    assert "-init_hw_device d3d11va" in s
    assert "-filter_complex ddagrab=output_idx=1:framerate=60[v] -map [v]" in s and "hwdownload" not in s
    assert "-fps_mode cfr -r 60" in s
    assert "-c:v hevc_nvenc" in s and "-cq 27" in s and "-tag:v hvc1" in s
    assert "-maxrate %d" % cfg.max_bitrate(2560, 1440, 60) in s
    assert cfg.max_bitrate(2560, 1440, 60) < 11_000_000       # small files: under 11 Mbit/s at 1440p60
    assert cmd[-1] == "out.mp4"


def test_command_windowed_crop_audio_and_downscale():
    cfg = config.Config(max_height=1080)
    geom = recorder.Geometry(-2560, 0, 2560, 1440, fps=60, crop_x=101, crop_y=50, crop_w=1921, crop_h=1201)
    cmd = recorder.build_command(plan(audio="Stereo Mix (Realtek)"), cfg, geom, "o.mp4")
    s = " ".join(cmd)
    assert "video_size=1920x1200:offset_x=101:offset_y=50" in s     # odd sizes rounded down to even
    assert "hwdownload,format=bgra,scale=-2:1080" in s              # scaling forces the download path
    assert "audio=Stereo Mix (Realtek)" in s and "-map 0:a" in s and "-c:a aac" in s
    gdi = " ".join(recorder.build_command(plan("libx264", "h264", "cpu", "gdi"), config.Config(), geom, None))
    assert "-f gdigrab" in gdi and "-offset_x -2459" in gdi and "format=yuv420p" in gdi
    assert gdi.endswith("-f null -")


@pytest.mark.skipif(not FFMPEG, reason="ffmpeg not installed")
def test_attune_finds_a_working_encoder():
    cfg = config.Config()
    p = attune.attune(cfg, FFMPEG, capture_test=None)
    opts = attune.encoder_variants(p.kind, p.family, attune.quality_for(cfg, p.family), 8_000_000, 60)[p.variant]
    assert attune.probe_encoder(FFMPEG, p.encoder, opts)
    assert not attune.probe_encoder(FFMPEG, "no_such_encoder", [])


@pytest.mark.skipif(not FFMPEG, reason="ffmpeg not installed")
def test_recorder_writes_playable_clip_and_discards_short_ones(tmp_path, monkeypatch):
    """Real FFmpeg process, with a test pattern standing in for the screen."""
    cfg = config.Config(output_dir=str(tmp_path), min_clip_seconds=1.0)
    p = attune.attune(cfg, FFMPEG, capture_test=None)

    def fake_command(plan_, cfg_, geom, out_path=None, duration=None):
        opts = attune.encoder_variants(plan_.kind, plan_.family, 30, 2_000_000, 30)[plan_.variant]
        return [FFMPEG, "-hide_banner", "-loglevel", "warning", "-y", "-re", "-f", "lavfi", "-i",
                "testsrc2=s=640x360:r=30", "-pix_fmt", "yuv420p", "-c:v", plan_.encoder] + opts + \
               ["-movflags", "+faststart", out_path]
    monkeypatch.setattr(recorder, "build_command", fake_command)

    rec = recorder.Recorder(p, cfg)
    geom = recorder.Geometry(0, 0, 640, 360)
    rec.start(geom, "Alliance")
    time.sleep(2.5)
    assert rec.active
    path, seconds = rec.stop()
    assert path and os.path.basename(path).startswith("WRC_Alliance_") and seconds >= 2
    rec.start(geom, "Manual")
    time.sleep(1.2)
    kept, _ = rec.stop(keep_short=True)                       # a recording you started by hand is kept
    assert kept and os.path.exists(kept)
    os.remove(kept)
    code, _, err = __import__("wrc_recorder.winutil", fromlist=["run"]).run(
        [FFMPEG, "-v", "error", "-i", path, "-f", "null", "-"])
    assert code == 0 and err.strip() == ""                    # file is complete and decodes cleanly

    rec.start(geom, "Alliance")
    time.sleep(0.3)
    assert rec.stop() == (None, 0.0)                          # too short: deleted
    assert [f for f in os.listdir(tmp_path) if f.endswith(".mp4")] == [os.path.basename(path)]


def test_storage_limit_removes_oldest_only(tmp_path):
    cfg = config.Config(output_dir=str(tmp_path), max_storage_gb=0.000003)     # 3 kB
    for i, name in enumerate(["WRC_a.mp4", "WRC_b.mp4", "WRC_c.mp4", "holiday.mp4"]):
        fp = tmp_path / name
        fp.write_bytes(b"x" * 2000)
        os.utime(fp, (1000 + i, 1000 + i))
    recorder.enforce_storage(cfg)
    assert sorted(os.listdir(tmp_path)) == ["WRC_c.mp4", "holiday.mp4"]        # never touches other files


# --- the recorder main loop, with the screen and FFmpeg replaced by fakes --
def run_app(monkeypatch, tmp_path, script, clicks=None, step=1.0, keep_file=False, **settings):
    """script: list of beacon readings (or None), one per tick. clicks: {tick: manual value}.
    Returns the list of events the loop produced."""
    import types
    from wrc_recorder import app as appmod
    events, tick = [], {"n": 0}

    class FakeSct:
        monitors = [{}, {"left": 0, "top": 0, "width": 1920, "height": 1080}]
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setitem(sys.modules, "mss", types.SimpleNamespace(mss=lambda: FakeSct()))

    class FakeTracker:
        def __init__(self, sct): self.lock = None
        def read(self, now):
            i = tick["n"]
            return script[i] if i < len(script) else None
    monkeypatch.setattr(appmod, "BeaconTracker", FakeTracker)
    monkeypatch.setattr(appmod, "open_folder", lambda cfg: events.append("folder"))
    monkeypatch.setattr(appmod, "enforce_storage", lambda cfg: None)
    monkeypatch.setattr(appmod.recorder, "trim_tail",
                        lambda ff, path, secs: events.append("trim:%g" % secs) or True)
    clock = types.SimpleNamespace(time=lambda: 1000.0 + tick["n"] * step, strftime=time.strftime,
                                  localtime=time.localtime)
    monkeypatch.setattr(appmod, "time", clock)                 # one tick = `step` seconds

    class FakeRecorder:
        proc, active, started, label = None, False, 0.0, ""
        def start(self, geom, label, character=""):
            self.proc, self.active, self.label, self.started = object(), True, label, clock.time()
            events.append("start:" + label + (":" + character if character else ""))
        def stop(self, keep_short=False, discard=False, final_label=None):
            self.proc, self.active = None, False
            if discard:
                events.append("discard")
                return None, 0.0
            events.append("stop" + (":" + final_label if final_label and final_label != self.label else ""))
            return os.path.join(str(tmp_path), "WRC_x.mp4") if keep_file else None, 30.0

    cfg = config.Config(output_dir=str(tmp_path), scan_hz=1000, linger_seconds=3600, start_confirm=2)
    for key, value in settings.items():
        setattr(cfg, key, value)
    if keep_file:
        (tmp_path / "WRC_x.mp4").write_bytes(b"x")
    a = appmod.App(cfg)
    a.plan = plan()
    a.recorder = FakeRecorder()
    real_wait = a.stop_event.wait

    def wait(interval):
        tick["n"] += 1
        if clicks and tick["n"] in clicks:
            a.manual = clicks[tick["n"]]
        if tick["n"] >= len(script):
            a.stop_event.set()
        return real_wait(0)
    a.stop_event.wait = wait
    a.run()
    return events


def reading(word="IDLE", **flags):
    return beacon.locate(on_screen(beacon.render(beacon.make_bits(**flags), word, 3)))


def test_app_enemy_starts_clip_named_by_faction(monkeypatch, tmp_path):
    idle, enemy = reading(), reading("ALLIANCE", enemy=True)
    events = run_app(monkeypatch, tmp_path, [idle, enemy, enemy, enemy, idle])
    assert events == ["start:Alliance", "stop"]           # final stop = app shutting down cleanly
    named = beacon.locate(on_screen(beacon.render(beacon.make_bits(enemy=True), "ALLIANCE", 3, name="AZZINOTH")))
    events = run_app(monkeypatch, tmp_path, [named, named, named])
    assert events == ["start:Alliance:Azzinoth", "stop"]


def test_app_window_record_button_works_without_beacon_and_stops_at_once(monkeypatch, tmp_path):
    events = run_app(monkeypatch, tmp_path, [None] * 8, clicks={1: True, 5: False})
    assert events == ["start:Manual", "stop"]


def test_app_ingame_rec_button_and_folder_button(monkeypatch, tmp_path):
    idle, rec, folder = reading(), reading("REC", manual=True), reading("FOLDER")
    events = run_app(monkeypatch, tmp_path, [idle, rec, rec, rec, idle, idle, folder, folder, idle, idle])
    assert events == ["start:Manual", "stop", "folder"]   # stop is immediate; folder opens once per press


def test_app_deathcam_keeps_last_seconds_of_a_fatal_fight(monkeypatch, tmp_path):
    fight, dead = reading("COMBAT", combat=True), reading("DEAD")
    events = run_app(monkeypatch, tmp_path, [reading()] + [fight] * 40 + [dead] * 8 + [reading()] * 3, keep_file=True)
    # the fight rolls on standby; 5 s after the death it is kept as "Death", cut to 20 s before + 5 s after
    assert events == ["start:Combat", "stop:Death", "trim:25"]


def test_app_deathcam_drops_fights_you_survive_and_respects_the_off_switch(monkeypatch, tmp_path):
    fight = reading("COMBAT", combat=True)
    events = run_app(monkeypatch, tmp_path, [fight] * 10 + [reading()] * 6 + [fight] * 5 + [reading()] * 6)
    assert events == ["start:Combat", "discard", "start:Combat", "discard"]       # nothing kept
    assert run_app(monkeypatch, tmp_path, [fight] * 10 + [reading("DEAD")] * 8, deathcam=False) == []


def test_app_afk_attack_is_kept_whole(monkeypatch, tmp_path):
    afk = reading("AFK", combat=True)
    events = run_app(monkeypatch, tmp_path, [reading()] + [afk] * 6, keep_file=True)
    assert events == ["start:Combat", "stop:AFK"]          # standby footage promoted, not restarted
    assert run_app(monkeypatch, tmp_path, [afk] * 6, afk_record=False, deathcam=False) == []


def test_app_pvp_clip_is_marked_when_you_die_in_it(monkeypatch, tmp_path):
    pvp = reading("ALLIANCE", enemy=True, pvp=True, combat=True)
    events = run_app(monkeypatch, tmp_path, [pvp] * 5 + [reading("DEAD")] * 3, keep_file=True)
    assert events == ["start:Combat", "stop:AllianceDeath"]


@pytest.mark.skipif(not FFMPEG, reason="ffmpeg not installed")
def test_trim_tail_keeps_only_the_end(tmp_path):
    src = str(tmp_path / "long.mp4")
    code, _, err = __import__("wrc_recorder.winutil", fromlist=["run"]).run(
        [FFMPEG, "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=30", "-t", "12", "-g", "30",
         "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "ultrafast", src], 60)
    assert code == 0, err
    assert recorder.trim_tail(FFMPEG, src, 4)
    _, _, info = __import__("wrc_recorder.winutil", fromlist=["run"]).run([FFMPEG, "-hide_banner", "-i", src])
    import re
    h, m, sec = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info).groups()
    assert 3.0 <= float(sec) <= 6.0 and not os.path.exists(src + ".trim.mp4")


def test_clean_screenshot_hides_all_interface_then_restores():
    game = Game()
    g = game.g
    game.slash("shot")
    shots = list(g.shots.values())
    assert len(shots) == 1
    shot = shots[0]
    assert shot.ui is False and shot.beacon is False      # UI and WRC strip gone for the picture
    assert shot.overlay == 0                             # nameplates / world overlays faded out
    assert shot.locked == 1                              # forbidden frames are never touched
    assert g.UIParent.shown is True and g.overlay.alpha == 1   # everything back afterwards
    assert any("clean screenshot saved" in p for p in g.printed.values())
    assert read(game) is not None                        # beacon is back and readable


def test_clean_screenshot_in_combat_takes_normal_shot():
    game = Game()
    g = game.g
    g.combat = True
    game.slash("shot")
    shots = list(g.shots.values())
    assert len(shots) == 1 and shots[0].ui is True       # WoW forbids hiding the UI in combat
    assert any("in combat" in p for p in g.printed.values())


def test_clean_screenshot_restores_when_combat_starts():
    game = Game()
    g = game.g
    g.defer_timers = True
    game.slash("shot")
    assert g.UIParent.shown is False
    g.fire("PLAYER_REGEN_DISABLED")                      # combat about to start: UI back at once
    assert g.UIParent.shown is True and g.overlay.alpha == 1
    g.defer_timers = False
    g.run_pending()
    assert len(list(g.shots.values())) == 0
    assert any("cancelled" in p for p in g.printed.values())


def test_shot_popout_and_key_binding():
    game = Game()
    g = game.g
    g.hover("WRCRoundButton", True)
    assert g.click("SHOT")
    assert len(list(g.shots.values())) == 1
    g.WRC_CleanScreenshot()
    assert len(list(g.shots.values())) == 2
    assert "Clean screenshot" in g.BINDING_NAME_WRC_SCREENSHOT


def test_recorder_bridges_short_beacon_gaps():
    from wrc_recorder.app import hold_last
    seen = object()
    f, last, t = hold_last(seen, None, 0.0, 10.0)
    assert f is seen and t == 10.0
    f, last, t = hold_last(None, last, t, 11.2)          # hidden for a clean screenshot
    assert f is seen
    f, last, t = hold_last(None, last, t, 14.0)          # really gone
    assert f is None
