"""Get Uber Receipts — fetch activities, then download/filter PDFs by month + PIN."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

import get_activities
import get_uber_receipts
from web.page_consent import require_page_consent
from web.pdf_preview import list_pdfs, render_pdf_pages
from web.runner import run_captured, run_streaming
from web.session_state import (
    ensure_ephemeral_text,
    ensure_receipt_pin,
    receipt_pin_input,
    save_uber_activities_cookie,
)
from web.workspace import clear_workspace_on_session_start, workspace_paths

st.set_page_config(page_title="Get Uber Receipts — CabClaim", layout="wide")
require_page_consent()
clear_workspace_on_session_start()
paths = workspace_paths()

st.title("Get Uber Receipts")
st.write(
    "Paste the Uber Cookie header, pick a month and pincode, then run. "
    "This fetches trip activities into "
    f"`{paths.activities}`, downloads receipt PDFs for the selected "
    f"month, keeps those matching the pincode, and previews files in "
    f"`{paths.uber_receipts}`."
)

ensure_ephemeral_text("uber_cookie_header")

if "uber_receipt_month" not in st.session_state:
    st.session_state.uber_receipt_month = get_uber_receipts.TARGET_MONTH
ensure_receipt_pin(default=get_uber_receipts.TARGET_PIN)

st.text_area(
    "Cookie Header",
    key="uber_cookie_header",
    height=140,
    help="Browser Cookie header for riders.uber.com",
)
ensure_ephemeral_text("uber_cookie_header")

col_month, col_pin = st.columns(2)
with col_month:
    month_index = 0
    if st.session_state.uber_receipt_month in get_uber_receipts.MONTHS:
        month_index = get_uber_receipts.MONTHS.index(st.session_state.uber_receipt_month)
    month = st.selectbox(
        "Month",
        options=list(get_uber_receipts.MONTHS),
        index=month_index,
    )
    st.session_state.uber_receipt_month = month

with col_pin:
    pin = receipt_pin_input()

run_clicked = st.button("Run", type="primary")

progress_slot = st.empty()
status_slot = st.empty()
log_slot = st.empty()
live_list_slot = st.empty()


def _render_live_receipts(highlight: str | None = None) -> None:
    pdfs = list_pdfs(paths.uber_receipts)
    with live_list_slot.container():
        st.markdown("**Receipts (live)**")
        if not pdfs:
            st.caption("Waiting for downloads…")
            return
        for path in pdfs:
            label = path.name
            if highlight and path.name == highlight:
                st.markdown(f"- **{label}** ← saved")
            else:
                st.markdown(f"- {label}")


if run_clicked:
    header = (st.session_state.get("uber_cookie_header") or "").strip()
    if not header:
        st.error("Cookie Header is empty.")
    else:
        status_slot.info("Fetching Uber activities…")
        progress_slot.progress(0, text="Fetching activities…")
        ok_activities, activities_log = run_captured(
            lambda: get_activities.main(
                cookie_header=header,
                output_file=str(paths.activities),
            ),
            label="Get Activities",
        )
        log_slot.code(activities_log or "(no output)", language="text")

        if not ok_activities:
            status_slot.error("Fetching activities failed — see log above.")
        else:
            save_uber_activities_cookie(header)
            status_slot.info("Activities saved — downloading Uber receipts…")
            progress_slot.progress(0, text="Starting receipt download…")
            _render_live_receipts()

            combined_parts = [activities_log]

            def on_output(text: str) -> None:
                combined = "\n".join(combined_parts + [text])
                log_slot.code(combined or "(no output)", language="text")

            def on_progress(event: dict) -> None:
                phase = event.get("phase")
                index = int(event.get("index") or 0)
                total = int(event.get("total") or 0)
                path = event.get("path")

                if phase == "cleared":
                    cleared = event.get("cleared", 0)
                    progress_slot.progress(0, text="Destination cleared — starting…")
                    status_slot.info(
                        f"Cleared {cleared} item(s) from `{paths.uber_receipts}`."
                    )
                    _render_live_receipts()
                elif phase == "start":
                    progress_slot.progress(
                        0,
                        text=f"Found {total} trip(s) — starting download…",
                    )
                    status_slot.info(f"Downloading 0 / {total}…")
                elif phase == "download":
                    frac = (index / total) if total else 1.0
                    name = Path(path).name if path else "(not saved)"
                    progress_slot.progress(
                        min(frac, 1.0),
                        text=f"Download {index} / {total}: {name}",
                    )
                    status_slot.info(f"Downloading {index} / {total}…")
                    _render_live_receipts(highlight=Path(path).name if path else None)
                elif phase == "filter":
                    frac = (index / total) if total else 1.0
                    kept = event.get("kept")
                    filename = event.get("filename") or ""
                    action = "kept" if kept else "removed"
                    progress_slot.progress(
                        min(frac, 1.0),
                        text=f"Filter {index} / {total}: {filename} ({action})",
                    )
                    status_slot.info(f"Filtering by pincode… {index} / {total}")
                    _render_live_receipts()
                elif phase == "done":
                    progress_slot.progress(1.0, text="Complete")
                    _render_live_receipts()

            ok, receipts_log = run_streaming(
                lambda: get_uber_receipts.main(
                    target_month=month,
                    target_pin=int(pin),
                    cookie_header=header,
                    activities_file=str(paths.activities),
                    output_dir=str(paths.uber_receipts),
                    deleted_dir=str(paths.deleted_uber_receipts),
                    on_progress=on_progress,
                ),
                label="Get Uber Receipts",
                on_output=on_output,
            )
            combined_parts.append(receipts_log)
            log_slot.code("\n".join(combined_parts) or "(no output)", language="text")

            if ok:
                status_slot.success(
                    f"Done — activities in `{paths.activities}`, "
                    f"receipts in `{paths.uber_receipts}`."
                )
                progress_slot.progress(1.0, text="Complete")
            else:
                status_slot.error("Receipt download failed — see log above.")

st.divider()
st.subheader("Downloaded receipts")

pdfs = list_pdfs(paths.uber_receipts)
if not pdfs:
    st.caption(f"No PDFs in `{paths.uber_receipts}` yet.")
else:
    names = [p.name for p in pdfs]
    if "uber_receipt_selected" not in st.session_state:
        st.session_state.uber_receipt_selected = names[0]
    if st.session_state.uber_receipt_selected not in names:
        st.session_state.uber_receipt_selected = names[0]

    list_col, preview_col = st.columns([1, 2])

    with list_col:
        selected_name = st.radio(
            "Select a PDF",
            options=names,
            key="uber_receipt_selected",
            label_visibility="collapsed",
        )

    with preview_col:
        selected_path = paths.uber_receipts / selected_name
        st.markdown(f"**{selected_name}**")
        try:
            pages = render_pdf_pages(selected_path)
            for i, png in enumerate(pages, start=1):
                st.caption(f"Page {i}")
                st.image(png, use_container_width=True)
        except Exception as exc:
            st.error(f"Could not render PDF: {exc}")
