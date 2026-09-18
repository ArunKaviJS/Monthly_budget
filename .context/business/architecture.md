# Business architecture (system level)

## Product
A personal expense tracker. Each person signs up (unique username + unique email + password)
and only ever sees their own data. The app is branded "Arun's Budget" in `mobile/app.json`,
but the Home header shows `<username>'s Budget` (`mobile/app/(tabs)/_layout.tsx`).

## Core concepts (shared by both modules)
- **Book** – a named container for expenses and debts (a month, a trip, anything; free name).
  Exactly one book per user is "active"; Home shows the active book.
- **Expense** – amount + description + category ("intent") + date, belongs to a book.
  The user types free text ("tea 20") and **chooses the category from a dropdown**; the
  backend still parses amount/date/description from the text (`backend/app/intent_engine.py`).
- **Category / intent** – 14 fixed categories defined in `backend/app/intent_config.py`
  (food, tea_snacks, petrol, movie, fruits_diet, transport, bills_recharge, medical, grooming,
  rent, education, grocery, purchase, others). Served publicly at `GET /api/intents`.
- **Debt** – money the user gave ("lent", they owe me) or got ("borrowed", I owe them),
  with person, reason, date; lives inside a book; `pending` -> `settled`. Debts never change
  expense totals. Pending count drives a red badge on the Home header.
- **Budget** – optional monthly limit per category (per user).
- **Learned keywords** – when the user corrects a category, the word is remembered per user.

## Rules that span modules
- Money is INR; dates are IST (`_get_today` in backend, `getToday`/`getCurrentMonth` in mobile).
- Data is isolated per user through `user_id` on every document (single shared collections,
  not per-user collections).
- Deleting a book deletes its expenses and debts; if the active book is deleted another
  becomes active.
- Sessions persist: phone keeps a JWT and re-validates it on every app open.
- Offline: adding an expense while offline is queued on the phone and sent later.

## Out of scope in code today
No password reset, no email verification, no rate limiting, no multi-currency.
(See each module's "Open questions" for behaviors that look unintended.)
