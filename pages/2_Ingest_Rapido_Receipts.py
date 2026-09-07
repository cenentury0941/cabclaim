"""Ingest Rapido Receipts — sort PDFs by PIN into keep/delete folders."""

from __future__ import annotations

import streamlit as st

import ingest_rapido_receipts
from web.pdf_preview import list_pdfs, render_pdf_pages
from web.runner import run_captured
from web.session_state import ensure_receipt_pin, receipt_pin_input
from web.workspace import clear_workspace_on_session_start

KEEP_FOLDER = ingest_rapido_receipts.KEEP_FOLDER

st.set_page_config(page_title="Ingest Rapido Receipts — CabClaim", layout="wide")
clear_workspace_on_session_start()
st.title("Ingest Rapido Receipts")
st.write(
    "Upload a zip of Rapido receipt PDFs. Only cab receipts matching the pincode "
    "are kept; auto receipts and non-matching files are discarded."
)

ensure_receipt_pin(default=ingest_rapido_receipts.PINCODE)

zip_file = st.file_uploader("Rapido receipts (zip)", type=["zip"])
pin = receipt_pin_input()

run_clicked = st.button("Run", type="primary")

if run_clicked:
    if zip_file is None:
        st.error("Select a zip file first.")
    else:
        zip_bytes = zip_file.getvalue()

        with st.spinner("Ingesting Rapido receipts…"):
            ok, log = run_captured(
                lambda: ingest_rapido_receipts.main(
                    pincode=int(pin),
                    zip_source=zip_bytes,
                ),
                label="Ingest Rapido Receipts",
            )
        st.subheader("Log")
        st.code(log or "(no output)", language="text")
        if ok:
            st.success("Done.")
        else:
            st.error("Run failed — see log above.")

st.divider()
st.subheader("Kept receipts")

pdfs = list_pdfs(KEEP_FOLDER)
if not pdfs:
    st.caption("No kept receipts yet.")
else:
    names = [p.name for p in pdfs]
    if "rapido_receipt_selected" not in st.session_state:
        st.session_state.rapido_receipt_selected = names[0]
    if st.session_state.rapido_receipt_selected not in names:
        st.session_state.rapido_receipt_selected = names[0]

    list_col, preview_col = st.columns([1, 2])

    with list_col:
        selected_name = st.radio(
            "Select a PDF",
            options=names,
            key="rapido_receipt_selected",
            label_visibility="collapsed",
        )

    with preview_col:
        selected_path = KEEP_FOLDER / selected_name
        st.markdown(f"**{selected_name}**")
        try:
            pages = render_pdf_pages(selected_path)
            for i, png in enumerate(pages, start=1):
                st.caption(f"Page {i}")
                st.image(png, use_container_width=True)
        except Exception as exc:
            st.error(f"Could not render PDF: {exc}")
