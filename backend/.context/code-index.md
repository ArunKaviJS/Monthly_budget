# backend — code-index

## Role
FastAPI JSON service that owns all data. It authenticates users (JWT), stores everything in
MongoDB (Atlas in production, `mongomock` in tests), turns typed expense text into
amount/date/description, and serves summaries, budgets, debts and exports. Deployed as a
single Vercel serverless function; called only by the `mobile` module.

## Files + dependencies
| File | Depends on | Purpose |
|---|---|---|
| `api/index.py` | `app.main` | Vercel entry; re-exports `app` |
| `app/main.py` | routers, `database`, pymongo | Creates FastAPI app (v2.0.0), CORS `*`, `PyMongoError` -> 503, mounts routers, `GET /api/health` |
| `app/database.py` | pymongo, python-dotenv, mongomock | Loads `backend/.env`, `get_db()`, index creation, `next_id()`, `reset_for_tests()` |
| `app/security.py` | pyjwt, hashlib.scrypt | Password hash/verify, JWT create/decode, `get_current_user` dependency |
| `app/schemas.py` | pydantic v2 | All request/response models + validators |
| `app/crud.py` | `database`, `schemas`, `intent_engine`, `intent_config` | Every DB operation; all functions take `user_id` |
| `app/intent_engine.py` | `intent_config`, difflib, dateutil | normalize -> amount -> date -> classify -> description |
| `app/intent_config.py` | — | 14 intents (keywords/phrases), weights, thresholds, stopwords |
| `app/routers/*.py` | `crud`, `schemas`, `security` | HTTP layer (see contract) |
| `tests/` | mongomock, httpx/TestClient | `conftest.py` + `test_api.py`, `test_auth.py`, `test_debts.py`, `test_intent_engine.py` |
| `vercel.json`, `.vercelignore`, `Dockerfile`, `requirements*.txt` | — | Deploy/build config |

## What the code actually does
1. **Startup** – `main.py` builds the app; `database.get_db()` lazily connects on first request
   (`MONGO_URI`, db `MONGO_DB` or `budget`; `mongomock://` URIs use an in-memory client) and
   ensures indexes once.
2. **Sign-up** (`POST /api/auth/signup`) – validates username `^[A-Za-z0-9_.]{3,24}$`, email,
   password 6-128; `crud.create_user` stores `username_lower`/`email_lower` (unique indexes),
   scrypt hash; duplicate -> `DuplicateUser` -> 409. Returns `{token, user}`.
3. **Login** (`POST /api/auth/login`) – `find_user_for_login(identifier)` matches username or
   email case-insensitively; on unknown user still runs `burn_password_check` to equalize timing.
4. **Every protected call** – `get_current_user` reads the Bearer token, `decode_token` -> user id,
   loads the user from Mongo; 401 with `WWW-Authenticate: Bearer` otherwise.
   `POST /api/auth/refresh` returns the user plus a freshly issued token.
5. **Books** – one active book per user. Creating a book makes it active; deleting removes its
   expenses and debts and activates the highest-`_id` remaining book. Book responses include
   `total`, `count`, `pending_debts` computed on read.
6. **Add expense** (`POST /api/expenses`) – requires an active book (else 409). With `raw_text`:
   optional `intent` (must be in `INTENTS`) overrides classification; `crud.create_expense_from_text`
   runs `intent_engine.parse_expense` (amount, date, description), no amount -> `ValueError` -> 422.
   With `amount+intent+description`: manual insert.
7. **Intent engine** – `normalize` (lowercase, cleanup); `extract_amount` (tries the ordered
   `_AMOUNT_PATTERNS`, first match wins, must be > 0); `extract_date` (substring keywords
   today/yesterday/ystd/ytd/day before(/yesterday), else `d/m[/y]` or `d-m[-y]` with day/month swap
   fallback, else today; IST); `classify` scores exact keyword (1.0), phrase (1.5), fuzzy (difflib, ratio >= 0.85,
   weight 0.6) and per-user learned keywords (2.0); ties within 0.05 resolved by `PRIORITY_ORDER`;
   below 0.35 confidence -> `others`.
8. **Learning** – `PATCH /api/expenses/{id}` with a new `intent` saves description tokens to
   `learned_keywords(user_id, keyword)`; deletable via `/api/keywords`.
9. **Debts** – `POST/GET/PATCH/DELETE /api/debts`; stored with `book_id` of the active book;
   status `pending|settled` with `settled_on`; `GET /api/debts/summary` totals owed each way.
   Never touched by expense totals.
10. **Summaries** – `GET /api/summary` (by `book_id` or `month`) groups by intent with budget
    limit/remaining; `/api/summary/daily` per-day totals for a month.
11. **Budgets / export** – per-user monthly limit per intent (upsert); `/api/export/json|csv`.
12. **Errors** – any `PyMongoError` becomes 503 `{"detail":"Database unavailable, please try again"}`.

## Input / output contract
Base path `/api`. Auth header `Authorization: Bearer <jwt>` on everything except `POST auth/signup`,
`POST auth/login`, `GET /api/intents`, `GET /api/health`.
| Area | Routes |
|---|---|
| auth | `POST /auth/signup` (201), `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me` |
| books | `POST /books` (201), `GET /books`, `GET /books/active`, `PATCH /books/{id}` (name, is_active), `DELETE /books/{id}` (200 `{deleted_expenses}`) |
| expenses | `POST /expenses` (201), `GET /expenses?month&intent&book_id&limit(1-1000)&offset`, `GET|PATCH|DELETE /expenses/{id}` (delete 204), `DELETE /expenses` (200 `{deleted}`) |
| debts | `POST /debts` (201), `GET /debts?book_id&status`, `GET /debts/summary`, `PATCH|DELETE /debts/{id}` (delete 204) |
| summary | `GET /summary?month|book_id`, `GET /summary/daily?month` |
| budgets | `GET /budgets`, `POST /budgets` (201) |
| intents/keywords | `GET /intents` (public), `GET /keywords`, `DELETE /keywords/{keyword}` (204), `DELETE /keywords` (200 `{deleted}`) |
| other | `POST /preview`, `GET /export/json`, `GET /export/csv`, `GET /health` |
Errors: `{"detail": string | validation array}`; 401 auth, 409 duplicate user / no active book,
422 bad input, 404 missing, 503 DB down. Env: `MONGO_URI`, `MONGO_DB`, `JWT_SECRET`, `JWT_DAYS` (default 30).
Money is Decimal128 in Mongo, numbers in JSON; ids are integers from the `counters` collection.

## Open questions
- **Manual expense date uses server time** – `routers/expenses.py` uses `date.today()` when no
  date is given, while the text path and debts use IST (`_get_today`). On Vercel (UTC) this can be
  the previous day in IST early morning. Also an unparseable `date` silently becomes today, whereas
  debts return 422 for bad dates.
- **Engine quirks** (confirmed by running it): "2 tickets 500" yields amount 2 (first matching
  amount pattern) rather than 500. Date keywords are matched as plain substrings
  (`if kw in lower`), so "bytdz 50" contains `ytd` and is dated yesterday; the leftover text also has
  the substring removed.
- **Keyword overlap between intents** – same keyword listed in two intents: rice, swiggy, paneer,
  dal, curd (food+grocery), buttermilk, roll (food+tea_snacks), ticket (movie+transport),
  reliance (grocery+purchase). Outcome depends on `PRIORITY_ORDER`.
- **Version mismatch** – `app.version` is `2.0.0` but `/api/health` returns `version: "1.0.0"`
  and `database: "mongodb"` as literals.
- **Ambiguous route styles** – `intents.py` declares full `/api/...` paths in its decorators while
  other routers use a prefix; `preview` is `/api/preview`.
- **Book on create** – `POST /api/expenses` and `POST /api/debts` always file into the active book;
  there is no way to add to a non-active book (list/summary/export do accept `book_id`).
- **`Dockerfile`** still creates a "data directory for SQLite"; `data/budget.db` is an unused leftover.
- **CORS** `allow_origins=["*"]` with credentials off (fine for Bearer tokens, but wide open).
- **No rate limiting** on login/signup.
- **`PRIORITY_ORDER`** lists 13 intents (no `others`) – `others` is only the fallback.
- **Budgets vs. books** – budgets are per-month/global per user, while Home/Summary in `mobile` are book-scoped.
- **Silent ignore of bad dates on edit** – `crud.update_expense` swallows an unparseable `date` and
  still returns 200 with the old date.
- **Book totals scan all expenses** – `_book_totals` / `_pending_debts` read every expense/pending
  debt of the user on each book listing (no aggregation pipeline).
- **Global id counters** – `next_id` uses one counter per collection shared by all users, so ids are
  unique across users and reveal overall volume (isolation still enforced by `user_id` in queries).
- **Book delete is API-only** – `DELETE /api/books/{id}` (cascades to expenses and debts) exists and
  is tested, but `mobile` defines `deleteBook` and never calls it.

## Go deeper
- Business rules: [business/index.md](business/index.md)
- Implementation detail: [technical/index.md](technical/index.md)
