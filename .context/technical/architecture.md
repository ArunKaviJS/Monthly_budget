# Technical architecture (system level)

## Runtime topology
```
Expo app (Android APK / Expo Go)  --HTTPS + Bearer JWT-->  FastAPI on Vercel  -->  MongoDB Atlas (db "budget")
mobile/src/api.ts                                          backend/api/index.py     collections: users, books,
(base URL hardcoded default)                               -> app.main:app          expenses, debts, budgets,
                                                                                    learned_keywords, counters
```
- The mobile base URL is `https://backend-ten-chi-67.vercel.app` unless `EXPO_PUBLIC_API_URL`
  is set at bundle time (`mobile/src/api.ts`).
- The backend is stateless; every request loads the user from the JWT `sub`.

## Deployment
- **Backend**: `backend/vercel.json` builds `api/index.py` with `@vercel/python` and routes
  every path to it. `.vercelignore` excludes venv, tests, data, `.env`. Environment variables
  on Vercel: `MONGO_URI`, `MONGO_DB`, `JWT_SECRET` (secrets; never commit values).
- **Mobile**: EAS Build, profile `preview` -> APK (`mobile/eas.json`), `appVersionSource: local`,
  Expo owner `arunkavijs`, slug `monthly-budget`. Android `usesCleartextTraffic: true` via
  `expo-build-properties`.
- **Local dev**: backend `uvicorn app.main:app`; mobile `expo start` (Expo Go over LAN).

## Secrets / config
- `backend/.env` (gitignored) holds `MONGO_URI`, `MONGO_DB`, `JWT_SECRET`; loaded by
  `backend/app/database.py` via python-dotenv without overriding real env vars.
- `mobile/.env` exists with an `API_URL=` key that no source file reads.
- Tests never touch Atlas: `MONGO_URI=mongomock://...` is forced in `backend/tests/conftest.py`.

## Repo layout
- `backend/` FastAPI service, `mobile/` Expo app, `README.md` (partly stale, see Open questions),
  `.claude/skills/update-context/` (doc-sync skill), `.context/` (this system).
- Git: branch `main`, remote `origin` github.com/ArunKaviJS/Monthly_budget.

## Cross-module contract
Types in `mobile/src/types.ts` are hand-maintained mirrors of `backend/app/schemas.py`
(no code generation). Auth header: `Authorization: Bearer <jwt>`. Error bodies: `{"detail": ...}`
(string or FastAPI validation array; parsed by `extractDetail` in `mobile/src/api.ts`).

## Open questions (system level)
- `README.md` (architecture/database text is MongoDB-correct) has a File Tree that omits
  `routers/auth.py`, `books.py`, `debts.py`, three of the four test files (lists only
  `test_intent_engine.py`), and `mobile/src/{AppContext,AuthScreen,authStorage,HeaderMenu,
  DebtsButton,SplashOverlay,useKeyboardOverlap}` plus `mobile/app/debts.tsx`.
- `backend/Dockerfile` still contains "Create data directory for SQLite" though storage is MongoDB.
- `backend/data/budget.db` is an old SQLite leftover (gitignored, unused).
- Committed logs under `mobile/` (`eas-build.log`, `eas-login.log`, `expo-native.log`) are tracked
  in git and `eas-build.log` shows as modified.
- The Atlas password was shared in chat during development; rotating it (then updating the
  Vercel `MONGO_URI`) is outstanding.
