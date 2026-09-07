"""GLASS SHARD — Glass Duelist. The only fighter that REFLECTS projectiles during a counter.
Fragile: launched the furthest in the roster."""

CID = "glass"

DATA = {
    "name": "GLASS SHARD", "title": "Glass Duelist",
    "ability": "DOWN-B: Mirror — punishes melee AND reflects projectiles back x1.5",
    "desc": "Hits like a truck stop sign. Breaks like a promise. Time it right.",
    "story": "Shard was a cathedral window that watched one duel too many. She stepped out of the frame mid-swing and kept the worst of the light. Everything thrown at her comes back.",
    "skin": {"main": (150, 120, 220), "dark": (70, 50, 120), "trim": (230, 220, 255), "glow": (190, 150, 255)},
    "weight": 0.75, "run": 275, "air": 235, "jumpv": -595, "djumpv": -525,
    "grav": 1480, "maxfall": 650, "power": 1.1,
    "proj": {"kind": "needle", "dmg": 6, "speed": 560, "cd": 1.2, "size": 6, "color": (210, 170, 255)},
    "up": {"dmg": 8, "lift": -790}, "down": {"kind": "mirror"},
}

TRAITS = {"mechanic": "projectile reflect + punish"}
