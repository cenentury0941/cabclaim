"""CabClaim — local web UI (Streamlit)."""

from __future__ import annotations

import streamlit as st

from web.workspace import WORKSPACE_DIR, clear_workspace

st.set_page_config(
    page_title="CabClaim",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("CabClaim")
st.write(
    "Walk through each step to prepare and upload cab receipts. "
    "Use the sidebar to open a screen; more steps will appear as they are added."
)

st.subheader("Pipeline")
st.markdown(
    """
1. Fetch Uber activities  
2. Download Uber receipts  
3. Ingest Rapido receipts  
4. Optimize under spend limit  
5. Upload Uber to Concur  
6. Upload Rapido to Concur  
"""
)

st.subheader("Workspace")
st.write(
    f"Runtime files live under `{WORKSPACE_DIR}/` "
    "(activities JSON, receipt PDFs, overlimit folders, etc.)."
)

if st.button("Clear workspace", type="secondary"):
    count, names = clear_workspace()
    if count == 0:
        st.info(f"`{WORKSPACE_DIR}/` was already empty (or missing).")
    else:
        st.success(f"Cleared {count} item(s) from `{WORKSPACE_DIR}/`.")
        if names:
            st.code("\n".join(names), language="text")

st.info("Open **Get Activities** in the sidebar to start.")
st.caption("Run locally only — cookie headers stay on this machine.")
