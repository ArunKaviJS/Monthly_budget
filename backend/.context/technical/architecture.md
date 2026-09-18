# backend — technical detail

## Storage (MongoDB)
Database `MONGO_DB` (default `budget`). Collections and indexes (`database._ensure_indexes`, run
once per process):
| Collection | Key fields | Indexes |
|---|---|---|
| users | `_id` int, username, username_lower, email, email_lower, password_hash | unique username_lower, unique email_lower |
| books | `_id`, user_id, name, is_active, created_at | (user_id, is_active) |
| expenses | `_id`, user_id, book_id, raw_text, description, amount (Decimal128), intent, confidence, spent_on (ISO string), created_at, is_manual_override | (user_id, book_id, spent_on) |
| debts | `_id`, user_id, book_id, direction, person, reason, amount, date, status, settled_on | (user_id, book_id, status) |
| budgets | user_id, intent, monthly_limit | unique (user_id, intent) |
| learned_keywords | user_id, keyword, intent, hits | unique (user_id, keyword) |
| counters | `_id` = collection name, seq | — |
Integer ids come from `next_id` (`find_one_and_update $inc`). Dates are stored as ISO strings; money as
Decimal128 and converted with `_dec` / `_d128`. `_month_range` builds string bounds for month filters.
Connection: `MongoClient(serverSelectionTimeoutMS=8000)`; `mongomock://...` URI -> in-memory client.

## Auth internals (`security.py`)
- Password: `hashlib.scrypt` with a random 16-byte salt, stored `scrypt$N$r$p$salt$hash` (base64),
  compared with `hmac.compare_digest`. Params are read from the stored string on verify.
- Unknown-user logins spend equal time via `burn_password_check` (dummy hash computed at import).
- Token: HS256 JWT with `sub`, `iat`, `exp`; secret from `JWT_SECRET` (missing secret is an error).
- `HTTPBearer(auto_error=False)` so the code returns its own 401 message.

## Intent engine (`intent_engine.py` + `intent_config.py`)
Constants: `CONFIDENCE_THRESHOLD 0.35`, `EXACT_KEYWORD_WEIGHT 1.0`, `PHRASE_WEIGHT 1.5`,
`FUZZY_WEIGHT 0.6`, `FUZZY_MIN_RATIO 0.85`, `LEARNED_KEYWORD_WEIGHT 2.0`, `TIE_MARGIN 0.05`,
`PRIORITY_ORDER` (13 intents, `others` excluded), `STOPWORDS`, `AMOUNT_PATTERNS_FOR_CLEANUP`.
Pipeline in `parse_expense`: normalize -> `extract_amount` -> `extract_date` -> `classify` ->
`build_description`. `extract_learnable_tokens` picks words to remember. `_get_today` is a fixed
UTC+5:30 offset (no tz library). Pure functions except learned keywords supplied by `crud`.

## Error handling
`PyMongoError` handler in `main.py` returns 503. Validation errors are Pydantic v2 (422) with the
"Value error, " prefix stripped client-side.

## Testing
`tests/conftest.py` sets `MONGO_URI=mongomock://...` and a test `JWT_SECRET` before importing `app`;
fixtures `fresh_database` (autouse reset), `alice`, `bob`, `anon`, helpers `signup`, `client_for`.
Suites: `test_intent_engine.py` (121 tests), `test_api.py` (38), `test_auth.py` (36), `test_debts.py` (22)
= 217 by function count; the last full run reported 254 passing (parametrized cases expand the count).
Run: `cd backend && pytest`.

## Packaging / deploy
`api/index.py` -> `app.main:app`; `vercel.json` uses `@vercel/python` and a catch-all route.
`requirements.txt` pins fastapi 0.115.12, uvicorn 0.34.2, pydantic 2.11.3, python-dateutil, pymongo
>=4.6,<5, dnspython (for `mongodb+srv`), pyjwt >=2.8,<3, python-dotenv. Dev extras in
`requirements-dev.txt` (pytest, httpx, mongomock). `.vercelignore` excludes tests, venv, data, env files.
`Dockerfile` (python:3.12-slim) exists but Vercel is the deployment path in use.
