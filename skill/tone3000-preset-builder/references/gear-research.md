# Gear research — cross-referencing real rigs before designing a chain

`tone-recipes.md` is a static starting map. For anything not already in it, or when the user
wants a specific era/album, **research the real gear first** — don't invent a chain from memory.

## Why not scrape equipboard.com directly
Equipboard disallows automated fetches (`robots.txt`) and sits behind Cloudflare bot protection —
every direct HTTP attempt returns 403, spoofed User-Agent or not. **Do not try to fetch
equipboard URLs directly** (`web_fetch`, `curl`, `requests`, etc.) — it will fail and waste a turn.

## What to do instead: search, don't fetch
Claude's own web search already indexes equipboard's per-artist gear pages (and Ground Guitar,
Premier Guitar, Guitar World, forum rig-rundowns) and returns real, often album/era-specific
snippets. This is *better* than parsing one page: it naturally cross-references multiple sources.

Run 2–4 targeted searches per artist, one per gear category, before falling back to the static
map:
```
<artist name> equipboard pedals
<artist name> equipboard amplifier
<artist name> pedalboard rig <song/album>        # when the user named a specific track/era
<artist name> guitar rig <song/album> interview
```
Read the snippets for: exact model names, which album/tour/song they're tied to, and any direct
quote from the player about *why* (a Rat vs a Tube Screamer changes the chain grammar, not just
the block). Note conflicting sources honestly (rig rundowns disagree constantly) and pick the
best-attested one — usually the one multiple independent sources repeat, or the one tied to the
specific song asked about.

## Turning real gear into a TONE3000 search term
Model names rarely match capture titles verbatim. Try the shortest distinctive part first, widen
if empty:
| Real gear | Try first | Then |
|---|---|---|
| ProCo Rat / Rat 2 | `rat` --gear pedal | `proco rat` |
| Ibanez Tube Screamer TS-9 / TS808 | `ts9` or `ts808` --gear pedal | `tube screamer` |
| Marshall JMP 2203 / 1959 SLP | `jmp` or `super lead` --gear amp-cab | `marshall plexi` |
| Mesa Boogie Mark IIC+ | `mark iic` --gear amp-cab | `mesa boogie iic` |
| Diezel VH4 | `vh4` --gear amp-cab | `diezel` |
| MXR Phase 100 / Distortion+ | model number --gear pedal | brand + short name |
| Boss NS-2 / TU-3 (noise gate/tuner) | not worth a NAM capture — these don't shape tone; skip, the plugin's own gate covers NS-2 |
Always confirm with `tone.py tone ID` before committing — a title match isn't proof it's the
right capture; check the description/tags for the amp+cab or pedal combo actually named.

## What this changes about the chain
A rig rundown often reveals gear grammar the static map guesses wrong:
- **Amp-only, no pedal** at all in some eras (Hetfield post-'85: "distortion always starts with
  the amp" — pedals removed, gain purely from the preamp/Mesa/Diezel). Don't force a drive block in.
- **Modulation/pitch gear** (Whammy, Phase 100, chorus) — NAM can't capture it; name it in the
  report as a limitation exactly like `tone-recipes.md` already does for delay/chorus.
- **Two amps blended** (Diezel + Plexi + Bogner, or dual-amp rigs) — this is exactly what the
  stereo branch pattern in `preset-format.md` is for; a "blended" rig described in a source maps
  naturally to two chains, not one.

## Worked example (verified live)
James Hetfield, *Ride the Lightning* era: Ibanez TS-9 → Marshall JMP-50 (`72145`, "SL68 I Drive").
*Kill 'Em All* era: ProCo Rat (`78883`) → modded Marshall plexi. *Master of Puppets* era: Mesa
Mark IIC+ (`81803`), no pedal. Later/Diezel era: Diezel VH4 (`89509`), no pedal. All four IDs
already existed in `tone-recipes.md`/`examples/library.json` from prior research — real sourcing
confirmed the earlier picks rather than replacing them, which is the point of doing this step: it
turns a plausible guess into a checked one, and sometimes it won't agree with the guess.

## Keep it silent
This research happens before you reply, not as a visible back-and-forth — the user asked for a
tone, not a bibliography. Mention sourcing only briefly in the final report (e.g. "per rig
rundowns from the Ride the Lightning era") and only where it's interesting or where you had to
choose between conflicting accounts.
