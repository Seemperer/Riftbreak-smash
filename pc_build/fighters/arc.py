"""ARC VOLTA — Static Brawler. Every dash banks static (max 3); the next melee hit discharges it."""

CID = "arc"

DATA = {
    "name": "ARC VOLTA", "title": "Static Brawler",
    "ability": "PASSIVE: Dash to bank static — next melee hit spends it all",
    "desc": "A fist full of lightning. Dash in, cash out, repeat until KO.",
    "story": "Volta drove night trams until lightning unionized inside him. He banks static the way other fighters bank grudges, and cashes out point-blank. The grid still sends bills.",
    "skin": {"main": (250, 215, 70), "dark": (150, 120, 20), "trim": (255, 255, 220), "glow": (255, 235, 90)},
    "weight": 0.85, "run": 300, "air": 250, "jumpv": -600, "djumpv": -530,
    "grav": 1500, "maxfall": 680, "power": 0.85,
    "proj": {"kind": "bolt", "dmg": 5, "speed": 620, "cd": 1.1, "size": 6, "color": (255, 240, 120)},
    "up": {"dmg": 8, "lift": -830}, "down": {"kind": "teleport"},
}

TRAITS = {"zoner": True, "mechanic": "static bank + discharge"}
