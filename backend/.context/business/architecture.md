# backend — business rules

## Accounts
- Username: 3-24 chars of letters, digits, `_` or `.`; unique case-insensitively.
- Email: unique case-insensitively (regex-validated). Password: 6-128 chars.
- Login accepts username **or** email. Sessions are 30-day tokens (`JWT_DAYS`); the app calls
  refresh at every open to re-validate and extend.
- No password reset, email verification, or account deletion endpoint exists.

## Isolation
Every document (books, expenses, debts, budgets, learned keywords) stores `user_id`; every query
filters by it. One user can never read/update another's ids (returns 404).

## Books
- A user starts with no book; adding an expense or debt without an active book is refused (409),
  so the client must create a book first.
- Name is free text; the newest created book becomes active; a user can switch the active book.
- Deleting a book deletes its expenses and debts; another book becomes active if any remain.

## Expenses
- Text like "petrol 500 yesterday" is parsed: amount, date (default today IST), description.
- Category is chosen by the user in the app (dropdown) and sent as `intent`; the classifier only
  decides when no intent is sent (also used by `/api/preview`).
- 14 categories (see `intent_config.INTENTS`): food, tea_snacks, petrol, movie, fruits_diet,
  transport, bills_recharge, medical, grooming, rent, education, grocery, purchase, others.
- Editing amount, description, date or category is allowed. Changing the category is treated as
  the user teaching the app: the description's meaningful words are remembered for that user and
  boost that category next time (weight 2.0).
- "Delete all expenses" wipes every book's expenses for that user (space is freed by real deletion).

## Debts
- Direction `lent` = "I gave" (they owe me), `borrowed` = "I got" (I owe them); person <=60 chars,
  amount > 0 and < 1e9, optional reason <=200, date (defaults today, format YYYY-MM-DD).
- `pending` until marked `settled` (records `settled_on`); can be reopened. Deleting is permanent.
- Debts are informational only: they never affect expense totals or budgets.
- The number of pending debts of a book is exposed on the book (`pending_debts`) for the badge.

## Budgets
Optional monthly limit per category per user; the summary shows limit and remaining.
Budgets are not tied to a book.

## Summaries / export
- Summary: totals and percent per category, either for one book or a calendar month.
- Export: JSON or CSV of the user's expenses, filterable by month or book.
