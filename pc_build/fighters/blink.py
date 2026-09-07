"""BLINK PRYOR — Rift Courier. The ONLY fighter with a TRIPLE jump. Impossible to edgeguard cleanly."""

CID = "blink"

DATA = {
    "name": "BLINK PRYOR", "title": "Rift Courier",
    "ability": "PASSIVE: Triple jump — two air jumps. Nobody edgeguards Blink",
    "desc": "Delivers pain overnight. Catches ranges no one else can recover from.",
    "story": "Pryor delivers parcels across the Rift overnight, every night, on foot. Customs never catches him: there is no form for a courier with three jumps and no fixed address.",
    "skin": {"main": (90, 220, 190), "dark": (30, 120, 100), "trim": (230, 255, 245), "glow": (120, 255, 210)},
    "weight": 0.8, "run": 295, "air": 262, "jumpv": -610, "djumpv": -540,
    "grav": 1450, "maxfall": 660, "power": 0.8, "air_jumps": 2,
    "proj": {"kind": "bolt", "dmg": 4, "speed": 660, "cd": 0.9, "size": 6, "color": (150, 255, 200)},
    "up": {"dmg": 7, "lift": -850}, "down": {"kind": "teleport"},
}

TRAITS = {"zoner": True, "mechanic": "triple jump"}
