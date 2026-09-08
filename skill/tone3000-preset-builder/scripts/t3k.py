#!/usr/bin/env python3
"""
t3k.py Ã¢â‚¬â€ TONE3000 preset builder CLI (stdlib only, Python 3.8+).

Builds real .t3kpreset files for the free TONE3000 NAM plugin from a JSON
"recipe" of TONE3000 tone IDs, using the plugin's own on-disk format (JUCE
ValueTree binary stream, magic "T3KB") Ã¢â‚¬â€ verified against the open-source
plugin: https://github.com/tone-3000/tone3000-plugin

Commands
  presets-dir                     print the user preset folder for this OS (and whether it exists)
  search TERM [--gear G] [--n N]  search TONE3000 (gear: amp, amp-cab, cab, pedal, outboard, space, experimental)
  tone ID                         show a tone + all its models (pick a model name/regex from here)
  build RECIPE.json [--out DIR] [--copy-to DIR] [--mono-only|--stereo-only]
  verify FILE.t3kpreset           parse a preset back and check every block resolves a model_url
  list [--dir DIR]                list presets in the preset folder (name + block count)

Auth: the public "anon" API key. Set T3K_API_KEY to override the bundled one
(see README.md if searches start returning 401).
"""
import argparse, json, os, platform, re, struct, sys, uuid
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import urllib.request, urllib.error, urllib.parse

API = "https://api.tone3000.com/rest/v1"
DEFAULT_KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
               "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd6eWJpdW9weGtkeGJ5dG5vamRzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzgwODIxNjUsImV4cCI6MjA1MzY1ODE2NX0."
               "Gq66BJXjtLsqP2nAGXm9Xb9PAjoeZalWUj66K4nmVSU")
KEY = os.environ.get("T3K_API_KEY", DEFAULT_KEY)
GEARS = ["amp", "amp-cab", "cab", "pedal", "outboard", "space", "experimental"]

# ----------------------------------------------------------------------------
# HTTP
# ----------------------------------------------------------------------------
def _req(url, body=None):
    hdr = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Accept": "application/json"}
    data = None
    if body is not None:
        hdr["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=hdr), timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="replace")[:300]
        if e.code in (401, 403):
            msg += "\n  -> API key rejected. Set T3K_API_KEY (see README: 'Getting the API key')."
        sys.exit(f"HTTP {e.code} for {url}\n  {msg}")

def get(path): return _req(API + "/" + path)

def search(term, gear=None, n=10, sort="trending", architecture="2"):
    body = {"query_term": term or "", "page_number": 1, "page_size": n, "order_by": sort,
            "tag_names": None, "make_names": None, "gear_filters": [gear] if gear else None, "is_calibrated": False,
            "size_filters": None, "usernames": None, "architecture_filter": architecture, "verified_only": False}
    return _req(API + "/rpc/search_tones_a2", body) or []

_cache = {}
def tone_bundle(tone_id):
    """tone row (+tags/makes), owner, models Ã¢â‚¬â€ everything a block needs."""
    if tone_id in _cache: return _cache[tone_id]
    t = get(f"tones?id=eq.{tone_id}&select=*,tone_tags(tags(id,name)),tone_makes(makes(id,name))")
    if not t: sys.exit(f"tone {tone_id} not found (private, deleted, or wrong id)")
    t = t[0]
    u = (get(f"users?id=eq.{t['user_id']}&select=id,username,display_name,is_verified,avatar_url") or [{}])[0]
    ms = get(f"models?tone_id=eq.{tone_id}&select=id,tone_id,user_id,created_at,updated_at,name,model_url,size,architecture_version&order=id.asc")
    if not ms: sys.exit(f"tone {tone_id} ('{t['title']}') has no downloadable models")
    _cache[tone_id] = (t, u, ms)
    return _cache[tone_id]

def pick_model(models, pattern):
    if pattern:
        for m in models:
            if re.search(pattern, m["name"], re.I): return m
        names = "\n    ".join(m["name"] for m in models)
        sys.exit(f"model pattern {pattern!r} matched nothing. Available:\n    {names}")
    return models[0]

def tone_json(t, u, ms):
    """The toneJson blob the plugin stores per block: Tone + models[] (with model_url)."""
    return {
        "id": t["id"], "user_id": t["user_id"], "title": t["title"], "description": t.get("description"),
        "created_at": t["created_at"], "updated_at": t["updated_at"], "published_at": t.get("published_at"),
        "gear": t["gear"], "format": t["platform"], "images": t.get("images") or [], "is_public": True,
        "links": t.get("links") or [], "models_count": len(ms), "favorites_count": 0, "downloads_count": 0,
        "license": t.get("license"), "sizes": None, "a1_models_count": 0, "a2_models_count": len(ms),
        "irs_count": len(ms) if t["platform"] == "ir" else 0, "custom_models_count": 0, "is_favorite": False,
        "url": f"https://www.tone3000.com/tones/{t['id']}",
        "user": {"id": u.get("id"), "username": u.get("username"), "display_name": u.get("display_name"),
                 "is_verified": u.get("is_verified", False), "avatar_url": u.get("avatar_url"),
                 "url": f"https://www.tone3000.com/{u.get('username')}"},
        "makes": [{"id": x["makes"]["id"], "name": x["makes"]["name"]} for x in t.get("tone_makes") or [] if x.get("makes")],
        "tags": [{"id": x["tags"]["id"], "name": x["tags"]["name"]} for x in t.get("tone_tags") or [] if x.get("tags")],
        "models": ms,
    }

# ----------------------------------------------------------------------------
# JUCE ValueTree binary writer (juce_ValueTree.cpp / juce_Variant.cpp / OutputStream)
# ----------------------------------------------------------------------------
def cint(v):
    un, out = abs(v), bytearray()
    while un: out.append(un & 0xFF); un >>= 8
    return bytes([len(out) | (0x80 if v < 0 else 0)]) + bytes(out)
def jstr(s): return s.encode("utf-8") + b"\0"
def v_int(v): return cint(5) + b"\x01" + struct.pack("<i", v)
def v_dbl(v): return cint(9) + b"\x04" + struct.pack("<d", v)
def v_bool(v): return cint(1) + (b"\x02" if v else b"\x03")
def v_str(s):
    u = s.encode("utf-8") + b"\0"
    return cint(len(u) + 1) + b"\x05" + u
def node(type_name, props, children):
    out = jstr(type_name) + cint(len(props))
    for name, val in props:
        out += jstr(name)
        if isinstance(val, bool): out += v_bool(val)
        elif isinstance(val, int): out += v_int(val)
        elif isinstance(val, float): out += v_dbl(val)
        else: out += v_str(str(val))
    out += cint(len(children))
    for c in children: out += c
    return out

# ----------------------------------------------------------------------------
# Reader (for verify)
# ----------------------------------------------------------------------------
class Reader:
    def __init__(self, b): self.b, self.i = b, 0
    def byte(self): v = self.b[self.i]; self.i += 1; return v
    def cint(self):
        sb = self.byte()
        if sb == 0: return 0
        n = sb & 0x7F; v = int.from_bytes(self.b[self.i:self.i+n], "little"); self.i += n
        return -v if sb & 0x80 else v
    def jstr(self):
        j = self.b.index(b"\0", self.i); s = self.b[self.i:j].decode("utf-8"); self.i = j + 1; return s
    def var(self):
        n = self.cint()
        if n == 0: return None
        m = self.byte(); payload = self.b[self.i:self.i+n-1]; self.i += n - 1
        if m == 1: return struct.unpack("<i", payload)[0]
        if m == 2: return True
        if m == 3: return False
        if m == 4: return struct.unpack("<d", payload)[0]
        if m == 5: return payload.rstrip(b"\0").decode("utf-8")
        if m == 6: return struct.unpack("<q", payload)[0]
        return f"<binary {len(payload)} bytes>"
    def node(self):
        t = self.jstr(); props = {}
        for _ in range(self.cint()):
            k = self.jstr(); props[k] = self.var()
        kids = [self.node() for _ in range(self.cint())]
        return {"type": t, "props": props, "children": kids}

# ----------------------------------------------------------------------------
# Preset assembly
# ----------------------------------------------------------------------------
LEVEL = {  # outputGain normalized: 0.5 = 0 dB, each 0.1 = 4.8 dB. Cab IRs get +7.7 dB to offset the plugin's -18 dB short-IR pad.
    "cab": 0.66,
}
DEFAULT_MIX = {"space": 0.3}
DEFAULT_PARAMS = {  # denormalized units, same as the plugin's own Params block
    "outputLevel": 0.5, "inputLevel": 0.5, "toneBass": 5.0, "toneMid": 5.0, "toneTreble": 5.5, "toneEqEnabled": 1.0,
    "gateThreshold": -80.0, "gateEnabled": 1.0, "chainPanLeft": 0.0, "chainPanRight": 1.0, "chainPanLinked": 1.0,
    "outputBalance": 0.5, "spreadEnabled": 0.0, "alignEnabled": 0.0,
}

def resolve_block(spec):
    t, u, ms = tone_bundle(int(spec["tone"]))
    m = pick_model(ms, spec.get("model"))
    gear = t["gear"]
    mix = float(spec.get("mix", DEFAULT_MIX.get(gear, 1.0)))
    out = float(spec.get("outGain", LEVEL.get(gear, 0.5)))
    inp = float(spec.get("inGain", 0.5))
    return {"id": uuid.uuid4().hex, "type": "ir" if t["platform"] == "ir" else "nam", "gear": gear,
            "toneId": t["id"], "title": t["title"], "modelId": m["id"], "modelName": m["name"],
            "json": json.dumps(tone_json(t, u, ms), separators=(",", ":"), ensure_ascii=False),
            "mix": mix, "out": out, "in": inp, "enabled": bool(spec.get("enabled", True)),
            "slim": float(spec.get("slimSize", 0.5))}

def block_node(b):
    return node("ChainBlock", [("id", b["id"]), ("type", b["type"]), ("enabled", b["enabled"]), ("normalize", True),
                               ("slimSize", b["slim"]), ("inputGain", b["in"]), ("outputGain", b["out"]), ("mix", b["mix"]),
                               ("toneId", b["toneId"]), ("toneJson", b["json"]), ("activeModelId", b["modelId"])], [])

def preset_bytes(name, left, right, stereo, branch_after_id, params):
    snap = node("ChainSnapshot",
                [("stereoEnabled", stereo), ("branchSide", "left"), ("branchAfterBlockId", branch_after_id or "")],
                [node("ChainBlocks", [], [block_node(b) for b in left]),
                 node("RightChainBlocks", [], [block_node(b) for b in right])])
    p = dict(DEFAULT_PARAMS); p.update(params or {})
    par = node("Params", [], [node("Param", [("id", k), ("value", float(v))], []) for k, v in p.items()])
    return b"T3KB" + node("T3KPreset", [("schemaVersion", 1), ("name", name)], [snap, par])

def build_recipe(r, out_dir, copy_to=None, mono=True, stereo=True):
    written = []
    left = [resolve_block(s) for s in r["chain"]]
    variants = []
    if mono: variants.append((r["name"], left, [], False, None))
    st = r.get("stereo")
    if stereo and st:
        left2 = [resolve_block(s) for s in r["chain"]]
        right = [resolve_block(s) for s in st.get("right", [])]
        bi = st.get("branchAfter")
        bid = left2[int(bi)]["id"] if bi is not None else None
        variants.append((r["name"] + " [Stereo]", left2, right, True, bid))
    for name, L, R, is_st, bid in variants:
        data = preset_bytes(name, L, R, is_st, bid, r.get("params"))
        fname = uuid.uuid4().hex + ".t3kpreset"
        path = os.path.join(out_dir, fname)
        with open(path, "wb") as f: f.write(data)
        written.append(path)
        if copy_to:
            os.makedirs(copy_to, exist_ok=True)
            safe = re.sub(r"[^\w\- \[\]]+", "", name).strip()
            with open(os.path.join(copy_to, safe + ".t3kpreset"), "wb") as f: f.write(data)
        print(f"== {name}  ->  {path}")
        for b in L: print(f"     L [{b['type']}/{b['gear']}] {b['title']} :: {b['modelName']}  (out {b['out']}, mix {b['mix']})")
        for b in R: print(f"     R [{b['type']}/{b['gear']}] {b['title']} :: {b['modelName']}  (out {b['out']}, mix {b['mix']})")
    return written

# ----------------------------------------------------------------------------
# Preset folder detection (mirrors PresetManager.cpp: userApplicationDataDirectory/TONE3000/Presets)
# ----------------------------------------------------------------------------
def presets_dir():
    s = platform.system()
    if s == "Windows":
        base = os.environ.get("APPDATA") or os.path.expanduser(r"~\AppData\Roaming")
    elif s == "Darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "TONE3000", "Presets")

def install_templates(category, out_dir, source_dir=None):
    src_root = source_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "presets")
    src_root = os.path.abspath(src_root)
    cats = ["standard", "di-reamp"] if category == "all" else [category]
    out_dir = out_dir or presets_dir()
    os.makedirs(out_dir, exist_ok=True)
    installed = []
    for cat in cats:
        cat_dir = os.path.join(src_root, cat)
        if not os.path.isdir(cat_dir):
            print(f"(no bundled '{cat}' presets found at {cat_dir})")
            continue
        for fn in sorted(os.listdir(cat_dir)):
            if not fn.endswith(".t3kpreset"):
                continue
            dst = os.path.join(out_dir, fn)
            with open(os.path.join(cat_dir, fn), "rb") as fsrc, open(dst, "wb") as fdst:
                fdst.write(fsrc.read())
            installed.append(dst)
            print(f"installed [{cat}]  {fn}")
    print(f"DONE — {len(installed)} template preset(s) installed to {out_dir}")
    return installed

def verify(path, quiet=False):
    with open(path, "rb") as f: b = f.read()
    if b[:4] != b"T3KB": raise ValueError("bad magic (not a .t3kpreset)")
    root = Reader(b[4:]).node()
    if root["type"] != "T3KPreset": raise ValueError("root is not T3KPreset")
    snap = next(c for c in root["children"] if c["type"] == "ChainSnapshot")
    problems, blocks = [], []
    for lane in snap["children"]:
        for blk in lane["children"]:
            if blk["type"] != "ChainBlock": continue
            p = blk["props"]
            try:
                tj = json.loads(p["toneJson"]); models = tj.get("models") or []
                m = next((x for x in models if x["id"] == p["activeModelId"]), None)
                if not m or not m.get("model_url"): problems.append(f"{tj.get('title')}: activeModelId not in models[]")
                blocks.append((lane["type"], tj.get("title"), m["name"] if m else "?", m["model_url"] if m else "?"))
            except Exception as e:
                problems.append(f"block {p.get('id')}: {e}")
    if not quiet:
        print(f"{root['props'].get('name')}  stereo={snap['props'].get('stereoEnabled')}  branch={snap['props'].get('branchAfterBlockId') or '-'}")
        for lane, title, mname, url in blocks: print(f"  {'L' if lane=='ChainBlocks' else 'R'} {title} :: {mname}\n      {url}")
        for pr in problems: print("  PROBLEM:", pr)
    return root["props"].get("name"), len(blocks), problems

# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("presets-dir")
    s = sub.add_parser("search"); s.add_argument("term"); s.add_argument("--gear", choices=GEARS); s.add_argument("--n", type=int, default=10)
    s.add_argument("--sort", default="trending", choices=["trending", "best-match", "newest", "downloads-all-time"]); s.add_argument("--json", action="store_true")
    t = sub.add_parser("tone"); t.add_argument("id", type=int)
    b = sub.add_parser("build"); b.add_argument("recipe"); b.add_argument("--out"); b.add_argument("--copy-to")
    b.add_argument("--mono-only", action="store_true"); b.add_argument("--stereo-only", action="store_true")
    v = sub.add_parser("verify"); v.add_argument("file")
    l = sub.add_parser("list"); l.add_argument("--dir")
    it = sub.add_parser("install-templates")
    it.add_argument("--category", choices=["standard", "di-reamp", "all"], default="all")
    it.add_argument("--out")
    it.add_argument("--source", help="Folder containing standard/ and di-reamp/ subfolders (default: bundled presets/ next to this script)")
    a = ap.parse_args()

    if a.cmd == "presets-dir":
        d = presets_dir(); print(d); print("exists" if os.path.isdir(d) else "NOT FOUND Ã¢â‚¬â€ is the TONE3000 plugin/app installed and run once?")
    elif a.cmd == "search":
        res = search(a.term, a.gear, a.n, a.sort)
        if a.json: print(json.dumps(res, indent=1)); return
        for r in res:
            print(f"{r['id']:>6}  {r['title']}  [{r.get('gear')}/{r.get('platform')}]  dl={r.get('downloads_count')} fav={r.get('favorites_count')} by {r.get('username')}")
            if r.get("makes"): print(f"        makes: {', '.join(r['makes'])}")
            if r.get("tags"): print(f"        tags:  {', '.join(r['tags'][:10])}")
    elif a.cmd == "tone":
        t, u, ms = tone_bundle(a.id)
        print(f"{t['id']}  {t['title']}  [{t['gear']}/{t['platform']}]  by {u.get('username')}")
        print(f"  makes: {', '.join(x['makes']['name'] for x in t.get('tone_makes') or [])}")
        print(f"  tags:  {', '.join(x['tags']['name'] for x in t.get('tone_tags') or [])}")
        print(f"  desc:  {(t.get('description') or '')[:400].replace(chr(10),' ')}")
        print(f"  models ({len(ms)}):")
        for m in ms: print(f"    {m['id']}  {m['name']}")
    elif a.cmd == "build":
        with open(a.recipe, encoding="utf-8-sig") as f: recipes = json.load(f)
        if isinstance(recipes, dict): recipes = [recipes]
        out = a.out or presets_dir(); os.makedirs(out, exist_ok=True)
        allw = []
        for r in recipes:
            allw += build_recipe(r, out, a.copy_to, mono=not a.stereo_only, stereo=not a.mono_only)
        bad = 0
        for w in allw:
            _, n, probs = verify(w, quiet=True)
            if probs or n == 0: bad += 1; print("VERIFY FAILED:", w, probs)
        print(f"DONE Ã¢â‚¬â€ {len(allw)} preset file(s) written to {out}, {bad} failed verification")
    elif a.cmd == "verify":
        _, n, probs = verify(a.file); print("OK" if n and not probs else "FAILED")
    elif a.cmd == "install-templates":
        install_templates(a.category, a.out, a.source)
    elif a.cmd == "list":
        d = a.dir or presets_dir()
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".t3kpreset"):
                try: name, n, probs = verify(os.path.join(d, fn), quiet=True); print(f"{fn}  {name}  ({n} blocks{', PROBLEMS' if probs else ''})")
                except Exception as e: print(f"{fn}  <unreadable: {e}>")

if __name__ == "__main__":
    main()
