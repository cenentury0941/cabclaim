"""CabClaim — local web UI (Streamlit)."""

from __future__ import annotations

import streamlit as st

from web.workspace import clear_workspace, clear_workspace_on_session_start, workspace_paths

st.set_page_config(
    page_title="CabClaim",
    layout="wide",
    initial_sidebar_state="expanded",
)

clear_workspace_on_session_start()
paths = workspace_paths()

st.title("CabClaim")
st.write(
    "Walk through each step to prepare and upload cab receipts. "
    "Use the sidebar to open a screen; more steps will appear as they are added."
)

st.subheader("Pipeline")
st.markdown(
    """
1. Fetch Uber activities & download receipts  
2. Ingest Rapido receipts  
3. Optimize under spend limit  
4. Upload receipts to Concur (Uber and Rapido)
"""
)

st.subheader("Workspace")
st.write(
    f"Runtime files for this browser live under `{paths.root}/` "
    "(activities JSON, receipt PDFs, overlimit folders, etc.). "
    "Each device gets its own subfolder so users on a shared host stay isolated."
)

if st.button("Clear workspace", type="secondary"):
    count, names = clear_workspace()
    if count == 0:
        st.info(f"`{paths.root}/` was already empty (or missing).")
    else:
        st.success(f"Cleared {count} item(s) from `{paths.root}/`.")
        if names:
            st.code("\n".join(names), language="text")

st.info("Open **Get Uber Receipts** in the sidebar to start.")
st.caption("Cookie headers stay in the browser session — do not share this UI publicly without access controls.")
