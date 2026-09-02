"""Get Uber Receipts — download and filter PDFs by month + PIN."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

import get_uber_receipts
from web.pdf_preview import list_pdfs, render_pdf_pages
from web.runner import run_streaming

st.set_page_config(page_title="Get Uber Receipts — CabClaim", layout="wide")
st.title("Get Uber Receipts")
st.write(
    "Download Uber receipt PDFs for the selected month, keep those matching the "
    f"pincode, and preview files in `{get_uber_receipts.OUTPUT_DIR}`."
)

if "uber_receipt_month" not in st.session_state:
    st.session_state.uber_receipt_month = get_uber_receipts.TARGET_MONTH
if "uber_receipt_pin" not in st.session_state:
    try:
        st.session_state.uber_receipt_pin = int(get_uber_receipts.TARGET_PIN)
    except ValueError:
        st.session_state.uber_receipt_pin = 600032

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
    pin = st.number_input(
        "Pincode",
        min_value=100000,
        max_value=999999,
        step=1,
        format="%d",
        key="uber_receipt_pin",
    )

activities_path = Path(get_uber_receipts.ACTIVITIES_FILE)
if not activities_path.is_file():
    st.warning(
        f"`{activities_path}` not found. Run **Get Activities** first."
    )

run_clicked = st.button("Run", type="primary")

progress_slot = st.empty()
status_slot = st.empty()
log_slot = st.empty()
live_list_slot = st.empty()


def _render_live_receipts(highlight: str | None = None) -> None:
    pdfs = list_pdfs(get_uber_receipts.OUTPUT_DIR)
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
    cookie_header = (st.session_state.get("uber_cookie_header") or "").strip() or None
    if cookie_header is None and not Path(get_uber_receipts.COOKIE_FILE).is_file():
        st.error(
            "No Uber cookie available. Paste one on **Get Activities** "
            f"or provide `{get_uber_receipts.COOKIE_FILE}`."
        )
    elif not activities_path.is_file():
        st.error(f"Missing `{activities_path}`.")
    else:
        progress_slot.progress(0, text="Starting…")
        status_slot.info("Downloading Uber receipts…")
        _render_live_receipts()

        def on_output(text: str) -> None:
            log_slot.code(text or "(no output)", language="text")

        def on_progress(event: dict) -> None:
            phase = event.get("phase")
            index = int(event.get("index") or 0)
            total = int(event.get("total") or 0)
            path = event.get("path")

            if phase == "cleared":
                cleared = event.get("cleared", 0)
                progress_slot.progress(0, text="Destination cleared — starting…")
                status_slot.info(
                    f"Cleared {cleared} item(s) from `{get_uber_receipts.OUTPUT_DIR}`."
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

        ok, log = run_streaming(
            lambda: get_uber_receipts.main(
                target_month=month,
                target_pin=int(pin),
                cookie_header=cookie_header,
                on_progress=on_progress,
            ),
            label="Get Uber Receipts",
            on_output=on_output,
        )

        log_slot.code(log or "(no output)", language="text")
        if ok:
            status_slot.success(
                f"Done — receipts in `{get_uber_receipts.OUTPUT_DIR}`."
            )
            progress_slot.progress(1.0, text="Complete")
        else:
            status_slot.error("Run failed — see log above.")

st.divider()
st.subheader("Downloaded receipts")

pdfs = list_pdfs(get_uber_receipts.OUTPUT_DIR)
if not pdfs:
    st.caption(f"No PDFs in `{get_uber_receipts.OUTPUT_DIR}` yet.")
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
        selected_path = Path(get_uber_receipts.OUTPUT_DIR) / selected_name
        st.markdown(f"**{selected_name}**")
        try:
            pages = render_pdf_pages(selected_path)
            for i, png in enumerate(pages, start=1):
                st.caption(f"Page {i}")
                st.image(png, use_container_width=True)
        except Exception as exc:
            st.error(f"Could not render PDF: {exc}")
