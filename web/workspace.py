"""Workspace helpers for the CabClaim web UI.

Runtime files are stored under ``workspace/<device_id>/`` so multiple users on
the same Streamlit host cannot read or overwrite each other's data. The device
ID is a UUID persisted in a browser cookie.
"""

from __future__ import annotations

import datetime
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

import extra_streamlit_components as stx
import streamlit as st

WORKSPACE_ROOT = Path("workspace")
# Back-compat alias used by older call sites / docs.
WORKSPACE_DIR = WORKSPACE_ROOT

_DEVICE_COOKIE = "cc_device_id"
_DEVICE_SESSION_KEY = "_cabclaim_device_id"
_CLEARED_KEY = "_cabclaim_workspace_cleared"
_MANAGER_KEY = "cabclaim_device_cookie"
_SEQ_KEY = "_cabclaim_device_cookie_seq"
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class WorkspacePaths:
    """Resolved paths under the current device's workspace folder."""

    root: Path
    activities: Path
    uber_receipts: Path
    deleted_uber_receipts: Path
    rapido_receipts: Path
    deleted_rapido_receipts: Path
    overlimit_uber_receipts: Path
    overlimit_rapido_receipts: Path
    rapido_ingest: Path


def _manager() -> stx.CookieManager:
    return stx.CookieManager(key=_MANAGER_KEY)


def _next_key(prefix: str) -> str:
    seq = int(st.session_state.get(_SEQ_KEY) or 0) + 1
    st.session_state[_SEQ_KEY] = seq
    return f"{prefix}_{seq}"


def _is_valid_device_id(value: str | None) -> bool:
    return bool(value and _UUID_RE.fullmatch(value))


def _read_device_id_cookie() -> str | None:
    raw = (st.context.cookies.get(_DEVICE_COOKIE) or "").strip()
    return raw if _is_valid_device_id(raw) else None


def _write_device_id_cookie(device_id: str) -> None:
    expires = datetime.datetime.now() + datetime.timedelta(days=365)
    manager = _manager()
    manager.set(
        _DEVICE_COOKIE,
        device_id,
        key=_next_key("set_device"),
        path="/",
        expires_at=expires,
        same_site="lax",
    )


def ensure_device_id() -> str:
    """Return a stable per-browser device ID, creating and cookie-persisting if needed."""
    existing = st.session_state.get(_DEVICE_SESSION_KEY)
    if _is_valid_device_id(existing):
        return existing

    from_cookie = _read_device_id_cookie()
    if from_cookie:
        st.session_state[_DEVICE_SESSION_KEY] = from_cookie
        return from_cookie

    device_id = str(uuid.uuid4())
    st.session_state[_DEVICE_SESSION_KEY] = device_id
    _write_device_id_cookie(device_id)
    return device_id


def device_workspace() -> Path:
    """Return ``workspace/<device_id>/``, creating it if missing."""
    device_id = ensure_device_id()
    # device_id is a validated UUID, so this cannot escape WORKSPACE_ROOT.
    path = WORKSPACE_ROOT / device_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def workspace_paths() -> WorkspacePaths:
    """Paths for scripts and UI previews, scoped to the current device."""
    root = device_workspace()
    return WorkspacePaths(
        root=root,
        activities=root / "Activities.json",
        uber_receipts=root / "uber_receipts",
        deleted_uber_receipts=root / "deleted_uber_receipts",
        rapido_receipts=root / "rapido_receipts",
        deleted_rapido_receipts=root / "deleted_rapido_receipts",
        overlimit_uber_receipts=root / "overlimit_uber_receipts",
        overlimit_rapido_receipts=root / "overlimit_rapido_receipts",
        rapido_ingest=root / "rapido_ingest",
    )


def clear_workspace(workspace: Path | None = None) -> tuple[int, list[str]]:
    """
    Delete all files and subfolders inside the given workspace directory
    (defaults to the current device folder). Recreates an empty directory.
    Returns (removed_entry_count, list of top-level names removed).
    """
    target = workspace if workspace is not None else device_workspace()
    removed: list[str] = []

    if target.exists():
        for entry in sorted(target.iterdir()):
            removed.append(entry.name)
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
    else:
        target.mkdir(parents=True, exist_ok=True)
        return 0, []

    target.mkdir(parents=True, exist_ok=True)
    return len(removed), removed


def clear_workspace_on_session_start() -> None:
    """Wipe this device's workspace once when a Streamlit session begins."""
    ensure_device_id()
    if st.session_state.get(_CLEARED_KEY):
        return
    clear_workspace()
    st.session_state[_CLEARED_KEY] = True
