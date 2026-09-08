# TONE3000 Preset Builder — a Claude skill

Turn "make me a Slash tone" into a real, loadable preset for the free
[TONE3000](https://www.tone3000.com/plugin) NAM plugin — pedal -> amp -> cab -> outboard -> reverb,
mono and stereo, or preamp-only DI chains for players reamping into real power amps and cabs —
written straight into your TONE3000 preset folder, using captures searched live on tone3000.com.
The `.t3kpreset` file format was reverse-engineered from the plugin's
[open-source code](https://github.com/tone-3000/tone3000-plugin) and is written byte-exact.

## What's in here
```
skill/tone3000-preset-builder/         the Claude skill
  SKILL.md                             the workflow Claude follows
  references/                          chain grammar, gear map, DI-reamp rules, API, binary format
  scripts/t3k.py                       the CLI (search, build, verify, install-templates)
  presets/standard/                    ~39 recipes, pre-built + verified (mic'd amps, mono+stereo)
  presets/di-reamp/                    8 recipes, pre-built + verified (preamp-only, no cab/mic)
examples/library.json                  source recipes behind presets/standard
examples/di-reamp.json                 source recipes behind presets/di-reamp
```
The `presets/` folders ship real, working `.t3kpreset` files in the repo (not just recipe JSON) so
the skill can install them instantly, offline, without hitting the TONE3000 API at all.
<img width="1026" height="646" alt="Ableton_Live_12_Suite_83P2aJaNke" src="https://github.com/user-attachments/assets/ce352932-c5ae-4f86-a00f-6eb287087379" />


## Requirements
- **TONE3000 plugin or standalone app** installed and run at least once (creates the preset folder).
- **Python 3.8+** on the PATH. No packages — standard library only.
- **Authentication**: needed only for searching the live catalog or building *new* (non-template) presets.
  Authenticate via official TONE3000 OAuth 2.0 PKCE (`python scripts/t3k.py login`) or set an API Secret Key
  via `T3K_SECRET_KEY`. Bundled preset templates install and verify 100% offline without credentials.

## Install the skill
**Claude.ai / Claude Desktop / Cowork:** zip the `skill/tone3000-preset-builder` folder and upload
it under *Settings -> Skills* (or drop the folder into your skills directory).
**Claude Code:** copy `skill/tone3000-preset-builder` into `.claude/skills/` in your project (or
`~/.claude/skills/` for all projects).

Then just ask, e.g.: *"Build me a Foo Fighters Everlong chorus tone in TONE3000, stereo."* Claude
will offer to install the bundled template library first, find your preset folder, ask what your
rig is (monitors vs real amp vs real power amp/cabs) if it doesn't know, search tone3000.com for
the captures, build, verify, and write the files. Reopen the preset browser in TONE3000 to see them.

## Use the CLI directly
```bash
cd skill/tone3000-preset-builder
python scripts/t3k.py login                                # authenticate via official OAuth 2.0 PKCE
python scripts/t3k.py whoami                               # show authenticated user info
python scripts/t3k.py presets-dir                          # where presets go on this machine
python scripts/t3k.py install-templates --category all     # drop in every bundled preset, offline
python scripts/t3k.py install-templates --category di-reamp
python scripts/t3k.py search "tube screamer" --gear pedal
python scripts/t3k.py tone 86314                            # models, tags, description
python scripts/t3k.py build ../../examples/library.json --copy-to ./out
python scripts/t3k.py verify "%APPDATA%\TONE3000\Presets\<file>.t3kpreset"
python scripts/t3k.py list
```
Recipe format, gain maths and the binary format: `references/preset-format.md`.
DI/reamp rig rules (who it's for, what "no cab, ever" means): `references/di-reamp-mode.md`.

## Authentication

TONE3000 provides an official OAuth 2.0 and API key service at [https://www.tone3000.com/api#auth](https://www.tone3000.com/api#auth).
Generate your credentials under [Settings -> API Keys](https://www.tone3000.com/settings).

### Option 1: Official OAuth 2.0 PKCE Login (Recommended)
1. In [TONE3000 Settings](https://www.tone3000.com/settings), copy your **Publishable Key** (`t3k_pub_...`). Ensure your registered Redirect URI includes `http://localhost:8080/callback`.
2. Run the login command and choose option `[2]` (or pass `--client-id`):
```bash
python scripts/t3k.py login
```
3. Your browser will open to the TONE3000 authorization screen. Once approved, it redirects back to localhost and securely stores your access and refresh tokens locally (`%APPDATA%\TONE3000\auth.json` on Windows, `~/.config/TONE3000/auth.json` on Linux, `~/Library/Application Support/TONE3000/auth.json` on macOS). Expired tokens are refreshed automatically.

*For headless servers or environments without a desktop browser, pass `--no-browser` to paste the authorization URL and callback code manually.*

### Option 2: Secret Key (Fastest Setup)
1. In [TONE3000 Settings](https://www.tone3000.com/settings), generate and copy your **Secret Key** (`t3k_cs_...`).
2. Save it directly via the CLI:
```bash
python scripts/t3k.py login --key t3k_cs_YOUR_SECRET_KEY
```
Or set it as an environment variable in your terminal session:
```bash
# Windows (PowerShell)
$env:T3K_SECRET_KEY="t3k_cs_..."

# Windows (Command Prompt)
set T3K_SECRET_KEY=t3k_cs_...

# macOS / Linux
export T3K_SECRET_KEY=t3k_cs_...
```

### How Claude automates this for you
When using the Claude skill:
- Claude automatically checks your login status with `whoami`.
- If you request a tone that matches an existing bundled template (e.g. Slash, Everlong, Hendrix, Master of Puppets, etc.), Claude installs it **100% offline** without needing any credentials.
- If you request a new live search, Claude will check your connection. You can paste your Secret Key in the conversation, and Claude will automatically configure it for you.

## Limits worth knowing
- NAM captures static gear only: no delay, chorus, phaser, wah, tremolo. Add those in your DAW.
- Custom (non-template) presets reference model URLs rather than embedding audio; TONE3000
  downloads each capture on first load (a few hundred KB each), so the first open needs internet.
  The bundled `presets/` templates work exactly the same way -- installing them is instant and
  offline, but TONE3000 still fetches the actual model weights the first time each is loaded.
- The plugin caches the loaded chain -- reopen the preset browser to see new files.
- Never edit your own presets with anything but TONE3000; the builder only creates new files.

## Credits
This project would not exist without [TONE3000](https://www.tone3000.com) and its open-source
plugin, [tone-3000/tone3000-plugin](https://github.com/tone-3000/tone3000-plugin). The
`.t3kpreset` binary format used by every builder and template in this repo was worked out by
reading that plugin's source (`PresetManager.cpp` and the JUCE `ValueTree` serialisation it
relies on) -- none of it is guessed. All credit for the plugin itself, and for every NAM capture
referenced by a preset here, goes to TONE3000 and the individual creators on tone3000.com; every
preset keeps the creator's name and a link back to their capture.

This repo (recipes, the CLI, the Claude skill, and the bundled preset templates) is built with
Claude and is not affiliated with or endorsed by TONE3000. MIT licence.
