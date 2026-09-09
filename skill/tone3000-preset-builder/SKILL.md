---
name: tone3000-preset-builder
description: Build complete, ready-to-load signal-chain presets (.t3kpreset files) for the free TONE3000 NAM guitar/bass plugin and standalone app — pedal → amp → cab → outboard → reverb chains, mono and stereo, or preamp-only DI chains for players reamping into real power amps and cabs — from an artist, a song, a section of a song, or a plain-English tone description, using real captures searched live on tone3000.com and cross-referenced against real-world rig research. Use this whenever someone mentions TONE3000, NAM captures, wants "a preset/tone/rig/chain that sounds like an artist or song", asks how to build a chain in TONE3000, wants their TONE3000 preset folder found, or wants existing .t3kpreset files inspected or fixed. Trigger even if they just say "make me a Slash tone" or "Nirvana rig" and they use TONE3000.
---

# TONE3000 Preset Builder

You build real preset files for TONE3000 (the free NAM plugin) that load and play, written
straight into the user's preset folder, using captures that exist on tone3000.com right now —
grounded in real rig research, not guessed gear. Everything deterministic lives in
`scripts/t3k.py` (stdlib Python 3.8+, no install). Your job is the tone design: turning "the
Everlong chorus" into the right pedal, amp, cab and room.

**Never guess IDs or model names.** Every block must come from a live `search`/`tone` lookup in
this session. The file format is exact-bytes binary — never hand-write it; always use the script.

## Workflow

### 1. Check preset folder and authentication (do this first, silently)
```
python scripts/t3k.py presets-dir
python scripts/t3k.py whoami
```
- **Preset folder**: Prints the folder for this OS (Windows `%APPDATA%\TONE3000\Presets`, macOS
  `~/Library/Application Support/TONE3000/Presets`, Linux `~/.config/TONE3000/Presets`) and
  whether it exists. If it does not exist, TONE3000 has never been run — tell the user to install and
  launch it once (https://www.tone3000.com/plugin), or build with `--out` to a folder of their choice.
  Never overwrite or delete files you did not create; the user's own presets live here too.
- **Authentication**: If `whoami` prints user info, you're ready to search and build live tones.
  If `whoami` reports not logged in:
  - If the user asks for an existing artist/tone covered in `presets/` (or `examples/library.json`),
    offer to install it offline immediately with `install-templates` (zero credentials needed).
  - If a new live search is required, instruct the user to run `python scripts/t3k.py login`
    (or paste their Secret Key `t3k_cs_...` from https://www.tone3000.com/settings). If the user
    provides their key in chat, run `python scripts/t3k.py login --key <key>` for them.

### 2. Intake — ask only what changes the build
Read `references/intake.md`. Ask in one short message, skipping anything already known:
- **Target**: artist / song / *which part* (Creed's clean intro vs the chorus wall; the Everlong
  verse is clean, the chorus is Mesa crunch). Default to the song's signature part and say so.
- **Mono, stereo, or both** (default both — stereo is free).
- **Rig**: what they plug into and monitor through. Studio monitors / headphones / FRFR →
  chain must include a cab. Real guitar amp + cab → no cab in the chain. **Real power amp(s) +
  real cab(s), wants only the preamp digitally** → this is DI/reamp mode, a distinct case — see
  step 4. Bass? Use bass captures.
- **Guitar/pickups** only if it changes the pick (single coils into high gain → nudge gain up;
  humbuckers into a plexi → run the amp capture's lower-gain model).
One round of questions maximum; then build. Plain "just make it" → sensible defaults, stated.

### 3. Check memory & research real gear (silent — before you design anything)
First, check the local repository memory to see if the artist/song hardware stack is already documented:
```
python scripts/t3k.py rig "<artist or song>"
```
The repository includes an offline database (`references/artist-rig-memory.json` / `references/artist-rig-library.md`) of 80+ iconic artists seeded from Equipboard (pages 1–5) and historical rig rundowns. If a match exists, use its verified hardware spec and pre-mapped captures immediately — no web searching required!

If not in memory, read `references/gear-research.md`. Cross-reference what the player actually used:
2–4 targeted web searches (`<artist> equipboard pedals`, `<artist> equipboard amplifier`, plus the song/era if given).
**Do not attempt to fetch equipboard.com directly** — it blocks automated access (robots.txt + Cloudflare, confirmed) —
work from the search tool's indexed snippets instead, which already pull from equipboard, Ground
Guitar, and rig-rundown interviews. This step is silent; don't narrate the searches to the user.


### 4. Design the chain
Read `references/tone-recipes.md` for chain grammar, genre defaults, and a starting gear map for
~40 artists (verified IDs as of Sept 2026 — re-verify with `tone ID`, captures get deleted). Use
your step-3 research to override or refine the map: real sourcing sometimes means *no* pedal at
all in an era, or a specific amp the map doesn't have. Chain order is normally:
`compressor/outboard → drive/fuzz/boost → amp (or amp+cab) → [cab IR if head] → console/EQ → reverb/space`

**If the user is in DI/reamp mode** (real power amp + real cabs, wants preamp-only), read
`references/di-reamp-mode.md` instead of following the grammar above: the chain stops at the amp's
preamp stage — no cab block, no mic, no reverb, ever. Search `gear=amp` (never `amp-cab`) and
confirm each pick is a true DI/preamp capture (tags like `di`, `preamp-only`, `reamp-ready`, `no ir
included`; reject anything naming a mic or cab spec) before using it.

What NAM **cannot** do: delay, chorus, phaser, tremolo, wah, pitch-shift — any time-varying
effect. If research turns up a Whammy, Phase 100, chorus etc., say so plainly and build the best
static rig around it.

### 5. Search TONE3000 and verify every block
```
python scripts/t3k.py search "jcm800" --gear amp-cab --n 8
python scripts/t3k.py tone 87735            # lists every model variant + tags + description
```
If authentication is needed, run `python scripts/t3k.py login` (or set `T3K_SECRET_KEY` / `T3K_API_KEY`).
Translate real gear names into search terms per the table in `gear-research.md` (a "ProCo Rat"
rarely matches a capture titled that exactly — search `rat`, widen if empty). Prefer: A2
captures, high download counts, creators with settings descriptions, and titles/tags naming the
artist directly (creators often upload "Kurt Cobain DS-1" style packs — search the artist name
too). Read the model list and pick the variant by **name regex** (`"model": "D5-T6"`), not index.
Gear tags: `amp-cab` (amp with cab, ready to go), `amp` (head — needs a `cab` IR after, unless
DI/reamp mode, which needs neither), `cab`, `pedal`, `outboard`, `space` (reverbs/rooms, IR). See
`references/api.md` for the API.

### 6. Write the recipe and build
Recipe JSON (one object or a list) — full schema in `references/preset-format.md`:
```json
{
  "name": "Foo Fighters - Everlong (chorus)",
  "chain": [
    {"tone": 87914, "model": "Drive-II$"},
    {"tone": 79103, "model": "Orange Crunch"},
    {"tone": 88038, "model": "Room", "mix": 0.28}
  ],
  "stereo": {"branchAfter": 0, "right": [{"tone": 70408}, {"tone": 88038, "model": "Room", "mix": 0.28}]}
}
```
```
python scripts/t3k.py build recipe.json --copy-to ./out
```
Writes mono + `[Stereo]` files into the preset folder (or `--out DIR`) and named copies into
`--copy-to` — present those copies to the user as downloads. The build self-verifies; if it
prints `VERIFY FAILED`, fix and rebuild before replying.

**Levels** (the script's defaults; only override with reason): every block at unity, except cab
IRs at +7.7 dB (the plugin pads short IRs −18 dB). Reverb/space IRs default to 30% mix. Per-block
normalisation is on, so stacking boosts clips — do not "help" the level. Global Params ship flat.

**Stereo** = TONE3000's dual-lane engine. `branchAfter: N` splits the right lane off after left
block N (0-based) — share the front end, differ after the split: dual amps (branch after the pedal),
dual cabs (after the head), dual rooms (after the amp). Omit `branchAfter` for two independent
chains — the natural shape for a real "blended two-amp rig" a rig rundown describes. Pans default
hard L/R. DI/reamp presets are normally mono-only (`--mono-only`) — there's rarely a reason to
stereo-split a chain the user is about to send to one physical amp.

### 7. Report
Tell the user: preset names, the chain per lane with the exact capture titles and model variants,
what to reload (TONE3000 caches the loaded chain — reopen the preset browser), and any honest
caveats (an effect NAM can't do, a sound-alike used instead of the exact amp, a level they may
want to trim, or where real gear research changed the chain from the obvious guess). Offer the
download copies. Keep it short — cite sourcing in a phrase, not a bibliography.

### 8. Grow repository memory (continuous learning)
When you research a new artist, song, or era that isn't already stored in `references/artist-rig-memory.json`,
save the researched profile back into memory so the repository library continuously expands for offline use:
```bash
python scripts/t3k.py rig --add new_profile.json
```

## References
- `references/artist-rig-memory.json` — queryable offline database of 80+ artist rigs & Equipboard specs (pages 1-5)
- `references/artist-rig-library.md` — human-readable catalog and hardware cheat-sheet
- `references/intake.md` — question bank and rig → chain rules
- `references/di-reamp-mode.md` — users with real power amps/cabs who want preamp-only, no cab, no mic
- `references/gear-research.md` — cross-referencing real rigs via search (equipboard etc.) before designing
- `references/tone-recipes.md` — chain grammar, genre defaults, artist gear map with IDs
- `references/api.md` — official REST API v1, OAuth 2.0 PKCE, search & model endpoints, model_url
- `references/preset-format.md` — recipe schema, on-disk binary format, gain/mix maths, Params
- `../../examples/library.json` — 34 worked recipes (mono+stereo) to copy patterns from
- `../../examples/rolling-stone-top-solos.json` — worked solo recipes (Prince, Blackmore, Skynyrd, Allman Bros, Chuck Berry, Steely Dan)

