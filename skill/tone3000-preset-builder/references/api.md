# TONE3000 data access (what the script does, for when you need to go off-piste)

TONE3000's site and plugin sit on a Supabase backend at `https://api.tone3000.com` (PostgREST).
Public tones are readable with the site's **public anon key** (a JWT, `role: anon`). The script
bundles it (`DEFAULT_KEY`) and honours `T3K_API_KEY` to override. Headers on every request:
`apikey: <key>` and `Authorization: Bearer <key>`.

The separately documented OAuth API at `www.tone3000.com/api/v1/...` needs a user login and is
**not** used here.

## Search (the RPC the website itself uses)
`POST /rest/v1/rpc/search_tones_a2`
```json
{"query_term":"jcm800","page_number":1,"page_size":10,"order_by":"trending",
 "tag_names":null,"make_names":null,"gear_filters":["amp-cab"],"is_calibrated":false,
 "size_filters":null,"usernames":null,"architecture_filter":"2","verified_only":false}
```
`order_by`: trending | best-match | newest | downloads-all-time. `gear_filters` values:
amp, amp-cab, cab, pedal, outboard, space, experimental. Returns id, title, gear, platform
(nam|ir), tags[], makes[], downloads_count, favorites_count, username, model_name.

## Tables (PostgREST; `?select=` and `eq.` filters)
- `tones?id=eq.ID&select=*,tone_tags(tags(id,name)),tone_makes(makes(id,name))`
- `users?id=eq.UUID&select=id,username,display_name,is_verified,avatar_url`
- `models?tone_id=eq.ID&select=id,name,model_url,size,architecture_version,...&order=id.asc`
  (avoid `select=*` — `model_json` holds the full weights, hundreds of KB per row)

`model_url` is a public storage URL, e.g.
`https://api.tone3000.com/storage/v1/object/public/models/xm25r2p1qqq.nam` (IRs end `.wav`).
No auth needed to download it; the plugin fetches it itself on first load.

## What the plugin needs per block (from the open-source code)
`toneJson` must contain a `models[]` array whose entries have `id`, `name`, `model_url`, and
`activeModelId` must equal one of those ids — that is the only load-bearing part; the rest is UI
metadata. `ProcessorHistory.cpp::queueActiveModelLoad` downloads `model_url` when the bytes are
not embedded. Metadata refresh never replaces `models[]`, so a bad URL is a broken block forever.

## Failure modes
- 401 → key rotated: open tone3000.com/search in a browser → DevTools → Network → any
  `api.tone3000.com` request → Request Headers → copy `apikey` → `set T3K_API_KEY=...`.
- Tone found by search but `models` empty → private/deleted; pick another.
- 300 Multiple Choices → ambiguous embed; query the table separately (the script already does).
