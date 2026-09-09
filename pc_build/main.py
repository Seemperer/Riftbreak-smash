"""
RIFTBREAK SMASH — 1v1 arena fighter (Smash-like). See ../docs.md.
PC prototype. Run: pip install pygame ; python main.py

P1 keys: A/D or arrows move, W aim-up, DOWN drop/fast-fall, Space/W/Up jump,
  Z/J/LMB attack (dir=side tilt, up=up tilt, air=air attack),
  X/K hold/release = charged smash, C = neutral special, V = up special (recover),
  S/E = SUPER down special (unique per fighter), Shift = dash (i-frames),
  RMB = SMART (auto counter / dash / heavy), L hold = shield, F ultimate,
  TAB = move list, F11 = fullscreen, Enter = confirm, P/Esc = pause.
Format: 4-stock rounds, 3:00 timer, blast-zone KOs. 18 stages. Online versus on LAN.
"""
import sys
import os
import time
import math
import random
import json
import pygame
import netplay
try:
    import netrelay
except Exception:
    netrelay = None
from fighters import ROSTER, FIGHTERS
from fighters import traits as char_traits

W, H = 960, 540
FPS = 60
STOCKS = 4
MATCH_TIME = 180
def _user_dir():
    if getattr(sys, "frozen", False):
        d = os.path.join(os.path.expanduser("~"), ".riftbreak")
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
        return d
    return os.path.dirname(os.path.abspath(__file__))


SAVE_PATH = os.path.join(_user_dir(), "save.json")


def asset_base():
    """Folder holding the bundled assets dir. PyInstaller onefile unpacks
    data files to sys._MEIPASS; plain Python uses the source tree."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "assets")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

STAGES = [
    # --- 1. EMBER ARENA: volcano duel. Wide main, 2 solid sides, crumbling crown. ---
    {"name": "Ember Arena", "top": (46, 12, 22), "bot": (130, 45, 25),
     "plat": (200, 110, 60), "glow": (255, 140, 60), "deco": "ember", "w": 3000,
     "skin": "obsidian",
     "main": {"x": 600, "w": 1800, "y": 430},
     "plats": [{"x": 880, "w": 170, "y": 320}, {"x": 1950, "w": 170, "y": 320}],
     "breakables": [{"x": 1365, "w": 270, "y": 215, "hp": 3}],
     "lava": [{"x": 1395, "w": 210, "y": 430}]},
    # --- 2. SKY BATTLEFIELD: pure competitive tri-platform. No hazards. ---
    {"name": "Sky Battlefield", "top": (40, 90, 190), "bot": (150, 200, 235),
     "plat": (235, 240, 250), "glow": (140, 220, 255), "deco": "sky", "w": 3200,
     "skin": "marble",
     "main": {"x": 700, "w": 1800, "y": 430},
     "plats": [{"x": 950, "w": 160, "y": 310}, {"x": 1520, "w": 160, "y": 215},
               {"x": 2090, "w": 160, "y": 310}]},
    # --- 3. VOID FINAL: Final-Destination duel. One high perch, endless void. ---
    {"name": "Void Final", "top": (12, 6, 26), "bot": (60, 20, 90),
     "plat": (120, 90, 160), "glow": (200, 120, 255), "deco": "void", "w": 2800,
     "skin": "voidcrystal",
     "main": {"x": 700, "w": 1400, "y": 430},
     "plats": [{"x": 1250, "w": 300, "y": 250}]},
    # --- 4. FUNGAL HOLLOW: bounce-shroom climb. Staircase + 2 pads, fragile cap. ---
    {"name": "Fungal Hollow", "top": (20, 40, 30), "bot": (70, 30, 90),
     "plat": (90, 160, 110), "glow": (170, 255, 150), "deco": "fungus", "w": 3200,
     "skin": "shroom",
     "main": {"x": 700, "w": 1800, "y": 430},
     "plats": [{"x": 850, "w": 150, "y": 335}, {"x": 1180, "w": 150, "y": 265},
               {"x": 1870, "w": 150, "y": 265}],
     "pads": [{"x": 1150, "w": 80, "y": 430, "pad": 780}, {"x": 1970, "w": 80, "y": 430, "pad": 780}],
     "breakables": [{"x": 1525, "w": 150, "y": 195, "hp": 2}]},
    # --- 5. STORM SPIRE: vertical tower siege. Stacked spire plats + tailwind. ---
    {"name": "Storm Spire", "top": (30, 40, 80), "bot": (90, 110, 150),
     "plat": (150, 170, 200), "glow": (255, 240, 150), "deco": "storm", "w": 3400, "wind": 70,
     "skin": "spire",
     "main": {"x": 800, "w": 1800, "y": 430},
     "plats": [{"x": 980, "w": 170, "y": 300}, {"x": 2280, "w": 150, "y": 335},
               {"x": 2280, "w": 150, "y": 115}],
     "breakables": [{"x": 2280, "w": 150, "y": 225, "hp": 3}]},
    # --- 6. TIDE VAULT: sunken low-grav vault. One wide fragile bridge. ---
    {"name": "Tide Vault", "top": (10, 50, 90), "bot": (40, 130, 170),
     "plat": (90, 180, 200), "glow": (120, 230, 255), "deco": "sky", "w": 3000, "gravm": 0.85,
     "skin": "abyss",
     "main": {"x": 600, "w": 1800, "y": 430},
     "plats": [{"x": 800, "w": 150, "y": 340}, {"x": 1950, "w": 150, "y": 340}],
     "breakables": [{"x": 1270, "w": 260, "y": 280, "hp": 4}]},
    # --- 7. IRON FOUNDRY: hazard pit. Molten channel mid, spike rails at the edges. ---
    {"name": "Iron Foundry", "top": (30, 12, 14), "bot": (90, 40, 30),
     "plat": (140, 130, 130), "glow": (255, 170, 80), "deco": "ember", "w": 3200,
     "skin": "foundry",
     "main": {"x": 700, "w": 1800, "y": 430},
     "plats": [{"x": 900, "w": 160, "y": 295}, {"x": 2140, "w": 160, "y": 295}],
     "spikes": [{"x": 1170, "w": 90, "y": 430}, {"x": 1940, "w": 90, "y": 430}],
     "lava": [{"x": 1555, "w": 190, "y": 430}]},
    # --- 8. THORN GARDEN: low skirmish row. Three brush ledges over thorn beds. ---
    {"name": "Thorn Garden", "top": (25, 45, 25), "bot": (60, 90, 60),
     "plat": (110, 150, 90), "glow": (200, 120, 220), "deco": "fungus", "w": 3000,
     "skin": "thorn",
     "main": {"x": 600, "w": 1800, "y": 430},
     "plats": [{"x": 760, "w": 150, "y": 345}, {"x": 1325, "w": 150, "y": 345},
               {"x": 1890, "w": 150, "y": 345}],
     "spikes": [{"x": 990, "w": 90, "y": 430}, {"x": 1430, "w": 90, "y": 430}, {"x": 1830, "w": 90, "y": 430}]},
    # --- 9. GLACIER: slippery summit. Wide frozen tri-platform, fragile peak. ---
    {"name": "Glacier", "top": (150, 190, 230), "bot": (210, 230, 245),
     "plat": (225, 240, 250), "glow": (170, 225, 255), "deco": "sky", "w": 3400, "ice": True,
     "skin": "frost",
     "main": {"x": 800, "w": 1800, "y": 430},
     "plats": [{"x": 1030, "w": 160, "y": 320}, {"x": 2210, "w": 160, "y": 285}],
     "breakables": [{"x": 1570, "w": 160, "y": 205, "hp": 3}]},
    # --- 10. DUNE SEA: headwind crossing. Descending dune steps into the wind. ---
    {"name": "Dune Sea", "top": (150, 110, 60), "bot": (220, 170, 100),
     "plat": (210, 170, 120), "glow": (255, 230, 160), "deco": "storm", "w": 3600, "wind": -60,
     "skin": "sandstone",
     "main": {"x": 900, "w": 1800, "y": 430},
     "plats": [{"x": 1100, "w": 160, "y": 340}, {"x": 1480, "w": 160, "y": 280},
               {"x": 2260, "w": 160, "y": 280}],
     "breakables": [{"x": 1870, "w": 160, "y": 215, "hp": 2}]},
    # --- 11. HOLLOW STAR: orbital low-grav. Wide wings, fragile zenith. ---
    {"name": "Hollow Star", "top": (30, 15, 60), "bot": (90, 50, 130),
     "plat": (150, 120, 190), "glow": (220, 160, 255), "deco": "void", "w": 3000, "gravm": 0.8,
     "skin": "station",
     "main": {"x": 600, "w": 1800, "y": 430},
     "plats": [{"x": 880, "w": 150, "y": 310}, {"x": 1970, "w": 150, "y": 310}],
     "breakables": [{"x": 1425, "w": 150, "y": 220, "hp": 3}]},
    # --- 12. CLOCKWORK: phasing engine room. 1 solid + 1 fragile + 3 ghost gears. ---
    {"name": "Clockwork", "top": (40, 38, 50), "bot": (100, 90, 80),
     "plat": (190, 170, 150), "glow": (255, 210, 130), "deco": "void", "w": 3200,
     "skin": "brass",
     "main": {"x": 700, "w": 1800, "y": 430},
     "plats": [{"x": 850, "w": 170, "y": 300}],
     "phases": [{"x": 1300, "w": 150, "y": 300, "period": 4.0, "off": 0.0},
                {"x": 1750, "w": 150, "y": 220, "period": 4.0, "off": 2.1},
                {"x": 1300, "w": 150, "y": 150, "period": 5.0, "off": 4.2}],
     "breakables": [{"x": 2130, "w": 170, "y": 300, "hp": 3}]},
    # --- 13. MAGMA CORE: triple causeway over twin lava vents. Fragile mid. ---
    {"name": "Magma Core", "top": (60, 8, 10), "bot": (150, 30, 20),
     "plat": (180, 70, 50), "glow": (255, 100, 50), "deco": "ember", "w": 3400,
     "skin": "magmarock",
     "main": {"x": 800, "w": 1800, "y": 430},
     "plats": [{"x": 1080, "w": 160, "y": 280}, {"x": 2160, "w": 160, "y": 280}],
     "spikes": [{"x": 1250, "w": 90, "y": 430}, {"x": 2060, "w": 90, "y": 430}],
     "pads": [{"x": 1660, "w": 80, "y": 430, "pad": 820}],
     "breakables": [{"x": 1620, "w": 160, "y": 280, "hp": 3}],
     "lava": [{"x": 1430, "w": 120, "y": 430}, {"x": 1790, "w": 120, "y": 430}]},
    # --- 14. CLOUD NINE: sky staircase. 3 solid puffs + 2 fragile crowns, pad row. ---
    {"name": "Cloud Nine", "top": (120, 170, 230), "bot": (200, 225, 245),
     "plat": (245, 248, 255), "glow": (255, 255, 220), "deco": "sky", "w": 3600, "wind": 40,
     "skin": "cloud",
     "main": {"x": 900, "w": 1800, "y": 430},
     "plats": [{"x": 1050, "w": 130, "y": 340}, {"x": 1320, "w": 130, "y": 280},
               {"x": 2120, "w": 130, "y": 280}],
     "pads": [{"x": 1300, "w": 80, "y": 430, "pad": 780}, {"x": 1720, "w": 80, "y": 430, "pad": 780},
              {"x": 2140, "w": 80, "y": 430, "pad": 780}],
     "breakables": [{"x": 1585, "w": 130, "y": 220, "hp": 2},
                    {"x": 1855, "w": 130, "y": 220, "hp": 2}]},
    # --- 15. THE RIFT: collapsing apex. Everything hazards on the biggest stage. ---
    {"name": "The Rift", "top": (5, 3, 12), "bot": (40, 10, 50),
     "plat": (90, 60, 120), "glow": (255, 70, 90), "deco": "void", "w": 4200, "gravm": 0.9,
     "skin": "rift",
     "main": {"x": 1200, "w": 1800, "y": 430},
     "plats": [{"x": 1480, "w": 160, "y": 300}, {"x": 2560, "w": 160, "y": 300}],
     "spikes": [{"x": 1550, "w": 90, "y": 430}, {"x": 2260, "w": 90, "y": 430}],
     "breakables": [{"x": 2020, "w": 160, "y": 200, "hp": 3}],
     "lava": [{"x": 1900, "w": 110, "y": 430}]},
    # --- 16. HARBOR TOWN: clean plaza duel. Two stone balconies, no hazards. ---
    {"name": "Harbor Town", "top": (90, 150, 220), "bot": (180, 220, 240),
     "plat": (190, 150, 110), "glow": (255, 220, 150), "deco": "sky", "w": 3000,
     "skin": "harbor",
     "main": {"x": 600, "w": 1800, "y": 430},
     "plats": [{"x": 950, "w": 170, "y": 300}, {"x": 1880, "w": 170, "y": 300}]},
    # --- 17. WORLD TREE: canopy crossing. Solid bough + fragile bloom + bounce bloom. ---
    {"name": "World Tree", "top": (80, 160, 220), "bot": (150, 220, 180),
     "plat": (150, 110, 70), "glow": (150, 255, 150), "deco": "fungus", "w": 3000,
     "skin": "bark",
     "main": {"x": 600, "w": 1800, "y": 430},
     "plats": [{"x": 900, "w": 150, "y": 310}],
     "pads": [{"x": 1460, "w": 80, "y": 430, "pad": 780}],
     "breakables": [{"x": 1950, "w": 150, "y": 310, "hp": 2}]},
    # --- 18. SUNSET KEEP: rooftop duel. Crumbing west parapet, solid east tower. ---
    {"name": "Sunset Keep", "top": (240, 120, 80), "bot": (120, 60, 140),
     "plat": (150, 100, 60), "glow": (255, 150, 90), "deco": "sky", "w": 3000,
     "skin": "keep",
     "main": {"x": 600, "w": 1800, "y": 430},
     "plats": [{"x": 1850, "w": 160, "y": 290}],
     "breakables": [{"x": 990, "w": 160, "y": 290, "hp": 2}]},
]
BLAST = {"l": -60, "r": W + 60, "t": -100, "b": H + 60}

# ---------------- gamepad (8BitDo SN30 etc.) ----------------
# XInput mode recommended: power the SN30 on with Start+X on PC.
PAD_XINPUT = {"jump": 0, "attack": 2, "smash": 1, "nb": 3, "upb": 5, "super": 6,
              "pause": 7, "confirm": 0, "back": 1, "lb": 4, "rb": 5}
PAD_DINPUT = {"jump": 1, "attack": 0, "smash": 2, "nb": 3, "upb": 5, "super": 6,
              "pause": 9, "confirm": 1, "back": 0, "lb": 4, "rb": 5}

# ---------------- UI theme (pro look: deep navy + gold/cyan) ----------------
UI_BG = (9, 11, 22)
UI_PANEL = (17, 22, 38)
UI_PANEL2 = (24, 30, 50)
UI_EDGE = (62, 70, 104)
UI_GOLD = (255, 210, 120)
UI_CYAN = (130, 220, 255)
UI_RED = (255, 110, 110)
UI_GREEN = (120, 235, 150)
UI_TEXT = (240, 242, 250)
UI_DIM = (150, 156, 180)


class Button:
    def __init__(self, label, action, w=250, h=46, sub=None):
        self.label, self.action, self.sub = label, action, sub
        self.rect = pygame.Rect(0, 0, w, h)

    def draw(self, surf, game, x, y, selected, hover):
        self.rect.topleft = (int(x), int(y))
        hot = selected or hover
        if hot:
            game.blit_add(x + self.rect.w / 2, y + self.rect.h / 2, self.rect.h, UI_GOLD, 80)
        base = UI_PANEL2 if hot else UI_PANEL
        pygame.draw.rect(surf, (8, 10, 20), (x + 3, y + 4, self.rect.w, self.rect.h), border_radius=10)
        pygame.draw.rect(surf, base, self.rect, border_radius=10)
        pygame.draw.rect(surf, UI_GOLD if hot else UI_EDGE, self.rect, 2 if hot else 1, border_radius=10)
        if hot:
            pygame.draw.rect(surf, UI_GOLD, (x, y + self.rect.h - 4, self.rect.w, 4), border_radius=2)
        img = game.font(22).render(self.label, True, UI_GOLD if hot else UI_TEXT)
        surf.blit(img, (x + (self.rect.w - img.get_width()) // 2,
                        y + (self.rect.h - img.get_height()) // 2 - (8 if self.sub else 0)))
        if self.sub:
            s2 = game.font(13, mono=True).render(self.sub, True, UI_DIM)
            surf.blit(s2, (x + (self.rect.w - s2.get_width()) // 2, y + self.rect.h - 20))


def clamp(v, a, b):
    return a if v < a else (b if v > b else v)


def ease_out(p):
    p = clamp(p, 0.0, 1.0)
    return 1.0 - (1.0 - p) * (1.0 - p)


def ease_out_back(p):
    p = clamp(p, 0.0, 1.0)
    c = 1.70158
    return 1.0 + (c + 1.0) * (p - 1.0) ** 3 + c * (p - 1.0) ** 2


def mix(c1, c2, k):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * k) for i in range(3))


# ---------------- particles / projectiles / announcements ----------------
class Particle:
    def __init__(self, x, y, vx, vy, life, color, size=4, grav=700, glow=False, grow=0.0, drag=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.max = life, life
        self.color, self.size, self.grav = color, size, grav
        self.glow, self.grow, self.drag = glow, grow, drag

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.grav * dt
        if self.drag:
            k = max(0.0, 1.0 - self.drag * dt)
            self.vx *= k
            self.vy *= k
        if self.grow:
            self.size += self.grow * dt
        self.life -= dt


class Slash:
    """Melee slash-arc fx, drawn as layered fading arcs."""
    def __init__(self, x, y, facing, rng, hi, color, life=0.22, spin=False):
        self.x, self.y, self.facing = x, y, facing
        self.rng, self.hi = rng, hi
        self.color = color
        self.life, self.max = life, life
        self.spin = spin


class Ring:
    """Expanding shockwave ring fx."""
    def __init__(self, x, y, color, vr=520, life=0.5, width=6):
        self.x, self.y, self.color = x, y, color
        self.r, self.vr, self.width = 12, vr, width
        self.life, self.max = life, life

    def update(self, dt):
        self.r += self.vr * dt
        self.life -= dt


class Proj:
    def __init__(self, owner, x, y, vx, dmg, kb, kind, color, size, life=2.2, vy=0.0):
        self.owner, self.x, self.y, self.vx = owner, x, y, vx
        self.dmg, self.kb, self.kind, self.color, self.size = dmg, kb, kind, color, size
        self.life = life
        self.vy = vy
        self.t = 0.0
        self.ret = False
        self.last_hit = {}
        self.trail = []


# ---------------- fighter ----------------
class Fighter:
    def __init__(self, cid, x, y, facing=1):
        self.cid = cid
        self.d = FIGHTERS[cid]
        big = cid in ("bulwark", "null", "tecton")
        self.w, self.h = (38, 62) if big else (30, 52)
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.facing = facing
        self.pct = 0.0
        self.stocks = STOCKS
        self.max_air = self.d.get("air_jumps", 1)
        self.jumps = self.max_air
        self.static = 0
        self.echo = None
        self.on_ground = False
        self.state = "free"
        self.t = 0.0
        self.atk = None
        self.charge = 0.0
        self.charging = False
        self.cd_nb = self.cd_up = self.cd_down = self.cd_dash = 0.0
        self.dash_t = self.iframes = 0.0
        self.shield_hp = 40.0
        self.shield_held = False
        self.shielding = False
        self.invuln = 0.0
        self.helpless = False
        self.counter = 0.0
        self.armor = 0.0
        self.burn = 0.0
        self.slow = 0.0
        self.drop_t = 0.0
        self.move_dir = 0
        self.anim = random.random() * 10
        self.ai = {"plan": "fight", "t": 0.0, "hold": 0.0, "up": False}
        self.max_pct = 0.0
        # --- animation state ---
        self.flash = 0.0
        self.sx, self.sy = 1.0, 1.0
        self.rot = 0.0
        self.tumble = 0.0
        self.streak = 0.0
        self.pop = 0.0
        self.shield_wob = 0.0
        self.skid = 0.0
        self.step_ph = 0.0
        self.step_sign = 1.0
        self.after = []
        self.after_t = 0
        self.spawn_fx = 0.0
        self.was_ground = True
        self.coyote, self.jump_buf = 0.0, 0.0
        self.star_t, self.hammer_t, self.fuse, self.ult = 0.0, 0.0, 0.0, 0.0
        self.spike_cd = 0.0
        self.lava_cd = 0.0
        self.combo, self.combo_t, self.max_combo = 0, 0.0, 0
        self.last_by, self.last_t = None, -99.0

    def rect(self):
        return pygame.Rect(int(self.x - self.w / 2), int(self.y - self.h), self.w, self.h)

    def alive(self):
        return self.stocks > 0 and self.state != "dead"

    def reset_stock(self, x, y, facing):
        self.x, self.y, self.facing = x, y, facing
        self.vx = self.vy = 0.0
        self.pct = 0.0
        self.jumps = self.max_air
        self.static = 0
        self.echo = None
        self.state = "respawn"
        self.t = 0.55
        self.atk, self.charging, self.helpless = None, False, False
        self.charge = 0.0
        self.invuln = 1.4
        self.shield_hp = 40.0
        self.counter = self.armor = self.burn = self.slow = 0.0
        self.coyote, self.jump_buf = 0.0, 0.0
        self.star_t, self.hammer_t, self.fuse, self.ult = 0.0, 0.0, 0.0, 0.0
        self.spike_cd = 0.0
        self.lava_cd = 0.0
        self.combo, self.combo_t = 0, 0.0
        self.last_by, self.last_t = None, -99.0
        self.flash = 0.0
        self.sx, self.sy = 0.6, 1.4
        self.rot, self.tumble, self.streak = 0.0, 0.0, 0.0
        self.pop, self.shield_wob, self.skid = 0.0, 0.0, 0.0
        self.after, self.after_t = [], 0
        self.spawn_fx = 0.5
        self.was_ground = True


def move_data(f, kind):
    p = f.d["power"]
    M = {
        "jab":   dict(dmg=4 * p, kb=150, kbs=4.0, angle=-35, startup=.06, active=.09, recover=.13, rng=48, hi=42),
        "ftilt": dict(dmg=7 * p, kb=250, kbs=4.6, angle=-30, startup=.09, active=.08, recover=.18, rng=58, hi=40),
        "utilt": dict(dmg=6 * p, kb=260, kbs=5.2, angle=-80, startup=.08, active=.09, recover=.18, rng=44, hi=62),
        "nair":  dict(dmg=8 * p, kb=300, kbs=4.8, angle=-35, startup=.07, active=.16, recover=.20, rng=52, hi=52),
        "uair":  dict(dmg=7 * p, kb=280, kbs=5.4, angle=-80, startup=.08, active=.12, recover=.20, rng=48, hi=60),
        "smash": dict(dmg=12 * p, kb=470, kbs=6.4, angle=-32, startup=.12, active=.08, recover=.30, rng=64, hi=46),
        "upb":   dict(dmg=9 * p, kb=330, kbs=4.6, angle=-75, startup=.04, active=.25, recover=.27, rng=54, hi=60),
    }
    return M[kind]


# ---------------- combat ----------------
def attack_hitbox(f, md):
    cx = f.x + f.facing * (f.w / 2 + md["rng"] / 2)
    return pygame.Rect(int(cx - md["rng"] / 2), int(f.y - md["hi"] - 6), int(md["rng"]), int(md["hi"]))


def apply_hit(att, vic, dmg, kb, kbs, angle_deg, game, silent=False, melee=False):
    if vic.invuln > 0 or vic.iframes > 0 or vic.dash_t > 0 or not vic.alive():
        return False
    if vic.state == "respawn":
        return False
    if vic.star_t > 0:
        game.splash_hit(vic.x, vic.y - 30, (255, 240, 150), 4)
        return False
    if melee and att.hammer_t > 0:
        dmg *= 1.4
        kb *= 1.4
    # counters (cinder / glass / leech)
    if vic.counter > 0 and att is not vic:
        kind = vic.d["down"]["kind"]
        vic.counter = 0
        game.m_glitch = 0.35
        if kind == "mirror":
            vic.x = att.x - att.facing * 55
            vic.facing = att.facing
            dmg2, kb2 = 12 * vic.d["power"], 480
            game.splash_hit((att.x + vic.x) / 2, att.y - 50, (200, 150, 255), 16)
            game.float_text("MIRROR!", vic.x, vic.y - 90, (210, 170, 255))
            raw_hit(vic, att, dmg2, kb2, 5.5, -30, game)
        else:
            game.splash_hit(vic.x, vic.y - 40, (255, 150, 60), 18)
            game.float_text("COUNTER!", vic.x, vic.y - 90, (255, 170, 80))
            raw_hit(vic, att, 14 * vic.d["power"], 520, 5.5, -35, game)
        return True
    # shield
    if vic.shielding and att is not vic and (att.x - vic.x) * vic.facing > -8:
        vic.shield_hp -= dmg * 1.1
        vic.shield_wob = 0.3
        vic.vx += (1 if vic.x >= att.x else -1) * 120
        game.splash_hit(vic.x, vic.y - 30, (140, 200, 255), 6)
        if vic.shield_hp <= 0:
            vic.state = "shieldbreak"
            vic.t = 1.6
            vic.shielding = False
            vic.shield_hp = 40.0
            game.float_text("BREAK!", vic.x, vic.y - 90, (255, 80, 80))
            game.m_glitch = 0.4
            game.shake = max(game.shake, 5)
            game.shock(vic.x, vic.y - 30, (140, 200, 255), vr=420, life=0.45, width=5)
        return False
    raw_hit(att, vic, dmg, kb, kbs, angle_deg, game)
    return True


def raw_hit(att, vic, dmg, kb, kbs, angle_deg, game):
    if vic.armor > 0:
        dmg *= 0.6
        kb *= 0.35
    if vic.cid == "bulwark" and vic.state == "charge":
        kb *= 0.3
    if game.fighters and att is game.fighters[0]:
        dmg *= getattr(game, "streak_mult", 1.0)
    if att.cid == "arc" and att.static > 0:
        dmg += 2 * att.static
        if att.static >= 2:
            game.float_text("DISCHARGE!", vic.x, vic.y - 100, (255, 245, 150))
        game.ring(att.x, att.y - 30, (255, 240, 130))
        att.static = 0
    vic.pct += dmg
    vic.max_pct = max(vic.max_pct, vic.pct)
    if not getattr(game, "ult_lock", False):
        att.ult = min(100.0, att.ult + dmg * 1.1)
        vic.ult = min(100.0, vic.ult + dmg * 0.4)
    if att.combo_t > 0:
        att.combo += 1
    else:
        att.combo = 1
    att.combo_t = 1.2
    att.max_combo = max(att.max_combo, att.combo)
    vic.last_by = att
    vic.last_t = game.t_global
    if att.combo in (3, 5, 8, 12):
        game.float_text({3: "TRIPLE!", 5: "RAMPAGE!", 8: "UNSTOPPABLE!", 12: "GODLIKE!"}[att.combo],
                        vic.x, vic.y - 110, (255, 210, 120))
        game.shake = max(game.shake, 6)
    total = (kb + vic.pct * kbs) / vic.d["weight"]
    if total > 1500:
        total = 1500 + (total - 1500) * 0.4
    rad = math.radians(angle_deg)
    s = 1 if vic.x >= att.x else -1
    vic.vx = abs(math.cos(rad)) * total * s
    vic.vy = math.sin(rad) * total
    vic.on_ground = False
    vic.state = "hitstun"
    vic.t = min(1.0, total / 900.0)
    vic.atk, vic.charging, vic.helpless = None, False, False
    vic.shielding = False
    # --- animation triggers ---
    vic.flash = 0.14
    vic.pop = 0.3
    vic.sx, vic.sy = 1.32, 0.68
    vic.rot = 0.0
    vic.tumble = clamp(140.0 + total * 0.32, 0.0, 620.0) * (1.0 if vic.vx >= 0 else -1.0)
    vic.streak = 0.3 if total > 750 else 0.0
    # per-fighter signatures
    if att.cid == "cinder" and dmg >= 8:
        vic.burn = 2.0
    if att.cid == "leech":
        att.pct = max(0.0, att.pct - dmg * 0.3)
    game.hitstop = max(game.hitstop, 0.035 + dmg * 0.004)
    game.shake = max(game.shake, min(10, 3 + dmg * 0.35))
    if total > 900:
        game.shake = max(game.shake, 9)
        game.dust(vic.x, vic.y - 10, 6)
    game.splash_hit((att.x + vic.x) / 2, vic.y - 34, (255, 255, 255), 8 + int(dmg * 0.7))
    game.glowpuff((att.x + vic.x) / 2, vic.y - 34, (255, 255, 255), 5, 300, 0.35, 6)


def start_attack(f, kind, game, charge_mult=1.0):
    md = move_data(f, kind)
    if kind == "smash":
        md = dict(md)
        md["dmg"] *= 1.0 + charge_mult * 0.75
        md["kb"] *= 1.0 + charge_mult * 0.45
    f.state = "attack"
    f.atk = {"kind": kind, "md": md, "t": 0.0, "has_hit": False, "fx": False,
             "dur": md["startup"] + md["active"] + md["recover"]}
    f.t = 0.0


def _exec_jump(f, game, air):
    if air:
        f.jumps -= 1
        f.vy = f.d["djumpv"]
        f.sx, f.sy = 0.85, 1.18
        game.ring(f.x, f.y - 10, f.d["skin"]["glow"])
    else:
        f.vy = f.d["jumpv"]
        f.on_ground = False
        f.coyote = 0.0
        f.sx, f.sy = 0.82, 1.2
        game.dust(f.x, f.y, 5)
    f.jump_buf = 0.0


def do_jump(f, game):
    if f.state in ("attack", "shieldbreak", "respawn", "dead"):
        return
    if f.helpless:
        return
    if f.on_ground or f.coyote > 0:
        _exec_jump(f, game, False)
    elif f.jumps > 0:
        _exec_jump(f, game, True)
    else:
        f.jump_buf = 0.12


def do_attack_ctx(f, game, up=False):
    if f.state not in ("free", "hitstun") or f.helpless or f.shielding:
        return
    if f.state == "hitstun" and f.t > 0.05:
        return
    if not f.on_ground:
        start_attack(f, "uair" if up else "nair", game)
    else:
        if up:
            start_attack(f, "utilt", game)
        elif f.move_dir != 0:
            f.facing = f.move_dir
            start_attack(f, "ftilt", game)
        else:
            start_attack(f, "jab", game)


def do_smash_start(f, game):
    if f.state == "free" and not f.helpless and not f.shielding:
        f.state = "charge"
        f.charging = True
        f.charge = 0.0


def do_smash_release(f, game):
    if f.state == "charge":
        c = min(0.9, f.charge)
        f.charging = False
        start_attack(f, "smash", game, charge_mult=c / 0.9)


def do_nb(f, game, opp=None):
    if f.cd_nb > 0 or f.state not in ("free",) or f.helpless:
        return
    pd = f.d["proj"]
    f.cd_nb = pd["cd"]
    f.state = "special"
    f.t = 0.28
    if pd["kind"] == "meteor" and opp is not None:
        # CINDER: delayed strike marks the foe's ground
        tx = opp.x + random.uniform(-30, 30)
        pr = Proj(f, tx, -30, 0, pd["dmg"] * f.d["power"], 380,
                  pd["kind"], pd["color"], pd["size"], vy=pd["speed"])
        game.projs.append(pr)
        game.float_text("!", tx, 70, (255, 120, 60))
        game.ring(tx, 60, (255, 130, 50))
        return
    px = f.x + f.facing * 26
    game.projs.append(Proj(f, px, f.y - 34, f.facing * pd["speed"],
                           pd["dmg"] * f.d["power"], 200 if pd["kind"] not in ("rock", "meteor") else 330,
                           pd["kind"], pd["color"], pd["size"]))
    game.dust(px, f.y - 34, 4)


def do_upb(f, game):
    if f.cd_up > 0 or f.jumps < 0:
        return
    if f.state not in ("free", "hitstun") or f.helpless:
        if f.state != "hitstun":
            return
    ud = f.d["up"]
    f.cd_up = 0.9
    f.vy = ud["lift"]
    f.vx = (f.move_dir * 260) if f.move_dir != 0 else f.facing * 180
    f.on_ground = False
    f.helpless = True
    f.state = "special"
    f.t = 0.32
    f.atk = {"kind": "upb", "md": move_data(f, "upb"), "t": 0.0,
             "has_hit": False, "fx": False, "dur": 0.4}
    f.rot = 0.0
    game.ring(f.x, f.y - 20, f.d["skin"]["glow"])


def do_downb(f, game, opp):
    if f.cd_down > 0 or f.helpless or f.state not in ("free",):
        return
    kind = f.d["down"]["kind"]
    f.state = "special"
    if kind == "counter":
        f.counter = 0.55
        f.t = 0.55
        f.cd_down = 2.5
    elif kind == "mirror":
        f.counter = 0.55
        f.t = 0.55
        f.cd_down = 3.0
    elif kind == "freeze":
        f.t = 0.35
        f.cd_down = 6.0
        game.ring(f.x, f.y - 26, (150, 225, 255))
        if abs(opp.x - f.x) < 165 and abs(opp.y - f.y) < 130:
            raw_hit(f, opp, 9 * f.d["power"], 300, 4.5, -50, game)
            opp.slow = 2.5
            game.float_text("FROZEN!", opp.x, opp.y - 90, (150, 225, 255))
    elif kind == "teleport":
        f.cd_down = 5.0
        f.t = 0.2
        direc = f.move_dir if f.move_dir != 0 else f.facing
        game.splash_hit(f.x, f.y - 30, (255, 240, 130), 10)
        f.x = max(game.blast["l"] + 20, min(game.blast["r"] - 20, f.x + direc * 230))
        f.iframes = max(f.iframes, 0.3)
        game.splash_hit(f.x, f.y - 30, (255, 240, 130), 12)
        if abs(opp.x - f.x) < 95 and abs(opp.y - f.y) < 110:
            raw_hit(f, opp, 8, 350, 5.0, -30, game)
    elif kind == "armor":
        f.armor = 2.0
        f.t = 0.3
        f.cd_down = 7.0
        game.float_text("STANCE!", f.x, f.y - 90, (255, 190, 90))
    elif kind == "wave":
        f.t = 0.4
        f.cd_down = 6.0
        game.shake = 9
        for dirc in (-1, 1):
            game.projs.append(Proj(f, f.x + dirc * 30, f.y - 16, dirc * 300,
                                   10 * f.d["power"], 420, "wave", (255, 80, 90), 12))
        game.splash_hit(f.x, f.y - 20, (255, 80, 90), 14)
    elif kind == "echo":
        # ECHO: first press sets the marker, second recalls to it
        f.t = 0.25
        f.cd_down = 4.0
        if f.echo is None:
            f.echo = (f.x, f.y)
            game.float_text("ECHO SET", f.x, f.y - 95, (150, 200, 255))
            game.ring(f.x, f.y - 26, (150, 200, 255))
        else:
            ex, ey = f.echo
            f.echo = None
            game.splash_hit(f.x, f.y - 30, (150, 200, 255), 10)
            f.x = max(game.blast["l"] + 20, min(game.blast["r"] - 20, ex))
            f.y = min(ey, STAGES[game.stage_idx]["main"]["y"] - 4)
            f.vx = f.vy = 0.0
            f.iframes = max(f.iframes, 0.25)
            game.splash_hit(f.x, f.y - 30, (150, 200, 255), 12)
            game.float_text("RECALL!", f.x, f.y - 95, (150, 200, 255))
    elif kind == "well":
        # NULL: birth a drifting gravity well that drags the foe, then implodes
        f.t = 0.4
        f.cd_down = 6.0
        dirc = f.move_dir if f.move_dir != 0 else f.facing
        game.projs.append(Proj(f, f.x + dirc * 30, f.y - 60, dirc * 70, 0, 0,
                               "well", (255, 90, 150), 13, life=2.6))
        game.float_text("COLLAPSE!", f.x, f.y - 95, (255, 90, 150))


def do_dash(f, game):
    if f.cd_dash > 0 or f.state not in ("free",) or f.helpless:
        return
    direc = f.move_dir if f.move_dir != 0 else f.facing
    f.facing = direc
    f.cd_dash = 0.34
    f.dash_t = 0.16
    f.iframes = max(f.iframes, 0.12)
    f.vx = direc * 560
    f.after_t = 0
    if f.cid == "arc" and f.static < 3:
        f.static += 1
        game.ring(f.x, f.y - 20, (255, 240, 130))
    if f.on_ground:
        game.dust(f.x, f.y, 6)


def smart_action(f, o, game):
    """RMB smart button: picks the highest-value option for the situation.
    Counter beats aggression > dash beats danger > heavy beats kill-% > chase > dash."""
    if game.phase != "battle" or f.state != "free" or f.helpless:
        return "none"
    dx = o.x - f.x
    dist = abs(dx)
    same_height = abs(o.y - f.y) < 100
    foe_aggro = o.state in ("attack", "charge") or o.charging
    counter_ready = f.cd_down <= 0 and f.d["down"]["kind"] in ("counter", "mirror")
    proj_incoming = False
    for pr in game.projs:
        if pr.owner is o and abs(pr.x - f.x) < 280 and (f.x - pr.x) * pr.vx > 0:
            proj_incoming = True
            break
    if dist < 115 and same_height and foe_aggro and counter_ready:
        do_downb(f, game, o)
        return "counter"
    if proj_incoming or (dist < 115 and same_height and foe_aggro):
        do_dash(f, game)
        return "dash"
    if o.pct > 70 and dist < 95 and same_height:
        start_attack(f, "smash", game, charge_mult=0.35)
        return "smash"
    if dist > 300:
        f.facing = 1 if dx > 0 else -1
        do_dash(f, game)
        return "chase"
    do_dash(f, game)
    return "dash"


DIFFS = [
    {"name": "ROOKIE", "react": 0.50, "aggro": 0.40, "shield": 0.05, "edge": 0.0,
     "recover": 0.45, "punish": 0.0, "dash": 0.08, "zone_nb": 0.05, "downb": 0.008,
     "evade": 0.0, "combo": 0.0, "item": 0.2, "ult_use": 0.25},
    {"name": "FIGHTER", "react": 0.32, "aggro": 0.65, "shield": 0.20, "edge": 0.4,
     "recover": 0.80, "punish": 0.30, "dash": 0.25, "zone_nb": 0.12, "downb": 0.03,
     "evade": 0.3, "combo": 0.4, "item": 0.5, "ult_use": 0.6},
    {"name": "VETERAN", "react": 0.22, "aggro": 0.80, "shield": 0.35, "edge": 0.7,
     "recover": 0.92, "punish": 0.55, "dash": 0.45, "zone_nb": 0.18, "downb": 0.05,
     "evade": 0.6, "combo": 0.7, "item": 0.7, "ult_use": 0.85},
    {"name": "NIGHTMARE", "react": 0.10, "aggro": 0.95, "shield": 0.50, "edge": 1.0,
     "recover": 1.0, "punish": 0.80, "dash": 0.65, "zone_nb": 0.25, "downb": 0.08,
     "evade": 0.9, "combo": 0.95, "item": 0.9, "ult_use": 1.0},
]
ZONERS = tuple(cid for cid in ROSTER if char_traits(cid).get("zoner"))
ZONEDOWN = tuple(cid for cid in ROSTER
                 if char_traits(cid).get("heavy") or FIGHTERS[cid]["down"]["kind"] == "freeze")
HEAVIES = tuple(cid for cid in ROSTER if char_traits(cid).get("heavy"))
DOWN_SHORT = {"counter": "Counter", "mirror": "Mirror punish", "freeze": "Freeze burst",
              "teleport": "Blink", "armor": "Armor stance", "wave": "Shockwave",
              "echo": "Echo recall", "well": "Collapse"}

# ---------------- Smash-style item drops ----------------
DROPS = {
    "star":   {"name": "POWER STAR", "color": (255, 230, 120), "dur": 12,
               "desc": "3s invincible!"},
    "snack":  {"name": "SNACK", "color": (255, 150, 180), "dur": 12,
               "desc": "-30% damage!"},
    "ult":    {"name": "ULT ORB", "color": (150, 220, 255), "dur": 14,
               "desc": "+35 ult charge!"},
    "hammer": {"name": "HAMMER", "color": (255, 170, 80), "dur": 12,
               "desc": "8s +40% melee!"},
    "bolt":   {"name": "HEX BOLT", "color": (200, 140, 255), "dur": 12,
               "desc": "foe +18%!"},
    "slow":   {"name": "FROST CELL", "color": (140, 230, 255), "dur": 12,
               "desc": "foe slowed 3s!"},
    "bomb":   {"name": "FUSE BOMB", "color": (255, 100, 90), "dur": 12,
               "desc": "1.2s fuse... run!"},
}
ULT_NAMES = {
    "cinder": "INFERNO CATACLYSM", "disc": "HALO OF BLADES", "arc": "OVERVOLT",
    "bulwark": "BEDROCK ERUPTION", "glass": "PRISM BREAK", "null": "RIFT COLLAPSE",
    "blink": "TERMINAL VELOCITY", "tecton": "EXTINCTION", "echo": "PARADOX BLOOM",
    "leech": "VENOM BLOOM",
}


def spawn_drop(game):
    plats = game.platforms()
    if random.random() < 0.65 or len(plats) < 2:
        pl = plats[0]
        x = random.uniform(pl["x"] + 80, pl["x"] + pl["w"] - 80)
    else:
        pl = random.choice(plats[1:])
        x = pl["x"] + pl["w"] / 2 + random.uniform(-pl["w"] / 4, pl["w"] / 4)
    kind = random.choice(list(DROPS.keys()))
    game.drops.append({"kind": kind, "x": x, "y": pl["y"], "t": random.random() * 9,
                       "life": DROPS[kind]["dur"]})
    game.ring(x, pl["y"] - 14, DROPS[kind]["color"])


def apply_drop(f, o, d, game):
    kind = d["kind"]
    info = DROPS[kind]
    cx, cy = d["x"], d["y"] - 16
    if kind == "star":
        f.star_t = 3.0
    elif kind == "snack":
        f.pct = max(0.0, f.pct - 30)
        game.glowpuff(cx, cy, (140, 255, 150), 10, 240, 0.5, 7)
    elif kind == "ult":
        f.ult = min(100.0, f.ult + 35)
        game.ring(cx, cy, (150, 220, 255))
    elif kind == "hammer":
        f.hammer_t = 8.0
        game.glowpuff(cx, cy, (255, 180, 90), 10, 260, 0.5, 7)
    elif kind == "bolt":
        o.pct += 18
        o.max_pct = max(o.max_pct, o.pct)
        game.glowpuff(o.x, o.y - 30, (200, 140, 255), 12, 340, 0.5, 7)
        game.shake = max(game.shake, 6)
    elif kind == "slow":
        o.slow = 3.0
        game.ring(o.x, o.y - 26, (140, 230, 255))
    elif kind == "bomb":
        f.fuse = 1.2
    game.float_text(info["name"] + "!", cx, cy - 26, info["color"])
    game.glowpuff(cx, cy, info["color"], 8, 220, 0.4, 6)


def explode_bomb(f, o, game):
    cx, cy = f.x, f.y - 26
    game.glowpuff(cx, cy, (255, 150, 60), 18, 460, 0.6, 9)
    game.splash_hit(cx, cy, (255, 220, 150), 14)
    game.shake = max(game.shake, 10)
    game.hitstop = max(game.hitstop, 0.12)
    game.ult_lock = True
    game.shock(cx, cy, (255, 170, 80), vr=560, life=0.55, width=7)
    for b in game.brk:
        if b["hp"] > 0 and abs(b["x"] + b["w"] / 2 - cx) < 170 and abs(b["y"] - cy) < 150:
            game.damage_brk(b, 3)
    if abs(o.x - f.x) < 150 and abs(o.y - f.y) < 140 and o.alive():
        raw_hit(f, o, 20, 600, 5.5, -40, game)
        game.float_text("BOOM!", o.x, o.y - 100, (255, 150, 60))
    else:
        game.float_text("fizzle...", cx, cy - 40, (180, 180, 190))
    game.ult_lock = False


def fire_ultimate(att, vic, game):
    if att.ult < 100 or att.state == "dead" or att.helpless:
        return False
    if att.state != "free":
        return False
    att.ult = 0.0
    att.invuln = max(att.invuln, 1.0)
    game.ult_lock = True
    game.m_cosmos = 1.4
    game.hitstop = max(game.hitstop, 0.45)
    game.shake = max(game.shake, 10)
    game.ko_flash = max(game.ko_flash, 0.2)
    game.ko_x, game.ko_y = vic.x, vic.y - 30
    game.say(f"{att.d['name'].split()[0]}: {ULT_NAMES[att.cid]}!", "", 1.6, 64, (255, 210, 120))
    game.shock((att.x + vic.x) / 2, (att.y + vic.y) / 2 - 30, (255, 220, 150), vr=600, life=0.6, width=7)
    rng_ok = abs(vic.x - att.x) < 320 and abs(vic.y - att.y) < 260
    c = att.cid
    pw = att.d["power"]
    if c == "cinder":
        game.glowpuff(att.x, att.y - 30, (255, 130, 50), 26, 520, 0.7, 10)
        game.ring(att.x, att.y - 30, (255, 150, 60))
        if rng_ok:
            raw_hit(att, vic, 25 * pw, 700, 5.0, -35, game)
            vic.burn = 3.0
        else:
            game.float_text("DODGED!", vic.x, vic.y - 100, (200, 200, 210))
    elif c == "disc":
        game.glowpuff(att.x, att.y - 30, (140, 220, 255), 22, 460, 0.7, 9)
        game.ring(att.x, att.y - 30, (150, 225, 255))
        for i in range(8):
            a = i / 8 * math.pi * 2
            game.projs.append(Proj(att, att.x, att.y - 30, math.cos(a) * 380,
                                   7 * pw, 320, "needle", (170, 230, 255), 7))
            game.projs[-1].vy = math.sin(a) * 380
    elif c == "arc":
        for _ in range(12):
            game.parts.append(Particle(vic.x + random.uniform(-8, 8), vic.y - random.uniform(0, 90),
                                       0, random.uniform(-500, -200), 0.4, (255, 245, 160), 5,
                                       grav=0, glow=True))
        game.ring(vic.x, vic.y - 30, (255, 240, 130))
        raw_hit(att, vic, 22 * pw, 500, 6.0, -85, game)
        att.static = 3
    elif c == "bulwark":
        att.armor = 2.0
        game.shake = 14
        for dirc in (-1, 1):
            for k in range(3):
                game.projs.append(Proj(att, att.x + dirc * (30 + k * 40), att.y - 16, dirc * (300 + k * 60),
                                       8 * pw, 380, "wave", (255, 140, 80), 11))
        game.glowpuff(att.x, att.y - 20, (255, 150, 80), 16, 420, 0.6, 9)
    elif c == "glass":
        game.glowpuff(att.x, att.y - 30, (200, 160, 255), 22, 460, 0.7, 9)
        game.ring(att.x, att.y - 30, (220, 190, 255))
        for i in range(10):
            a = i / 10 * math.pi * 2 + 0.3
            game.projs.append(Proj(att, att.x, att.y - 30, math.cos(a) * 420,
                                   6 * pw, 300, "needle", (210, 180, 255), 6))
            game.projs[-1].vy = math.sin(a) * 420
        if rng_ok:
            vic.slow = 2.5
    elif c == "null":
        game.shake = 14
        game.glowpuff(att.x, att.y - 40, (255, 90, 120), 26, 520, 0.7, 10)
        for dirc in (-1, 1):
            game.projs.append(Proj(att, att.x + dirc * 30, att.y - 16, dirc * 320,
                                   10 * pw, 420, "wave", (255, 80, 90), 12))
        if rng_ok:
            raw_hit(att, vic, 24 * pw, 700, 5.0, -35, game)
        else:
            game.float_text("DODGED!", vic.x, vic.y - 100, (200, 200, 210))
    elif c == "blink":
        att.x = max(game.blast["l"] + 30, min(game.blast["r"] - 30, vic.x))
        att.y = max(game.blast["t"] + 30, min(game.blast["b"] - 120, vic.y - 170))
        att.vx = att.vy = 0
        game.glowpuff(att.x, att.y - 20, (120, 255, 210), 18, 420, 0.6, 9)
        game.shake = max(game.shake, 12)
        raw_hit(att, vic, 24 * pw, 700, 5.0, -40, game)
    elif c == "tecton":
        game.shake = 14
        game.glowpuff(att.x, att.y - 20, (255, 140, 60), 26, 520, 0.7, 10)
        game.ring(att.x, att.y - 20, (255, 170, 80))
        if rng_ok:
            raw_hit(att, vic, 30 * pw, 750, 5.0, -35, game)
        else:
            game.float_text("DODGED!", vic.x, vic.y - 100, (200, 200, 210))
    elif c == "echo":
        ax, ay = att.x, att.y
        att.x = max(game.blast["l"] + 30, min(game.blast["r"] - 30, vic.x))
        att.y = max(game.blast["t"] + 30, min(game.blast["b"] - 60, vic.y))
        vic.x = max(game.blast["l"] + 30, min(game.blast["r"] - 30, ax))
        vic.y = max(game.blast["t"] + 30, min(game.blast["b"] - 60, ay))
        game.splash_hit(att.x, att.y - 30, (150, 200, 255), 18)
        game.splash_hit(vic.x, vic.y - 30, (150, 200, 255), 18)
        raw_hit(att, vic, 15 * pw, 450, 5.0, -35, game)
    elif c == "leech":
        game.glowpuff(vic.x, vic.y - 30, (170, 255, 120), 22, 420, 0.7, 9)
        raw_hit(att, vic, 18 * pw, 400, 5.0, -35, game)
        vic.burn = 5.0
        vic.slow = 4.0
    for b in game.brk:
        if b["hp"] > 0 and abs(b["x"] + b["w"] / 2 - att.x) < 220 and abs(b["y"] - att.y) < 200:
            game.damage_brk(b, 3)
    game.ult_lock = False
    return True


# ---------------- CPU ----------------
def ai_control(f, o, stage, game, dt):
    ai = f.ai
    ai["t"] -= dt
    ai["hold"] -= dt
    ai["atk_cd"] = max(0.0, ai.get("atk_cd", 0.0) - dt)
    D = DIFFS[getattr(f, "ai_lv", game.ai_level)]
    main = stage["main"]
    # offstage? (low levels sometimes botch the recovery)
    off = (f.x < main["x"] - 30 or f.x > main["x"] + main["w"] + 30 or f.y > main["y"] + 40)
    if off:
        cx = main["x"] + main["w"] / 2
        f.move_dir = 1 if cx > f.x else -1
        f.facing = f.move_dir
        f.shield_held = False
        if f.cid == "echo" and f.echo is not None and f.cd_down <= 0 and random.random() < D["recover"]:
            do_downb(f, game, o)
            return
        if random.random() < D["recover"]:
            if f.jumps > 0 and (f.y > main["y"] - 10 or f.vy > 200):
                do_jump(f, game)
            elif f.cd_up <= 0.1 and (f.jumps == 0 or f.y > main["y"] + 120):
                if abs(f.x - cx) < 420:
                    do_upb(f, game)
        return
    dx = o.x - f.x
    dist = abs(dx)
    dy = o.y - f.y
    if ai["t"] <= 0:
        ai["t"] = D["react"]
        r = random.random()
        o_charging = (o.state == "charge")
        if o_charging and dist < 220 and r < D["shield"]:
            ai["plan"] = "shield"
            ai["hold"] = 0.55
        elif dist > 430:
            ai["plan"] = "zone" if r < 0.55 else "approach"
        elif dist > 150:
            ai["plan"] = "approach" if r < 0.35 + 0.45 * D["aggro"] else "zone"
        else:
            ai["plan"] = "fight"
        ai["up"] = dy < -70
        # edgeguard: foe offstage while I am safe
        o_off = (o.x < main["x"] - 20 or o.x > main["x"] + main["w"] + 20 or o.y > main["y"] + 60)
        if o_off and random.random() < D["edge"]:
            ai["plan"] = "edge"
    plan = ai["plan"]
    if plan == "shield":
        f.move_dir = 0
        f.shield_held = ai["hold"] > 0
        if ai["hold"] <= 0:
            ai["plan"] = "fight"
        return
    f.shield_held = False
    # hazard watch: hop spikes/lava ahead (all plans, uses last frame's heading)
    if f.on_ground and f.state == "free" and f.move_dir != 0:
        nx = f.x + f.move_dir * 60
        for hz in stage.get("spikes", []) + stage.get("lava", []):
            if hz["x"] - 10 <= nx <= hz["x"] + hz["w"] + 10 and random.random() < 0.4 + D["aggro"] * 0.5:
                do_jump(f, game)
                break
    if plan == "edge":
        ex = main["x"] + 40 if f.x < main["x"] + main["w"] / 2 else main["x"] + main["w"] - 40
        f.move_dir = 1 if ex > f.x else (-1 if ex < f.x - 8 else 0)
        if abs(o.x - f.x) < 170 and -140 < dy < 60 and f.cd_down <= 0 and random.random() < D["downb"]:
            do_downb(f, game, o)
        elif dist < 160 and o.y < main["y"] + 80 and o.vy < 60 and random.random() < 0.04 + 0.06 * D["edge"]:
            do_smash_start(f, game)
        if f.state == "charge":
            f.charge += dt
            if f.charge > 0.5 or dist > 200:
                do_smash_release(f, game)
        return
    if plan == "zone":
        f.move_dir = 0 if dist < 380 else (1 if dx > 0 else -1)
        if dx != 0:
            f.facing = 1 if dx > 0 else -1
        if f.cd_nb <= 0 and random.random() < D["zone_nb"]:
            do_nb(f, game, o)
        elif f.cd_down <= 0 and f.cid in ZONEDOWN and random.random() < D["downb"]:
            do_downb(f, game, o)
        elif random.random() < 0.04:
            ai["plan"] = "approach"
        return
    if plan == "approach":
        f.move_dir = 1 if dx > 8 else (-1 if dx < -8 else 0)
        if f.move_dir:
            f.facing = f.move_dir
        # respect: don't walk into an active attack — shield or back off
        if o.state == "attack" and dist < 130 and random.random() < D["shield"] + 0.3:
            if random.random() < 0.5:
                f.move_dir = 0
                f.shield_held = True
                ai["hold"] = 0.0
                ai["plan"] = "shield"
                return
            f.move_dir = -1 if dx > 0 else 1
            f.facing = 1 if dx > 0 else -1
            return
        # item greed: detour to nearby drops
        if game.drops and random.random() < D["item"]:
            nd = min(game.drops, key=lambda d: abs(d["x"] - f.x))
            if abs(nd["x"] - f.x) < 280:
                f.move_dir = 1 if nd["x"] > f.x else -1
                f.facing = f.move_dir
                return
        if f.on_ground and dy > 130:
            # drop through float plat to chase
            f.drop_t = 0.25
            f.y += 3
        if dy < -110 and f.on_ground and random.random() < 0.15:
            do_jump(f, game)
        if dist < 300 and f.cd_nb <= 0 and f.cid in ZONERS and random.random() < D["zone_nb"] * 0.5:
            do_nb(f, game, o)
        if dist < 260 and random.random() < D["dash"] * 0.1:
            do_dash(f, game)
        if dist < 320 and f.on_ground and random.random() < 0.02 + D["aggro"] * 0.05:
            do_jump(f, game)
        if dist <= 150:
            ai["plan"] = "fight"
        return
    # fight
    f.move_dir = 1 if dx > 30 else (-1 if dx < -30 else 0)
    if f.move_dir:
        f.facing = 1 if dx > 0 else -1
    r = random.random()
    if f.state == "charge":
        f.charge += dt
        if f.charge > 0.45 + (0.3 if f.cid in HEAVIES else 0):
            do_smash_release(f, game)
        return
    if f.state != "free":
        return
    # combo: keep swinging while MY victim is stunned nearby
    if o.state == "hitstun" and getattr(o, "last_by", None) is f and dist < 210 \
            and random.random() < D["combo"]:
        do_attack_ctx(f, game, up=ai["up"] or dy < -70)
        return
    # whiff punish: foe stuck in attack recovery
    if o.state == "attack" and o.atk and \
            o.atk["t"] > o.atk["md"]["startup"] + o.atk["md"]["active"] and dist < 140 and \
            random.random() < 0.05 + D["punish"]:
        do_attack_ctx(f, game, up=ai["up"] or dy < -70)
        return
    # evade: dash through incoming projectiles
    for pr in game.projs:
        if pr.owner is o and abs(pr.x - f.x) < 230 and (f.x - pr.x) * pr.vx > 0:
            if random.random() < D["evade"]:
                do_dash(f, game)
            return
    # ultimate: fire when charged (rookies waste it at bad range)
    if f.ult >= 100 and random.random() < D["ult_use"] * (0.5 if dist > 320 else 1.0):
        if fire_ultimate(f, o, game):
            return
    # character-specific fight brains
    if f.cid == "glass" and (o.state == "attack" or o.dash_t > 0) and dist < 150 \
            and f.cd_down <= 0 and random.random() < 0.3 + D["punish"]:
        do_downb(f, game, o)
        return
    if f.cid == "tecton" and dy > 140 and dist < 130 and not f.on_ground:
        f.vy = min(f.d["maxfall"], f.vy + 500)
    if f.cid == "arc" and dist > 200 and random.random() < D["dash"]:
        f.move_dir = 1 if dx > 0 else -1
        f.facing = f.move_dir
        do_dash(f, game)
        return
    if f.cid == "echo" and f.echo is None and f.cd_down <= 0 \
            and random.random() < 0.02 + D["aggro"] * 0.02:
        do_downb(f, game, o)
        return
    # punish charged smashes with a counter (counter characters, high levels)
    if o.state == "charge" and dist < 170 and f.cd_down <= 0 and \
            f.d["down"]["kind"] in ("counter", "mirror") and random.random() < D["punish"]:
        do_downb(f, game, o)
        return
    # neutral pacing: no machine-gun buttons (shorter gap at high level)
    if ai.get("atk_cd", 0) > 0:
        return
    a_atk = 0.05 + 0.08 * D["aggro"]
    a_smash = a_atk + 0.02 + 0.04 * D["aggro"]
    a_down = a_smash + (0.025 if f.cd_down <= 0 else 0)
    a_nb = a_down + (0.025 if f.cd_nb <= 0 and dist > 130 else 0)
    a_dash = a_nb + D["dash"] * 0.05
    if r < a_atk:
        do_attack_ctx(f, game, up=ai["up"] or dy < -70)
        ai["atk_cd"] = 0.55 - 0.40 * D["aggro"]
    elif r < a_smash and dist < 230:
        do_smash_start(f, game)
        ai["atk_cd"] = 0.55 - 0.40 * D["aggro"]
    elif r < a_smash:
        pass
    elif r < a_down:
        do_downb(f, game, o)
        ai["atk_cd"] = 0.55 - 0.40 * D["aggro"]
    elif r < a_nb:
        do_nb(f, game, o)
        ai["atk_cd"] = 0.55 - 0.40 * D["aggro"]
    elif r < a_dash:
        # gap-close dash only — never dash point-blank into an active attack
        if dist > 170 or o.state != "attack":
            do_dash(f, game)
            ai["atk_cd"] = max(ai.get("atk_cd", 0), 0.25)


# ---------------- game ----------------
class Game:
    def __init__(self, fullscreen=True):
        pygame.init()
        pygame.display.set_caption("RIFTBREAK SMASH — 1v1 arena prototype")
        self.fullscreen = fullscreen
        self._apply_screen()
        self.clock = pygame.time.Clock()
        self.f_big = pygame.font.SysFont("arialblack", 84, bold=True)
        self.f_med = pygame.font.SysFont("arialblack", 40, bold=True)
        self.f_pct = pygame.font.SysFont("arialblack", 58, bold=True)
        self.f = pygame.font.SysFont("consolas", 18)
        self.f_small = pygame.font.SysFont("consolas", 14)
        self.state = "title"
        self.p1cid, self.cpucid, self.stage_idx = "cinder", "disc", 0
        self.ai_level = 1
        self.show_moves = False
        self.cam = 0.0
        self.blast = {"l": -60, "r": W + 60, "t": -100, "b": H + 60}
        self.m_glitch = self.m_cosmos = self.m_solar = 0.0
        self._chaos_on = False
        self.sel = {"row": 0, "col": 0, "lock": False, "stage": 0,
                    "srow": 0, "scol": 0}
        self.fighters = []
        self.projs, self.parts, self.texts, self.slashes = [], [], [], []
        self.rings = []
        self.drops, self.drop_t = [], 5.0
        self.ult_lock = False
        self.cam_shake = 0.0
        self.shake = 0.0
        self.hitstop = 0.0
        self.ko_flash = 0.0
        self.ko_x, self.ko_y = W // 2, H // 2
        self.glow_layer = pygame.Surface((W, H), pygame.SRCALPHA)
        self.vignette = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(5):
            pygame.draw.rect(self.vignette, (0, 0, 10, 30 - i * 6), (0, 0, W, H), 40 + i * 30)
        self._glowc = {}
        self.phase = "countdown"
        self.phase_t = 0.0
        self.timer = MATCH_TIME
        self.sudden = False
        self.announce = None
        self.winner = None
        self.save = self.load_save()
        self.t_global = 0.0
        self.demo = [Fighter("cinder", 330, 430, 1), Fighter("glass", 630, 430, -1)]
        # --- UI state ---
        self.menu_idx = 0
        self.paused_idx = 0
        self.go_idx = 0
        self.state_t = 0.0
        self.fade = 0.0
        self.quit_req = False
        self._fonts = {}
        self.title_buttons, self.pause_buttons, self.go_buttons = [], [], []
        self.sel_cards, self.stage_cards = [], []
        self.online_buttons = []
        self.gpick_cards = []
        self.prev_p1 = Fighter("cinder", 0, 0, 1)
        self.prev_cpu = Fighter("disc", 0, 0, -1)
        # --- gamepad ---
        self.pad_joy = None
        self.pad_name = ""
        self.pad_prof = PAD_XINPUT
        self.pad_lb_t = None
        self.pad_swallow_lb = False
        self.pad_test = None
        self.pad_last = "—"
        self._pad_scan = 0.0
        self.pad_refresh()
        self.sprites = self.load_sprites()
        self.stage_art = self.load_stage_art()
        # --- online play (host-authoritative; see netplay.py) ---
        self.net_role = None
        self.net_peer = None
        self.net_listen = None
        self.net_guest_cid = None
        self.net_inputs = {"move": 0, "shield": False, "acts": []}
        self.net_events = []
        self.net_sq = 0
        self.net_frame = 0
        self.net_last_rx = 0.0
        self.net_local_ip = ""
        self.net_link = None
        self.net_room = ""
        self.net_outbox = []
        self.net_in_sq = 0
        self.net_heard_guest = False
        self.ip_buf = ""
        self.ip_err = ""
        self.ip_mode = "ip"
        self.gpick_idx = 0
        self.online_buttons = []
        self.gpick_cards = []

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self._apply_screen()

    def _apply_screen(self):
        flags = pygame.FULLSCREEN | pygame.SCALED if self.fullscreen else 0
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            self.fullscreen = False
            self.screen = pygame.display.set_mode((W, H))

    # ---- UI helpers ----
    def glow_surf(self, color, r):
        key = (color, max(4, int(r // 4) * 4))
        s = self._glowc.get(key)
        if s is None:
            rr = key[1]
            sz = rr * 2 + 2
            s = pygame.Surface((sz, sz), pygame.SRCALPHA)
            for k in range(rr, 0, -4):
                al = int(150 * (1 - k / rr) ** 1.6)
                pygame.draw.circle(s, (*color, al), (rr + 1, rr + 1), k)
            self._glowc[key] = s
        return s

    def blit_add(self, x, y, r, color, alpha=160):
        s = self.glow_surf(color, r).copy()
        s.set_alpha(max(0, min(255, int(alpha))))
        self.screen.blit(s, (int(x - s.get_width() // 2), int(y - s.get_height() // 2)),
                         special_flags=pygame.BLEND_ADD)

    def shock(self, x, y, color, vr=520, life=0.5, width=6):
        if len(self.rings) < 24:
            self.rings.append(Ring(x, y, color, vr, life, width))

    def font(self, size, bold=True, mono=False):
        key = (size, bold, mono)
        f = self._fonts.get(key)
        if f is None:
            f = pygame.font.SysFont("consolas", size, bold=bold) if mono else \
                pygame.font.SysFont("segoeui,arial", size, bold=bold)
            self._fonts[key] = f
        return f

    def ctext(self, s, cx, y, size, color, bold=True, mono=False, alpha=255):
        img = self.font(size, bold, mono).render(s, True, color)
        if alpha < 255:
            img.set_alpha(alpha)
        self.screen.blit(img, (int(cx - img.get_width() // 2), int(y)))
        return img.get_height()

    def text(self, s, x, y, size, color, bold=True, mono=False, alpha=255):
        img = self.font(size, bold, mono).render(s, True, color)
        if alpha < 255:
            img.set_alpha(alpha)
        self.screen.blit(img, (int(x), int(y)))
        return img.get_width()

    def panel(self, x, y, w, h, accent=None, alpha=222, radius=12):
        bg = pygame.Surface((int(w), int(h)), pygame.SRCALPHA)
        bg.fill((UI_PANEL[0], UI_PANEL[1], UI_PANEL[2], alpha))
        hi = pygame.Surface((int(w), max(1, int(h) // 2)), pygame.SRCALPHA)
        hi.fill((255, 255, 255, 13))
        bg.blit(hi, (0, 0))
        self.screen.blit(bg, (int(x), int(y)))
        pygame.draw.rect(self.screen, UI_EDGE, (int(x), int(y), int(w), int(h)), 1, border_radius=radius)
        if accent:
            pygame.draw.rect(self.screen, accent, (int(x), int(y), int(w), 4), border_radius=2)

    def fit_text(self, s, size, maxw, mono=False):
        if self.font(size, mono=mono).size(s)[0] <= maxw:
            return s
        while s and self.font(size, mono=mono).size(s + "...")[0] > maxw:
            s = s.rsplit(" ", 1)[0]
        return s + "..."

    def refresh_previews(self):
        self.prev_p1 = Fighter(self.p1cid, 0, 0, 1)
        self.prev_cpu = Fighter(self.cpucid, 0, 0, -1)
        for f in (self.prev_p1, self.prev_cpu):
            f.on_ground = True
            f.anim = self.t_global

    def goto_select(self):
        self.state = "select"
        self.sel = {"row": 0, "col": 0, "lock": False, "stage": self.stage_idx,
                    "srow": (self.stage_idx // 5) % ((len(STAGES) + 4) // 5), "scol": self.stage_idx % 5}
        if self.cpucid == self.p1cid:
            self.cpucid = random.choice([c for c in ROSTER if c != self.p1cid])
        self.refresh_previews()

    def sync_stage_cursor(self, s):
        rows = (len(STAGES) + 4) // 5
        s["srow"] = s.get("srow", 0) % rows
        if s["srow"] * 5 + s.get("scol", 0) >= len(STAGES):
            s["scol"] = (len(STAGES) - 1) % 5
        s["stage"] = s["srow"] * 5 + s["scol"]

    def load_save(self):
        try:
            with open(SAVE_PATH) as fh:
                data = json.load(fh)
            if not isinstance(data.get("wins"), dict):
                data = {"wins": {}, "games": 0}
            data.setdefault("wins", {})
            data.setdefault("games", 0)
            data.setdefault("streak", 0)
            data.setdefault("best_streak", 0)
            return data
        except Exception:
            return {"wins": {}, "games": 0, "streak": 0, "best_streak": 0}

    def store_save(self):
        try:
            with open(SAVE_PATH, "w") as fh:
                json.dump(self.save, fh)
        except Exception:
            pass

    # fx helpers
    def dust(self, x, y, n):
        for _ in range(n):
            self.parts.append(Particle(x + random.uniform(-12, 12), y - 2,
                                       random.uniform(-140, 140), random.uniform(-220, -30),
                                       random.uniform(0.25, 0.55), (200, 200, 210), 3, grav=500))

    def ring(self, x, y, color):
        for i in range(10):
            a = i / 10 * math.pi * 2
            self.parts.append(Particle(x, y, math.cos(a) * 220, math.sin(a) * 220,
                                       0.35, color, 4, grav=0))

    def splash_hit(self, x, y, color, n):
        for _ in range(n):
            a = random.uniform(0, math.pi * 2)
            sp = random.uniform(120, 520)
            self.parts.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp,
                                       random.uniform(0.2, 0.5), color, random.randint(3, 6), grav=200))

    def glowpuff(self, x, y, color, n=8, spd=260, life=0.45, size=7):
        for _ in range(n):
            a = random.uniform(0, math.pi * 2)
            sp = random.uniform(spd * 0.3, spd)
            self.parts.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp,
                                       random.uniform(life * 0.6, life), color,
                                       random.randint(max(2, size - 3), size + 2),
                                       grav=60, glow=True, drag=3.0))

    def smoke(self, x, y, n=6, color=(200, 200, 210), spd=120, life=0.6, size=6):
        for _ in range(n):
            self.parts.append(Particle(x + random.uniform(-10, 10), y + random.uniform(-6, 2),
                                       random.uniform(-spd, spd), random.uniform(-spd * 1.4, -20),
                                       random.uniform(life * 0.6, life), color,
                                       random.randint(max(2, size - 2), size + 2),
                                       grav=-160, grow=size * 1.6, drag=2.0))

    def spawn_slash(self, f, md, big=False, spin=False):
        if len(self.slashes) > 40:
            self.slashes.pop(0)
        hb = attack_hitbox(f, md)
        self.slashes.append(Slash(hb.centerx, hb.centery, f.facing,
                                  md["rng"] * (1.4 if big else 1.1), md["hi"] + 8,
                                  f.d["skin"]["glow"], life=0.28 if big else 0.2, spin=spin))
        if big:
            self.glowpuff(hb.centerx, hb.centery, (255, 255, 255), 6, 320, 0.3, 5)

    def update_fx(self, dt, rate=1.0):
        for pt in list(self.parts):
            pt.update(dt * rate)
            if pt.life <= 0:
                self.parts.remove(pt)
        if len(self.parts) > 260:
            self.parts = self.parts[-260:]
        for sl in list(self.slashes):
            sl.life -= dt * rate
            if sl.life <= 0:
                self.slashes.remove(sl)
        for rg in list(self.rings):
            rg.update(dt * rate)
            if rg.life <= 0:
                self.rings.remove(rg)
        for t in list(self.texts):
            t["life"] -= dt * rate
            t["y"] -= 34 * dt * rate
            if t["life"] <= 0:
                self.texts.remove(t)
        if self.ko_flash > 0:
            self.ko_flash = max(0.0, self.ko_flash - dt)
        for k in ("m_glitch", "m_cosmos", "m_solar"):
            v = getattr(self, k, 0)
            if v > 0:
                setattr(self, k, max(0.0, v - dt * rate))

    def float_text(self, s, x, y, color):
        self.texts.append({"s": s, "x": x, "y": y, "color": color, "life": 1.1})
        if self.net_is_host() and self.net_peer is not None and len(self.net_events) < 12:
            try:
                self.net_events.append({"s": str(s)[:24], "x": round(float(x), 1),
                                        "y": round(float(y), 1), "color": list(color)})
            except Exception:
                pass

    def say(self, text, sub="", dur=1.4, size=84, color=(255, 255, 255)):
        self.announce = {"text": text, "sub": sub, "t": 0.0, "dur": dur, "size": size, "color": color}

    # flow
    def start_match(self):
        st = STAGES[self.stage_idx]
        m = st["main"]
        lx, rx = m["x"] + 130, m["x"] + m["w"] - 130
        if self.net_is_host() and self.net_guest_cid:
            self.cpucid = self.net_guest_cid
        self.fighters = [Fighter(self.p1cid, lx, m["y"], 1),
                         Fighter(self.cpucid, rx, m["y"], -1)]
        self.projs, self.parts, self.texts, self.slashes = [], [], [], []
        self.rings = []
        self.drops, self.drop_t = [], 4.0
        self.ult_lock = False
        self.brk = [{**b, "hp": b["hp"], "regen": 0.0} for b in st.get("breakables", [])]
        self.streak_mult = 1.0 + min(0.20, 0.04 * self.save.get("streak", 0))
        self.net_heard_guest = False
        sw = st.get("w", W)
        self.blast = {"l": -60, "r": sw + 60, "t": -100, "b": H + 60}
        self.cam = max(0, min(sw - W, (lx + rx) / 2 - W / 2))
        self.m_glitch = self.m_cosmos = self.m_solar = 0.0
        self._chaos_on = False
        self.timer = MATCH_TIME
        self.sudden = False
        self.phase, self.phase_t = "countdown", 0.0
        self.hitstop = 0.0
        self.winner = None
        self.say("READY", "", 0.7, 64, (255, 230, 140))
        self.state = "fight"
        self.save["games"] = self.save.get("games", 0) + 1
        if self.net_is_host():
            self.net_send_hello()

    def phase_on(self, ph):
        return math.sin(self.t_global * 6.283 / ph["period"] + ph.get("off", 0)) > -0.2

    def damage_brk(self, b, dmg):
        if b["hp"] <= 0:
            return
        b["hp"] -= dmg
        if b["hp"] <= 0:
            b["hp"] = 0
            b["regen"] = 12.0
            cx, cy = b["x"] + b["w"] / 2, b["y"]
            self.splash_hit(cx, cy, (200, 180, 150), 14)
            self.glowpuff(cx, cy, (255, 220, 160), 8, 300, 0.5, 7)
            self.shock(cx, cy, (255, 220, 150), vr=460, life=0.45, width=5)
            self.shake = max(self.shake, 7)
            self.float_text("BREAK!", cx, cy - 30, (255, 210, 130))
        else:
            self.dust(b["x"] + b["w"] / 2, b["y"], 3)

    def platforms(self):
        st = STAGES[self.stage_idx]
        pls = [st["main"]] + st["plats"] + st.get("pads", [])
        for ph in st.get("phases", []):
            if self.phase_on(ph):
                pls.append(ph)
        for b in getattr(self, "brk", []):
            if b["hp"] > 0:
                pls.append(b)
        return pls

    def update_fighter(self, f, o, dt):
        d = f.d
        slowm = 0.6 if f.slow > 0 else 1.0
        for k in ("cd_nb", "cd_up", "cd_down", "cd_dash", "invuln", "iframes",
                  "counter", "armor", "burn", "slow", "drop_t"):
            v = getattr(f, k)
            if v > 0:
                setattr(f, k, max(0.0, v - dt))
        if f.burn > 0:
            f.pct += 2.2 * dt
            if random.random() < dt * 12:
                self.parts.append(Particle(f.x + random.uniform(-10, 10), f.y - 30,
                                           0, -120, 0.4, (255, 130, 40), 4, grav=-200))
        if f.dash_t > 0:
            f.dash_t -= dt
        f.anim += dt * (1.4 if abs(f.vx) > 40 else 1.0)
        # --- animation drivers ---
        for k in ("flash", "pop", "shield_wob", "skid", "streak", "spawn_fx", "combo_t",
                  "coyote", "jump_buf", "star_t", "hammer_t", "spike_cd", "lava_cd"):
            v = getattr(f, k)
            if v > 0:
                setattr(f, k, max(0.0, v - dt))
        if f.combo_t <= 0:
            f.combo = 0
        if f.fuse > 0:
            f.fuse -= dt
            if random.random() < dt * 20 and len(self.parts) < 250:
                self.parts.append(Particle(f.x + random.uniform(-8, 8), f.y - 52,
                                           random.uniform(-40, 40), random.uniform(-140, -40),
                                           0.3, (255, 200, 100), 3, grav=300, glow=True))
            if f.fuse <= 0:
                explode_bomb(f, o, self)
        f.sx += (1.0 - f.sx) * min(1, 11 * dt)
        f.sy += (1.0 - f.sy) * min(1, 11 * dt)
        if f.state == "hitstun":
            f.rot += f.tumble * dt
        elif f.state == "attack" and f.atk and f.atk["kind"] in ("nair", "uair"):
            a0 = f.atk
            prog = clamp(a0["t"] / max(0.01, a0["dur"]), 0.0, 1.0)
            f.rot = -f.facing * 360.0 * ease_out(prog)
        elif f.state == "special" and f.atk and f.atk.get("kind") == "upb":
            f.rot += -f.facing * 900.0 * dt
        elif f.on_ground and f.rot != 0.0:
            f.rot = 0.0
        for gh in list(f.after):
            gh["life"] -= dt
            if gh["life"] <= 0:
                f.after.remove(gh)
        running = abs(f.vx) > 60 and f.on_ground and f.state == "free"
        if running:
            f.step_ph += dt * (7.0 + abs(f.vx) / 45.0)
            sgn = 1.0 if math.sin(f.step_ph) >= 0 else -1.0
            if sgn != f.step_sign:
                f.step_sign = sgn
                self.dust(f.x - f.facing * 8, f.y, 1)
        if f.state == "free" and f.on_ground and f.move_dir != 0 and abs(f.vx) > 150 and (f.vx * f.move_dir < 0):
            if f.skid <= 0:
                self.dust(f.x, f.y, 2)
            f.skid = 0.12
        if f.state == "charge" and random.random() < dt * (14 + f.charge * 30):
            self.parts.append(Particle(f.x + random.uniform(-18, 18), f.y - random.uniform(0, 40),
                                       random.uniform(-20, 20), random.uniform(-190, -90),
                                       0.4, f.d["skin"]["glow"], 4, grav=-120, glow=True))
        stg = STAGES[self.stage_idx]
        main = stg["main"]

        if f.state == "respawn":
            f.t -= dt
            if f.t <= 0:
                f.state = "free"
            return
        if f.shield_held and f.state == "free" and f.on_ground and not f.helpless:
            f.shielding = True
            f.shield_hp = max(0.0, f.shield_hp - 4 * dt)
            f.vx *= 0.85
            if f.shield_hp <= 0:
                f.state = "shieldbreak"
                f.t = 1.6
                f.shielding = False
                f.shield_hp = 40.0
                self.float_text("BREAK!", f.x, f.y - 90, (255, 80, 80))
                self.m_glitch = 0.4
                self.shake = max(self.shake, 5)
                self.shock(f.x, f.y - 30, (140, 200, 255), vr=420, life=0.45, width=5)
        else:
            f.shielding = False
            if f.state == "free":
                f.shield_hp = min(40.0, f.shield_hp + 12 * dt)

        # state machine
        if f.state == "attack" and f.atk:
            a = f.atk
            a["t"] += dt
            md = a["md"]
            if f.on_ground:
                f.vx *= 0.86
            if not a["fx"] and a["t"] >= md["startup"] - 0.02:
                a["fx"] = True
                big = a["kind"] == "smash"
                self.spawn_slash(f, md, big=big, spin=a["kind"] in ("nair", "uair"))
            if not a["has_hit"] and a["t"] >= md["startup"] and a["t"] <= md["startup"] + md["active"]:
                if attack_hitbox(f, md).colliderect(o.rect()):
                    a["has_hit"] = True
                    extra = "smash" if a["kind"] == "smash" else None
                    apply_hit(f, o, md["dmg"], md["kb"], md["kbs"], md["angle"], self, melee=True)
                    if extra and f.cid == "arc":
                        self.ring(o.x, o.y - 30, (255, 240, 130))
                hb = attack_hitbox(f, md)
                for b in self.brk:
                    if b["hp"] > 0 and hb.colliderect(
                            pygame.Rect(int(b["x"]), int(b["y"] - 8), int(b["w"]), 22)):
                        self.damage_brk(b, max(1, round(md["dmg"] / 8)))
            if a["t"] >= a["dur"]:
                f.state = "free"
                f.atk = None
        elif f.state == "charge":
            if f.charging:
                f.charge = min(0.9, f.charge + dt)
            f.vx *= 0.9
        elif f.state == "special":
            f.t -= dt
            if f.atk and f.atk["kind"] == "upb":
                a = f.atk
                a["t"] += dt
                md = a["md"]
                if not a.get("fx"):
                    a["fx"] = True
                    self.spawn_slash(f, md, spin=True)
                if not a["has_hit"] and a["t"] <= md["active"]:
                    if attack_hitbox(f, md).colliderect(o.rect()):
                        a["has_hit"] = True
                        apply_hit(f, o, md["dmg"], md["kb"], md["kbs"], md["angle"], self, melee=True)
            if f.t <= 0:
                f.state = "free"
                f.atk = None
        elif f.state == "hitstun":
            f.t -= dt
            if f.t <= 0:
                f.state = "free"
        elif f.state == "shieldbreak":
            f.t -= dt
            if f.t <= 0:
                f.state = "free"

        # movement driver
        run = d["run"] * slowm * 1.08
        air = d["air"] * slowm * 1.08
        if f.state in ("free",) and not f.shielding and f.dash_t <= 0:
            tgt = f.move_dir * (run if f.on_ground else air) + stg.get("wind", 0)
            rate = 13 if f.on_ground else 7.5
            if stg.get("ice") and f.on_ground:
                rate *= 0.35
            f.vx += (tgt - f.vx) * min(1, rate * dt)
        if f.state == "hitstun":
            f.vx *= (1 - 0.4 * dt)
        # gravity
        f.vy = min(d["maxfall"], f.vy + d["grav"] * stg.get("gravm", 1.0) * dt)
        prev_bottom = f.y
        f.x += f.vx * dt
        f.y += f.vy * dt
        # one-way platforms (pass-through from below = easy recovery)
        f.on_ground = False
        for pl in self.platforms():
            is_main = pl is main
            if f.drop_t > 0 and not is_main:
                continue
            if f.vy >= 0 and prev_bottom <= pl["y"] + 2 and f.y >= pl["y"]:
                if pl["x"] - 14 <= f.x <= pl["x"] + pl["w"] + 14:
                    impact = f.vy
                    f.y = pl["y"]
                    f.vy = 0
                    f.on_ground = True
                    f.jumps = f.max_air
                    if f.helpless:
                        f.helpless = False
                        f.cd_up = 0
                    if not f.was_ground:
                        k = clamp(impact / 2600.0, 0.0, 0.34)
                        if k > 0.03:
                            f.sx, f.sy = 1.0 + k, 1.0 - k * 0.9
                            self.dust(f.x, f.y, 3 + int(k * 22))
                            if k > 0.2:
                                self.ring(f.x, f.y - 4, (255, 255, 255))
                                self.shock(f.x, f.y - 4, (255, 255, 255), vr=380, life=0.4, width=4)
                                self.shake = max(self.shake, 2)
                            if f.cid == "tecton" and k > 0.12:
                                for dirc in (-1, 1):
                                    self.projs.append(Proj(f, f.x + dirc * 24, f.y - 14, dirc * 320,
                                                           8 * f.d["power"], 380, "wave", (255, 160, 90), 11))
                                self.float_text("QUAKE!", f.x, f.y - 100, (255, 170, 90))
                    if pl.get("pad"):
                        f.vy = -pl["pad"]
                        f.on_ground = False
                        f.jumps = f.max_air
                        f.sx, f.sy = 0.85, 1.2
                        self.ring(f.x, f.y - 4, (255, 255, 255))
                        self.dust(f.x, f.y, 4)
        # spike hazards
        if f.spike_cd <= 0 and f.state != "respawn":
            fr = f.rect()
            for sp in STAGES[self.stage_idx].get("spikes", []):
                sr = pygame.Rect(int(sp["x"]), int(sp["y"] - 16), int(sp["w"]), 16)
                if fr.colliderect(sr):
                    f.spike_cd = 0.8
                    f.pct += 8
                    f.max_pct = max(f.max_pct, f.pct)
                    f.pop = 0.3
                    f.vy = min(f.vy, -320)
                    self.splash_hit(f.x, f.y - 26, (255, 80, 80), 6)
                    break
        # lava pools: burn + launch out
        if f.lava_cd <= 0 and f.state != "respawn":
            fr = f.rect()
            for lv in STAGES[self.stage_idx].get("lava", []):
                lr = pygame.Rect(int(lv["x"]), int(lv["y"] - 14), int(lv["w"]), 16)
                if fr.colliderect(lr):
                    f.lava_cd = 1.0
                    f.pct += 10
                    f.max_pct = max(f.max_pct, f.pct)
                    f.pop = 0.3
                    f.burn = max(f.burn, 2.0)
                    f.vy = min(f.vy, -520)
                    f.on_ground = False
                    self.glowpuff(f.x, f.y - 26, (255, 130, 50), 10, 340, 0.5, 7)
                    self.float_text("HOT!", f.x, f.y - 100, (255, 150, 60))
                    break
        if f.on_ground:
            f.coyote = 0.09
        if f.jump_buf > 0 and f.state == "free" and not f.helpless:
            if f.on_ground or f.coyote > 0:
                _exec_jump(f, self, False)
            elif f.jumps > 0:
                _exec_jump(f, self, True)
        f.x = max(self.blast["l"] - 40, min(self.blast["r"] + 40, f.x))
        f.was_ground = f.on_ground

    def update_projs(self, dt):
        st = STAGES[self.stage_idx]
        for pr in list(self.projs):
            pr.life -= dt
            pr.t += dt
            pr.x += pr.vx * dt
            pr.y += pr.vy * dt
            pr.trail.append((pr.x, pr.y))
            if len(pr.trail) > 8:
                pr.trail.pop(0)
            if pr.life <= 0 or pr.x < self.blast["l"] or pr.x > self.blast["r"] or \
                    pr.y < self.blast["t"] or pr.y > self.blast["b"]:
                self.projs.remove(pr)
                continue
            # DISC: the chakram turns around and comes back (hits both trips)
            if pr.kind == "disc" and not pr.ret and pr.t > 0.45:
                pr.ret = True
                pr.vx *= -1
            # METEOR: detonates on the floor with a small blast
            if pr.kind == "meteor" and pr.vy > 0:
                hit_floor = False
                for pl in self.platforms():
                    if pl["x"] - 10 <= pr.x <= pl["x"] + pl["w"] + 10 and abs(pr.y - pl["y"]) < 14:
                        hit_floor = True
                        break
                if hit_floor:
                    self.glowpuff(pr.x, pr.y, (255, 140, 50), 12, 380, 0.5, 8)
                    self.shock(pr.x, pr.y, (255, 150, 60), vr=460, life=0.45, width=5)
                    for f in self.fighters:
                        if f is not pr.owner and f.alive() and f.state != "respawn" and \
                                abs(f.x - pr.x) < 80 and abs(f.y - pr.y) < 110:
                            raw_hit(pr.owner, f, pr.dmg, pr.kb, 5.0, -50, self)
                            f.burn = max(f.burn, 2.0)
                    self.projs.remove(pr)
                    continue
            # WELL: drags the foe, then implodes
            if pr.kind == "well":
                foe = None
                for f in self.fighters:
                    if f is not pr.owner and f.alive() and f.state != "respawn":
                        foe = f
                        break
                if foe is not None:
                    pull = 1 if pr.x >= foe.x else -1
                    foe.vx += pull * 560 * dt
                    foe.vy -= 180 * dt
                    if random.random() < dt * 14:
                        self.parts.append(Particle(foe.x + random.uniform(-14, 14), foe.y - 26,
                                                   (pr.x - foe.x) * 1.5, random.uniform(-60, 60),
                                                   0.35, (255, 90, 150), 4, grav=0, glow=True))
                    if (abs(foe.x - pr.x) < 40 and abs(foe.y - pr.y) < 60) or pr.life < 0.5:
                        if not pr.ret:
                            pr.ret = True
                            self.glowpuff(pr.x, pr.y, (255, 90, 150), 18, 460, 0.6, 9)
                            self.shock(pr.x, pr.y, (255, 90, 150), vr=560, life=0.55, width=7)
                            self.shake = max(self.shake, 9)
                            if abs(foe.x - pr.x) < 200 and abs(foe.y - pr.y) < 150:
                                raw_hit(pr.owner, foe, 16, 500, 5.0, -40, self)
                            self.projs.remove(pr)
                            continue
            r = pygame.Rect(int(pr.x - pr.size), int(pr.y - pr.size), pr.size * 2, pr.size * 2)
            terrain_hit = False
            for b in self.brk:
                if b["hp"] > 0 and r.colliderect(
                        pygame.Rect(int(b["x"]), int(b["y"] - 24), int(b["w"]), 44)):
                    self.damage_brk(b, max(1, round(pr.dmg / 6)))
                    terrain_hit = True
                    break
            if terrain_hit:
                if pr in self.projs:
                    self.projs.remove(pr)
                continue
            for f in self.fighters:
                if not f.alive() or f.state == "respawn":
                    continue
                if f is pr.owner and not (pr.kind == "disc" and pr.ret):
                    continue
                if id(f) in pr.last_hit and pr.t - pr.last_hit[id(f)] < 0.5:
                    continue
                if r.colliderect(f.rect()):
                    # GLASS: a raised counter reflects projectiles back x1.5
                    if f.counter > 0 and f.cid == "glass":
                        f.counter = 0
                        pr.owner = f
                        pr.vx = -pr.vx * 1.3
                        pr.vy = -pr.vy * 1.3
                        pr.dmg *= 1.5
                        pr.last_hit = {}
                        self.ring(f.x, f.y - 30, (255, 255, 255))
                        self.float_text("REFLECT!", f.x, f.y - 100, (230, 220, 255))
                        break
                    pr.last_hit[id(f)] = pr.t
                    ok = apply_hit(pr.owner, f, pr.dmg, pr.kb, 5.0, -25, self)
                    if pr.kind in ("ice", "venom"):
                        f.slow = max(f.slow, 1.5)
                    if pr.kind in ("fire", "meteor"):
                        f.burn = max(f.burn, 2.0)
                    if pr.kind == "disc":
                        break  # chakram pierces through
                    if pr in self.projs:
                        self.projs.remove(pr)
                    break

    def record_result(self, winner):
        w = self.save.get("wins", {})
        w[winner.cid] = w.get(winner.cid, 0) + 1
        self.save["wins"] = w
        if winner is self.fighters[0]:
            self.save["streak"] = self.save.get("streak", 0) + 1
            self.save["best_streak"] = max(self.save.get("best_streak", 0), self.save["streak"])
        else:
            self.save["streak"] = 0
        self.store_save()

    def check_ko(self):
        for i, f in enumerate(self.fighters):
            o = self.fighters[1 - i]
            if not f.alive() or f.state == "respawn":
                continue
            if f.x < self.blast["l"] or f.x > self.blast["r"] or f.y < self.blast["t"] or f.y > self.blast["b"]:
                f.stocks -= 1
                self.splash_hit(max(self.blast["l"], min(self.blast["r"], f.x)),
                                max(0, min(H, f.y - 40)), (255, 220, 120), 26)
                self.glowpuff(max(self.blast["l"], min(self.blast["r"], f.x)),
                              max(0, min(H, f.y - 40)), (255, 240, 200), 12, 420, 0.5, 8)
                self.shake = 12
                self.ko_flash = 0.25
                self.m_glitch = 0.4
                self.shock(f.x, f.y - 40, (255, 220, 130), vr=640, life=0.6, width=8)
                self.ko_x, self.ko_y = f.x, f.y - 40
                if f.stocks <= 0:
                    f.state = "dead"
                    self.winner = o
                    self.phase = "end"
                    self.phase_t = 0.0
                    self.say("GAME!", "", 2.0, 110, (255, 220, 120))
                    self.record_result(o)
                else:
                    st = STAGES[self.stage_idx]
                    m = st["main"]
                    sx = m["x"] + m["w"] / 2
                    f.reset_stock(sx, m["y"] - 4, -1 if i == 0 else 1)
                    self.phase = "ko_freeze"
                    self.phase_t = 0.0
                    self.say("K.O.!", "", 1.1, 110, (255, 90, 80))
                break

    def update_fight(self, dt, p1keys):
        self.phase_t += dt
        if self.announce:
            self.announce["t"] += dt
            if self.announce["t"] >= self.announce["dur"]:
                self.announce = None
        if self.phase == "countdown":
            seq = ["READY", "3", "2", "1", "GO!"]
            idx = min(len(seq) - 1, int(self.phase_t / 0.45))
            cur = seq[idx]
            if not self.announce or self.announce["text"] != cur:
                col = (120, 255, 150) if cur == "GO!" else (255, 255, 255)
                self.say(cur, "", 0.45, 110, col)
            if self.phase_t >= len(seq) * 0.45:
                self.phase = "battle"
                self.announce = None
                self.m_solar = 1.0
            return
        if self.phase == "ko_freeze":
            self.update_fx(dt, 0.15)
            if self.phase_t >= 0.95:
                self.phase = "battle"
            return
        if self.phase == "end":
            self.update_fx(dt, 0.4)
            if self.phase_t >= 2.2:
                self.state = "gameover"
            return
        # battle
        if not self.sudden:
            self.timer -= dt
            if self.timer <= 0:
                self.timer = 0
                a, b = self.fighters
                if a.stocks != b.stocks:
                    self.winner = a if a.stocks > b.stocks else b
                    self.record_result(self.winner)
                    self.phase, self.phase_t = "end", 0.0
                    self.say("TIME!", "", 1.8, 100, (255, 230, 140))
                else:
                    self.sudden = True
                    a.pct = b.pct = 300.0
                    self.say("SUDDEN DEATH", "both at 300%", 2.0, 64, (255, 80, 80))
        p1, cpu = self.fighters
        p1.move_dir = (1 if (p1keys[pygame.K_d] or p1keys[pygame.K_RIGHT]) else 0) - \
                      (1 if (p1keys[pygame.K_a] or p1keys[pygame.K_LEFT]) else 0)
        pad_mv, pad_up, pad_dn, pad_sh = self.pad_intents()
        if pad_mv != 0:
            p1.move_dir = pad_mv
        if p1.move_dir:
            p1.facing = p1.move_dir
        p1.shield_held = bool(p1keys[pygame.K_l]) or pad_sh
        if p1.state == "charge" and p1.charging:
            p1.charge = min(0.9, p1.charge + dt)
        if self.hitstop > 0:
            self.hitstop -= dt
            return
        if self.net_is_host():
            self.net_handle_host_msgs()
            # relay hello is best-effort over the public broker: resend it
            # until the guest's inputs arrive (they set net_heard_guest).
            if (self.state == "fight" and self.net_guest_present()
                    and not getattr(self, "net_heard_guest", False)):
                now = time.time()
                if now - getattr(self, "net_hello_wall", 0) > 1.0:
                    self.net_hello_wall = now
                    self.net_send_hello()
        if self.net_guest_present():
            self.net_apply_guest_inputs(dt)
        else:
            ai_control(cpu, p1, STAGES[self.stage_idx], self, dt)
        self.update_fighter(p1, cpu, dt)
        self.update_fighter(cpu, p1, dt)
        self.update_projs(dt)
        self.update_fx(dt)
        # breakable terrain: collapse, then regenerate after 12s
        for b in getattr(self, "brk", []):
            if b["hp"] <= 0:
                b["regen"] -= dt
                if b["regen"] <= 0:
                    st0 = STAGES[self.stage_idx]
                    maxhp = next((d["hp"] for d in st0.get("breakables", [])
                                  if d["x"] == b["x"] and d["y"] == b["y"]), 3)
                    b["hp"] = maxhp
                    b["regen"] = 0.0
                    self.ring(b["x"] + b["w"] / 2, b["y"], (255, 220, 150))
                    self.float_text("RESTORED", b["x"] + b["w"] / 2, b["y"] - 24,
                                    (255, 220, 150))
        # item drops: spawn over time, pickup on touch
        self.drop_t -= dt
        if self.drop_t <= 0:
            self.drop_t = random.uniform(7, 12)
            if len(self.drops) < 2:
                spawn_drop(self)
        for d in list(self.drops):
            d["t"] += dt
            d["life"] -= dt
            if d["life"] <= 0:
                self.drops.remove(d)
        for d in list(self.drops):
            dr = pygame.Rect(int(d["x"] - 13), int(d["y"] - 13), 26, 26)
            for i, f in enumerate(self.fighters):
                if f.alive() and f.state != "respawn" and dr.colliderect(f.rect()):
                    apply_drop(f, self.fighters[1 - i], d, self)
                    if d in self.drops:
                        self.drops.remove(d)
                    break
        # camera glued to the PLAYER (position + velocity lookahead only)
        anchor = p1.x + p1.vx * 0.25
        sw = STAGES[self.stage_idx].get("w", W)
        tgt = max(0, min(sw - W, anchor - W / 2))
        self.cam += (tgt - self.cam) * min(1, 5 * dt)
        # CHAOS ULTRA mode: both ultimates full
        if p1.ult >= 100 and cpu.ult >= 100:
            if not self._chaos_on:
                self._chaos_on = True
                self.float_text("CHAOS ULTRA!", W / 2 + self.cam, 120, (255, 180, 100))
        else:
            self._chaos_on = False
        self.check_ko()
        if self.shake > 0:
            self.shake = max(0, self.shake - 26 * dt)

    # ---------------- events ----------------
    def key_down_fight(self, ev):
        p1 = self.fighters[0]
        k = ev.key
        up = pygame.key.get_pressed()[pygame.K_w] or pygame.key.get_pressed()[pygame.K_UP]
        if k == pygame.K_TAB:
            self.show_moves = not self.show_moves
        elif k in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
            if self.phase == "battle":
                # Down+Jump on platform = drop; else jump (buffered)
                keys = pygame.key.get_pressed()
                if keys[pygame.K_DOWN]:
                    p1.drop_t = 0.25
                    p1.y += 3
                else:
                    do_jump(p1, self)
        elif k in (pygame.K_j, pygame.K_z):
            if self.phase == "battle":
                do_attack_ctx(p1, self, up=up)
        elif k in (pygame.K_k, pygame.K_x):
            if self.phase == "battle":
                do_smash_start(p1, self)
        elif k in (pygame.K_u, pygame.K_c):
            if self.phase == "battle":
                do_nb(p1, self, self.fighters[1])
        elif k in (pygame.K_i, pygame.K_v):
            if self.phase == "battle":
                do_upb(p1, self)
        elif k in (pygame.K_o, pygame.K_e, pygame.K_s):
            if self.phase == "battle":
                do_downb(p1, self, self.fighters[1])
        elif k == pygame.K_f:
            if self.phase == "battle":
                fire_ultimate(p1, self.fighters[1], self)
        elif k == pygame.K_LSHIFT or k == pygame.K_RSHIFT:
            if self.phase == "battle":
                do_dash(p1, self)
        elif k == pygame.K_DOWN:
            if self.phase == "battle" and p1.on_ground and not p1.shield_held:
                # drop through floating plat (no-op on main)
                st = STAGES[self.stage_idx]
                on_main = abs(p1.y - st["main"]["y"]) < 3 and \
                    st["main"]["x"] - 14 <= p1.x <= st["main"]["x"] + st["main"]["w"] + 14
                if not on_main:
                    p1.drop_t = 0.25
                    p1.y += 3
                else:
                    p1.vy += 1  # crouch flavor
            elif self.phase == "battle" and not p1.on_ground:
                p1.vy = min(p1.d["maxfall"], p1.vy + 320)

    def key_up_fight(self, ev):
        if ev.key in (pygame.K_k, pygame.K_x) and self.phase == "battle":
            do_smash_release(self.fighters[0], self)

    def mouse_down_fight(self, ev):
        if self.phase != "battle":
            return
        p1 = self.fighters[0]
        if ev.button == 1:  # LMB = attack
            keys = pygame.key.get_pressed()
            do_attack_ctx(p1, self, up=bool(keys[pygame.K_w] or keys[pygame.K_UP]))
        elif ev.button == 3:  # RMB = SMART (counter / dash / heavy)
            smart_action(p1, self.fighters[1], self)

    # ================= GAMEPAD =================
    def pad_refresh(self):
        try:
            pygame.joystick.init()
        except Exception:
            pass
        try:
            if self.pad_joy is not None:
                try:
                    self.pad_joy.quit()
                except Exception:
                    pass
                self.pad_joy = None
                self.pad_name = ""
            if pygame.joystick.get_count() > 0:
                self.pad_joy = pygame.joystick.Joystick(0)
                self.pad_joy.init()
                self.pad_name = self.pad_joy.get_name()
                nl = self.pad_name.lower()
                self.pad_prof = PAD_XINPUT if ("xinput" in nl or "xbox" in nl) else PAD_DINPUT
        except Exception:
            self.pad_joy = None
            self.pad_name = ""

    def pad_intents(self):
        """Held-state intents: (move_dir, aim_up, down, shield_hold)."""
        if self.pad_test is not None:
            return self.pad_test
        mv, up, dn, sh = 0, False, False, False
        j = self.pad_joy
        if j is None:
            return mv, up, dn, sh
        try:
            if j.get_numhats() > 0:
                hx, hy = j.get_hat(0)
                if hx < 0:
                    mv = -1
                elif hx > 0:
                    mv = 1
                up = hy > 0
                dn = hy < 0
            if mv == 0 and j.get_numaxes() >= 1:
                ax = j.get_axis(0)
                if ax < -0.4:
                    mv = -1
                elif ax > 0.4:
                    mv = 1
            if j.get_numaxes() >= 2:
                ay = j.get_axis(1)
                up = up or ay < -0.4
                dn = dn or ay > 0.4
            lb = self.pad_prof["lb"]
            if j.get_numbuttons() > lb and j.get_button(lb) and self.pad_lb_t is not None:
                if pygame.time.get_ticks() - self.pad_lb_t > 220:
                    sh = True
        except Exception:
            pass
        return mv, up, dn, sh

    def pad_action(self, btn):
        """Edge-triggered pad button during battle."""
        if self.phase != "battle" or not self.fighters or getattr(self, "paused", False):
            return False
        self.pad_last = f"btn {btn}"
        P = self.pad_prof
        p1, foe = self.fighters
        mv, up, dn, _ = self.pad_intents()
        if btn == P["jump"]:
            if dn and p1.on_ground:
                p1.drop_t = 0.25
                p1.y += 3
            else:
                do_jump(p1, self)
        elif btn == P["attack"]:
            do_attack_ctx(p1, self, up=up)
        elif btn == P["smash"]:
            do_smash_start(p1, self)
        elif btn == P["nb"]:
            do_nb(p1, self, foe)
        elif btn == P["upb"]:
            do_upb(p1, self)
        elif btn == P["super"]:
            do_downb(p1, self, foe)
        elif btn == P["pause"]:
            self.paused = not self.paused
            if self.paused:
                self.paused_idx = 0
        elif btn == P["lb"] or btn == P.get("rb", -1):
            try:
                other = P["rb"] if btn == P["lb"] else P["lb"]
                both = self.pad_joy is not None and self.pad_joy.get_numbuttons() > other \
                    and self.pad_joy.get_button(other)
            except Exception:
                both = False
            if both:
                self.pad_swallow_lb = True
                fire_ultimate(p1, foe, self)
            elif btn == P["lb"]:
                self.pad_lb_t = pygame.time.get_ticks()
        else:
            return False
        return True

    def pad_release(self, btn):
        P = self.pad_prof
        if not self.fighters:
            return
        p1 = self.fighters[0]
        if btn == P["smash"]:
            do_smash_release(p1, self)
        elif btn == P["lb"]:
            if self.pad_swallow_lb:
                self.pad_swallow_lb = False
                self.pad_lb_t = None
                return
            if self.pad_lb_t is not None:
                held = pygame.time.get_ticks() - self.pad_lb_t
                self.pad_lb_t = None
                if held < 220 and self.phase == "battle" and not getattr(self, "paused", False):
                    do_dash(p1, self)

    def pad_hat_fight(self, value):
        self.pad_last = f"hat {tuple(value)}"
        if self.phase != "battle" or not self.fighters or getattr(self, "paused", False):
            return
        p1 = self.fighters[0]
        if value[1] < 0:
            if p1.on_ground:
                st = STAGES[self.stage_idx]
                on_main = abs(p1.y - st["main"]["y"]) < 3 and \
                    st["main"]["x"] - 14 <= p1.x <= st["main"]["x"] + st["main"]["w"] + 14
                if not on_main:
                    p1.drop_t = 0.25
                    p1.y += 3
            else:
                p1.vy = min(p1.d["maxfall"], p1.vy + 320)

    def pad_menu_button(self, btn):
        self.pad_last = f"btn {btn}"
        P = self.pad_prof
        if self.state == "title":
            if btn == P["confirm"]:
                self.do_title_action(["fight", "help", "online", "quit"][self.menu_idx])
            return True
        if self.state == "help":
            if btn == P["confirm"] or btn == P["back"]:
                self.state = "title"
            return True
        if self.state == "online":
            if btn == P["confirm"]:
                if self.menu_idx == 0:
                    if self.net_start_host():
                        self.goto_select()
                elif self.menu_idx == 1:
                    self.state = "ip"
                    self.ip_buf = ""
                    self.ip_err = ""
                    self.ip_mode = "ip"
                else:
                    self.state = "net"
                    self.menu_idx = 0
            elif btn == P["back"]:
                self.state = "title"
                self.menu_idx = 2
            return True
        if self.state == "net":
            if btn == P["confirm"]:
                if self.menu_idx == 0:
                    if self.net_start_host(link="relay"):
                        self.goto_select()
                else:
                    self.state = "ip"
                    self.ip_buf = ""
                    self.ip_err = ""
                    self.ip_mode = "room"
            elif btn == P["back"]:
                self.state = "online"
            return True
        if self.state == "ip":
            if btn == P["back"]:
                self.state = "online"
            return True
        if self.state == "select":
            s = self.sel
            if btn == P["confirm"]:
                if not s["lock"]:
                    s["lock"] = True
                    self.p1cid = ROSTER[s["row"] * 5 + s["col"]]
                    if self.cpucid == self.p1cid:
                        self.cpucid = random.choice([c for c in ROSTER if c != self.p1cid])
                    self.refresh_previews()
                else:
                    self.stage_idx = s["stage"]
                    if self.net_role == "host":
                        self.state = "lobby"
                    else:
                        self.state = "vs"
                        self.vs_t = 0.0
            elif btn == P["back"]:
                if s["lock"]:
                    s["lock"] = False
                    idx = ROSTER.index(self.p1cid)
                    s["row"], s["col"] = idx // 5, idx % 5
                else:
                    self.state = "title"
            elif btn == 3:
                self.ai_level = (self.ai_level + 1) % len(DIFFS)
            elif btn == 2 or btn == 0:
                self.cpucid = random.choice([c for c in ROSTER])
                self.refresh_previews()
            return True
        if self.state == "online":
            if btn == P["confirm"]:
                if self.menu_idx == 0:
                    if self.net_start_host():
                        self.goto_select()
                else:
                    self.state = "ip"
                    self.ip_buf = ""
                    self.ip_err = ""
            elif btn == P["back"]:
                self.state = "title"
                self.menu_idx = 2
            return True
        if self.state == "ip":
            if btn == P["back"]:
                self.state = "online"
            return True
        if self.state == "lobby":
            if btn == P["confirm"]:
                if self.net_guest_cid:
                    self.start_match()
            elif btn == P["back"]:
                self.state = "select"
            return True
        if self.state == "gpick":
            if btn == P["confirm"]:
                self.p1cid = ROSTER[self.gpick_idx]
                if self.net_peer is not None:
                    self.net_peer.send({"t": "pick", "cid": self.p1cid})
                self.state = "gwait"
            elif btn == P["back"]:
                self.net_stop()
                self.state = "title"
            return True
        if self.state == "gwait":
            if btn == P["back"]:
                self.net_stop()
                self.state = "title"
            return True
        if self.state == "vs":
            if btn == P["confirm"]:
                self.start_match()
            elif btn == P["back"]:
                self.state = "select"
            return True
        if self.state == "fight" and getattr(self, "paused", False):
            if self.net_is_guest():
                if self.net_peer is not None:
                    self.net_peer.send({"t": "pause"})
                return True
            if btn == P["confirm"]:
                self.do_pause_action(["resume", "rematch", "select", "title"][self.paused_idx])
            elif btn == P["back"]:
                self.paused = False
            return True
        if self.state == "gameover":
            if btn == P["confirm"]:
                if self.net_is_guest():
                    self.net_stop()
                    self.state = "title"
                else:
                    self.do_gameover_action(["rematch", "select", "title"][self.go_idx])
            return True
        return False

    def pad_menu_hat(self, value):
        self.pad_last = f"hat {tuple(value)}"
        hx, hy = value[0], value[1]
        if self.state == "title":
            if hy > 0:
                self.menu_idx = (self.menu_idx - 1) % 4
            elif hy < 0:
                self.menu_idx = (self.menu_idx + 1) % 4
        elif self.state == "online":
            if hy > 0:
                self.menu_idx = (self.menu_idx - 1) % 3
            elif hy < 0:
                self.menu_idx = (self.menu_idx + 1) % 3
        elif self.state == "net":
            if hy > 0:
                self.menu_idx = (self.menu_idx - 1) % 2
            elif hy < 0:
                self.menu_idx = (self.menu_idx + 1) % 2
        elif self.state == "select":
            s = self.sel
            if not s["lock"]:
                if hx < 0:
                    move_select(s, 0, -1)
                elif hx > 0:
                    move_select(s, 0, 1)
                elif hy > 0:
                    move_select(s, -1, 0)
                elif hy < 0:
                    move_select(s, 1, 0)
            else:
                if hx < 0:
                    s["scol"] = (s.get("scol", 0) - 1) % 5
                elif hx > 0:
                    s["scol"] = (s.get("scol", 0) + 1) % 5
                elif hy > 0:
                    s["srow"] = (s.get("srow", 0) - 1) % ((len(STAGES) + 4) // 5)
                elif hy < 0:
                    s["srow"] = (s.get("srow", 0) + 1) % ((len(STAGES) + 4) // 5)
                self.sync_stage_cursor(s)
        elif self.state == "gpick":
            if hx < 0:
                self.gpick_idx = (self.gpick_idx - 1) % len(ROSTER)
            elif hx > 0:
                self.gpick_idx = (self.gpick_idx + 1) % len(ROSTER)
            elif hy > 0:
                self.gpick_idx = (self.gpick_idx - 5) % len(ROSTER)
            elif hy < 0:
                self.gpick_idx = (self.gpick_idx + 5) % len(ROSTER)
        elif self.state == "fight" and getattr(self, "paused", False):
            if hy > 0:
                self.paused_idx = (self.paused_idx - 1) % 4
            elif hy < 0:
                self.paused_idx = (self.paused_idx + 1) % 4
        elif self.state == "gameover":
            if hx < 0:
                self.go_idx = (self.go_idx - 1) % 3
            elif hx > 0:
                self.go_idx = (self.go_idx + 1) % 3

    # ================= ONLINE (host side) =================
    def net_is_host(self):
        return self.net_role == "host"

    def net_is_guest(self):
        return self.net_role == "guest"

    def net_guest_present(self):
        return self.net_is_host() and self.net_peer is not None and not self.net_peer.dead

    def net_start_host(self, link="lan"):
        try:
            if self.net_listen is not None:
                try:
                    self.net_listen.close()
                except Exception:
                    pass
                self.net_listen = None
            self.net_stop_peer_only()
            if link == "relay":
                if netrelay is None or not netrelay.available():
                    self.ip_err = "need: pip install paho-mqtt"
                    return False
                code = netrelay.make_code()
                peer = netrelay.RelayPeer(code, "host")
                err = peer.connect()
                if err:
                    self.ip_err = err
                    return False
                self.net_peer = peer
                self.net_link = "relay"
                self.net_room = code
            else:
                self.net_listen = netplay.host_socket()
                self.net_link = "lan"
                self.net_room = ""
            self.net_role = "host"
            self.net_peer = self.net_peer if link == "relay" else None
            self.net_guest_cid = None
            self.net_local_ip = netplay.local_ip()
            return True
        except Exception:
            self.net_listen = None
            self.net_role = None
            return False

    def net_stop_peer_only(self):
        try:
            if self.net_peer is not None:
                self.net_peer.close()
        except Exception:
            pass
        self.net_peer = None

    def net_relay_join(self, code):
        code = "".join(ch for ch in code.upper() if ch.isalnum())[:8]
        if netrelay is None or not netrelay.available():
            self.ip_err = "need: pip install paho-mqtt"
            return False
        if len(code) < 3:
            self.ip_err = "room code too short"
            return False
        peer = netrelay.RelayPeer(code, "guest")
        err = peer.connect()
        if err:
            self.ip_err = err
            return False
        self.net_stop_peer_only()
        self.net_peer = peer
        self.net_role = "guest"
        self.net_link = "relay"
        self.net_room = code
        self.net_last_rx = self.t_global
        return True

    def net_stop(self):
        try:
            if self.net_peer is not None:
                try:
                    self.net_peer.send({"t": "bye"})
                    self.net_peer.pump()
                except Exception:
                    pass
                self.net_peer.close()
        except Exception:
            pass
        try:
            if self.net_listen is not None:
                self.net_listen.close()
        except Exception:
            pass
        self.net_role = None
        self.net_peer = None
        self.net_listen = None
        self.net_guest_cid = None
        self.net_link = None
        self.net_room = ""
        self.net_inputs = {"move": 0, "shield": False, "acts": []}
        self.net_events = []

    def net_poll_lobby(self):
        """Host: accept a guest. Returns True on new connection."""
        if self.net_listen is None:
            return False
        try:
            conn, _ = self.net_listen.accept()
        except BlockingIOError:
            return False
        except Exception:
            return False
        if self.net_peer is not None and not self.net_peer.dead:
            try:
                conn.close()
            except Exception:
                pass
            return False
        self.net_peer = netplay.Peer(conn)
        self.net_guest_cid = None
        self.net_last_rx = self.t_global
        return True

    def net_send_hello(self):
        if not self.net_guest_present():
            return
        p2cid = self.net_guest_cid or self.cpucid
        self.net_peer.send({"t": "hello", "p1": self.p1cid, "p2": p2cid,
                            "stage": self.stage_idx, "stocks": STOCKS})

    def net_snapshot(self):
        a, b = self.fighters
        snap = {"t": "snap", "sq": self.net_sq, "timer": round(self.timer, 2),
                "phase": self.phase, "sudden": bool(self.sudden), "cam": round(self.cam, 1),
                "p1": netplay.fighter_state(a), "p2": netplay.fighter_state(b),
                "projs": [netplay.proj_state(p, 0 if p.owner is a else 1) for p in self.projs],
                "rings": [netplay.ring_state(r) for r in self.rings[:8]],
                "slashes": [netplay.slash_state(s) for s in self.slashes[:8]],
                "drops": [netplay.drop_state(d) for d in self.drops],
                "events": self.net_events[:12],
                "paused": bool(getattr(self, "paused", False)),
                "over": None}
        if self.state == "gameover" and self.winner is not None:
            snap["over"] = 0 if self.winner is a else 1
        an = self.announce
        snap["announce"] = None if not an else {
            "text": an["text"], "sub": an["sub"], "size": an["size"],
            "color": list(an["color"]), "dur": an["dur"]}
        self.net_events = []
        return snap

    def net_handle_host_msgs(self):
        """Pump guest messages on the host. Drives P2 inputs / lobby / pause."""
        if self.net_peer is None:
            return
        for m in self.net_peer.pump():
            self.net_last_rx = self.t_global
            t = m.get("t")
            if t == "pick":
                cid = m.get("cid")
                if cid in ROSTER:
                    self.net_guest_cid = cid
                    if self.state == "lobby":
                        self.net_peer.send({"t": "lobby", "p2": cid})
            elif t == "in":
                self.net_heard_guest = True
                if self.state == "fight":
                    try:
                        self.net_inputs["move"] = max(-1, min(1, int(m.get("move", 0))))
                    except Exception:
                        pass
                    self.net_inputs["shield"] = bool(m.get("shield", False))
                    acts = m.get("acts", [])
                    if isinstance(acts, list):
                        self.net_inputs["acts"].extend(acts[:8])
            elif t == "pause":
                if self.state == "fight":
                    self.paused = not getattr(self, "paused", False)
                    if self.paused:
                        self.paused_idx = 0
            elif t == "ping":
                self.net_peer.send({"t": "pong", "sq": m.get("sq", 0), "t0": m.get("t0", 0)})
        if self.net_peer.dead and self.state == "fight":
            self.net_peer = None
            self.net_inputs = {"move": 0, "shield": False, "acts": []}
            self.float_text("GUEST LEFT — CPU TAKES OVER", W // 2 + self.cam, 120, (255, 150, 120))

    def net_apply_guest_inputs(self, dt):
        """Drive fighters[1] from the guest's input state + edge queue."""
        if len(self.fighters) < 2:
            return
        o = self.fighters[1]
        ni = self.net_inputs
        o.move_dir = ni["move"]
        if o.move_dir:
            o.facing = o.move_dir
        o.shield_held = bool(ni["shield"])
        if o.state == "charge" and o.charging:
            o.charge = min(0.9, o.charge + dt)
        for act in ni["acts"]:
            if not isinstance(act, list) or not act:
                continue
            k = act[0]
            if k == "jump":
                do_jump(o, self)
            elif k == "attack":
                do_attack_ctx(o, self, up=bool(act[1]) if len(act) > 1 else False)
            elif k == "smash_start":
                do_smash_start(o, self)
            elif k == "smash_release":
                do_smash_release(o, self)
            elif k == "nb":
                do_nb(o, self, self.fighters[0])
            elif k == "upb":
                do_upb(o, self)
            elif k == "downb":
                do_downb(o, self, self.fighters[0])
            elif k == "dash":
                do_dash(o, self)
            elif k == "drop":
                o.drop_t = 0.25
                o.y += 3
            elif k == "ffall":
                o.vy = min(o.d["maxfall"], o.vy + 320)
            elif k == "ult":
                fire_ultimate(o, self.fighters[0], self)
            elif k == "smart":
                smart_action(o, self.fighters[0], self)
        ni["acts"] = []

    # ================= ONLINE (guest side) =================
    def net_connect(self, ip, port=7001):
        import socket
        import time as _time
        last_err = ""
        for _ in range(3):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5.0)
                s.connect((ip.strip(), port))
                s.settimeout(None)
                self.net_peer = netplay.Peer(s)
                self.net_role = "guest"
                self.net_last_rx = self.t_global
                return True
            except Exception as e:
                last_err = str(e)[:60]
                try:
                    s.close()
                except Exception:
                    pass
                _time.sleep(0.4)
        self.ip_err = "could not connect: " + last_err
        return False

    def net_send_inputs(self, p1keys):
        if self.net_peer is None or self.net_peer.dead or not self.fighters:
            return
        mv = (1 if (p1keys[pygame.K_d] or p1keys[pygame.K_RIGHT]) else 0) - \
             (1 if (p1keys[pygame.K_a] or p1keys[pygame.K_LEFT]) else 0)
        pmv, _, _, psh = self.pad_intents()
        if mv == 0:
            mv = pmv
        self.net_in_sq += 1
        self.net_peer.send({"t": "in", "sq": self.net_in_sq, "move": mv,
                            "shield": bool(p1keys[pygame.K_l]) or psh,
                            "acts": self.net_outbox})
        self.net_outbox = []

    def net_guest_act(self, act):
        self.net_outbox.append(act)
        if len(self.net_outbox) > 8:
            self.net_outbox = self.net_outbox[-8:]

    def net_guest_key(self, ev):
        keys = pygame.key.get_pressed()
        up = bool(keys[pygame.K_w] or keys[pygame.K_UP])
        k = ev.key
        if k in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                self.net_guest_act(["drop"])
            else:
                self.net_guest_act(["jump"])
        elif k in (pygame.K_j, pygame.K_z):
            self.net_guest_act(["attack", up])
        elif k in (pygame.K_k, pygame.K_x):
            self.net_guest_act(["smash_start"])
        elif k in (pygame.K_u, pygame.K_c):
            self.net_guest_act(["nb"])
        elif k in (pygame.K_i, pygame.K_v):
            self.net_guest_act(["upb"])
        elif k in (pygame.K_o, pygame.K_e, pygame.K_s):
            self.net_guest_act(["downb"])
        elif k in (pygame.K_LSHIFT, pygame.K_RSHIFT):
            self.net_guest_act(["dash"])
        elif k == pygame.K_f:
            self.net_guest_act(["ult"])
        elif k == pygame.K_TAB:
            self.show_moves = not self.show_moves
        elif k == pygame.K_DOWN:
            if self.fighters and self.fighters[0].on_ground:
                self.net_guest_act(["drop"])
            else:
                self.net_guest_act(["ffall"])

    def net_guest_keyup(self, ev):
        if ev.key in (pygame.K_k, pygame.K_x):
            self.net_guest_act(["smash_release"])

    def net_guest_mouse(self, ev):
        if ev.button == 1:
            keys = pygame.key.get_pressed()
            self.net_guest_act(["attack", bool(keys[pygame.K_w] or keys[pygame.K_UP])])
        elif ev.button == 3:
            self.net_guest_act(["smart"])

    def net_guest_pad(self, btn):
        P = self.pad_prof
        _, up, dn, _ = self.pad_intents()
        if btn == P["jump"]:
            if dn:
                self.net_guest_act(["drop"])
            else:
                self.net_guest_act(["jump"])
        elif btn == P["attack"]:
            self.net_guest_act(["attack", up])
        elif btn == P["smash"]:
            self.net_guest_act(["smash_start"])
        elif btn == P["nb"]:
            self.net_guest_act(["nb"])
        elif btn == P["upb"]:
            self.net_guest_act(["upb"])
        elif btn == P["super"]:
            self.net_guest_act(["downb"])
        elif btn == P["lb"] or btn == P.get("rb", -1):
            try:
                other = P["rb"] if btn == P["lb"] else P["lb"]
                both = self.pad_joy is not None and self.pad_joy.get_numbuttons() > other \
                    and self.pad_joy.get_button(other)
            except Exception:
                both = False
            if both:
                self.pad_swallow_lb = True
                self.net_guest_act(["ult"])
            elif btn == P["lb"]:
                self.pad_lb_t = pygame.time.get_ticks()

    def net_guest_pad_up(self, btn):
        P = self.pad_prof
        if btn == P["smash"]:
            self.net_guest_act(["smash_release"])
        elif btn == P["lb"]:
            if self.pad_swallow_lb:
                self.pad_swallow_lb = False
                self.pad_lb_t = None
                return
            if self.pad_lb_t is not None:
                if pygame.time.get_ticks() - self.pad_lb_t < 220:
                    self.net_guest_act(["dash"])
                self.pad_lb_t = None

    def net_guest_hat(self, value):
        self.pad_last = f"hat {tuple(value)}"
        if self.phase != "battle" or not self.fighters or getattr(self, "paused", False):
            return
        if value[1] < 0:
            p1 = self.fighters[0]
            if p1.on_ground:
                self.net_guest_act(["drop"])
            else:
                self.net_guest_act(["ffall"])

    def net_guest_tick(self, dt, p1keys):
        if self.net_peer is not None and not self.net_peer.dead:
            if self.state == "fight" and not getattr(self, "paused", False):
                self.net_send_inputs(p1keys)
            for m in self.net_peer.pump():
                self.net_last_rx = self.t_global
                t = m.get("t")
                if t == "hello":
                    if self.state in ("fight", "gameover", "gwait", "gpick"):
                        self.net_apply_hello(m)
                elif t == "snap":
                    if self.state == "fight":
                        self.net_apply_snap(m)
                elif t == "pong":
                    pass
                elif t == "bye":
                    self.net_peer.dead = True
        if self.net_peer is None or self.net_peer.dead:
            if self.state in ("fight", "gwait"):
                self.net_stop()
                self.state = "title"
            return
        if self.state == "fight" and self.t_global - self.net_last_rx > 5.0:
            self.net_stop()
            self.state = "title"
            return
        self.update_fx(dt)

    def net_apply_hello(self, m):
        try:
            p1, p2, st = m.get("p1"), m.get("p2"), int(m.get("stage", 0))
        except Exception:
            return
        if p1 not in ROSTER or p2 not in ROSTER:
            return
        st = max(0, min(len(STAGES) - 1, st))
        if self.state == "fight" and (self.p1cid, self.cpucid, self.stage_idx) == (p1, p2, st):
            return
        self.p1cid, self.cpucid = p1, p2
        self.stage_idx = st
        self.net_last_rx = self.t_global
        self.start_match()

    def net_apply_snap(self, m):
        if len(self.fighters) != 2:
            return
        for key, i in (("p1", 0), ("p2", 1)):
            d = m.get(key)
            if not isinstance(d, dict):
                return
            f = self.fighters[i]
            if f.cid != d.get("cid") and d.get("cid") in ROSTER:
                nf = Fighter(d["cid"], d.get("x", 400), d.get("y", 400), f.facing)
                self.fighters[i] = nf
                f = nf
            prev_pct, prev_stocks = f.pct, f.stocks
            try:
                f.x = float(d.get("x", f.x))
                f.y = float(d.get("y", f.y))
                f.vx = float(d.get("vx", 0))
                f.vy = float(d.get("vy", 0))
                f.facing = 1 if int(d.get("facing", 1)) >= 0 else -1
                f.pct = float(d.get("pct", 0))
                f.stocks = int(d.get("stocks", f.stocks))
                f.jumps = int(d.get("jumps", 1))
                f.shield_hp = float(d.get("shield", 40))
                f.ult = float(d.get("ult", 0))
                f.combo = int(d.get("combo", 0))
                f.state = str(d.get("state", "free"))
                f.charge = float(d.get("charge", 0))
                a = d.get("atk")
                f.atk = None if not a else {"kind": str(a.get("kind", "jab")),
                                           "t": float(a.get("t", 0)), "dur": float(a.get("dur", 0.3)),
                                           "md": dict(a.get("md", {})), "has_hit": True, "fx": True}
                f.shielding = bool(d.get("shielding", False))
                f.invuln = float(d.get("invuln", 0))
                f.helpless = bool(d.get("helpless", False))
                f.counter = float(d.get("counter", 0))
                f.armor = float(d.get("armor", 0))
                f.burn = float(d.get("burn", 0))
                f.slow = float(d.get("slow", 0))
                f.on_ground = bool(d.get("ground", True))
                f.move_dir = int(d.get("mv", 0))
                f.dash_t = float(d.get("dash", 0))
                f.rot = float(d.get("rot", 0))
                f.sx = float(d.get("sx", 1))
                f.sy = float(d.get("sy", 1))
                f.flash = float(d.get("flash", 0))
                f.star_t = float(d.get("star", 0))
                f.hammer_t = float(d.get("hammer", 0))
                f.fuse = float(d.get("fuse", 0))
                f.max_pct = float(d.get("maxp", f.max_pct))
                f.pop = float(d.get("pop", 0))
            except Exception:
                pass
            if f.pct > prev_pct + 0.5:
                self.splash_hit((f.x + self.fighters[1 - i].x) / 2, f.y - 30,
                                (255, 255, 255), min(14, 4 + int(f.pct - prev_pct)))
            if f.stocks < prev_stocks:
                self.splash_hit(max(0, min(W, f.x)), max(0, min(H, f.y - 40)),
                                (255, 220, 120), 22)
                self.shake = 12
        self.projs = []
        for pd in (m.get("projs") or [])[:12]:
            try:
                owner = self.fighters[1 if int(pd.get("o", 0)) else 0]
                pr = Proj(owner, float(pd.get("x", 0)), float(pd.get("y", 0)),
                          float(pd.get("vx", 0)), float(pd.get("dmg", 5)), float(pd.get("kb", 200)),
                          str(pd.get("kind", "bolt")), tuple(pd.get("color", (255, 255, 255))),
                          int(pd.get("size", 6)))
                pr.vy = float(pd.get("vy", 0))
                pr.life = float(pd.get("life", 2))
                self.projs.append(pr)
            except Exception:
                continue
        self.rings = []
        for rd in (m.get("rings") or [])[:8]:
            try:
                rg = Ring(float(rd.get("x", 0)), float(rd.get("y", 0)),
                          tuple(rd.get("color", (255, 255, 255))))
                rg.r = float(rd.get("r", 12))
                rg.life = float(rd.get("life", 0.4))
                rg.max = float(rd.get("max", 0.4))
                rg.width = float(rd.get("w", 5))
                self.rings.append(rg)
            except Exception:
                continue
        self.slashes = []
        for sd in (m.get("slashes") or [])[:8]:
            try:
                sl = Slash(float(sd.get("x", 0)), float(sd.get("y", 0)), int(sd.get("facing", 1)),
                           float(sd.get("rng", 40)), float(sd.get("hi", 40)),
                           tuple(sd.get("color", (255, 255, 255))))
                sl.life = float(sd.get("life", 0.2))
                sl.max = float(sd.get("max", 0.2))
                sl.spin = bool(sd.get("spin", False))
                self.slashes.append(sl)
            except Exception:
                continue
        self.drops = []
        for dd in (m.get("drops") or [])[:4]:
            try:
                if dd.get("kind") in DROPS:
                    self.drops.append({"kind": dd["kind"], "x": float(dd.get("x", 0)),
                                       "y": float(dd.get("y", 0)), "t": float(dd.get("t", 0)),
                                       "life": float(dd.get("life", 10))})
            except Exception:
                continue
        try:
            self.timer = float(m.get("timer", self.timer))
            self.phase = str(m.get("phase", self.phase))
            self.sudden = bool(m.get("sudden", False))
            self.cam = float(m.get("cam", self.cam))
            self.paused = bool(m.get("paused", False))
        except Exception:
            pass
        for e in (m.get("events") or [])[:12]:
            try:
                self.float_text(e.get("s", "!"), float(e.get("x", 0)), float(e.get("y", 0)),
                                tuple(e.get("color", (255, 255, 255))))
            except Exception:
                continue
        an = m.get("announce")
        cur = self.announce.get("text") if isinstance(self.announce, dict) else None
        if isinstance(an, dict) and an.get("text") != cur:
            try:
                self.say(an.get("text", ""), an.get("sub", ""), 1.4, int(an.get("size", 84)),
                         tuple(an.get("color", (255, 255, 255))))
            except Exception:
                pass
        ov = m.get("over")
        if ov in (0, 1) and self.state == "fight":
            self.winner = self.fighters[ov]
            self.phase = "end"
            self.phase_t = 0.0
            self.state = "gameover"

    def load_sprites(self, base=None):
        """Load external 3D sprite packs: assets/fighters/<cid>/*.png + meta.json.
        Missing packs fall back to the procedural 3D rig automatically."""
        out = {}
        if base is None:
            base = os.path.join(asset_base(), "fighters")
        try:
            cids = sorted(os.listdir(base))
        except Exception:
            return out
        for cid in cids:
            d = os.path.join(base, cid)
            if not os.path.isdir(d):
                continue
            poses, meta = {}, {"fps": 10, "anchor": [80, 146]}
            mp = os.path.join(d, "meta.json")
            if os.path.isfile(mp):
                try:
                    with open(mp) as fh:
                        meta.update(json.load(fh))
                except Exception:
                    continue
                for pose, files in meta.get("poses", {}).items():
                    fr = []
                    for fn in files:
                        p = os.path.join(d, fn)
                        if os.path.isfile(p):
                            try:
                                fr.append(pygame.image.load(p).convert_alpha())
                            except Exception:
                                pass
                    if fr:
                        poses[pose] = fr
            else:
                for fn in sorted(os.listdir(d)):
                    if not fn.lower().endswith(".png"):
                        continue
                    stem = fn[:-4]
                    if "_" not in stem:
                        continue
                    pose = stem.rsplit("_", 1)[0]
                    try:
                        poses.setdefault(pose, []).append(
                            pygame.image.load(os.path.join(d, fn)).convert_alpha())
                    except Exception:
                        pass
            if poses:
                out[cid] = {"poses": poses, "meta": meta}
        return out

    def sprite_pose(self, f):
        if f.state == "charge":
            return "charge"
        if f.shielding:
            return "shield"
        if f.state == "hitstun":
            return "hit"
        if f.state == "shieldbreak":
            return "break"
        if f.state == "attack" and f.atk:
            return "attack_" + f.atk["kind"]
        if f.state == "special":
            return "special"
        if not f.on_ground:
            return "jump" if f.vy < 0 else "fall"
        if abs(f.vx) > 60:
            return "run"
        return "idle"

    def load_stage_art(self, base=None, manifest="stages.json"):
        """Load external stage paintings: assets/stages/<file>.png per stages.json.
        Missing files fall back to procedural backgrounds automatically.
        Optional <stem>_mid.png (transparent) draws as a parallax mid layer."""
        out = {}
        if base is None:
            base = os.path.join(asset_base(), "stages")
        mp = os.path.join(asset_base(), manifest)
        try:
            with open(mp) as fh:
                mapping = json.load(fh)
        except Exception:
            return out
        for stage, fn in mapping.items():
            p = os.path.join(base, fn)
            if not os.path.isfile(p):
                continue
            try:
                bg = pygame.image.load(p).convert()
            except Exception:
                continue
            stem, _ = os.path.splitext(fn)
            mid = None
            for ext in (".png", ".jpg", ".jpeg"):
                q = os.path.join(base, stem + "_mid" + ext)
                if os.path.isfile(q):
                    try:
                        mid = pygame.image.load(q).convert_alpha()
                    except Exception:
                        mid = None
                    break
            out[stage] = {"bg": bg, "mid": mid}
        return out

    def draw_stage_art(self, idx):
        """Cover-fit stage painting with slight parallax. Returns True if drawn."""
        art = self.stage_art.get(STAGES[idx]["name"])
        if not art:
            return False
        sw = STAGES[idx].get("w", W)
        cam_max = max(1, sw - W)
        for surf, par, alpha in ((art["bg"], 0.06, 255), (art["mid"], 0.15, 255)):
            if surf is None:
                continue
            iw, ih = surf.get_size()
            need_w = W + 240 + cam_max * par
            s = max(need_w / max(1, iw), H / max(1, ih))
            dw, dh = max(1, int(iw * s)), max(1, int(ih * s))
            try:
                img = pygame.transform.smoothscale(surf, (dw, dh))
            except Exception:
                continue
            x = int(-120 - self.cam * par)
            x = max(W - dw, min(-100, x))
            self.screen.blit(img, (x, int((H - dh) // 2)))
        return True

    def do_title_action(self, a):
        if a == "fight":
            self.net_stop()
            self.goto_select()
        elif a == "help":
            self.state = "help"
        elif a == "online":
            self.state = "online"
            self.menu_idx = 0
        elif a == "quit":
            self.quit_req = True

    # ================= 3D FIGHTER RENDERER (low-poly rigs, yawed camera) =================
    def render_fighter_3d(self, f, yaw_override=None):
        """Render the fighter as a flat-shaded low-poly 3D rig to a 160x160
        surface, feet anchored at (80, 146). Poses drive joint targets; limbs,
        torso, head, helms and weapons are boxes with depth under a yawed
        camera with directional lighting."""
        S = 160
        surf = pygame.Surface((S, S), pygame.SRCALPHA)
        sk = f.d["skin"]
        fl = f.facing
        c = f.cid
        big = f.cid in ("bulwark", "null", "tecton")
        B = 1.18 if big else 1.0
        ox, oy = S // 2, 146
        dark = sk["dark"]
        trim = sk["trim"]
        main_c = (150, 150, 160) if f.helpless else sk["main"]
        lite = mix(main_c, (255, 255, 255), 0.35)
        t = self.t_global + f.anim
        # ---------- pose decode ----------
        running = abs(f.vx) > 60 and f.on_ground and f.state in ("free", "attack")
        air = not f.on_ground
        crouch = 0.0
        if f.state == "charge":
            crouch = 0.45 + 0.55 * (f.charge / 0.9)
        elif f.shielding:
            crouch = 0.5
        elif f.state == "shieldbreak":
            crouch = 0.85
        kind, md, prog, segm = None, None, 0.0, ""
        if f.atk and f.state in ("attack", "special"):
            kind, md = f.atk["kind"], f.atk["md"]
            tt = f.atk["t"]
            prog = clamp(tt / max(0.01, f.atk["dur"]), 0.0, 1.0)
            segm = "wind" if tt < md["startup"] else ("hit" if tt < md["startup"] + md["active"] else "rec")
        lean = clamp(f.vx / 1600.0, -0.3, 0.3)
        lunge = 0.0
        armx, army = 10.0, -32.0
        backx, backy = -9.0, -24.0
        tucked = sprawl = arms_up = crossed = cast = droop = False
        leg_pose = "idle"
        if kind in ("jab", "ftilt", "smash", "utilt") and f.state == "attack":
            tt = f.atk["t"]
            if segm == "wind":
                e = -0.45 * (tt / max(0.01, md["startup"]))
            elif segm == "hit":
                e = -0.45 + 1.45 * ease_out((tt - md["startup"]) / max(0.01, md["active"]))
            else:
                e = max(0.0, 1.0 - (tt - md["startup"] - md["active"]) / max(0.01, md["recover"]))
            if kind == "utilt":
                armx, army = 6 + 5 * e, -32 - 24 * e
            else:
                reach = 20 if kind == "jab" else (26 if kind == "ftilt" else 30)
                armx = 10 + reach * e
                army = -32 - (5 * e if kind == "smash" else 0)
                lean += (0.05 if kind == "jab" else 0.12 if kind == "ftilt" else 0.24) * e
                lunge = (8 if kind == "smash" else 3) * max(0.0, e)
                if kind == "smash" and segm == "wind":
                    crouch = 0.65
            leg_pose = "brace" if kind == "smash" else "step"
        elif kind in ("nair", "uair", "upb"):
            tucked = True
            leg_pose = "tuck"
        elif f.state == "special":
            if f.counter > 0:
                crossed = True
            elif f.armor > 0:
                crouch = max(crouch, 0.55)
                armx, army = 14.0, -24.0
                backx, backy = -14.0, -24.0
            else:
                armx, army = 27.0, -36.0
                cast = True
        elif f.shielding:
            crossed = True
        elif f.state == "hitstun":
            sprawl = True
            leg_pose = "sprawl"
        elif f.helpless:
            arms_up = True
            leg_pose = "dangle"
        elif f.state == "shieldbreak":
            droop = True
            leg_pose = "sit"
        elif air:
            leg_pose = "rise" if f.vy < -50 else "fall"
        elif running:
            leg_pose = "run"
        elif f.skid > 0:
            leg_pose = "skid"
        hipx = lunge * 0.3
        hipy = -20 * B + crouch * 8
        shx = hipx + lean * 26 + lunge * 0.5
        shy = hipy - 22 * B + crouch * 2
        # ---------- tiny software 3D core (strong yaw so volume reads) ----------
        yaw = 0.42 if yaw_override is None else yaw_override
        if yaw_override is None:
            yaw += math.sin(t * 1.3) * 0.05
            if f.state == "charge":
                yaw += 0.55 * (f.charge / 0.9)
            elif kind in ("jab", "ftilt", "smash") and f.state == "attack":
                yaw += 0.30 if segm == "wind" else (-0.20 if segm == "hit" else 0.0)
            elif f.state == "hitstun":
                yaw += math.sin(math.radians(f.rot)) * 0.45
            if f.dash_t > 0:
                yaw += 0.15
        ca, sa = math.cos(yaw), math.sin(yaw)
        ll = math.sqrt(0.60 ** 2 + 0.60 ** 2 + 0.50 ** 2)
        lx, ly, lz = 0.60 / ll, -0.60 / ll, 0.50 / ll
        FACES = []

        def proj(x, y, z):
            x *= fl
            z *= 1.3
            xr = x * ca + z * sa
            zr = -x * sa + z * ca
            s = 1.0 / (1.0 - zr * 0.0011)
            return (ox + xr * s, oy + y * s, zr)

        def shade(col, nx, ny, nz, emissive=False):
            if emissive:
                return (min(255, int(col[0] * 1.3) + 20), min(255, int(col[1] * 1.3) + 20),
                        min(255, int(col[2] * 1.3) + 20))
            nx *= fl
            rx = nx * ca + nz * sa
            rz = -nx * sa + nz * ca
            b = 0.45 + 0.55 * max(0.0, rx * lx + ny * ly + rz * lz)
            return (min(255, int(col[0] * b)), min(255, int(col[1] * b)), min(255, int(col[2] * b)))

        def emit(pts, n, col, emissive=False):
            q = [proj(*p) for p in pts]
            FACES.append((q, shade(col, n[0], n[1], n[2], emissive), (q[0][2] + q[1][2] + q[2][2] + q[3][2]) / 4))

        def obox(center, ax, aw, ay, ah, az, ad, col, emissive=False):
            cx, cy, cz = center

            def P(sx, sy, sz):
                return (cx + ax[0] * sx * aw + ay[0] * sy * ah + az[0] * sz * ad,
                        cy + ax[1] * sx * aw + ay[1] * sy * ah + az[1] * sz * ad,
                        cz + ax[2] * sx * aw + ay[2] * sy * ah + az[2] * sz * ad)

            C = [P(-1, -1, -1), P(1, -1, -1), P(-1, 1, -1), P(1, 1, -1),
                 P(-1, -1, 1), P(1, -1, 1), P(-1, 1, 1), P(1, 1, 1)]

            def wn(n):
                return (n[0] * ax[0] + n[1] * ay[0] + n[2] * az[0],
                        n[0] * ax[1] + n[1] * ay[1] + n[2] * az[1],
                        n[0] * ax[2] + n[1] * ay[2] + n[2] * az[2])

            for n, idx in (((1, 0, 0), (1, 3, 7, 5)), ((-1, 0, 0), (0, 4, 6, 2)),
                           ((0, 1, 0), (2, 3, 7, 6)), ((0, -1, 0), (0, 1, 5, 4)),
                           ((0, 0, 1), (4, 5, 7, 6)), ((0, 0, -1), (0, 2, 3, 1))):
                emit([C[i] for i in idx], wn(n), col, emissive)

        def box(cx, cy, cz, sx, sy, sz, col, emissive=False):
            obox((cx, cy, cz), (1, 0, 0), sx / 2, (0, 1, 0), sy / 2, (0, 0, 1), sz / 2, col, emissive)

        def limb(p0, p1, w, col, t=0.9):
            dx, dy, dz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
            L = max(0.001, math.sqrt(dx * dx + dy * dy + dz * dz))
            u = (dx / L, dy / L, dz / L)
            tmp = (0, 0, 1) if abs(u[2]) < 0.9 else (0, 1, 0)
            n1 = (u[1] * tmp[2] - u[2] * tmp[1], u[2] * tmp[0] - u[0] * tmp[2], u[0] * tmp[1] - u[1] * tmp[0])
            nl = max(0.001, math.sqrt(n1[0] ** 2 + n1[1] ** 2 + n1[2] ** 2))
            n1 = (n1[0] / nl, n1[1] / nl, n1[2] / nl)
            n2 = (u[1] * n1[2] - u[2] * n1[1], u[2] * n1[0] - u[0] * n1[2], u[0] * n1[1] - u[1] * n1[0])
            mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2)
            obox(mid, u, L / 2, n1, w / 2, n2, w / 2 * t, col)

        # ---------- legs ----------
        def leg_to(ftx, fty, bend, boot=(25, 25, 32)):
            mx, my = (hipx + ftx) / 2 + bend, (hipy + fty) / 2
            hip = (hipx, hipy, 0)
            knee = (mx, my, 1)
            foot = (ftx, fty, 0)
            limb(hip, knee, 7, main_c)
            limb(knee, foot, 6, dark)
            box(ftx, fty + 2, 0, 10, 5, 9, boot)

        if leg_pose == "run":
            ph = f.step_ph
            leg_to(math.sin(ph) * 11, -max(0.0, math.cos(ph)) * 7, 5)
            leg_to(math.sin(ph + math.pi) * 11, -max(0.0, -math.cos(ph)) * 7, 5)
        elif leg_pose == "rise":
            leg_to(-6, -11, 6)
            leg_to(9, -6, 6)
        elif leg_pose == "fall":
            leg_to(-11, -2, 3)
            leg_to(11, -5, 3)
        elif leg_pose == "tuck":
            leg_to(-6, -12, 7)
            leg_to(7, -12, 7)
        elif leg_pose == "sprawl":
            leg_to(-14, -6, 2)
            leg_to(14, -10, 2)
        elif leg_pose == "sit":
            leg_to(-13, -3, 6)
            leg_to(13, -3, 6)
        elif leg_pose == "dangle":
            sw = math.sin(t * 9) * 3
            leg_to(-6 + sw, -2, 3)
            leg_to(7 - sw, -2, 3)
        elif leg_pose == "skid":
            leg_to(16, 0, 2)
            leg_to(-8, -5, 6)
        elif leg_pose == "brace":
            leg_to(-13, -1, 7)
            leg_to(13, -1, 7)
        elif leg_pose == "step":
            leg_to(-8, 0, 4)
            leg_to(12, -1, 4)
        else:
            sw = math.sin(t * 2.2) * 1.2
            leg_to(-7 + sw * 0.3, 0, 3)
            leg_to(7 - sw * 0.3, 0, 3)
        # ---------- torso ----------
        hw = 11 * B
        box(hipx, (hipy + shy) / 2, 0, hw * 2, hipy - shy, 15, main_c)
        box(shx, shy + 5, 1.5, hw * 1.7, 13, 15.5, lite)
        box(hipx, hipy - 3, 0, hw * 2 + 3, 4, 16, trim)
        if f.cid == "bulwark":
            box(shx - hw - 4, shy + 2, 0, 12, 12, 14, dark)
            box(shx + hw + 4, shy + 2, 0, 12, 12, 14, dark)
        if f.cid == "null":
            box(shx - 4, shy + 18, -9, 22, 34, 3, (120, 20, 30))
        if f.cid == "disc":
            box(shx - 10, shy, -8, 8, 22, 6, (90, 65, 40))
            for i in (-1, 0, 1):
                limb((shx - 13, shy - 10 + i * 3, -8), (shx - 13, shy - 22 + i * 3, -8), 2, (200, 220, 235))
        # ---------- arms ----------
        def arm_to(hx, hy, z, col=None, w=6):
            ex, ey = (shx + hx) / 2, (shy + hy) / 2 + 3
            limb((shx, shy, z), (ex, ey, z), w, col or main_c)
            limb((ex, ey, z), (hx, hy, z), w - 1, col or main_c)
            box(hx, hy, z, 7, 6, 7, trim)

        show_weapon, whx, why = True, armx + lunge, army
        if tucked:
            arm_to(3, -30, 4)
            arm_to(-3, -28, -4, dark, 5)
            whx, why = 14, -28
        elif sprawl:
            arm_to(20, -44, 4)
            arm_to(-18, -38, -4, dark, 5)
            whx, why = 20, -44
        elif arms_up:
            sw = math.sin(t * 9) * 3
            arm_to(12 + sw, -52, 4)
            arm_to(-10 - sw, -52, -4, dark, 5)
            whx, why = 12 + sw, -52
        elif crossed:
            limb((shx, shy, 3), (-7, -30, 5), 6, main_c)
            limb((shx, shy, -3), (7, -26, 5), 6, dark)
            box(-7, -30, 5, 6, 5, 6, trim)
            box(7, -26, 5, 6, 5, 6, trim)
            show_weapon = False
        elif droop:
            arm_to(8, -12, 3)
            arm_to(-8, -12, -3, dark, 5)
            whx, why = 8, -12
        elif cast:
            arm_to(armx, army, 5)
            arm_to(-10, -24, -5, dark, 5)
            show_weapon = False
            pulse = 5 + 2 * math.sin(t * 14)
            box(armx + 5, army, 6, int(pulse) + 3, int(pulse) + 3, int(pulse) + 3, sk["glow"], True)
            box(armx + 5, army, 6, 3, 3, 3, (255, 255, 255), True)
        elif running and not kind:
            ph = f.step_ph
            arm_to(10 + math.sin(ph + math.pi) * 9, -30, 5)
            arm_to(-9 + math.sin(ph) * 9, -24, -5, dark, 5)
            whx, why = 10 + math.sin(ph + math.pi) * 9 + lunge, -30
        elif leg_pose == "rise":
            arm_to(14, -44, 4)
            arm_to(-12, -38, -4, dark, 5)
            whx, why = 14, -44
        elif leg_pose == "fall":
            arm_to(20, -30, 4)
            arm_to(-20, -30, -4, dark, 5)
            whx, why = 20, -30
        else:
            sway = math.sin(t * 2.2) * 1.5
            arm_to(armx + lunge + (0 if kind else sway), army, 5)
            arm_to(backx - (0 if kind else sway), backy, -5, dark, 5)
            whx, why = armx + lunge + (0 if kind else sway), army
        if f.cid == "arc":
            for i in (0, 1):
                wy = math.sin(t * 12 + i * 1.7) * 4
                limb((shx - 8, shy + 2 + i * 4, -4), (shx - 20, shy + 8 + i * 4 + wy, -4), 2, trim)
        if f.cid == "glass":
            wy = math.sin(t * 5) * 3
            limb((shx - 10, shy + 4, -5), (shx - 24, shy + 12 + wy, -5), 3, trim)
        # ---------- weapons (boxes at the hand) ----------
        if show_weapon:
            if c == "cinder":
                box(whx + 7, why - 4, 9, 5, 9, 5, (90, 60, 40))
                box(whx + 22, why - 9, 9, 26, 4, 3, lite)
            elif c == "disc":
                box(whx, why, 9, 5, 12, 5, (120, 90, 60))
                box(whx + 2, why - 12, 9, 3, 14, 3, lite)
                box(whx + 2, why + 12, 9, 3, 14, 3, lite)
            elif c == "arc":
                box(whx, why, 9, 10, 9, 10, (80, 70, 60))
            elif c == "bulwark":
                box(whx + 5, why - 10, 9, 6, 20, 6, (90, 70, 50))
                box(whx + 5, why - 32, 9, 26, 20, 20, (120, 120, 140))
            elif c == "glass":
                box(whx + 12, why - 3, 9, 24, 3, 3, lite)
            elif c == "null":
                box(whx + 10, why - 4, 9, 14, 14, 14, (40, 10, 20))
                box(whx + 10, why - 4, 9, 8, 8, 8, sk["glow"], True)
            elif c == "blink":
                box(whx + 7, why - 4, 9, 5, 9, 5, (60, 60, 70))
                box(whx + 24, why - 12, 9, 30, 3, 3, lite)
            elif c == "tecton":
                box(whx + 5, why - 10, 9, 6, 20, 6, (80, 55, 35))
                box(whx + 5, why - 34, 9, 28, 22, 24, (110, 80, 55))
            elif c == "echo":
                box(whx + 8, why - 4, 9, 22, 12, 12, (70, 90, 140))
                box(whx + 20, why - 2, 9, 5, 5, 5, sk["glow"], True)
            elif c == "leech":
                box(whx + 10, why - 8, 9, 20, 3, 3, lite)
                box(whx + 10, why + 2, 9, 20, 3, 3, lite)
            else:
                box(whx + 10, why - 4, 9, 14, 14, 14, (40, 10, 20))
        # ---------- head ----------
        hx = shx + lean * 22 + lunge * 0.4
        hy = shy - 11 - (2 if crouch > 0.5 else 0)
        r = 12 if big else 11
        box(hx, hy, 0, r * 1.9, r * 2, r * 2.0, main_c)
        box(hx, hy - r * 0.4, 1, r * 1.5, r * 0.8, r * 1.8, lite)
        if c == "cinder":
            box(hx, hy - 8, 0, 23, 5, 19, trim)
            box(hx, hy - 18, -2, 4, 14, 4, (255, 90, 60))
        elif c == "disc":
            box(hx, hy - 6, -5, 24, 14, 12, dark)
            box(hx + 2, hy - 12, 6, 4, 4, 4, sk["glow"], True)
        elif c == "arc":
            box(hx, hy - 4, 0, 23, 4, 19, dark)
            box(hx - 4, hy - 14, 0, 2, 12, 2, trim)
            box(hx - 4, hy - 21, 0, 4, 4, 4, sk["glow"], True)
        elif c == "bulwark":
            box(hx, hy - 10, 0, 25, 9, 21, dark)
            box(hx, hy - 17, 0, 4, 8, 16, trim)
        elif c == "glass":
            box(hx, hy - 3, 0, 23, 6, 19, dark)
            box(hx, hy - 14, 0, 4, 12, 5, trim)
        elif c == "null":
            for ox2 in (-8, 0, 8):
                box(hx + ox2, hy - 16, 0, 5, 10, 5, trim)
        elif c == "blink":
            box(hx, hy - 8, 0, 23, 6, 19, dark)
            box(hx - 12, hy - 4, -6, 8, 4, 4, trim)
        elif c == "tecton":
            box(hx, hy - 11, 0, 25, 9, 21, dark)
            box(hx, hy - 18, 0, 16, 5, 5, trim)
        elif c == "echo":
            box(hx, hy - 4, 0, 23, 7, 19, dark)
            box(hx, hy - 4, 8, 14, 2, 2, sk["glow"], True)
            box(hx + 6, hy - 14, 0, 2, 10, 2, trim)
            box(hx + 6, hy - 20, 0, 4, 4, 4, (255, 255, 220), True)
        elif c == "leech":
            box(hx - 8, hy - 10, 0, 7, 10, 7, dark)
            box(hx + 8, hy - 10, 0, 7, 10, 7, dark)
            box(hx + 3, hy - 12, 6, 5, 5, 5, trim)
        else:
            for ox2 in (-8, 0, 8):
                box(hx + ox2, hy - 16, 0, 5, 10, 5, trim)
        # eyes (front of head)
        if f.state == "shieldbreak":
            box(hx + 1, hy - 1, r * 0.85, 6, 5, 2, (15, 15, 20))
            box(hx + 8, hy - 1, r * 0.85, 6, 5, 2, (15, 15, 20))
        elif (t * 0.9) % 3.4 < 0.12:
            box(hx + 4, hy - 1, r * 0.85, 11, 2, 2, (15, 15, 20))
        else:
            for exx in (hx + 1, hx + 8):
                box(exx, hy - 1, r * 0.85, 5, 6, 2, (255, 255, 255))
                box(exx + 1.5, hy - 1, r * 0.85 + 1, 2, 3, 1, (15, 15, 20))
        if f.helpless:
            box(hx - 13, hy - 8 + ((t * 40) % 12), 4, 3, 3, 3, (150, 210, 255))
        FACES.sort(key=lambda e: e[2])
        for q, col, _ in FACES:
            pygame.draw.polygon(surf, col, [(p[0], p[1]) for p in q])
        return surf

    def silhouette(self, surf, color, alpha):
        m = pygame.mask.from_surface(surf)
        s = m.to_surface(setcolor=(color[0], color[1], color[2], 255),
                         unsetcolor=(0, 0, 0, 0))
        s.set_alpha(max(0, min(255, int(alpha))))
        return s

    def draw_fighter(self, f, shake_x=0, shake_y=0):
        if f.state == "dead":
            return
        if f.invuln > 0 and f.state == "respawn" and int(self.t_global * 12) % 2 == 0:
            return
        s = self.screen
        L = self.glow_layer
        sk = f.d["skin"]
        x, y = f.x + shake_x, f.y + shake_y
        # blob shadow
        st = STAGES[self.stage_idx]
        gy = None
        for pl in [st["main"]] + st["plats"]:
            if pl["x"] - 10 <= f.x <= pl["x"] + pl["w"] + 10 and pl["y"] >= f.y - 4:
                gy = pl["y"] if gy is None else min(gy, pl["y"])
        if gy is not None and gy - f.y < 220:
            sc = max(0.3, 1 - (gy - f.y) / 260)
            for si, sa in ((1.35, 36), (1.0, 55), (0.68, 65)):
                pygame.draw.ellipse(L, (0, 0, 0, sa),
                                    (x - 20 * sc * si, gy - 4, 40 * sc * si, 8))
        # motion trail ghosts (dash + high speed)
        spd = math.hypot(f.vx, f.vy)
        if f.dash_t > 0 or spd > 520:
            f.after_t -= 1
            if f.after_t <= 0:
                f.after_t = 2
                if len(f.after) > 10:
                    f.after.pop(0)
                f.after.append({"surf": self.render_fighter_3d(f), "x": f.x, "y": f.y,
                                "life": 0.22, "max": 0.22})
        for gh in f.after:
            a = 150 * max(0.0, gh["life"] / gh["max"])
            gs = self.silhouette(gh["surf"], sk["glow"], a)
            s.blit(gs, (gh["x"] + shake_x - gs.get_width() // 2,
                        gh["y"] + shake_y - 26 - gs.get_height() // 2))
        # main body: external 3D sprite pack if supplied, else procedural 3D rig
        body = None
        sp = self.sprites.get(f.cid)
        if sp:
            frames = sp["poses"].get(self.sprite_pose(f)) or sp["poses"].get("idle")
            if frames:
                body = frames[int(self.t_global * sp["meta"].get("fps", 10) + f.anim) % len(frames)]
        if body is None:
            body = self.render_fighter_3d(f)
        if f.flash > 0:
            a = 230 * min(1.0, f.flash / 0.14)
            body = body.copy()
            body.blit(self.silhouette(body, (255, 255, 255), a), (0, 0))
        sx, sy = f.sx, f.sy
        if f.state == "free" and f.on_ground and abs(f.vx) < 60:
            sy *= 1.0 + 0.015 * math.sin(self.t_global * 4 + f.anim)
        if f.state == "charge":
            x += random.uniform(-1, 1) * (1 + f.charge * 7)
            y += random.uniform(-1, 1) * (1 + f.charge * 5)
        w0, h0 = max(1, int(160 * sx)), max(1, int(160 * sy))
        scaled = pygame.transform.scale(body, (w0, h0)) if (w0, h0) != (160, 160) else body
        rz = pygame.transform.rotate(scaled, f.rot) if f.rot % 360 != 0 else scaled
        if f.spawn_fx > 0:
            try:
                rz.set_alpha(int(120 + 135 * (1 - f.spawn_fx / 0.5)))
            except Exception:
                pass
            if random.random() < 0.5 and len(self.parts) < 240:
                self.glowpuff(x + random.uniform(-14, 14), y - random.uniform(0, 50),
                              sk["glow"], 1, 60, 0.4, 5)
        s.blit(rz, (int(x - rz.get_width() // 2), int(y - 26 - rz.get_height() // 2)))
        head_y = y - 52
        # speed streaks on huge launches
        if f.streak > 0 and (abs(f.vx) + abs(f.vy) > 300):
            sp = math.hypot(f.vx, f.vy)
            dxn = -f.vx / max(1, sp)
            for i in range(3):
                yy = y - 18 - i * 11
                ln = min(120, sp * 0.09)
                pygame.draw.line(s, (255, 255, 255),
                                 (x + dxn * 14, yy), (x + dxn * (14 + ln), yy), 2)
        # team ring + CPU marker
        is_p1 = self.fighters and self.fighters[0] is f
        pygame.draw.arc(s, (90, 160, 255) if is_p1 else (255, 110, 110),
                        (x - 16, y - 4, 32, 8), 0, 6.29, 2)
        if not is_p1:
            bob = math.sin(self.t_global * 5) * 3
            pygame.draw.polygon(s, (255, 90, 90),
                                [(x, head_y - 30 + bob), (x - 7, head_y - 40 + bob), (x + 7, head_y - 40 + bob)])
        # charge aura
        if f.state == "charge":
            r = 20 + f.charge * 45
            pygame.draw.circle(L, (*sk["glow"], 150), (int(x), int(y - 28)), int(r), 3)
            pygame.draw.circle(L, (255, 255, 255, 170), (int(x), int(y - 28)), int(r * 0.6), 2)
            if f.charge >= 0.85:
                r2 = int(r + 6 * math.sin(self.t_global * 20))
                pygame.draw.circle(L, (255, 255, 255, 200), (int(x), int(y - 28)), r2, 2)
            self.blit_add(x, y - 28, r, sk["glow"], 70)
        if f.counter > 0:
            pygame.draw.circle(L, (255, 255, 255, 160), (int(x), int(y - 28)), 26, 2)
            ga = self.t_global * 10
            for k in range(4):
                a = ga + k * math.pi / 2
                pygame.draw.line(s, (255, 255, 255),
                                 (x + math.cos(a) * 8, y - 28 + math.sin(a) * 8),
                                 (x + math.cos(a) * 20, y - 28 + math.sin(a) * 20), 2)
        if f.armor > 0:
            pr = 30 + 2 * math.sin(self.t_global * 8)
            pygame.draw.circle(s, (200, 170, 120), (int(x), int(y - 26)), int(pr), 3)
        if f.hammer_t > 0:
            hr = 32 + 2 * math.sin(self.t_global * 10)
            pygame.draw.circle(s, (255, 190, 100), (int(x), int(y - 26)), int(hr), 3)
        if f.star_t > 0:
            rainbow = (int(180 + 75 * math.sin(self.t_global * 7)),
                       int(180 + 75 * math.sin(self.t_global * 7 + 2.1)),
                       int(180 + 75 * math.sin(self.t_global * 7 + 4.2)))
            pygame.draw.circle(s, rainbow, (int(x), int(y - 26)), 34, 3)
        if f.ult >= 100:
            ur = 37 + 3 * math.sin(self.t_global * 8)
            pygame.draw.circle(L, (255, 210, 120, 170), (int(x), int(y - 26)), int(ur), 3)
        if f.fuse > 0:
            fa = self.t_global * 20
            for kk in range(4):
                a = fa + kk * math.pi / 2
                pygame.draw.line(s, (255, 200, 100),
                                 (x + math.cos(a) * 5, y - 64 + math.sin(a) * 5),
                                 (x + math.cos(a) * 11, y - 64 + math.sin(a) * 11), 2)
        if f.cid == "arc" and f.static > 0:
            for i in range(f.static):
                a = self.t_global * 8 + i * 2.1
                pygame.draw.circle(s, (255, 245, 150),
                                   (int(x + math.cos(a) * 22), int(y - 52 + math.sin(a) * 7)), 3)
        if f.burn > 0:
            fl2 = math.sin(self.t_global * 30) * 3
            pygame.draw.polygon(s, (255, 140, 40),
                                [(x - 7, head_y - 12), (x + fl2, head_y - 28), (x + 7, head_y - 12)])
            pygame.draw.polygon(s, (255, 230, 150),
                                [(x - 3, head_y - 12), (x + fl2, head_y - 21), (x + 3, head_y - 12)])
        if f.shielding:
            wob = 1 + 0.07 * math.sin(self.t_global * 30) * max(0.3, f.shield_wob * 3)
            r = (30 + f.shield_hp * 0.12) * wob
            low = f.shield_hp < 12
            sh = pygame.Surface((int(r * 2 + 8), int(r * 2 + 8)), pygame.SRCALPHA)
            c = (255, 120, 120, 130) if low else (120, 200, 255, 110)
            pygame.draw.circle(sh, c, (int(r + 4), int(r + 4)), int(r))
            pygame.draw.circle(sh, (255, 255, 255, 210), (int(r + 4), int(r + 4)), int(r), 2)
            pygame.draw.arc(sh, (255, 255, 255, 220), (8, 8, r, r),
                            2.4 + self.t_global * 2, 4.2 + self.t_global * 2, 3)
            s.blit(sh, (x - r - 4, y - 28 - r - 4))
        nstars = 0
        if f.state == "shieldbreak":
            nstars = 3
        elif f.state == "hitstun" and abs(f.vx) + abs(f.vy) > 700:
            nstars = 3
        elif f.state == "hitstun":
            nstars = 2
        for i in range(nstars):
            a = self.t_global * (9 if f.state == "shieldbreak" else 6) + i * 2.1
            sx = x + math.cos(a) * 20
            sy2 = head_y - 16 + math.sin(a) * 6
            pygame.draw.circle(s, (255, 230, 120), (int(sx), int(sy2)), 3)

    def draw_icon(self, surf, cid, cx, cy, r):
        d = FIGHTERS[cid]
        pygame.draw.circle(surf, (12, 12, 18), (cx, cy), r + 3)
        pygame.draw.circle(surf, d["skin"]["main"], (cx, cy), r)
        pygame.draw.circle(surf, d["skin"]["dark"], (cx, cy - r // 3), r // 2)
        pygame.draw.circle(surf, (255, 255, 255), (cx - r // 3, cy - r // 4), max(2, r // 5))
        pygame.draw.circle(surf, (255, 255, 255), (cx + r // 3, cy - r // 4), max(2, r // 5))
        pygame.draw.arc(surf, d["skin"]["trim"], (cx - r, cy - r, r * 2, r * 2), 3.4, 6.0, 2)

    def draw_slashes(self, shx=0, shy=0):
        L = self.glow_layer
        for sl in self.slashes:
            p = 1 - sl.life / sl.max
            fade = 1 - p
            cx, cy = sl.x + shx, sl.y + shy
            if sl.spin:
                r = int(max(sl.rng, sl.hi) * (0.75 + 0.35 * p))
                pygame.draw.circle(L, (*sl.color, int(200 * fade)), (int(cx), int(cy)), r, 5)
                pygame.draw.circle(L, (255, 255, 255, int(160 * fade)), (int(cx), int(cy)), int(r * 0.65), 2)
                pygame.draw.circle(self.screen, (255, 255, 255), (int(cx), int(cy)), int(r * 0.65), 1)
            else:
                w = int(sl.rng * (0.7 + 0.5 * p))
                h = int(sl.hi)
                rect = pygame.Rect(int(cx - w / 2), int(cy - h / 2), w, h)
                if sl.facing > 0:
                    a0, a1 = -1.35, 1.25
                else:
                    a0, a1 = math.pi - 1.25, math.pi + 1.35
                pygame.draw.arc(L, (*sl.color, int(190 * fade)), rect, a0, a1, 7)
                pygame.draw.arc(L, (255, 255, 255, int(200 * fade)), rect, a0 + 0.15, a1 - 0.15, 3)
                pygame.draw.arc(self.screen, (255, 255, 255), rect, a0 + 0.15, a1 - 0.15, 1)
                ex = cx + sl.facing * w / 2 * math.cos(0.4)
                ey = cy + h / 2 * math.sin(0.4)
                pygame.draw.circle(L, (255, 255, 255, int(220 * fade)), (int(ex), int(ey)), 5)

    def draw_rings(self, shx=0, shy=0):
        L = self.glow_layer
        for rg in self.rings:
            a = max(0.0, rg.life / rg.max)
            pygame.draw.circle(L, (*rg.color, int(210 * a)),
                               (int(rg.x + shx), int(rg.y + shy)), int(rg.r), max(1, int(rg.width * a) + 1))
            pygame.draw.circle(L, (255, 255, 255, int(140 * a)),
                               (int(rg.x + shx), int(rg.y + shy)), int(rg.r * 0.7), 2)

    def draw_echoes(self, shx=0, shy=0):
        for f in self.fighters:
            if f.echo is None or not f.alive():
                continue
            ex, ey = f.echo[0] + shx, f.echo[1] + shy
            pulse = 0.6 + 0.4 * math.sin(self.t_global * 6)
            col = f.d["skin"]["glow"]
            pygame.draw.line(self.screen, col, (ex - 10, ey - 30), (ex + 10, ey - 30), 2)
            pygame.draw.polygon(self.screen, col,
                                [(ex, ey - 52 - 4 * pulse), (ex + 8, ey - 40),
                                 (ex, ey - 28 + 4 * pulse), (ex - 8, ey - 40)], 2)
            pygame.draw.circle(self.glow_layer, (*col, 80), (int(ex), int(ey - 40)), 14)

    def draw_drops(self, shx=0, shy=0):
        for d in self.drops:
            if d["life"] < 2 and int(self.t_global * 10) % 2 == 0:
                continue
            x = d["x"] + shx
            bob = math.sin(d["t"] * 4) * 5
            y = d["y"] - 16 + bob + shy
            info = DROPS[d["kind"]]
            pygame.draw.ellipse(self.screen, (0, 0, 0, 80), (x - 13, d["y"] + 2 + shy, 26, 7))
            pygame.draw.circle(self.glow_layer, (*info["color"], 90), (int(x), int(y)),
                               20 + int(3 * math.sin(d["t"] * 6)))
            k = d["kind"]
            if k == "star":
                pts = []
                for i in range(10):
                    a = -math.pi / 2 + i * math.pi / 5 + d["t"]
                    r = 13 if i % 2 == 0 else 6
                    pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
                pygame.draw.polygon(self.screen, (255, 220, 100), pts)
            elif k == "snack":
                pygame.draw.circle(self.screen, (255, 170, 190), (int(x), int(y)), 11)
                pygame.draw.circle(self.screen, (255, 220, 230), (int(x - 3), int(y - 3)), 4)
                pygame.draw.rect(self.screen, (150, 90, 60), (x - 11, y + 4, 22, 7), border_radius=3)
            elif k == "ult":
                pygame.draw.circle(self.screen, (40, 120, 180), (int(x), int(y)), 12)
                pygame.draw.circle(self.screen, (150, 220, 255), (int(x), int(y)), 8)
                u = self.font(11).render("U", True, (10, 30, 50))
                self.screen.blit(u, (x - u.get_width() // 2, y - u.get_height() // 2))
            elif k == "hammer":
                pygame.draw.line(self.screen, (120, 85, 50), (x - 6, y + 8), (x + 4, y - 8), 5)
                pygame.draw.rect(self.screen, (200, 200, 215), (x - 4, y - 20, 20, 14), border_radius=3)
            elif k == "bolt":
                pygame.draw.polygon(self.screen, (220, 170, 255),
                                    [(x + 3, y - 13), (x - 6, y + 1), (x - 1, y + 1), (x - 3, y + 13),
                                     (x + 6, y - 1), (x + 1, y - 1)])
            elif k == "slow":
                for a in (0, math.pi / 3, 2 * math.pi / 3):
                    pygame.draw.line(self.screen, (170, 235, 255),
                                     (x - math.cos(a) * 11, y - math.sin(a) * 11),
                                     (x + math.cos(a) * 11, y + math.sin(a) * 11), 3)
            else:  # bomb
                pygame.draw.circle(self.screen, (35, 35, 45), (int(x), int(y)), 12)
                pygame.draw.circle(self.screen, (90, 90, 110), (int(x - 3), int(y - 3)), 4)
                pygame.draw.line(self.screen, (150, 110, 70), (x + 8, y - 8), (x + 13, y - 15), 2)
                if int(self.t_global * 12) % 2 == 0:
                    pygame.draw.circle(self.screen, (255, 200, 100), (x + 13, y - 15), 3)

    # ================= DRAW =================
    def gradient(self, top, bot):
        for y in range(0, H, 4):
            t = y / H
            c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
            pygame.draw.rect(self.screen, c, (0, y, W, 4))

    def draw_cube(self, cx, cy, size, ang, col):
        """Solid shaded rotating cube (background 3D garnish)."""
        ca, sa = math.cos(ang), math.sin(ang)
        cb, sb = math.cos(ang * 0.7), math.sin(ang * 0.7)

        def rot(p):
            x, y, z = p
            x2 = x * ca + z * sa
            z2 = -x * sa + z * ca
            y2 = y * cb - z2 * sb
            z3 = y * sb + z2 * cb
            return (cx + x2, cy + y2, z3)

        s = size / 2
        C = [rot((sx * s, sy * s, sz * s)) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
        faces = [((0, 2, 6, 4), (0, 0, -1)), ((1, 3, 7, 5), (0, 0, 1)),
                 ((0, 1, 5, 4), (0, -1, 0)), ((2, 3, 7, 6), (0, 1, 0)),
                 ((0, 1, 3, 2), (-1, 0, 0)), ((4, 5, 7, 6), (1, 0, 0))]
        vis = []
        for ids, n in faces:
            rn = rot(n)
            if rn[2] > 0.1:
                vis.append((sum(C[i][2] for i in ids) / 4, ids, rn))
        vis.sort(key=lambda e: e[0])
        for _, ids, rn in vis:
            b = 0.4 + 0.6 * max(0.0, rn[0] * 0.5 + rn[1] * -0.6 + rn[2] * 0.62)
            pygame.draw.polygon(self.screen, (min(255, int(col[0] * b)), min(255, int(col[1] * b)),
                                              min(255, int(col[2] * b))),
                                [(C[i][0], C[i][1]) for i in ids])

    def draw_floor_grid(self, y0, col, vanish_x=None):
        """Perspective floor grid converging past the horizon."""
        vx = W // 2 if vanish_x is None else vanish_x
        for i in range(-8, 9):
            pygame.draw.line(self.screen, col, (vx, y0 - 60), (vx + i * 130, H), 1)
        for j in range(4):
            yy = y0 + j * j * 14
            pygame.draw.line(self.screen, col, (0, yy), (W, yy), 1)

    # ================= PER-STAGE BACKGROUNDS (18 unique arenas) =================
    def _bg_gear(self, cx, cy, r, ang, col, teeth=8, hole=True):
        for i in range(teeth):
            a = ang + i * 6.283 / teeth
            tx, ty = cx + math.cos(a) * r, cy + math.sin(a) * r
            pygame.draw.circle(self.screen, col, (int(tx), int(ty)), max(3, int(r * 0.22)))
        pygame.draw.circle(self.screen, col, (int(cx), int(cy)), int(r))
        if hole:
            pygame.draw.circle(self.screen, (12, 10, 12), (int(cx), int(cy)), max(3, int(r * 0.38)))

    def _bg_stars(self, camx, t, n, par=0.1, seed=0):
        for i in range(n):
            x = ((i * 137 + seed * 61 - (camx * par if i % 2 == 0 else 0)) % (W + 100)) - 50
            y = (i * 89 + seed * 37) % H
            tw = 0.4 + 0.6 * abs(math.sin(t * 1.5 + i * 1.3 + seed))
            c = int(120 + 120 * tw)
            pygame.draw.circle(self.screen, (c, c, min(255, c + 40)), (int(x), int(y)), 1 + (i % 2))

    def _bg_ember_arena(self, st, camx, fx, mx, t, L):
        pygame.draw.polygon(self.screen, (30, 8, 12), [(fx - 100, H), (fx + 140, 300), (fx + 380, H)])
        pygame.draw.polygon(self.screen, (26, 10, 16), [(fx + 560, H), (fx + 810, 330), (fx + 1060, H)])
        pygame.draw.polygon(self.screen, (255, 110, 40),
                            [(fx + 150, 300), (fx + 165, 268), (fx + 180, 300)])
        pygame.draw.circle(L, (255, 120, 50, 70), (int(fx + 165), 292), 26)
        pygame.draw.ellipse(L, (255, 110, 40, 60), (-40, H - 26, W + 80, 40))
        for i in range(3):
            sx = fx + 165 + math.sin(t * 0.7 + i * 2.1) * 26
            sy = 250 - ((t * 26 + i * 90) % 240)
            pygame.draw.circle(L, (90, 70, 70, 90), (int(sx), int(sy)), 16 + i * 5)
        # shattered obsidian arch + floating shards
        pygame.draw.arc(self.screen, (22, 10, 14), (mx + 330, 150, 300, 260), 0.2, 2.9, 14)
        pygame.draw.arc(self.screen, (255, 120, 50), (mx + 330, 150, 300, 260), 0.9, 1.6, 2)
        for i in range(4):
            sx = 180 + i * 200 - camx * 0.55 + math.sin(t * 0.6 + i * 2.0) * 18
            sy = 170 + (i % 2) * 70 + math.sin(t * 0.9 + i) * 10
            pygame.draw.polygon(self.screen, (45, 20, 18),
                                [(sx, sy - 9), (sx + 7, sy), (sx, sy + 9), (sx - 7, sy)])
        pygame.draw.polygon(self.screen, (38, 12, 14), [(mx - 200, H), (mx + 60, 380), (mx + 320, H)])
        pygame.draw.polygon(self.screen, (38, 12, 14), [(mx + 700, H), (mx + 980, 400), (mx + 1260, H)])
        pts = [(x, H - 14 + math.sin(x * 0.05 + t * 3) * 4) for x in range(-20, W + 20, 24)]
        pygame.draw.lines(self.screen, (255, 160, 70), False, pts, 2)
        self.draw_floor_grid(H - 6, (120, 50, 25))
        self.draw_cube(220 - camx * 0.4, 180 + math.sin(t * 0.8) * 10, 34, t * 0.5, (60, 25, 20))
        self.draw_cube(760 - camx * 0.4, 130 + math.cos(t * 0.6) * 12, 24, -t * 0.4, (80, 32, 22))
        if len(self.parts) < 110:
            for _ in range(2):
                self.parts.append(Particle(random.uniform(0, W), H + 6,
                                           random.uniform(-24, 24), random.uniform(-150, -50),
                                           random.uniform(1.2, 2.4),
                                           random.choice([(255, 140, 50), (255, 90, 40), (120, 110, 110)]),
                                           random.randint(2, 4), grav=-60, glow=True))

    def _bg_sky_battlefield(self, st, camx, fx, mx, t, L):
        sunx = int(800 - camx * 0.15)
        pygame.draw.circle(L, (255, 246, 200, 70), (sunx, 90), 64)
        pygame.draw.circle(self.screen, (255, 246, 200), (sunx, 90), 34)
        for ri in range(3):
            ang = 0.9 + ri * 0.35 + math.sin(t * 0.3) * 0.05
            pygame.draw.line(L, (255, 250, 220, 26), (sunx, 90),
                             (int(sunx + math.cos(ang) * 700), int(90 + math.sin(ang) * 700)), 34 - ri * 8)
        # floating ruin islands with waterfalls
        for i, (ix, iy, iw) in enumerate(((180, 150, 130), (560, 100, 90), (830, 190, 110))):
            bx = ix - camx * 0.3 + math.sin(t * 0.5 + i * 2.0) * 10
            by = iy + math.sin(t * 0.7 + i) * 6
            pygame.draw.ellipse(self.screen, (110, 150, 130), (bx - iw / 2, by - 14, iw, 26))
            pygame.draw.ellipse(self.screen, (150, 190, 150), (bx - iw / 2 + 8, by - 18, iw - 16, 18))
            pygame.draw.polygon(self.screen, (90, 115, 140),
                                [(bx - iw / 2 + 12, by + 8), (bx + iw / 2 - 12, by + 8), (bx, by + 52)])
            pygame.draw.line(self.screen, (200, 230, 245), (bx + iw / 4, by + 10), (bx + iw / 4, by + 90), 3)
            pygame.draw.rect(self.screen, (140, 150, 160), (bx - 10, by - 44, 20, 30))
        for layer in range(2):
            spd = 14 + layer * 12
            for i in range(4):
                x = (i * 300 + layer * 150 - t * spd - camx * (0.4 + 0.15 * layer)) % (W + 320) - 160
                y = 60 + layer * 90 + i * 38
                sc = 0.7 + layer * 0.5
                for ox2, s2 in ((0, 46), (38, 34), (-38, 32)):
                    pygame.draw.ellipse(self.screen, (196, 212, 232),
                                        (int(x + ox2 * sc - s2 * sc), int(y - s2 * sc // 2 + 10 * sc),
                                         int(s2 * 2 * sc), int(s2 * sc)))
                    pygame.draw.ellipse(self.screen, (255, 255, 255),
                                        (int(x + ox2 * sc - s2 * sc), int(y - s2 * sc // 2),
                                         int(s2 * 2 * sc), int(s2 * sc)))
        pygame.draw.polygon(self.screen, (70, 110, 150), [(mx - 200, H), (mx + 180, 340), (mx + 560, H)])
        pygame.draw.polygon(self.screen, (235, 245, 255), [(mx + 180, 340), (mx + 150, 372), (mx + 210, 372)])
        pygame.draw.polygon(self.screen, (60, 100, 140), [(mx + 620, H), (mx + 820, 360), (mx + 1160, H)])
        pygame.draw.polygon(self.screen, (240, 248, 255), [(mx + 820, 360), (mx + 796, 388), (mx + 844, 388)])
        for cxi in range(6):
            clx = cxi * 200 - 100 - camx * 0.2 + math.sin(t * 0.4 + cxi) * 12
            pygame.draw.ellipse(self.screen, (225, 235, 248), (clx - 90, 392, 180, 30))
            pygame.draw.ellipse(self.screen, (255, 255, 255), (clx - 70, 386, 140, 24))
        for i in range(2):
            bx = (t * (40 + i * 18) + i * 500) % (W + 100) - 50
            by = 130 + i * 60 + math.sin(t * 2 + i * 3) * 12
            pygame.draw.arc(self.screen, (40, 50, 70), (int(bx - 10), int(by - 4), 20, 10), 3.4, 6.0, 2)
        if len(self.parts) < 110 and random.random() < 0.25:
            self.parts.append(Particle(random.uniform(0, W), random.uniform(300, H),
                                       random.uniform(-40, -10), random.uniform(-16, -4),
                                       random.uniform(2.0, 3.5), (255, 255, 255), 2, grav=0, glow=True))

    def _bg_void_final(self, st, camx, fx, mx, t, L):
        for i, (nx, ny, nr, col) in enumerate(((240, 150, 150, (120, 60, 180)),
                                               (720, 380, 170, (60, 40, 140)),
                                               (500, 120, 110, (150, 60, 160)))):
            pygame.draw.circle(L, (*col, 46),
                               (int(nx - camx * 0.25 + math.sin(t * 0.3 + i * 2) * 20), int(ny)), nr)
        self._bg_stars(camx, t, 110, par=0.1)
        # twin monoliths + glowing runes
        for i, mox in enumerate((200, 700)):
            bx = mox - camx * 0.35
            pygame.draw.polygon(self.screen, (22, 14, 34),
                                [(bx - 34, H), (bx - 22, 190 + i * 30), (bx + 22, 190 + i * 30), (bx + 34, H)])
            for j in range(3):
                ry = 260 + j * 60 + i * 20
                on = int(t * 2 + i + j) % 2 == 0
                pygame.draw.circle(self.screen, (200, 130, 255) if on else (90, 60, 130),
                                   (int(bx), int(ry)), 4)
                pygame.draw.circle(L, (190, 130, 255, 60), (int(bx), int(ry)), 12)
        cx, cy = W // 2 - camx * 0.3, H // 2 - 20
        for r, al in ((150, 60), (200, 40), (250, 26)):
            pygame.draw.arc(self.screen, (150, 90, 220),
                            (cx - r, cy - r // 2, r * 2, r), 0.3 + t * 0.25, 2.6 + t * 0.25, 3)
            _ = al
        for i in range(5):
            sx = 120 + i * 180 - camx * 0.6 + math.sin(t * 0.5 + i * 1.9) * 24
            sy = 150 + (i % 3) * 90 + math.sin(t * 0.8 + i) * 14
            pygame.draw.polygon(self.screen, (90, 70, 130),
                                [(sx, sy - 10), (sx + 8, sy), (sx, sy + 10), (sx - 8, sy)])
            pygame.draw.line(self.screen, (180, 140, 230), (sx, sy - 10), (sx + 8, sy), 1)
        self.draw_floor_grid(H - 6, (50, 30, 80))
        self.draw_cube(300 - camx * 0.5, 200 + math.sin(t * 0.7) * 12, 30, t * 0.45, (90, 60, 140))
        self.draw_cube(660 - camx * 0.5, 150 + math.cos(t * 0.5) * 10, 22, -t * 0.55, (70, 45, 120))
        if len(self.parts) < 110 and random.random() < 0.5:
            self.parts.append(Particle(random.uniform(0, W), H + 6,
                                       random.uniform(-16, 16), random.uniform(-70, -25),
                                       random.uniform(1.5, 3.0), (190, 150, 255), 3, grav=-30, glow=True))

    def _bg_fungal_hollow(self, st, camx, fx, mx, t, L):
        fx2 = -camx * 0.3
        pygame.draw.ellipse(L, (60, 120, 90, 50), (W // 2 - 320, H - 160, 640, 170))
        for i, (mx2, mh, mr) in enumerate(((140, 260, 46), (700, 200, 60), (1050, 280, 40))):
            bx = fx2 + mx2 + math.sin(t * 0.4 + i) * 8
            pygame.draw.rect(self.screen, (50, 70, 60), (bx - 12, H - mh, 24, mh + 40))
            pygame.draw.rect(self.screen, (70, 95, 80), (bx - 12, H - mh, 8, mh + 40))
            pygame.draw.ellipse(self.screen, (120, 70, 150), (bx - mr, H - mh - 34, mr * 2, 44))
            pygame.draw.ellipse(self.screen, (150, 95, 175), (bx - mr, H - mh - 34, mr * 2, 18))
            for sxr in (-mr // 2, 0, mr // 2):
                pygame.draw.ellipse(self.screen, (225, 200, 235), (bx + sxr - 7, H - mh - 26, 14, 10))
            pygame.draw.circle(L, (190, 130, 230, 50), (int(bx), int(H - mh - 10)), mr)
        for i in range(7):
            bx = (i * 150 + 40 - camx * 0.5) % (W + 80) - 40
            pygame.draw.ellipse(self.screen, (130, 90, 160), (bx - 12, H - 42, 24, 16))
            pygame.draw.rect(self.screen, (60, 80, 66), (bx - 3, H - 32, 6, 14))
            pygame.draw.circle(L, (190, 160, 230, 40), (int(bx), int(H - 40)), 10)
        for i in range(4):
            vx = 120 + i * 220 - camx * 0.15
            sway = math.sin(t * 0.9 + i * 1.7) * 14
            pygame.draw.line(self.screen, (45, 90, 60), (vx, 0), (vx + sway, 150 + i * 22), 3)
            pygame.draw.circle(self.screen, (170, 255, 170), (int(vx + sway), int(150 + i * 22)), 4)
            pygame.draw.circle(L, (170, 255, 170, 70), (int(vx + sway), int(150 + i * 22)), 12)
        pygame.draw.ellipse(L, (150, 200, 170, 36), (0, H - 120, W, 60))
        if len(self.parts) < 110 and random.random() < 0.5:
            self.parts.append(Particle(random.uniform(0, W) + camx * 0.5, H + 6,
                                       random.uniform(-20, 20), random.uniform(-60, -20),
                                       random.uniform(1.5, 3.0), (190, 230, 160), 3, grav=-30, glow=True))

    def _bg_storm_spire(self, st, camx, fx, mx, t, L):
        # colossal spire + lit windows
        sx = 640 - camx * 0.3
        pygame.draw.polygon(self.screen, (36, 44, 66),
                            [(sx - 90, H), (sx - 46, 90), (sx + 46, 90), (sx + 90, H)])
        pygame.draw.polygon(self.screen, (30, 36, 56),
                            [(sx - 46, 90), (sx, 40), (sx + 46, 90)])
        pygame.draw.line(self.screen, (255, 240, 150), (sx, 40), (sx, 18), 2)
        pygame.draw.circle(L, (255, 240, 150, 80), (int(sx), 16), 10)
        for j in range(5):
            wy = 140 + j * 62
            on = int(t * 1.5 + j) % 2 == 0
            pygame.draw.rect(self.screen, (255, 235, 150) if on else (70, 80, 105),
                             (sx - 14, wy, 28, 10))
        for i in range(3):
            cx2 = 200 + i * 300 + math.sin(t * 0.5 + i * 2) * 30 - camx * 0.35
            pygame.draw.ellipse(self.screen, (70, 80, 110), (cx2 - 90, 60 + i * 40, 180, 44))
            pygame.draw.ellipse(self.screen, (50, 58, 86), (cx2 - 70, 74 + i * 40, 140, 30))
        # lightning bolt + flash
        if random.random() < 0.012:
            self.parts.append(Particle(random.uniform(100, W - 100), 0, 0, 0, 0.12,
                                       (255, 255, 255), 60, grav=0, glow=True))
            bx = random.uniform(120, W - 120)
            pts = [(bx, 0)]
            for k in range(1, 7):
                pts.append((bx + random.uniform(-36, 36), k * 60))
            pygame.draw.lines(self.screen, (240, 245, 255), False, pts, 3)
            pygame.draw.lines(L, (200, 210, 255, 90), False, pts, 7)
        for i in range(24):
            rx = (i * 173 + t * 900) % (W + 40) - 20
            ry = (i * 311 + t * 1400) % H
            pygame.draw.line(self.screen, (170, 190, 220), (rx, ry), (rx - 4, ry + 14), 1)
        if len(self.parts) < 110 and random.random() < 0.3:
            self.parts.append(Particle(random.uniform(0, W), -6,
                                       random.uniform(-60, -20), random.uniform(300, 420),
                                       0.8, (170, 190, 230), 2, grav=0))

    def _bg_tide_vault(self, st, camx, fx, mx, t, L):
        for ri in range(3):
            bx = 260 + ri * 220 - camx * 0.1
            pygame.draw.polygon(L, (140, 220, 255, 30),
                                [(bx, 0), (bx + 90, 0), (bx - 40, H), (bx - 130, H)])
        for i, (px, ph) in enumerate(((160, 300), (430, 220), (700, 330), (900, 200))):
            bx = px - camx * 0.3 + math.sin(t * 0.4 + i) * 6
            pygame.draw.rect(self.screen, (45, 95, 120), (bx - 18, H - ph, 36, ph))
            pygame.draw.rect(self.screen, (70, 135, 160), (bx - 18, H - ph, 36, 10))
            pygame.draw.rect(self.screen, (35, 75, 100), (bx - 24, H - ph - 12, 48, 14))
        pygame.draw.arc(self.screen, (45, 95, 120), (300 - camx * 0.3, 190, 320, 200), 0.1, 3.0, 18)
        pygame.draw.ellipse(self.screen, (190, 160, 110), (-60, H - 40, W + 120, 60))
        pygame.draw.ellipse(self.screen, (220, 190, 140), (-60, H - 40, W + 120, 22))
        for i in range(5):
            gx = 100 + i * 180 - camx * 0.4
            sway = math.sin(t * 1.4 + i * 2.2) * 16
            pygame.draw.line(self.screen, (60, 150, 120), (gx, H - 30), (gx + sway, H - 110 - i * 8), 4)
        if len(self.parts) < 120 and random.random() < 0.6:
            self.parts.append(Particle(random.uniform(0, W), H + 6,
                                       random.uniform(-14, 14), random.uniform(-90, -30),
                                       random.uniform(1.5, 3.2), (170, 225, 255), 3, grav=-40, glow=True))
        if len(self.parts) < 120 and random.random() < 0.25:
            self.parts.append(Particle(random.uniform(0, W), random.uniform(200, H),
                                       random.uniform(-10, 10), random.uniform(-20, -6),
                                       random.uniform(2.0, 4.0), (150, 255, 220), 2, grav=0, glow=True))

    def _bg_iron_foundry(self, st, camx, fx, mx, t, L):
        for i, stx in enumerate((240, 640)):
            bx = stx - camx * 0.3
            pygame.draw.rect(self.screen, (40, 30, 30), (bx - 26, 190, 52, H - 190))
            pygame.draw.rect(self.screen, (58, 44, 42), (bx - 26, 190, 52, 14))
            pygame.draw.rect(self.screen, (30, 22, 22), (bx - 34, 176, 68, 16))
            for k in range(2):
                sy = 150 - ((t * 30 + i * 80 + k * 60) % 160)
                pygame.draw.circle(L, (110, 95, 90, 80), (int(bx + math.sin(t + k) * 10), int(sy)), 14 + k * 4)
        self._bg_gear(480 - camx * 0.4, 330, 56, t * 0.5, (52, 44, 46))
        self._bg_gear(600 - camx * 0.4, 250, 34, -t * 0.8, (66, 56, 56))
        self._bg_gear(120 - camx * 0.4, 140, 26, t * 0.7, (52, 44, 46))
        for i in range(3):
            fx0 = 300 + i * 170 - camx * 0.2
            pygame.draw.rect(self.screen, (25, 14, 12), (fx0 - 40, H - 90, 80, 40))
            flick = 0.7 + 0.3 * math.sin(t * 9 + i * 2.4)
            pygame.draw.rect(self.screen, (255, int(130 * flick), 50), (fx0 - 30, H - 78, 60, 16))
            pygame.draw.circle(L, (255, 130, 50, 70), (int(fx0), int(H - 70)), 30)
        for i in range(4):
            chx = 140 + i * 220 - camx * 0.45 + math.sin(t * 0.8 + i) * 6
            pygame.draw.line(self.screen, (60, 58, 62), (chx, 0), (chx, 200 + (i % 2) * 60), 3)
            pygame.draw.circle(self.screen, (90, 88, 92), (int(chx), int(200 + (i % 2) * 60)), 6)
        pygame.draw.ellipse(L, (255, 120, 50, 46), (-40, H - 26, W + 80, 40))
        self.draw_floor_grid(H - 6, (110, 70, 50))
        if len(self.parts) < 110:
            for _ in range(2):
                self.parts.append(Particle(random.uniform(0, W), H - 40,
                                           random.uniform(-30, 30), random.uniform(-220, -80),
                                           random.uniform(0.6, 1.4),
                                           random.choice([(255, 170, 60), (255, 120, 50), (200, 200, 200)]),
                                           random.randint(2, 4), grav=-60, glow=True))

    def _bg_thorn_garden(self, st, camx, fx, mx, t, L):
        moonx = int(180 - camx * 0.1)
        pygame.draw.circle(L, (220, 170, 255, 60), (moonx, 110), 52)
        pygame.draw.circle(self.screen, (235, 220, 245), (moonx, 110), 30)
        for i in range(3):
            vx = 200 + i * 260 - camx * 0.3
            pygame.draw.arc(self.screen, (50, 90, 55), (vx - 120, 200 + i * 40, 240, 260),
                            0.4 + math.sin(t * 0.4 + i) * 0.1, 2.6, 10)
            pygame.draw.arc(self.screen, (70, 130, 75), (vx - 120, 200 + i * 40, 240, 260),
                            0.9 + math.sin(t * 0.4 + i) * 0.1, 1.9, 3)
            for th in range(5):
                a = 0.6 + th * 0.4 + math.sin(t * 0.4 + i) * 0.05
                tx = vx - 120 + 120 + math.cos(a) * 120
                tyy = 200 + i * 40 + 130 + math.sin(a) * 130
                pygame.draw.polygon(self.screen, (60, 100, 60),
                                    [(tx, tyy), (tx + 12, tyy - 8), (tx + 20, tyy + 2)])
            bx, by = vx + 60, 240 + i * 50 + math.sin(t * 0.8 + i * 2) * 6
            pygame.draw.circle(self.screen, (210, 130, 220), (int(bx), int(by)), 9)
            pygame.draw.circle(self.screen, (240, 190, 245), (int(bx), int(by)), 4)
            pygame.draw.circle(L, (220, 140, 230, 70), (int(bx), int(by)), 18)
        for cxi in range(8):
            gx = cxi * 130 - 40 - camx * 0.4
            pygame.draw.polygon(self.screen, (45, 85, 50), [(gx, H), (gx + 8, H - 34), (gx + 16, H)])
        if len(self.parts) < 110 and random.random() < 0.5:
            self.parts.append(Particle(random.uniform(0, W), random.uniform(100, H),
                                       random.uniform(-24, -6), random.uniform(-14, 6),
                                       random.uniform(2.0, 4.0), (230, 170, 230), 2, grav=0, glow=True))
        if len(self.parts) < 110 and random.random() < 0.3:
            self.parts.append(Particle(random.uniform(0, W), random.uniform(150, H),
                                       random.uniform(-12, 12), random.uniform(-18, 18),
                                       random.uniform(1.5, 3.0), (200, 255, 170), 2, grav=0, glow=True))

    def _bg_glacier(self, st, camx, fx, mx, t, L):
        moonx = int(760 - camx * 0.12)
        pygame.draw.circle(L, (220, 240, 255, 70), (moonx, 100), 56)
        pygame.draw.circle(self.screen, (240, 248, 255), (moonx, 100), 32)
        for li in range(3):
            for x in range(0, W + 20, 18):
                y = 70 + li * 46 + math.sin(x * 0.012 + t * (0.5 + li * 0.2) + li * 2.0) * 26
                cols = [(120, 255, 170), (130, 200, 255), (220, 160, 255)]
                pygame.draw.circle(L, (*cols[li], 26), (x, int(y)), 9)
                if x % 54 == 0:
                    pygame.draw.circle(self.screen, cols[li], (x, int(y)), 2)
        pygame.draw.polygon(self.screen, (90, 130, 165), [(mx - 200, H), (mx + 180, 330), (mx + 560, H)])
        pygame.draw.polygon(self.screen, (240, 248, 255), [(mx + 180, 330), (mx + 150, 362), (mx + 210, 362)])
        pygame.draw.polygon(self.screen, (75, 115, 155), [(mx + 620, H), (mx + 820, 350), (mx + 1160, H)])
        pygame.draw.polygon(self.screen, (245, 250, 255), [(mx + 820, 350), (mx + 796, 378), (mx + 844, 378)])
        for i in range(5):
            cx0 = 90 + i * 190 - camx * 0.5
            ch = 60 + (i % 3) * 30
            pygame.draw.polygon(self.screen, (170, 215, 240),
                                [(cx0 - 16, H), (cx0, H - ch), (cx0 + 16, H)])
            pygame.draw.polygon(self.screen, (225, 245, 255),
                                [(cx0 - 6, H - ch * 0.4), (cx0, H - ch), (cx0 + 6, H - ch * 0.4)])
            pygame.draw.circle(L, (180, 225, 255, 40), (int(cx0), int(H - ch)), 16)
        if len(self.parts) < 130:
            for _ in range(2):
                self.parts.append(Particle(random.uniform(0, W), -6,
                                           random.uniform(-40, -5), random.uniform(40, 110),
                                           random.uniform(1.5, 3.0), (240, 248, 255), 2, grav=60))

    def _bg_dune_sea(self, st, camx, fx, mx, t, L):
        sunx = int(480 - camx * 0.1)
        pygame.draw.circle(L, (255, 220, 150, 80), (sunx, 130), 80)
        pygame.draw.circle(self.screen, (255, 240, 200), (sunx, 130), 44)
        for i, (dy, col) in enumerate(((330, (200, 150, 95)), (390, (220, 175, 115)), (450, (235, 200, 140)))):
            pts = [(x, dy + math.sin(x * 0.008 + i * 2.0 + t * 0.2) * 16 - camx * 0.05 * (i + 1) % 60)
                   for x in range(-40, W + 40, 30)]
            pts += [(W + 40, H), (-40, H)]
            pygame.draw.polygon(self.screen, col, pts)
        obx = 700 - camx * 0.35
        pygame.draw.polygon(self.screen, (120, 90, 60), [(obx - 20, H - 220), (obx + 20, H - 220),
                                                         (obx + 30, H - 60), (obx - 30, H - 60)])
        pygame.draw.polygon(self.screen, (150, 115, 75), [(obx - 20, H - 220), (obx + 20, H - 220),
                                                          (obx + 14, H - 120), (obx - 14, H - 120)])
        pygame.draw.circle(L, (255, 230, 170, 50), (int(obx), int(H - 160)), 30)
        for i in range(3):
            hx = 0 + ((t * (60 + i * 30) + i * 400) % (W + 200)) - 100
            pygame.draw.line(self.screen, (240, 210, 160), (hx, 300 + i * 50), (hx + 120, 300 + i * 50), 2)
        for i in range(2):
            bx = (t * (40 + i * 18) + i * 500) % (W + 100) - 50
            by = 120 + i * 50 + math.sin(t * 2 + i * 3) * 10
            pygame.draw.arc(self.screen, (90, 70, 50), (int(bx - 10), int(by - 4), 20, 10), 3.4, 6.0, 2)
        if len(self.parts) < 130:
            for _ in range(3):
                self.parts.append(Particle(random.uniform(0, W), random.uniform(200, H),
                                           random.uniform(-260, -120), random.uniform(-24, 10),
                                           random.uniform(0.8, 1.8), (240, 210, 160), 2, grav=0))

    def _bg_hollow_star(self, st, camx, fx, mx, t, L):
        self._bg_stars(camx, t, 110, par=0.08, seed=3)
        pygame.draw.circle(self.screen, (70, 60, 120), (W // 2 - int(camx * 0.1), H + 320), 420)
        pygame.draw.arc(self.screen, (150, 130, 220), (W // 2 - int(camx * 0.1) - 420, H - 100, 840, 160),
                        3.3, 6.1, 3)
        pygame.draw.circle(L, (150, 130, 220, 50),
                           (W // 2 - int(camx * 0.1), H - 60), 200)
        rx, ry = W // 2 - camx * 0.25, 150
        pygame.draw.ellipse(self.screen, (50, 45, 70), (rx - 260, ry - 26, 520, 52), 8)
        for i in range(6):
            a = t * 0.2 + i * 1.047
            bx, by = rx + math.cos(a) * 240, ry + math.sin(a) * 22
            on = int(t * 2 + i) % 2 == 0
            pygame.draw.circle(self.screen, (255, 120, 140) if on else (90, 80, 110),
                               (int(bx), int(by)), 4)
            pygame.draw.circle(L, (255, 120, 140, 70 if on else 20), (int(bx), int(by)), 12)
        for i in range(4):
            px = 150 + i * 220 - camx * 0.4 + math.sin(t * 0.5 + i) * 12
            py = 300 + (i % 2) * 100 + math.cos(t * 0.4 + i * 2) * 10
            pygame.draw.rect(self.screen, (60, 60, 80), (px - 8, py - 3, 16, 6))
            pygame.draw.circle(L, (170, 160, 255, 40), (int(px), int(py)), 14)
        self.draw_cube(300 - camx * 0.5, 220 + math.sin(t * 0.7) * 12, 26, t * 0.45, (80, 70, 120))
        self.draw_cube(680 - camx * 0.5, 160 + math.cos(t * 0.5) * 10, 20, -t * 0.55, (70, 60, 110))
        if len(self.parts) < 110 and random.random() < 0.4:
            self.parts.append(Particle(random.uniform(0, W), H + 6,
                                       random.uniform(-14, 14), random.uniform(-60, -20),
                                       random.uniform(1.5, 3.0), (180, 170, 255), 2, grav=-30, glow=True))

    def _bg_clockwork(self, st, camx, fx, mx, t, L):
        ccx, ccy = 480 - camx * 0.2, 170
        pygame.draw.circle(self.screen, (60, 50, 42), (int(ccx), int(ccy)), 110)
        pygame.draw.circle(self.screen, (150, 125, 90), (int(ccx), int(ccy)), 100)
        pygame.draw.circle(self.screen, (45, 36, 30), (int(ccx), int(ccy)), 88)
        for i in range(12):
            a = i * 0.5236
            tx1, ty1 = ccx + math.cos(a) * 78, ccy + math.sin(a) * 78
            tx2, ty2 = ccx + math.cos(a) * 88, ccy + math.sin(a) * 88
            pygame.draw.line(self.screen, (200, 175, 130), (tx1, ty1), (tx2, ty2), 4 if i % 3 == 0 else 2)
        ha = -1.57 + (t * 0.1) % 6.283
        ma = -1.57 + (t * 0.8) % 6.283
        pygame.draw.line(self.screen, (240, 220, 180), (ccx, ccy),
                         (ccx + math.cos(ha) * 44, ccy + math.sin(ha) * 44), 5)
        pygame.draw.line(self.screen, (255, 200, 120), (ccx, ccy),
                         (ccx + math.cos(ma) * 66, ccy + math.sin(ma) * 66), 3)
        pygame.draw.circle(self.screen, (255, 210, 140), (int(ccx), int(ccy)), 7)
        self._bg_gear(150 - camx * 0.35, 380, 52, t * 0.6, (70, 58, 48))
        self._bg_gear(830 - camx * 0.35, 380, 64, -t * 0.45, (60, 50, 42))
        self._bg_gear(830 - camx * 0.35, 380, 20, t * 0.9, (90, 75, 60))
        for i in range(2):
            px = 250 + i * 450 - camx * 0.3
            pygame.draw.rect(self.screen, (50, 42, 38), (px - 14, 260, 28, H - 260))
            pygame.draw.circle(L, (255, 200, 130, 60), (int(px), 250), 18)
            if int(t * 1.2 + i) % 2 == 0:
                pygame.draw.circle(L, (200, 190, 180, 60),
                                   (int(px + math.sin(t + i) * 8), int(230 - (t * 20 + i * 50) % 60)), 12)
        self.draw_floor_grid(H - 6, (120, 95, 70))
        if len(self.parts) < 100 and random.random() < 0.3:
            self.parts.append(Particle(random.uniform(0, W), H - 60,
                                       random.uniform(-20, 20), random.uniform(-120, -50),
                                       random.uniform(1.0, 2.0), (210, 190, 170), 3, grav=-40, glow=True))

    def _bg_magma_core(self, st, camx, fx, mx, t, L):
        for i, (bx, bw) in enumerate(((180, 70), (420, 90), (700, 70), (880, 100))):
            cx0 = bx - camx * 0.3
            pygame.draw.rect(self.screen, (32, 14, 14), (cx0 - bw / 2, 120 + (i % 2) * 40, bw, H))
            pygame.draw.rect(self.screen, (52, 24, 20), (cx0 - bw / 2, 120 + (i % 2) * 40, 12, H))
        for i, mfx in enumerate((330, 620)):
            cx0 = mfx - camx * 0.35
            pygame.draw.rect(self.screen, (255, 120, 40), (cx0 - 12, 60, 24, H - 60))
            pygame.draw.rect(self.screen, (255, 200, 110), (cx0 - 5, 60, 10, H - 60))
            for k in range(3):
                by = 120 + ((t * 160 + i * 200 + k * 180) % (H - 160))
                pygame.draw.circle(self.screen, (255, 230, 150), (int(cx0), int(by)), 7)
            pygame.draw.circle(L, (255, 130, 50, 80), (int(cx0), H - 40), 46)
        pygame.draw.ellipse(L, (255, 110, 40, 70), (-40, H - 26, W + 80, 40))
        pts = [(x, H - 14 + math.sin(x * 0.05 + t * 3) * 4) for x in range(-20, W + 20, 24)]
        pygame.draw.lines(self.screen, (255, 160, 70), False, pts, 2)
        self.draw_floor_grid(H - 6, (120, 50, 25))
        if len(self.parts) < 130:
            for _ in range(3):
                self.parts.append(Particle(random.uniform(0, W), H + 6,
                                           random.uniform(-30, 30), random.uniform(-260, -90),
                                           random.uniform(1.0, 2.2),
                                           random.choice([(255, 140, 50), (255, 90, 40), (255, 200, 110)]),
                                           random.randint(2, 5), grav=-60, glow=True))

    def _bg_cloud_nine(self, st, camx, fx, mx, t, L):
        sunx = int(180 - camx * 0.12)
        pygame.draw.circle(L, (255, 250, 220, 70), (sunx, 100), 60)
        pygame.draw.circle(self.screen, (255, 252, 230), (sunx, 100), 32)
        rcx, rcy = W // 2 - camx * 0.15, H + 40
        for i, col in enumerate([(255, 120, 120), (255, 190, 120), (255, 245, 150),
                                 (150, 235, 150), (140, 200, 255), (210, 160, 255)]):
            pygame.draw.arc(self.screen, col, (rcx - 330 + i * 12, rcy - 330 + i * 12,
                                               660 - i * 24, 660 - i * 24), 3.25, 6.15, 9)
        for layer in range(2):
            spd = 12 + layer * 10
            for i in range(4):
                x = (i * 300 + layer * 150 - t * spd - camx * (0.35 + 0.12 * layer)) % (W + 320) - 160
                y = 120 + layer * 110 + i * 40
                sc = 0.8 + layer * 0.5
                for ox2, s2 in ((0, 52), (42, 38), (-42, 36)):
                    pygame.draw.ellipse(self.screen, (255, 255, 255),
                                        (int(x + ox2 * sc - s2 * sc), int(y - s2 * sc // 2),
                                         int(s2 * 2 * sc), int(s2 * sc)))
        for i in range(2):
            bx = 300 + i * 380 - camx * 0.3 + math.sin(t * 0.6 + i * 3) * 14
            by = 200 + i * 60 + math.sin(t * 0.8 + i) * 10
            pygame.draw.ellipse(self.screen, (255, 150, 150) if i == 0 else (150, 200, 255),
                                (bx - 16, by - 20, 32, 40))
            pygame.draw.line(self.screen, (120, 120, 140), (bx, by + 20), (bx, by + 54), 2)
        if len(self.parts) < 110 and random.random() < 0.4:
            self.parts.append(Particle(random.uniform(0, W), random.uniform(0, H),
                                       random.uniform(-16, 16), random.uniform(-30, -8),
                                       random.uniform(1.5, 3.0), (255, 255, 255), 2, grav=0, glow=True))

    def _bg_the_rift(self, st, camx, fx, mx, t, L):
        self._bg_stars(camx, t, 80, par=0.12, seed=7)
        rcx, rcy = W // 2 - camx * 0.2, H // 2 - 30
        pygame.draw.circle(L, (200, 40, 80, 60), (int(rcx), int(rcy)), 190)
        pygame.draw.circle(L, (120, 40, 180, 50), (int(rcx), int(rcy)), 130)
        for ri, (rr, col, wd) in enumerate((((150, (255, 70, 90), 10), (195, (170, 90, 255), 7),
                                             (240, (255, 200, 220), 4))[ri] for ri in range(3))):
            a0 = t * (0.5 + ri * 0.25) + ri * 2.0
            pygame.draw.arc(self.screen, col, (rcx - rr, rcy - rr // 2, rr * 2, rr), a0, a0 + 4.2, wd)
            pygame.draw.arc(self.screen, col, (rcx - rr, rcy - rr // 2, rr * 2, rr), a0 + 3.4, a0 + 5.6, wd)
        for i in range(9):
            a = t * 0.4 + i * 0.698
            dx, dy = rcx + math.cos(a) * 215, rcy + math.sin(a) * 105
            pygame.draw.polygon(self.screen, (110, 70, 140),
                                [(dx, dy - 8), (dx + 6, dy), (dx, dy + 8), (dx - 6, dy)])
            pygame.draw.line(self.screen, (255, 130, 150), (dx, dy - 8), (dx + 6, dy), 1)
        pygame.draw.ellipse(self.screen, (30, 10, 25), (-60, H - 50, W + 120, 70))
        pts = [(x, H - 16 + math.sin(x * 0.06 + t * 4) * 4) for x in range(-20, W + 20, 26)]
        pygame.draw.lines(self.screen, (255, 80, 100), False, pts, 2)
        if len(self.parts) < 130 and random.random() < 0.6:
            self.parts.append(Particle(random.uniform(0, W), H + 6,
                                       random.uniform(-20, 20), random.uniform(-90, -30),
                                       random.uniform(1.2, 2.6),
                                       random.choice([(255, 90, 120), (190, 140, 255), (255, 170, 90)]),
                                       3, grav=-40, glow=True))

    def _bg_harbor_town(self, st, camx, fx, mx, t, L):
        for i, (bx, bw, bh) in enumerate(((60, 130, 220), (220, 110, 170), (560, 140, 240), (730, 100, 180))):
            cx0 = bx - camx * 0.3
            pygame.draw.rect(self.screen, (48, 60, 88), (cx0, H - 120 - bh, bw, bh + 120))
            pygame.draw.polygon(self.screen, (66, 80, 112), [(cx0 - 8, H - 120 - bh),
                                                             (cx0 + bw / 2, H - 150 - bh), (cx0 + bw + 8, H - 120 - bh)])
            for wx in range(3):
                for wy in range(3):
                    on = (wx * 3 + wy + i) % 3 != 0
                    pygame.draw.rect(self.screen, (255, 220, 150) if on else (40, 48, 70),
                                     (cx0 + 16 + wx * 34, H - 100 - bh + wy * 30, 18, 16))
        # lighthouse + sweeping beam
        lhx = 860 - camx * 0.25
        pygame.draw.rect(self.screen, (200, 200, 210), (lhx - 16, 180, 32, H - 300))
        pygame.draw.rect(self.screen, (200, 90, 90), (lhx - 16, 220, 32, 16))
        pygame.draw.rect(self.screen, (200, 90, 90), (lhx - 16, 280, 32, 16))
        pygame.draw.polygon(self.screen, (60, 60, 80), [(lhx - 22, 180), (lhx + 22, 180), (lhx, 150)])
        pygame.draw.circle(L, (255, 240, 180, 90), (int(lhx), 168), 14)
        ba = math.sin(t * 0.7) * 0.5
        pygame.draw.polygon(L, (255, 244, 200, 36),
                            [(lhx, 168), (lhx + math.cos(ba) * 700 - 60, 168 + math.sin(ba) * 700 + 120),
                             (lhx + math.cos(ba) * 700 + 60, 168 + math.sin(ba) * 700 + 200)])
        # masts + water
        for i in range(2):
            mxx = 320 + i * 260 - camx * 0.4
            pygame.draw.line(self.screen, (70, 55, 45), (mxx, 330), (mxx, H - 90), 4)
            pygame.draw.polygon(self.screen, (220, 120, 120),
                                [(mxx, 340), (mxx + 44, 370), (mxx, 400)])
        pygame.draw.rect(self.screen, (50, 110, 150), (-40, H - 90, W + 80, 90))
        for i in range(10):
            wx = (i * 130 + int(t * 30)) % (W + 60) - 30
            pygame.draw.line(self.screen, (150, 210, 240), (wx, H - 60 + (i % 3) * 14),
                             (wx + 46, H - 60 + (i % 3) * 14), 2)
        for i in range(4):
            lx0 = 140 + i * 200 - camx * 0.45
            pygame.draw.circle(self.screen, (255, 210, 140), (int(lx0), H - 110), 5)
            pygame.draw.circle(L, (255, 210, 140, 70), (int(lx0), int(H - 110)), 16)
        for i in range(2):
            bx = (t * 36 + i * 480) % (W + 100) - 50
            by = 120 + i * 50 + math.sin(t * 2 + i) * 8
            pygame.draw.arc(self.screen, (50, 60, 80), (int(bx - 10), int(by - 4), 20, 10), 3.4, 6.0, 2)

    def _bg_world_tree(self, st, camx, fx, mx, t, L):
        tx = 480 - camx * 0.2
        pygame.draw.polygon(self.screen, (70, 55, 40),
                            [(tx - 70, H), (tx - 34, 120), (tx + 34, 120), (tx + 70, H)])
        pygame.draw.polygon(self.screen, (95, 75, 55),
                            [(tx - 34, 120), (tx - 150, 40), (tx - 110, 30), (tx, 100)])
        pygame.draw.polygon(self.screen, (95, 75, 55),
                            [(tx + 34, 120), (tx + 160, 60), (tx + 120, 46), (tx, 100)])
        for i in range(4):
            by = 200 + i * 80
            pygame.draw.line(self.screen, (55, 42, 30), (tx - 50, by), (tx + 50, by), 2)
        for i, (cx0, cy0, cw) in enumerate(((tx - 140, 90, 300), (tx + 150, 120, 280), (tx, 30, 380))):
            bx = cx0 - camx * 0.08 + math.sin(t * 0.5 + i * 2) * 8
            pygame.draw.ellipse(self.screen, (60, 140, 90), (bx - cw / 2, cy0 - 40, cw, 90))
            pygame.draw.ellipse(self.screen, (95, 185, 120), (bx - cw / 2 + 20, cy0 - 52, cw - 40, 60))
            for g in range(3):
                gx = bx - cw / 3 + g * cw / 3
                pygame.draw.ellipse(self.screen, (150, 230, 160), (gx - 14, cy0 - 30, 28, 18))
        for ri in range(2):
            bx = tx - 60 + ri * 120
            pygame.draw.polygon(L, (220, 255, 200, 26), [(bx, 60), (bx + 50, 60), (bx - 30, H), (bx - 80, H)])
        for cxi in range(5):
            clx = cxi * 220 - 60 - camx * 0.25 + math.sin(t * 0.4 + cxi) * 10
            pygame.draw.ellipse(self.screen, (120, 190, 150), (clx - 60, H - 70, 120, 30))
        if len(self.parts) < 120 and random.random() < 0.55:
            self.parts.append(Particle(random.uniform(0, W), -6,
                                       random.uniform(-40, 10), random.uniform(30, 80),
                                       random.uniform(2.0, 4.0),
                                       random.choice([(150, 220, 150), (190, 240, 170), (220, 255, 200)]),
                                       3, grav=30))
        if len(self.parts) < 120 and random.random() < 0.3:
            self.parts.append(Particle(random.uniform(0, W), random.uniform(100, H),
                                       random.uniform(-12, 12), random.uniform(-20, -6),
                                       random.uniform(1.5, 3.0), (220, 255, 200), 2, grav=0, glow=True))

    def _bg_sunset_keep(self, st, camx, fx, mx, t, L):
        sunx = int(480 - camx * 0.1)
        pygame.draw.circle(L, (255, 160, 90, 80), (sunx, 300), 90)
        pygame.draw.circle(self.screen, (255, 200, 130), (sunx, 300), 52)
        pygame.draw.circle(self.screen, (255, 225, 170), (sunx, 300), 40)
        kx = 480 - camx * 0.3
        pygame.draw.rect(self.screen, (70, 50, 80), (kx - 60, 220, 120, H - 220))
        for tx0 in (kx - 150, kx + 150):
            pygame.draw.rect(self.screen, (62, 44, 72), (tx0 - 40, 270, 80, H - 270))
            pygame.draw.polygon(self.screen, (50, 36, 60),
                                [(tx0 - 48, 270), (tx0 - 48, 240), (tx0 - 24, 240), (tx0 - 24, 270),
                                 (tx0, 270), (tx0, 240), (tx0 + 24, 240), (tx0 + 24, 270),
                                 (tx0 + 48, 270), (tx0 + 48, 240), (tx0 - 48, 240)])
            pygame.draw.rect(self.screen, (48, 30, 50), (tx0 - 40, 240, 80, 8))
            wave = math.sin(t * 3 + tx0) * 6
            pygame.draw.polygon(self.screen, (200, 80, 90),
                                [(tx0, 196), (tx0 + 44 + wave, 206), (tx0, 218)])
            pygame.draw.line(self.screen, (40, 30, 40), (tx0, 180), (tx0, 200), 3)
        pygame.draw.polygon(self.screen, (50, 36, 60),
                            [(kx - 70, 220), (kx - 70, 190), (kx - 46, 190), (kx - 46, 220),
                             (kx - 22, 220), (kx - 22, 190), (kx + 2, 190), (kx + 2, 220),
                             (kx + 26, 220), (kx + 26, 190), (kx + 50, 190), (kx + 50, 220),
                             (kx + 70, 220), (kx + 70, 190), (kx - 70, 190)])
        for j in range(3):
            wy = 260 + j * 50
            on = int(t * 1.4 + j) % 2 == 0
            pygame.draw.rect(self.screen, (255, 190, 120) if on else (60, 45, 65),
                             (kx - 16, wy, 32, 20))
            if on:
                pygame.draw.circle(L, (255, 180, 110, 50), (int(kx), int(wy + 10)), 20)
        for i in range(4):
            clx = (i * 280 - t * 12 - camx * 0.2) % (W + 300) - 150
            cy = 120 + i * 46
            pygame.draw.ellipse(self.screen, (235, 150, 150), (clx - 80, cy, 160, 26))
            pygame.draw.ellipse(self.screen, (250, 190, 190), (clx - 60, cy - 8, 120, 20))
        pygame.draw.polygon(self.screen, (80, 55, 80), [(-40, H), (300, 400), (700, H)])
        pygame.draw.polygon(self.screen, (70, 48, 72), [(500, H), (800, 420), (1100, H)])
        for i in range(2):
            bx = (t * 34 + i * 500) % (W + 100) - 50
            by = 150 + i * 60 + math.sin(t * 2 + i) * 10
            pygame.draw.arc(self.screen, (60, 40, 55), (int(bx - 10), int(by - 4), 20, 10), 3.4, 6.0, 2)

    def _bg_haze(self, idx):
        """Smash-style atmospheric perspective: a cached translucent wash that
        pushes the background back so platforms and fighters pop."""
        cache = getattr(self, "_haze_cache", None)
        if cache is None:
            cache = self._haze_cache = {}
        ov = cache.get(idx)
        if ov is None:
            st = STAGES[idx]
            tint = mix(st["bot"], (232, 238, 248), 0.55)
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            for y in range(120, H, 6):
                if y < 300:
                    a = int(46 * (y - 120) / 180)
                elif y < 430:
                    a = 46
                else:
                    a = int(46 - 22 * (y - 430) / max(1, H - 430))
                if a > 0:
                    pygame.draw.rect(ov, (*tint, a), (0, y, W, 6))
            cache[idx] = ov
        self.screen.blit(ov, (0, 0))

    def draw_bg(self, idx, camx=0):
        st = STAGES[idx]
        self.gradient(st["top"], st["bot"])
        t = self.t_global
        L = self.glow_layer
        fx, mx = -camx * 0.25, -camx * 0.5
        _paint = {
            "Ember Arena": self._bg_ember_arena,
            "Sky Battlefield": self._bg_sky_battlefield,
            "Void Final": self._bg_void_final,
            "Fungal Hollow": self._bg_fungal_hollow,
            "Storm Spire": self._bg_storm_spire,
            "Tide Vault": self._bg_tide_vault,
            "Iron Foundry": self._bg_iron_foundry,
            "Thorn Garden": self._bg_thorn_garden,
            "Glacier": self._bg_glacier,
            "Dune Sea": self._bg_dune_sea,
            "Hollow Star": self._bg_hollow_star,
            "Clockwork": self._bg_clockwork,
            "Magma Core": self._bg_magma_core,
            "Cloud Nine": self._bg_cloud_nine,
            "The Rift": self._bg_the_rift,
            "Harbor Town": self._bg_harbor_town,
            "World Tree": self._bg_world_tree,
            "Sunset Keep": self._bg_sunset_keep,
        }.get(st["name"])
        if _paint is not None:
            _paint(st, camx, fx, mx, t, L)
            self._bg_haze(idx)
            return
        if st["deco"] == "ember":
            # volcano silhouettes + glowing crater + lava floor glow
            pygame.draw.polygon(self.screen, (30, 8, 12), [(fx - 100, H), (fx + 140, 300), (fx + 380, H)])
            pygame.draw.polygon(self.screen, (26, 10, 16), [(fx + 560, H), (fx + 810, 330), (fx + 1060, H)])
            pygame.draw.polygon(self.screen, (255, 110, 40),
                                [(fx + 150, 300), (fx + 165, 268), (fx + 180, 300)])
            pygame.draw.circle(L, (255, 120, 50, 70), (int(fx + 165), 292), 26)
            pygame.draw.ellipse(L, (255, 110, 40, 60), (-40, H - 26, W + 80, 40))
            for i in range(3):  # drifting smoke columns
                sx = fx + 165 + math.sin(t * 0.7 + i * 2.1) * 26
                sy = 250 - ((t * 26 + i * 90) % 240)
                pygame.draw.circle(L, (90, 70, 70, 90), (int(sx), int(sy)), 16 + i * 5)
            pygame.draw.polygon(self.screen, (38, 12, 14), [(mx - 200, H), (mx + 60, 380), (mx + 320, H)])
            pygame.draw.polygon(self.screen, (38, 12, 14), [(mx + 700, H), (mx + 980, 400), (mx + 1260, H)])
            pts = [(x, H - 14 + math.sin(x * 0.05 + t * 3) * 4) for x in range(-20, W + 20, 24)]
            pygame.draw.lines(self.screen, (255, 160, 70), False, pts, 2)
            self.draw_floor_grid(H - 6, (120, 50, 25))
            self.draw_cube(220 - camx * 0.4, 180 + math.sin(t * 0.8) * 10, 34, t * 0.5, (60, 25, 20))
            self.draw_cube(760 - camx * 0.4, 130 + math.cos(t * 0.6) * 12, 24, -t * 0.4, (80, 32, 22))
            if len(self.parts) < 110:  # rising embers + ash
                for _ in range(2):
                    self.parts.append(Particle(random.uniform(0, W), H + 6,
                                               random.uniform(-24, 24), random.uniform(-150, -50),
                                               random.uniform(1.2, 2.4),
                                               random.choice([(255, 140, 50), (255, 90, 40), (120, 110, 110)]),
                                               random.randint(2, 4), grav=-60, glow=True))
        elif st["deco"] == "sky":
            # sun + halo + god rays, parallax clouds, peaks, birds, cloud sea
            sunx = int(800 - camx * 0.15)
            pygame.draw.circle(L, (255, 246, 200, 70), (sunx, 90), 64)
            pygame.draw.circle(self.screen, (255, 246, 200), (sunx, 90), 34)
            for ri in range(3):
                ang = 0.9 + ri * 0.35 + math.sin(t * 0.3) * 0.05
                pygame.draw.line(L, (255, 250, 220, 26), (sunx, 90),
                                 (int(sunx + math.cos(ang) * 700), int(90 + math.sin(ang) * 700)), 34 - ri * 8)
            for cxi in range(6):
                clx = cxi * 200 - 100 - camx * 0.2 + math.sin(t * 0.4 + cxi) * 12
                pygame.draw.ellipse(self.screen, (225, 235, 248), (clx - 90, 392, 180, 30))
                pygame.draw.ellipse(self.screen, (255, 255, 255), (clx - 70, 386, 140, 24))
            for layer in range(2):
                spd = 14 + layer * 12
                for i in range(4):
                    x = (i * 300 + layer * 150 - t * spd - camx * (0.4 + 0.15 * layer)) % (W + 320) - 160
                    y = 60 + layer * 90 + i * 38
                    sc = 0.7 + layer * 0.5
                    for ox2, s2 in ((0, 46), (38, 34), (-38, 32)):
                        pygame.draw.ellipse(self.screen, (196, 212, 232),
                                            (int(x + ox2 * sc - s2 * sc), int(y - s2 * sc // 2 + 10 * sc),
                                             int(s2 * 2 * sc), int(s2 * sc)))
                        pygame.draw.ellipse(self.screen, (255, 255, 255),
                                            (int(x + ox2 * sc - s2 * sc), int(y - s2 * sc // 2),
                                             int(s2 * 2 * sc), int(s2 * sc)))
            pygame.draw.polygon(self.screen, (70, 110, 150), [(mx - 200, H), (mx + 180, 340), (mx + 560, H)])
            pygame.draw.polygon(self.screen, (235, 245, 255), [(mx + 180, 340), (mx + 150, 372), (mx + 210, 372)])
            pygame.draw.polygon(self.screen, (60, 100, 140), [(mx + 620, H), (mx + 820, 360), (mx + 1160, H)])
            pygame.draw.polygon(self.screen, (240, 248, 255), [(mx + 820, 360), (mx + 796, 388), (mx + 844, 388)])
            for i in range(2):  # birds
                bx = (t * (40 + i * 18) + i * 500) % (W + 100) - 50
                by = 130 + i * 60 + math.sin(t * 2 + i * 3) * 12
                pygame.draw.arc(self.screen, (40, 50, 70), (int(bx - 10), int(by - 4), 20, 10),
                                3.4, 6.0, 2)
            if len(self.parts) < 110 and random.random() < 0.25:
                self.parts.append(Particle(random.uniform(0, W), random.uniform(300, H),
                                           random.uniform(-40, -10), random.uniform(-16, -4),
                                           random.uniform(2.0, 3.5), (255, 255, 255),
                                           2, grav=0, glow=True))
        elif st["deco"] == "fungus":
            # giant glowing mushrooms + drifting spores
            fx2 = -camx * 0.3
            for i, (mx2, mh, mr) in enumerate(((140, 260, 46), (700, 200, 60), (1050, 280, 40))):
                bx = fx2 + mx2 + math.sin(t * 0.4 + i) * 8
                pygame.draw.rect(self.screen, (50, 70, 60), (bx - 12, H - mh, 24, mh + 40))
                pygame.draw.ellipse(self.screen, (120, 70, 150), (bx - mr, H - mh - 34, mr * 2, 44))
                pygame.draw.ellipse(self.screen, (200, 140, 220), (bx - mr + 12, H - mh - 30, 16, 12))
                pygame.draw.circle(L, (190, 130, 230, 50), (int(bx), int(H - mh - 10)), mr)
            if len(self.parts) < 110 and random.random() < 0.5:
                self.parts.append(Particle(random.uniform(0, W) + camx * 0.5, H + 6,
                                           random.uniform(-20, 20), random.uniform(-60, -20),
                                           random.uniform(1.5, 3.0), (190, 230, 160),
                                           3, grav=-30, glow=True))
        elif st["deco"] == "storm":
            # lightning-split sky + rain streaks
            if random.random() < 0.012:
                self.parts.append(Particle(random.uniform(100, W - 100), 0, 0, 0, 0.12,
                                           (255, 255, 255), 60, grav=0, glow=True))
            for i in range(24):
                rx = (i * 173 + t * 900) % (W + 40) - 20
                ry = (i * 311 + t * 1400) % H
                pygame.draw.line(self.screen, (170, 190, 220), (rx, ry), (rx - 4, ry + 14), 1)
            for i in range(3):
                cx2 = 200 + i * 300 + math.sin(t * 0.5 + i * 2) * 30 - camx * 0.35
                pygame.draw.ellipse(self.screen, (70, 80, 110), (cx2 - 90, 60 + i * 40, 180, 44))
                pygame.draw.ellipse(self.screen, (50, 58, 86), (cx2 - 70, 74 + i * 40, 140, 30))
            if len(self.parts) < 110 and random.random() < 0.3:
                self.parts.append(Particle(random.uniform(0, W), -6,
                                           random.uniform(-60, -20), random.uniform(300, 420),
                                           0.8, (170, 190, 230), 2, grav=0))
        else:
            # nebula blobs, twinkle stars, rune rings, floating shards
            for i, (nx, ny, nr, col) in enumerate(((240, 150, 150, (120, 60, 180)),
                                                   (720, 380, 170, (60, 40, 140)),
                                                   (500, 120, 110, (150, 60, 160)))):
                pygame.draw.circle(L, (*col, 46),
                                   (int(nx - camx * 0.25 + math.sin(t * 0.3 + i * 2) * 20), int(ny)), nr)
            for i in range(110):
                x = ((i * 137 - (camx * 0.1 if i % 2 == 0 else 0)) % (W + 100)) - 50
                y = (i * 89) % H
                tw = 0.4 + 0.6 * abs(math.sin(t * 1.5 + i * 1.3))
                c = int(120 + 120 * tw)
                pygame.draw.circle(self.screen, (c, c, min(255, c + 40)), (int(x), int(y)), 1 + (i % 2))
            cx, cy = W // 2 - camx * 0.3, H // 2 - 20
            for r, al in ((150, 60), (200, 40), (250, 26)):
                pygame.draw.arc(self.screen, (150, 90, 220),
                                (cx - r, cy - r // 2, r * 2, r), 0.3 + t * 0.25, 2.6 + t * 0.25, 3)
                _ = al
            for i in range(5):  # floating shards
                sx = 120 + i * 180 - camx * 0.6 + math.sin(t * 0.5 + i * 1.9) * 24
                sy = 150 + (i % 3) * 90 + math.sin(t * 0.8 + i) * 14
                pygame.draw.polygon(self.screen, (90, 70, 130),
                                    [(sx, sy - 10), (sx + 8, sy), (sx, sy + 10), (sx - 8, sy)])
                pygame.draw.line(self.screen, (180, 140, 230), (sx, sy - 10), (sx + 8, sy), 1)
            self.draw_floor_grid(H - 6, (50, 30, 80))
            self.draw_cube(300 - camx * 0.5, 200 + math.sin(t * 0.7) * 12, 30, t * 0.45, (90, 60, 140))
            self.draw_cube(660 - camx * 0.5, 150 + math.cos(t * 0.5) * 10, 22, -t * 0.55, (70, 45, 120))
            if len(self.parts) < 110 and random.random() < 0.5:
                self.parts.append(Particle(random.uniform(0, W), H + 6,
                                           random.uniform(-16, 16), random.uniform(-70, -25),
                                           random.uniform(1.5, 3.0), (190, 150, 255),
                                           3, grav=-30, glow=True))

    # ================= PLATFORM SKINS (material look per arena) =================
    def _slab(self, x, y, w, st, is_main, pi):
        base, glow = st["plat"], st["glow"]
        skin = st.get("skin", "")
        thick = 22 if is_main else 14
        dark_b = mix(base, (0, 0, 0), 0.55)
        lite_b = mix(base, (255, 255, 255), 0.35)
        side_b = mix(base, (0, 0, 0), 0.35)
        pulse = 0.5 + 0.5 * math.sin(self.t_global * 3 + pi)
        # drop shadow + extruded 3D side/end caps
        pygame.draw.rect(self.screen, (10, 12, 20), (x - 6, y + 8, w + 12, thick + 12), border_radius=8)
        dd = 15 if not is_main else 20
        pygame.draw.polygon(self.screen, side_b,
                            [(x + w, y + 2), (x + w + dd, y + 10), (x + w + dd, y + 10 + thick),
                             (x + w, y + thick)])
        pygame.draw.polygon(self.screen, mix(base, (0, 0, 0), 0.7),
                            [(x, y + 2), (x - dd, y + 10), (x - dd, y + 10 + thick), (x, y + thick)])
        pygame.draw.rect(self.screen, dark_b, (x, y + 6, w, thick - 4), border_radius=7)
        pygame.draw.rect(self.screen, base, (x, y, w, 12 if not is_main else 14), border_radius=6)
        pygame.draw.rect(self.screen, lite_b, (x, y, w, 4), border_radius=2)
        pygame.draw.line(self.screen, (255, 255, 255), (x + 3, y + 1), (x + w - 3, y + 1), 1)
        # --- material top pattern ---
        if skin in ("obsidian", "magmarock"):
            for ci in range(max(2, int(w // 130))):
                cx2 = x + 30 + ci * (w - 60) / max(1, max(2, int(w // 130)) - 1)
                if int(self.t_global * 3 + ci + pi) % 2 == 0:
                    pygame.draw.line(self.screen, (255, 140, 60), (cx2, y + 4), (cx2 + 16, y + 4), 2)
        elif skin in ("marble", "harbor", "keep", "spire", "sandstone"):
            for sx in range(int(x + 40), int(x + w - 8), 44):
                pygame.draw.line(self.screen, dark_b, (sx, y + 2), (sx, y + 11), 2)
        elif skin in ("voidcrystal", "rift", "station"):
            for sx in range(int(x + 26), int(x + w - 8), 52):
                pygame.draw.line(self.screen, lite_b, (sx, y + 2), (sx + 12, y + 11), 2)
            for sx in range(int(x + 40), int(x + w - 8), 78):
                pygame.draw.circle(self.screen, glow, (sx, int(y + 6)), 2)
        elif skin in ("shroom", "bark", "thorn"):
            for sx in range(int(x + 22), int(x + w - 8), 40):
                pygame.draw.circle(self.screen, mix(base, (200, 255, 190), 0.25), (sx, int(y + 7)), 3)
            pygame.draw.line(self.screen, mix(base, (0, 0, 0), 0.4), (x + 4, y + 11), (x + w - 4, y + 11), 1)
        elif skin == "abyss":
            pygame.draw.line(self.screen, (220, 245, 255), (x + 8, y + 9), (x + w // 3, y + 3), 2)
        elif skin in ("foundry", "brass"):
            for rx in range(int(x + 14), int(x + w - 6), 34):
                pygame.draw.circle(self.screen, dark_b, (rx, int(y + 9)), 2)
            for ex in (x + 2, x + w - 14):
                pygame.draw.rect(self.screen, (255, 200, 90), (ex, y + 2, 12, 8))
                pygame.draw.line(self.screen, (30, 20, 15), (ex + 2, y + 2), (ex + 10, y + 10), 2)
        elif skin == "frost":
            pygame.draw.rect(self.screen, (250, 252, 255), (x, y, w, 3), border_radius=2)
            pygame.draw.line(self.screen, (200, 230, 245), (x + 10, y + 10), (x + w // 2, y + 4), 2)
        elif skin == "cloud":
            for sx in range(int(x + 12), int(x + w - 4), 26):
                pygame.draw.circle(self.screen, (255, 255, 255), (sx, int(y + 2)), 6)
        # --- pulsing glow line + travelling spark ---
        pygame.draw.line(self.screen, glow, (x, y + (18 if is_main else 15)),
                         (x + w, y + (18 if is_main else 15)), 2)
        pygame.draw.circle(self.glow_layer, (*glow, int(60 + 60 * pulse)),
                           (int(x + w / 2), int(y + 15)), 5)
        sx2 = x + ((self.t_global * 120 + pi * 170) % max(1, w))
        pygame.draw.circle(self.screen, (255, 255, 255), (int(sx2), int(y + 15)), 2)
        # --- corner caps (tech skins blink, others stay solid) ---
        tech = skin in ("station", "brass", "foundry", "rift", "voidcrystal")
        on = int(self.t_global * 2 + pi) % 2 == 0
        c1 = (255, 220, 130) if (on or not tech) else (90, 70, 50)
        c2 = (255, 220, 130) if ((not on) or not tech) else (90, 70, 50)
        pygame.draw.circle(self.screen, c1, (int(x + 4), int(y + 4)), 2)
        pygame.draw.circle(self.screen, c2, (int(x + w - 4), int(y + 4)), 2)
        # --- hangers under floating platforms ---
        if not is_main:
            if skin in ("marble", "keep", "harbor", "spire", "brass", "foundry", "sandstone"):
                for chx in (x + 18, x + w - 18):
                    sway = math.sin(self.t_global * 2 + chx * 0.05) * 4
                    pygame.draw.line(self.screen, (40, 42, 55), (chx, y + 22), (chx + sway, y + 52), 2)
                    pygame.draw.circle(self.screen, (60, 62, 78), (int(chx + sway), int(y + 54)), 3)
            elif skin in ("shroom", "bark", "thorn"):
                for chx in (x + 18, x + w - 18):
                    sway = math.sin(self.t_global * 1.6 + chx * 0.06) * 6
                    pygame.draw.line(self.screen, (60, 120, 70), (chx, y + 20), (chx + sway, y + 50), 3)
                    pygame.draw.circle(self.screen, (120, 200, 120), (int(chx + sway), int(y + 46)), 3)
            elif skin in ("voidcrystal", "rift", "obsidian", "magmarock", "station", "abyss"):
                cx0 = x + w / 2
                bob = math.sin(self.t_global * 1.8 + x * 0.05) * 3
                pygame.draw.polygon(self.screen, side_b,
                                    [(cx0 - 9, y + 20), (cx0 + 9, y + 20), (cx0, y + 38 + bob)])
                pygame.draw.line(self.screen, glow, (cx0 - 9, y + 20), (cx0, y + 38 + bob), 1)
                pygame.draw.circle(self.glow_layer, (*glow, 60), (int(cx0), int(y + 30)), 10)
            elif skin == "frost":
                for ix in range(int(x + 20), int(x + w - 8), 34):
                    pygame.draw.polygon(self.screen, (200, 230, 245),
                                        [(ix, y + 20), (ix + 10, y + 20), (ix + 5, y + 34)])
            elif skin == "cloud":
                for px in (x + 24, x + w - 24):
                    pygame.draw.circle(self.screen, (245, 248, 255), (int(px), int(y + 24)), 8)
                    pygame.draw.circle(self.screen, (225, 232, 245), (int(px + 10), int(y + 28)), 6)

    def _main_supports(self, m, st, shake_x, shake_y):
        skin = st.get("skin", "")
        mx0, my0, mw = m["x"] + shake_x, m["y"] + shake_y, m["w"]
        if skin in ("voidcrystal", "rift", "station", "cloud"):
            # floating island: crystal cluster + glow underneath, no pillars
            for i, fxr in enumerate((0.3, 0.5, 0.7)):
                cx0 = mx0 + mw * fxr
                bob = math.sin(self.t_global * 1.5 + i * 2.1) * 4
                pygame.draw.polygon(self.screen, mix(st["plat"], (0, 0, 0), 0.4),
                                    [(cx0 - 12, my0 + 26), (cx0 + 12, my0 + 26), (cx0, my0 + 58 + bob)])
                pygame.draw.circle(self.glow_layer, (*st["glow"], 50), (int(cx0), int(my0 + 40)), 14)
        elif skin in ("shroom", "bark", "thorn"):
            for fxr in (0.22, 0.5, 0.78):
                cx0 = mx0 + mw * fxr
                pygame.draw.polygon(self.screen, (60, 48, 36),
                                    [(cx0 - 16, my0 + 28), (cx0 + 16, my0 + 28), (cx0 + 7, my0 + 100)])
                pygame.draw.line(self.screen, (90, 140, 95), (cx0 - 10, my0 + 40), (cx0 - 4, my0 + 90), 2)
        elif skin == "frost":
            for fxr in (0.2, 0.5, 0.8):
                cx0 = mx0 + mw * fxr
                pygame.draw.polygon(self.screen, (170, 210, 235),
                                    [(cx0 - 14, my0 + 28), (cx0 + 14, my0 + 28),
                                     (cx0 + 8, my0 + 100), (cx0 - 8, my0 + 100)])
                pygame.draw.line(self.screen, (240, 248, 255), (cx0 - 8, my0 + 34), (cx0 - 4, my0 + 94), 2)
        else:
            for fxr in (0.2, 0.5, 0.8):
                cx0 = mx0 + mw * fxr
                pygame.draw.rect(self.screen, (14, 15, 24), (cx0 - 9, my0 + 34, 18, 66))
                pygame.draw.rect(self.screen, mix(st["plat"], (0, 0, 0), 0.4),
                                 (cx0 - 9, my0 + 34, 18, 8))

    def _main_dressing(self, m, st, shake_x, shake_y):
        name = st["name"]
        mxx, myy = m["x"] + shake_x, m["y"] + shake_y
        if name in ("Ember Arena", "Magma Core"):
            for ci in range(6):
                cx2 = mxx + 60 + ci * (m["w"] - 120) / 5
                if int(self.t_global * 3 + ci) % 2 == 0:
                    pygame.draw.line(self.screen, (255, 140, 60), (cx2, myy + 4), (cx2 + 14, myy + 4), 2)
        elif name == "Sky Battlefield":
            for gi in range(7):
                gx = mxx + 60 + gi * (m["w"] - 120) / 6
                pygame.draw.circle(self.screen, (160, 220, 255), (int(gx), int(myy + 4)), 3)
                pygame.draw.line(self.screen, (160, 220, 255), (gx - 8, myy + 4), (gx + 8, myy + 4), 1)
        elif name in ("Void Final", "The Rift", "Hollow Star"):
            rw = m["w"] * 0.3 * (0.9 + 0.1 * math.sin(self.t_global * 2))
            pygame.draw.ellipse(self.screen, st["glow"], (mxx + m["w"] / 2 - rw / 2, myy - 8, rw, 14), 2)
            pygame.draw.ellipse(self.glow_layer, (*st["glow"], 60),
                                (mxx + m["w"] / 2 - rw / 2, myy - 8, rw, 14))
        elif name in ("Fungal Hollow", "World Tree", "Thorn Garden"):
            for gi in range(8):
                gx = mxx + 40 + gi * (m["w"] - 80) / 7
                if name == "Thorn Garden" and gi % 2 == 0:
                    pygame.draw.polygon(self.screen, (70, 120, 70),
                                        [(gx, myy), (gx + 5, myy - 12), (gx + 10, myy)])
                else:
                    pygame.draw.circle(self.screen, (140, 220, 150), (int(gx), int(myy - 4)), 3)
                    pygame.draw.rect(self.screen, (80, 110, 85), (gx - 1, myy - 4, 2, 5))
        elif name in ("Harbor Town", "Sunset Keep", "Storm Spire", "Clockwork", "Iron Foundry"):
            for sx in range(int(mxx + 30), int(mxx + m["w"] - 10), 60):
                pygame.draw.line(self.screen, mix(st["plat"], (0, 0, 0), 0.45), (sx, myy + 2), (sx, myy + 12), 2)
        elif name == "Glacier":
            pygame.draw.rect(self.screen, (250, 252, 255), (mxx + 2, myy, m["w"] - 4, 3), border_radius=2)
        elif name == "Tide Vault":
            pygame.draw.ellipse(self.screen, (200, 240, 255), (mxx + m["w"] / 2 - 90, myy + 1, 180, 7))
        elif name == "Cloud Nine":
            for sx in range(int(mxx + 16), int(mxx + m["w"] - 4), 44):
                pygame.draw.circle(self.screen, (255, 255, 255), (sx, int(myy + 1)), 7)

    def draw_stage(self, idx, shake_x=0, shake_y=0):
        st = STAGES[idx]
        glow = st["glow"]
        pulse = 0.5 + 0.5 * math.sin(self.t_global * 3)
        m = st["main"]
        # soft under-glow beneath main platform
        pygame.draw.ellipse(self.glow_layer, (*glow, int(40 + 30 * pulse)),
                            (m["x"] - 30 + shake_x, m["y"] + 22 + shake_y, m["w"] + 60, 30))
        for pi, pl in enumerate([st["main"]] + st["plats"]):
            self._slab(pl["x"] + shake_x, pl["y"] + shake_y, pl["w"], st,
                       pl is m, pi)
        # supports under the main platform (per material: pillars / roots / crystals)
        self._main_supports(m, st, shake_x, shake_y)
        # theme dressing on the main platform (per arena)
        self._main_dressing(m, st, shake_x, shake_y)
        # bounce pads
        for pd in st.get("pads", []):
            px, py, pw = pd["x"] + shake_x, pd["y"] + shake_y, pd["w"]
            pygame.draw.rect(self.screen, (30, 32, 48), (px - 4, py - 14, pw + 8, 16), border_radius=6)
            for ci in range(3):
                cxp = px + 8 + ci * (pw - 16) / max(1, 2)
                pygame.draw.line(self.screen, (150, 150, 170), (cxp, py - 12), (cxp, py - 2), 2)
            pygame.draw.rect(self.screen, st["glow"], (px, py - 18, pw, 8), border_radius=4)
            pygame.draw.circle(self.glow_layer, (*st["glow"], 70), (int(px + pw / 2), int(py - 14)), 12)
        # phasing platforms (solid while active, ghost outline while gone)
        for ph in st.get("phases", []):
            px, py, pw = ph["x"] + shake_x, ph["y"] + shake_y, ph["w"]
            if self.phase_on(ph):
                pygame.draw.rect(self.screen, st["plat"], (px, py, pw, 14), border_radius=6)
                pygame.draw.rect(self.screen, (255, 255, 255), (px, py, pw, 4), border_radius=2)
                pygame.draw.line(self.screen, st["glow"], (px, py + 15), (px + pw, py + 15), 2)
            else:
                pygame.draw.rect(self.screen, st["glow"], (px, py, pw, 14), 1, border_radius=6)
        # spike strips (themed per arena: thorns / ice shards / hot metal)
        for sp in st.get("spikes", []):
            sx, sy, sw = sp["x"] + shake_x, sp["y"] + shake_y, sp["w"]
            skin = st.get("skin", "")
            if skin == "thorn":
                scol, tip = (90, 160, 90), (200, 230, 170)
            elif skin == "frost":
                scol, tip = (150, 200, 235), (240, 250, 255)
            elif skin in ("foundry", "magmarock", "obsidian"):
                scol, tip = (200, 90, 50), (255, 190, 110)
            else:
                scol, tip = (200, 60, 60), (255, 150, 150)
            n = max(2, int(sw // 18))
            for ti in range(n):
                tx0 = sx + ti * sw / n
                pygame.draw.polygon(self.screen, scol,
                                    [(tx0, sy), (tx0 + sw / n / 2, sy - 15), (tx0 + sw / n, sy)])
                pygame.draw.line(self.screen, tip, (tx0 + sw / n / 2, sy - 15),
                                 (tx0 + sw / n / 2, sy - 4), 1)
            pygame.draw.circle(self.glow_layer, (scol[0], scol[1], scol[2], 60),
                               (int(sx + sw / 2), int(sy - 8)), 14)
        # lava pools (animated surface + bubbles + glow)
        for lv in st.get("lava", []):
            lx, ly, lw = lv["x"] + shake_x, lv["y"] + shake_y, lv["w"]
            pygame.draw.rect(self.screen, (120, 30, 10), (lx - 4, ly - 6, lw + 8, 10), border_radius=4)
            pygame.draw.rect(self.screen, (220, 80, 20), (lx, ly - 4, lw, 7), border_radius=3)
            pts = [(lx + x, ly - 4 + math.sin(x * 0.09 + self.t_global * 5) * 2.5)
                   for x in range(0, int(lw) + 1, 12)]
            if len(pts) > 1:
                pygame.draw.lines(self.screen, (255, 190, 90), False, pts, 2)
            pygame.draw.circle(self.glow_layer, (255, 120, 40, 70), (int(lx + lw / 2), int(ly - 4)), 20)
            if random.random() < 0.15 and len(self.parts) < 240:
                self.parts.append(Particle(lx + random.uniform(0, lw) + self.cam, ly - 6,
                                           random.uniform(-20, 20), random.uniform(-120, -40),
                                           0.5, (255, 150, 60), 4, grav=-200, glow=True))
        # breakable platforms (cracks grow as hp drops, ghost outline while regenerating)
        for b in getattr(self, "brk", []):
            bx, by, bw = b["x"] + shake_x, b["y"] + shake_y, b["w"]
            if b["hp"] <= 0:
                pygame.draw.rect(self.screen, st["glow"], (bx, by, bw, 14), 1, border_radius=6)
                if b.get("regen", 0) > 0:
                    frac = 1.0 - b["regen"] / 12.0
                    pygame.draw.rect(self.screen, st["glow"],
                                     (bx, by + 16, bw * max(0.0, min(1.0, frac)), 3), border_radius=2)
                continue
            maxhp = next((d["hp"] for d in st.get("breakables", [])
                          if d["x"] == b["x"] and d["y"] == b["y"]), 3)
            frac = b["hp"] / max(1, maxhp)
            base = mix(st["plat"], (60, 30, 20), 0.35 * (1 - frac))
            pygame.draw.rect(self.screen, (10, 12, 20), (bx - 4, by + 8, bw + 8, 24), border_radius=7)
            pygame.draw.rect(self.screen, mix(base, (0, 0, 0), 0.35), (bx, by + 6, bw, 14), border_radius=6)
            pygame.draw.rect(self.screen, base, (bx, by, bw, 13), border_radius=6)
            pygame.draw.rect(self.screen, (255, 220, 160), (bx, by, bw, 4), border_radius=2)
            pygame.draw.line(self.screen, st["glow"], (bx, by + 15), (bx + bw, by + 15), 2)
            if frac < 1.0:
                nck = int((1 - frac) * 4) + 1
                for ci in range(nck):
                    cxp = bx + (ci + 1) * bw / (nck + 1)
                    pygame.draw.line(self.screen, (20, 10, 8), (cxp, by + 2), (cxp + 6, by + 13), 2)
                pygame.draw.circle(self.glow_layer, (255, 120, 80, 50),
                                   (int(bx + bw / 2), int(by + 8)), 12)

    def draw_projs(self, shx=0, shy=0):
        for pr in self.projs:
            for i, (tx, ty) in enumerate(pr.trail):
                col = pr.color
                pygame.draw.circle(self.screen, (col[0], col[1], col[2]),
                                   (int(tx + shx), int(ty + shy)), max(1, pr.size * (i + 1) // 9))
                _ = tx, ty
            x, y = pr.x + shx, pr.y + shy
            pygame.draw.circle(self.screen, pr.color, (int(x), int(y)), pr.size + 4)
            if pr.kind == "fire":
                pygame.draw.polygon(self.screen, (255, 220, 120),
                                    [(x - pr.size, y), (x + pr.size, y), (x + pr.vx * 0.03, y - pr.size - 3)])
            elif pr.kind == "ice":
                pygame.draw.polygon(self.screen, (230, 250, 255),
                                    [(x - pr.size, y), (x, y - pr.size - 2), (x + pr.size, y), (x, y + pr.size + 2)])
            elif pr.kind == "rock":
                pygame.draw.polygon(self.screen, (140, 115, 85),
                                    [(x - pr.size, y - 4), (x - 3, y - pr.size), (x + pr.size, y), (x, y + pr.size)])
            elif pr.kind == "needle":
                pygame.draw.line(self.screen, (240, 220, 255), (x - pr.size - 6, y), (x + pr.size + 6, y), 3)
            elif pr.kind == "venom":
                pygame.draw.line(self.screen, (170, 255, 120), (x - pr.size - 6, y), (x + pr.size + 6, y), 3)
                pygame.draw.circle(self.screen, (110, 190, 70), (int(x), int(y)), 3)
            elif pr.kind == "meteor":
                pygame.draw.polygon(self.screen, (255, 220, 130),
                                    [(x - pr.size, y - pr.size), (x + pr.size, y - pr.size), (x, y + pr.size + 4)])
            elif pr.kind == "disc":
                pygame.draw.circle(self.screen, (230, 250, 255), (int(x), int(y)), pr.size)
                pygame.draw.circle(self.screen, pr.color, (int(x), int(y)), max(2, pr.size - 4), 2)
            elif pr.kind == "well":
                pygame.draw.circle(self.screen, (20, 5, 25), (int(x), int(y)), pr.size + 3)
                pygame.draw.circle(self.screen, pr.color, (int(x), int(y)), pr.size)
                pygame.draw.arc(self.screen, (255, 255, 255),
                                (x - pr.size - 5, y - pr.size - 5, (pr.size + 5) * 2, (pr.size + 5) * 2),
                                self.t_global * 4, self.t_global * 4 + 4.0, 2)
            else:
                pygame.draw.circle(self.screen, (255, 255, 255), (int(x), int(y)), pr.size // 2)
            self.blit_add(x, y, pr.size * 3, pr.color, 100)

    def draw_modes(self):
        """Event-driven visual modes: Blood, Void, Dark rainbow, Rainbow, Chaos ultra,
        Solaris, Cosmosis, Glitch, Screen-shake dust is instant, Black-and-white."""
        s = self.screen
        L = self.glow_layer
        t = self.t_global
        if len(self.fighters) != 2:
            return
        a, b = self.fighters
        # BLOOD — anyone at 100%+
        if any(f.alive() and f.pct >= 100 for f in (a, b)):
            va = int(46 + 26 * math.sin(t * 5))
            for rct in ((0, 0, W, 14), (0, H - 14, W, 14), (0, 0, 14, H), (W - 14, 0, 14, H)):
                pygame.draw.rect(L, (200, 20, 25, va), rct)
        # VOID — anyone offstage in danger
        st = STAGES[self.stage_idx]
        m = st["main"]
        if any(f.alive() and (f.x < m["x"] - 20 or f.x > m["x"] + m["w"] + 20 or f.y > m["y"] + 80)
               for f in (a, b)):
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((30, 8, 60, 70))
            s.blit(ov, (0, 0))
            if len(self.parts) < 240 and random.random() < 0.4:
                self.parts.append(Particle(random.uniform(0, W) + self.cam, H + 6,
                                           random.uniform(-16, 16), random.uniform(-80, -30),
                                           random.uniform(1.5, 3), (170, 120, 255), 3, grav=-30, glow=True))
        # DARK RAINBOW — both on last stock
        if self.phase == "battle" and a.alive() and b.alive() and a.stocks == 1 and b.stocks == 1:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((5, 5, 16, 95))
            s.blit(ov, (0, 0))
            cols = [(255, 90, 90), (255, 210, 110), (130, 255, 150), (130, 200, 255), (200, 140, 255)]
            ci = int(t * 6) % len(cols)
            for k, rct in enumerate(((0, 0, W, 8), (0, H - 8, W, 8), (0, 0, 8, H), (W - 8, 0, 8, H))):
                pygame.draw.rect(s, cols[(ci + k) % len(cols)], rct)
        # RAINBOW — sudden death
        if self.sudden:
            hue = (int(127 + 127 * math.sin(t * 3)), int(127 + 127 * math.sin(t * 3 + 2.1)),
                   int(127 + 127 * math.sin(t * 3 + 4.2)))
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((*hue, 34))
            s.blit(ov, (0, 0))
        # CHAOS ULTRA — both ultimates full
        if self._chaos_on:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((255, 180, 80, 26))
            s.blit(ov, (0, 0))
            if len(self.parts) < 240 and random.random() < 0.5:
                self.parts.append(Particle(random.uniform(0, W) + self.cam, random.uniform(0, H),
                                           random.uniform(-30, 30), random.uniform(-120, -40),
                                           random.uniform(0.5, 1),
                                           random.choice([(255, 210, 120), (255, 150, 200), (150, 220, 255)]),
                                           4, grav=-60, glow=True))
        # SOLARIS — golden burst at GO
        if self.m_solar > 0:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((255, 220, 150, int(110 * self.m_solar)))
            s.blit(ov, (0, 0))
            rays = pygame.Surface((W, H), pygame.SRCALPHA)
            for i in range(12):
                ang = i / 12 * math.pi * 2 + t
                r0, r1 = 60 + (1 - self.m_solar) * 200, 120 + (1 - self.m_solar) * 420
                pygame.draw.line(rays, (255, 240, 200, int(140 * self.m_solar)),
                                 (W / 2 + math.cos(ang) * r0, H / 2 + math.sin(ang) * r0),
                                 (W / 2 + math.cos(ang) * r1, H / 2 + math.sin(ang) * r1), 3)
            s.blit(rays, (0, 0))
        # COSMOSIS — violet starfield on ultimates
        if self.m_cosmos > 0:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((40, 20, 90, int(80 * min(1, self.m_cosmos))))
            s.blit(ov, (0, 0))
            for i in range(40):
                sx = (i * 173) % W
                sy = (i * 131) % H
                tw2 = 0.4 + 0.6 * abs(math.sin(t * 4 + i))
                pygame.draw.circle(s, (220, 200, 255), (sx, sy), 1 + int(tw2 * 2))
        # GLITCH — rgb slices on breaks/counters/KOs
        if self.m_glitch > 0:
            for _ in range(7):
                gy = random.uniform(0, H)
                gh = random.uniform(4, 22)
                col = random.choice([(0, 255, 255, 70), (255, 0, 255, 70), (255, 255, 255, 50)])
                pygame.draw.rect(s, col, (0, int(gy), W, int(gh)))
        # BLACK AND WHITE — match-deciding end phase
        if self.phase == "end":
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((200, 200, 210, 85))
            s.blit(ov, (0, 0))

    def draw_hud(self):
        s = self.screen
        a, b = self.fighters
        # slim timer pill (top center, never covers the fight)
        urgent = self.sudden or self.timer < 30
        self.panel(W // 2 - 62, 6, 124, 36, accent=UI_RED if urgent else UI_GOLD, alpha=200)
        mm, ss = int(self.timer) // 60, int(self.timer) % 60
        pulse = 1 + (0.08 * math.sin(self.t_global * 10) if urgent else 0)
        tim = self.font(int(21 * pulse)).render(f"{mm}:{ss:02d}", True,
                                                UI_RED if urgent else UI_TEXT)
        s.blit(tim, (W // 2 - tim.get_width() // 2, 7))
        sub = "SUDDEN DEATH" if self.sudden else STAGES[self.stage_idx]["name"]
        self.ctext(sub, W // 2, 29, 9, UI_RED if urgent else UI_DIM, mono=True)
        self.draw_panel(a, 8, 6, True)
        self.draw_panel(b, W - 8, 6, False)
        if self.pad_joy is not None:
            self.text("PAD · " + self.pad_name[:16], W - 180, H - 20, 11, UI_DIM)
        if self.net_role:
            nm = "HOST" if self.net_role == "host" else "GUEST"
            extra = ""
            if self.net_is_host():
                extra = " +CPU" if not self.net_guest_present() else " vs GUEST"
            self.text("NET·" + nm + extra, 8, H - 20, 11, UI_GREEN)

    def draw_panel(self, f, x, y, left):
        # slim top-corner chip: icon + % + stocks + ult + cooldowns, out of the way
        s = self.screen
        pw, ph = 196, 44
        ox = x if left else x - pw
        mine = self.fighters[0] is f
        team = (90, 160, 255) if mine else UI_RED
        if f.combo >= 2:
            cs = self.font(14).render(f"x{f.combo}", True, UI_GOLD)
            cxp = ox + (44 if left else pw - 44)
            s.blit(cs, (cxp - cs.get_width() // 2, y + ph + 2))
        self.panel(ox, y, pw, ph, accent=team, alpha=150)
        fill = (pw - 4) * min(1.0, f.ult / 100)
        if fill > 0:
            pygame.draw.rect(s, UI_GOLD, (ox + 2, y + 1, fill, 3), border_radius=2)
        if f.ult >= 100:
            pygame.draw.rect(s, (255, 225, 140), (ox, y, pw, ph), 2, border_radius=10)
        icx = ox + (20 if left else pw - 20)
        pygame.draw.circle(s, team, (int(icx), int(y + 22)), 13, 2)
        self.draw_icon(s, f.cid, int(icx), int(y + 22), 10)
        tag = "P1" if mine else f"CPU{self.ai_level + 1}"
        pop = 1 + min(0.5, f.pop * 2.0)
        pct = self.font(int(21 * pop)).render(f"{f.pct:.0f}%", True, self.pct_color(f.pct))
        if left:
            self.text(tag, ox + 36, y + 3, 9, team, mono=True)
            s.blit(pct, (ox + 36, y + 12))
            for i in range(STOCKS):
                sx = ox + 38 + i * 13
                if i < f.stocks:
                    pygame.draw.circle(s, team, (sx, y + 37), 4)
                else:
                    pygame.draw.circle(s, (70, 70, 85), (sx, y + 37), 4, 1)
            for i, cd in enumerate((f.cd_nb, f.cd_up, f.cd_down)):
                dx = ox + pw - 12 - i * 13
                pygame.draw.circle(s, f.d["skin"]["glow"] if cd <= 0 else (70, 72, 90),
                                   (dx, y + 35), 3)
        else:
            tagw = self.font(9, mono=True).size(tag)[0]
            self.text(tag, ox + pw - 36 - tagw, y + 3, 9, team, mono=True)
            s.blit(pct, (ox + pw - 36 - pct.get_width(), y + 12))
            for i in range(STOCKS):
                sx = ox + pw - 38 - i * 13
                if i < f.stocks:
                    pygame.draw.circle(s, team, (sx, y + 37), 4)
                else:
                    pygame.draw.circle(s, (70, 70, 85), (sx, y + 37), 4, 1)
            for i, cd in enumerate((f.cd_nb, f.cd_up, f.cd_down)):
                dx = ox + 12 + i * 13
                pygame.draw.circle(s, f.d["skin"]["glow"] if cd <= 0 else (70, 72, 90),
                                   (dx, y + 35), 3)

    def pct_color(self, v):
        if v < 30:
            return (255, 255, 255)
        if v < 70:
            return (255, 235, 120)
        if v < 110:
            return (255, 165, 80)
        return (255, 80, 70)

    def draw_announce(self):
        a = self.announce
        if not a:
            return
        prog = a["t"] / max(0.01, a["dur"])
        alpha = 255 if prog < 0.8 else int(255 * (1 - prog) / 0.2)
        if a["text"] in ("3", "2", "1"):
            scale = 1.35 - 0.35 * min(1, a["t"] * 6)
            img = self.font(int(a["size"] * scale)).render(a["text"], True, a["color"])
            sh = self.font(int(a["size"] * scale)).render(a["text"], True, (10, 10, 16))
            cx, cy = W // 2, H // 2 - 150
            for ox, oy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
                self.screen.blit(sh, (cx - sh.get_width() // 2 + ox, cy + oy))
            self.screen.blit(img, (cx - img.get_width() // 2, cy))
            rr = int(44 + a["t"] * 300)
            ring = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.circle(ring, (*a["color"], int(190 * max(0, 1 - a["t"] / 0.55))), (cx, cy + 40), rr, 4)
            self.screen.blit(ring, (0, 0))
            return
        slide = (1 - ease_out(min(1, a["t"] / 0.25))) * -140
        band_y = H // 2 - 178
        band = pygame.Surface((W, 100), pygame.SRCALPHA)
        band.fill((5, 6, 14, 205))
        self.screen.blit(band, (0, band_y))
        pygame.draw.rect(self.screen, a["color"], (slide, band_y, 10, 100))
        pygame.draw.rect(self.screen, a["color"], (W - 10 - slide, band_y, 10, 100))
        scale = 1.18 - 0.18 * min(1, a["t"] * 5)
        img = self.font(int(a["size"] * scale)).render(a["text"], True, a["color"])
        sh = self.font(int(a["size"] * scale)).render(a["text"], True, (10, 10, 16))
        cx = W // 2 + slide
        cy = band_y + 50 - img.get_height() // 2 - (14 if a["sub"] else 0)
        img.set_alpha(max(0, alpha))
        sh.set_alpha(max(0, alpha))
        for ox, oy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
            self.screen.blit(sh, (cx - sh.get_width() // 2 + ox, cy + oy))
        self.screen.blit(img, (cx - img.get_width() // 2, cy))
        if a["sub"]:
            sub = self.font(16).render(a["sub"], True, (240, 240, 245))
            sub.set_alpha(max(0, alpha))
            self.screen.blit(sub, (cx - sub.get_width() // 2, cy + img.get_height() + 4))

    def draw_floats(self, shx=0, shy=0):
        for t in self.texts:
            img = self.f.render(t["s"], True, t["color"])
            self.screen.blit(img, (t["x"] - img.get_width() // 2 + shx, t["y"] + shy))

    def draw_moves(self):
        """Compact translucent side move-list (toggle with TAB)."""
        f = self.fighters[0]
        x, y, w = W - 216, 76, 204
        rows = [
            ("Z·J·LMB", "Jab / Tilt / Air", None),
            ("X·K", "Charged smash", None),
            ("C", f"{f.d['proj']['kind'].title()} shot", "cd_nb"),
            ("V", "Up special", "cd_up"),
            ("S·E", DOWN_SHORT[f.d["down"]["kind"]], "cd_down"),
            ("SHIFT", "Dash i-frames", "cd_dash"),
            ("RMB", "SMART move", None),
            ("F", "ULTIMATE", "ULT"),
            ("L", "Shield", None),
            ("SPC", "Jump x2", None),
            ("v", "Drop / fall", None),
        ]
        h = 30 + len(rows) * 22 + 8
        self.panel(x, y, w, h, accent=UI_CYAN, alpha=140)
        self.text("MOVES", x + 10, y + 7, 12, UI_TEXT)
        for i, (keys, name, cd) in enumerate(rows):
            ry = y + 30 + i * 22
            kw = 62
            pygame.draw.rect(self.screen, (24, 30, 50), (x + 8, ry, kw, 18), border_radius=4)
            self.ctext(keys, x + 8 + kw // 2, ry + 2, 10, UI_GOLD, mono=True)
            self.text(name, x + 76, ry + 2, 11, UI_TEXT)
            if cd:
                ready = (f.ult >= 100) if cd == "ULT" else getattr(f, cd) <= 0
                pygame.draw.circle(self.screen, UI_GREEN if ready else (80, 82, 100),
                                   (int(x + w - 13), int(ry + 9)), 4)

    def do_title_action(self, a):
        if a == "fight":
            self.net_stop()
            self.goto_select()
        elif a == "help":
            self.state = "help"
        elif a == "online":
            self.state = "online"
            self.menu_idx = 0
        elif a == "quit":
            self.quit_req = True

    def do_pause_action(self, a):
        if a == "resume":
            self.paused = False
        elif a == "rematch":
            self.paused = False
            self.start_match()
        elif a == "select":
            self.paused = False
            self.goto_select()
        elif a == "title":
            self.paused = False
            self.state = "title"

    def do_gameover_action(self, a):
        if a == "rematch":
            self.start_match()
        elif a == "select":
            self.goto_select()
        elif a == "title":
            self.state = "title"

    def draw_title(self):
        self.draw_bg(2)
        t = self.t_global
        # demo fighters facing off (marked P1 blue vs CPU red)
        self.fighters = self.demo
        for d in self.demo:
            d.anim = t
            d.on_ground = True
        self.draw_stage(1)
        self.draw_fighter(self.demo[0])
        self.draw_fighter(self.demo[1])
        # legibility band + shine sweep
        band = pygame.Surface((W, 260), pygame.SRCALPHA)
        band.fill((5, 6, 14, 150))
        self.screen.blit(band, (0, 36))
        sx = ((t * 170) % (W + 500)) - 250
        sh = pygame.Surface((90, 180), pygame.SRCALPHA)
        pygame.draw.polygon(sh, (255, 255, 255, 26), [(30, 0), (90, 0), (60, 180), (0, 180)])
        self.screen.blit(sh, (sx, 36))
        # logo with depth
        rise = int((1 - min(1, self.state_t / 0.45)) * -22)
        y0 = 56 + rise
        for ox, oy, col in ((3, 4, (70, 40, 8)), (0, 0, UI_GOLD)):
            img = self.font(92).render("RIFTBREAK", True, col)
            self.screen.blit(img, (W // 2 - img.get_width() // 2 + ox, y0 + oy))
        sm = self.font(34).render("S M A S H", True, UI_CYAN)
        self.screen.blit(sm, (W // 2 - sm.get_width() // 2, y0 + 100))
        self.blit_add(W // 2, 130, 150, (255, 200, 100), 70)
        self.ctext("1v1 arena fighter · 10 fighters · 4-stock rounds · 3:00", W // 2, y0 + 142, 16, UI_DIM)
        # menu buttons
        labels = [("FIGHT", "fight", "Jump into a 1v1"),
                  ("HOW TO PLAY", "help", "Controls & rules"),
                  ("ONLINE", "online", "Versus over LAN"),
                  ("QUIT", "quit", "Exit to desktop")]
        self.title_buttons = [Button(lb, a, sub=s) for lb, a, s in labels]
        mpos = pygame.mouse.get_pos()
        for i, b in enumerate(self.title_buttons):
            b.draw(self.screen, self, W // 2 - 125, 278 + i * 52,
                   self.menu_idx == i, b.rect.collidepoint(mpos))
        w = self.save.get("wins", {})
        tot = sum(w.values()) if isinstance(w, dict) else 0
        self.ctext(f"{tot} WINS · {self.save.get('games', 0)} GAMES · STREAK x{self.save.get('streak', 0)} (BEST {self.save.get('best_streak', 0)})", W // 2, 470, 14, UI_DIM, mono=True)
        padline = f"PAD: {self.pad_name}" if self.pad_joy is not None else "PAD: none — boot SN30 with Start+X"
        self.ctext(padline, W // 2, 486, 12, UI_GREEN if self.pad_joy is not None else UI_DIM)
        self.ctext("↑↓ + ENTER or click · F11 fullscreen · blast them off-screen!", W // 2, 500, 14, UI_DIM)

    def draw_help(self):
        self.draw_bg(2)
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((5, 6, 14, 170))
        self.screen.blit(dim, (0, 0))
        self.ctext("HOW TO PLAY", W // 2, 26, 40, UI_GOLD)
        self.ctext("Launch the CPU past the blast zone · 4 stocks · 3:00", W // 2, 74, 15, UI_DIM)
        rows = [[("MOVE", "A / D  or  ← →"), ("JUMP ×2", "SPACE / W / ↑"),
                 ("ATTACK", "Z / J / LEFT CLICK"), ("SMASH (hold)", "X / K — release")],
                [("NEUTRAL SPECIAL", "C"), ("UP SPECIAL (recover)", "V"),
                 ("SUPER (down sp)", "S / E — unique"), ("ULTIMATE (full bar)", "F")],
                [("DASH (i-frames)", "SHIFT"), ("SHIELD (hold)", "L"),
                 ("DROP / FAST-FALL", "↓ ARROW"), ("PAUSE", "P / ESC")]]
        y = 112
        for group in rows:
            x = 60
            for label, keys in group:
                if not label:
                    x += 200
                    continue
                self.panel(x, y, 192, 62, alpha=200)
                self.text(label, x + 12, y + 6, 12, UI_DIM)
                self.text(keys, x + 12, y + 28, 15, UI_TEXT)
                x += 204
            y += 72
        self.panel(60, y + 2, 840, 108, accent=UI_CYAN, alpha=200)
        tips = ["% = launch power: the higher their %, the further they fly. Items drop in — STARs, HAMMERS, ULT ORBs!",
                "Shield blocks — but it breaks. Dash has i-frames. Double jump + UP SPECIAL to recover.",
                "RIGHT CLICK is SMART: counters aggression, dashes danger, heavies kill-% foes. TAB = move list.",
                "S = SUPER (your DOWN SPECIAL). F = ULTIMATE at full bar. ↓ drops. F11 fullscreen."]
        for i, ln in enumerate(tips):
            self.text("▸  " + ln, 80, y + 14 + i * 26, 14, UI_TEXT)
        self.ctext("PAD (XInput: boot SN30 with Start+X): dpad move · A jump · X atk · B smash · Y spec · LB tap dash/hold shield",
                   W // 2, H - 100, 11, UI_DIM)
        self.ctext("RB recover · SEL super · LB+RB ult · dpad in menus, A confirm, B back",
                   W // 2, H - 86, 11, UI_DIM)
        padst = f"STATUS: {self.pad_name} · last input: {self.pad_last}" if self.pad_joy is not None \
            else f"STATUS: none detected · last input: {self.pad_last} — connect the pad, then press any button"
        self.ctext(padst, W // 2, H - 72, 11, UI_GREEN if self.pad_joy is not None else (255, 150, 120))
        self.help_back = Button("BACK", "back", w=220, h=44)
        self.help_back.draw(self.screen, self, W // 2 - 110, H - 56, True,
                            self.help_back.rect.collidepoint(pygame.mouse.get_pos()))

    def fit_text(self, s, size, maxw, mono=False):
        if self.font(size, mono=mono).size(s)[0] <= maxw:
            return s
        while s and self.font(size, mono=mono).size(s + "...")[0] > maxw:
            s = s.rsplit(" ", 1)[0]
        return s + "..."

    def draw_css_pane(self, x, y, w, h, cid, tag, accent, mirror):
        self.panel(x, y, w, h, accent=accent, alpha=235)
        d = FIGHTERS[cid]
        fx = x + (72 if not mirror else w - 72)
        f = self._prev_for(cid)
        f.anim = self.t_global
        f.on_ground = True
        f.facing = -1 if mirror else 1
        sc = 0.85
        body = pygame.transform.scale(self.render_fighter_3d(f), (int(160 * sc), int(160 * sc)))
        feet = y + h - 14
        pygame.draw.circle(self.glow_layer, (*accent, 55), (int(fx), int(feet - 55)), 52, 3)
        pygame.draw.ellipse(self.screen, (0, 0, 0, 90), (int(fx - 36), int(feet), 72, 11))
        self.screen.blit(body, (int(fx - 80 * sc), int(feet - 146 * sc)))
        tx = x + 132 if not mirror else x + 14
        self.text(tag, tx, y + 10, 12, accent, mono=True)
        self.text(d["name"], tx, y + 26, 21, UI_TEXT)
        self.text(d["title"], tx, y + 50, 12, UI_DIM)
        self.text(self.fit_text(d["ability"], 11, w - 165, mono=True), tx, y + 68, 11, UI_GOLD, mono=True)
        for j, (lb, v) in enumerate([("POW", d["power"] / 1.5), ("SPD", d["run"] / 300), ("WGT", d["weight"] / 1.6)]):
            by = y + 90 + j * 22
            self.text(lb, tx, by, 11, UI_DIM, mono=True)
            pygame.draw.rect(self.screen, (30, 32, 48), (tx + 44, by, w - 192, 11), border_radius=5)
            pygame.draw.rect(self.screen, d["skin"]["glow"],
                             (tx + 44, by, (w - 192) * max(0.08, min(1, v)), 11), border_radius=5)
        self.text(self.fit_text(d.get("story", ""), 10, w - 170), tx, y + 150, 10, (170, 176, 200))

    def draw_select(self):
        self.screen.fill(UI_BG)
        sel = self.sel
        # header
        self.panel(0, 0, W, 50, accent=UI_GOLD, alpha=255, radius=0)
        self.text("SELECT FIGHTER", 20, 8, 24, UI_TEXT)
        step = "2 · STAGE" if sel["lock"] else "1 · FIGHTER"
        self.text(step, 300, 15, 14, UI_GOLD, mono=True)
        d_cpu = FIGHTERS[self.cpucid]
        self.panel(W - 300, 6, 288, 38, accent=UI_RED, alpha=255, radius=10)
        self.draw_icon(self.screen, self.cpucid, W - 274, 25, 13)
        self.text(f"CPU · {d_cpu['name']}", W - 252, 8, 14, UI_TEXT)
        self.text("click / T to reroll", W - 252, 27, 11, UI_DIM)
        self.cpu_chip = pygame.Rect(W - 300, 6, 288, 38)
        # difficulty strip
        dn = DIFFS[self.ai_level]["name"]
        self.ctext("CPU LEVEL", 330, 58, 12, UI_DIM, mono=True)
        self.diff_btns = [(pygame.Rect(408, 54, 34, 26), -1), (pygame.Rect(592, 54, 34, 26), +1)]
        for rect, _ in self.diff_btns:
            pygame.draw.rect(self.screen, UI_PANEL2, rect, border_radius=6)
            pygame.draw.rect(self.screen, UI_EDGE, rect, 1, border_radius=6)
        self.ctext("◀", 425, 55, 15, UI_GOLD)
        self.ctext("▶", 609, 55, 15, UI_GOLD)
        self.panel(448, 54, 138, 26, accent=UI_GOLD, alpha=255, radius=6)
        self.ctext(f"LV{self.ai_level + 1} · {dn}", 517, 59, 13, UI_TEXT, mono=True)
        self.text("Y to change", 636, 59, 12, UI_DIM)
        # hero panes (Smash-style: chosen fighters up top)
        cur_idx = sel["row"] * 5 + sel["col"]
        if cur_idx >= len(ROSTER):
            cur_idx = len(ROSTER) - 1
        cur_cid = self.p1cid if sel["lock"] else ROSTER[cur_idx]
        self.draw_css_pane(14, 86, 460, 166, cur_cid, "P1 · YOU", (90, 160, 255), False)
        self.draw_css_pane(486, 86, 460, 166, self.cpucid,
                           f"CPU · {DIFFS[self.ai_level]['name']}", UI_RED, True)
        # portrait tile grid (bottom, like Smash CSS)
        self.sel_cards = []
        tw, th2, tgap, tx0 = 176, 76, 8, 24
        for i, cid in enumerate(ROSTER):
            r, c = i // 5, i % 5
            slide = (1 - ease_out(min(1, max(0, self.state_t - 0.04 * i) / 0.28))) * 22
            x, y = tx0 + c * (tw + tgap), 260 + slide + r * (th2 + tgap)
            dd = FIGHTERS[cid]
            cur = (sel["row"] == r and sel["col"] == c and not sel["lock"])
            picked = sel["lock"] and self.p1cid == cid
            dimmed = sel["lock"] and not picked
            rect = pygame.Rect(int(x), int(y), tw, th2)
            self.sel_cards.append((rect, i))
            col = (44, 48, 70) if not (cur or picked) else (62, 54, 40)
            if dimmed:
                col = (26, 28, 42)
            pygame.draw.rect(self.screen, col, rect, border_radius=8)
            pygame.draw.rect(self.screen,
                             UI_GOLD if picked else (UI_TEXT if cur else UI_EDGE),
                             rect, 3 if (cur or picked) else 1, border_radius=8)
            self.draw_icon(self.screen, cid, int(x + 28), int(y + 38), 20)
            self.text(dd["name"], x + 54, y + 10, 14, UI_TEXT if not dimmed else UI_DIM)
            self.text(dd["title"], x + 54, y + 30, 10, UI_DIM)
            pwv = tw - 66
            pygame.draw.rect(self.screen, (28, 30, 46), (x + 54, y + 50, pwv, 8), border_radius=4)
            pygame.draw.rect(self.screen, dd["skin"]["glow"] if not dimmed else (80, 80, 95),
                             (x + 54, y + 50, pwv * max(0.08, min(1, dd["power"] / 1.5)), 8), border_radius=4)
            if self.cpucid == cid:
                pygame.draw.rect(self.screen, UI_RED, (x + tw - 52, y + 5, 47, 18), border_radius=5)
                self.text("CPU", x + tw - 43, y + 6, 11, (255, 255, 255), mono=True)
            if picked:
                pygame.draw.rect(self.screen, UI_GOLD, (x + 5, y + 5, 34, 18), border_radius=5)
                self.text("P1", x + 12, y + 6, 11, (20, 20, 20), mono=True)
        # stage grid (5 cols, dynamic rows; modal after locking a fighter)
        if sel["lock"]:
            dim = pygame.Surface((W, H), pygame.SRCALPHA)
            dim.fill((5, 6, 14, 225))
            self.screen.blit(dim, (0, 0))
            self.text("STAGE — pick your arena", 24, 60, 15, UI_GOLD, mono=True)
        self.stage_cards = []
        if sel["lock"]:
            tw2, th2, tgap, tx0 = 176, 92, 6, 24
            for i in range(len(STAGES)):
                r, c = i // 5, i % 5
                x, y = tx0 + c * (tw2 + tgap), 86 + r * (th2 + tgap)
                rect = pygame.Rect(int(x), int(y), tw2, th2)
                self.stage_cards.append((rect, i))
                cur2 = sel["stage"] == i
                pygame.draw.rect(self.screen, (44, 48, 70) if not cur2 else (62, 54, 40),
                                 rect, border_radius=8)
                pygame.draw.rect(self.screen, UI_GOLD if cur2 else UI_EDGE, rect,
                                 3 if cur2 else 1, border_radius=8)
                self.text(f"{i + 1} · {self.fit_text(STAGES[i]['name'], 12, tw2 - 20)}",
                          x + 10, y + 6, 12, UI_TEXT)
                tags = []
                if STAGES[i].get("wind"):
                    tags.append("WIND")
                if STAGES[i].get("spikes"):
                    tags.append("SPIKES")
                if STAGES[i].get("pads"):
                    tags.append("PADS")
                if STAGES[i].get("ice"):
                    tags.append("ICE")
                if STAGES[i].get("gravm", 1.0) < 1.0:
                    tags.append("LOW-G")
                if STAGES[i].get("phases"):
                    tags.append("PHASE")
                if STAGES[i].get("breakables"):
                    tags.append("BREAK")
                if STAGES[i].get("lava"):
                    tags.append("LAVA")
                self.text(" · ".join(tags) if tags else "CLASSIC", x + 10, y + 22, 10, UI_GOLD, mono=True)
                # mini diorama: sky gradient, layout plats, hazards, glow accent
                dx0, dy0, dw2, dh2 = x + 8, y + 38, tw2 - 16, th2 - 46
                pygame.draw.rect(self.screen, STAGES[i]["top"], (dx0, dy0, dw2, dh2), border_radius=5)
                pygame.draw.rect(self.screen, STAGES[i]["bot"], (dx0, dy0 + dh2 // 2, dw2, dh2 - dh2 // 2),
                                 border_bottom_left_radius=5, border_bottom_right_radius=5)
                k = (tw2 - 24) / float(STAGES[i].get("w", 960))
                oy = y + th2 - 8
                for pl in [STAGES[i]["main"]] + STAGES[i]["plats"]:
                    px, pw2 = x + 12 + pl["x"] * k, max(5, pl["w"] * k)
                    py = oy - (430 - pl["y"]) * 0.06
                    pygame.draw.rect(self.screen, STAGES[i]["plat"], (px, py, pw2, 3), border_radius=2)
                    pygame.draw.line(self.screen, STAGES[i]["glow"], (px, py + 3, px + pw2, py + 3), 1)
                for b in STAGES[i].get("breakables", []):
                    px, pw2 = x + 12 + b["x"] * k, max(5, b["w"] * k)
                    py = oy - (430 - b["y"]) * 0.06
                    pygame.draw.rect(self.screen, STAGES[i]["glow"], (px, py - 3, pw2, 3), 1,
                                     border_radius=1)
                for ph in STAGES[i].get("phases", []):
                    px, pw2 = x + 12 + ph["x"] * k, max(5, ph["w"] * k)
                    py = oy - (430 - ph["y"]) * 0.06
                    pygame.draw.rect(self.screen, (255, 255, 255), (px, py, pw2, 2), border_radius=1)
                for pd in STAGES[i].get("pads", []):
                    px, pw2 = x + 12 + pd["x"] * k, max(4, pd["w"] * k)
                    pygame.draw.line(self.screen, (150, 255, 170), (px, oy - 4), (px + pw2, oy - 4), 2)
                for sp in STAGES[i].get("spikes", []):
                    pygame.draw.line(self.screen, (255, 90, 90),
                                     (x + 12 + sp["x"] * k, oy), (x + 12 + (sp["x"] + sp["w"]) * k, oy), 2)
                for lv in STAGES[i].get("lava", []):
                    pygame.draw.line(self.screen, (255, 140, 60),
                                     (x + 12 + lv["x"] * k, oy), (x + 12 + (lv["x"] + lv["w"]) * k, oy), 2)
            self.ctext("click a stage (or ENTER) to fight · ESC back", W // 2, 500, 12, UI_DIM)
        else:
            self.ctext("click a fighter · Y difficulty · T reroll CPU", W // 2, 500, 12, UI_DIM)
        self.screen.blit(self.glow_layer, (0, 0))

    def _prev_for(self, cid):
        if getattr(self, "_prev_cid", None) != cid:
            self._prev_cid = cid
            self._prev_tmp = Fighter(cid, 0, 0, 1)
            self._prev_tmp.on_ground = True
        return self._prev_tmp

    def draw_vs(self):
        self.screen.fill(UI_BG)
        a, b = FIGHTERS[self.p1cid], FIGHTERS[self.cpucid]
        t = getattr(self, "vs_t", 0.0)
        e = ease_out(min(1, t / 0.5))
        wash = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.circle(wash, (*a["skin"]["main"], 55), (150, H // 2), 270)
        pygame.draw.circle(wash, (*b["skin"]["main"], 55), (W - 150, H // 2), 270)
        self.screen.blit(wash, (0, 0))
        off = (1 - e) * 520
        # P1 card
        self.panel(50 - off, 105, 340, 300, accent=(90, 160, 255))
        self.draw_icon(self.screen, self.p1cid, int(220 - off), 195, 62)
        self.text("P1", int(220 - off) - 100, 128, 14, (90, 160, 255), mono=True)
        self.ctext(a["name"], 220 - off, 272, 34, UI_TEXT)
        self.ctext(a["title"], 220 - off, 312, 14, UI_DIM)
        self.ctext(f"{self.save.get('wins', {}).get(self.p1cid, 0)} wins", 220 - off, 336, 13, UI_GOLD, mono=True)
        st0 = self.save.get("streak", 0)
        if st0 > 0:
            self.ctext(f"STREAK x{st0} · +{int(min(0.20, 0.04 * st0) * 100)}% power",
                       220 - off, 358, 13, (140, 255, 170), mono=True)
        # CPU card
        self.panel(570 + off, 105, 340, 300, accent=UI_RED)
        self.draw_icon(self.screen, self.cpucid, int(740 + off), 195, 62)
        self.text("CPU", int(740 + off) + 62, 128, 14, UI_RED, mono=True)
        self.ctext(b["name"], 740 + off, 272, 34, UI_TEXT)
        self.ctext(b["title"], 740 + off, 312, 14, UI_DIM)
        self.ctext(f"{self.save.get('wins', {}).get(self.cpucid, 0)} wins", 740 + off, 336, 13, UI_GOLD, mono=True)
        self.ctext(f"LV{self.ai_level + 1} · {DIFFS[self.ai_level]['name']}", 740 + off, 358, 13, UI_RED, mono=True)
        # VS emblem with pop
        pop = max(0.01, ease_out_back(min(1, t / 0.6)))
        r = int(56 * pop)
        pygame.draw.circle(self.screen, (24, 18, 8), (W // 2, H // 2 - 40), r + 7)
        pygame.draw.circle(self.screen, UI_GOLD, (W // 2, H // 2 - 40), r, 4)
        self.blit_add(W // 2, H // 2 - 40, r + 30, (255, 200, 110), 90)
        vs = self.font(int(52 * pop)).render("VS", True, UI_GOLD)
        self.screen.blit(vs, (W // 2 - vs.get_width() // 2, H // 2 - 40 - vs.get_height() // 2))
        # stage pill
        self.panel(W // 2 - 200, H // 2 + 120, 400, 58, accent=STAGES[self.stage_idx]["glow"])
        self.ctext(STAGES[self.stage_idx]["name"], W // 2, H // 2 + 128, 18, UI_TEXT)
        self.ctext(f"{STOCKS} STOCKS · 3:00", W // 2, H // 2 + 150, 12, UI_DIM, mono=True)
        if int(t * 2) % 2 == 0:
            self.ctext("ENTER / click to skip", W // 2, H - 40, 13, UI_DIM)

    def draw_gameover(self):
        self.draw_bg(self.stage_idx)
        self.draw_stage(self.stage_idx)
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((4, 5, 12, 165))
        self.screen.blit(dim, (0, 0))
        w = self.winner
        you = w is self.fighters[0]
        col = (140, 190, 255) if you else UI_RED
        pop = ease_out_back(min(1, self.state_t / 0.5))
        ban = self.font(int(84 * max(0.2, pop))).render("VICTORY" if you else "DEFEAT", True, col)
        self.screen.blit(ban, (W // 2 - ban.get_width() // 2, 66))
        self.ctext(f"{w.d['name']} takes the match", W // 2, 158, 16, UI_DIM)
        # stats panel
        self.panel(W // 2 - 270, 196, 540, 148, accent=col)
        a, b = self.fighters
        for i, f in enumerate((a, b)):
            ry = 210 + i * 40
            tag = "YOU" if i == 0 else "CPU"
            self.draw_icon(self.screen, f.cid, W // 2 - 232, ry + 14, 15)
            self.text(f"{tag} · {f.d['name']}", W // 2 - 208, ry, 15, UI_TEXT)
            self.text(f"{f.stocks} left · peak {f.max_pct:.0f}% · best x{f.max_combo}",
                      W // 2 - 208, ry + 20, 12, UI_DIM, mono=True)
        mm, ss = int(self.timer) // 60, int(self.timer) % 60
        tm = f"{mm}:{ss:02d} left" + (" · sudden death" if self.sudden else "")
        self.ctext(tm, W // 2, 292, 13, UI_DIM, mono=True)
        self.text(f"head-to-head wins — YOU {self.save.get('wins', {}).get(a.cid, 0)} · CPU {self.save.get('wins', {}).get(b.cid, 0)}",
                  W // 2 - 270, 308, 12, UI_GOLD, mono=True)
        st = self.save.get("streak", 0)
        if w is self.fighters[0] and st > 0:
            self.text(f"WIN STREAK x{st} · +{int(min(0.20, 0.04 * st) * 100)}% power next match",
                      W // 2 - 270, 326, 12, (140, 255, 170), mono=True)
        elif w is not self.fighters[0]:
            self.text("STREAK LOST — win to start a new one", W // 2 - 270, 326, 12, UI_DIM, mono=True)
        # buttons
        labels = [("REMATCH", "rematch"), ("FIGHTERS", "select"), ("TITLE", "title")]
        self.go_buttons = [Button(lb, ac, w=168, h=48) for lb, ac in labels]
        mpos = pygame.mouse.get_pos()
        x0 = W // 2 - (3 * 168 + 2 * 16) // 2
        for i, btn in enumerate(self.go_buttons):
            btn.draw(self.screen, self, x0 + i * (168 + 16), 368,
                     self.go_idx == i, btn.rect.collidepoint(mpos))
        self.ctext("← → + ENTER · or click", W // 2, 432, 13, UI_DIM)

    def draw_online(self):
        self.draw_bg(2)
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((5, 6, 14, 170))
        self.screen.blit(dim, (0, 0))
        self.ctext("ONLINE VERSUS", W // 2, 70, 44, UI_GOLD)
        self.ctext("LAN: same WiFi · host shares IP · port 7001", W // 2, 125, 14, UI_DIM)
        labels = [("HOST GAME", "host", "LAN: you run the match"),
                  ("JOIN GAME", "join", "LAN: enter the host IP"),
                  ("INTERNET ROOM", "room", "Online: room code, no setup")]
        self.online_buttons = [Button(lb, a, sub=s, w=280) for lb, a, s in labels]
        mpos = pygame.mouse.get_pos()
        for i, b in enumerate(self.online_buttons):
            b.draw(self.screen, self, W // 2 - 140, 180 + i * 62,
                   self.menu_idx == i, b.rect.collidepoint(mpos))
        self.ctext("ESC back", W // 2, 390, 13, UI_DIM)

    def draw_net(self):
        self.draw_bg(2)
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((5, 6, 14, 170))
        self.screen.blit(dim, (0, 0))
        self.ctext("INTERNET ROOM", W // 2, 90, 44, UI_GOLD)
        self.ctext("no port forwarding needed — just share the code", W // 2, 145, 14, UI_DIM)
        labels = [("HOST ROOM", "rhost", "Get a code, wait for friend"),
                  ("JOIN ROOM", "rjoin", "Enter a friend's code")]
        self.net_buttons = [Button(lb, a, sub=s, w=280) for lb, a, s in labels]
        mpos = pygame.mouse.get_pos()
        for i, b in enumerate(self.net_buttons):
            b.draw(self.screen, self, W // 2 - 140, 210 + i * 62,
                   self.menu_idx == i, b.rect.collidepoint(mpos))
        self.ctext("ESC back", W // 2, 360, 13, UI_DIM)

    def draw_ip(self):
        room = getattr(self, "ip_mode", "ip") == "room"
        self.draw_bg(2)
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((5, 6, 14, 170))
        self.screen.blit(dim, (0, 0))
        self.ctext("JOIN ROOM" if room else "JOIN GAME", W // 2, 120, 40, UI_GOLD)
        self.ctext("Type the room code your friend is showing" if room else
                   "Type the host IP shown on their lobby screen", W // 2, 175, 14, UI_DIM)
        self.panel(W // 2 - 220, 220, 440, 64, accent=UI_CYAN)
        cur = self.ip_buf + ("_" if int(self.t_global * 2) % 2 == 0 else "")
        self.ctext(cur or " ", W // 2, 232, 30, UI_TEXT, mono=True)
        if getattr(self, "ip_err", ""):
            self.ctext(self.ip_err, W // 2, 296, 14, UI_RED)
        self.ctext("ENTER connect · ESC back", W // 2, 330, 13, UI_DIM)

    def draw_lobby(self):
        self.draw_bg(self.stage_idx)
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((5, 6, 14, 170))
        self.screen.blit(dim, (0, 0))
        self.ctext("LOBBY — YOU HOST", W // 2, 60, 36, UI_GOLD)
        self.panel(W // 2 - 230, 120, 460, 66, accent=(90, 160, 255))
        self.draw_icon(self.screen, self.p1cid, W // 2 - 180, 153, 22)
        self.text(f"YOU · {FIGHTERS[self.p1cid]['name']}", W // 2 - 145, 132, 17, UI_TEXT)
        self.text(STAGES[self.stage_idx]["name"], W // 2 - 145, 156, 13, UI_DIM)
        self.panel(W // 2 - 230, 198, 460, 66, accent=UI_RED)
        if self.net_guest_cid:
            self.draw_icon(self.screen, self.net_guest_cid, W // 2 - 180, 231, 22)
            self.text(f"GUEST · {FIGHTERS[self.net_guest_cid]['name']}", W // 2 - 145, 210, 17, UI_TEXT)
            self.text("READY", W // 2 - 145, 234, 13, UI_GREEN, mono=True)
        else:
            self.text("GUEST · waiting…", W // 2 - 145, 210, 17, UI_DIM)
            self.text("they pick a fighter on join", W // 2 - 145, 234, 13, UI_DIM)
        self.panel(W // 2 - 230, 276, 460, 56, accent=UI_GOLD)
        if getattr(self, "net_link", None) == "relay":
            self.ctext(f"ROOM CODE  {self.net_room}", W // 2, 286, 24, UI_TEXT, mono=True)
        else:
            self.ctext(f"HOST IP  {self.net_local_ip} : 7001", W // 2, 286, 20, UI_TEXT, mono=True)
        self.ctext("same WiFi (or ZeroTier / Hamachi for internet)", W // 2, 310, 12, UI_DIM)
        if self.net_guest_cid:
            if int(self.t_global * 2) % 2 == 0:
                self.ctext("ENTER — start the match", W // 2, 360, 20, UI_GREEN)
        else:
            self.ctext("waiting for guest…", W // 2, 360, 16, UI_DIM)
        self.ctext("ESC back (closes lobby)", W // 2, 400, 13, UI_DIM)

    def draw_gpick(self):
        self.screen.fill(UI_BG)
        self.panel(0, 0, W, 50, accent=UI_GOLD, alpha=255, radius=0)
        self.text("PICK YOUR FIGHTER (guest)", 20, 10, 22, UI_TEXT)
        self.gpick_cards = []
        tw, th, gap, x0 = 168, 88, 10, 20
        for i, cid in enumerate(ROSTER):
            r, c = i // 5, i % 5
            x, y = x0 + c * (tw + gap), 70 + r * (th + gap)
            rect = pygame.Rect(int(x), int(y), tw, th)
            self.gpick_cards.append((rect, i))
            cur = (self.gpick_idx // 5 == r and self.gpick_idx % 5 == c)
            pygame.draw.rect(self.screen, (58, 52, 40) if cur else (44, 48, 70), rect, border_radius=8)
            pygame.draw.rect(self.screen, UI_GOLD if cur else UI_EDGE, rect, 3 if cur else 1, border_radius=8)
            self.draw_icon(self.screen, cid, int(x + 30), int(y + 44), 22)
            self.text(FIGHTERS[cid]["name"], x + 60, y + 14, 15, UI_TEXT)
            self.text(FIGHTERS[cid]["title"], x + 60, y + 36, 11, UI_DIM)
            ab = self.fit_text(FIGHTERS[cid]["ability"], 10, tw - 72, mono=True)
            self.text(ab, x + 60, y + 54, 10, UI_GOLD, mono=True)
        self.ctext("click / arrows + ENTER — sends your pick to the host", W // 2, H - 40, 13, UI_DIM)
        self.ctext("ESC back", W // 2, H - 22, 13, UI_DIM)

    def draw_gwait(self):
        self.draw_bg(2)
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((5, 6, 14, 170))
        self.screen.blit(dim, (0, 0))
        self.ctext("LOCKED IN", W // 2, 150, 40, UI_GOLD)
        self.draw_icon(self.screen, self.p1cid, W // 2, 250, 54)
        self.ctext(FIGHTERS[self.p1cid]["name"], W // 2, 320, 28, UI_TEXT)
        if int(self.t_global * 2) % 2 == 0:
            self.ctext("waiting for host to start…", W // 2, 370, 16, UI_DIM)
        self.ctext("ESC back", W // 2, 410, 13, UI_DIM)

    def draw(self):
        shx = random.uniform(-self.shake, self.shake) if self.shake else 0
        shy = random.uniform(-self.shake, self.shake) if self.shake else 0
        self.glow_layer.fill((0, 0, 0, 0))
        if self.state == "title":
            self.draw_title()
            self.screen.blit(self.glow_layer, (0, 0))
        elif self.state == "select":
            self.draw_select()
        elif self.state == "help":
            self.draw_help()
        elif self.state == "online":
            self.draw_online()
        elif self.state == "net":
            self.draw_net()
        elif self.state == "ip":
            self.draw_ip()
        elif self.state == "lobby":
            self.draw_lobby()
        elif self.state == "gpick":
            self.draw_gpick()
        elif self.state == "gwait":
            self.draw_gwait()
        elif self.state == "vs":
            self.draw_vs()
        elif self.state == "gameover":
            self.draw_gameover()
        elif self.state == "fight":
            wx = shx - self.cam
            self.draw_bg(self.stage_idx, self.cam)
            self.draw_stage_art(self.stage_idx)
            self.draw_stage(self.stage_idx, wx, shy)
            self.draw_projs(wx, shy)
            self.draw_drops(wx, shy)
            self.draw_echoes(wx, shy)
            for f in self.fighters:
                self.draw_fighter(f, wx, shy)
            self.draw_slashes(wx, shy)
            self.draw_rings(wx, shy)
            for pt in self.parts:
                a = max(0.0, pt.life / pt.max)
                px, py = int(pt.x + wx), int(pt.y + shy)
                if pt.glow:
                    r = max(1, int(pt.size * (0.6 + 0.4 * a)))
                    pygame.draw.circle(self.glow_layer, (*pt.color, int(95 * a)), (px, py), r * 2)
                    pygame.draw.circle(self.screen, pt.color, (px, py), max(1, r // 2))
                elif pt.grow:
                    pygame.draw.circle(self.glow_layer, (*pt.color, int(75 * a)), (px, py), int(max(1, pt.size)))
                else:
                    c = tuple(int(v * a + 20 * (1 - a)) for v in pt.color)
                    pygame.draw.rect(self.screen, c, (px, py, pt.size, pt.size))
            self.draw_modes()
            self.screen.blit(self.glow_layer, (0, 0))
            if self.sudden or self.timer < 10:
                vg = pygame.Surface((W, H), pygame.SRCALPHA)
                va = int(50 + 36 * math.sin(self.t_global * 6))
                pygame.draw.rect(vg, (255, 40, 40, va), (0, 0, W, 12))
                pygame.draw.rect(vg, (255, 40, 40, va), (0, H - 12, W, 12))
                pygame.draw.rect(vg, (255, 40, 40, va), (0, 0, 12, H))
                pygame.draw.rect(vg, (255, 40, 40, va), (W - 12, 0, 12, H))
                self.screen.blit(vg, (0, 0))
            if self.phase == "ko_freeze":
                bh = int(46 * ease_out(min(1, self.phase_t / 0.3)))
                pygame.draw.rect(self.screen, (0, 0, 0), (0, 0, W, bh))
                pygame.draw.rect(self.screen, (0, 0, 0), (0, H - bh, W, bh))
                pygame.draw.line(self.screen, UI_GOLD, (0, bh), (W, bh), 2)
                pygame.draw.line(self.screen, UI_GOLD, (0, H - bh), (W, H - bh), 2)
            if self.ko_flash > 0:
                ka = int(150 * self.ko_flash / 0.25)
                ov = pygame.Surface((W, H), pygame.SRCALPHA)
                ov.fill((255, 255, 255, ka))
                kx, ky = self.ko_x - self.cam, self.ko_y
                for i in range(10):
                    ang = i / 10 * math.pi * 2 + self.t_global * 2
                    pygame.draw.line(ov, (255, 255, 255, ka),
                                     (kx, ky),
                                     (kx + math.cos(ang) * 700, ky + math.sin(ang) * 700), 3)
                self.screen.blit(ov, (0, 0))
                self.blit_add(kx, ky, 170, (255, 240, 210), 190)
            self.draw_hud()
            self.draw_floats(wx, shy)
            self.draw_announce()
            if self.show_moves:
                self.draw_moves()
            else:
                self.ctext("TAB · move list", W // 2, H - 22, 11, UI_DIM, mono=True)
            if self.state == "fight" and getattr(self, "paused", False):
                ov = pygame.Surface((W, H), pygame.SRCALPHA)
                ov.fill((4, 5, 12, 178))
                self.screen.blit(ov, (0, 0))
                self.panel(W // 2 - 165, 108, 330, 322, accent=UI_GOLD)
                self.ctext("PAUSED", W // 2, 122, 32, UI_TEXT)
                if self.net_is_guest():
                    self.ctext("waiting for host…", W // 2, 220, 18, UI_DIM)
                    self.ctext("ESC asks host to resume", W // 2, 260, 14, UI_DIM)
                    self.pause_buttons = []
                else:
                    labels = [("Resume", "resume", "P / ESC"),
                              ("Rematch", "rematch", "ENTER"),
                              ("Character Select", "select", "new matchup"),
                              ("Quit to Title", "title", "give up")]
                    self.pause_buttons = [Button(lb, a, sub=s, w=270, h=52) for lb, a, s in labels]
                    mpos = pygame.mouse.get_pos()
                    for i, btn in enumerate(self.pause_buttons):
                        btn.draw(self.screen, self, W // 2 - 135, 172 + i * 60,
                                 self.paused_idx == i, btn.rect.collidepoint(mpos))
        if self.fade > 0:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, int(255 * min(1, self.fade / 0.35))))
            self.screen.blit(ov, (0, 0))
        self.screen.blit(self.vignette, (0, 0))
        pygame.display.flip()

def move_select(sel, drow, dcol):
    cols = 5
    rows = (len(ROSTER) + cols - 1) // cols
    sel["row"] = (sel["row"] + drow) % rows
    sel["col"] = (sel["col"] + dcol) % cols
    if sel["row"] * cols + sel["col"] >= len(ROSTER):
        sel["col"] = (len(ROSTER) - 1) % cols


def main():
    smoke = "--smoke" in sys.argv
    if smoke:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    g = Game(fullscreen=("--windowed" not in sys.argv and not smoke))
    g.paused = False
    if smoke:
        g.p1cid, g.cpucid, g.stage_idx = "cinder", "disc", 1
        g.start_match()
        g.phase, g.phase_t = "battle", 99
        frames = 0
        kos0 = STOCKS * 2
        while frames < 1500:
            dt = 1 / 60
            g.t_global += dt
            p1, cpu = g.fighters
            ai_control(p1, cpu, STAGES[g.stage_idx], g, dt)
            ai_control(cpu, p1, STAGES[g.stage_idx], g, dt)
            g.update_fighter(p1, cpu, dt)
            g.update_fighter(cpu, p1, dt)
            g.update_projs(dt)
            for pt in list(g.parts):
                pt.update(dt)
                if pt.life <= 0:
                    g.parts.remove(pt)
            if frames == 400:
                cpu.pct = 999  # guarantee a launch -> KO path exercised
                raw_hit(p1, cpu, 10, 900, 6.0, -30, g)
            g.check_ko()
            if frames == 800 and g.phase not in ("end",):
                # force end-of-match path
                g.fighters[1].stocks = 0
                g.fighters[1].state = "dead"
                g.winner = g.fighters[0]
                g.phase, g.phase_t = "end", 2.5
            if frames % 300 == 0:
                print(f"smoke f={frames} p1={p1.pct:.0f}%/{p1.stocks} cpu={cpu.pct:.0f}%/{cpu.stocks} phase={g.phase} projs={len(g.projs)}")
            frames += 1
            if g.phase == "end":
                g.phase_t += dt
                if g.phase_t >= 2.2:
                    break
        left = sum(f.stocks for f in g.fighters)
        print(f"SMOKE-OK frames={frames} stocks_left={left} (started {kos0}) winner={g.winner.d['name'] if g.winner else None}")
        pygame.quit()
        return

    while True:
        dt = min(0.033, g.clock.tick(FPS) / 1000.0)
        g.t_global += dt
        events = pygame.event.get()
        for ev in events:
            if ev.type == pygame.QUIT:
                pygame.quit()
                return
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_F11:
                    g.toggle_fullscreen()
                    continue
                k = ev.key
                if g.state == "title":
                    if k in (pygame.K_UP, pygame.K_w):
                        g.menu_idx = (g.menu_idx - 1) % 4
                    elif k in (pygame.K_DOWN, pygame.K_s):
                        g.menu_idx = (g.menu_idx + 1) % 4
                    elif k in (pygame.K_RETURN, pygame.K_SPACE):
                        g.do_title_action(["fight", "help", "online", "quit"][g.menu_idx])
                elif g.state == "help":
                    if k in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                        g.state = "title"
                elif g.state == "online":
                    if k in (pygame.K_UP, pygame.K_w):
                        g.menu_idx = (g.menu_idx - 1) % 3
                    elif k in (pygame.K_DOWN, pygame.K_s):
                        g.menu_idx = (g.menu_idx + 1) % 3
                    elif k in (pygame.K_RETURN, pygame.K_SPACE):
                        if g.menu_idx == 0:
                            if g.net_start_host():
                                g.goto_select()
                            else:
                                g.state = "title"
                        elif g.menu_idx == 1:
                            g.state = "ip"
                            g.ip_buf = ""
                            g.ip_err = ""
                            g.ip_mode = "ip"
                            g.menu_idx = 0
                        else:
                            g.state = "net"
                            g.menu_idx = 0
                    elif k == pygame.K_ESCAPE:
                        g.state = "title"
                        g.menu_idx = 2
                elif g.state == "net":
                    if k in (pygame.K_UP, pygame.K_w):
                        g.menu_idx = (g.menu_idx - 1) % 2
                    elif k in (pygame.K_DOWN, pygame.K_s):
                        g.menu_idx = (g.menu_idx + 1) % 2
                    elif k in (pygame.K_RETURN, pygame.K_SPACE):
                        if g.menu_idx == 0:
                            if g.net_start_host(link="relay"):
                                g.goto_select()
                            else:
                                g.state = "online"
                        else:
                            g.state = "ip"
                            g.ip_buf = ""
                            g.ip_err = ""
                            g.ip_mode = "room"
                            g.menu_idx = 0
                    elif k == pygame.K_ESCAPE:
                        g.state = "online"
                elif g.state == "ip":
                    if k == pygame.K_ESCAPE:
                        g.state = "online"
                    elif k == pygame.K_RETURN:
                        if getattr(g, "ip_mode", "ip") == "room":
                            if g.net_relay_join(g.ip_buf):
                                g.state = "gpick"
                                g.gpick_idx = 0
                            elif not g.ip_err:
                                g.ip_err = "could not join room"
                        elif g.net_connect(g.ip_buf):
                            g.state = "gpick"
                            g.gpick_idx = 0
                        elif not g.ip_err:
                            g.ip_err = "could not connect — check IP, same WiFi, host lobby open"
                    elif k == pygame.K_BACKSPACE:
                        g.ip_buf = g.ip_buf[:-1]
                        g.ip_err = ""
                    elif ev.unicode and len(g.ip_buf) < 15 and (
                            ev.unicode.isdigit() or ev.unicode == "." or
                            (getattr(g, "ip_mode", "ip") == "room" and ev.unicode.isalnum())):
                        g.ip_buf += ev.unicode.upper() if getattr(g, "ip_mode", "ip") == "room" else ev.unicode
                        g.ip_err = ""
                elif g.state == "select":
                    s = g.sel
                    if not s["lock"]:
                        if k in (pygame.K_a, pygame.K_LEFT):
                            move_select(s, 0, -1)
                        elif k in (pygame.K_d, pygame.K_RIGHT):
                            move_select(s, 0, 1)
                        elif k in (pygame.K_w, pygame.K_UP):
                            move_select(s, -1, 0)
                        elif k in (pygame.K_s, pygame.K_DOWN):
                            move_select(s, 1, 0)
                        elif k in (pygame.K_RETURN, pygame.K_j, pygame.K_z):
                            s["lock"] = True
                            g.p1cid = ROSTER[s["row"] * 5 + s["col"]]
                            if g.cpucid == g.p1cid:
                                g.cpucid = random.choice([c for c in ROSTER if c != g.p1cid])
                            g.refresh_previews()
                        elif k == pygame.K_t:
                            g.cpucid = random.choice([c for c in ROSTER])
                            g.refresh_previews()
                        elif k == pygame.K_y:
                            g.ai_level = (g.ai_level + 1) % len(DIFFS)
                        elif k == pygame.K_ESCAPE:
                            g.state = "title"
                    else:
                        if k in (pygame.K_a, pygame.K_LEFT):
                            s["scol"] = (s.get("scol", 0) - 1) % 5
                        elif k in (pygame.K_d, pygame.K_RIGHT):
                            s["scol"] = (s.get("scol", 0) + 1) % 5
                        elif k in (pygame.K_w, pygame.K_UP):
                            s["srow"] = (s.get("srow", 0) - 1) % ((len(STAGES) + 4) // 5)
                        elif k in (pygame.K_s, pygame.K_DOWN):
                            s["srow"] = (s.get("srow", 0) + 1) % ((len(STAGES) + 4) // 5)
                        elif k in (pygame.K_RETURN, pygame.K_j, pygame.K_z):
                            g.stage_idx = s["stage"]
                            if g.net_role == "host":
                                g.state = "lobby"
                            else:
                                g.state = "vs"
                                g.vs_t = 0.0
                        elif k == pygame.K_ESCAPE:
                            s["lock"] = False
                            idx = ROSTER.index(g.p1cid)
                            s["row"], s["col"] = idx // 5, idx % 5
                        g.sync_stage_cursor(s)
                elif g.state == "lobby":
                    if k in (pygame.K_RETURN, pygame.K_SPACE):
                        if g.net_guest_cid:
                            g.start_match()
                    elif k == pygame.K_ESCAPE:
                        g.state = "select"
                elif g.state == "gpick":
                    if k in (pygame.K_a, pygame.K_LEFT):
                        g.gpick_idx = (g.gpick_idx - 1) % len(ROSTER)
                    elif k in (pygame.K_d, pygame.K_RIGHT):
                        g.gpick_idx = (g.gpick_idx + 1) % len(ROSTER)
                    elif k in (pygame.K_w, pygame.K_UP):
                        g.gpick_idx = (g.gpick_idx - 5) % len(ROSTER)
                    elif k in (pygame.K_s, pygame.K_DOWN):
                        g.gpick_idx = (g.gpick_idx + 5) % len(ROSTER)
                    elif k in (pygame.K_RETURN, pygame.K_j, pygame.K_SPACE):
                        g.p1cid = ROSTER[g.gpick_idx]
                        if g.net_peer is not None:
                            g.net_peer.send({"t": "pick", "cid": g.p1cid})
                        g.state = "gwait"
                    elif k == pygame.K_ESCAPE:
                        g.net_stop()
                        g.state = "title"
                elif g.state == "gwait":
                    if k == pygame.K_ESCAPE:
                        g.net_stop()
                        g.state = "title"
                elif g.state == "vs":
                    if k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_j, pygame.K_z):
                        g.start_match()
                    elif k == pygame.K_ESCAPE:
                        g.state = "select"
                elif g.state == "fight":
                    if g.net_is_guest():
                        if k in (pygame.K_p, pygame.K_ESCAPE):
                            if g.net_peer is not None:
                                g.net_peer.send({"t": "pause"})
                        else:
                            g.net_guest_key(ev)
                    elif k in (pygame.K_p, pygame.K_ESCAPE):
                        g.paused = not g.paused
                        if g.paused:
                            g.paused_idx = 0
                    elif g.paused:
                        if k in (pygame.K_UP, pygame.K_w):
                            g.paused_idx = (g.paused_idx - 1) % 4
                        elif k in (pygame.K_DOWN, pygame.K_s):
                            g.paused_idx = (g.paused_idx + 1) % 4
                        elif k in (pygame.K_RETURN, pygame.K_SPACE):
                            g.do_pause_action(["resume", "rematch", "select", "title"][g.paused_idx])
                    else:
                        g.key_down_fight(ev)
                elif g.state == "gameover":
                    if g.net_is_guest():
                        if k in (pygame.K_RETURN, pygame.K_t, pygame.K_ESCAPE):
                            g.net_stop()
                            g.state = "title"
                    elif k in (pygame.K_LEFT, pygame.K_a):
                        g.go_idx = (g.go_idx - 1) % 3
                    elif k in (pygame.K_RIGHT, pygame.K_d):
                        g.go_idx = (g.go_idx + 1) % 3
                    elif k == pygame.K_RETURN:
                        g.do_gameover_action(["rematch", "select", "title"][g.go_idx])
                    elif k == pygame.K_t:
                        g.goto_select()
                    elif k == pygame.K_ESCAPE:
                        g.state = "title"
            if ev.type == pygame.KEYUP and g.state == "fight" and not g.paused:
                if g.net_is_guest():
                    g.net_guest_keyup(ev)
                else:
                    g.key_up_fight(ev)
            if ev.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                g.pad_refresh()
            if ev.type == pygame.JOYBUTTONDOWN:
                if g.state == "fight" and not g.paused:
                    if g.net_is_guest():
                        g.net_guest_pad(ev.button)
                    else:
                        g.pad_action(ev.button)
                else:
                    g.pad_menu_button(ev.button)
            if ev.type == pygame.JOYBUTTONUP:
                if g.state == "fight" and not g.paused:
                    if g.net_is_guest():
                        g.net_guest_pad_up(ev.button)
                    else:
                        g.pad_release(ev.button)
            if ev.type == pygame.JOYHATMOTION:
                if g.state == "fight" and not g.paused:
                    if g.net_is_guest():
                        g.net_guest_hat(ev.value)
                    else:
                        g.pad_hat_fight(ev.value)
                else:
                    g.pad_menu_hat(ev.value)
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                pos = ev.pos
                if g.state == "title":
                    for i, b in enumerate(g.title_buttons):
                        if b.rect.collidepoint(pos):
                            g.menu_idx = i
                            g.do_title_action(b.action)
                elif g.state == "online":
                    for i, b in enumerate(g.online_buttons):
                        if b.rect.collidepoint(pos):
                            g.menu_idx = i
                            if i == 0:
                                if g.net_start_host():
                                    g.goto_select()
                            elif i == 1:
                                g.state = "ip"
                                g.ip_buf = ""
                                g.ip_err = ""
                                g.ip_mode = "ip"
                            else:
                                g.state = "net"
                                g.menu_idx = 0
                            break
                elif g.state == "net":
                    for i, b in enumerate(g.net_buttons):
                        if b.rect.collidepoint(pos):
                            g.menu_idx = i
                            if i == 0:
                                if g.net_start_host(link="relay"):
                                    g.goto_select()
                            else:
                                g.state = "ip"
                                g.ip_buf = ""
                                g.ip_err = ""
                                g.ip_mode = "room"
                            break
                elif g.state == "help":
                    if getattr(g, "help_back", None) and g.help_back.rect.collidepoint(pos):
                        g.state = "title"
                elif g.state == "select":
                    if getattr(g, "cpu_chip", None) and g.cpu_chip.collidepoint(pos):
                        g.cpucid = random.choice([c for c in ROSTER])
                        g.refresh_previews()
                    elif any(r.collidepoint(pos) for r, _ in getattr(g, "diff_btns", [])):
                        for r, d in g.diff_btns:
                            if r.collidepoint(pos):
                                g.ai_level = (g.ai_level + d) % len(DIFFS)
                                break
                    elif not g.sel["lock"]:
                        for r, idx in g.sel_cards:
                            if r.collidepoint(pos):
                                g.sel["row"], g.sel["col"] = idx // 5, idx % 5
                                g.sel["lock"] = True
                                g.p1cid = ROSTER[idx]
                                if g.cpucid == g.p1cid:
                                    g.cpucid = random.choice([c for c in ROSTER if c != g.p1cid])
                                g.refresh_previews()
                                break
                    else:
                        for r, idx in g.stage_cards:
                            if r.collidepoint(pos):
                                g.sel["stage"] = idx
                                g.stage_idx = idx
                                if g.net_role == "host":
                                    g.state = "lobby"
                                else:
                                    g.state = "vs"
                                    g.vs_t = 0.0
                                break
                elif g.state == "gpick":
                    for r, idx in g.gpick_cards:
                        if r.collidepoint(pos):
                            g.gpick_idx = idx
                            g.p1cid = ROSTER[idx]
                            if g.net_peer is not None:
                                g.net_peer.send({"t": "pick", "cid": g.p1cid})
                            g.state = "gwait"
                            break
                elif g.state == "vs":
                    g.start_match()
                elif g.state == "gameover":
                    for i, b in enumerate(g.go_buttons):
                        if b.rect.collidepoint(pos):
                            g.go_idx = i
                            if g.net_is_guest():
                                if b.action == "title":
                                    g.net_stop()
                                    g.state = "title"
                            else:
                                g.do_gameover_action(b.action)
                elif g.state == "fight" and g.paused:
                    for i, b in enumerate(g.pause_buttons):
                        if b.rect.collidepoint(pos):
                            g.paused_idx = i
                            g.do_pause_action(b.action)
            if ev.type == pygame.MOUSEBUTTONDOWN and g.state == "fight" and not g.paused:
                if g.net_is_guest():
                    g.net_guest_mouse(ev)
                else:
                    g.mouse_down_fight(ev)
        if g.state == "title" and (g.net_role is not None or g.net_listen is not None):
            g.net_stop()
        if g.state == "lobby":
            if g.net_poll_lobby():
                pass
            if g.net_peer is not None:
                for m in g.net_peer.pump():
                    if m.get("t") == "pick" and m.get("cid") in ROSTER:
                        g.net_guest_cid = m["cid"]
                        g.net_peer.send({"t": "lobby", "p2": m["cid"]})
                if g.net_peer.dead:
                    g.net_peer = None
                    g.net_guest_cid = None
        if g.state != getattr(g, "_prev_state", None):
            g._prev_state = g.state
            g.state_t = 0.0
            g.fade = 0.35
        g.state_t += dt
        g.fade = max(0.0, g.fade - dt)
        g._pad_scan += dt
        if g._pad_scan > 2.0:
            g._pad_scan = 0.0
            if g.pad_joy is None:
                g.pad_refresh()
        if g.quit_req:
            pygame.quit()
            return
        if g.state == "vs":
            g.vs_t = getattr(g, "vs_t", 0.0) + dt
            if g.vs_t > 2.0:
                g.start_match()
        if g.net_is_guest() and g.state in ("fight", "gameover", "gwait"):
            g.net_guest_tick(dt, pygame.key.get_pressed())
        elif g.state == "fight" and not g.paused:
            g.update_fight(dt, pygame.key.get_pressed())
            if g.net_is_host() and g.net_guest_present():
                g.net_frame += 1
                if g.net_frame % netplay.SNAP_EVERY == 0:
                    g.net_sq += 1
                    g.net_peer.send(g.net_snapshot())
        else:
            g.update_fx(dt)
        g.draw()


if __name__ == "__main__":
    main()
