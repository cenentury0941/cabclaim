"""Get Uber Receipts — download and filter PDFs by month + PIN."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

import get_uber_receipts
from web.pdf_preview import list_pdfs, render_pdf_pages
from web.runner import run_captured

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
        with st.spinner("Downloading and filtering Uber receipts…"):
            ok, log = run_captured(
                lambda: get_uber_receipts.main(
                    target_month=month,
                    target_pin=int(pin),
                    cookie_header=cookie_header,
                ),
                label="Get Uber Receipts",
            )
        st.subheader("Log")
        st.code(log or "(no output)", language="text")
        if ok:
            st.success(f"Done — receipts in `{get_uber_receipts.OUTPUT_DIR}`.")
        else:
            st.error("Run failed — see log above.")

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
