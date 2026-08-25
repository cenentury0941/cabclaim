"""Capture or stream stdout/stderr while running a script callable."""

from __future__ import annotations

import contextlib
import io
import sys
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


class _LiveTee(io.TextIOBase):
    """Mirror writes to a buffer, the original stream, and an optional callback."""

    def __init__(
        self,
        original: Any,
        buffer: io.StringIO,
        on_write: Callable[[str], None] | None,
    ):
        self._original = original
        self._buffer = buffer
        self._on_write = on_write

    def write(self, s: str) -> int:
        if not s:
            return 0
        self._buffer.write(s)
        try:
            self._original.write(s)
        except Exception:
            pass
        if self._on_write is not None:
            self._on_write(self._buffer.getvalue())
        return len(s)

    def flush(self) -> None:
        try:
            self._original.flush()
        except Exception:
            pass


def run_streaming(
    target: Callable[[], Any],
    *,
    label: str = "task",
    on_output: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """
    Run target while streaming combined stdout/stderr to on_output(full_text)
    after each write. Returns (ok, full log text).
    """
    buf = io.StringIO()
    ok = False
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = _LiveTee(old_out, buf, on_output)
    sys.stderr = _LiveTee(old_err, buf, on_output)
    try:
        print(f"—— Running: {label} ——")
        target()
        print(f"—— Finished: {label} ——")
        ok = True
    except Exception:
        print(traceback.format_exc())
        print(f"—— Failed: {label} ——")
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
    return ok, buf.getvalue()
