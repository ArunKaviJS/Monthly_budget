# mobile — user-facing behavior

## Opening
Black splash: "JSA" is written in a Yellowtail signature style with a fading white and an
underline stroke; "by Arun" fades in at the bottom centre; then the screen fades away. After it,
the app shows "Signing you in…" while the saved login is verified, then either the app or the
Sign in / Sign up page.

## Accounts
- Sign up: username, email, password. Sign in: username **or** email + password.
- The phone remembers who is signed in; every app open re-verifies with the server. Offline opens keep
  the last known user. Signing out (⋮ menu) forgets the login and any not-yet-sent offline entries.
- Home title is "`<username>'s Budget`".

## Books and expenses (Home tab)
- First use asks to "Start a book" (suggested name = current month, any name allowed).
- Tap the book card to switch books or create another (the new one becomes current).
- Quick add: type e.g. "tea 20 yesterday", pick a category from the dropdown that appears, tap add.
  The category is never guessed for the user at this step.
- The table shows Date | Amount | Description; tap a cell to edit it in place; delete a row from its
  action; totals update immediately.
- Offline adds are saved and sent later; a banner shows offline/pending counts.

## Summary tab
Current book's total, and a card per category with amount, share (or budget progress, flagged when
over budget); tap a category to list/edit its entries.

## Debts (🤝 button on Home)
- "I gave" (friend owes me) and "I got" (I owe them), each with person, reason, date, amount.
- Pending entries show a red count badge on the 🤝 button; marking one "Got it back"/"Paid back"
  moves it to Returned and lowers the badge; badge hides at zero. Undo and delete are available.
- Debts belong to a book and never change expense totals.

## Settings tab
Monthly budget per category, learned keywords (remove one or all), export (preview), delete all
expenses (irreversible, all books).

## Theme
⋮ menu: Dark (default) or Light; choice is remembered on the device.
