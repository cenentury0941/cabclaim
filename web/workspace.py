"""Workspace helpers for the CabClaim web UI."""

from __future__ import annotations

import shutil
from pathlib import Path

import streamlit as st

WORKSPACE_DIR = Path("workspace")
_CLEARED_KEY = "_cabclaim_workspace_cleared"


def clear_workspace(workspace: Path = WORKSPACE_DIR) -> tuple[int, list[str]]:
    """
    Delete all files and subfolders inside workspace/.
    Recreates an empty workspace/ directory.
    Returns (removed_entry_count, list of top-level names removed).
    """
    removed: list[str] = []

    if workspace.exists():
        for entry in sorted(workspace.iterdir()):
            removed.append(entry.name)
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
    else:
        workspace.mkdir(parents=True, exist_ok=True)
        return 0, []

    workspace.mkdir(parents=True, exist_ok=True)
    return len(removed), removed


def clear_workspace_on_session_start() -> None:
    """Wipe workspace/ once when a Streamlit session begins."""
    if st.session_state.get(_CLEARED_KEY):
        return
    clear_workspace()
    st.session_state[_CLEARED_KEY] = True
