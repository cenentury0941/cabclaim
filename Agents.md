# CabClaim — Agent Notes

Use this file to stay aligned across chats. **Whenever a feature is added, completed, or materially changed, update the Pending Work (and related sections) in this file** so the next session has accurate context.

---

## Project summary

Local Python tooling to pull Uber/Rapido ride receipts, filter them, optimize under a spend limit, and upload expenses to Concur.

**Remote:** https://github.com/cenentury0941/cabclaim.git  

**Do not commit:** cookie files (`*Cookie*.txt`), `Activities.json` / `workspace/`, `venv/`, `rapido_ingest/`, PDFs (see `.gitignore`).

---

## Script pipeline

| Step | Script | Role |
|------|--------|------|
| 1 | `get_activities.py` | Fetch Uber trip activities → `workspace/Activities.json` |
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
| `get_uber_receipts.py` | Done — `main(target_month=..., target_pin=..., cookie_header=...)`; reads `workspace/Activities.json` |
| `optimize_receipts.py` | Already has `main()` — OK |
| `ingest_rapido_receipts.py` | Has `main()`, but `mkdir` runs at import — move into `main()` |
| `get_activities.py` | Done — `main(cookie_header=None)`; writes `workspace/Activities.json`; CLI loads `Uber_Cookie.txt` if cookie omitted |
| `upload_uber_to_concur.py` | Session + upload loop at module level — wrap in `main()` |
| `upload_rapido_to_concur.py` | Same as Uber upload |
| `upload_test.py` | Same pattern — wrap in `main()` if kept |

Keep defaults for CLI use; avoid rewriting business logic.

### 2. Multi-screen web UI

**Goal:** A local web UI that walks through multiple screens. Each screen collects params for one script and runs it.

**Constraints:**
- Do **not** rewrite script logic.
- Only change how config variables are initialized so they can take values from the UI (e.g. optional `main(**kwargs)` overrides).
- Capture `print` output into an on-page log (`web.runner.run_captured`).

**Stack (in place):** [Streamlit](https://streamlit.io/) (local browser UI).

**Run (from repo root, with venv):**
```bash
./venv/bin/streamlit run app.py
```
Deps: `requirements.txt` (`streamlit`, `requests`, `pymupdf`).

**Layout:**
- `app.py` — home page (includes **Clear workspace**)
- `pages/` — one Streamlit page module per script screen (sidebar auto-lists them)
- `web/runner.py` — stdout/stderr capture helper
- `web/workspace.py` — clear `workspace/` contents

**Screens done:**
- **Home** (`app.py`) — pipeline overview + **Clear workspace** (wipes `workspace/`)
- **Get Activities** (`pages/1_Get_Activities.py`) — configurable **Cookie Header**; runs `get_activities.main(cookie_header=...)`; saves `workspace/Activities.json`; optional load from `Uber_Cookie.txt`
- **Get Uber Receipts** (`pages/2_Get_Uber_Receipts.py`) — **Month** dropdown, **Pincode** number field; runs `get_uber_receipts.main(...)`; lists PDFs in `workspace/uber_receipts` with in-page preview (click/select item)

**Screens still to add (one at a time as specified):**

1. ~~**Activities**~~ → done (Cookie Header only)  
2. ~~**Uber receipts**~~ → done (Month, Pincode, PDF list + preview)  
3. **Rapido ingest** — PIN, ingest/keep/delete folders → `ingest_rapido_receipts.py`  
4. **Optimize** — `MAX_AMOUNT`, receipt dirs → `optimize_receipts.py`  
5. **Upload Uber** — `REPORT_ID`, `USER_ID`, Concur cookie, purpose, PDF folder  
6. **Upload Rapido** — same family of Concur fields  

Shared values: `st.session_state` (e.g. `uber_cookie_header`, `uber_receipt_month`, `uber_receipt_pin`).

### 3. Agents.md maintenance (ongoing)

This file’s **Pending work** (and status tables) must be updated when features land or scope changes. Do not leave completed items listed as pending.

---

## Done (for context)

- [x] Initialized git in `CabClaim/` (not the parent `PycharmProjects` folder)
- [x] Added `.gitignore` (secrets, venv, workspace data, PDFs)
- [x] Pushed initial source to `cenentury0941/cabclaim`
- [x] Removed unfinished parent `PycharmProjects/.git` that was polluting Source Control
- [x] Replaced tkinter GUI with Streamlit web UI (`app.py` + `pages/` + `web/runner.py`)
- [x] Get Activities screen (Cookie Header) + `get_activities.main(cookie_header=...)`
- [x] Get Uber Receipts screen (Month, Pincode, PDF list + preview)

---

## Working agreements

- Prefer minimal diffs to existing scripts until the UI needs param injection.
- Never commit cookies or live activity dumps.
- Keep the web UI local-only when handling cookie headers.
- After finishing a pending item: check it off here, move notes to “Done” if useful, and refresh remaining pending scope.
