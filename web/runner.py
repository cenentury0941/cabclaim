"""Capture stdout/stderr while running a script callable."""

from __future__ import annotations

import contextlib
import io
import traceback
from collections.abc import Callable
from typing import Any


def run_captured(target: Callable[[], Any], *, label: str = "task") -> tuple[bool, str]:
    """Run target, return (ok, combined log text)."""
    buf = io.StringIO()
    ok = False
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            print(f"—— Running: {label} ——")
            target()
            print(f"—— Finished: {label} ——")
            ok = True
        except Exception:
            print(traceback.format_exc())
            print(f"—— Failed: {label} ——")
    return ok, buf.getvalue()
