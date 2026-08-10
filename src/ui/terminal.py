"""
Helpers for cleaner Rich <-> questionary / prompt_toolkit handoffs.

For select menus, prefer ansi_clear() + questionary with no Rich output
immediately beforehand. Rich leaves a stray Windows cursor on menu screens.
"""

import sys
from contextlib import contextmanager
from typing import Iterator, Optional


_HIDE_CURSOR = "\033[?25l"
_SHOW_CURSOR = "\033[?25h"
_ANSI_CLEAR = "\033[2J\033[H"


def ansi_clear() -> None:
    """Clear the terminal with ANSI (no Rich) and move cursor home."""
    try:
        sys.stdout.write(_ANSI_CLEAR)
        sys.stdout.flush()
    except Exception:
        pass


def hide_cursor() -> None:
    """Hide the terminal text cursor."""
    try:
        sys.stdout.write(_HIDE_CURSOR)
        sys.stdout.flush()
    except Exception:
        pass


def show_cursor() -> None:
    """Show the terminal text cursor."""
    try:
        sys.stdout.write(_SHOW_CURSOR)
        sys.stdout.flush()
    except Exception:
        pass


@contextmanager
def hidden_cursor() -> Iterator[None]:
    """Hide the cursor for the duration of a block (e.g. select menus)."""
    hide_cursor()
    try:
        yield
    finally:
        show_cursor()


def sync_after_rich(console: Optional[object] = None) -> None:
    """
    Flush Rich/stdout so the next prompt_toolkit UI starts cleanly.

    Call this after Rich output (clear, panels, status) and before
    questionary / prompt_toolkit prompts.
    """
    try:
        if console is not None:
            file = getattr(console, "file", None)
            if file is not None:
                file.flush()
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass


def print_plain(text: str = "") -> None:
    """Print plain text via stdout (safe immediately before questionary)."""
    try:
        if text and not text.endswith("\n"):
            text = text + "\n"
        elif text == "":
            text = "\n"
        sys.stdout.write(text)
        sys.stdout.flush()
    except Exception:
        pass
