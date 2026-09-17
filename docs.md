# RIFTBREAK: Smash Cells — Complete Game Docs
> Smash Bros × Dead Cells hybrid for **ESP32 + TFT LCD + SD 2GB + Joystick Shield (4 btns + joystick + 2 extra)**
> PC prototype first → ESP32 port second. This file stores ALL data to make the game.

**Status: PC build DONE in `pc_build/main.py`. Wire hardware ONLY after you can beat Level 3 on PC.**
**Target TFT logical res: 320×240 (ILI9341). PC prototype runs 960×540 but all logic uses TILE=16-friendly coords so it ports 1:1.**

---

## 1. High Concept (what you asked for)

- **Less enemies / less map than Dead Cells, more dueling than Dead Cells:** max 1–3 enemies per room (not hordes), 12 hand-designed maps in a linear roguelite run (not 20+ huge biomes).
- **Smash-like duels but slightly lighter than Smash:** no frame-perfect tech. You get: Light combo, chargeable Heavy/Smash, Air attack, Dash with i-frames, Shield, Double-jump, Knockback-% system. No stocks, no wave-dash, no parry window — HP kill + ring-out pits.
- **Dead Cells-like exploration + loot:** interconnected maps, exit doors, weapon drops, Cells currency, Heal Flask (1 per run, refill on boss), permadeath, random weapon rolls.
- **Lots of maps:** 12 maps total. Run = 8 in order + boss. After boss you loop NG+ with +25% enemy HP.

If you want it in one sentence: *Side-view platform fighter where you explore 12 small arenas, duel 1–3 smart enemies per room Smash-style, grab Dead Cells-style weapons, and don't die.*

---

## 2. Controls — single source of truth

Same logical actions on PC and hardware. Port does not change game code, only input driver.

| Action | PC (prototype) | Joystick Shield + 2 extra | ESP32 GPIO (CYD default) |
|---|---|---|---|
| Move Left/Right | `A`/`D` or `←`/`→` | Joystick X (VRx) | GPIO 34 (ADC, VRx) |
| Aim Up / Crouch-Fall | `W` / `S` | Joystick Y (VRy) | GPIO 35 (ADC, VRy) |
| Jump / Double-Jump | `Space` | A button | GPIO 22 |
| Light Attack | `J` | B button | GPIO 21 |
| Heavy / Smash (hold to charge) | `K` (hold) | C button | GPIO 17 |
| Dash / Dodge (i-frames) | `L` or `Shift` | Joystick Click (SW) | GPIO 16 |
| Shield / Block (hold) | `I` (hold) | D button | GPIO 4* |
| Interact / Pickup weapon | `E` or `F` | EXTRA1 | GPIO 5* |
| Heal Flask / Pause (tap=heal, hold 1s=pause) | `H` / `P` or `Esc` | EXTRA2 | GPIO 0 |
| Confirm / Start | `Enter` | EXTRA1 | same |

`*` On CYD the SD uses GPIO 5 and touch uses GPIO 4 — see wiring §8. If conflict, move Shield D → GPIO 26, EXTRA1 → GPIO 27. Table in §8 gives conflict-free map.

Smash inputs that matter:
- Light + holding Left/Right = side-tilt (more range). Light + Up = up-tilt (launcher).
- Heavy hold 0–0.8s = charge ×1.0–×1.8 dmg/knockback. Release near enemy = Smash.
- Air + Light/Heavy while airborne = air attack (no charge).
- Shield reduces dmg 75%, knockback 60%, drains 30/s, breaks → 1.2s stun.
- Dash: 0.18s, i-frames 0.14s, cooldown 0.5s, keeps momentum.

---

## 3. Combat Numbers (Smash % + Dead Cells HP)

- Both player and enemies have **HP** and **% meter**.
- Taking hit: `HP -= dmg`, `% += dmg`. Knockback velocity = `base_kb * (1 + pct/60) * charge_mult * weight_mult`.
- Pits / spikes: take 15 dmg + respawn at room center with +20% (Smash-like punishment, no instant death — friendlier on small TFT).
- Player base: HP 100, weight 1.0, walk 220 px/s, air 180, jump -520, double -460, gravity 1400, max fall 600, dash 520.
- Flask: heal 40 HP, 1 charge per run (+1 after map 6 boss).
- Cells (currency): enemy drops 2–6, weapon chest costs 0 (free pickup, drop old), heal refill costs 10 cells at fountains (map 4, 7).

Balance target: duel lasts 20–40s. Light DPS ~18, Heavy charged ~30 burst.

---

## 4. WEAPONS — 10 total (Dead Cells-style loot)

ID, damage, speed (sec per swing), range px, knockback, special. Speed <0.3 = fast. All weapons have Light / Heavy / Air variants (Heavy = dmg×1.6, kb×1.8).

| # | Name | Dmg | Speed | Range | KB | Special | Drop maps | Rarity |
|---|---|---|---|---|---|---|---|---|
| 0 | Rust Blade (starter) | 8 | 0.32 | 52 | 220 | none | start | common |
| 1 | Swift Daggers | 5+5 (2-hit) | 0.20 | 42 | 140 | 3rd hit dash-through | 1,2,5 | common |
| 2 | Heavy Hammer | 16 | 0.65 | 58 | 520 | ground slam shockwave | 2,4,6 | rare |
| 3 | Spear of Echoes | 11 | 0.42 | 78 | 300 | tipper ×1.5 at max range | 3,5 | rare |
| 4 | Bow of Thorns | 7 | 0.45 | 260 | 180 | fires projectile, 12 ammo/room | 2,3,7 | rare |
| 5 | Fire Tome | 6+burn 2/s×3s | 0.55 | 200 | 160 | projectile + burn | 4,6 | epic |
| 6 | Ice Gauntlet | 9 | 0.38 | 46 | 260 | hit slows enemy 40% 2s | 5,7 | epic |
| 7 | Volt Knuckles | 7 | 0.24 | 40 | 200 | every 4th hit stuns 0.8s | 6,8 | epic |
| 8 | Greatshield Blade | 10 | 0.45 | 54 | 280 | blocking costs 50% less | 3,6 | epic |
| 9 | Void Scythe (legendary) | 14 | 0.40 | 64 | 420 | kill → explosion 10 dmg AoE | 7, boss only | legendary |

Drop logic (PC + ESP32 same): on room clear 35% drop random weapon allowed for that map (see table), reroll rarity luck +10% per NG+. Old weapon drops on ground, press Interact to swap. Bow/Tome ammo refills each room.

PC data lives in `WEAPONS` dict in `main.py`. ESP32/SD copy lives in `/weapons.json` (same fields) — see §7.

---

## 5. ENEMIES — 6 + 1 boss (less than Dead Cells, deeper than mob)

All have Smash-like % scaling, shield-piercing heavies, and directional influence (they drift toward stage center at high %).

| ID | Name | HP | % resist (weight) | Behavior (AI tick 10Hz) | Attacks | Cells |
|---|---|---|---|---|---|---|
| 0 | Husk Brawler | 30 | 1.0 | walk to player, jump if gap, light punch ×2 | Light 6/180kb, Heavy 12/380kb (telegraphed 0.5s red flash) | 3 |
| 1 | Dart Imp | 22 | 0.8 (flies farther) | keeps 180px range, hops away, throws dart | Dart projectile 5 dmg/150kb, dive 7 | 4 |
| 2 | Stone Guard | 60 | 1.8 (tanky) | slow chase, holds shield 1s when player charges heavy | Slam 14/450kb, shield blocks 80% | 6 |
| 3 | Wind Monk | 35 | 0.9 | double-jumps, air-attacks, dashes behind player | Air spin 8×2, gust pushes player | 5 |
| 4 | Bomber Wisp | 18 | 0.7 | floats to player, blinks 1s then explodes | Explosion 18 dmg/600kb (also hurts enemies) | 4 |
| 5 | Mirror Duelist | 45 | 1.0 | mirrors inputs: dashes your dash, shields your heavy 50%, punishes flask | Light 8, Counter-Heavy 15 (only if you spam) | 8 |
| B | Rift King (boss, map 8) | 220 + summons 2 wisps at 50% | 2.2 | Phase1 brawler+slam, Phase2 (<50%) jumps to center, shockwaves + summons | Slam 16, Wave projectile 10, Grab 20 | 30 |

Spawn budget per map (keeps duels 1v1–1v2): maps 1–2: 1 enemy, 3–5: 2 enemies, 6–7: 2–3 enemies (max 3), 8 boss + adds. Never more than 3 alive — this is the anti-Dead-Cells-horde rule.

Enemy data lives in `ENEMIES` dict in `main.py` + `/enemies.json` on SD.

---

## 6. MAPS — 12 total (run uses 8 + boss, rest are variants/NG+)

Tile 16px on ESP32 (320×240 = 20×15 tiles). PC renders 960×540 but collision uses same tile strings. Legend: `#`=solid, `=`=one-way, `^`=spikes, `D`=exit door, `P`=player spawn, `1`–`5`=enemy spawn, `W`=weapon chest, `H`=heal fountain, `.`=empty.

| # | Name | Theme colors (TFT 16-bit) | Size (tiles) | Gimmick | Enemies | Weapon drops |
|---|---|---|---|---|---|---|
| 1 | Ember Ruins | bg 0x2104, tiles 0xBDF7 | 60×15 | flat + 2 platforms, no pits | Husk | Daggers |
| 2 | Moss Cavern | bg 0x0320, tiles 0x4CA3 | 60×15 | one-way vines, small pit | Husk, Imp | Hammer, Bow |
| 3 | Sky Bridges | bg 0x001F, tiles 0xFFFF | 70×15 | 3 floating islands, pits = fall +20% | Imp, Guard | Spear, ShieldBlade |
| 4 | Sunken Vault | bg 0x000F, tiles 0x07FF | 65×15 | water slows fall, spikes | Guard, Monk | Hammer, Fire |
| 5 | Ashen Forge | bg 0x4000, tiles 0xF800 | 65×15 | lava floor edges (spike tiles), moving? static on ESP32 | Monk, Husk+ | Daggers, Spear, Ice |
| 6 | Howling Peaks | bg 0x10A2, tiles 0xFFFF | 70×15 | wind pushes +40px/s, narrow | Stone, Monk, Wisp | Volt, ShieldBlade, Fire |
| 7 | Void Rift | bg 0x1002, tiles 0xC0CF | 60×15 | low gravity 0.85×, 2 wisps intro | Wisp, Duelist | Ice, Volt, Bow |
| 8 | Throne of Echoes (BOSS) | bg 0x0000, tiles 0xFE60 | 40×15 | flat arena, no pits, fountains locked till win | Rift King | Scythe (on win) |
| 9 | Fungal Deep (variant) | green/purple | 60×15 | bouncy shrooms (jump×1.3) | Imp, Wisp | Bow, Fire |
| 10 | Iron Bastion (variant) | gray/gold | 60×15 | crushers (timed spike tiles) | Guard, Duelist | Hammer, Spear |
| 11 | Storm Spire (variant) | blue/white | 70×15 | wind + pits | Monk, Imp | Volt, Daggers |
| 12 | Hollow Garden (secret) | pink/dark | 50×15 | heal fountain free, 1 Duelist guarding Scythe | Duelist | Scythe (alt) |

Run order: 1→2→3→4→5→6→7→8. Maps 9–12 swap in on NG+ or via secret doors (map 4 → 9, map 6 → 10/11, map 7 → 12 if you have 20+ cells). PC prototype implements 1–8 fully; 9–12 share generator with different palette + spawn table (so "lots of maps" without 12× hand-draw code).

Level strings: stored as list of strings in `MAPS` in `main.py`. ESP32/SD copy: `/maps/map01.txt` … `/maps/map12.txt` + `/maps/meta.json` (spawn/weapon tables). 2GB SD holds all + BMP sprites with room to spare (<2MB used).

---

## 7. SD CARD (2GB) LAYOUT + FILE FORMATS

Format FAT32, cluster 4KB. Total game <2MB.

```
/weapons.json      # copy of WEAPONS table
/enemies.json      # copy of ENEMIES table
/maps/meta.json    # [{id,name,parTime,bg,tile,spawn[],drops[]}]
/maps/map01.txt … /maps/map12.txt  # ascii tilemaps above
/sprites/player.bmp  (16×24, 16-bit)
/sprites/enemy0.bmp … /sprites/boss.bmp
/save.dat          # best_map, best_cells, wins, unlocks (binary or json, 64 bytes)
```

`meta.json` example:
```json
{"id":3,"name":"Sky Bridges","bg":31,"tile":65535,"spawn":[1,2],"drops":[3,8],"par":75}
```

Port rule: PC `load_maps()` reads `MAPS` dict; ESP32 `loadMap(id)` reads SD line-by-line (never load all 12 at once — RAM!). Sprites as 16-bit BMP, no PNG/JPG decoder on ESP32.

---

## 8. WIRING — STEP BY STEP (do AFTER PC build works)

> You have: ESP32 TFT LCD + 2GB SD + Joystick Shield (4 btns + stick + 2 extra). Two cases below. **Follow only one.**

### Case A — You have ESP32-2432S028R CYD (TFT+ESP32 one board, RECOMMENDED)

This is what "TFT LCD ESP32" usually means. TFT, touch, RGB LED and SD slot are already wired. **Do NOT rewire TFT/SD.**

1. Power off everything. USB unplugged.
2. SD: push 2GB card (FAT32) into onboard TF slot. If card >2GB it still works if formatted FAT32, but your 2GB is perfect.
3. Joystick Shield → CYD pins (solder or Dupont to CYD extension header). CYD is 3.3V ONLY — **never connect shield VCC to 5V**:
   - Shield `GND` → CYD `GND`
   - Shield `5V/VCC` → CYD `3V3` (shield works at 3.3V, joystick range 0–3.3V)
   - Shield `VRx` → `GPIO 34` (input-only, ADC1)
   - Shield `VRy` → `GPIO 35` (input-only, ADC1)
   - Shield `SW` (stick click) → `GPIO 16` (via 10k pull-up to 3V3 if shield has none; most shields pull low on press → use `INPUT_PULLUP`)
   - Shield `A` (Jump) → `GPIO 22`
   - Shield `B` (Light) → `GPIO 21`
   - Shield `C` (Heavy) → `GPIO 17`
   - Shield `D` (Shield) → `GPIO 26` (NOT 4 — GPIO4 is touch SDA on CYD)
   - `EXTRA1` (Interact) → `GPIO 27`
   - `EXTRA2` (Heal/Pause) → `GPIO 0` (BOOT button pin — tap works, hold 1s+ for pause, hold 5s enters flash mode, that's fine)
4. All buttons: other leg → GND. Use `INPUT_PULLUP`, pressed = LOW. Add 100nF cap to GND per button if you see bounce (optional).
5. Joystick center calibration: on boot, read VRx/VRy 10×, average = center (~2048). Deadzone ±180. Done in code (`calibrateStick()`).
6. Power: USB 5V/1A+ into CYD USB. TFT backlight (GPIO 21 on some CYDs — conflict!) — if your CYD backlight is GPIO 21, move Light button `B` → `GPIO 25`. Check your CYD variant table in code header before compiling.
7. Smoke test: multimeter continuity GND→GND, 3V3→VCC (no short), then USB on. TFT should show boot logo. Open Serial 115200, move stick → ADC 0–4095 prints.

### Case B — You have separate ESP32 DevKit + ILI9341 TFT + SD module + Shield

Use only if you do NOT have a CYD.

**Power rail (critical): ESP32 is 3.3V. ILI9341 VCC → 3V3, LED → 3V3 via 100Ω, SD VCC → 3V3. 5V will kill TFT/SD logic (some TFTs tolerate 5V VCC but not logic).**

| TFT ILI9341 | ESP32 | SD module | ESP32 (shared HSPI) | Shield | ESP32 |
|---|---|---|---|---|---|
| VCC | 3V3 | VCC | 3V3 | VCC | 3V3 |
| GND | GND | GND | GND | GND | GND |
| CS | GPIO 15 | CS | GPIO 5 | VRx | GPIO 34 |
| RST | GPIO 2 | MOSI | GPIO 23 (shared) | VRy | GPIO 35 |
| DC | GPIO 4 | MISO | GPIO 19 (shared) | SW | GPIO 16 |
| MOSI | GPIO 23 | SCK | GPIO 18 (shared) | A | GPIO 22 |
| SCK | GPIO 18 | — | — | B | GPIO 21 |
| MISO | GPIO 19 | — | — | C | GPIO 17 |
| LED | 3V3 | — | — | D | GPIO 26 |
| — | — | — | — | EXTRA1 | GPIO 27 |
| — | — | — | — | EXTRA2 | GPIO 0 |

Steps: 1) unplug USB, 2) wire GND first, 3) wire 3V3, 4) wire SPI bus (23/19/18 shared — TFT + SD on same bus, different CS), 5) wire TFT CS/RST/DC, 6) wire SD CS, 7) wire shield analog+buttons, 8) insert FAT32 SD, 9) USB on, flash `TFT_eSPI` (setup: ILI9341, 320×240) + SD test sketch, 10) Serial check.

Libraries (Arduino IDE): `TFT_eSPI` (Bodmer), `SD`, `ArduinoJson`. `TFT_eSPI/User_Setup.h`: uncomment ILI9341, set pins per table above, `TFT_WIDTH 240 TFT_HEIGHT 320`, rotation 1 (landscape 320×240).

### Bring-up checklist (both cases)

- [ ] PC prototype beats map 3 without crash
- [ ] SD formatted FAT32, files from §7 copied, `map01.txt` opens on PC
- [ ] TFT shows 320×240 test pattern (run `tft.fillScreen()` sketch)
- [ ] Serial prints stick 0–4095 + each button LOW on press
- [ ] 60 FPS target on ESP32: 16×16 tiles, max 3 enemies, no floating point in hot loop (use int), sprites from SD cached to PSRAM once

---

## 9. ESP32 PORT PLAN (after wiring)

1. Copy `WEAPONS`/`ENEMIES`/`MAPS` from `pc_build/main.py` → `weapons.json`/`enemies.json`/`maps/*.txt` on SD (script: `python pc_build/export_sd.py` — TODO, format in §7).
2. Arduino sketch structure: `boot → init TFT/SD → calibrateStick() → loadMap(1) → loop: readInput() → update(player+max3 enemies) → drawTiles+Sprites → SD save on map clear`.
3. Cut for ESP32 perf: particles max 30, projectiles max 6, no per-pixel alpha, text via `TFT_eSPI` font 1/2 only, sound = passive buzzer on GPIO 25 (optional, square-wave beeps on hit/pickup).
4. Controls driver: `analogRead(34/35)` + deadzone, `digitalRead()` for buttons (debounce 25ms, heavy-charge measures hold time).
5. Test order: input test → map load test → 1-enemy duel test → full run test.

---

## 10. How to run PC build (do this FIRST)

```powershell
pip install pygame
python pc_build/main.py
```

Keys (Smash build): `A`/`D`/`←`/`→` move, `W` aim-up, `↓` drop/fast-fall, `Space` jump (×2, buffered + coyote time),
`Z`/`J`/`LMB` attack (dir=side-tilt, up=up-tilt, air=air), `X`/`K` hold/release charged smash,
`C` neutral special, `V` up special (recovery), `S`/`E` SUPER down special (counter for Blaze/Shade/Viper),
`Shift` dash (i-frames), `RMB` SMART (auto: counter aggression / dash danger / heavy kill-%),
`L` hold shield, `Enter` confirm, `P/Esc` pause, `TAB` slim move list (mid-fight), `F11` fullscreen,
`F` ULTIMATE (when gold bar is full).
Starts fullscreen (scaled); `--windowed` flag for window mode.

Gamepad (8BitDo SN30, XInput mode — boot it with Start+X): d-pad move/aim/drop, `A` jump,
`X` attack, `B` smash, `Y` neutral special, `LB` tap = dash / hold = shield, `RB` recover,
`Select` super, `Start` pause, `LB`+`RB` together = ULTIMATE. Menus: d-pad + `A` confirm /
`B` back (`Y` difficulty, `X` reroll CPU on select). Hot-plug supported; `PAD` shows in HUD.
Troubleshooting: title + help screens show live pad status and last input seen. If nothing appears:
1) power the pad with Start+X (XInput, blue LED pattern), 2) re-pair Bluetooth, 3) press any
button (status updates live), 4) Steam Input can hide pads from other apps — disable it for this game.

Win: take all 4 CPU stocks (launch past blast zone). Lose: lose your 4 stocks or time-out behind on stocks. Record kept per-fighter in `pc_build/save.json`.

---

## 11. Tuning checklist (when playtesting PC)

- Duel too short? +10 enemy HP. Too hard? player HP 100→120, dash cooldown 0.5→0.4.
- Pits too punishing? spike 15→10.
- Stick drift on hardware? widen deadzone 180→250.
- TFT slow? reduce particles 60→30, draw distance cull to camera.

## 12. Smash 1v1 Arena rebuild (replaces exploration mode on PC)

Feedback was: rect graphics + Dead Cells loop. New direction = pure Smash-like 1v1:

- **Battle format:** 1v1, **4 stocks**, **3:00 timer**, blast-zone KOs on huge scrolling stages. Fast pace:
  short recoveries, quick countdown/KO/respawn, fast dash cooldown, +8% move speed, 40-HP shields.
  Timeout → higher stocks wins, tie → sudden death (both to 300%).
- **Item drops (Smash-style):** every 7–12s (max 2 on stage), walk over to grab. POWER STAR
  (3s invincible), SNACK (−30% damage), ULT ORB (+35 ult), HAMMER (8s +40% melee), HEX BOLT
  (foe +18%), FROST CELL (foe slowed 3s), FUSE BOMB (1.2s fuse, big AoE near the foe).
- **Ultimates:** dealing damage charges your gold bar (taking hits charges less); ULT ORBs help.
  At 100, press `F` (must be free/grounded-neutral): cinematic freeze + banner + unique effect —
  INFERNO CATACLYSM, ZERO FIELD, JUDGMENT, BEDROCK ERUPTION, MIRROR ANNIHILATION, RIFT COLLAPSE,
  TEMPEST, EXTINCTION, SUPERNOVA, VENOM BLOOM. Point-blank ults can be dashed (DODGED!).
  Damage % raises knockback. Timeout → higher stocks wins, tie → sudden death (both to 300%).
  Stages pass through from below (easy recovery), 2 air actions (double jump + up special).
- **Roster — one file per fighter in `pc_build/fighters/`** (registry in `fighters/__init__.py`).
  Each module owns stats, projectile, specials + a signature mechanic no one else has:

| Fighter | Weight / Speed | Neutral-B | Up-B (recovery) | Down-B (unique) |
|---|---|---|---|---|
| CINDER, Meteor Heretic | 1.0 / med | Delayed meteor (+burn) | Rising slash | Inferno Counter |
| DISC, Chakram Dancer | 0.9 / med | Returning chakram | High leap | Glacier Burst (slow) |
| ARC, Static Brawler | 0.85 / fastest | Bolt | Longest lift | Blink + static bank/discharge |
| BULWARK, Living Fortress | 1.5 / slow, power 1.35× | Heavy rock | Short lift | Stance + unlaunchable charge |
| GLASS, Glass Duelist | 0.75 / fast, power 1.1× | Needle | Slash leap | Mirror punish + REFLECTS shots |
| NULL, Gravity Well | 1.45 / slow, power 1.3× | Rift orb | Heavy lift | Collapse well (drag + boom) |
| BLINK, Rift Courier | 0.8 / fastest air | Phase dart | Best lift + TRIPLE jump | Blink |
| TECTON, Seismic Monk | 1.6 / slowest, power 1.5× | Seismic rock | Short lift | Stance + landing quakes |
| ECHO, Paradox Thief | 0.95 / fast | Phase bolt | Slash leap | Echo set/recall teleport |
| LEECH, Debt Collector | 0.9 / fast, power 1.05× | Venom darts (slow) | Slash leap | Venom Counter + 30% lifesteal |

- **Shared kit:** jab / side-tilt / up-tilt / air / up-air / charged smash / shield (40 HP, breaks → 1.6s stun + glitch) / dash with i-frames. Knockback soft-caps past 1500 so 999% stays sane.
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
  Signature mechanics: triple jump (Blink), telegraphed meteors + burn (Cinder), returning
  chakram that can hit its owner (Disc), dash-banked static discharge (Arc), unlaunchable
  smash-charge (Bulwark), projectile reflect ×1.5 (Glass), dragging gravity well (Null),
  landing shockwaves (Tecton), echo set/recall (Echo), 30% lifesteal (Leech).
- **Win streaks:** consecutive match wins build a power multiplier (+4% per streak, max +20%, P1 only,
  shown on VS/title/game-over). Losing resets it. Best streak saved.
- **Smash UI (pro pass):** navy+gold theme, cached fonts, rounded panels, buttons clickable via mouse.
  Title (live demo fight, shine-sweep logo, FIGHT / HOW TO PLAY / QUIT menu, win record) → HOW TO PLAY
  (controls grid + tips) → character select (Smash-style: P1 + CPU hero panes up top,
  10 portrait tiles below, clickable CPU reroll chip, difficulty picker, stage cards with
  mini platform thumbnails, staggered slide-in) → VS screen (sliding
  team-color cards, popping VS emblem, stage pill) → READY 3-2-1-GO (ring pulse on numbers, sliding
  banner for K.O./GAME/TIME) → slim HUD (top-center timer pill, tiny top-corner chips: icon +
  popping %, stock pips, ult micro-bar, cooldown dots — never covers the fight) → pause menu
  (Resume/Rematch/Characters/Title) → VICTORY/DEFEAT screen (per-fighter stocks/peak%/best-combo
  stats, head-to-head wins, REMATCH/FIGHTERS/TITLE buttons). `TAB` opens a live side move-list
  mid-fight (every attack + real-time special cooldown dots, slim translucent). KO freeze plays
  cinematic letterbox bars + white flash; sudden-death/low-time pulses a red vignette; combo
  milestones splash TRIPLE!/RAMPAGE!/UNSTOPPABLE!/GODLIKE!; fast movers leave ghost trails.
  Coyote time + jump buffering for smooth movement. Fade transitions between states.
- **Stages (18, big + scrolling + detailed):** Ember Arena (3000), Sky Battlefield (3200),
  Void Final (2800), Fungal Hollow (bounce shrooms), Storm Spire (wind), Tide Vault (low-grav),
  Iron Foundry (spikes), Thorn Garden (spikes), Glacier (slippery ice), Dune Sea (headwind),
  Hollow Star (floaty), Clockwork (phasing platforms), Magma Core (spikes + bounce),
  Cloud Nine (pads + wind), The Rift (4200, everything),
  Harbor Town (clean plaza), World Tree (bounce bloom), Sunset Keep (rooftop duel).
  Collision platforms are aligned to the key art layouts. Camera follows the PLAYER (72% P1 +
  28% foe + velocity lookahead) with parallax;
  pillars, chains, runes, grass, lava cracks, pads, phases, spikes all drawn per theme. Blast zones scale with world width.
- **Stage paintings:** drop AI-generated backgrounds in `pc_build/assets/stages/` using the exact
  filenames in `pc_build/assets/stages.json` (e.g. `sky_battlefield.png` for the floating ruins,
  `magma_core.png` for the volcano). Optional `<name>_mid.png` transparent layer parallaxes on top.
  Paintings cover-fit with camera scroll; procedural platforms/hazards/fighters draw over them and
  the glowing platforms always mark real ground. Missing files fall back to procedural art.
- **Breakable terrain:** floating platforms marked cracked take melee/projectile/bomb/ult damage
  and collapse (removed from collision), regenerating after 12s. Mains are never breakable.
- **Lava pools:** animated pools burn (+10%, 2s burn) and launch you out. Spikes: +8% pop-up.
- **Event visual modes (auto-triggered):** BLOOD (anyone ≥100%), VOID (offstage danger + wisps),
  DARK RAINBOW (both on last stock), RAINBOW (sudden death), CHAOS ULTRA (both ults full + shout),
  SOLARIS (golden burst at GO), COSMOSIS (starfield on ultimates), GLITCH (rgb slices on
  breaks/counters/KOs), screen-shake QUAKE boost + dust on huge launches, BLACK AND WHITE
  (match-deciding end phase). KO freeze keeps letterbox bars; sudden/low-time keeps red vignette.
- **Render quality:** real low-poly 3D fighters (one rig file of logic per pose state: boxes with
  depth, strong 24-degree camera yaw + idle sway, windup turns, swing sweeps, launch corkscrews,
  directional flat shading, per-char 3D helms/weapons, glow eyes),
  extruded 3D stage slabs with side caps, rotating background cubes, perspective floor grids,
  additive-blend bloom (projectiles, charges, KOs, logo, buttons), cached radial
  glow sprites, gradient UI panels, shadowed HUD numbers, shockwave rings on KOs/ults/bombs/breaks/
  landings, white-hot slash cores, soft layered blob shadows, gradient-shaded fighters with limb
  highlights and head crescents, god rays + animated lava + shaded clouds, pulsing under-glow,
  fullscreen vignette grade. Holds ~300fps headless.
- **3D art drops:** put AI-generated fighter sprites in `pc_build/assets/fighters/<cid>/`
  (160×160 transparent PNGs, feet at (80,146), facing right — full spec in `assets/README.md`).
  Poses used automatically (idle/run/jump/fall/charge/shield/hit/break/special/attack_*);
  anything missing falls back to the procedural 3D rig. No code changes needed.
- **CPU:** per-character AI with 4 difficulty levels (select screen, `Y` or click):
  ROOKIE (slow reactions, no edgeguards, botches recoveries) → FIGHTER → VETERAN →
  NIGHTMARE (0.10s reactions, shields smashes, edgeguards rising foes, punishes charged smashes
  with counters). All levels combo stunned victims, whiff-punish recoveries, dash through incoming
  projectiles, grab items, fire charged ultimates, and play their kit (Echo recalls offstage, Glass
  reads dashes, Arc dash-banks static, Tecton stomps from above). Measured: Nightmare beats Rookie
  ~7/8 across matchups. Per-fighter `ai_lv` override exists for testing.
- **Animation system** (`render_fighter` + squash/rot compositor, `pc_build/main.py`): fighters render to a 160px
  canvas then get non-uniform squash & stretch (spring-damped), tumble/spin rotation, white hit-flash, dash
  afterimage ghosts. Keyframed poses: idle breathe + blink, 2-phase run cycle with footstep dust, skid,
  jump stretch / land squash (impact-scaled) / fall spread, per-move windup→active→recover arm/weapon
  keyframes, full-body 360° nair/uair/up-B spins, charge crouch + tremble + rising aura, shield crouch +
  wobble, sprawl + tumble on launch, X-eyes + orbiting stars on shieldbreak, cast/counter/stance poses,
  per-char extras (king cape, frost quiver, volt headband tails, shade scarf, golem rock shoulders).
  Combat fx: slash-arc + spin-ring fx, glow puffs, smoke, hit sparks, speed streaks, KO white-flash +
  radial lines, % pop on HUD, outlined announcements. Living stages: volcano smoke/embers, drifting
  clouds + birds + sun halo, nebula + twinkle stars + floating shards, metallic platforms with rivets,
  blinking edge lights, travelling spark, under-glow.

*End of docs — single source of truth. If code and this file disagree, this file wins; update code to match.*
