# Intake — what to ask, and what each answer changes

Ask once, in one short message, only the items not already answered. Then build.

## 1. Target sound
| Ask | Why it matters |
|---|---|
| Artist, song, or description ("thick 70s fuzz into a cranked Marshall") | drives the whole gear map |
| **Which part of the track?** (intro/verse/chorus/solo) | many songs have two rigs: Creed "Higher" clean intro vs chorus wall; Everlong clean verse vs Mesa chorus; Comfortably Numb rhythm vs the Big Muff solo; SLTS clean chorus-y verse vs DS-1 chorus |
| Era / live vs studio? | Slash '87 Appetite vs later Jubilee; Metallica Puppets (Mark IIC+) vs Black Album (Rectifier-ish) |
| Their own tweak ("more mids", "less fizz") | choose model variant / add outboard EQ |

If they give only an artist, default to the artist's most iconic rig and *say which part you built*.

## 2. Output format
- **Mono, stereo, or both** — default both; stereo doubles files but costs nothing.
- Name preference (default `Artist - Song (part)`; stereo gets ` [Stereo]`).

## 3. Their rig (this changes the chain shape)
| Setup | Chain rule |
|---|---|
| Interface → DAW/standalone → studio monitors, headphones, FRFR/PA | Chain **must** end in a cab: use an `amp-cab` capture, or `amp` head + `cab` IR |
| Real guitar amp/cab, or plugin used purely for pedals/preamp in front of it | **No cab in the chain** — amp-cab captures will sound boxy; use `amp` heads or pedal-only chains; skip room IRs |
| **Real power amp(s) + real cab(s), wants only the preamp digitally** ("I do my own thing", names specific cabs/speakers, mentions reamping) | **DI / reamp mode** — read `references/di-reamp-mode.md`. No cab, no mic, no reverb, ever; find true DI/preamp-only captures, not amp-cab. Ask which real cab each chain is meant to feed and name presets accordingly. |
| Bass | search bass captures (`bass` in query); pedals/outboard fine |
| Direct DI recording for reamping later (no real cab yet, generic) | pedal/preamp only, tell them to add cab later |

Detect what you can: `python scripts/t3k.py presets-dir` proves the plugin is installed and which OS this is; don't ask for that. Interface/monitors/cabs you must ask (or read from memory if the user's rig is already known) — the difference between "no cab, add one later" and "no cab, ever, I have real hardware" is exactly the difference between the last two rows above, so if they mention *any* real speaker/cab/power-amp specifics, that's DI mode, not just "no cab."

## 4. Guitar / pickups (optional)
- Single coils (Strat/Tele) into high-gain: pick the amp's hotter model variant or add a boost pedal.
- Humbuckers into vintage Marshall/Vox: pick the lower-gain variant; the capture was likely made with humbuckers already.
- 7-string / downtuned: prefer tight amps (5150, Rectifier, Diezel) and a TS-style boost.

## Defaults when the user says "just make it"
Both mono+stereo; FRFR assumed (cab included); signature part of the song; unity levels; one room/plate reverb at ~30%. State every assumption in one line.
