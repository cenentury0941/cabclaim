"""Upload Receipts — upload Uber and Rapido PDFs to Concur."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import streamlit as st

import upload_rapido_to_concur
import upload_uber_to_concur
from web.field_cookies import hydrate_text_fields, mark_field_dirty, persist_dirty_fields
from web.pdf_preview import list_pdfs
from web.runner import run_streaming
from web.session_state import ensure_ephemeral_text
from web.workspace import clear_workspace_on_session_start, workspace_paths

st.set_page_config(page_title="Upload Receipts — CabClaim", layout="wide")
clear_workspace_on_session_start()
paths = workspace_paths()

UBER_FOLDER = paths.uber_receipts
RAPIDO_FOLDER = paths.rapido_receipts

st.title("Upload Receipts")
st.write(
    "Upload optimized receipt PDFs to Concur as expense entries. "
    "Configure shared Concur settings below, then run Uber or Rapido upload separately."
)

hydrate_text_fields("concur_report_id", "concur_user_id")
ensure_ephemeral_text("concur_cookie_header")

st.subheader("Concur settings")

col_report, col_user = st.columns(2)
with col_report:
    st.text_input(
        "Report ID",
        key="concur_report_id",
        on_change=mark_field_dirty,
        args=("concur_report_id",),
    )
with col_user:
    st.text_input(
        "User ID",
        key="concur_user_id",
        on_change=mark_field_dirty,
        args=("concur_user_id",),
    )

st.text_area(
    "Concur Cookie Header",
    key="concur_cookie_header",
    height=140,
    help="Browser Cookie header for concursolutions.com",
)
ensure_ephemeral_text("concur_cookie_header")
persist_dirty_fields()


def _shared_kwargs() -> dict:
    return {
        "report_id": (st.session_state.get("concur_report_id") or "").strip(),
        "user_id": (st.session_state.get("concur_user_id") or "").strip(),
        "cookie_header": (st.session_state.get("concur_cookie_header") or "").strip(),
    }


def _validate_concur_settings() -> str | None:
    kwargs = _shared_kwargs()
    if not kwargs["report_id"]:
        return "Report ID is empty."
    if not kwargs["user_id"]:
        return "User ID is empty."
    if not kwargs["cookie_header"]:
        return "Concur Cookie Header is empty."
    return None


def _render_live_expenses(
    results: list[dict],
    *,
    highlight: str | None = None,
    container,
) -> None:
    with container.container():
        st.markdown("**Expenses (live)**")
        if not results:
            st.caption("Waiting for uploads…")
            return
        for item in results:
            filename = item["filename"]
            if item.get("pending"):
                label = f"{filename} — uploading…"
            elif item.get("success"):
                expense_id = item.get("expense_id") or "created"
                label = f"{filename} → {expense_id}"
            else:
                label = f"{filename} — failed"
            if highlight and filename == highlight:
                st.markdown(f"- **{label}**")
            else:
                st.markdown(f"- {label}")


def _run_upload_section(
    *,
    label: str,
    folder: Path,
    upload_main: Callable,
    button_key: str,
) -> None:
    count = len(list_pdfs(folder))
    st.caption(f"Found **{count}** receipt(s) ready to upload.")

    progress_slot = st.empty()
    status_slot = st.empty()
    log_slot = st.empty()
    live_list_slot = st.empty()

    if not st.button(f"Upload {label}", type="primary", key=button_key):
        return

    error = _validate_concur_settings()
    if error:
        st.error(error)
        return
    if count == 0:
        st.error(f"No {label} receipt PDFs found. Run earlier pipeline steps first.")
        return

    results: list[dict] = []
    progress_slot.progress(0, text="Starting…")
    status_slot.info(f"Uploading {label} receipts…")
    _render_live_expenses(results, container=live_list_slot)

    def on_output(text: str) -> None:
        log_slot.code(text or "(no output)", language="text")

    def on_progress(event: dict) -> None:
        phase = event.get("phase")
        index = int(event.get("index") or 0)
        total = int(event.get("total") or 0)
        filename = event.get("filename") or ""

        if phase == "start":
            progress_slot.progress(0, text=f"Found {total} receipt(s) — starting…")
            status_slot.info(f"Uploading 0 / {total}…")
        elif phase == "processing":
            results[:] = [
                item for item in results if item.get("filename") != filename
            ]
            results.append({"filename": filename, "pending": True})
            frac = ((index - 1) / total) if total else 0.0
            progress_slot.progress(
                min(frac, 1.0),
                text=f"Upload {index} / {total}: {filename}",
            )
            status_slot.info(f"Uploading {index} / {total}: {filename}")
            _render_live_expenses(results, highlight=filename, container=live_list_slot)
        elif phase == "expense":
            for item in results:
                if item.get("filename") == filename:
                    item["pending"] = False
                    item["success"] = bool(event.get("success"))
                    item["expense_id"] = event.get("expense_id")
                    break
            else:
                results.append({
                    "filename": filename,
                    "pending": False,
                    "success": bool(event.get("success")),
                    "expense_id": event.get("expense_id"),
                })
            frac = (index / total) if total else 1.0
            state = "created" if event.get("success") else "failed"
            progress_slot.progress(
                min(frac, 1.0),
                text=f"Upload {index} / {total}: {filename} ({state})",
            )
            status_slot.info(f"Uploaded {index} / {total}…")
            _render_live_expenses(results, highlight=filename, container=live_list_slot)
        elif phase == "done":
            progress_slot.progress(1.0, text="Complete")
            _render_live_expenses(results, container=live_list_slot)

    ok, log = run_streaming(
        lambda: upload_main(
            **_shared_kwargs(),
            pdf_folder=str(folder),
            on_progress=on_progress,
        ),
        label=f"Upload {label} Receipts",
        on_output=on_output,
    )

    log_slot.code(log or "(no output)", language="text")
    if ok:
        status_slot.success(f"{label} upload finished.")
        progress_slot.progress(1.0, text="Complete")
    else:
        status_slot.error(f"{label} upload failed — see log above.")


st.divider()
st.subheader("Upload Uber receipts")
st.caption(f"PDF folder: `{UBER_FOLDER}`")
_run_upload_section(
    label="Uber",
    folder=UBER_FOLDER,
    upload_main=upload_uber_to_concur.main,
    button_key="upload_uber",
)

st.divider()
st.subheader("Upload Rapido receipts")
st.caption(f"PDF folder: `{RAPIDO_FOLDER}`")
_run_upload_section(
    label="Rapido",
    folder=RAPIDO_FOLDER,
    upload_main=upload_rapido_to_concur.main,
    button_key="upload_rapido",
)
