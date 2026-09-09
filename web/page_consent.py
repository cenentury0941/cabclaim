"""One-time browser consent dialog for CabClaim workflow pages."""

from __future__ import annotations

import base64
import datetime
from pathlib import Path

import extra_streamlit_components as stx
import streamlit as st

_COOKIE_NAME = "cc_page_consent"
_SESSION_KEY = "_cabclaim_page_consent"
_MANAGER_KEY = "cabclaim_page_consent_cookie"
_IMAGE_PATH = Path(__file__).parent / "assets" / "srtcs.jpg"


def _accepted() -> bool:
    if st.session_state.get(_SESSION_KEY):
        return True

    accepted = (st.context.cookies.get(_COOKIE_NAME) or "").strip() == "accepted"
    if accepted:
        st.session_state[_SESSION_KEY] = True
    return accepted


def _persist_acceptance() -> None:
    manager = stx.CookieManager(key=_MANAGER_KEY)
    manager.set(
        _COOKIE_NAME,
        "accepted",
        key="set_page_consent",
        path="/",
        expires_at=datetime.datetime.now() + datetime.timedelta(days=3650),
        same_site="lax",
    )


@st.dialog("\u200b", width="medium", dismissible=False)
def _show_dialog() -> None:
    image_data = base64.b64encode(_IMAGE_PATH.read_bytes()).decode("ascii")
    st.markdown(
        (
            '<div style="display:flex; justify-content:center; width:100%; margin-bottom:1rem;">'
            f'<img src="data:image/jpeg;base64,{image_data}" '
            'style="display:block; width:100%; max-width:640px; height:auto;" '
            'alt="Stop right there, criminal scum!">'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        (
            '<div style="padding:0 3.9rem; text-align:justify;">'
            "The technology implemented here is most likely in violation of Uber's and/or "
            "Concur's terms of service. Be fore-warned, ye who choose to venture down this "
            "path, that this is a high risk high reward scenario."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    exit_col, accept_col = st.columns(2)
    with exit_col:
        if st.button("Exit", width="stretch"):
            st.switch_page("app.py")
    with accept_col:
        if st.button(
            "Accept and Continue",
            type="primary",
            width="stretch",
        ):
            _persist_acceptance()
            st.session_state[_SESSION_KEY] = True
            st.rerun()


def require_page_consent() -> None:
    """Show the consent dialog unless this browser has already accepted it."""
    if not _accepted():
        _show_dialog()
