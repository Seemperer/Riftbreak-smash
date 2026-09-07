"""ECHO VANE — Paradox Thief. DOWN-B drops an echo marker; press again to snap back to it."""

CID = "echo"

DATA = {
    "name": "ECHO VANE", "title": "Paradox Thief",
    "ability": "DOWN-B: Set echo → recall. Bait, swap, punish. Never be where hit",
    "desc": "Stole yesterday and spent it today. Fights two places at once.",
    "story": "Vane robbed yesterday and is spending it today. She fights from two places at once and pays for neither, which is why the timeline filed three complaints.",
    "skin": {"main": (130, 160, 255), "dark": (60, 80, 160), "trim": (255, 255, 220), "glow": (150, 200, 255)},
    "weight": 0.95, "run": 265, "air": 225, "jumpv": -590, "djumpv": -520,
    "grav": 1480, "maxfall": 650, "power": 1.0,
    "proj": {"kind": "bolt", "dmg": 6, "speed": 540, "cd": 1.2, "size": 7, "color": (160, 200, 255)},
    "up": {"dmg": 8, "lift": -790}, "down": {"kind": "echo"},
}

TRAITS = {"mechanic": "echo recall teleport"}
