# CabClaim — Agent Notes

Use this file to stay aligned across chats. **Whenever a feature is added, completed, or materially changed, update the Pending Work (and related sections) in this file** so the next session has accurate context.

---

## Project summary

Local Python tooling to pull Uber/Rapido ride receipts, filter them, optimize under a spend limit, and upload expenses to Concur.

**Remote:** https://github.com/cenentury0941/cabclaim.git  

**Do not commit:** cookie files (`*Cookie*.txt`), `Activities.json`, `venv/`, `workspace/`, `rapido_ingest/`, PDFs (see `.gitignore`).

---

## Script pipeline

| Step | Script | Role |
|------|--------|------|
| 1 | `get_activities.py` | Fetch Uber trip activities → `Activities.json` |
| 2 | `get_uber_receipts.py` | Download Uber PDFs; filter by month + PIN |
| 3 | `ingest_rapido_receipts.py` | Sort Rapido PDFs by PIN into keep/delete folders |
| 4 | `optimize_receipts.py` | Keep best receipt subset under `MAX_AMOUNT` |
| 5 | `upload_uber_to_concur.py` | Upload Uber receipts as Concur expenses |
| 6 | `upload_rapido_to_concur.py` | Upload Rapido receipts as Concur expenses |

Shared helpers: `utils.py`. Config today is mostly **module-level constants** (paths, PIN, month, report IDs, cookies).

---

## Pending work

### 1. Refactor: move executable logic into `main()`

**Goal:** Importing a script must not run network I/O or mutate the filesystem. Only `main()` (or CLI `__main__`) should.

| Script | Status / needed change |
|--------|-------------------------|
| `get_uber_receipts.py` | Already has `main()` — OK |
| `optimize_receipts.py` | Already has `main()` — OK |
| `ingest_rapido_receipts.py` | Has `main()`, but `mkdir` runs at import — move into `main()` |
| `get_activities.py` | Entire body is top-level — wrap in `main()` + `__main__` guard |
| `upload_uber_to_concur.py` | Session + upload loop at module level — wrap in `main()` |
| `upload_rapido_to_concur.py` | Same as Uber upload |
| `upload_test.py` | Same pattern — wrap in `main()` if kept |

Keep defaults for CLI use; avoid rewriting business logic.

### 2. Multi-screen GUI

**Goal:** A desktop GUI that walks through multiple screens. Each screen collects params for one script and runs it.

**Constraints:**
- Do **not** rewrite script logic.
- Only change how config variables are initialized so they can take values from the GUI (e.g. optional `main(**kwargs)` overrides, or set module attrs then call `main()`).
- Long work must run off the UI thread; capture `print` output into a log panel.

**Suggested stack:** `customtkinter` or stdlib `tkinter` with a page stack.

**Suggested screens ↔ params:**

1. **Activities** — cookie path, CSRF token, lookback days, profile  
2. **Uber receipts** — month, PIN, cookie/activities paths  
3. **Rapido ingest** — PIN, ingest/keep/delete folders  
4. **Optimize** — `MAX_AMOUNT`, receipt dirs  
5. **Upload Uber** — `REPORT_ID`, `USER_ID`, Concur cookie, purpose, PDF folder  
6. **Upload Rapido** — same family of Concur fields  

Shared wizard state (PIN, cookies, report id) should carry across steps.

**Suggested layout:** `app.py` + `pages/` + `runner.py` (worker thread + stdout redirect).

### 3. Agents.md maintenance (ongoing)

This file’s **Pending work** (and status tables) must be updated when features land or scope changes. Do not leave completed items listed as pending.

---

## Done (for context)

- [x] Initialized git in `CabClaim/` (not the parent `PycharmProjects` folder)
- [x] Added `.gitignore` (secrets, venv, workspace data, PDFs)
- [x] Pushed initial source to `cenentury0941/cabclaim`
- [x] Removed unfinished parent `PycharmProjects/.git` that was polluting Source Control

---

## Working agreements

- Prefer minimal diffs to existing scripts until the GUI needs param injection.
- Never commit cookies or live activity dumps.
- After finishing a pending item: check it off here, move notes to “Done” if useful, and refresh remaining pending scope.
