# mobile — code-index

## Role
Expo (SDK 57) / React Native app, Android-first ("Arun's Budget"), built to an APK with EAS.
It is a thin client over the `backend` module: sign-in gate, per-user book with a typed quick-add
and an editable expense table, Summary by category, Debts, Settings (budgets, learned keywords,
export, delete-all). It holds no business logic beyond validation, formatting, an offline queue and
a saved login token.

## Files + dependencies
| File | Depends on | Purpose |
|---|---|---|
| `index.ts` | expo-router | `import "expo-router/entry"` |
| `app/_layout.tsx` | AppContext, SplashOverlay, AuthScreen | Root stack; splash -> auth gate; `key={user?.id ?? "guest"}` remounts screens per account |
| `app/(tabs)/_layout.tsx` | AppContext, HeaderMenu, DebtsButton, safe-area | Tabs Home/Summary/Settings; bottom inset padding for gesture bar |
| `app/(tabs)/index.tsx` | api, AppContext, useKeyboardOverlap, helpers | Home: book card, quick-add + category dropdown, editable table, book switcher |
| `app/(tabs)/summary.tsx` | api | Active-book totals by category; taps open detail |
| `app/(tabs)/settings.tsx` | api | Budgets, learned keywords, export preview, delete all expenses |
| `app/detail/[intent].tsx` | api, expo-router params | Expenses of one category (edit/delete) |
| `app/debts.tsx` | api, AppContext, useKeyboardOverlap | Debts list (Pending/Returned), add form, mark returned/undo, delete |
| `src/api.ts` | AsyncStorage, types | Only network layer: token, errors, connectivity flag, offline queue, all endpoints |
| `src/AppContext.tsx` | api, authStorage, theme | Theme, auth status/user, `pendingDebts` |
| `src/authStorage.ts` | expo-secure-store, AsyncStorage | Persist token (SecureStore; AsyncStorage on web) + cached user |
| `src/AuthScreen.tsx` | AppContext, api | Sign in / Sign up form |
| `src/SplashOverlay.tsx` | expo-linear-gradient, @expo-google-fonts/yellowtail | "JSA" signature + "by Arun" opening screen |
| `src/HeaderMenu.tsx` | AppContext | "⋮" menu: theme, signed-in user, sign out |
| `src/DebtsButton.tsx` | AppContext | Header 🤝 button with pending badge |
| `src/useKeyboardOverlap.ts` | RN Keyboard | Lifts content by measured keyboard overlap (Android edge-to-edge) |
| `src/helpers.ts`, `src/theme.ts`, `src/types.ts` | — | INR/date formatting, colors, backend type mirrors |
| `app.json`, `eas.json`, `package.json`, `tsconfig.json` | — | Expo/EAS/build config |

## What the code actually does
1. **Launch** – `RootLayout` mounts `AppProvider`; `SplashOverlay` plays (~1.5s write + "by Arun"
   + fade; waits at most 1.5s for the Yellowtail font), then `onDone` reveals the app.
2. **Session check** – `AppProvider` loads the token from `authStorage`. No token -> `signedOut` ->
   `AuthScreen`. With a token it calls `POST /api/auth/refresh`; success stores the new token and
   user; a 401 signs out; any other failure (offline) falls back to the cached user.
3. **Sign in/up** – `AuthScreen` validates locally (same username/email/password rules as the backend),
   calls `api.signIn`/`api.signUp`, then `startSession` (sets in-memory token, saves token + user).
4. **Any 401 while signed in** – `api.apiFetch` calls the unauthorized handler -> `signOut()` (clears
   token, cached user, offline queue).
5. **Home** – on focus loads the active book (`GET /books/active`), its expenses (limit 1000) and the
   intents list; sets the header badge from `book.pending_debts`. No book -> "Start a book" card
   (default name = current month). Book card opens a switcher modal (pick / create a book).
6. **Quick add** – typing shows a category dropdown; a category must be chosen, then `POST /expenses`
   with `{raw_text, intent}`. Offline (`isOnline()` false) -> entry saved to AsyncStorage queue;
   `flushQueue` runs after a successful add and when connectivity returns. Other API errors are shown.
7. **Table editing** – tap Date/Amount/Description cell -> inline input -> `PATCH /expenses/{id}`;
   rows are deleted via a confirm alert -> `DELETE`. Book total/count are computed from the in-memory rows.
8. **Summary** – active book's `GET /summary?book_id=`; each category card shows total, percent or
   budget progress (over-budget flagged); tap -> `detail/[intent]?intent&bookId`.
9. **Debts** – loads active book + `GET /debts?book_id=`; splits pending/settled, shows totals
   "will get"/"owe"; add form posts `{person, amount, direction, reason, date}` (date typed as
   YYYY-MM-DD); "Got it back / Paid back" PATCHes `status`; updates the Home badge count.
10. **Settings** – set budget per category, list/delete learned keywords, export (fetches JSON/CSV
    and shows the first 500 characters in an alert), delete all expenses.
11. **Header menu** – theme choice stored in AsyncStorage (`@budget_theme`, default dark); sign out.
12. **Keyboard** – screens with inputs wrap in a View using `useKeyboardOverlap` and add `overlap`
    as bottom padding (auth screen, Home, debts, modals).

## Input / output contract
- **Consumes**: backend REST under `EXPO_PUBLIC_API_URL || https://backend-ten-chi-67.vercel.app`,
  JSON, `Authorization: Bearer <token>`; expects `{detail}` errors and 204 for deletes.
  Public paths (no token needed): `/api/auth/login`, `/api/auth/signup`, `/api/intents`, `/api/health`.
- **Persists on device**: SecureStore `budget_auth_token`; AsyncStorage `@budget_user`,
  `@budget_theme`, `@budget_pending_queue` (entries `{id, raw_text, intent, timestamp}`).
- **Produces**: a UI only; build outputs are the Expo bundle / APK (`eas build -p android --profile preview`).
- **Routes (expo-router)**: `/(tabs)` (index, summary, settings), `/debts`, `/detail/[intent]`.

## Open questions
- **`getActiveBook` hides failures** – `api.getActiveBook` returns `null` on *any* error (offline,
  503, 401), so Home/Summary/Debts can show "Start a book"/"No book yet" when the real problem is the
  network. Home also never sets `online=false` in that case because no exception reaches `loadData`.
- **Dead API helpers** – defined but never called: `getDailySummary`, `previewExpense`, `checkHealth`,
  `renameBook`, `deleteBook`; helpers `debounce`, `prevMonth`, `nextMonth` unused. The book
  rename/delete backend features have no UI.
- **Offline detection is string-based** – `apiFetch` flags offline when the error text contains
  "Network request failed", "Failed to fetch" or "TypeError"; other failure messages are not treated as
  offline, so the queue is not used for them.
- **Queue coverage** – only "add expense" is queued; edits, deletes, debts and book changes fail
  when offline. `flushQueue` stops at the first failure, including non-network errors (e.g. 409 no
  active book), leaving the item queued indefinitely.
- **`exportData` bypasses `apiFetch`** – no online flag update and no 401 -> sign-out handling, and the
  result is only a 500-character preview in an alert (no file/share).
- **Delete-all scope vs. UI** – Settings "Delete All Expenses" calls `DELETE /api/expenses`, which removes
  expenses in *every* book; the alert text does not mention books.
- **Budgets vs. books** – Settings edits budgets that the Summary applies to the active book's totals
  (backend budgets are global per user, not per book).
- **`mobile/.env`** has an `API_URL=` key that nothing reads (the app uses `EXPO_PUBLIC_API_URL`).
- **`app.json` `web` section and `react-native-web`** remain in the project although Android is the only
  tested target; `authStorage` has a web fallback that stores the token in plain AsyncStorage.
- **Naming** – app name is "Arun's Budget" in `app.json` (and splash "by Arun") while the header shows
  `<username>'s Budget`; `package.json` name is `monthly-budget`.
- **Silent summary errors** – `summary.tsx` only `console.error`s a failed load (no message to the user).
- **Committed logs** – `eas-build.log`, `eas-login.log`, `expo-native.log` are in the repo folder.
- **Manual date typing** – date cells and the debt form accept free text; only debts validate the
  `YYYY-MM-DD` shape client-side, the expense date cell relies on the backend (which silently ignores
  an unparseable edit).
- **iOS** – `app.json` declares a bundle id but only Android is built/tested here.

## Go deeper
- Business rules: [business/index.md](business/index.md)
- Implementation detail: [technical/index.md](technical/index.md)
