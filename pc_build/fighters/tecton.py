"""TECTON OSMOND — Seismic Monk. Hard landings detonate the floor into twin shockwaves."""

CID = "tecton"

DATA = {
    "name": "TECTON OSMOND", "title": "Seismic Monk",
    "ability": "PASSIVE: Land hard — the floor erupts into shockwaves both ways",
    "desc": "Prays with his feet. The stage itself is his second hitbox.",
    "story": "Osmond took a vow of stillness, then broke it with his feet. Every landing is a sermon and the floor says amen: in shockwaves, both directions, no exceptions.",
    "skin": {"main": (190, 90, 60), "dark": (100, 40, 25), "trim": (255, 200, 130), "glow": (255, 140, 60)},
    "weight": 1.6, "run": 175, "air": 150, "jumpv": -530, "djumpv": -460,
    "grav": 1650, "maxfall": 740, "power": 1.5,
    "proj": {"kind": "rock", "dmg": 11, "speed": 300, "cd": 1.8, "size": 12, "color": (220, 150, 90)},
    "up": {"dmg": 11, "lift": -680}, "down": {"kind": "armor"},
}

TRAITS = {"heavy": True, "mechanic": "landing shockwaves"}
