"""Upload Receipts — upload Uber and Rapido PDFs to Concur."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

import upload_rapido_to_concur
import upload_uber_to_concur
from web.pdf_preview import list_pdfs
from web.runner import run_captured

UBER_FOLDER = Path(upload_uber_to_concur.PDF_FOLDER)
RAPIDO_FOLDER = Path(upload_rapido_to_concur.PDF_FOLDER)
CONCUR_COOKIE_FILE = upload_uber_to_concur.COOKIE_FILE

st.set_page_config(page_title="Upload Receipts — CabClaim", layout="wide")
st.title("Upload Receipts")
st.write(
    "Upload optimized receipt PDFs to Concur as expense entries. "
    "Configure shared Concur settings below, then run Uber or Rapido upload separately."
)

if "concur_report_id" not in st.session_state:
    st.session_state.concur_report_id = upload_uber_to_concur.REPORT_ID
if "concur_user_id" not in st.session_state:
    st.session_state.concur_user_id = upload_uber_to_concur.USER_ID
if "concur_cookie_header" not in st.session_state:
    default = ""
    path = Path(CONCUR_COOKIE_FILE)
    if path.is_file():
        default = path.read_text(encoding="utf-8").strip()
    st.session_state.concur_cookie_header = default

st.subheader("Concur settings")

col_report, col_user = st.columns(2)
with col_report:
    st.text_input("Report ID", key="concur_report_id")
with col_user:
    st.text_input("User ID", key="concur_user_id")

st.text_area(
    "Concur Cookie Header",
    key="concur_cookie_header",
    height=140,
    help="Browser Cookie header for concursolutions.com",
)


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


st.divider()
st.subheader("Upload Uber receipts")
st.caption(f"PDF folder: `{UBER_FOLDER}`")

uber_count = len(list_pdfs(UBER_FOLDER))
st.caption(f"Found **{uber_count}** Uber receipt(s) ready to upload.")

upload_uber_clicked = st.button("Upload Uber", type="primary", key="upload_uber")

if upload_uber_clicked:
    error = _validate_concur_settings()
    if error:
        st.error(error)
    elif uber_count == 0:
        st.error("No Uber receipt PDFs found. Run earlier pipeline steps first.")
    else:
        with st.spinner("Uploading Uber receipts…"):
            ok, log = run_captured(
                lambda: upload_uber_to_concur.main(
                    **_shared_kwargs(),
                    pdf_folder=str(UBER_FOLDER),
                ),
                label="Upload Uber Receipts",
            )
        st.subheader("Uber log")
        st.code(log or "(no output)", language="text")
        if ok:
            st.success("Uber upload finished.")
        else:
            st.error("Uber upload failed — see log above.")

st.divider()
st.subheader("Upload Rapido receipts")
st.caption(f"PDF folder: `{RAPIDO_FOLDER}`")

rapido_count = len(list_pdfs(RAPIDO_FOLDER))
st.caption(f"Found **{rapido_count}** Rapido receipt(s) ready to upload.")

upload_rapido_clicked = st.button("Upload Rapido", type="primary", key="upload_rapido")

if upload_rapido_clicked:
    error = _validate_concur_settings()
    if error:
        st.error(error)
    elif rapido_count == 0:
        st.error("No Rapido receipt PDFs found. Run earlier pipeline steps first.")
    else:
        with st.spinner("Uploading Rapido receipts…"):
            ok, log = run_captured(
                lambda: upload_rapido_to_concur.main(
                    **_shared_kwargs(),
                    pdf_folder=str(RAPIDO_FOLDER),
                ),
                label="Upload Rapido Receipts",
            )
        st.subheader("Rapido log")
        st.code(log or "(no output)", language="text")
        if ok:
            st.success("Rapido upload finished.")
        else:
            st.error("Rapido upload failed — see log above.")
