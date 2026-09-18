---
name: update-context
description: Sync this project's .context/ docs (code-index.md, business/, technical/) to match the current uncommitted changes. Use ONLY when the user explicitly runs /update-context — never run proactively, never after every edit, never as part of another task.
---

# update-context

Updates `.context/` documentation to reflect **the current working phase
only** — whatever is actually changed right now. Not a full repo re-scan,
not a routine that runs after every edit. Manual, on-demand, scoped to the
diff.

## When to run

Only on explicit `/update-context` invocation. If no files have changed
since the last update, say so and do nothing — do not "refresh" content that
isn't stale.

## Steps

1. **Find what actually changed.**
   `git status --short` and `git diff` (staged + unstaged) against `HEAD`.
   This diff *is* the scope — nothing outside it gets touched.

2. **Map changed files to context levels.**
   Read `.context/context.yml` for the folder → `code-index.md` map.
   - A changed file under `<module-folder>/` → that module needs a
     **specific** update.
   - A changed root-level config/infra file, a new/removed/renamed module
     folder, or a change spanning more than one module → the root needs an
     **overall** update.
   - Both can apply in the same run.

3. **Specific update** (per touched module, only those touched):
   - Re-read the changed source file(s) in that folder — the actual code,
     not the old `.context/` content.
   - Open that module's `.context/code-index.md`. Edit only the facts that
     are now wrong or missing — leave everything else as-is.
   - Update business/architecture.md or technical/architecture.md only for
     the sections the change actually affects.
   - Update that module's index.md only if summary/covers/keywords no
     longer match reality.

4. **Overall update** (only if step 2 flagged it):
   - Update root `.context/context.yml` — add/remove/rename the module entry.
   - Update root business/architecture.md / technical/architecture.md only
     for the parts the change actually affects — not a rewrite.

5. **Do not touch:** any module folder with no changed files, sections of a
   file unrelated to the diff.

6. **Report**, one line per file actually edited: path + one-line reason.
   If nothing needed updating, say that explicitly instead of forcing an edit.
