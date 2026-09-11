# TONE3000 Preset Builder — a Claude skill

Turn *"make me a Slash tone"* into a real, loadable preset for the free **[TONE3000](https://www.tone3000.com)** Neural Amp Modeler (NAM) plugin and standalone app ([GitHub: tone-3000/tone3000-plugin](https://github.com/tone-3000/tone3000-plugin)) — pedal -> amp -> cab -> outboard -> reverb, mono and stereo, or preamp-only DI chains for players reamping into real power amps and cabs.

Presets are written straight into your local TONE3000 preset folder using captures searched live on [tone3000.com](https://www.tone3000.com) or bundled offline templates. The `.t3kpreset` format was reverse-engineered from the plugin's open-source C++ JUCE codebase and is written byte-exact.

> [!IMPORTANT]
> **Free TONE3000 API Key Required**: To use this tool to search the capture catalog and build custom presets, you need a free API key from TONE3000. Keys can be generated in seconds at [tone3000.com/settings](https://www.tone3000.com/settings) (under API Keys). See [🔐 Authentication & API Configuration (OAuth 2.0 PKCE & Secret Key)](#-authentication--api-configuration-oauth-20-pkce--secret-key) below for setup instructions.

## Changelog
- **User Preference & Gear Hierarchy Engine**: Define ranked brand/amp/cab priorities, DI-reamp vs. Full setup monitoring, stereo vs. mono voicing, and auto-sync favorite creators from TONE3000.
- **Official API v1 & OAuth 2.0 Compliance**: Presets and model downloads strictly adhere to official TONE3000 OAuth authentication, creator licensing, and API v1 endpoints.
- **186 Bundled Artist Presets (Mono & Stereo)**: Pre-built, verified presets for all 80 Equipboard artist profiles plus iconic tone variations, installable via `t3k.py install-templates --category artists`.
- **Official TONE3000 API v1 & OAuth 2.0**: Migrated from legacy scraping to official REST API v1 with OAuth 2.0 PKCE browser login and Secret Key support.
- **Offline Artist Rig Memory & Web Search Hybrid**: Added persistent artist hardware database (`t3k.py rig`) with continuous memory growth and Equipboard integration.

<p align="center"><img src="docs/pipeline.svg" alt="How the TONE3000 preset builder pipeline works, from prompt to installed preset" width="680"></p>

---

## ⚡ Quick Start

### 1. Requirements
- Download and install the free **[TONE3000 Plugin & Standalone App](https://www.tone3000.com/plugin)** (macOS / Windows / Linux) and run it once so your presets directory is created.
- **Python 3.8+** on your PATH (standard library only — zero third-party dependencies).

### 2. Get the Presets Instantly (Offline)
You can install **230+ pre-built, verified presets** (artists, standard albums, and DI-reamp packs) with a single command without creating an account or hitting the internet:

```bash
cd skill/tone3000-preset-builder
python scripts/t3k.py install-templates --category all
```

Open TONE3000 in your DAW (Ableton, Logic, Reaper, Pro Tools, FL Studio) or standalone app — your presets are ready to play!

### 3. Use with Claude (Natural Language)
- **Claude.ai / Claude Desktop / Cowork:** Download the upload-ready **[`tone3000-preset-builder.zip`](https://github.com/tlennon-ie/Tone3000-PresetBuilder/raw/main/tone3000-preset-builder.zip)** (or run `python scripts/t3k.py package-skill` from your repo) and upload it in *Settings -> Skills*.
- **Claude Code:** Copy `skill/tone3000-preset-builder` into `.claude/skills/` in your repository or `~/.claude/skills/`.

*(Note: The skill package includes complete offline hardware specs and recipes in `references/artist-rig-memory.json`. When you ask Claude to install presets, `t3k.py install-templates` automatically fetches the verified presets on demand if they aren't already on disk).*

Then simply ask:
> *"Build me a Foo Fighters Everlong chorus tone in TONE3000, stereo."*  
> *"Make me Larry Carlton's Kid Charlemagne solo tone with dual mic cabs."*  
> *"Set up a DI-reamp chain for a Hendrix fuzz face into a Two-Rock without a cab."*

---

## 🎬 See it in action

![TONE3000 Preset Builder in action](assets/example.gif)

<details>
<summary>🔍 <b>Example Flow: Building Presets for Iconic Guitar Solos (Click to expand)</b></summary>

<br>

**User Prompt:**
> *"Build me a mono and stereo preset for the top guitar solos of all time (Steely Dan - Kid Charlemagne, Prince - Purple Rain, Deep Purple - Highway Star, Allman Brothers - Blue Sky, Lynyrd Skynyrd - Free Bird, Chuck Berry - Johnny B. Goode)"*

1. **Rig Research & Memory Check**: Cross-references verified studio gear against the local `artist-rig-memory.json` database and historical rig rundowns (e.g. Prince's Hohner MadCat + Boss DS-1 into a Mesa Mark; Blackmore's 1968 Marshall Major 200W + Rangemaster Treble Booster; Chuck Berry's Gibson GA-200 amp & Chess Studios tape echo).
2. **Live Catalog Resolution**: Queries the official TONE3000 API v1 (`tone3000.com/api/v1`) for the highest-rated, authentic Neural Amp Modeler (NAM) models and IR captures.
3. **Preset Generation & Gain Staging**: Generates byte-exact JUCE `ValueTree` binary `.t3kpreset` files with unity gain staging (+7.7 dB IR pad compensation, calibrated wet/dry reverb mixes).
4. **Stereo Voicing**: Builds complementary stereo pairs — e.g. dual-mic blends (SM57 + MD421 for Larry Carlton), dual-lead players (Duane Allman Left + Dickey Betts Right for *Blue Sky*), or multi-amp stacks (Marshall Major + Super Lead for *Highway Star*).
5. **Instant Local Verification**: Verifies the binary structure and writes directly to your local `%APPDATA%\TONE3000\Presets` folder — ready to play instantly in your DAW.

| Song & Artist | Original Rig | TONE3000 Chain | Stereo Voicing |
| :--- | :--- | :--- | :--- |
| **Prince**<br>*Purple Rain* (1984) | Hohner MadCat Tele → Boss DS-1 → Mesa Boogie Mark → Plate Reverb | **Tone 89559** (Boss DS-1 `CLASSIC`) → **Tone 89805** (Boogie Mark V 1x12 `LEAD`) → **Tone 69103** (LA-2A Tube Compressor) → **Tone 88038** (Alabs Cetus `Plate`, 32% mix) | **Left**: Mark V Lead<br>**Right**: Mark V Rhythm (both pushed by DS-1 for stadium width) |
| **Deep Purple**<br>*Highway Star* (1972)<br>*(Ritchie Blackmore)* | 1968 Strat → Dallas Rangemaster → 1968 Marshall Major 200W cranked dimed → Pulsonic 4x12 | **Tone 87264** (Dallas Rangemaster `SET 5`) → **Tone 51310** (Marshall Major 200 Plexi 1968 `Dimed BAL3`) → **Tone 88038** (Alabs Cetus `Room`, 20% mix) | **Left**: Marshall Major 200W Dimed<br>**Right**: Marshall Super Lead 12,000 Series (both boosted) |
| **The Allman Brothers Band**<br>*Blue Sky* (1972)<br>*(Duane Allman & Dickey Betts)* | 1957/59 Les Pauls → 50W Marshall 1987 Plexis cranked → 4x12 cabs | **Tone 65578** (Marshall JMP-50 Lead 1969 `FAT CAB`) → **Tone 69103** (LA-2A Tube Compressor) → **Tone 88038** (Alabs Cetus `Room`, 22% mix) | **Left**: Duane Allman (1969 JMP-50)<br>**Right**: Dickey Betts (1976 JMP 50W Jumpered) |
| **Lynyrd Skynyrd**<br>*Free Bird* (1973)<br>*(Allen Collins)* | 1964 Gibson Firebird I → 100W Marshall Super Lead Plexi cranked | **Tone 72145** (1968 Marshall Super Lead 12,000 Series `BRI CAB`) → **Tone 69103** (LA-2A Compressor) → **Tone 88038** (Alabs Cetus `Room`, 25% mix) | **Left**: 1968 Marshall Super Lead 12k<br>**Right**: 1969 Marshall JMP Super Lead (multi-tracked wall) |
| **Chuck Berry**<br>*Johnny B. Goode* (1958) | Gibson ES-350T → Gibson GA tube amp / Tweed Bassman → Chess Studios tape slapback | **Tone 60033** (Gibson GA-200 Rhythm King 1960 `BAL CAB`) → **Tone 65088** (Echo Fix EF-X2 Tape Delay, 35% mix) → **Tone 88038** (Alabs Cetus `Room`, 18% mix) | **Left**: Gibson GA-200 Rhythm King<br>**Right**: Eric Clapton's 1950s Bassman 5F6-A |
| **Steely Dan**<br>*Kid Charlemagne* (1976)<br>*(Larry Carlton)* | 1969 ES-335 → 1960 Tweed Deluxe 5E3 → LA-2A → Room | **Tone 54580** (1960 Tweed Deluxe 5E3 `SM57 CAP EDGE`) → **Tone 69103** (LA-2A Classic) → **Tone 88038** (Alabs Cetus `Room`, 22% mix) | **Left**: Shure SM57 Cap Edge<br>**Right**: Sennheiser MD 421 Middle |

<br>

<p align="center">
  <img width="1026" height="646" alt="Ableton Live 12 Suite with TONE3000 presets loaded" src="https://github.com/user-attachments/assets/ce352932-c5ae-4f86-a00f-6eb287087379" />
</p>

</details>

---

## 🎛️ Gear Hierarchy & Personal Tone Preferences

You can define your personal gear hierarchy so Claude and the CLI know exactly what brands, amps, drives, and speakers you prefer, whether you play through a **Full Setup** (studio monitors/FRFR/headphones with cabs) or a **DI-Reamp Setup** (preamp-only into real power amps & physical cabs), and whether you prefer **Stereo** or **Mono**.

Preferences are stored in `%APPDATA%\TONE3000\preferences.json` (or `~/.config/TONE3000/preferences.json` on macOS/Linux), so they persist across git updates and skill reloads.

### 1. Configure in Plain English with Claude (Zero Friction)
Simply tell Claude what you like in the chat:
> *"Claude, my preferred amp brands are Marshall and Mesa Boogie, I like Tube Screamers for boost, and I monitor with studio monitors in stereo."*  
> *"Switch my setup to DI-reamp mode because I run into a real 4x12 guitar cab."*

Claude runs `t3k.py prefs set ...` under the hood and updates your tone profile automatically!

### 2. 30-Second Terminal Questionnaire
Run the interactive wizard from your terminal:
```bash
cd skill/tone3000-preset-builder
python scripts/t3k.py prefs init --interactive
```

### 3. Jump-Start with Style Archetypes
Load pre-configured tone profiles for your favorite style:
```bash
python scripts/t3k.py prefs template modern-high-gain   # 5150, Dual Rectifier, Precision Drive, V30s
python scripts/t3k.py prefs template vintage-blues      # Tweed Deluxe, Twin Reverb, Two-Rock, Klon, Spring
python scripts/t3k.py prefs template british-crunch     # Plexi, JCM800, Treble Booster, Greenbacks
python scripts/t3k.py prefs template 90s-grunge         # Mesa Dual Rectifier, DS-1, Big Muff, Rat
python scripts/t3k.py prefs template di-reamp-studio    # Preamp-only DI chains, zero cabs/reverbs
```

### 4. Auto-Sync Favorite Creators from TONE3000
```bash
python scripts/t3k.py prefs sync
```
Discovers the capture creators you've favorited or downloaded on [tone3000.com](https://www.tone3000.com) (e.g. `@amalgamaudio`, `@flaviospanker`) and prioritizes their captures whenever searching or building tones!

### 5. View Your Active Setup
```bash
python scripts/t3k.py prefs
```

---

## 🛠️ CLI Reference

You can run the builder directly from your terminal:

```bash
cd skill/tone3000-preset-builder

# Preferences & Gear Hierarchy
python scripts/t3k.py prefs                                 # view active hierarchy, monitoring, and voicing
python scripts/t3k.py prefs init --interactive              # run guided 30-second setup questionnaire
python scripts/t3k.py prefs set --brands "Marshall,Mesa"    # rank preferred brands in priority order
python scripts/t3k.py prefs set --monitoring di-reamp       # switch to preamp-only DI mode (no cabs/reverbs)
python scripts/t3k.py prefs set --monitoring frfr           # switch to full setup (includes cabs & mics)
python scripts/t3k.py prefs set --voicing mono              # default to mono presets (or stereo/both)
python scripts/t3k.py prefs sync                            # auto-discover favorite creators from your account
python scripts/t3k.py prefs template modern-high-gain       # load a genre archetype profile

# Rig Database & Offline Memory
python scripts/t3k.py rig "prince"                          # query Prince hardware stack & TONE3000 IDs
python scripts/t3k.py rig list                              # list all 80+ artists in offline memory

# Install Bundled Templates (100% Offline)
python scripts/t3k.py install-templates --category all      # drop in every preset (artists, standard, di-reamp)
python scripts/t3k.py install-templates --category artists  # drop in all 186 pre-built artist presets
python scripts/t3k.py install-templates --category di-reamp # drop in preamp-only DI presets

# Live Search & Inspection (requires login)
python scripts/t3k.py search "tube screamer" --gear pedal   # search TONE3000 catalog (boosts preferred creators/brands)
python scripts/t3k.py tone 86314                            # inspect tone details, models, tags, and description

# Build & Verify Presets
python scripts/t3k.py build ../../examples/artist-library.json --named
python scripts/t3k.py verify "%APPDATA%\TONE3000\Presets\<preset>.t3kpreset"
python scripts/t3k.py list                                  # list all presets in your local TONE3000 folder
```

---

## 📚 Deep Dive & Documentation

<details>
<summary>📁 <b>What's in here (Repository & File Structure)</b></summary>

<br>

```
skill/tone3000-preset-builder/         the Claude skill & core engine
  SKILL.md                             the agentic workflow Claude follows
  references/                          chain grammar, gear map, artist rig memory, DI-reamp rules, API, binary format
    artist-rig-memory.json             offline memory database (80+ iconic artists covering Equipboard pages 1-5)
    artist-rig-library.md              searchable rig library & hardware reference
    api.md                             official REST API v1 & OAuth 2.0 PKCE documentation
    preset-format.md                   recipe schema, JUCE ValueTree binary format, gain staging maths
    di-reamp-mode.md                   preamp-only guidelines for real power amps and physical cabs
  scripts/t3k.py                       the unified CLI (search, build, verify, rig, auth, install-templates)
  presets/standard/                    ~39 recipes, pre-built + verified (mic'd amps, mono+stereo)
  presets/di-reamp/                    8 recipes, pre-built + verified (preamp-only, no cab/mic)
  presets/artists/                     186 presets, pre-built + verified (80+ artists, mono+stereo)
examples/                              source recipes (library.json, artist-library.json, rolling-stone-top-solos.json)
```

The `presets/` folders ship real, working `.t3kpreset` files in the repo (not just recipe JSON) so
the skill can install them instantly, offline, without hitting the TONE3000 API at all.

</details>

<details>
<summary>🧠 <b>Offline Artist Rig Memory (Equipboard Stacks & Continuous Learning)</b></summary>

<br>

For users running locally without internet access, the repo includes a **persistent rig mapping memory** seeded from historical gear breakdowns and [Equipboard's Top Guitarists (Pages 1–5)](https://equipboard.com/role/guitarists):
- **80+ pre-mapped artist rig profiles**: Hendrix, Page, Gilmour, EVH, Slash, Prince, SRV, Clapton, Cobain, Homme, Kevin Parker, Bellamy, Alex Turner, Iommi, Brian May, Hetfield, Frusciante, Knopfler, Morello, Mayer, Santana, Beck, Moore, Rhoads, Dimebag, Tim Henson, Tosin Abasi, Jonny Greenwood, Noel Gallagher, Rivers Cuomo, Stephen Carpenter, Jim Root, St. Vincent, Gary Clark Jr., and more.
- **Full hardware specifications**: Exact guitars, pickups, overdrive/fuzz pedals, amp heads, cabinets, speakers, outboard compression, and reverb types.
- **Pre-mapped TONE3000 captures**: Tested Tone IDs and model regexes ready to build without an active connection.
- **Continuously growing**: When new rigs or solos are researched, they can be saved back to memory:
  ```bash
  python scripts/t3k.py rig --add new_profile.json
  ```

</details>

<a id="-authentication--api-configuration-oauth-20-pkce--secret-key"></a>
<a id="authentication"></a>
<details id="authentication">
<summary>🔐 <b>Authentication & API Configuration (OAuth 2.0 PKCE & Secret Key)</b></summary>

<br>

TONE3000 provides an official OAuth 2.0 and API key service at [https://www.tone3000.com/api#auth](https://www.tone3000.com/api#auth). Generate credentials under [Settings -> API Keys](https://www.tone3000.com/settings).

### Option 1: Official OAuth 2.0 PKCE Login (Recommended)
1. In [TONE3000 Settings](https://www.tone3000.com/settings), copy your **Publishable Key** (`t3k_pub_...`). Ensure your registered Redirect URI includes `http://localhost:8080/callback`.
2. Run the login command and choose option `[2]` (or pass `--client-id`):
   ```bash
   python scripts/t3k.py login
   ```
3. Your browser opens to the TONE3000 authorization screen. Once approved, it redirects to localhost and securely stores access and refresh tokens locally (`%APPDATA%\TONE3000\auth.json` on Windows, `~/.config/TONE3000/auth.json` on Linux, `~/Library/Application Support/TONE3000/auth.json` on macOS). Expired tokens are refreshed automatically.

*For headless servers or environments without a desktop browser, pass `--no-browser` to paste the authorization URL and callback code manually.*

### Option 2: Secret Key (Fastest Setup)
1. In [TONE3000 Settings](https://www.tone3000.com/settings), generate and copy your **Secret Key** (`t3k_cs_...`).
2. Save it directly via the CLI:
   ```bash
   python scripts/t3k.py login --key t3k_cs_YOUR_SECRET_KEY
   ```
   Or set it as an environment variable in your terminal session (`export T3K_SECRET_KEY=t3k_cs_...` or `$env:T3K_SECRET_KEY="t3k_cs_..."`).

<details>
<summary>🤖 <b>How Claude automates this for you</b></summary>

<br>

When using the Claude skill:
- Claude automatically checks your login status with `whoami`.
- If you request a tone that matches an existing bundled template (e.g. Slash, Everlong, Hendrix, Master of Puppets, etc.), Claude installs it **100% offline** without needing any credentials.
- If you request a new live search, Claude checks your connection. You can paste your Secret Key in the conversation, and Claude will automatically configure it for you.

</details>

</details>

<details>
<summary>⚠️ <b>Limits worth knowing</b></summary>

<br>

- **Static Gear Modeling**: NAM models capture static gear only (preamps, power amps, drive pedals, compressors, EQs, and IR cabs): no dynamic time-based effects like chorus, phaser, flanger, tremolo, or delay. Add those in your DAW track after TONE3000.
- **Model Weight Downloads**: Custom (non-template) presets reference model URLs rather than embedding multi-megabyte audio files. TONE3000 automatically downloads each capture on first load (a few hundred KB each), so the first time you open a newly created preset requires an internet connection. The bundled `presets/` templates work the same way — installing is instant and offline, and TONE3000 caches model weights on first play.
- **Cache Refresh**: The TONE3000 plugin and standalone app cache the loaded preset list — reopen the preset browser to see newly installed files.
- **Preset Editing**: Never manually edit binary `.t3kpreset` files with a text editor; use the CLI builder or edit within TONE3000 directly.

</details>

---

## Credits & Links

- **TONE3000 Plugin & Standalone App**: Download the free app and plugin at **[tone3000.com/plugin](https://www.tone3000.com/plugin)**.
- **Official Open-Source Plugin Repository**: **[tone-3000/tone3000-plugin on GitHub](https://github.com/tone-3000/tone3000-plugin)**.
- **Official TONE3000 Platform & Catalog**: **[tone3000.com](https://www.tone3000.com)**.
- **Official API Documentation**: **[tone3000.com/api](https://www.tone3000.com/api)**.

The `.t3kpreset` binary format used by every builder and template in this repo was worked out by reading the plugin's source (`PresetManager.cpp` and JUCE `ValueTree` serialisation) — none of it is guessed. All credit for the plugin itself, and for every NAM capture referenced by a preset here, goes to TONE3000 and the individual creators on tone3000.com; every preset keeps the creator's name and a link back to their capture.

*This repository (recipes, the CLI, the Claude skill, and the bundled preset templates) is built with Claude and is not affiliated with or endorsed by TONE3000. Released under the MIT licence.*
