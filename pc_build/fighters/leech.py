"""LEECH MOSS — The Debt Collector. Heals 30% of every point of damage it deals. Bleed it fast."""

CID = "leech"

DATA = {
    "name": "LEECH MOSS", "title": "Debt Collector",
    "ability": "PASSIVE: Lifesteal — every hit pays 30% back off your %",
    "desc": "Everything you owe, it collects in blood. Kill it before it bills you.",
    "story": "Moss audits the living and always finds arrears. Every wound you take, he books as payment toward a debt you never signed: thirty percent, non-negotiable.",
    "skin": {"main": (150, 200, 80), "dark": (70, 110, 30), "trim": (240, 255, 200), "glow": (180, 255, 120)},
    "weight": 0.9, "run": 285, "air": 240, "jumpv": -600, "djumpv": -530,
    "grav": 1490, "maxfall": 665, "power": 1.05,
    "proj": {"kind": "venom", "dmg": 6, "speed": 520, "cd": 1.2, "size": 7, "color": (170, 255, 100)},
    "up": {"dmg": 8, "lift": -800}, "down": {"kind": "counter"},
}

TRAITS = {"mechanic": "lifesteal"}
