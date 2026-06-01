"""Graceful cancellation via Ctrl-C.

Long-running operations (export, import, sync, clean_space) install a SIGINT
handler that:

  - First Ctrl-C  → sets a module-level Event, prints a hint, and lets in-flight
    work observe the flag and bail out cleanly between pages / retries.
  - Second Ctrl-C within a few seconds → restores the default handler and
    re-raises KeyboardInterrupt so Python tears the process down hard.

Call sites use `check_cancelled()` between units of work and
`cancellable_sleep()` instead of `time.sleep()` so retry back-offs interrupt
immediately.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_cancelled = threading.Event()
_press_count = 0
_previous_handler: Optional[signal.Handlers] = None
_handler_installed = False


class CancelledError(KeyboardInterrupt):
    """Raised when a long-running operation observes the cancel flag.

    Inherits from KeyboardInterrupt so existing `except KeyboardInterrupt:`
    handlers in command code catch graceful cancellations without any
    refactor — the user gets the same "cancelled by user" message
    whether the signal was observed mid-sleep, between pages, or
    in-flight.
    """


def is_cancelled() -> bool:
    return _cancelled.is_set()


def check_cancelled() -> None:
    """Raise CancelledError if the user has pressed Ctrl-C."""
    if _cancelled.is_set():
        raise CancelledError("Cancelled by user (Ctrl-C)")


def cancellable_sleep(seconds: float) -> None:
    """Sleep, but return immediately and raise CancelledError if cancelled."""
    if seconds <= 0:
        check_cancelled()
        return
    if _cancelled.wait(seconds):
        raise CancelledError("Cancelled by user (Ctrl-C)")


def install_handler() -> None:
    """Install the two-stage SIGINT handler. Idempotent."""
    global _handler_installed, _previous_handler

    if _handler_installed:
        return

    def handler(signum, frame):  # noqa: ARG001
        global _press_count
        _press_count += 1
        if _press_count == 1:
            _cancelled.set()
            try:
                sys.stderr.write(
                    "\n\n[Ctrl-C received] Cancelling — finishing the current "
                    "HTTP request, then exiting cleanly.\n"
                    "Press Ctrl-C again to force-quit immediately.\n\n"
                )
                sys.stderr.flush()
            except Exception:
                pass
        else:
            # Hard-out. os._exit skips finally/atexit; we want that — the user
            # has already asked twice. 130 is the conventional shell exit code
            # for SIGINT-terminated programs.
            try:
                sys.stderr.write("\n[Ctrl-C x2] Force-quit.\n")
                sys.stderr.flush()
            except Exception:
                pass
            os._exit(130)

    try:
        _previous_handler = signal.signal(signal.SIGINT, handler)
        _handler_installed = True
    except (ValueError, OSError) as exc:
        # signal.signal() only works in the main thread; if we're not there
        # (rare for a CLI), fall back to default behavior with a warning.
        logger.debug(f"Could not install SIGINT handler: {exc}")


def uninstall_handler() -> None:
    """Restore the previous SIGINT handler. Used between distinct command
    invocations within the same process (e.g. inside the wizard loop)."""
    global _handler_installed, _previous_handler, _press_count
    if not _handler_installed:
        return
    try:
        if _previous_handler is not None:
            signal.signal(signal.SIGINT, _previous_handler)
        else:
            signal.signal(signal.SIGINT, signal.SIG_DFL)
    except (ValueError, OSError):
        pass
    _handler_installed = False
    _previous_handler = None
    _press_count = 0
    _cancelled.clear()


def reset() -> None:
    """Clear cancellation state without touching signal handlers.
    Useful before starting a new logical operation inside the wizard."""
    global _press_count
    _cancelled.clear()
    _press_count = 0
