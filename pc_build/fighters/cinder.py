"""CINDER VEX — Meteor Heretic. Calls down delayed, telegraphed meteors. Burn on big hits."""

CID = "cinder"

DATA = {
    "name": "CINDER VEX", "title": "Meteor Heretic",
    "ability": "NEUTRAL-B: Meteor — delayed strike marks the foe's ground",
    "desc": "Heretic who sold the sky. Meteors punish campers; burns finish jobs.",
    "story": "Vex read the sky's forbidden last verse and the sky answered wrong. Now meteors trail her like unpaid debts, and she conducts every fall like music.",
    "skin": {"main": (235, 110, 40), "dark": (140, 55, 15), "trim": (255, 210, 120), "glow": (255, 150, 50)},
    "weight": 1.0, "run": 250, "air": 210, "jumpv": -580, "djumpv": -510,
    "grav": 1500, "maxfall": 660, "power": 1.0,
    "proj": {"kind": "meteor", "dmg": 14, "speed": 650, "cd": 1.6, "size": 10, "color": (255, 130, 40)},
    "up": {"dmg": 9, "lift": -780}, "down": {"kind": "counter"},
}

TRAITS = {"zoner": True, "mechanic": "meteor + burn"}
