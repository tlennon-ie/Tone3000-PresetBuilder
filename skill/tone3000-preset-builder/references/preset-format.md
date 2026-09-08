# Recipe schema and the .t3kpreset file format

## Recipe (input to `t3k.py build`)
```json
{
  "name": "Artist - Song (part)",
  "chain": [ { "tone": 86314, "model": "D5-T6", "mix": 1.0, "outGain": 0.5, "inGain": 0.5, "enabled": true, "slimSize": 0.5 } ],
  "stereo": { "branchAfter": 1, "right": [ { "tone": 88038, "model": "Plate", "mix": 0.3 } ] },
  "params": { "toneTreble": 6.0 }
}
```
- `tone` (required): tone3000 tone id. `model`: case-insensitive regex against model names
  (first match); omit for the first model. Escape regex metachars (`0\\.50in`, `Boost-I$`).
- `mix` 0–1 (default 1.0; spaces 0.3). `outGain`/`inGain` normalised 0–1: **0.5 = 0 dB, each 0.1 = ±4.8 dB**
  (range ±24 dB). Defaults: unity; cab IRs 0.66 (+7.7 dB) to offset the plugin's −18 dB short-IR pad.
- `slimSize` 0–1: NAM A2 size tier (0.5 = full; 0 = lite for weak CPUs).
- `stereo.branchAfter`: 0-based index into `chain`; the right lane is fed from the *output of that
  left block*. Omit for an independent right chain (both lanes get the input). `right` blocks use the same spec.
- `params`: overrides for the faceplate (denormalised, the plugin's own units): `outputLevel`/`inputLevel`
  0–1 (0.5 = 0 dB), `toneBass/Mid/Treble` 0–10 (5 flat), `toneEqEnabled`/`gateEnabled` 0|1, `gateThreshold` dB,
  `chainPanLeft`/`chainPanRight` 0–1, `spreadEnabled` (mono widener), `alignEnabled`.
- A file can hold one recipe or a list. `build` writes `name` (mono) and `name [Stereo]` when `stereo` is present.

## Gear → block behaviour
| gear | platform | type | notes |
|---|---|---|---|
| amp-cab | nam | nam | complete; do not add a cab |
| amp | nam | nam | head only; must be followed by a `cab` IR for FRFR/monitors |
| cab | ir | ir | −18 dB pad applied by plugin → script uses +7.7 dB |
| pedal / outboard | nam | nam | unity; mix 1.0 |
| space | ir | ir | reverb/room IRs; plugin defaults long IRs to 50% — script uses 30% |

## On-disk format (why you never hand-write it)
`T3KB` magic + a JUCE `ValueTree::writeToStream` binary tree (verified against the plugin source
`PresetManager.cpp` and JUCE `juce_ValueTree.cpp`/`juce_Variant.cpp`):
```
T3KPreset {schemaVersion:int=1, name:string}
  ChainSnapshot {stereoEnabled:bool, branchSide:"left", branchAfterBlockId:string}
    ChainBlocks       [ChainBlock...]        (left lane)
    RightChainBlocks  [ChainBlock...]        (right lane)
  Params [Param {id, value:double}...]       (optional; missing → defaults)
ChainBlock {id:32-hex uuid, type:"nam"|"ir"|"insert", enabled, normalize, slimSize, inputGain,
            outputGain, mix, toneId:int, toneJson:string, activeModelId:int}
  [Eq]  (optional, flat if absent)  [ModelCache] (optional embedded bytes; omitted → downloaded)
```
Encoding: strings are UTF-8 + NUL; `var` values are `compressedInt(len) + marker + payload` with
markers int=1(int32 LE) boolTrue=2 boolFalse=3 double=4(f64 LE) string=5 int64=6 binary=8.
`compressedInt`: one size byte (bit 7 = negative) + that many little-endian bytes.
Use `t3k.py verify FILE` to parse any preset, including the user's own.
