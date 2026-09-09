"""DISC MARO — Chakram Dancer. Neutral-B throws a chakram that returns, hitting twice."""

CID = "disc"

DATA = {
    "name": "DISC MARO", "title": "Chakram Dancer",
    "ability": "NEUTRAL-B: Halo — the chakram comes BACK, both trips hurt the foe (never Maro)",
    "desc": "Dances in circles around zoners. Never stand in line twice.",
    "story": "Maro danced for coins on station platforms until a thrown halo took her eye. She kept dancing, learned to throw it back twice as hard, and never missed since.",
    "skin": {"main": (120, 200, 255), "dark": (50, 110, 170), "trim": (230, 250, 255), "glow": (140, 220, 255)},
    "weight": 0.9, "run": 250, "air": 230, "jumpv": -590, "djumpv": -520,
    "grav": 1420, "maxfall": 620, "power": 0.9,
    "proj": {"kind": "disc", "dmg": 6, "speed": 460, "cd": 1.1, "size": 9, "color": (170, 230, 255)},
    "up": {"dmg": 7, "lift": -800}, "down": {"kind": "freeze"},
}

TRAITS = {"zoner": True, "mechanic": "returning chakram"}
