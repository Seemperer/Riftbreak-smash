"""NULL HOLLOW — Gravity Well. DOWN-B births a drifting well that drags the foe in, then implodes."""

CID = "null"

DATA = {
    "name": "NULL HOLLOW", "title": "Gravity Well",
    "ability": "DOWN-B: Collapse — a well drags the foe, then detonates",
    "desc": "A hole in the world wearing a crown. Nowhere is safe to stand.",
    "story": "Hollow is what is left when a king divides by himself. A walking absence in a crown-shaped hole, collecting battlefields the way lint collects pockets.",
    "skin": {"main": (220, 60, 70), "dark": (120, 20, 30), "trim": (255, 210, 90), "glow": (255, 80, 90)},
    "weight": 1.45, "run": 200, "air": 170, "jumpv": -550, "djumpv": -480,
    "grav": 1580, "maxfall": 710, "power": 1.3,
    "proj": {"kind": "orb", "dmg": 10, "speed": 330, "cd": 1.6, "size": 11, "color": (255, 90, 150)},
    "up": {"dmg": 11, "lift": -720}, "down": {"kind": "well"},
}

TRAITS = {"heavy": True, "zoner": True, "mechanic": "gravity well"}
