"""Get Activities — fetch Uber trips into workspace/Activities.json."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

import get_activities
from web.runner import run_captured
from web.session_state import save_uber_activities_cookie

st.set_page_config(page_title="Get Activities — CabClaim", layout="wide")
st.title("Get Activities")
st.write(
    "Paste the Uber Cookie header from the browser. "
    f"This fetches trip activities and saves `{get_activities.OUTPUT_FILE}`."
)

if "uber_cookie_header" not in st.session_state:
    default = ""
    path = Path(get_activities.COOKIE_FILE)
    if path.is_file():
        default = path.read_text(encoding="utf-8").strip()
    st.session_state.uber_cookie_header = default

st.text_area(
    "Cookie Header",
    key="uber_cookie_header",
    height=180,
    help="Browser Cookie header for riders.uber.com",
)

col_load, col_run = st.columns([1, 1])

with col_load:
    if st.button("Load from Uber_Cookie.txt", use_container_width=True):
        path = Path(get_activities.COOKIE_FILE)
        if not path.is_file():
            st.error(f"File not found: {path}")
        else:
            st.session_state.uber_cookie_header = path.read_text(encoding="utf-8").strip()
            st.success(f"Loaded from {path}")
            st.rerun()

with col_run:
    run_clicked = st.button("Run", type="primary", use_container_width=True)

if run_clicked:
    header = (st.session_state.get("uber_cookie_header") or "").strip()
    if not header:
        st.error("Cookie Header is empty.")
    else:
        with st.spinner("Fetching activities…"):
            ok, log = run_captured(
                lambda: get_activities.main(cookie_header=header),
                label="Get Activities",
            )
        st.subheader("Log")
        st.code(log or "(no output)", language="text")
        if ok:
            save_uber_activities_cookie(header)
            st.success(f"Done — saved to `{get_activities.OUTPUT_FILE}`.")
        else:
            st.error("Run failed — see log above.")
