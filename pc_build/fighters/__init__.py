"""Per-character fighter modules. Each file defines ONE unique fighter.

Every module exposes:
  CID: str            - stable character id
  DATA: dict          - name/title/ability/desc/story/skin/stats/proj/up/down (+ air_jumps)
  TRAITS: dict        - AI hints, e.g. {"zoner": True, "heavy": True}

Unique mechanics live in the engine (main.py) keyed by CID, so the
simulation stays in sync for both local players and AI.
"""
from . import cinder, disc, arc, bulwark, glass, null, blink, tecton, echo, leech

MODULES = (cinder, disc, arc, bulwark, glass, null, blink, tecton, echo, leech)

ROSTER = [m.CID for m in MODULES]
FIGHTERS = {m.CID: m.DATA for m in MODULES}
TRAITS = {m.CID: m.TRAITS for m in MODULES}


def get(cid):
    return FIGHTERS[cid]


def traits(cid):
    return TRAITS.get(cid, {})
