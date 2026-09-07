# RIFTBREAK: Smash Cells — Complete Game Docs
> 1v1 Smash-like arena fighter for PC (Pygame) — 10 unique fighters, 18 scrolling stages,
> online versus over LAN, full gamepad support.
> PC build: `pip install pygame`, then `python pc_build/main.py` (`--windowed` for window mode).

**Controls (P1):** `A`/`D` or arrows move, `W` aim-up, `↓` drop/fast-fall, `Space` jump (×2,
buffered + coyote time), `Z`/`J`/`LMB` attack (dir=side-tilt, up=up-tilt, air=air),
`X`/`K` hold/release charged smash, `C` neutral special, `V` up special (recover),
`S`/`E` SUPER down special, `Shift` dash (i-frames), `RMB` SMART (auto: counter aggression /
dash danger / heavy kill-%), `L` hold shield, `F` ULTIMATE (full gold bar),
`TAB` slim move list, `F11` fullscreen, `Enter` confirm, `P/Esc` pause.
Starts fullscreen (scaled).

**Gamepad (8BitDo SN30, XInput mode — boot it with Start+X):** d-pad move/aim/drop,
`A` jump, `X` attack, `B` smash, `Y` neutral special, `LB` tap = dash / hold = shield,
`RB` recover, `Select` super, `Start` pause, `LB`+`RB` together = ULTIMATE.
Menus: d-pad + `A` confirm / `B` back (`Y` difficulty, `X` reroll CPU on select).
Hot-plug supported; `PAD` shows in HUD. Title + help screens show live pad status
and last input seen — if nothing appears: Start+X mode, re-pair Bluetooth, press any
button, disable Steam Input for this game.

Win: take all 4 CPU stocks (launch past blast zone). Lose: lose your 4 stocks or time-out
behind on stocks. Record kept per-fighter in `pc_build/save.json`.

---

## 12. Smash 1v1 Arena (current game)

- **Battle format:** 1v1, **4 stocks**, **3:00 timer**, blast-zone KOs on huge scrolling stages
  (2800–4200px). Fast pace: short recoveries, quick countdown/KO/respawn, fast dash cooldown,
  +8% move speed, 40-HP shields. Timeout → higher stocks wins, tie → sudden death (both to 300%).
- **Stages (18, big + scrolling + detailed):** Ember Arena (3000), Sky Battlefield (3200),
  Void Final (2800), Fungal Hollow (bounce shrooms), Storm Spire (wind), Tide Vault (low-grav),
  Iron Foundry (spikes), Thorn Garden (spikes), Glacier (slippery ice), Dune Sea (headwind),
  Hollow Star (floaty), Clockwork (phasing platforms), Magma Core (spikes + bounce),
  Cloud Nine (pads + wind), The Rift (4200, everything),
  Harbor Town (clean plaza), World Tree (bounce bloom), Sunset Keep (rooftop duel).
  Collision platforms are aligned to the key art layouts. Camera follows the PLAYER (72% P1 +
  28% foe + velocity lookahead) with parallax;
  pillars, chains, runes, grass, lava cracks, pads, phases, spikes all drawn per theme.
  Blast zones scale with world width.
- **Stage paintings:** drop AI-generated backgrounds in `pc_build/assets/stages/` using the exact
  filenames in `pc_build/assets/stages.json` (e.g. `sky_battlefield.png` for the floating ruins,
  `magma_core.png` for the volcano). Optional `<name>_mid.png` transparent layer parallaxes on top.
  Paintings cover-fit with camera scroll; procedural platforms/hazards/fighters draw over them and
  the glowing platforms always mark real ground. Missing files fall back to procedural art.
- **Breakable terrain:** floating platforms marked cracked take melee/projectile/bomb/ult damage
  and collapse (removed from collision), regenerating after 12s. Mains are never breakable.
- **Lava pools:** animated pools burn (+10%, 2s burn) and launch you out. Spikes: +8% pop-up.
- **Roster — one file per fighter in `pc_build/fighters/`** (registry in `fighters/__init__.py`).
  Each module owns stats, projectile, specials + a signature mechanic no one else has:

| Fighter | Weight / Speed | Neutral-B | Up-B (recovery) | Down-B (unique) |
|---|---|---|---|---|
| CINDER VEX, Meteor Heretic | 1.0 / med | Delayed meteor (+burn) | Rising slash | Inferno Counter |
| DISC MARO, Chakram Dancer | 0.9 / med | Returning chakram | High leap | Glacier Burst (slow) |
| ARC VOLTA, Static Brawler | 0.85 / fastest | Bolt | Longest lift | Blink + static bank/discharge |
| BULWARK BOONE, Living Fortress | 1.5 / slow, power 1.35× | Heavy rock | Short lift | Stance + unlaunchable charge |
| GLASS SHARD, Glass Duelist | 0.75 / fast, power 1.1× | Needle | Slash leap | Mirror punish + REFLECTS shots |
| NULL HOLLOW, Gravity Well | 1.45 / slow, power 1.3× | Rift orb | Heavy lift | Collapse well (drag + boom) |
| BLINK PRYOR, Rift Courier | 0.8 / fastest air | Phase dart | Best lift + TRIPLE jump | Blink |
| TECTON OSMOND, Seismic Monk | 1.6 / slowest, power 1.5× | Seismic rock | Short lift | Stance + landing quakes |
| ECHO VANE, Paradox Thief | 0.95 / fast | Phase bolt | Slash leap | Echo set/recall teleport |
| LEECH MOSS, Debt Collector | 0.9 / fast, power 1.05× | Venom darts (slow) | Slash leap | Venom Counter + 30% lifesteal |

- **Shared kit:** jab / side-tilt / up-tilt / air / up-air / charged smash / shield (40 HP, breaks → 1.6s stun + glitch) / dash with i-frames. Knockback soft-caps past 1500 so 999% stays sane.
- **Signature mechanics:** triple jump (Blink), telegraphed meteors + burn (Cinder), returning
  chakram that can hit its owner (Disc), dash-banked static discharge (Arc), unlaunchable
  smash-charge (Bulwark), projectile reflect ×1.5 (Glass), dragging gravity well (Null),
  landing shockwaves (Tecton), echo set/recall (Echo), 30% lifesteal (Leech).
- **Stories (shown truncated on select, full here):**
  - CINDER VEX: Vex read the sky's forbidden last verse and the sky answered wrong. Now meteors trail her like unpaid debts.
  - DISC MARO: Maro danced for coins until a thrown halo took her eye. She kept dancing and learned to throw it back twice as hard.
  - ARC VOLTA: Volta drove night trams until lightning unionized inside him. He banks static and cashes out point-blank.
  - BULWARK BOONE: Boone was a siege door for three hundred years and got bored of opening. Nothing has launched him since.
  - GLASS SHARD: Shard was a cathedral window that watched one duel too many. Everything thrown at her comes back.
  - NULL HOLLOW: Hollow is what is left when a king divides by himself. A walking absence collecting battlefields.
  - BLINK PRYOR: Pryor delivers parcels across the Rift overnight, every night, on foot. Customs never catches him.
  - TECTON OSMOND: Osmond took a vow of stillness, then broke it with his feet. Every landing is a sermon in shockwaves.
  - ECHO VANE: Vane robbed yesterday and is spending it today. She fights from two places at once and pays for neither.
  - LEECH MOSS: Moss audits the living and always finds arrears. Thirty percent, non-negotiable, due immediately.
- **Win streaks:** consecutive match wins build a power multiplier (+4% per streak, max +20%, P1 only,
  shown on VS/title/game-over). Losing resets it. Best streak saved.
- **Item drops (Smash-style):** every 7–12s (max 2 on stage), walk over to grab. POWER STAR
  (3s invincible), SNACK (−30% damage), ULT ORB (+35 ult), HAMMER (8s +40% melee), HEX BOLT
  (foe +18%), FROST CELL (foe slowed 3s), FUSE BOMB (1.2s fuse, big AoE near the foe).
- **Ultimates:** dealing damage charges your gold bar (taking hits charges less); ULT ORBs help.
  At 100, press `F` (must be free/grounded-neutral): cinematic freeze + banner + unique effect —
  INFERNO CATACLYSM, HALO OF BLADES, OVERVOLT, BEDROCK ERUPTION, PRISM BREAK, RIFT COLLAPSE,
  TERMINAL VELOCITY, EXTINCTION, PARADOX BLOOM, VENOM BLOOM. Point-blank ults can be dashed (DODGED!).
- **CPU:** per-character AI with 4 difficulty levels (select screen, `Y` or click):
  ROOKIE (slow reactions, no edgeguards, botches recoveries) → FIGHTER → VETERAN →
  NIGHTMARE (0.10s reactions, shields smashes, edgeguards rising foes, punishes charged smashes
  with counters). All levels combo stunned victims, whiff-punish recoveries, dash through incoming
  projectiles, grab items, fire charged ultimates, and play their kit (Echo recalls offstage, Glass
  reads dashes, Arc dash-banks static, Tecton stomps from above). Measured: Nightmare beats Rookie
  ~7/8 across matchups. Per-fighter `ai_lv` override exists for testing.
- **Smash UI (pro pass):** navy+gold theme, cached fonts, rounded panels, buttons clickable via mouse.
  Title (live demo fight, shine-sweep logo, FIGHT / HOW TO PLAY / ONLINE / QUIT menu, win record,
  pad status) → HOW TO PLAY (controls grid + tips + pad status) → character select (Smash-style:
  P1 + CPU hero panes up top, 10 portrait tiles below, clickable CPU reroll chip, difficulty picker,
  stage cards with thumbnails) → VS screen (sliding team-color cards, popping VS emblem, stage pill)
  → READY 3-2-1-GO (ring pulse on numbers, sliding banner for K.O./GAME/TIME) → slim HUD
  (top-center timer pill, tiny top-corner chips: icon + popping %, stock pips, ult micro-bar,
  cooldown dots — never covers the fight) → pause menu (Resume/Rematch/Characters/Title) →
  VICTORY/DEFEAT screen (per-fighter stocks/peak%/best-combo stats, head-to-head wins,
  REMATCH/FIGHTERS/TITLE buttons). Character picker is Smash-style: P1 + CPU hero panes up top,
  10 portrait tiles below, stage cards with thumbnails. `TAB` opens a live side move-list
  mid-fight (every attack + real-time special cooldown dots, slim translucent). Fade transitions.
- **Event visual modes (auto-triggered):** BLOOD (anyone ≥100%), VOID (offstage danger + wisps),
  DARK RAINBOW (both on last stock), RAINBOW (sudden death), CHAOS ULTRA (both ults full + shout),
  SOLARIS (golden burst at GO), COSMOSIS (starfield on ultimates), GLITCH (rgb slices on
  breaks/counters/KOs), screen-shake QUAKE boost + dust on huge launches, BLACK AND WHITE
  (match-deciding end phase). KO freeze keeps letterbox bars; sudden/low-time keeps red vignette.
- **Render quality:** real low-poly 3D fighters (poses drive joint targets; boxes with depth,
  strong 24-degree camera yaw + idle sway, windup turns, swing sweeps, launch corkscrews,
  directional flat shading, per-char 3D helms/weapons, glow eyes),
  extruded 3D stage slabs with side caps, rotating background cubes, perspective floor grids,
  additive-blend bloom (projectiles, charges, KOs, logo, buttons), cached radial
  glow sprites, gradient UI panels, shadowed HUD numbers, shockwave rings on KOs/ults/bombs/breaks/
  landings, white-hot slash cores, soft layered blob shadows, gradient-shaded fighters with limb
  highlights, god rays + animated lava + shaded clouds, pulsing under-glow,
  fullscreen vignette grade. Holds ~300fps headless (171fps with all fx in heavy scenes).
- **3D art drops:** put AI-generated fighter sprites in `pc_build/assets/fighters/<cid>/`
  (160×160 transparent PNGs, feet at (80,146), facing right — full spec in `assets/README.md`).
  Poses used automatically (idle/run/jump/fall/charge/shield/hit/break/special/attack_*);
  anything missing falls back to the procedural 3D rig. No code changes needed.

---

## 13. Online versus (LAN, no servers)

Host-authoritative: the host simulates; the guest sends inputs (60Hz) and renders snapshots
(20Hz) with local cosmetic fx. No determinism needed. Same WiFi, or ZeroTier/Hamachi/Radmin
for internet play. Port **7001** TCP — allow it through the firewall.

- HOST: title → ONLINE → HOST GAME → pick fighter + stage → LOBBY (shows your IP, guest
  pick appears, ENTER starts). Pause works for both (guest asks, host toggles). If the guest
  drops, CPU takes over their fighter mid-match. Rematch from the host starts a new round
  for both.
- GUEST: title → ONLINE → JOIN GAME → type host IP → pick fighter → wait → fight.
  Game over screen follows the host; ENTER returns to title (host rematch auto-rejoins you).
- Protocol (`pc_build/netplay.py`, JSON lines over TCP): guest→host `in`/`pick`/`pause`/`ping`;
  host→guest `hello`/`snap`/`lobby`/`pong`/`bye`. Snapshots are fully self-contained
  (fighters, projectiles, rings, slashes, drops, timer, phase, announce, pause, winner),
  so a dropped packet is just an old frame. Hello retransmits until guest input arrives.
- Notes: win records save on the host only; the host's win streak powers only the host;
  guest pause/game-over buttons are host-gated to prevent desyncs.

*End of docs — single source of truth. If code and this file disagree, this file wins; update code to match.*
