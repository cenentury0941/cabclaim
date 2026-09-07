"""Persist Streamlit text-field values in browser cookies across sessions."""

from __future__ import annotations

import datetime

import extra_streamlit_components as stx
import streamlit as st

# Browser cookie names for each session_state field key.
# Cookie header fields are intentionally omitted — they stay empty each session.
FIELD_COOKIE_NAMES: dict[str, str] = {
    "concur_report_id": "cc_concur_rid",
    "concur_user_id": "cc_concur_uid",
}

# Previously persisted header cookies; cleared when we next write field cookies.
_OBSOLETE_COOKIE_NAMES = ("cc_uber_hdr", "cc_concur_hdr")

# Stay under typical ~4KB cookie limits (name + attributes included).
_CHUNK_SIZE = 3000
_EXPIRES_DAYS = 365
_MANAGER_KEY = "cabclaim_field_cookies"
_DIRTY_KEY = "_cabclaim_cookie_dirty"
_SEQ_KEY = "_cabclaim_cookie_seq"


def _manager() -> stx.CookieManager:
    return stx.CookieManager(key=_MANAGER_KEY)


def _next_key(prefix: str) -> str:
    seq = int(st.session_state.get(_SEQ_KEY) or 0) + 1
    st.session_state[_SEQ_KEY] = seq
    return f"{prefix}_{seq}"


def _expires_at() -> datetime.datetime:
    return datetime.datetime.now() + datetime.timedelta(days=_EXPIRES_DAYS)


def _backup_key(session_key: str) -> str:
    return f"_cabclaim_saved_{session_key}"


def _read_browser_value(cookie_name: str) -> str:
    """Read a (possibly chunked) value from cookies on the current HTTP request."""
    cookies = st.context.cookies
    count_raw = cookies.get(f"{cookie_name}__n")
    if count_raw is not None:
        try:
            count = int(count_raw)
        except (TypeError, ValueError):
            return ""
        parts: list[str] = []
        for i in range(count):
            part = cookies.get(f"{cookie_name}__{i}")
            if part is None:
                return ""
            parts.append(part)
        return "".join(parts)
    return cookies.get(cookie_name) or ""


def hydrate_text_fields(*session_keys: str) -> None:
    """Initialize session_state from backup or browser cookies; missing keys stay empty."""
    for session_key in session_keys:
        backup_key = _backup_key(session_key)
        if session_key not in st.session_state:
            if backup_key in st.session_state:
                st.session_state[session_key] = st.session_state[backup_key]
            else:
                cookie_name = FIELD_COOKIE_NAMES.get(session_key)
                st.session_state[session_key] = (
                    _read_browser_value(cookie_name) if cookie_name else ""
                )
        st.session_state[backup_key] = st.session_state.get(session_key) or ""


def mark_field_dirty(session_key: str) -> None:
    """Widget on_change callback: queue this field for browser-cookie write."""
    dirty = st.session_state.setdefault(_DIRTY_KEY, [])
    if session_key not in dirty:
        dirty.append(session_key)
    st.session_state[_backup_key(session_key)] = st.session_state.get(session_key) or ""


def _known_cookie_names(cookie_name: str, cookies: dict) -> list[str]:
    names: list[str] = []
    count_raw = cookies.get(f"{cookie_name}__n")
    if count_raw is not None:
        try:
            count = int(count_raw)
        except (TypeError, ValueError):
            count = 0
        names.append(f"{cookie_name}__n")
        names.extend(f"{cookie_name}__{i}" for i in range(count))
    if cookie_name in cookies:
        names.append(cookie_name)
    # Also clear leftovers using request cookies as a hint.
    request_cookies = st.context.cookies
    req_count = request_cookies.get(f"{cookie_name}__n")
    if req_count is not None:
        try:
            count = int(req_count)
        except (TypeError, ValueError):
            count = 0
        names.append(f"{cookie_name}__n")
        names.extend(f"{cookie_name}__{i}" for i in range(count))
    if request_cookies.get(cookie_name) is not None:
        names.append(cookie_name)
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def _delete_cookie(manager: stx.CookieManager, cookie_name: str) -> None:
    cookies = dict(manager.cookies or {})
    for name in _known_cookie_names(cookie_name, cookies):
        manager.delete(name, key=_next_key(f"del_{name}"))


def _write_cookie(manager: stx.CookieManager, cookie_name: str, value: str) -> None:
    _delete_cookie(manager, cookie_name)
    value = value or ""
    if not value:
        return

    expires = _expires_at()
    if len(value) <= _CHUNK_SIZE:
        manager.set(
            cookie_name,
            value,
            key=_next_key(f"set_{cookie_name}"),
            path="/",
            expires_at=expires,
            same_site="lax",
        )
        return

    chunks = [value[i : i + _CHUNK_SIZE] for i in range(0, len(value), _CHUNK_SIZE)]
    manager.set(
        f"{cookie_name}__n",
        str(len(chunks)),
        key=_next_key(f"set_{cookie_name}_n"),
        path="/",
        expires_at=expires,
        same_site="lax",
    )
    for i, chunk in enumerate(chunks):
        manager.set(
            f"{cookie_name}__{i}",
            chunk,
            key=_next_key(f"set_{cookie_name}_{i}"),
            path="/",
            expires_at=expires,
            same_site="lax",
        )


def persist_dirty_fields() -> None:
    """Write dirty text fields to browser cookies. Call after the related widgets."""
    dirty = list(st.session_state.pop(_DIRTY_KEY, None) or [])
    if not dirty:
        return
    manager = _manager()
    if not st.session_state.get("_cabclaim_cleared_obsolete_hdr"):
        for name in _OBSOLETE_COOKIE_NAMES:
            _delete_cookie(manager, name)
        st.session_state["_cabclaim_cleared_obsolete_hdr"] = True
    for session_key in dirty:
        cookie_name = FIELD_COOKIE_NAMES.get(session_key)
        if cookie_name is None:
            continue
        value = st.session_state.get(session_key) or ""
        if not isinstance(value, str):
            value = str(value)
        st.session_state[_backup_key(session_key)] = value
        _write_cookie(manager, cookie_name, value)


def persist_field_now(session_key: str) -> None:
    """Immediately persist one field to a browser cookie."""
    mark_field_dirty(session_key)
    persist_dirty_fields()
