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
| 3 | `ingest_rapido_receipts.py` | Unpack Rapido zip, keep cab PDFs matching PIN |
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
| `get_uber_receipts.py` | Done — `main(..., on_progress=)`; clears `workspace/uber_receipts` before download; live UI updates; reads `workspace/Activities.json` |
| `optimize_receipts.py` | Done — `main(max_amount=, uber_dir=, rapido_dir=, …)` |
| `ingest_rapido_receipts.py` | Done — `main(pincode=, zip_source=, …)`; unpacks zip into ingest folder; mkdir in `main()` |
| `get_activities.py` | Done — `main(cookie_header=None, output_file=None)`; writes `workspace/Activities.json`; CLI loads `Uber_Cookie.txt` if cookie omitted |
| `upload_uber_to_concur.py` | Done — `main(report_id=, user_id=, cookie_header=, …)` |
| `upload_rapido_to_concur.py` | Done — `main(report_id=, user_id=, cookie_header=, …)` |
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
Deps: `requirements.txt` (`streamlit`, `requests`, `pymupdf`, `extra-streamlit-components`).

**Layout:**
- `app.py` — home page (includes **Clear workspace**)
- `pages/` — one Streamlit page module per script screen (sidebar auto-lists them)
- `web/runner.py` — stdout/stderr capture helper
- `web/workspace.py` — per-device workspace under `workspace/<device_id>/` (UUID in `cc_device_id` browser cookie); delete that folder entirely on clear (manual button + once per Streamlit session); recreate on demand
- `web/field_cookies.py` — persist Report ID / User ID text fields in browser cookies (cookie headers stay empty each session)
- `web/page_consent.py` — one-time, non-dismissible privacy dialog on workflow pages; acceptance persists in the `cc_page_consent` browser cookie

**Device isolation (shared host):**
- UI never reads/writes the shared `workspace/` root; all CRUD goes through `web.workspace.workspace_paths()` → `workspace/<uuid>/…`
- CLI scripts still default to flat `workspace/…` paths; the UI injects device-scoped paths via `main(**kwargs)`
- Rapido zip unpack also uses `workspace/<uuid>/rapido_ingest` (not repo-root `rapido_ingest/`) when run from the UI
- Clear workspace / session-start wipe deletes the current device folder entirely (`workspace/<uuid>/`), not just its contents (other users' data is untouched); the folder is recreated on demand when a screen needs paths

**Screens done:**
- **Home** (`app.py`) — pipeline overview + **Clear workspace** (removes this device's `workspace/<uuid>/` folder); also removes that folder once on Streamlit session start
- **Get Uber Receipts** (`pages/1_Get_Uber_Receipts.py`) — **Cookie Header** (empty each session), **Month**, **Pincode**; on Run fetches activities via `get_activities.main(...)` then downloads via `get_uber_receipts.main(...)` with live progress; PDF preview for files in the device `uber_receipts` folder
- **Ingest Rapido Receipts** (`pages/2_Ingest_Rapido_Receipts.py`) — zip upload, shared **Pincode**; runs `ingest_rapido_receipts.main(...)`; PDF preview for kept receipts
- **Optimize Receipts** (`pages/3_Optimize_Receipts.py`) — **Spend limit**; runs `optimize_receipts.main(...)`; PDF preview for kept receipts
- **Upload Receipts** (`pages/4_Upload_Receipts.py`) — shared Concur settings (**Report ID** / **User ID** restored from browser cookies; **Cookie Header** empty each session); fetches and displays read-only list values for Concur `mainForm` fields 24–26, then injects their IDs into `orgUnit1`–`orgUnit3` during upload; separate **Upload Uber** and **Upload Rapido** sections with live per-expense progress

**Screens still to add (one at a time as specified):**

1. ~~**Activities + Uber receipts**~~ → done (merged: Cookie Header, Month, Pincode, PDF list + preview)  
2. ~~**Rapido ingest**~~ → done (zip upload, PIN, PDF preview)  
3. ~~**Optimize**~~ → done (spend limit, PDF preview)  
4. ~~**Upload**~~ → done (shared Concur fields; Uber + Rapido sections on one page)  

Shared values: `st.session_state` (e.g. `uber_cookie_header`, `uber_activities_cookie_header` set after successful activities fetch on Get Uber Receipts, `uber_receipt_month`, `receipt_pin` via `web.session_state`, `concur_*` on upload screen). Concur **Report ID** / **User ID** hydrate from browser cookies via `web.field_cookies`; Uber/Concur cookie header fields stay empty at each session start. Device ID via `cc_device_id` cookie (`web.workspace.ensure_device_id`).

### 3. Agents.md maintenance (ongoing)

This file’s **Pending work** (and status tables) must be updated when features land or scope changes. Do not leave completed items listed as pending.

---

## Done (for context)

- [x] Initialized git in `CabClaim/` (not the parent `PycharmProjects` folder)
- [x] Added `.gitignore` (secrets, venv, workspace data, PDFs)
- [x] Pushed initial source to `cenentury0941/cabclaim`
- [x] Removed unfinished parent `PycharmProjects/.git` that was polluting Source Control
- [x] Replaced tkinter GUI with Streamlit web UI (`app.py` + `pages/` + `web/runner.py`)
- [x] Get Uber Receipts screen (Cookie Header + activities fetch merged in; Month, Pincode, PDF list + preview, live per-receipt UI updates)
- [x] Removed standalone Get Activities page; renumbered remaining `pages/`
- [x] Ingest Rapido Receipts screen (zip upload, shared PIN, PDF preview) + `ingest_rapido_receipts.main(...)` param injection
- [x] Optimize Receipts screen (spend limit, PDF preview) + `optimize_receipts.main(...)` param injection
- [x] Upload Receipts screen (shared Concur settings, Uber + Rapido sections) + `upload_*_to_concur.main(...)` param injection
- [x] Concur uploads serialize fares as exact JSON decimal numbers with two fractional digits and no binary-float conversion
- [x] Upload screen fetches Concur's new-expense form, displays the listValue ID/value for `mainForm` fields 24–26 as read-only inputs, and uses those IDs for `orgUnit1`–`orgUnit3` in both upload APIs
- [x] Cookie Header / Report ID / User ID text fields empty by default; Report ID / User ID persisted in browser cookies; cookie headers not stored across sessions
- [x] Per-device workspace isolation: `workspace/<device_id>/` keyed by browser cookie UUID; UI injects scoped paths into script `main()` calls
- [x] One-time workflow-page privacy dialog with local illustration, Exit-to-home action, and cookie-persisted acceptance

---

## Working agreements

- Prefer minimal diffs to existing scripts until the UI needs param injection.
- Never commit cookies or live activity dumps.
- Keep the web UI local-only when handling cookie headers.
- After finishing a pending item: check it off here, move notes to “Done” if useful, and refresh remaining pending scope.
