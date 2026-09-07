"""Shared Streamlit session state for CabClaim screens."""

from __future__ import annotations

import streamlit as st

RECEIPT_PIN_KEY = "receipt_pin"
UBER_ACTIVITIES_COOKIE_KEY = "uber_activities_cookie_header"
_DEFAULT_RECEIPT_PIN = 600032
_LEGACY_RECEIPT_PIN_KEY = "uber_receipt_pin"


def save_uber_activities_cookie(header: str) -> None:
    """Store the cookie used for a successful activities fetch on Get Uber Receipts."""
    st.session_state[UBER_ACTIVITIES_COOKIE_KEY] = header.strip()


def uber_activities_cookie() -> str | None:
    """Cookie from the last successful activities fetch, if any."""
    value = (st.session_state.get(UBER_ACTIVITIES_COOKIE_KEY) or "").strip()
    return value or None


def ensure_receipt_pin(*, default: int | str | None = None) -> int:
    """Initialize the shared pincode used across receipt screens."""
    if RECEIPT_PIN_KEY not in st.session_state:
        if _LEGACY_RECEIPT_PIN_KEY in st.session_state:
            st.session_state[RECEIPT_PIN_KEY] = int(st.session_state[_LEGACY_RECEIPT_PIN_KEY])
        else:
            raw = default if default is not None else _DEFAULT_RECEIPT_PIN
            try:
                st.session_state[RECEIPT_PIN_KEY] = int(raw)
            except (TypeError, ValueError):
                st.session_state[RECEIPT_PIN_KEY] = _DEFAULT_RECEIPT_PIN
    return int(st.session_state[RECEIPT_PIN_KEY])


def ensure_ephemeral_text(session_key: str) -> None:
    """Init a text field empty each Streamlit session; keep value across page nav."""
    mem_key = f"_mem_{session_key}"
    if session_key not in st.session_state:
        st.session_state[session_key] = st.session_state.get(mem_key, "")
    st.session_state[mem_key] = st.session_state.get(session_key) or ""


def receipt_pin_input(**kwargs) -> int:
    """Pincode field shared by Get Uber Receipts and Ingest Rapido Receipts."""
    ensure_receipt_pin()
    kwargs.setdefault("label", "Pincode")
    kwargs.setdefault("min_value", 100000)
    kwargs.setdefault("max_value", 999999)
    kwargs.setdefault("step", 1)
    kwargs.setdefault("format", "%d")
    kwargs.setdefault("key", RECEIPT_PIN_KEY)
    return int(st.number_input(**kwargs))
