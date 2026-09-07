"""BULWARK BOONE — Living Fortress. Cannot be launched while charging a smash. Heaviest in the game."""

CID = "bulwark"

DATA = {
    "name": "BULWARK BOONE", "title": "Living Fortress",
    "ability": "PASSIVE: Unlaunchable mid smash-charge. DOWN-B: Bedrock Stance",
    "desc": "A wall with opinions. Charge smashes THROUGH enemy attacks.",
    "story": "Boone was a siege door for three hundred years and got bored of opening. Nothing has launched him since, and nothing will. He makes his point personally.",
    "skin": {"main": (150, 150, 170), "dark": (80, 80, 100), "trim": (255, 190, 90), "glow": (255, 170, 60)},
    "weight": 1.5, "run": 185, "air": 160, "jumpv": -540, "djumpv": -470,
    "grav": 1600, "maxfall": 720, "power": 1.35,
    "proj": {"kind": "rock", "dmg": 11, "speed": 300, "cd": 1.8, "size": 12, "color": (200, 170, 120)},
    "up": {"dmg": 11, "lift": -700}, "down": {"kind": "armor"},
}

TRAITS = {"heavy": True, "mechanic": "charge armor"}
