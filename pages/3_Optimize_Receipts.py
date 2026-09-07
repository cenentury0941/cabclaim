"""Optimize Receipts — pick the best subset under a spend limit."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import streamlit as st

import optimize_receipts
from web.pdf_preview import list_pdfs, render_pdf_pages
from web.runner import run_captured
from web.workspace import clear_workspace_on_session_start, workspace_paths

st.set_page_config(page_title="Optimize Receipts — CabClaim", layout="wide")
clear_workspace_on_session_start()
paths = workspace_paths()

st.title("Optimize Receipts")
st.write(
    "Choose the largest total fare from Uber and Rapido receipts that stays under "
    "your spend limit. Receipts that do not fit are set aside."
)

if "optimize_max_amount" not in st.session_state:
    st.session_state.optimize_max_amount = float(optimize_receipts.MAX_AMOUNT)

max_amount = st.number_input(
    "Spend limit (₹)",
    min_value=0.0,
    step=100.0,
    format="%.2f",
    key="optimize_max_amount",
)

uber_count = len(list_pdfs(paths.uber_receipts))
rapido_count = len(list_pdfs(paths.rapido_receipts))

st.caption(
    f"Found **{uber_count}** Uber and **{rapido_count}** Rapido receipt(s) ready to optimize."
)

run_clicked = st.button("Run", type="primary")

if run_clicked:
    if uber_count + rapido_count == 0:
        st.error(
            "No receipt PDFs found. Run **Get Uber Receipts** and/or "
            "**Ingest Rapido Receipts** first."
        )
    else:
        with st.spinner("Optimizing receipts…"):
            ok, log = run_captured(
                lambda: optimize_receipts.main(
                    max_amount=Decimal(str(max_amount)),
                    uber_dir=paths.uber_receipts,
                    rapido_dir=paths.rapido_receipts,
                    uber_overlimit_dir=paths.overlimit_uber_receipts,
                    rapido_overlimit_dir=paths.overlimit_rapido_receipts,
                ),
                label="Optimize Receipts",
            )
        st.subheader("Log")
        st.code(log or "(no output)", language="text")
        if ok:
            st.success("Done.")
        else:
            st.error("Run failed — see log above.")

st.divider()
st.subheader("Kept receipts")

kept_pdfs: list[tuple[str, Path]] = []
for label, folder in (
    ("Uber", paths.uber_receipts),
    ("Rapido", paths.rapido_receipts),
):
    for path in list_pdfs(folder):
        kept_pdfs.append((label, path))

if not kept_pdfs:
    st.caption("No kept receipts yet.")
else:
    options = [f"{label}: {path.name}" for label, path in kept_pdfs]
    if "optimize_receipt_selected" not in st.session_state:
        st.session_state.optimize_receipt_selected = options[0]
    if st.session_state.optimize_receipt_selected not in options:
        st.session_state.optimize_receipt_selected = options[0]

    list_col, preview_col = st.columns([1, 2])

    with list_col:
        selected = st.radio(
            "Select a PDF",
            options=options,
            key="optimize_receipt_selected",
            label_visibility="collapsed",
        )

    with preview_col:
        idx = options.index(selected)
        label, selected_path = kept_pdfs[idx]
        st.markdown(f"**{label} — {selected_path.name}**")
        try:
            pages = render_pdf_pages(selected_path)
            for i, png in enumerate(pages, start=1):
                st.caption(f"Page {i}")
                st.image(png, use_container_width=True)
        except Exception as exc:
            st.error(f"Could not render PDF: {exc}")
