#!/usr/bin/env python3
"""
t3k.py — TONE3000 preset builder CLI (stdlib only, Python 3.8+).

Builds real .t3kpreset files for the free TONE3000 NAM plugin from a JSON
"recipe" of TONE3000 tone IDs, using the plugin's own on-disk format (JUCE
ValueTree binary stream, magic "T3KB") — verified against the open-source
plugin: https://github.com/tone-3000/tone3000-plugin

Commands
  login                           authenticate with TONE3000 via official OAuth 2.0 PKCE flow or API key
  logout                          remove saved local authentication tokens
  whoami                          display currently authenticated TONE3000 user
  presets-dir                     print the user preset folder for this OS (and whether it exists)
  search TERM [--gear G] [--n N]  search TONE3000 (gear: amp, amp-cab, cab, pedal, outboard, space, experimental)
  tone ID                         show a tone + all its models (pick a model name/regex from here)
  build RECIPE.json [--out DIR] [--copy-to DIR] [--mono-only|--stereo-only]
  verify FILE.t3kpreset           parse a preset back and check every block resolves a model_url
  list [--dir DIR]                list presets in the preset folder (name + block count)
  install-templates               install bundled presets to preset folder

Auth:
  Official OAuth 2.0 PKCE flow (python t3k.py login) or direct API key / secret key:
  Set T3K_SECRET_KEY (or T3K_API_KEY) with a secret key (t3k_cs_...) or access token.
  Configure keys and OAuth at https://www.tone3000.com/settings
"""
import argparse, base64, hashlib, json, os, platform, re, secrets, struct, sys, time, uuid, webbrowser
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import urllib.request, urllib.error, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

API_BASE = "https://www.tone3000.com/api/v1"
OAUTH_AUTHORIZE_URL = f"{API_BASE}/oauth/authorize"
OAUTH_TOKEN_URL = f"{API_BASE}/oauth/token"
DEFAULT_REDIRECT_URI = "http://localhost:8080/callback"

GEARS = ["amp", "amp-cab", "cab", "pedal", "outboard", "space", "experimental"]

# ----------------------------------------------------------------------------
# Auth & Token Management
# ----------------------------------------------------------------------------
def auth_file_path():
    custom = os.environ.get("T3K_AUTH_FILE")
    if custom:
        return custom
    return os.path.join(os.path.dirname(presets_dir()), "auth.json")

def load_stored_auth():
    path = auth_file_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_stored_auth(auth_data):
    path = auth_file_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(auth_data, f, indent=2)
    except Exception as e:
        sys.stderr.write(f"Warning: could not save auth tokens to {path}: {e}\n")

def clear_stored_auth():
    path = auth_file_path()
    if os.path.isfile(path):
        try:
            os.remove(path)
            return True
        except Exception:
            pass
    return False

def refresh_access_token(client_id, refresh_token):
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    }).encode("utf-8")
    req = urllib.request.Request(
        OAUTH_TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            auth = load_stored_auth()
            auth["access_token"] = data["access_token"]
            if "refresh_token" in data:
                auth["refresh_token"] = data["refresh_token"]
            expires_in = data.get("expires_in", 3600)
            auth["expires_at"] = time.time() + expires_in
            save_stored_auth(auth)
            return data["access_token"]
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"Failed to refresh access token: {e.code} {e.read().decode('utf-8', errors='replace')}\n")
        return None
    except Exception as e:
        sys.stderr.write(f"Failed to refresh access token: {e}\n")
        return None

def get_active_token():
    # 1. Environment variable override (direct Bearer token or secret key t3k_cs_...)
    for env_var in ("T3K_SECRET_KEY", "T3K_ACCESS_TOKEN", "T3K_API_KEY"):
        token = os.environ.get(env_var)
        if token and token.strip():
            return token.strip()

    # 2. Stored OAuth session or saved API key
    auth = load_stored_auth()
    access_token = auth.get("access_token")
    refresh_token = auth.get("refresh_token")
    client_id = auth.get("client_id")
    expires_at = auth.get("expires_at", float("inf"))

    if access_token:
        # Check if token needs proactive refresh (60s margin)
        if expires_at != float("inf") and time.time() > (expires_at - 60) and refresh_token and client_id:
            new_token = refresh_access_token(client_id, refresh_token)
            if new_token:
                return new_token
        return access_token

    return None

def generate_pkce():
    code_verifier = secrets.token_urlsafe(64)[:64]
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return code_verifier, code_challenge

class OAuthCallbackServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, target_state, target_path):
        super().__init__(server_address, RequestHandlerClass)
        self.target_state = target_state
        self.target_path = target_path
        self.auth_code = None
        self.auth_error = None
        self.timeout = 5.0

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != self.server.target_path:
            self.send_response(404)
            self.end_headers()
            return

        qs = urllib.parse.parse_qs(parsed.query)
        state = qs.get("state", [None])[0]
        code = qs.get("code", [None])[0]
        error = qs.get("error", [None])[0]
        canceled = qs.get("canceled", [None])[0]

        if canceled == "true":
            self.server.auth_error = "Authorization was canceled by the user."
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body style='font-family:sans-serif;text-align:center;padding:40px;background:#111;color:#eee;'>"
                             b"<h2 style='color:#e53935;'>Authorization Canceled</h2><p>You can close this tab and return to your terminal.</p></body></html>")
            return

        if state != self.server.target_state:
            self.server.auth_error = "State mismatch (possible CSRF attack)."
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body style='font-family:sans-serif;text-align:center;padding:40px;background:#111;color:#eee;'>"
                             b"<h2 style='color:#e53935;'>Authentication Error</h2><p>State verification failed.</p></body></html>")
            return

        if error:
            self.server.auth_error = f"Authorization failed: {error}"
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<html><body style='font-family:sans-serif;text-align:center;padding:40px;background:#111;color:#eee;'>"
                             f"<h2 style='color:#e53935;'>Authentication Error</h2><p>{error}</p></body></html>".encode("utf-8"))
            return

        if code:
            self.server.auth_code = code
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body style='font-family:sans-serif;text-align:center;padding:40px;background:#111;color:#eee;'>"
                b"<h2 style='color:#4caf50;'>TONE3000 Authentication Successful</h2>"
                b"<p>You can close this tab and return to your terminal.</p>"
                b"</body></html>"
            )
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        # Silence access logs
        pass

def save_secret_key(key):
    key = key.strip()
    print("Verifying key with TONE3000 API...")
    user = get_current_user(key)
    if not user:
        sys.exit(
            "\nError: Could not authenticate with this Secret Key.\n"
            "Please ensure you copied the full key (starts with t3k_cs_) from https://www.tone3000.com/settings"
        )
    auth_data = {
        "access_token": key,
        "client_id": "direct_secret_key",
        "token_type": "bearer",
        "expires_at": float("inf"),
    }
    save_stored_auth(auth_data)
    uname = user.get("username")
    dname = user.get("display_name")
    print(f"\nSuccessfully authenticated as @{uname}" + (f" ({dname})" if dname else "") + "!")
    print(f"Credentials saved to: {auth_file_path()}")
    return True

def start_oauth_flow(client_id, redirect_uri=None, port=8080, no_browser=False):
    redirect_uri = redirect_uri or os.environ.get("T3K_REDIRECT_URI") or f"http://localhost:{port}/callback"
    parsed_redirect = urllib.parse.urlparse(redirect_uri)
    listen_host = parsed_redirect.hostname or "127.0.0.1"
    listen_port = parsed_redirect.port or port
    target_path = parsed_redirect.path or "/callback"

    code_verifier, code_challenge = generate_pkce()
    state = secrets.token_urlsafe(32)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    authorize_url = f"{OAUTH_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    auth_code = None
    if not no_browser:
        try:
            server = OAuthCallbackServer((listen_host, listen_port), OAuthCallbackHandler, state, target_path)
            print(f"\nOpening browser for TONE3000 OAuth authorization...")
            print(f"If the browser does not open automatically, visit:\n  {authorize_url}\n")
            webbrowser.open(authorize_url)

            print(f"Waiting for authorization callback on {redirect_uri} (timeout in 120s)...")
            start_time = time.time()
            while not server.auth_code and not server.auth_error:
                if time.time() - start_time > 120:
                    sys.exit("Login timed out waiting for browser callback. You can retry with --no-browser.")
                server.handle_request()

            if server.auth_error:
                sys.exit(f"Login failed: {server.auth_error}")
            auth_code = server.auth_code
        except OSError as e:
            print(f"Note: Could not bind local callback listener on {listen_host}:{listen_port} ({e}).")
            print("Falling back to manual code entry.\n")
            no_browser = True

    if no_browser or not auth_code:
        print(f"Visit this URL in your browser to authorize:\n  {authorize_url}\n")
        try:
            user_input = input("Enter the callback URL or authorization code: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            return False

        if "code=" in user_input:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(user_input).query)
            auth_code = qs.get("code", [None])[0]
        else:
            auth_code = user_input

    if not auth_code:
        sys.exit("Error: No authorization code provided.")

    print("Exchanging authorization code for access tokens...")
    token_body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": auth_code,
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
    }).encode("utf-8")

    req = urllib.request.Request(
        OAUTH_TOKEN_URL,
        data=token_body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            tokens = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"Token exchange failed (HTTP {e.code}):\n  {e.read().decode('utf-8', errors='replace')}")

    auth_data = {
        "client_id": client_id,
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
        "expires_at": time.time() + tokens.get("expires_in", 3600),
        "token_type": tokens.get("token_type", "bearer"),
    }
    save_stored_auth(auth_data)
    print(f"Successfully logged in! Tokens saved to {auth_file_path()}")

    # Fetch and display current user
    user = get_current_user(auth_data["access_token"])
    if user:
        uname = user.get("username")
        dname = user.get("display_name")
        print(f"Authenticated as @{uname}" + (f" ({dname})" if dname else ""))
    return True

def login_flow(client_id=None, secret_key=None, redirect_uri=None, port=8080, no_browser=False):
    # Direct argument passed via --key
    if secret_key:
        return save_secret_key(secret_key)

    # Direct argument passed via --client-id
    if client_id:
        return start_oauth_flow(client_id, redirect_uri=redirect_uri, port=port, no_browser=no_browser)

    print("========================================")
    print("       TONE3000 Authentication          ")
    print("========================================")
    print("Keys can be generated at: https://www.tone3000.com/settings (under API Keys)\n")
    print("Select an option:")
    print("  [1] Secret Key (paste t3k_cs_... — fastest setup)")
    print("  [2] OAuth 2.0 PKCE (browser authorization with Publishable Key / client_id)")
    print("  [q] Quit\n")

    try:
        choice = input("Enter your choice [1/2]: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        return False

    if choice in ("q", "quit", "exit"):
        print("Aborted.")
        return False

    if choice == "1":
        try:
            key = input("\nPaste your Secret Key (starts with t3k_cs_): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            return False
        if not key:
            sys.exit("Error: Secret Key cannot be empty.")
        return save_secret_key(key)

    elif choice == "2":
        try:
            cid = input("\nEnter your Publishable Key (client_id from settings): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            return False
        if not cid:
            sys.exit("Error: Publishable Key cannot be empty.")
        return start_oauth_flow(cid, redirect_uri=redirect_uri, port=port, no_browser=no_browser)

    else:
        # Check if user pasted a Secret Key directly into the choice prompt
        if choice.startswith("t3k_cs_"):
            return save_secret_key(choice)
        # Check if user pasted a long client_id directly into the choice prompt
        elif len(choice) > 10:
            return start_oauth_flow(choice, redirect_uri=redirect_uri, port=port, no_browser=no_browser)
        else:
            sys.exit(f"Invalid option '{choice}'. Please enter 1 or 2.")

# ----------------------------------------------------------------------------
# HTTP & API Client
# ----------------------------------------------------------------------------
def _req(url, query_params=None, body=None, token_override=None, retry_auth=True):
    token = token_override or get_active_token()
    if not token:
        sys.exit(
            "Authentication required.\n"
            "  Run `python scripts/t3k.py login` to authenticate with TONE3000,\n"
            "  or set T3K_SECRET_KEY / T3K_ACCESS_TOKEN with your key from https://www.tone3000.com/settings"
        )

    if query_params:
        filtered = {k: v for k, v in query_params.items() if v is not None}
        if filtered:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{urllib.parse.urlencode(filtered)}"

    hdr = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "Tone3000-PresetBuilder/2.0",
    }
    data = None
    if body is not None:
        hdr["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=hdr), timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="replace")[:400]
        # Auto refresh token on 401 if we have stored OAuth credentials
        if e.code == 401 and retry_auth and not token_override:
            stored = load_stored_auth()
            cid = stored.get("client_id")
            rt = stored.get("refresh_token")
            if cid and rt and cid != "direct_secret_key":
                new_token = refresh_access_token(cid, rt)
                if new_token:
                    return _req(url, query_params=None, body=body, token_override=new_token, retry_auth=False)

        if e.code in (401, 403):
            msg += (
                "\n  -> Authentication rejected. Your token may be expired or invalid.\n"
                "     Run `python scripts/t3k.py login` to re-authenticate, or verify your T3K_SECRET_KEY."
            )
        sys.exit(f"HTTP {e.code} for {url}\n  {msg}")

def api_get(path, params=None, token_override=None):
    url = f"{API_BASE}/{path.lstrip('/')}"
    return _req(url, query_params=params, token_override=token_override)

def get_current_user(token=None):
    try:
        return api_get("user", token_override=token)
    except Exception:
        return None

def search(term, gear=None, n=10, sort="trending", architecture="2"):
    all_results = []
    page = 1
    remaining = n
    while remaining > 0:
        page_size = min(remaining, 25)
        params = {
            "query": term or "",
            "page": page,
            "page_size": page_size,
            "sort": sort,
            "gears": gear if gear else None,
            "architecture": architecture,
        }
        res = api_get("tones/search", params)
        batch = res.get("data", []) if isinstance(res, dict) else (res if isinstance(res, list) else [])
        if not batch:
            break
        all_results.extend(batch)
        remaining -= len(batch)
        if len(batch) < page_size:
            break
        page += 1
    return all_results

_cache = {}
def tone_bundle(tone_id):
    """tone row, creator user info, models — everything a block needs."""
    if tone_id in _cache:
        return _cache[tone_id]

    t = api_get(f"tones/{tone_id}", {"architecture": "2"})
    if not t or not isinstance(t, dict):
        sys.exit(f"tone {tone_id} not found (private, deleted, or wrong id)")

    models_res = api_get("models", {"tone_id": tone_id, "page_size": 100, "architecture": "2"})
    ms = models_res.get("data", []) if isinstance(models_res, dict) else (models_res if isinstance(models_res, list) else [])
    if not ms:
        sys.exit(f"tone {tone_id} ('{t.get('title')}') has no downloadable models")

    _cache[tone_id] = (t, ms)
    return _cache[tone_id]

def pick_model(models, pattern):
    if pattern:
        for m in models:
            if re.search(pattern, m["name"], re.I):
                return m
        names = "\n    ".join(m["name"] for m in models)
        sys.exit(f"model pattern {pattern!r} matched nothing. Available:\n    {names}")
    return models[0]

def tone_json(t, ms):
    """The toneJson blob the plugin stores per block: Tone + models[] (with model_url)."""
    u = t.get("user") or {}
    platform_val = t.get("format") or t.get("platform") or "nam"
    return {
        "id": t["id"],
        "user_id": t.get("user_id") or u.get("id"),
        "title": t["title"],
        "description": t.get("description"),
        "created_at": t.get("created_at"),
        "updated_at": t.get("updated_at"),
        "published_at": t.get("published_at"),
        "gear": t.get("gear"),
        "format": platform_val,
        "images": t.get("images") or [],
        "is_public": t.get("is_public", True),
        "links": t.get("links") or [],
        "models_count": len(ms),
        "favorites_count": t.get("favorites_count", 0),
        "downloads_count": t.get("downloads_count", 0),
        "license": t.get("license"),
        "sizes": t.get("sizes"),
        "a1_models_count": t.get("a1_models_count", 0),
        "a2_models_count": t.get("a2_models_count", len(ms) if platform_val == "nam" else 0),
        "irs_count": len(ms) if platform_val == "ir" else 0,
        "custom_models_count": t.get("custom_models_count", 0),
        "is_favorite": t.get("is_favorite", False),
        "url": t.get("url") or f"https://www.tone3000.com/tones/{t['id']}",
        "user": {
            "id": u.get("id"),
            "username": u.get("username"),
            "display_name": u.get("display_name"),
            "is_verified": u.get("is_verified", False),
            "avatar_url": u.get("avatar_url"),
            "url": u.get("url") or f"https://www.tone3000.com/{u.get('username')}",
        },
        "makes": [{"id": x.get("id"), "name": x.get("name")} for x in t.get("makes") or [] if isinstance(x, dict)],
        "tags": [{"id": x.get("id"), "name": x.get("name")} for x in t.get("tags") or [] if isinstance(x, dict)],
        "models": ms,
    }

# ----------------------------------------------------------------------------
# JUCE ValueTree binary writer (juce_ValueTree.cpp / juce_Variant.cpp / OutputStream)
# ----------------------------------------------------------------------------
def cint(v):
    un, out = abs(v), bytearray()
    while un:
        out.append(un & 0xFF)
        un >>= 8
    return bytes([len(out) | (0x80 if v < 0 else 0)]) + bytes(out)

def jstr(s):
    return s.encode("utf-8") + b"\0"

def v_int(v):
    return cint(5) + b"\x01" + struct.pack("<i", v)

def v_dbl(v):
    return cint(9) + b"\x04" + struct.pack("<d", v)

def v_bool(v):
    return cint(1) + (b"\x02" if v else b"\x03")

def v_str(s):
    u = s.encode("utf-8") + b"\0"
    return cint(len(u) + 1) + b"\x05" + u

def node(type_name, props, children):
    out = jstr(type_name) + cint(len(props))
    for name, val in props:
        out += jstr(name)
        if isinstance(val, bool):
            out += v_bool(val)
        elif isinstance(val, int):
            out += v_int(val)
        elif isinstance(val, float):
            out += v_dbl(val)
        else:
            out += v_str(str(val))
    out += cint(len(children))
    for c in children:
        out += c
    return out

# ----------------------------------------------------------------------------
# Reader (for verify)
# ----------------------------------------------------------------------------
class Reader:
    def __init__(self, b):
        self.b, self.i = b, 0
    def byte(self):
        v = self.b[self.i]
        self.i += 1
        return v
    def cint(self):
        sb = self.byte()
        if sb == 0:
            return 0
        n = sb & 0x7F
        v = int.from_bytes(self.b[self.i:self.i+n], "little")
        self.i += n
        return -v if sb & 0x80 else v
    def jstr(self):
        j = self.b.index(b"\0", self.i)
        s = self.b[self.i:j].decode("utf-8")
        self.i = j + 1
        return s
    def var(self):
        n = self.cint()
        if n == 0:
            return None
        m = self.byte()
        payload = self.b[self.i:self.i+n-1]
        self.i += n - 1
        if m == 1:
            return struct.unpack("<i", payload)[0]
        if m == 2:
            return True
        if m == 3:
            return False
        if m == 4:
            return struct.unpack("<d", payload)[0]
        if m == 5:
            return payload.rstrip(b"\0").decode("utf-8")
        if m == 6:
            return struct.unpack("<q", payload)[0]
        return f"<binary {len(payload)} bytes>"
    def node(self):
        t = self.jstr()
        props = {}
        for _ in range(self.cint()):
            k = self.jstr()
            props[k] = self.var()
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
    t, ms = tone_bundle(int(spec["tone"]))
    m = pick_model(ms, spec.get("model"))
    gear = t.get("gear")
    fmt = t.get("format") or t.get("platform") or "nam"
    mix = float(spec.get("mix", DEFAULT_MIX.get(gear, 1.0)))
    out = float(spec.get("outGain", LEVEL.get(gear, 0.5)))
    inp = float(spec.get("inGain", 0.5))
    return {
        "id": uuid.uuid4().hex,
        "type": "ir" if fmt == "ir" else "nam",
        "gear": gear,
        "toneId": t["id"],
        "title": t["title"],
        "modelId": m["id"],
        "modelName": m["name"],
        "json": json.dumps(tone_json(t, ms), separators=(",", ":"), ensure_ascii=False),
        "mix": mix,
        "out": out,
        "in": inp,
        "enabled": bool(spec.get("enabled", True)),
        "slim": float(spec.get("slimSize", 0.5)),
    }

def block_node(b):
    return node(
        "ChainBlock",
        [
            ("id", b["id"]), ("type", b["type"]), ("enabled", b["enabled"]), ("normalize", True),
            ("slimSize", b["slim"]), ("inputGain", b["in"]), ("outputGain", b["out"]), ("mix", b["mix"]),
            ("toneId", b["toneId"]), ("toneJson", b["json"]), ("activeModelId", b["modelId"]),
        ],
        [],
    )

def preset_bytes(name, left, right, stereo, branch_after_id, params):
    snap = node(
        "ChainSnapshot",
        [("stereoEnabled", stereo), ("branchSide", "left"), ("branchAfterBlockId", branch_after_id or "")],
        [node("ChainBlocks", [], [block_node(b) for b in left]),
         node("RightChainBlocks", [], [block_node(b) for b in right])],
    )
    p = dict(DEFAULT_PARAMS)
    p.update(params or {})
    par = node("Params", [], [node("Param", [("id", k), ("value", float(v))], []) for k, v in p.items()])
    return b"T3KB" + node("T3KPreset", [("schemaVersion", 1), ("name", name)], [snap, par])

def build_recipe(r, out_dir, copy_to=None, mono=True, stereo=True):
    written = []
    left = [resolve_block(s) for s in r["chain"]]
    variants = []
    if mono:
        variants.append((r["name"], left, [], False, None))
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
        with open(path, "wb") as f:
            f.write(data)
        written.append(path)
        if copy_to:
            os.makedirs(copy_to, exist_ok=True)
            safe = re.sub(r"[^\w\- \[\]]+", "", name).strip()
            with open(os.path.join(copy_to, safe + ".t3kpreset"), "wb") as f:
                f.write(data)
        print(f"== {name}  ->  {path}")
        for b in L:
            print(f"     L [{b['type']}/{b['gear']}] {b['title']} :: {b['modelName']}  (out {b['out']}, mix {b['mix']})")
        for b in R:
            print(f"     R [{b['type']}/{b['gear']}] {b['title']} :: {b['modelName']}  (out {b['out']}, mix {b['mix']})")
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
    with open(path, "rb") as f:
        b = f.read()
    if b[:4] != b"T3KB":
        raise ValueError("bad magic (not a .t3kpreset)")
    root = Reader(b[4:]).node()
    if root["type"] != "T3KPreset":
        raise ValueError("root is not T3KPreset")
    snap = next(c for c in root["children"] if c["type"] == "ChainSnapshot")
    problems, blocks = [], []
    for lane in snap["children"]:
        for blk in lane["children"]:
            if blk["type"] != "ChainBlock":
                continue
            p = blk["props"]
            try:
                tj = json.loads(p["toneJson"])
                models = tj.get("models") or []
                m = next((x for x in models if x["id"] == p["activeModelId"]), None)
                if not m or not m.get("model_url"):
                    problems.append(f"{tj.get('title')}: activeModelId not in models[]")
                blocks.append((lane["type"], tj.get("title"), m["name"] if m else "?", m["model_url"] if m else "?"))
            except Exception as e:
                problems.append(f"block {p.get('id')}: {e}")
    if not quiet:
        print(f"{root['props'].get('name')}  stereo={snap['props'].get('stereoEnabled')}  branch={snap['props'].get('branchAfterBlockId') or '-'}")
        for lane, title, mname, url in blocks:
            print(f"  {'L' if lane=='ChainBlocks' else 'R'} {title} :: {mname}\n      {url}")
        for pr in problems:
            print("  PROBLEM:", pr)
    return root["props"].get("name"), len(blocks), problems

# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    # Auth commands
    lg = sub.add_parser("login", help="authenticate with TONE3000 via OAuth 2.0 PKCE or Secret Key")
    lg.add_argument("--client-id", help="TONE3000 Publishable Key (client_id)")
    lg.add_argument("--key", "--secret-key", dest="secret_key", help="direct Secret Key (t3k_cs_...) to save")
    lg.add_argument("--port", type=int, default=8080, help="local callback port (default: 8080)")
    lg.add_argument("--redirect-uri", help="override redirect URI (default: http://localhost:8080/callback)")
    lg.add_argument("--no-browser", action="store_true", help="manual code entry for headless/terminal environments")

    sub.add_parser("logout", help="clear locally stored authentication tokens")
    sub.add_parser("whoami", help="show authenticated user information")

    # Preset / Search commands
    sub.add_parser("presets-dir", help="print the user preset folder for this OS")
    s = sub.add_parser("search", help="search TONE3000 catalog")
    s.add_argument("term")
    s.add_argument("--gear", choices=GEARS, help="filter by gear type")
    s.add_argument("--n", type=int, default=10, help="number of results")
    s.add_argument("--sort", default="trending", choices=["trending", "best-match", "newest", "oldest", "downloads-all-time"])
    s.add_argument("--json", action="store_true", help="output raw JSON")

    t = sub.add_parser("tone", help="show tone details and model variants")
    t.add_argument("id", type=int)

    b = sub.add_parser("build", help="build preset files from recipe JSON")
    b.add_argument("recipe")
    b.add_argument("--out", help="destination folder (default: TONE3000 presets folder)")
    b.add_argument("--copy-to", help="optional secondary folder to copy named presets to")
    b.add_argument("--mono-only", action="store_true")
    b.add_argument("--stereo-only", action="store_true")

    v = sub.add_parser("verify", help="verify a .t3kpreset file")
    v.add_argument("file")

    l = sub.add_parser("list", help="list presets in preset folder")
    l.add_argument("--dir", help="directory to list (default: TONE3000 presets folder)")

    it = sub.add_parser("install-templates", help="install bundled presets")
    it.add_argument("--category", choices=["standard", "di-reamp", "all"], default="all")
    it.add_argument("--out")
    it.add_argument("--source", help="folder containing standard/ and di-reamp/ subfolders")

    a = ap.parse_args()

    if a.cmd == "login":
        login_flow(client_id=a.client_id, secret_key=a.secret_key, redirect_uri=a.redirect_uri, port=a.port, no_browser=a.no_browser)
    elif a.cmd == "logout":
        if clear_stored_auth():
            print("Successfully logged out. Stored tokens cleared.")
        else:
            print("No stored tokens found.")
    elif a.cmd == "whoami":
        token = get_active_token()
        if not token:
            print("Not logged in. Run `python scripts/t3k.py login` or set T3K_SECRET_KEY.")
            return
        user = get_current_user(token)
        if user:
            print(f"Username:     @{user.get('username')}")
            if user.get("display_name"):
                print(f"Display Name: {user.get('display_name')}")
            print(f"ID:           {user.get('id')}")
            if user.get("url"):
                print(f"Profile:      {user.get('url')}")
            print(f"Verified:     {user.get('is_verified', False)}")
        else:
            print("Could not retrieve user info (token may be invalid or expired).")
    elif a.cmd == "presets-dir":
        d = presets_dir()
        print(d)
        print("exists" if os.path.isdir(d) else "NOT FOUND — is the TONE3000 plugin/app installed and run once?")
    elif a.cmd == "search":
        res = search(a.term, a.gear, a.n, a.sort)
        if a.json:
            print(json.dumps(res, indent=2))
            return
        if not res:
            print(f"No tones found matching '{a.term}'.")
            return
        for r in res:
            u = r.get("user") or {}
            uname = u.get("username") if isinstance(u, dict) else r.get("username")
            fmt = r.get("format") or r.get("platform") or "nam"
            print(f"{r['id']:>6}  {r['title']}  [{r.get('gear')}/{fmt}]  dl={r.get('downloads_count', 0)} fav={r.get('favorites_count', 0)} by {uname}")
            if r.get("makes"):
                make_names = [m.get("name") if isinstance(m, dict) else str(m) for m in r["makes"]]
                print(f"        makes: {', '.join(make_names)}")
            if r.get("tags"):
                tag_names = [tg.get("name") if isinstance(tg, dict) else str(tg) for tg in r["tags"]]
                print(f"        tags:  {', '.join(tag_names[:10])}")
    elif a.cmd == "tone":
        t, ms = tone_bundle(a.id)
        u = t.get("user") or {}
        uname = u.get("username") if isinstance(u, dict) else t.get("username")
        fmt = t.get("format") or t.get("platform") or "nam"
        print(f"{t['id']}  {t['title']}  [{t.get('gear')}/{fmt}]  by {uname}")
        if t.get("makes"):
            make_names = [m.get("name") if isinstance(m, dict) else str(m) for m in t["makes"]]
            print(f"  makes: {', '.join(make_names)}")
        if t.get("tags"):
            tag_names = [tg.get("name") if isinstance(tg, dict) else str(tg) for tg in t["tags"]]
            print(f"  tags:  {', '.join(tag_names)}")
        if t.get("description"):
            desc = t["description"].replace("\r\n", " ").replace("\n", " ")[:400]
            print(f"  desc:  {desc}")
        print(f"  models ({len(ms)}):")
        for m in ms:
            arch = f" (A{m.get('architecture_version')})" if m.get("architecture_version") else ""
            print(f"    {m['id']}  {m['name']}{arch}")
    elif a.cmd == "build":
        with open(a.recipe, encoding="utf-8-sig") as f:
            recipes = json.load(f)
        if isinstance(recipes, dict):
            recipes = [recipes]
        out = a.out or presets_dir()
        os.makedirs(out, exist_ok=True)
        allw = []
        for r in recipes:
            allw += build_recipe(r, out, a.copy_to, mono=not a.stereo_only, stereo=not a.mono_only)
        bad = 0
        for w in allw:
            _, n, probs = verify(w, quiet=True)
            if probs or n == 0:
                bad += 1
                print("VERIFY FAILED:", w, probs)
        print(f"DONE — {len(allw)} preset file(s) written to {out}, {bad} failed verification")
    elif a.cmd == "verify":
        _, n, probs = verify(a.file)
        print("OK" if n and not probs else "FAILED")
    elif a.cmd == "install-templates":
        install_templates(a.category, a.out, a.source)
    elif a.cmd == "list":
        d = a.dir or presets_dir()
        if not os.path.isdir(d):
            print(f"Presets directory not found: {d}")
            return
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".t3kpreset"):
                try:
                    name, n, probs = verify(os.path.join(d, fn), quiet=True)
                    print(f"{fn}  {name}  ({n} blocks{', PROBLEMS' if probs else ''})")
                except Exception as e:
                    print(f"{fn}  <unreadable: {e}>")

if __name__ == "__main__":
    main()
