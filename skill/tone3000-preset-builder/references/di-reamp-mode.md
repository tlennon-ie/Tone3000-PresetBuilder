# DI / reamp mode — for users with their own power amp + real cabs

Some users don't want TONE3000 doing the cab or mic at all — they own real cabs (often paired
with boutique/expensive tube power amps) and just want the *preamp* character digitally, then
reamp it out to real hardware. Detect this whenever the user describes real speaker cabinets,
a separate power amp, or says anything like "I do my own thing with a real rig" — treat it as a
distinct rig type in `intake.md`, not a variant of "real guitar amp."

## What to ask
- What real cab(s)/speaker(s) are they reamping into? (informational only — it tells you nothing
  to search for on TONE3000, but confirms this is DI mode and is worth reflecting back in the
  preset name so they remember which chain feeds which cab.)
- Any preference among boutique makers, or "surprise me" within a budget tier they mention.
- Genre/feel (this still drives pedal choice same as any other build).

## The rule: no cab, no mic, ever
**Never add a `cab` (gear=cab) or `space`/room-mic block to a DI-mode chain.** The chain ends at
the amp's preamp stage; their real power amp + real cab supplies everything after that. Adding a
cab IR or reverb here double-dips the signal path and defeats the entire point.

## Finding true DI / preamp-only captures
`gear=amp-cab` captures are already mic'd through a cab — wrong category entirely for this mode.
Search `gear=amp` (head/preamp only) and look for these markers in title/tags/description before
trusting a result:
| Marker | Meaning |
|---|---|
| `DI`, `BAL DI`, `DI-ready` | captured direct out — no cab in the signal at all |
| `preamp`, `preamp-only`, `preamp capture` | preamp stage only, sometimes still assumes a poweramp/cab downstream — check description |
| `reamp-ready`, `no ir included`, `no cab` | explicit statement, highest confidence |
| Silence on cab/mic (no "SM57", "Royer", "MD421", "cab" anywhere) | weak positive — verify with `tone ID`, read the description for reamp intent |
Reject anything whose title/tags name a mic (SM57, MD421, Royer, U87) or a cab spec (4x12, V30,
Greenback) — that means a cab is already baked in, exactly what this mode must avoid.

Two known-good starting points (verified live): **Two-Rock SSS Clean BAL DI** (`4658`) and
**Diezel VH4** (`53749`, tagged `di-ready`/`reamp-ready`/`poweramp-capture`) — both `gear=amp`,
no mic/cab in the signal. Treat these as the pattern to match, not a fixed list — boutique brands
turn over on TONE3000 constantly (Two-Rock, Bad Cat, Friedman, Wizard, Revv, Diezel, Category 5,
Komet, Carr, Cornell all show up; search the specific brand the user names first).

## Genre notes for this crowd
Users asking for this setup skew toward players who care about touch/dynamics and real-amp feel —
lean toward fewer, better-chosen pedals over a stacked chain. Common asks and what to reach for:
- **Hendrix**: Fuzz Face (`1531` verified) → clean-to-edge-of-breakup boutique amp DI, low mix.
- **Stoner / doom / fuzz**: Pro Co RAT 2 (`45294`, extensively stoner/doom-tagged) or Big Muff →
  a higher-gain boutique DI (Diezel, Friedman). Don't add a noise gate block unless asked; stoner
  tone usually wants the amp's own sag, not a tight gate.
- **Boutique clean platform**: skip pedals entirely — LA-2A (`69103`) → the DI capture is often
  the whole ask; these users often *are* the pedal (fingers/pick dynamics).

## Recipe shape
Just a `chain` with no `space`/`cab` entries — the recipe format doesn't need anything special:
```json
{"name": "Hendrix Boutique DI - Fuzz into Two-Rock (feeds real 1x12 Greenback)",
 "chain": [{"tone": 1531}, {"tone": 4658}]}
```
Name the preset after *which real cab it's meant to feed* when the user has more than one — it's
the only thing that tells them apart once loaded, since the plugin has no idea a physical cab exists.
