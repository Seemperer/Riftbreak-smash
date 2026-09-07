# 3D art drops — how to add external fighter sprites

The game renders fighters procedurally by default. Drop real 3D art here
and it is used automatically, no code changes needed.

## Folder layout

```
pc_build/assets/fighters/<cid>/
    meta.json            # optional but recommended (poses + fps + anchor)
    idle_0.png  idle_1.png  ...
    run_0.png   run_1.png   ...
    ...one PNG per frame, transparent background...
```

`<cid>` is one of: cinder disc arc bulwark glass null blink tecton echo leech.

## Image spec (important — the engine assumes this)

- Size: **160 x 160 px**, transparent PNG.
- Feet anchor: the fighter's feet touch **(80, 146)** — same for every frame,
  so squash / spin / flash / shadows line up with the procedural rig.
- Facing: **right**. The engine mirrors for left automatically.
- Style: keep lighting from the upper right, keep all 10 fighters the same
  height (~100 px tall) so nobody looks out of place.

## Poses (each = list of frames, loops automatically)

idle / run / jump / fall / charge / shield / hit / break / special /
attack_jab / attack_ftilt / attack_utilt / attack_nair / attack_uair /
attack_smash

Missing poses fall back to `idle`, then to the procedural rig — so you can
drop in just `idle` + `run` first and it already works.

## meta.json example

```json
{
  "fps": 10,
  "anchor": [80, 146],
  "poses": {
    "idle": ["idle_0.png", "idle_1.png", "idle_2.png", "idle_3.png"],
    "run": ["run_0.png", "run_1.png", "run_2.png", "run_3.png",
            "run_4.png", "run_5.png"],
    "attack_jab": ["jab_0.png", "jab_1.png", "jab_2.png"]
  }
}
```

No meta.json? Files named `<pose>_<anything>.png` are grouped by pose
automatically at 10 fps.

## Tips for AI-generated 3D

- Render orthographic (no perspective), camera side-on, character centered.
- Ask for a "game sprite sheet, transparent background, consistent character,
  T-pose neutral" first, then per-pose variations from the same seed/model.
- If your tool exports a sheet instead of files: slice it into the PNGs
  above (any free tool works), keeping the 160x160 canvas + anchor.

## Stage paintings (AI-generated backgrounds)

Save each stage painting as a **PNG or JPG** in `pc_build/assets/stages/`
using EXACTLY these filenames (rename your downloads to match):

| File | Stage it skins |
|---|---|
| `ember_arena.png` | Ember Arena (twin volcanoes, obsidian arch) |
| `sky_battlefield.png` | Sky Battlefield (floating sky ruins) |
| `void_final.png` | Void Final (void monoliths) |
| `fungal_hollow.png` | Fungal Hollow (glowing mushroom grove) |
| `storm_spire.png` | Storm Spire (lightning tower) |
| `tide_vault.png` | Tide Vault (sunken vault) |
| `iron_foundry.png` | Iron Foundry (skull fortress) |
| `thorn_garden.png` | Thorn Garden (moonlit briar) |
| `glacier.png` | Glacier (ice aurora) |
| `dune_sea.png` | Dune Sea (desert obelisk) |
| `hollow_star.png` | Hollow Star (orbital station) |
| `clockwork.png` | Clockwork (brass engine room) |
| `magma_core.png` | Magma Core (volcano arena) |
| `cloud_nine.png` | Cloud Nine (rainbow sky) |
| `the_rift.png` | The Rift (void vortex) |
| `harbor_town.png` | Harbor Town (plaza) |
| `world_tree.png` | World Tree (great tree island) |
| `sunset_keep.png` | Sunset Keep (castle at dusk) |

The mapping lives in `pc_build/assets/stages.json` (stage name → file).
Optional: add `<same-name>_mid.png` (transparent PNG) for a parallax
mid layer that drifts against the background.

How it works: paintings are cover-fit to 960×540 with a slight scroll
parallax as the camera moves. Collision platforms, hazards, fighters and
effects still draw procedurally on top, and the glowing platforms always
mark the REAL ground — so the art can be anything. Missing files fall back
to procedural backgrounds automatically. Restart the game after adding files.
