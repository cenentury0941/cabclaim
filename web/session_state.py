"""Shared Streamlit session state for CabClaim screens."""

from __future__ import annotations

import streamlit as st

RECEIPT_PIN_KEY = "receipt_pin"
_DEFAULT_RECEIPT_PIN = 600032
_LEGACY_RECEIPT_PIN_KEY = "uber_receipt_pin"


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
