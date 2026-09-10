# TONE3000 API & OAuth Integration

TONE3000 provides an official RESTful API and OAuth 2.0 service at `https://www.tone3000.com/api/v1`.
Full official API documentation: [https://www.tone3000.com/api](https://www.tone3000.com/api)

## Authentication

Every API call requires a Bearer token in the `Authorization` header:
```
Authorization: Bearer <token>
```

Authentication is supported via two mechanisms:

### 1. OAuth 2.0 Authorization Flow with PKCE (Recommended)
Used for user-facing and interactive environments.
- **Authorize Endpoint**: `GET https://www.tone3000.com/api/v1/oauth/authorize`
- **Token Endpoint**: `POST https://www.tone3000.com/api/v1/oauth/token`

Flow:
1. Generate a PKCE `code_verifier` (URL-safe random string) and derive `code_challenge` (`base64url(sha256(code_verifier))`).
2. Generate a random `state` for CSRF prevention.
3. Direct the user to authorize:
   ```
   https://www.tone3000.com/api/v1/oauth/authorize?client_id=<YOUR_PUBLISHABLE_KEY>&redirect_uri=<REDIRECT_URI>&response_type=code&code_challenge=<CHALLENGE>&code_challenge_method=S256&state=<STATE>
   ```
4. Handle the redirect at `redirect_uri` (`GET /callback?code=...&state=...`). Verify `state`.
5. Exchange the authorization code for tokens:
   ```http
   POST /api/v1/oauth/token
   Content-Type: application/x-www-form-urlencoded

   grant_type=authorization_code&code=<code>&code_verifier=<verifier>&redirect_uri=<uri>&client_id=<client_id>
   ```
   Response:
   ```json
   {
     "access_token": "...",
     "refresh_token": "...",
     "expires_in": 3600,
     "token_type": "bearer"
   }
   ```
6. **Token Refresh**: When the access token expires, refresh using `grant_type=refresh_token`:
   ```http
   POST /api/v1/oauth/token
   Content-Type: application/x-www-form-urlencoded

   grant_type=refresh_token&refresh_token=<refresh_token>&client_id=<client_id>
   ```

In `t3k.py`, run:
```bash
python scripts/t3k.py login
```
This runs a local callback server (`http://localhost:8080/callback`), opens your browser, completes the exchange, and stores tokens in your OS config folder (`%APPDATA%\TONE3000\auth.json` on Windows, `~/.config/TONE3000/auth.json` on Linux, `~/Library/Application Support/TONE3000/auth.json` on macOS) with automatic refresh.

### 2. Secret Key (Headless / Automation / CI)
Generated under [Settings -> API Keys](https://www.tone3000.com/settings).
Pass the secret key (`t3k_cs_...`) or an access token via environment variable:
```bash
set T3K_SECRET_KEY=t3k_cs_...     # Windows
export T3K_SECRET_KEY=t3k_cs_...   # macOS / Linux
```

---

## Endpoints Used by Preset Builder

### Current User
`GET /api/v1/user`
Returns the authenticated user (`id`, `username`, `display_name`, `avatar_url`, `is_verified`).

### Search Tones
`GET /api/v1/tones/search`
Query parameters:
- `query`: search term (e.g. `jcm800`)
- `gears`: gear type filter (`amp`, `amp-cab`, `pedal`, `cab`, `outboard`, `space`, `experimental`). Underscore-separated for multiple (e.g. `amp_amp-cab`).
- `page`: 1-based page number
- `page_size`: number of results (max 25)
- `sort`: `trending`, `best-match`, `newest`, `oldest`, `downloads-all-time`
- `architecture`: `1`, `2`, or `custom` (preset builder defaults to `2` for modern NAM A2 models)
- `format`: `nam` or `ir`

Returns `PaginatedResponse<Tone[]>`:
```json
{
  "data": [
    {
      "id": 87735,
      "title": "Marshall Jcm800 + V30 1960",
      "gear": "amp-cab",
      "format": "nam",
      "downloads_count": 23771,
      "favorites_count": 346,
      "user": {
        "id": 123,
        "username": "flaviospanker",
        "display_name": "Flavio",
        "avatar_url": "..."
      },
      "makes": [{"id": 1, "name": "Marshall JCM800"}],
      "tags": [{"id": 2, "name": "british crunch"}]
    }
  ],
  "page": 1,
  "page_size": 10,
  "total": 45,
  "total_pages": 5
}
```

### Get Tone
`GET /api/v1/tones/{id}?architecture=2`
Returns full tone details including creator `user`, `makes`, `tags`, `gear`, `format`, `description`.

### List Models for Tone
`GET /api/v1/models?tone_id={id}&page_size=100&architecture=2`
Returns `PaginatedResponse<Model[]>`:
```json
{
  "data": [
    {
      "id": 741409,
      "tone_id": 87735,
      "name": "Jcm800",
      "model_url": "https://www.tone3000.com/api/v1/models/741409/download/...",
      "size": "standard",
      "architecture_version": "2"
    }
  ]
}
```

---

## What the Plugin Needs Per Block

The `.t3kpreset` format contains a JUCE ValueTree with a `ChainBlock` node for each gear item.
Each block contains a `toneJson` string serialization of the tone:
- Must have `models[]` array with `id`, `name`, and `model_url` (from official API).
- `activeModelId` property on `ChainBlock` must match one of the model IDs in `models[]`.
- `ProcessorHistory.cpp::queueActiveModelLoad` downloads `model_url` when loading the preset in TONE3000 (authenticated via the user's active TONE3000 session).
