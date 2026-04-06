# HAR Parse Rules

> Referenced by: `agents/har-parser.md`
> Purpose: Filtering, deduplication, and repo-matching rules for the `har-parser` agent.

---

## 1. Keep Rules (Keep only these)

An entry is retained only if ALL of the following conditions are true:

1. **Response Content-Type contains `application/json`**
   - Check the response `Content-Type` header first.
   - If absent, fall back to the HAR `content.mimeType` field.
   - Accept partial matches: `application/json`, `application/json;charset=utf-8`, etc.

2. **Not a static resource** (see Drop Rules §2 below)

3. **Not a WebSocket upgrade** (see Drop Rules §3 below)

4. **Not a noise URL** (see Drop Rules §4 below)

Practical note: XHR and Fetch requests with JSON responses are what you want. If you are unsure whether an entry is an API call, check: does it return `application/json`? If yes, keep it.

---

## 2. Drop Rules — Static Resources

Drop any entry whose request URL path ends with one of the following file extensions (case-insensitive):

```
.js   .css  .png  .jpg  .jpeg  .gif  .svg  .ico
.woff .woff2 .ttf  .map
```

Check the **path component only** (ignore query string when matching extensions).

Example paths to drop:
- `/static/main.bundle.js`
- `/assets/logo.png`
- `/fonts/roboto.woff2`
- `/dist/vendor.js.map`

---

## 3. Drop Rules — WebSocket Upgrades

Drop any entry where `response.status == 101`.

HTTP 101 Switching Protocols is always a WebSocket or SSE upgrade — never an API response to test.

---

## 4. Drop Rules — Noise URL Patterns

Drop any entry whose request URL path contains any of the following substrings (case-insensitive, substring match on the full path):

| Pattern | Reason |
|---------|--------|
| `hot-update` | Webpack HMR update files |
| `sockjs` | SockJS WebSocket handshake |
| `__webpack` | Webpack internal resources |
| `source-map` | Source map requests |

Example paths to drop:
- `/static/main.8f3c2.hot-update.json`
- `/sockjs-node/info`
- `/__webpack_hmr`

---

## 5. Deduplication Strategy

Apply deduplication **after** filtering. Process entries in chronological order (HAR order). First occurrence wins.

### 5.1 Exact Duplicate — Merge (Keep First)

Two entries are exact duplicates if all four of the following match:
- `request.method`
- `request.path` (URL path, no query string)
- `response.status`
- `request.body` (JSON body, serialized with sorted keys; `null` if absent)

**Action**: Keep the first occurrence, discard all subsequent duplicates.

### 5.2 Same Path, Different Params — Keep All as Parameterized Data

If two entries share the same `method + path` but differ in request body or query params, treat them as **different test cases** (parameterized variants).

**Action**: Keep both. The case-writer agent will generate `@pytest.mark.parametrize` or separate test methods from these variants.

Example:
```
POST /dassets/v1/datamap/query  body={"page":1,"size":10}   → keep
POST /dassets/v1/datamap/query  body={"page":2,"size":10}   → keep (different page)
```

### 5.3 Same Path, Different Status Codes — Keep Separately

If two entries share `method + path` but differ in `response.status`, they represent different scenarios (normal + error path).

**Action**: Keep both.

Example:
```
POST /dmetadata/v1/syncTask/add  status=200  → keep (success case)
POST /dmetadata/v1/syncTask/add  status=400  → keep (validation error case)
```

---

## 6. Sensitive Header Stripping

**Before writing** any parsed output, strip the following request headers from all entries:

| Header Name (case-insensitive) | Reason |
|--------------------------------|--------|
| `Cookie` | Session tokens / auth cookies |
| `Authorization` | Bearer tokens, Basic auth |
| `x-auth-token` | Custom auth tokens |

Strip the header entirely from the parsed output — do not replace with a placeholder.

Response headers are not stripped (they rarely contain secrets, and `Set-Cookie` values are needed for auth flow analysis).

---

## 7. URL Prefix → Repo Matching

Match each endpoint's URL path to a source code repository using `repo-profiles.yaml`.

**Algorithm** (first match wins):

```python
for profile in profiles:
    for prefix in profile["url_prefixes"]:
        if path.startswith(prefix):
            return profile["name"], profile["branch"]
return None, None
```

Example:
- Path `/dassets/v1/datamap/recentQuery` → prefix `/dassets/v1/` → repo `dt-center-assets`, branch `release_6.2.x`
- Path `/dmetadata/v1/syncTask/add` → prefix `/dmetadata/v1/` → repo `dt-center-metadata`, branch `release_6.2.x`
- Path `/unknown/v1/foo` → no match → `matched_repo: null`

**Important**: A `null` `matched_repo` means no source code is available for that endpoint. The scenario-analyzer will still generate L1-L2 assertions from HAR data alone, but L3-L5 assertions will be skipped or marked as SPECULATIVE.

---

## 8. Service and Module Extraction

Extract `service` and `module` from the URL path structure:

```
/dassets/v1/datamap/recentQuery
  └── service = "dassets"   (parts[0])
  └── module  = "datamap"   (parts[2])

/dmetadata/v1/syncTask/pageTask
  └── service = "dmetadata"
  └── module  = "syncTask"
```

Rule: `parts = [p for p in path.split("/") if p]`
- `service = parts[0]` if available, else `"unknown"`
- `module  = parts[2]` if available, else `parts[1]` if available, else `"unknown"`

---

## 9. Output: parsed.json Schema

Write results to `.autoflow/parsed.json` with the following structure:

```json
{
  "source_har": "<filename>",
  "parsed_at": "<ISO8601 UTC>",
  "base_url": "http://<host>",
  "endpoints": [
    {
      "id": "ep_001",
      "method": "POST",
      "path": "/dassets/v1/datamap/recentQuery",
      "service": "dassets",
      "module": "datamap",
      "request": {
        "headers": { "<name>": "<value>" },
        "body": {}
      },
      "response": {
        "status": 200,
        "body": {},
        "time_ms": 45
      },
      "matched_repo": "dt-center-assets",
      "matched_branch": "release_6.2.x"
    }
  ],
  "summary": {
    "total_raw": 36,
    "after_filter": 29,
    "after_dedup": 27,
    "services": ["dassets", "dmetadata"],
    "modules": ["datamap", "dataTable", "syncTask"]
  }
}
```

**Notes**:
- `id` format: `ep_001`, `ep_002`, ... (zero-padded, 3 digits)
- `base_url`: scheme + host from the first raw entry's URL
- `headers` in `request`: dict of `{name: value}` pairs, sensitive headers already stripped
- `time_ms`: integer milliseconds from HAR `entry.time`

---

## 10. Post-Parse Action

After writing `parsed.json`, move the source HAR file to the `.trash/` directory:

```
.trash/{YYYYMMDD_HHMMSS}_{original_filename}
```

Example: `.trash/20260406_143022_172.16.115.247.har`

Create `.trash/` if it does not exist. This keeps the working directory clean and prevents accidental re-processing of the same HAR.
